from __future__ import annotations
from typing import Optional, Dict, Any
import pandas as pd

def r0(x):
    try: return None if x is None else int(round(float(x)))
    except Exception: return None

def r1(x):
    try: return None if x is None else round(float(x), 1)
    except Exception: return None

def condicao_icone(chuva_mm: float | None, solar_wm2: float | None = None, vis_km: float | None = None, prob_chuva: float | None = None):
    def _f(v):
        try: return None if v is None else float(v)
        except: return None
    chuva_mm  = _f(chuva_mm); solar_wm2 = _f(solar_wm2); vis_km = _f(vis_km); prob_chuva = _f(prob_chuva)
    if chuva_mm is not None:
        if chuva_mm >= 8:   return "Chuva forte", "⛈️"
        if chuva_mm >= 4:   return "Chuva moderada", "🌧️"
        if chuva_mm >= 0.5: return "Chuva fraca", "🌦️"
        if solar_wm2 is not None: return ("Nublado","☁️") if solar_wm2 < 150 else ("Ensolarado","☀️")
        if vis_km is not None and vis_km <= 5: return "Neblina","🌫️"
        return "Parcialmente nublado","🌤️"
    if vis_km is not None and vis_km <= 5: return "Neblina","🌫️"
    if solar_wm2 is not None: return ("Nublado","☁️") if solar_wm2 < 150 else ("Ensolarado","☀️")
    if prob_chuva is not None and prob_chuva >= 50: return "Possível chuva","🌦️"
    return "Indefinido","⛅"

def indice_atividade(temp_c: float | None, chuva_mm: float | None, vento_kmh: float | None, umid_pct: float | None):
    score = 10
    if temp_c is not None:
        t = float(temp_c)
        if t < 10: score -= 3
        elif t < 18: score -= 1
        elif t > 35: score -= 4
        elif t > 32: score -= 3
        elif t > 26: score -= 1
    if chuva_mm is not None:
        r = float(chuva_mm)
        if r >= 8: score -= 4
        elif r >= 4: score -= 3
        elif r >= 0.5: score -= 1
    if vento_kmh is not None:
        v = float(vento_kmh)
        if v > 40: score -= 3
        elif v > 28: score -= 2
        elif v > 12: score -= 1
    if umid_pct is not None:
        try:
            if float(umid_pct) >= 85: score -= 1
        except: pass
    return int(max(0, min(10, score)))

# conversions (US units para o front internacional)
def c2f(v):   return None if v is None else round((float(v) * 9.0/5.0) + 32.0, 1)
def kmh2mph(v): return None if v is None else round(float(v) * 0.621371, 1)
def mm2in(v): return None if v is None else round(float(v) / 25.4, 2)
def km2mi(v): return None if v is None else round(float(v) * 0.621371, 1)

def cond_pt_to_en(txt: str) -> str:
    m = (txt or "").lower()
    if "forte" in m and "chuva" in m: return "Heavy rain"
    if "moderada" in m and "chuva" in m: return "Moderate rain"
    if "fraca" in m and "chuva" in m: return "Light rain"
    if "possível chuva" in m or "possivel chuva" in m: return "Chance of rain"
    if "parcial" in m and "nublado" in m: return "Partly cloudy"
    if "nublado" in m: return "Cloudy"
    if "ensolarado" in m: return "Sunny"
    if "neblina" in m: return "Fog"
    if "indefinido" in m: return "Uncertain"
    return txt or "—"

def formatar_prev_diaria(d: dict) -> dict:
    from .utils import r0, c2f, mm2in, kmh2mph, km2mi, cond_pt_to_en, indice_atividade, condicao_icone
    if not isinstance(d, dict): return {"units":"us"}
    try: data = str(pd.to_datetime(d.get("date")).date())
    except Exception: data = d.get("date") or None
    tmin = d.get("tmin"); tmax = d.get("tmax")
    chuva = d.get("precip_mm"); prob = d.get("precip_prob")
    wnd  = d.get("wind_max");  hum  = d.get("humidity_mean")
    vis  = d.get("visibility_km")
    tempC = None
    try:
        if tmax is not None and tmin is not None: tempC = (float(tmax)+float(tmin))/2.0
        elif tmax is not None: tempC = float(tmax)
        elif tmin is not None: tempC = float(tmin)
    except Exception: pass
    cond_pt, icone = condicao_icone(chuva_mm=chuva, vis_km=vis, prob_chuva=prob)
    indice = indice_atividade(tempC, chuva, wnd, hum)
    return {
        "units":"us", "date": data,
        "tminF": c2f(tmin), "tmaxF": c2f(tmax),
        "precipIn": mm2in(chuva), "precipProbPct": r0(prob),
        "windMaxMph": kmh2mph(wnd), "humidityPct": r0(hum),
        "visibilityMiles": km2mi(vis),
        "condition": cond_pt_to_en(cond_pt), "icon": icone,
        "activityIndex": indice
    }
