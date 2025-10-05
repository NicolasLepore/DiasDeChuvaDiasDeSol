# -*- coding: utf-8 -*-
from __future__ import annotations
"""
evento_meteo_assistente.py (com IA local via Ollama opcional)

Pipeline:
 - Lê SUBSET_FILE (TXT do GES DISC) e filtra SOMENTE os dias relevantes (mês/dia do evento ± janela) para 2020–2024
 - Baixa os .nc4 (GLDAS) usando earthaccess (EARTHDATA_USER/PASS no .env ou ~/.netrc)
 - Converte GLDAS 3h -> diário para o ponto (lat, lon)
 - Calcula climatologia (GLDAS). Se faltar dado, fallback ERA5 (Open-Meteo archive)
 - Previsão 7 dias: Google Weather (se GOOGLE_WEATHER_API_KEY) → fallback Open-Meteo (com umidade, visibilidade, sensação)
 - Gera recomendação determinística e, opcionalmente, recomendação contextual (IA local via Ollama)

Requisitos:
 pip install python-dotenv xarray netCDF4 pandas numpy requests earthaccess
 (IA local) Instalar Ollama e um modelo (ex.: `ollama pull phi3`)
"""
import unicodedata

import os, re, time, json, math, subprocess, shlex
from pathlib import Path
from typing import Sequence, Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs, unquote

import numpy as np
import pandas as pd
import xarray as xr
import requests
import earthaccess as ea

# ===================== .env / Config =====================
try:
    from dotenv import load_dotenv
except ImportError:
    raise SystemExit("Instale dependências:  pip install python-dotenv")

load_dotenv()

DATA_DIR        = Path(os.getenv("DATA_DIR", r"D:\NASA\programas\dados"))
SUBSET_FILE     = Path(os.getenv("SUBSET_FILE",  "") or "")
GLDAS_RAW_DIR   = DATA_DIR / os.getenv("GLDAS_RAW_SUBDIR", r"gldas\raw")
GLDAS_OUT_DIR   = DATA_DIR / os.getenv("GLDAS_OUT_SUBDIR",  r"gldas\out")
MAX_FILES       = int(os.getenv("MAX_FILES", "0"))   # 0 = baixa todos os links filtrados
TIMEZONE        = os.getenv("TIMEZONE", "America/Sao_Paulo")
GOOGLE_WEATHER_API_KEY = os.getenv("GOOGLE_WEATHER_API_KEY", "").strip()

# ---- IA via Ollama (opcional) ----
OLLAMA_ENABLE   = os.getenv("OLLAMA_ENABLE", "false").lower() in ("1","true","yes","y")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "phi3")
OLLAMA_HOST     = os.getenv("OLLAMA_HOST", "http://localhost:11434")  # se mudar a porta
EVENT_TYPE      = os.getenv("EVENT_TYPE", "").strip()                 # ex.: "passear com cachorro", "churrasco"
PERSON_NAME     = os.getenv("PERSON_NAME", "").strip()                # ex.: "Guilherme"
PET_NAME        = os.getenv("PET_NAME", "").strip()                   # ex.: "Thor"

for p in (DATA_DIR, GLDAS_RAW_DIR, GLDAS_OUT_DIR):
    p.mkdir(parents=True, exist_ok=True)

# ===================== Utils: subset TXT / download =====================
def autodiscover_subset_file(explicit: Path, root: Path) -> Path:
    if explicit and explicit.is_file():
        print(f"[OK] SUBSET_FILE (env/CLI): {explicit}")
        return explicit
    print(f"[AUTO] Procurando subset TXT em: {root}")
    patterns = ["subset_GLDAS*.txt", "*subset*GLDAS*.txt", "subset_*.txt"]
    cand: List[Path] = []
    for pat in patterns:
        cand += list(root.rglob(pat))
    if not cand:
        raise SystemExit("❌ subset TXT não encontrado. Ajuste SUBSET_FILE no .env.")
    cand.sort(key=lambda p: (p.stat().st_size, p.stat().st_mtime), reverse=True)
    print(f"[AUTO] Usando: {cand[0]}")
    return cand[0]

def fix_gldas_url(u: str) -> str:
    # normaliza variações de cgi
    u = re.sub(r"HTTP_s+er+v+ices\.cgi", "HTTP_services.cgi", u)
    u = u.replace("HTTP_service.cgi", "HTTP_services.cgi")
    return u

