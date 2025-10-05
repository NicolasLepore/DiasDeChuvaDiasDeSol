from __future__ import annotations
from typing import Any, Dict
import pandas as pd
import requests
from .config import GOOGLE_WEATHER_API_KEY

def forecast_google(lat: float, lon: float, days:int=7, timezone="auto") -> Dict[str,Any]:
    key = GOOGLE_WEATHER_API_KEY
    if not key:
        return {"ok": False, "msg": "GOOGLE_WEATHER_API_KEY ausente."}
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
            return {"ok": False, "msg": "Google Weather 403."}
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
            return {"ok": False, "msg": "Google Weather sem daily."}
        return {"ok": True, "daily": daily, "provider": "google"}
    except Exception as e:
        return {"ok": False, "msg": f"Google Weather falhou: {e}"}

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
