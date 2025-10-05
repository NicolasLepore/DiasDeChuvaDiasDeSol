from __future__ import annotations
from typing import Any, Dict
import numpy as np
import pandas as pd
import requests

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
            if not d: continue
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