def prefer_data_host(u: str) -> str:
    # força host estável do GES DISC
    from urllib.parse import urlsplit, urlunsplit
    parts = urlsplit(u)
    if "HTTP_services.cgi" in parts.path and parts.netloc != "data.gesdisc.earthdata.nasa.gov":
        parts = parts._replace(netloc="data.gesdisc.earthdata.nasa.gov")
        return urlunsplit(parts)
    return u

def read_links_from_txt(path: Path) -> list[str]:
    patt = re.compile(r"https?://\S+?\.nc4(?:\?\S+)?", re.I)
    links: List[str] = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            links += patt.findall(line)
    # dedup + normalização
    seen, out = set(), []
    for u in links:
        u = prefer_data_host(fix_gldas_url(u))
        if u not in seen:
            seen.add(u)
            out.append(u)
    if not out:
        raise ValueError("Nenhum link .nc4 no subset TXT.")
    print(f"🔗 {len(out)} link(s) .nc4 encontrados. Ex.: {out[0]}")
    return out

# ---- parser de data a partir da URL/arquivo ----
def parse_y_doy_hhmm_from_url(url: str) -> Tuple[int,int,int,int]:
    """
    Retorna (ano, DOY, hora, minuto) a partir de uma URL GLDAS.
    Preferimos extrair AAAAMMDD.HHMM do nome do arquivo; se não, tentamos AAAA/DOY no path.
    """
    p = urlparse(url)
    fname = Path(p.path).name
    m = re.search(r"A(\d{4})(\d{2})(\d{2})\.(\d{2})(\d{2})", fname)
    if m:
        year = int(m.group(1)); month = int(m.group(2)); day = int(m.group(3))
        hour = int(m.group(4)); minute = int(m.group(5))
        dt = datetime(year, month, day, hour, minute)
        doy = int(dt.strftime("%j"))
        return year, doy, hour, minute
    # fallback: AAAA/DOY no path + HHMM no nome
    parts = p.path.split("/")
    year = next((int(x) for x in parts if x.isdigit() and len(x)==4), None)
    doy = None
    for x in parts:
        if x.isdigit() and len(x)==3:
            v = int(x)
            if 1 <= v <= 366:
                doy = v; break
    hhmm = re.search(r"\.(\d{4})\.", fname)
    hour = minute = 0
    if hhmm: hour, minute = int(hhmm.group(1)[:2]), int(hhmm.group(1)[2:])
    if year and doy:
        return year, doy, hour, minute
    raise ValueError(f"Não consegui extrair data/hora: {url}")

def dt_from_year_doy(year: int, doy: int) -> datetime:
    return datetime(year, 1, 1) + timedelta(days=doy - 1)

def filter_links_for_event_window(links: list[str], data_evento: str, janela:int=1,
                                  anos=(2020,2021,2022,2023,2024)) -> list[str]:
    """
    Filtra para manter SOMENTE os arquivos cujas datas (UTC) caem no mês/dia do evento ± janela, por ano.
    """
    target = pd.to_datetime(data_evento)
    md = (target.month, target.day)
    allow_dates = set()
    for y in anos:
        base = datetime(y, md[0], md[1])
        for d in range(-janela, janela+1):
            allow_dates.add((base + timedelta(days=d)).date())

    kept = []
    for u in links:
        try:
            y, doy, hh, mm = parse_y_doy_hhmm_from_url(u)
            dt = dt_from_year_doy(y, doy).date()
            if y in anos and dt in allow_dates:
                kept.append(u)
        except Exception:
            continue

    print(f"🎯 Filtro (±{janela}d, anos {anos}): {len(kept)} de {len(links)} links mantidos.")
    return kept

# ---- nome de arquivo amigável (sem '?') ----
def derive_dest_name(url: str, for_direct: bool = False) -> str:
    invalid = '<>:"/\\|?*'
    def sanitize(s: str) -> str:
        for ch in invalid:
            s = s.replace(ch, "_")
        return s

    p = urlparse(url)
    if for_direct:
        base = Path(unquote(p.path)).name
        return sanitize(base if base.lower().endswith(".nc4") else base + ".nc4")

    qs = parse_qs(p.query)
    label = (qs.get("LABEL") or qs.get("label") or [None])[0]
    if label:
        cand = unquote(label)
        return sanitize(cand if cand.lower().endswith(".nc4") else cand + ".nc4")

    fn = (qs.get("FILENAME") or qs.get("filename") or [None])[0]
    if fn:
        base = Path(unquote(fn)).name
        return sanitize(base if base.lower().endswith(".nc4") else base + ".nc4")

    last = Path(p.path).name
    return sanitize(last + ".nc4")

