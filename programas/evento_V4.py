# -*- coding: utf-8 -*-
from __future__ import annotations
"""
evento_meteo_assistente.py (GLDAS/ERA5 + Previsão + IA local via Ollama opcional)

Pipeline:
 - Lê SUBSET_FILE (TXT do GES DISC) e filtra SOMENTE os dias relevantes (mês/dia do evento ± janela) para 2020–2024
 - Baixa os .nc4 (GLDAS) usando earthaccess (EARTHDATA_USER/PASS no .env ou ~/.netrc)
 - Converte GLDAS 3h -> diário para o ponto (lat, lon) com variáveis essenciais + secundárias
 - Calcula climatologia (GLDAS). Se faltar dado, fallback ERA5 (Open-Meteo archive)
 - Previsão 7 dias: Google Weather (se GOOGLE_WEATHER_API_KEY) → fallback Open-Meteo (com umidade, visibilidade, sensação)
 - Gera recomendação determinística e, opcionalmente, recomendação contextual (IA local via Ollama)
 - Entrega payload completo OU JSONs “amigáveis” para o front (card, blocos, etc.)

Requisitos:
 pip install python-dotenv xarray netCDF4 pandas numpy requests earthaccess
 (opcional) pip install metpy
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

import sys
try:
    # evita erros de decodificação no Windows (cp1252)
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

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
OLLAMA_HOST     = os.getenv("OLLAMA_HOST", "http://localhost:11434")
EVENT_TYPE      = os.getenv("EVENT_TYPE", "").strip()
PERSON_NAME     = os.getenv("PERSON_NAME", "").strip()
PET_NAME        = os.getenv("PET_NAME", "").strip()

# ---- Saídas / Flags globais (também lidas no __main__) ----
COMPACT_JSON     = os.getenv("COMPACT_JSON", "false").lower() in ("1","true","yes","y")  # só {"ok":..,"motivo":..}
FRONT_MIN        = os.getenv("FRONT_MIN", "false").lower() in ("1","true","yes","y")     # card único
FRONT_BLOCKS     = os.getenv("FRONT_BLOCKS", "false").lower() in ("1","true","yes","y")  # {card, dias7, meta}
FRIENDLY_OUTPUT  = os.getenv("FRIENDLY_OUTPUT", "false").lower() in ("1","true","yes","y")
FRIENDLY_STYLE   = os.getenv("FRIENDLY_STYLE", "amigavel").strip().lower()               # amigavel | curto | formal
MENTION_PET      = os.getenv("MENTION_PET", "false").lower() in ("1","true","yes","y")
PET_FROM_TITLE   = os.getenv("PET_FROM_TITLE", "false").lower() in ("1","true","yes","y")
FREE_EVENT_MODE  = os.getenv("FREE_EVENT_MODE", "false").lower() in ("1","true","yes","y")  # aceitar QUALQUER título como tipo de evento
REC_VERBOSE      = os.getenv("REC_VERBOSE", "true").lower() in ("1","true","yes","y")

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
    u = re.sub(r"HTTP_s+er+v+ices\.cgi", "HTTP_services.cgi", u)
    u = u.replace("HTTP_service.cgi", "HTTP_services.cgi")
    return u

def prefer_data_host(u: str) -> str:
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
def parse_y_doy_hhmm_from_url(url: str) -> tuple[int,int,int,int]:
    p = urlparse(url)
    fname = Path(p.path).name

    def _try(fname_str: str):
        m = re.search(r"A(\d{4})(\d{2})(\d{2})\.(\d{2})(\d{2})", fname_str)
        if not m:
            return None
        y, mo, da, hh, mm = map(int, m.groups())
        dt = datetime(y, mo, da, hh, mm)
        return y, int(dt.strftime("%j")), hh, mm

    out = _try(fname)
    if out: return out

    qs = parse_qs(p.query)
    for key in ("LABEL", "label", "FILENAME", "filename"):
        vals = qs.get(key)
        if not vals: continue
        cand = unquote(vals[0])
        cand_name = Path(cand).name
        out = _try(cand_name)
        if out: return out

    raise ValueError(f"Não consegui extrair data/hora: {url}")

def dt_from_year_doy(year: int, doy: int) -> datetime:
    return datetime(year, 1, 1) + timedelta(days=doy - 1)

def filter_links_for_event_window(links: list[str], data_evento: str, janela:int=1,
                                  anos=(2020,2021,2022,2023,2024)) -> list[str]:
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
    # Auth via earthaccess (EARTHDATA_* no .env ou ~/.netrc)
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

# ---- UX helpers ----
def _r0(x):
    try:
        return None if x is None else int(round(float(x)))
    except Exception:
        return None

def _r1(x):
    try:
        return None if x is None else round(float(x), 1)
    except Exception:
        return None

def classifica_solar_wm2(wm2: float|None) -> str:
    if wm2 is None: return "—"
    if wm2 < 150: return "Nublado"
    if wm2 < 350: return "Parcialmente nublado"
    return "Ensolarado"

def escolhe_icone(rain_mm_day: float|None, solar_mean_wm2: float|None) -> str:
    r = (rain_mm_day or 0)
    if r >= 8: return "⛈️"
    if r >= 0.5: return "🌧️"
    if solar_mean_wm2 is not None:
        if solar_mean_wm2 < 150: return "☁️"
        if solar_mean_wm2 < 350: return "🌤️"
        return "☀️"
    return "🌤️"

def _condicao_icone(chuva_mm: float | None, solar_wm2: float | None = None, vis_km: float | None = None, prob_chuva: float | None = None):
    # Normaliza numéricos
    def _f(v):
        try: return None if v is None else float(v)
        except: return None
    chuva_mm  = _f(chuva_mm)
    solar_wm2 = _f(solar_wm2)
    vis_km    = _f(vis_km)
    prob_chuva = _f(prob_chuva)

    # Regras simples: prioriza chuva
    if chuva_mm is not None:
        if chuva_mm >= 8:   return "Chuva forte", "⛈️"
        if chuva_mm >= 4:   return "Chuva moderada", "🌧️"
        if chuva_mm >= 0.5: return "Chuva fraca", "🌦️"
        # sem chuva significativa -> avalia "céu"
        if solar_wm2 is not None:
            return ("Nublado", "☁️") if solar_wm2 < 150 else ("Ensolarado", "☀️")
        if vis_km is not None and vis_km <= 5:
            return "Neblina", "🌫️"
        return "Parcialmente nublado", "🌤️"

    # sem dado de chuva -> usa outros sinais
    if vis_km is not None and vis_km <= 5:
        return "Neblina", "🌫️"
    if solar_wm2 is not None:
        return ("Nublado", "☁️") if solar_wm2 < 150 else ("Ensolarado", "☀️")
    if prob_chuva is not None and prob_chuva >= 50:
        return "Possível chuva", "🌦️"
    return "Indefinido", "⛅"

def _indice_atividade(temp_c: float | None, chuva_mm: float | None, vento_kmh: float | None, umid_pct: float | None):
    # Escore 0–10: começa em 10 e vai penalizando
    score = 10

    # Temperatura (zona de conforto ~18–26°C)
    if temp_c is not None:
        t = float(temp_c)
        if t < 10: score -= 3
        elif t < 18: score -= 1
        elif t > 35: score -= 4
        elif t > 32: score -= 3
        elif t > 26: score -= 1

    # Chuva
    if chuva_mm is not None:
        r = float(chuva_mm)
        if r >= 8: score -= 4
        elif r >= 4: score -= 3
        elif r >= 0.5: score -= 1

    # Vento
    if vento_kmh is not None:
        v = float(vento_kmh)
        if v > 40: score -= 3
        elif v > 28: score -= 2
        elif v > 12: score -= 1

    # Umidade alta piora um pouco o conforto
    if umid_pct is not None:
        try:
            if float(umid_pct) >= 85:
                score -= 1
        except:
            pass

    # Limites
    if score < 0: score = 0
    if score > 10: score = 10
    return int(score)

def process_gldas_to_daily(files, lat, lon) -> pd.DataFrame:
    K2C       = lambda x: x - 273.15
    MS2KMH    = lambda x: x * 3.6
    KGm2S2MMH = lambda x: x * 3600.0  # kg m-2 s-1 -> mm/h
    Pa2hPa    = lambda x: x / 100.0

    ds = open_many(files)
    ds = subset_point(ds, lat, lon).load()

    out = xr.Dataset()
    if "Tair_f_inst"  in ds: out["temp_c"]       = K2C(ds["Tair_f_inst"])
    if "Wind_f_inst"  in ds: out["wind_kmh"]     = MS2KMH(ds["Wind_f_inst"])
    if "Rainf_f_tavg" in ds: out["rain_mm"]      = KGm2S2MMH(ds["Rainf_f_tavg"]) * 3.0  # passo 3h → mm por passo
    if "Psurf_f_inst" in ds: out["press_hpa"]    = Pa2hPa(ds["Psurf_f_inst"])
    if "SWdown_f_tavg" in ds: out["solar_wm2"]   = ds["SWdown_f_tavg"]  # já média no passo
    # Umidade relativa a partir de Qair + T + P (se MetPy disponível)
    if all(v in ds for v in ["Qair_f_inst", "Tair_f_inst", "Psurf_f_inst"]):
        try:
            import metpy.calc as mpcalc
            from metpy.units import units
            q = (ds["Qair_f_inst"].values * units("kg/kg"))
            t = (ds["Tair_f_inst"].values * units.kelvin)
            p = (ds["Psurf_f_inst"].values * units.pascal)
            rh = mpcalc.relative_humidity_from_specific_humidity(q, t, p).m  # frac
            out["rh_pct"] = (xr.DataArray(rh, dims=ds["Tair_f_inst"].dims) * 100.0).clip(0, 100)
        except Exception:
            pass

    # Agregado diário
    daily = xr.Dataset()
    if "temp_c" in out:
        daily["temp_mean_c"] = out["temp_c"].resample(time="1D").mean()
        daily["temp_max_c"]  = out["temp_c"].resample(time="1D").max()
        daily["temp_min_c"]  = out["temp_c"].resample(time="1D").min()
    if "wind_kmh" in out:
        daily["wind_mean_kmh"] = out["wind_kmh"].resample(time="1D").mean()
    if "rain_mm" in out:
        daily["rain_mm_day"] = out["rain_mm"].resample(time="1D").sum()
    if "press_hpa" in out:
        daily["pressure_mean_hpa"] = out["press_hpa"].resample(time="1D").mean()
    if "solar_wm2" in out:
        daily["solar_mean_wm2"] = out["solar_wm2"].resample(time="1D").mean()
    if "rh_pct" in out:
        daily["rh_mean_pct"] = out["rh_pct"].resample(time="1D").mean()

    if not daily.variables:
        raise ValueError("Dataset GLDAS sem variáveis esperadas.")

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
        if col not in base: return None
        s = pd.to_numeric(base[col], errors="coerce").dropna()
        if s.empty: return None
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
        "rh_mean_pct":   stats("rh_mean_pct"),
        "pressure_mean_hpa": stats("pressure_mean_hpa"),
        "solar_mean_wm2":    stats("solar_mean_wm2"),
    }
    pm = (out.get("rain_mm_day") or {}).get("mean", 0.0)
    tm = (out.get("temp_mean_c") or {}).get("mean", float("nan"))
    chuva_txt = "tende a ser seco" if pm < 1 else ("há chance de chuva" if pm < 20 else "chuva forte é comum")
    if not np.isnan(tm):
        temp_txt  = "bem quente" if tm >= 30 else ("quente" if tm >= 25 else ("frio" if tm <= 15 else "ameno"))
        out["resumo"] = f"Histórico (2020–2024 ±{janela}d): {chuva_txt}; média {tm:.1f}°C ({temp_txt})."
    else:
        out["resumo"] = f"Histórico (2020–2024 ±{janela}d): {chuva_txt}."
    return out

def hist_fallback_era5_openmeteo(lat: float, lon: float, data_evento: str, janela:int=1,
                                 anos=(2020,2021,2022,2023,2024)) -> Dict[str,Any]:
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
        "wind_mean_kmh": stats(base["wind_speed_10m_max"]),
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

# ===================== IA local via Ollama (opcional) =====================
def _ollama_run(model: str, prompt: str, host: str = OLLAMA_HOST, timeout: int = 30) -> str:
    """
    Chama o Ollama via CLI, decodificando a saída como UTF-8 (seguro no Windows).
    """
    cmd = f'ollama run {shlex.quote(model)} {shlex.quote(prompt)}'
    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=False,  # lê bytes
            timeout=timeout,
            env={**os.environ, "OLLAMA_HOST": host},
        )
        stdout = (proc.stdout or b"").decode("utf-8", errors="replace")
        stderr = (proc.stderr or b"").decode("utf-8", errors="replace")
        if proc.returncode != 0:
            raise RuntimeError(stderr.strip() or "Falha desconhecida no Ollama.")
        return stdout.strip()
    except Exception as e:
        return f"[Ollama erro] {e}"

def _pega_prev_no_dia(prev: Optional[Dict[str,Any]], data_evento: str) -> Optional[Dict[str,Any]]:
    if not prev or not prev.get("ok"): return None
    try:
        de = pd.to_datetime(data_evento).date()
        return next((d for d in prev["daily"] if pd.to_datetime(d["date"]).date() == de), None)
    except Exception:
        return None

def _mensagem_deterministica(hist: dict, prev: dict | None, data_evento: str,
                             evento_tipo: str, person_name: str, pet_name: str) -> str:
    """Mensagem amigável (sem IA), usando previsão do dia se houver; senão, histórico."""
    try:
        data_pt = pd.to_datetime(data_evento).strftime("%d/%m/%Y")
    except Exception:
        data_pt = str(data_evento)

    sujeito = person_name or "Você"
    alvo = evento_tipo or "seu evento"

    intro = f"{sujeito} vai {alvo}" + (f" com {pet_name}" if (MENTION_PET and pet_name) else "") + f" em {data_pt}? "

    item = _pega_prev_no_dia(prev, data_evento)
    partes = [intro]

    if item:
        tmin = item.get("tmin"); tmax = item.get("tmax")
        try:
            tspan = f"{int(round(tmin))}–{int(round(tmax))}°C" if tmin is not None and tmax is not None else None
        except Exception:
            tspan = None

        pp = item.get("precip_prob") or 0
        pr = item.get("precip_mm") or 0
        riscos = []
        if pr >= 10 or pp >= 60: riscos.append("chuva")
        if (item.get("apparent_max") or item.get("tmax") or 0) >= 35: riscos.append("calor")
        if (item.get("wind_max") or 0) >= 40: riscos.append("vento")
        if (item.get("visibility_km") or 99) <= 5: riscos.append("baixa visibilidade")

        base = f"Previsão aponta {tspan}." if tspan else "Previsão consultada."
        if riscos:
            partes.append(f"{base} Atenção com " + ", ".join(riscos) + ". ")
        else:
            partes.append(f"{base} Sem sinais relevantes. ")
    else:
        tm = (hist.get("temp_mean_c") or {}).get("mean")
        pm = (hist.get("rain_mm_day") or {}).get("mean")
        if tm is not None and pm is not None:
            partes.append(f"Historicamente, média de {tm:.1f}°C e {pm:.1f} mm/dia neste período. ")

    det = decide_passeio_curto(hist, prev, data_evento, evento_tipo)
    partes.append("Parece uma boa! 👍" if det.get("ok") else "Considere plano B.")
    return "".join(partes).strip()

def gerar_recomendacao_contextual_ollama(
    hist: Dict[str,Any],
    prev: Optional[Dict[str,Any]],
    data_evento: str,
    evento_tipo: str = "",
    person_name: str = "",
    pet_name: str = "",
    model: str = OLLAMA_MODEL,
) -> Dict[str, Any]:
    """
    Retorna SEMPRE um dict JSON curto:
      {"ok": true|false, "motivo": "até 8 palavras", "mensagem": "texto (<=220 chars)"}
    Se o Ollama falhar, cai no fallback determinístico.
    """
    def _deterministico_ok_motivo_msg() -> Dict[str,Any]:
        det = decide_passeio_curto(hist, prev, data_evento, evento_tipo or "evento")
        motivo = " ".join(str(det.get("motivo","")).split()[:8]).strip() or ("condições favoráveis" if det.get("ok") else "condições desfavoráveis")
        msg = _mensagem_deterministica(hist, prev, data_evento, evento_tipo, person_name, pet_name)
        return {"ok": bool(det.get("ok")), "motivo": motivo, "mensagem": msg}

    item_prev = _pega_prev_no_dia(prev, data_evento)

    contexto = {
        "data_evento": str(pd.to_datetime(data_evento).date()),
        "evento_tipo": evento_tipo or "evento",
        "person_name": person_name or "",
        "pet_name": pet_name or "",
        "historico": {
            "temp_mean_c": (hist.get("temp_mean_c") or {}).get("mean"),
            "rain_mm_day": (hist.get("rain_mm_day") or {}).get("mean"),
            "resumo": hist.get("resumo"),
        },
        "previsao_dia": item_prev or {},
    }

    instrucoes = (
        "Responda SOMENTE com um JSON de UM objeto (sem texto extra), assim:\n"
        '{"ok": true|false, "motivo": "até 8 palavras", "mensagem": "até 220 caracteres"}\n'
        "Regras ok=false: (prob_chuva>=50 ou chuva_mm>=10) OU (tmax>=35 ou sensacao_max>=35) "
        "OU (vento_max>=40) OU (vis_km<=5). Se pet_name existir e envolver passeio/corrida, seja mais cauteloso com calor. "
        "A 'mensagem' deve ser em português, natural e útil ao usuário, citando temperatura e chuva quando relevante."
    )

    prompt = (
        f"INSTRUCOES:\n{instrucoes}\n\n"
        f"CONTEXTO:\n{json.dumps(contexto, ensure_ascii=False)}\n\n"
        "RESPOSTA:"
    )

    raw = _ollama_run(model, prompt)
    raw = (raw or "").strip().strip("`").strip()

    import re as _re, json as _json
    m = _re.search(r"\{[^{}]*\}", raw, flags=_re.S)
    if not m:
        return _deterministico_ok_motivo_msg()
    try:
        obj = _json.loads(m.group(0))
        ok = bool(obj.get("ok"))
        motivo = " ".join(str(obj.get("motivo","")).split()[:8]).strip() or ("condições favoráveis" if ok else "condições desfavoráveis")
        mensagem = str(obj.get("mensagem","")).strip()
        if len(mensagem) > 220:
            mensagem = mensagem[:220].rstrip()
        if not mensagem:
            mensagem = _mensagem_deterministica(hist, prev, data_evento, evento_tipo, person_name, pet_name)
        return {"ok": ok, "motivo": motivo, "mensagem": mensagem}
    except Exception:
        return _deterministico_ok_motivo_msg()

# ======== decisão binária ultra-curta ========
def decide_passeio_curto(hist: dict, prev: dict | None, data_evento: str, evento_tipo: str = "passeio"):
    TH_PPROB = int(os.getenv("TH_PPROB", "50"))       # % chuva
    TH_PMM   = float(os.getenv("TH_PMM", "10"))       # mm dia
    TH_TMAX  = float(os.getenv("TH_TMAX", "35"))      # °C calor
    TH_WIND  = float(os.getenv("TH_WIND", "40"))      # km/h vento
    TH_VIS   = float(os.getenv("TH_VIS", "5"))        # km
    TH_HRAIN = float(os.getenv("TH_HRAIN", "10"))     # mm média histórica “muito chuvoso”
    TH_HTEMP = float(os.getenv("TH_HTEMP", "30"))     # °C média hist “muito quente”

    item = _pega_prev_no_dia(prev, data_evento)
    if item:
        pp  = (item.get("precip_prob") or 0)
        pm  = (item.get("precip_mm") or 0.0)
        tmx = (item.get("tmax") or item.get("apparent_max") or 0.0)
        wnd = (item.get("wind_max") or 0.0)
        vis = item.get("visibility_km")
        if pp >= TH_PPROB or pm >= TH_PMM: return {"ok": False, "motivo": "Chuva no dia."}
        if tmx >= TH_TMAX:                 return {"ok": False, "motivo": "Calor forte."}
        if wnd >= TH_WIND:                 return {"ok": False, "motivo": "Vento forte."}
        if vis is not None and vis <= TH_VIS: return {"ok": False, "motivo": "Baixa visibilidade."}
        return {"ok": True, "motivo": "Condições ok."}

    if hist and hist.get("ok"):
        pm_hist = (hist.get("rain_mm_day") or {}).get("mean", 0.0)
        tm_hist = (hist.get("temp_mean_c") or {}).get("mean", 0.0)
        if pm_hist >= TH_HRAIN: return {"ok": False, "motivo": "Período costuma ser chuvoso."}
        if tm_hist >= TH_HTEMP: return {"ok": False, "motivo": "Período costuma ser quente."}
        return {"ok": True, "motivo": "Histórico favorável."}

    return {"ok": True, "motivo": "Sem bloqueios."}

def decisao_binaria_evento(hist, prev, data_evento, evento_tipo="", person_name="", pet_name="") -> Dict[str, Any]:
    if OLLAMA_ENABLE:
        try:
            pet_safe = (pet_name or PET_NAME) if MENTION_PET else ""
            out_ai = gerar_recomendacao_contextual_ollama(
                hist, prev, data_evento,
                evento_tipo=evento_tipo or EVENT_TYPE,
                person_name=person_name or PERSON_NAME,
                pet_name=pet_safe,
                model=OLLAMA_MODEL
            )
            if isinstance(out_ai, dict) and "ok" in out_ai and "motivo" in out_ai:
                motivo = " ".join(str(out_ai.get("motivo","")).split()[:8]).strip()
                payload = {"ok": bool(out_ai.get("ok")), "motivo": motivo}
                if REC_VERBOSE and out_ai.get("mensagem"):
                    payload["mensagem"] = out_ai["mensagem"]
                return payload
        except Exception:
            pass

    det = decide_passeio_curto(hist, prev, data_evento, evento_tipo or "evento")
    det["motivo"] = " ".join(str(det.get("motivo","")).split()[:8]).strip() or ("condições favoráveis" if det.get("ok") else "condições desfavoráveis")
    if REC_VERBOSE:
        det["mensagem"] = _mensagem_deterministica(hist, prev, data_evento, evento_tipo, person_name, pet_name)
    return det

# ===================== Front: formatos amigáveis =====================
def _formatar_prev_diaria(d: dict) -> dict:
    if not isinstance(d, dict):
        return {}
    data = None
    try:
        data = str(pd.to_datetime(d.get("date")).date())
    except Exception:
        data = d.get("date") or None

    tmin = d.get("tmin")
    tmax = d.get("tmax")
    chuva = d.get("precip_mm")
    prob = d.get("precip_prob")
    wnd  = d.get("wind_max")
    hum  = d.get("humidity_mean")
    vis  = d.get("visibility_km")

    # média térmica para índice
    tempC = None
    try:
        if tmax is not None and tmin is not None:
            tempC = (float(tmax) + float(tmin)) / 2.0
        elif tmax is not None:
            tempC = float(tmax)
        elif tmin is not None:
            tempC = float(tmin)
    except Exception:
        tempC = None

    cond, icone = _condicao_icone(chuva_mm=chuva, solar_wm2=None, vis_km=vis, prob_chuva=prob)
    indice = _indice_atividade(tempC, chuva, wnd, hum)

    return {
        "data": data,
        "tminC": _r1(tmin),
        "tmaxC": _r1(tmax),
        "chuvaMm": _r1(chuva),
        "probChuvaPct": _r0(prob),
        "ventoMaxKmh": _r1(wnd),
        "umidadePct": _r0(hum),
        "visKm": _r1(vis),
        "condicao": cond,
        "icone": icone,
        "indiceAtividade": indice
    }

def compose_human_message(data_evento: str,
                          event_type: str,
                          person_name: str,
                          pet_name: Optional[str],
                          hist: Dict[str,Any],
                          decision: Dict[str,Any]) -> str:
    """
    Mensagem curta/simpática configurável via FRIENDLY_STYLE (amigavel|curto|formal)
    e MENTION_PET (só cita pet se true e houver nome).
    """
    # quem / quando
    try:
        data_pt = pd.to_datetime(data_evento).strftime("%d/%m/%Y")
    except Exception:
        data_pt = str(data_evento)

    person = (person_name or "").strip()
    pet    = (pet_name or "").strip()
    say_pet = (MENTION_PET and bool(pet))

    # histórico curto
    t_mean = (hist.get("temp_mean_c") or {}).get("mean")
    r_mean = (hist.get("rain_mm_day") or {}).get("mean")
    hist_bits = []
    if t_mean is not None: hist_bits.append(f"{t_mean:.1f}°C")
    if r_mean is not None: hist_bits.append(f"{r_mean:.1f} mm/dia")
    hist_txt = ("Histórico: " + ", ".join(hist_bits) + ".") if hist_bits else ""

    ok = bool(decision.get("ok"))
    motivo = (decision.get("motivo") or "").strip()

    if FRIENDLY_STYLE in ("curto","curtinho"):
        base = f"{person or 'Você'} vai {event_type}" + (f" com {pet}" if say_pet else "") + f" em {data_pt}? "
        fin  = "Parece ok." if ok else "Considere um plano B."
        return (base + (hist_txt + " " if hist_txt else "") + fin).strip()

    if FRIENDLY_STYLE in ("formal","neutro"):
        base = f"{person or 'Usuário'} tem {event_type}" + (f" com {pet}" if say_pet else "") + f" em {data_pt}. "
        fin  = "Cenário favorável." if ok else f"Atenção: {motivo or 'condições não ideais'}."
        return (base + (hist_txt + " " if hist_txt else "") + fin).strip()

    # amigável (padrão)
    if ok:
        head = f"Boa, {person or 'você'}!"
        corpo = f" {data_pt} tá com cara de dar certo para {event_type}" + (f" com {pet}" if say_pet else "") + "."
        cauda = " Fique de olho na previsão da semana. 😉"
        extra = f" {hist_txt}" if hist_txt else ""
        return (head + corpo + extra + cauda).strip()
    else:
        head = f"{person or 'Ei'}, eu iria com calma:"
        corpo = f" para {event_type}" + (f" com {pet}" if say_pet else "") + f" em {data_pt}, {motivo or 'as condições não são ideais'}."
        extra = f" {hist_txt}" if hist_txt else ""
        cauda = " Se puder, tenha um plano B. ✨"
        return (head + corpo + extra + cauda).strip()

def formatar_card_evento(payload: dict) -> dict:
    lat = payload.get("coords", {}).get("lat")
    lon = payload.get("coords", {}).get("lon")
    data_evento = payload.get("data_evento")
    analise = payload.get("analise_evento", {}) or {}
    hist = analise.get("historico", {}) or {}
    prev = payload.get("painel_7dias", {}) or {}
    decisao = analise.get("decisao_binaria") or {"ok": False, "motivo": "dados insuficientes"}

    # acha o dia na previsão
    daily = prev.get("daily") or []
    item_prev = None
    try:
        de = pd.to_datetime(data_evento).date()
        for d in daily:
            if pd.to_datetime(d.get("date")).date() == de:
                item_prev = d
                break
    except Exception:
        pass

    if item_prev:
        tmax = item_prev.get("tmax"); tmin = item_prev.get("tmin")
        temp_c = None
        if tmax is not None and tmin is not None:
            temp_c = (float(tmax) + float(tmin)) / 2.0
        elif tmax is not None:
            temp_c = float(tmax)
        sens_c = item_prev.get("apparent_max") or temp_c
        chuva_mm = item_prev.get("precip_mm")
        vento_kmh = item_prev.get("wind_max")
        umid_pct = item_prev.get("humidity_mean")
        vis_km   = item_prev.get("visibility_km")
        cond, icone = _condicao_icone(chuva_mm=chuva_mm, solar_wm2=None, vis_km=vis_km, prob_chuva=item_prev.get("precip_prob"))
        indice = _indice_atividade(temp_c, chuva_mm, vento_kmh, umid_pct)
    else:
        temp_c    = (hist.get("temp_mean_c") or {}).get("mean")
        sens_c    = temp_c
        chuva_mm  = (hist.get("rain_mm_day") or {}).get("mean")
        vento_kmh = (hist.get("wind_mean_kmh") or {}).get("mean")
        umid_pct  = (hist.get("rh_mean_pct") or {}).get("mean")
        solar_wm2 = (hist.get("solar_mean_wm2") or {}).get("mean")
        cond, icone = _condicao_icone(chuva_mm=chuva_mm, solar_wm2=solar_wm2, vis_km=None, prob_chuva=None)
        indice = _indice_atividade(temp_c, chuva_mm, vento_kmh, umid_pct)

    card = {
        "data": str(pd.to_datetime(data_evento).date()) if data_evento else None,
        "local": {"lat": lat, "lon": lon},
        "resumo": {
            "temperaturaC": _r1(temp_c),
            "sensacaoC": _r1(sens_c),
            "chuvaMmDia": _r1(chuva_mm),
            "ventoKmh": _r1(vento_kmh),
            "umidadePct": _r0(umid_pct),
            "condicao": cond,
            "icone": icone,
            "indiceAtividade": indice,
        },
        "recomendacao": {
            "ok": bool(decisao.get("ok")),
            "motivo": str(decisao.get("motivo",""))[:120]
        }
    }
    if "mensagem" in decisao and decisao["mensagem"]:
        card["recomendacao"]["mensagem"] = decisao["mensagem"]
    return card

def montar_blocos_front(payload: dict, limitar_dias: int = 7) -> dict:
    prev = payload.get("painel_7dias", {}) or {}
    hist = (payload.get("analise_evento", {}) or {}).get("historico", {}) or {}
    daily = prev.get("daily") or []
    # ordena por data para evitar datas fora de ordem
    try:
        daily_sorted = sorted(daily, key=lambda x: pd.to_datetime(x.get("date")))
    except Exception:
        daily_sorted = daily
    dias_fmt = [_formatar_prev_diaria(d) for d in (daily_sorted[:limitar_dias] if limitar_dias else daily_sorted)]

    return {
        "card": formatar_card_evento(payload),
        "dias7": dias_fmt,
        "meta": {
            "fonte_previsao": prev.get("provider"),
            "fonte_historico": hist.get("fonte") or (payload.get("analise_evento", {}) or {}).get("fonte_historico")
        }
    }

def formatar_bem_amigavel(payload: dict) -> dict:
    """
    Cartão minimalista para o front + painel amigável dos próximos 7 dias.
    Inclui 'mensagem' dentro de 'recomendacao'.
    """
    # bases
    lat = payload.get("coords", {}).get("lat")
    lon = payload.get("coords", {}).get("lon")
    data_evento = payload.get("data_evento")
    analise = payload.get("analise_evento", {}) or {}
    hist = analise.get("historico", {}) or {}
    prev = payload.get("painel_7dias", {}) or {}
    decisao = analise.get("decisao_binaria") or {"ok": False, "motivo": "dados insuficientes"}

    # previsão do dia
    daily = prev.get("daily") or []
    item_prev = None
    try:
        de = pd.to_datetime(data_evento).date()
        for d in daily:
            if pd.to_datetime(d.get("date")).date() == de:
                item_prev = d
                break
    except Exception:
        item_prev = None

    if item_prev:
        tmax = item_prev.get("tmax")
        tmin = item_prev.get("tmin")
        temp_c = None
        if tmax is not None and tmin is not None:
            temp_c = (float(tmax) + float(tmin)) / 2.0
        elif tmax is not None:
            temp_c = float(tmax)

        sens_c = item_prev.get("apparent_max")
        if sens_c is None:
            sens_c = temp_c

        chuva_mm = item_prev.get("precip_mm")
        vento_kmh = item_prev.get("wind_max")
        umid_pct = item_prev.get("humidity_mean")
        vis_km = item_prev.get("visibility_km")

        cond, icone = _condicao_icone(
            chuva_mm=chuva_mm,
            solar_wm2=None,
            vis_km=vis_km,
            prob_chuva=item_prev.get("precip_prob"),
        )
        indice = _indice_atividade(temp_c, chuva_mm, vento_kmh, umid_pct)
    else:
        # fora do horizonte -> climatologia
        temp_c    = (hist.get("temp_mean_c") or {}).get("mean")
        chuva_mm  = (hist.get("rain_mm_day") or {}).get("mean")
        vento_kmh = (hist.get("wind_mean_kmh") or {}).get("mean")
        umid_pct  = (hist.get("rh_mean_pct") or {}).get("mean")
        solar_wm2 = (hist.get("solar_mean_wm2") or {}).get("mean")
        sens_c    = temp_c
        cond, icone = _condicao_icone(chuva_mm=chuva_mm, solar_wm2=solar_wm2, vis_km=None, prob_chuva=None)
        indice = _indice_atividade(temp_c, chuva_mm, vento_kmh, umid_pct)

    resumo = {
        "temperaturaC": _r1(temp_c),
        "sensacaoC": _r1(sens_c),
        "chuvaMmDia": _r1(chuva_mm),
        "ventoKmh": _r1(vento_kmh),
        "umidadePct": _r0(umid_pct),
        "condicao": cond,
        "icone": icone,
        "indiceAtividade": indice,
    }

    # próximos 7 dias
    proximos7 = []
    if isinstance(daily, list) and daily:
        try:
            daily_sorted = sorted(daily, key=lambda x: pd.to_datetime(x.get("date")))
        except Exception:
            daily_sorted = daily
        for d in daily_sorted[:7]:
            proximos7.append(_formatar_prev_diaria(d))

    # mensagem simpática
    ctx = (analise.get("contexto_detectado") or {})
    event_type_final = (ctx.get("event_type") or EVENT_TYPE or "evento")
    person_final = (PERSON_NAME or "")
    pet_final = (ctx.get("pet_name") or PET_NAME)

    try:
        mensagem = compose_human_message(
            data_evento=data_evento,
            event_type=event_type_final,
            person_name=person_final,
            pet_name=pet_final,
            hist=hist,
            decision=decisao
        )
    except Exception:
        mensagem = None

    return {
        "data": str(pd.to_datetime(data_evento).date()) if data_evento else None,
        "local": {"lat": lat, "lon": lon},
        "resumo": resumo,
        "recomendacao": {
            "ok": bool(decisao.get("ok")),
            "motivo": str(decisao.get("motivo", "")).strip()[:120],
            "mensagem": mensagem
        },
        "proximos7dias": proximos7,
        "fonte_previsao": prev.get("provider"),
        "fonte_historico": hist.get("fonte") or analise.get("fonte_historico"),
    }

# ===================== Contexto do evento (título livre ou mapeado) =====================
def _strip_accents(s: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

_EVENT_MAP = [
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

def _guess_pet_name(title_norm: str, original: str) -> Optional[str]:
    m = re.search(r'["“”\'’]([^"“”\'’]{2,20})["“”\'’]', original)
    if m: return m.group(1).strip()
    m2 = re.search(r'\bcom\s+([A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wÁÉÍÓÚÂÊÔÃÕÇ-]{1,20})\b', original)
    if m2: return m2.group(1).strip()
    m3 = re.search(r'\bcom\s+([a-z0-9\-]{2,20})\b', title_norm)
    if m3:
        cand = m3.group(1)
        if cand not in ("amigos", "familia", "familiares", "galera", "time"):
            return cand.capitalize()
    return None

def infer_context_from_title(title: str, free_mode: bool = False, allow_pet_guess: bool = False) -> Dict[str, Optional[str]]:
    """
    Retorna: {"event_type": str, "person_name": Optional[str], "pet_name": Optional[str]}
    - Se free_mode=True: usa o título como event_type (sem mapa fixo).
    - Só tenta adivinhar pet se allow_pet_guess=True.
    """
    if not title:
        return {"event_type": None, "person_name": None, "pet_name": None}

    original = title.strip()
    title_norm = _strip_accents(original).lower()

    # modo livre: qualquer texto vira tipo do evento
    if free_mode:
        pet_name = _guess_pet_name(title_norm, original) if allow_pet_guess else None
        short = original if len(original) <= 60 else original[:60].rsplit(" ", 1)[0]
        return {"event_type": short, "person_name": None, "pet_name": pet_name}

    # modo mapa + heurísticas
    found_type = None
    for keys, label in _EVENT_MAP:
        for k in keys:
            if f" {k} " in f" {title_norm} " or title_norm.startswith(k + " ") or title_norm.endswith(" " + k):
                found_type = label
                break
        if found_type:
            break

    if not found_type and ("passeio" in title_norm or "passear" in title_norm):
        found_type = "passeio"
    if ("cachorro" in title_norm or " dog " in f" {title_norm} " or " pet " in f" {title_norm} ") and ("passeio" in title_norm or "passear" in title_norm):
        found_type = "passear com cachorro"

    pet_name = _guess_pet_name(title_norm, original) if (allow_pet_guess and found_type == "passear com cachorro") else None

    if not found_type:
        fallback = original.strip()
        if len(fallback) > 60:
            fallback = fallback[:60].rsplit(" ", 1)[0]
        found_type = fallback

    return {"event_type": found_type or "evento", "person_name": None, "pet_name": pet_name}

def gerar_recomendacao_texto(hist: dict, prev: dict | None, data_evento: str, curto: bool = True) -> str:
    """
    Recomendações determinísticas curtas (sem IA).
    - Se existir previsão para o dia do evento, usa ela.
    - Senão, usa o histórico/climatologia.
    """
    linhas: list[str] = []
    alerta_hist = False

    if hist and hist.get("ok"):
        linhas.append(hist.get("resumo", ""))
        pm = (hist.get("rain_mm_day") or {}).get("mean", 0.0)
        if pm is not None and pm >= 10:
            alerta_hist = True

    # pega o item da previsão exatamente no dia do evento
    item = _pega_prev_no_dia(prev, data_evento)

    if curto:
        if item:
            pp   = item.get("precip_prob") or 0
            pr   = item.get("precip_mm") or 0.0
            app  = item.get("apparent_max") or item.get("tmax") or None
            wmax = item.get("wind_max") or 0
            vis  = item.get("visibility_km") or 99

            risco = []
            if pp >= 60 or pr >= 10: risco.append("chuva")
            if app is not None and app >= 35: risco.append("calor")
            if wmax >= 40: risco.append("vento")
            if vis <= 5: risco.append("baixa visibilidade")

            if risco:
                return "⚠️ Recomendação: **evitar** — risco de " + ", ".join(risco) + "."
            return "✅ Recomendação: **ok** — sem sinais relevantes para o dia."

        if alerta_hist:
            return "⚠️ Recomendação: **atenção** — histórico indica chuva/instabilidade no período."
        return "✅ Recomendação: **ok** — histórico não indica risco relevante."

    # versão não-curta (texto mais completo)
    if item:
        tmax = item.get("tmax"); tmin = item.get("tmin")
        pp   = item.get("precip_prob"); pr = item.get("precip_mm")
        hum  = item.get("humidity_mean"); vis = item.get("visibility_km")
        wmax = item.get("wind_max"); app = item.get("apparent_max")
        prov = item.get("provider", "open-meteo")

        try:
            tspan = f"{int(round(tmin))}–{int(round(tmax))}°C" if (tmin is not None and tmax is not None) else None
        except Exception:
            tspan = None

        linhas.append(
            f"Previsão ({prov}) para o dia: "
            f"{tspan or 'temperaturas disponíveis'}, "
            f"chuva {0 if pr is None else round(pr,1)} mm (prob {pp or 0}%), "
            f"umidade {'' if hum is None else int(round(hum))}%, "
            f"vis {'' if vis is None else round(vis,1)} km, "
            f"vento máx {wmax or 0} km/h, sensação máx {'' if app is None else round(app,1)}°C."
        )
    else:
        tm = (hist.get("temp_mean_c") or {}).get("mean")
        pm = (hist.get("rain_mm_day") or {}).get("mean")
        if tm is not None and pm is not None:
            linhas.append(f"Historicamente, média de {tm:.1f}°C e {pm:.1f} mm/dia neste período.")

    if alerta_hist:
        linhas.append("⚠️ Em anos anteriores, acumulados diários elevados não são raros neste período.")

    return " ".join(x for x in linhas if x).strip() or "Sem dados suficientes para recomendação."

# ===================== Orquestração =====================
def avaliar_evento(lat: float, lon: float, data_evento: str,
                   subset_txt: Path = SUBSET_FILE,
                   gldas_raw_dir: Path = GLDAS_RAW_DIR,
                   max_files:int = MAX_FILES,
                   janela_hist:int = 1,
                   anos_hist= (2020,2021,2022,2023,2024),
                   timezone:str = TIMEZONE,
                   event_title: Optional[str] = None) -> Dict[str,Any]:
    # 1) subset
    txt = autodiscover_subset_file(subset_txt, DATA_DIR)

    # 2) links + filtro
    links_all = read_links_from_txt(txt)
    links = filter_links_for_event_window(links_all, data_evento,
                                          janela=janela_hist, anos=anos_hist)

    # 3) download
    limite = len(links) if max_files == 0 else min(max_files, len(links))
    download_gldas(links, gldas_raw_dir, max_files=limite)

    # 4) GLDAS -> diário
    files = list_nc4(gldas_raw_dir)
    hist: Dict[str, Any] = {"ok": False, "msg": "Sem dados GLDAS para a janela."}
    if files:
        try:
            df_daily = process_gldas_to_daily(files, lat, lon)
            hist = climatologia(df_daily, data_evento,
                                anos=anos_hist, janela=janela_hist)
            if hist.get("ok"):
                hist["fonte"] = "GLDAS/Earthdata"
        except Exception as e:
            hist = {"ok": False, "msg": f"Falha ao processar GLDAS: {e}"}

    # 5) fallback histórico
    if not hist.get("ok"):
        print("… GLDAS insuficiente → usando fallback ERA5.")
        hist = hist_fallback_era5_openmeteo(lat, lon, data_evento,
                                            janela=janela_hist, anos=anos_hist)

    # 6) Previsão 7 dias
    prev = previsao_7_dias(lat, lon, days=7, timezone=timezone)

    # 7) Recomendação determinística (string)
    texto = gerar_recomendacao_texto(hist, prev, data_evento, curto=True)

    # 8) Contexto do evento (livre se FREE_EVENT_MODE)
    inferidos = infer_context_from_title(event_title or "", free_mode=FREE_EVENT_MODE, allow_pet_guess=PET_FROM_TITLE)

    # 9) Decisão (IA local -> fallback determinístico)
    decisao = decisao_binaria_evento(
        hist, prev, data_evento,
        evento_tipo=(inferidos.get("event_type") or EVENT_TYPE or (event_title or "evento")),
        person_name=(inferidos.get("person_name") or PERSON_NAME),
        pet_name=(inferidos.get("pet_name") or PET_NAME),
    )

    return {
        "ok": True,
        "coords": {"lat": lat, "lon": lon},
        "data_evento": data_evento,
        "painel_7dias": prev,
        "analise_evento": {
            "historico": hist,
            "fonte_historico": hist.get("fonte", "desconhecida"),
            "usou_earthdata": hist.get("fonte") == "GLDAS/Earthdata",
            "recomendacao": texto,
            "decisao_binaria": decisao,
            "contexto_detectado": inferidos,
        }
    }

# ===================== Main (exemplo CLI) =====================
if __name__ == "__main__":
    import sys, os, json

    LAT = float(os.getenv("LAT", "-23.62"))
    LON = float(os.getenv("LON", "-46.55"))
    DATA_EVENTO = os.getenv("TARGET_DATE", "2025-10-07")
    EVENT_TITLE = os.getenv("EVENT_TITLE", "")

    # flags do .env (reforça leitura aqui também)
    COMPACT_JSON    = os.getenv("COMPACT_JSON", "false").lower() in ("1","true","yes","y")
    FRONT_MIN       = os.getenv("FRONT_MIN", "false").lower() in ("1","true","yes","y")
    FRONT_BLOCKS    = os.getenv("FRONT_BLOCKS", "false").lower() in ("1","true","yes","y")
    FRIENDLY_OUTPUT = os.getenv("FRIENDLY_OUTPUT", "false").lower() in ("1","true","yes","y")

    # flags via CLI
    if any(a in ("--compact","-c") for a in sys.argv[1:]): COMPACT_JSON = True
    if any(a in ("--min","--card") for a in sys.argv[1:]): FRONT_MIN = True
    if any(a in ("--blocks","--blocos") for a in sys.argv[1:]): FRONT_BLOCKS = True
    if any(a in ("--friendly","--amigavel") for a in sys.argv[1:]): FRIENDLY_OUTPUT = True

    res = avaliar_evento(LAT, LON, DATA_EVENTO, event_title=EVENT_TITLE)

    # Ordem de prioridade de saída:
    # 1) --compact  2) --blocks  3) --min  4) FRIENDLY_OUTPUT  5) payload completo
    if COMPACT_JSON:
        payload = res.get("analise_evento", {}).get("decisao_binaria", {"ok": False, "motivo": "dados insuficientes"})
        print(json.dumps(payload, ensure_ascii=False))
    elif FRONT_BLOCKS:
        print(json.dumps(montar_blocos_front(res), ensure_ascii=False))
    elif FRONT_MIN:
        print(json.dumps(formatar_card_evento(res), ensure_ascii=False))
    elif FRIENDLY_OUTPUT:
        print(json.dumps(formatar_bem_amigavel(res), ensure_ascii=False))
    else:
        print("\n==== RESULTADO ====")
        print(json.dumps(res, ensure_ascii=False, indent=2, default=str))