def download_gldas(links: list[str], out_dir: Path, max_files: int) -> int:
    # Auth via earthaccess (EARTHDATA_USER/PASS no .env ou ~/.netrc)
    ea.login(strategy="environment", persist=True)
    sess = ea.get_requests_https_session()
    out_dir.mkdir(parents=True, exist_ok=True)

    total = len(links) if max_files == 0 else min(max_files, len(links))
    count = 0
    for raw_url in links[:total]:
        url = prefer_data_host(fix_gldas_url(raw_url))
        dest_name = derive_dest_name(url)
        dest = out_dir / dest_name
        if dest.exists():
            print(f"✅ Já existe: {dest.name}")
            continue

        print(f"⬇️ Baixando (OTF): {dest.name}")
        try:
            r = sess.get(url, stream=True, allow_redirects=True, timeout=300)
            if r.status_code >= 400:
                r.close()
                qs = parse_qs(urlparse(url).query)
                fn = (qs.get("FILENAME") or qs.get("filename") or [None])[0]
                if not fn:
                    raise requests.HTTPError(f"OTF {r.status_code} e sem FILENAME para fallback.")
                direct = "https://data.gesdisc.earthdata.nasa.gov" + fn
                dest = out_dir / derive_dest_name(direct, for_direct=True)
                print(f"   ↪ OTF {r.status_code}. Tentando direto: {direct}")
                r = sess.get(direct, stream=True, allow_redirects=True, timeout=600)

            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_content(1024 * 1024):
                    if chunk:
                        f.write(chunk)
            print(f"✔ Concluído: {dest.name}")
            count += 1
        except Exception as e:
            print(f"⚠️ Falha em {dest_name}: {e}")
        finally:
            try: r.close()
            except: pass
        time.sleep(0.5)

    print(f"🛰️ Total baixado nesta execução: {count}")
    return count

# ===================== GLDAS 3h -> diário (ponto) =====================
def list_nc4(paths: Sequence[str|Path] | str | Path) -> list[str]:
    if isinstance(paths, (str, Path)):
        p = Path(paths)
        files = [str(pp) for pp in sorted(p.rglob("*.nc4"))] if p.is_dir() else ([str(p)] if p.exists() else [])
    else:
        files = [str(Path(x)) for x in paths if Path(x).exists()]
    return [f for f in files if f.lower().endswith(".nc4")]

def open_many(files: Sequence[str|Path]) -> xr.Dataset:
    files = list_nc4(files)
    if not files:
        raise FileNotFoundError("Nenhum .nc4 disponível.")
    print(f"🧩 Abrindo {len(files)} arquivo(s) GLDAS…")
    ds = xr.open_mfdataset(files, combine="by_coords", parallel=False)
    if "latitude" in ds: ds = ds.rename({"latitude":"lat"})
    if "longitude" in ds: ds = ds.rename({"longitude":"lon"})
    return ds

def subset_point(ds: xr.Dataset, lat: float, lon: float) -> xr.Dataset:
    if float(ds.lon.max()) > 180:
        lon = (lon + 360) % 360
    return ds.sel(lat=lat, lon=lon, method="nearest")

def process_gldas_to_daily(files, lat, lon) -> pd.DataFrame:
    K2C       = lambda x: x - 273.15
    MS2KMH    = lambda x: x * 3.6
    KGm2S2MMH = lambda x: x * 3600.0  # kg m-2 s-1 -> mm/h

    ds = open_many(files)
    ds = subset_point(ds, lat, lon).load()

    out = xr.Dataset()
    if "Tair_f_inst"  in ds: out["temp_c"]     = K2C(ds["Tair_f_inst"])
    if "Wind_f_inst"  in ds: out["wind_kmh"]   = MS2KMH(ds["Wind_f_inst"])
    if "Rainf_f_tavg" in ds: out["rain_mm"]    = KGm2S2MMH(ds["Rainf_f_tavg"]) * 3.0  # passo 3h

    daily = xr.Dataset({
        "temp_mean_c":    out["temp_c"].resample(time="1D").mean(),
        "temp_max_c":     out["temp_c"].resample(time="1D").max(),
        "temp_min_c":     out["temp_c"].resample(time="1D").min(),
        "wind_mean_kmh":  out["wind_kmh"].resample(time="1D").mean(),
        "rain_mm_day":    out["rain_mm"].resample(time="1D").sum(),
    })
    df = daily.to_dataframe().reset_index()
    df["date"] = pd.to_datetime(df["time"]).dt.date
    df = df.drop(columns=["time"])
    return df.set_index("date")

# ===================== Climatologia (GLDAS) + fallback ERA5 =====================
def climatologia(df_daily: pd.DataFrame, target_date: str,
                 anos=(2020,2021,2022,2023,2024), janela=1) -> Dict[str,Any]:
    tg = pd.to_datetime(target_date)
    rows = []
    for y in anos:
        base = tg.replace(year=y)
        for d in range(-janela, janela+1):
            day = (base + pd.Timedelta(days=d)).date()
            if day in df_daily.index:
                rows.append(df_daily.loc[[day]])
    if not rows:
        return {"ok": False, "msg": "Sem dados históricos nessa janela."}
    base = pd.concat(rows)

    def stats(col):
        s = base[col].dropna()
        return {"mean": float(s.mean()), "p25": float(s.quantile(0.25)),
                "p50": float(s.quantile(0.5)), "p75": float(s.quantile(0.75)),
                "min": float(s.min()), "max": float(s.max()), "n": int(s.shape[0])}

    out = {
        "ok": True,
        "amostra": int(base.shape[0]),
        "temp_mean_c":   stats("temp_mean_c"),
        "temp_min_c":    stats("temp_min_c"),
        "temp_max_c":    stats("temp_max_c"),
        "wind_mean_kmh": stats("wind_mean_kmh"),
        "rain_mm_day":   stats("rain_mm_day"),
    }
    pm = out["rain_mm_day"]["mean"]
    tm = out["temp_mean_c"]["mean"]
    chuva_txt = "tende a ser seco" if pm < 1 else ("há chance de chuva" if pm < 20 else "chuva forte é comum")
    temp_txt  = "bem quente" if tm >= 30 else ("quente" if tm >= 25 else ("frio" if tm <= 15 else "ameno"))
    out["resumo"] = f"Histórico (2020–2024 ±{janela}d): {chuva_txt}; média {tm:.1f}°C ({temp_txt})."
    return out

def hist_fallback_era5_openmeteo(lat: float, lon: float, data_evento: str, janela:int=1,
                                 anos=(2020,2021,2022,2023,2024)) -> Dict[str,Any]:
    """Climatologia diária via ERA5 (Open-Meteo archive) quando GLDAS não cobrir a janela."""
    base_url = "https://archive-api.open-meteo.com/v1/era5"
    rows = []
    for y in anos:
        target = pd.to_datetime(data_evento).replace(year=y)
        start = (target - pd.Timedelta(days=janela)).date().isoformat()
        end   = (target + pd.Timedelta(days=janela)).date().isoformat()
        params = dict(
            latitude=lat, longitude=lon, timezone="UTC",
            start_date=start, end_date=end,
            daily="temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max"
        )
        try:
            r = requests.get(base_url, params=params, timeout=30)
            r.raise_for_status()
            d = r.json().get("daily", {})
            if not d:
                continue
            df = pd.DataFrame(d)
            df["date"] = pd.to_datetime(df["time"]).dt.date
            df = df.drop(columns=["time"])
            rows.append(df)
        except Exception:
            continue

    if not rows:
        return {"ok": False, "msg": "ERA5 (fallback) não retornou dados."}

    base = pd.concat(rows, ignore_index=True)
    def stats(s):
        s = pd.to_numeric(s, errors="coerce").dropna()
        return {"mean": float(s.mean()), "p25": float(s.quantile(0.25)), "p50": float(s.quantile(0.5)),
                "p75": float(s.quantile(0.75)), "min": float(s.min()), "max": float(s.max()), "n": int(s.shape[0])}
    out = {
        "ok": True,
        "fonte": "ERA5 (Open-Meteo archive)",
        "amostra": int(base.shape[0]),
        "temp_mean_c": stats((pd.to_numeric(base["temperature_2m_max"])+pd.to_numeric(base["temperature_2m_min"])) / 2.0),
        "temp_min_c":  stats(base["temperature_2m_min"]),
        "temp_max_c":  stats(base["temperature_2m_max"]),
        "rain_mm_day": stats(base["precipitation_sum"]),
        "wind_mean_kmh": stats(base["wind_speed_10m_max"]),  # aproximação
    }
    pm = out["rain_mm_day"]["mean"]; tm = out["temp_mean_c"]["mean"]
    chuva_txt = "tende a ser seco" if pm < 1 else ("há chance de chuva" if pm < 20 else "chuva forte é comum")
    temp_txt  = "bem quente" if tm >= 30 else ("quente" if tm >= 25 else ("frio" if tm <= 15 else "ameno"))
    out["resumo"] = f"Histórico (ERA5, 2020–2024 ±{janela}d): {chuva_txt}; média {tm:.1f}°C ({temp_txt})."
    return out

# ===================== Previsão 7 dias (Google/Open-Meteo) =====================
def forecast_google(lat: float, lon: float, days:int=7, timezone="auto") -> Dict[str,Any]:
    key = GOOGLE_WEATHER_API_KEY
    if not key:
        return {"ok": False, "msg": "GOOGLE_WEATHER_API_KEY ausente; usando Open-Meteo."}

    endpoint = "https://weather.googleapis.com/v1/weather:forecast"
    params = {
        "location": f"{lat},{lon}",
        "timesteps": "daily",
        "units": "metric",
        "languageCode": "pt-BR",
        "dailyFieldMask": ",".join([
            "temperatureMax","temperatureMin","humidityAvg","visibilityAvg",
            "precipitationAmount","windSpeedMax","apparentTemperatureMax"
        ]),
        "key": key,
    }
    try:
        r = requests.get(endpoint, params=params, timeout=20)
        if r.status_code == 403:
            return {"ok": False, "msg": "Google Weather não habilitado (403). Fallback Open-Meteo."}
        r.raise_for_status()
        data = r.json()
        daily = []
        for d in (data.get("dailyForecasts", []) or data.get("daily", [])):
            daily.append({
                "date": d.get("date") or d.get("time"),
                "tmax": d.get("temperatureMax"),
                "tmin": d.get("temperatureMin"),
                "humidity_mean": d.get("humidityAvg"),
                "visibility_km": d.get("visibilityAvg"),
                "precip_mm": d.get("precipitationAmount"),
                "wind_max": d.get("windSpeedMax"),
                "apparent_max": d.get("apparentTemperatureMax"),
                "provider": "google",
            })
        if not daily:
            return {"ok": False, "msg": "Google Weather sem 'daily'. Fallback Open-Meteo."}
        return {"ok": True, "daily": daily, "provider": "google"}
    except Exception as e:
        return {"ok": False, "msg": f"Google Weather falhou: {e}. Fallback Open-Meteo."}

def forecast_openmeteo(lat: float, lon: float, days:int=7, timezone="auto") -> Dict[str,Any]:
    url = "https://api.open-meteo.com/v1/forecast"
    params = dict(
        latitude=lat, longitude=lon, timezone=timezone, forecast_days=days,
        daily="temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_mean,wind_speed_10m_max,apparent_temperature_max",
        hourly="relative_humidity_2m,visibility,apparent_temperature,temperature_2m,wind_speed_10m,precipitation"
    )
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    jd = r.json()
    d_d = jd.get("daily", {}); d_h = jd.get("hourly", {})
    if not d_d:
        return {"ok": False, "msg": "Sem dados diários do Open-Meteo."}

    df_d = pd.DataFrame({
        "date": pd.to_datetime(d_d["time"]).date,
        "tmax": d_d.get("temperature_2m_max"),
        "tmin": d_d.get("temperature_2m_min"),
        "precip_mm": d_d.get("precipitation_sum"),
        "precip_prob": d_d.get("precipitation_probability_mean"),
        "wind_max": d_d.get("wind_speed_10m_max"),
        "apparent_max": d_d.get("apparent_temperature_max"),
    }).set_index("date")

    if d_h:
        df_h = pd.DataFrame(d_h)
        df_h["time"] = pd.to_datetime(df_h["time"])
        df_h["date"] = df_h["time"].dt.date
        hum = df_h.groupby("date")["relative_humidity_2m"].mean().rename("humidity_mean")
        vis = (df_h.groupby("date")["visibility"].mean() / 1000.0).rename("visibility_km")
        df_d = df_d.join(hum, how="left").join(vis, how="left")

    daily = df_d.reset_index().to_dict("records")
    for r_ in daily: r_["provider"] = "open-meteo"
    return {"ok": True, "daily": daily, "provider": "open-meteo"}

def previsao_7_dias(lat: float, lon: float, days=7, timezone="auto") -> Dict[str,Any]:
    g = forecast_google(lat, lon, days=days, timezone=timezone)
    if g.get("ok"): return g
    return forecast_openmeteo(lat, lon, days=days, timezone=timezone)

# ===================== Recomendação p/ evento (determinística) =====================
def gerar_recomendacao_texto(hist: Dict[str,Any], prev: Optional[Dict[str,Any]], data_evento: str) -> str:
    linhas = []
    if hist.get("ok"):
        linhas.append(hist["resumo"])
        pm = (hist.get("rain_mm_day") or {}).get("mean", 0.0)
        if pm >= 10:
            linhas.append("⚠️ Em anos anteriores, acumulados diários elevados não são raros neste período.")

    if prev and prev.get("ok"):
        try:
            de = pd.to_datetime(data_evento).date()
            item = next((d for d in prev["daily"] if pd.to_datetime(d["date"]).date() == de), None)
        except Exception:
            item = None
        if item:
            tmax = item.get("tmax"); tmin = item.get("tmin")
            pp   = item.get("precip_prob"); pr = item.get("precip_mm")
            hum  = item.get("humidity_mean"); vis = item.get("visibility_km")
            wmax = item.get("wind_max"); app = item.get("apparent_max")
            prov = item.get("provider", "open-meteo")
            linhas.append(
                f"Previsão ({prov}) para o dia: "
                f"{tmin is not None and round(tmin)}–{tmax is not None and round(tmax)}°C, "
                f"chuva {pr if pr is not None else 0:.1f} mm (prob {pp or 0}%), "
                f"umidade {hum is not None and round(hum)}%, "
                f"vis {vis is not None and round(vis,1)} km, "
                f"vento máx {wmax} km/h, sensação máx {app}°C."
            )
            alertas = []
            if (pp or 0) >= 60 or (pr or 0) >= 10: alertas.append("chuva moderada/forte")
            if (app or (tmax or 0)) >= 35:         alertas.append("calor extremo")
            if (wmax or 0) >= 40:                  alertas.append("vento forte")
            if (vis or 99) <= 5:                   alertas.append("baixa visibilidade")
            if alertas:
                linhas.append("⚠️ Sinais para o dia do evento: " + ", ".join(alertas) + ".")
        else:
            linhas.append("ℹ️ A data do evento está fora do horizonte de 7 dias ou não há ponto diário correspondente.")

    if not linhas:
        linhas.append("Sem dados suficientes para recomendação.")

    return " ".join(str(x) for x in linhas if x)

# ===================== IA local via Ollama (opcional) =====================
def _ollama_run(model: str, prompt: str, host: str = OLLAMA_HOST, timeout: int = 30) -> str:
    """
    Chama o Ollama via CLI (`ollama run <model> "<prompt>"`).
    Requer Ollama instalado e modelo baixado (`ollama pull phi3` / `mistral` / `llama3` etc.).
    """
    cmd = f'ollama run {shlex.quote(model)} {shlex.quote(prompt)}'
    try:
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout, env={**os.environ, "OLLAMA_HOST": host})
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or "Falha desconhecida no Ollama.")
        return proc.stdout.strip()
    except Exception as e:
        return f"[Ollama erro] {e}"

def _pick_prev_for_date(prev: Optional[Dict[str,Any]], data_evento: str) -> Optional[Dict[str,Any]]:
    if not prev or not prev.get("ok"): return None
    try:
        de = pd.to_datetime(data_evento).date()
        return next((d for d in prev["daily"] if pd.to_datetime(d["date"]).date() == de), None)
    except Exception:
        return None

def gerar_recomendacao_contextual_ollama(hist: Dict[str,Any],
                                         prev: Optional[Dict[str,Any]],
                                         data_evento: str,
                                         evento_tipo: str = "",
                                         person_name: str = "",
                                         pet_name: str = "",
                                         model: str = OLLAMA_MODEL) -> str:
    """
    Gera um texto curto e amigável levando em conta:
    - histórico (GLDAS/ERA5)
    - previsão (para a data se existir dentro dos 7 dias)
    - tipo de evento ("churrasco", "passear com cachorro", "corrida", etc.)
    - nomes (opcionais) para personalizar (pessoa/pet)
    """
    hist_resumo = hist.get("resumo", "")
    fonte = hist.get("fonte", "GLDAS/Earthdata" if hist.get("ok") else "desconhecida")
    item_prev = _pick_prev_for_date(prev, data_evento) or {}

    # Monta um contexto bem compacto (evitar prompt longo)
    contexto = {
        "data_evento": str(pd.to_datetime(data_evento).date()),
        "evento_tipo": evento_tipo or "evento",
        "person_name": person_name or "",
        "pet_name": pet_name or "",
        "historico": {
            "fonte": fonte,
            "resumo": hist_resumo
        },
        "previsao_dia": {
            "tmin": item_prev.get("tmin"),
            "tmax": item_prev.get("tmax"),
            "chuva_mm": item_prev.get("precip_mm"),
            "prob_chuva": item_prev.get("precip_prob"),
            "umidade": item_prev.get("humidity_mean"),
            "vis_km": item_prev.get("visibility_km"),
            "sensacao_max": item_prev.get("apparent_max"),
            "vento_max": item_prev.get("wind_max"),
            "provider": item_prev.get("provider")
        }
    }

    instrucoes = (
        "Você é um assistente conciso. Dado o contexto climático e o tipo de evento, "
        "produza UMA recomendação curta (1–2 frases), amigável e prática em PT-BR. "
        "Se houver chance de chuva, sugira plano B ou equipamento. "
        "Se calor, fale de hidratação/horário. "
        "Se vento forte ou baixa visibilidade, mencione cautela. "
        "Se pet_name existir e o evento envolver passeio, personalize com o nome do pet. "
        "Não repita números demais; foque no conselho."
    )

    prompt = f"INSTRUÇÕES:\n{instrucoes}\n\nCONTEXTO(JSON):\n{json.dumps(contexto, ensure_ascii=False)}\n\nRESPOSTA:"
    return _ollama_run(model, prompt)

def _strip_accents(s: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

# dicionário simples de keywords -> tipo de evento
_EVENT_MAP = [
    # (lista de palavras a detectar, rótulo do tipo)
    (["churrasco", "bbq"], "churrasco"),
    (["piquenique", "picnic"], "piquenique"),
    (["corrida", "correr", "race", "maratona", "5k", "10k"], "corrida"),
    (["trilha", "hiking", "caminhada"], "trilha"),
    (["praia", "beach"], "praia"),
    (["futebol", "pelada", "soccer"], "futebol"),
    (["show", "concerto", "festival"], "show"),
    (["voo", "aeroporto", "embarque", "aviao", "avião", "flight"], "viagem"),
    (["viagem", "travel", "roadtrip"], "viagem"),
    (["casamento", "wedding"], "casamento"),
    (["aniversario", "aniversário", "birthday"], "aniversario"),
    (["passeio", "passear"], "passeio"),
    (["cachorro", "dog", "pet"], "passear com cachorro"),
    (["bike", "bicicleta", "ciclismo", "pedal"], "ciclismo"),
    (["moto", "motocicleta"], "passeio de moto"),
    (["churras"], "churrasco"),
]

# heurística simples pra extrair nome do pet
def _guess_pet_name(title_norm: str, original: str) -> Optional[str]:
    # 1) Nome entre aspas: Passeio com "Thor"
    m = re.search(r'["“”\'’]([^"“”\'’]{2,20})["“”\'’]', original)
    if m:
        return m.group(1).strip()

    # 2) depois de "com " alguma palavra com inicial maiúscula no original
    m2 = re.search(r'\bcom\s+([A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÁÉÍÓÚÂÊÔÃÕÇ-]{1,20})\b', original)
    if m2:
        return m2.group(1).strip()

    # 3) no normalizado, depois de "com " pega a próxima palavra
    m3 = re.search(r'\bcom\s+([a-z0-9\-]{2,20})\b', title_norm)
    if m3:
        cand = m3.group(1)
        # evitar palavras genéricas
        if cand not in ("amigos", "familia", "familiares", "galera", "time"):
            return cand.capitalize()
    return None

def infer_context_from_title(title: str) -> Dict[str, Optional[str]]:
    """
    Retorna: {"event_type": str, "person_name": Optional[str], "pet_name": Optional[str]}
    """
    if not title:
        return {"event_type": None, "person_name": None, "pet_name": None}

    original = title.strip()
    title_norm = _strip_accents(original).lower()

    # detectar tipo
    found_type = None
    for keys, label in _EVENT_MAP:
        for k in keys:
            if f" {k} " in f" {title_norm} ":
                found_type = label
                break
        if found_type:
            break

    # regras extras para diferenciar "passear com cachorro"
    if not found_type and ("passeio" in title_norm or "passear" in title_norm):
        found_type = "passeio"

    if ("cachorro" in title_norm or " dog " in f" {title_norm} " or " pet " in f" {title_norm} ") and "passeio" in title_norm:
        found_type = "passear com cachorro"

    # nome do pet (heurística)
    pet_name = None
    if found_type in ("passear com cachorro",):
        pet_name = _guess_pet_name(title_norm, original)

    return {"event_type": found_type or "evento", "person_name": None, "pet_name": pet_name}

# ===================== Orquestração =====================
def avaliar_evento(lat: float, lon: float, data_evento: str,
                   subset_txt: Path = SUBSET_FILE,
                   gldas_raw_dir: Path = GLDAS_RAW_DIR,
                   max_files:int = MAX_FILES,
                   janela_hist:int = 1,
                   anos_hist= (2020,2021,2022,2023,2024),
                   timezone:str = TIMEZONE,
                   event_title: Optional[str] = None) -> Dict[str,Any]:
    # 1) localizar subset TXT
    txt = autodiscover_subset_file(subset_txt, DATA_DIR)

    # 2) ler todos os links e filtrar pela janela (mês/dia do evento ± janela, para os anos desejados)
    links_all = read_links_from_txt(txt)
    links = filter_links_for_event_window(links_all, data_evento,
                                          janela=janela_hist, anos=anos_hist)

    # 3) baixar os arquivos necessários (se MAX_FILES=0, baixa todos os filtrados)
    #    Obs: se já estiverem no disco, ele pula
    limite = len(links) if max_files == 0 else min(max_files, len(links))
    download_gldas(links, gldas_raw_dir, max_files=limite)

    # 4) Processar GLDAS -> diário para o ponto
    files = list_nc4(gldas_raw_dir)
    hist: Dict[str, Any] = {"ok": False, "msg": "Sem dados GLDAS para a janela."}
    fonte_hist = None
    if files:
        try:
            df_daily = process_gldas_to_daily(files, lat, lon)
            hist = climatologia(df_daily, data_evento,
                                anos=anos_hist, janela=janela_hist)
            if hist.get("ok"):
                fonte_hist = "GLDAS/Earthdata"
                hist["fonte"] = fonte_hist
        except Exception as e:
            hist = {"ok": False, "msg": f"Falha ao processar GLDAS: {e}"}

    # 5) Fallback histórico (ERA5) se GLDAS não cobriu
    if not hist.get("ok"):
        print("… GLDAS insuficiente → usando fallback ERA5.")
        hist = hist_fallback_era5_openmeteo(lat, lon, data_evento,
                                            janela=janela_hist, anos=anos_hist)
        fonte_hist = hist.get("fonte")

    # 6) Previsão 7 dias (Google Weather se chave, senão Open-Meteo)
    prev = previsao_7_dias(lat, lon, days=7, timezone=timezone)

    # 7) Recomendação determinística (sempre)
    texto = gerar_recomendacao_texto(hist, prev, data_evento)

    # 8) Recomendação contextual (IA local via Ollama – opcional)
    inferidos = {"event_type": None, "person_name": None, "pet_name": None}
    texto_ai = None
    if OLLAMA_ENABLE:
        inferidos = infer_context_from_title(event_title or "")
        evt_type  = inferidos.get("event_type")  or EVENT_TYPE
        person    = inferidos.get("person_name") or PERSON_NAME
        pet       = inferidos.get("pet_name")    or PET_NAME

        texto_ai = gerar_recomendacao_contextual_ollama(
            hist, prev, data_evento,
            evento_tipo=evt_type,
            person_name=person,
            pet_name=pet,
            model=OLLAMA_MODEL
        )

    return {
        "ok": True,
        "coords": {"lat": lat, "lon": lon},
        "data_evento": data_evento,
        "painel_7dias": prev,
        "analise_evento": {
            "historico": hist,
            "fonte_historico": fonte_hist or hist.get("fonte", "desconhecida"),
            "usou_earthdata": (fonte_hist == "GLDAS/Earthdata"),
            "recomendacao": texto,
            "recomendacao_contextual": texto_ai,
            "contexto_detectado": inferidos if OLLAMA_ENABLE else None
        }
    }

# ===================== Main (exemplo CLI) =====================
if __name__ == "__main__":
    LAT = float(os.getenv("LAT", "-23.62"))
    LON = float(os.getenv("LON", "-46.55"))
    DATA_EVENTO = os.getenv("TARGET_DATE", "2025-10-07")
    EVENT_TITLE = os.getenv("EVENT_TITLE", "")  # novo: título do evento

    res = avaliar_evento(LAT, LON, DATA_EVENTO, event_title=EVENT_TITLE)
    print("\n==== RESULTADO ====")
    print(json.dumps(res, ensure_ascii=False, indent=2, default=str))

