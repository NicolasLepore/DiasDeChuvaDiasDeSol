from __future__ import annotations
from typing import Dict, Any, Optional, List
import pandas as pd
from .config import (REC_VERBOSE, OLLAMA_ENABLE, OLLAMA_MODEL, EVENT_TYPE, PERSON_NAME, PET_NAME)
from .rules import decide_passeio_curto
from .ai import gerar_recomendacao_contextual_ollama
from .utils import c2f, mm2in

def _pega_prev_no_dia(prev: Optional[Dict[str,Any]], data_evento: str) -> Optional[Dict[str,Any]]:
    if not prev or not prev.get("ok"): return None
    try:
        de = pd.to_datetime(data_evento).date()
        return next((d for d in prev["daily"] if pd.to_datetime(d["date"]).date() == de), None)
    except Exception:
        return None

def _mensagem_deterministica(hist: dict, prev: dict | None, data_evento: str,
                             evento_tipo: str, person_name: str, pet_name: str) -> str:
    try: data_en = pd.to_datetime(data_evento).strftime("%Y-%m-%d")
    except Exception: data_en = str(data_evento)
    sujeito = person_name or "You"
    alvo = evento_tipo or "your event"
    intro = f"{sujeito} will attend {alvo}" + (f" with {pet_name}" if pet_name else "") + f" on {data_en}? "
    item = _pega_prev_no_dia(prev, data_evento)
    partes: List[str] = [intro]
    if item:
        tmin = item.get("tmin"); tmax = item.get("tmax")
        def _c2f_i(x): 
            try: return int(round((float(x)*9/5)+32))
            except: return None
        tspan = f"{_c2f_i(tmin)}–{_c2f_i(tmax)}°F" if (tmin is not None and tmax is not None) else None
        pp = item.get("precip_prob") or 0; pr = item.get("precip_mm") or 0
        riscos = []
        if pp >= 60 or pr >= 10: riscos.append("rain")
        if (item.get("apparent_max") or item.get("tmax") or 0) >= 35: riscos.append("heat")
        if (item.get("wind_max") or 0) >= 40: riscos.append("wind")
        if (item.get("visibility_km") or 99) <= 5: riscos.append("low visibility")
        base = f"Forecast suggests {tspan}." if tspan else "Forecast checked."
        partes.append(f"{base} {'Watch out for ' + ', '.join(riscos) + '. ' if riscos else 'No significant signals. '}")
    else:
        tm = (hist.get("temp_mean_c") or {}).get("mean"); pr = (hist.get("rain_mm_day") or {}).get("mean")
        if tm is not None and pr is not None:
            partes.append(f"Historically around {c2f(tm)}°F and {mm2in(pr)} in/day in this period. ")
    det = decide_passeio_curto(hist, prev, data_evento, evento_tipo)
    partes.append("Looks good! 👍" if det.get("ok") else "Consider a plan B.")
    return "".join(partes).strip()

def gerar_recomendacao_texto(hist: dict, prev: dict | None, data_evento: str, curto: bool = True) -> str:
    linhas: list[str] = []
    alerta_hist = False
    if hist and hist.get("ok"):
        pm = (hist.get("rain_mm_day") or {}).get("mean", 0.0)
        tm = (hist.get("temp_mean_c") or {}).get("mean")
        bits = []
        if tm is not None: bits.append(f"{c2f(tm)}°F")
        if pm is not None: bits.append(f"{mm2in(pm)} in/day")
        if bits: linhas.append("History: " + ", ".join(bits) + ".")
        if pm is not None and pm >= 10: alerta_hist = True

    item = _pega_prev_no_dia(prev, data_evento)
    if curto:
        if item:
            pp = item.get("precip_prob") or 0; pr = item.get("precip_mm") or 0.0
            app = item.get("apparent_max") or item.get("tmax") or None
            wmx = item.get("wind_max") or 0; vis = item.get("visibility_km") or 99
            riscos = []
            if pp >= 60 or pr >= 10: riscos.append("rain")
            if app is not None and app >= 35: riscos.append("heat")
            if wmx >= 40: riscos.append("wind")
            if vis <= 5: riscos.append("low visibility")
            if riscos: return "⚠️ Recommendation: **avoid** — risk of " + ", ".join(riscos) + "."
            return "✅ Recommendation: **ok** — no significant risks for the day."
        if alerta_hist: return "⚠️ Recommendation: **caution** — history suggests frequent rain/instability in this period."
        return "✅ Recommendation: **ok** — history shows no relevant risks."

    return " ".join(x for x in linhas if x).strip() or "Not enough data for a recommendation."

def decisao_binaria_evento(hist, prev, data_evento, evento_tipo="", person_name="", pet_name="") -> Dict[str, Any]:
    det = decide_passeio_curto(hist, prev, data_evento, evento_tipo or "event")
    motivo_pt = str(det.get("motivo","")).lower()
    motivo_en = "favorable conditions"
    if "chuva" in motivo_pt: motivo_en = "rain on the day"
    elif "calor" in motivo_pt: motivo_en = "excessive heat"
    elif "vento" in motivo_pt: motivo_en = "strong winds"
    elif "visibilidade" in motivo_pt: motivo_en = "low visibility"
    elif "chuvoso" in motivo_pt: motivo_en = "historically rainy period"
    elif "quente" in motivo_pt: motivo_en = "historically hot period"
    elif "bloqueios" in motivo_pt: motivo_en = "no blockers"
    payload = {"ok": bool(det.get("ok")), "motivo": motivo_en}

    msg_fallback = _mensagem_deterministica(hist, prev, data_evento, evento_tipo or "event", person_name, pet_name)
    if OLLAMA_ENABLE:
        try:
            ai = gerar_recomendacao_contextual_ollama(hist, prev, data_evento,
                                                      evento_tipo or EVENT_TYPE,
                                                      person_name or PERSON_NAME,
                                                      pet_name or PET_NAME,
                                                      msg_fallback,
                                                      model=OLLAMA_MODEL)
            payload = {"ok": bool(ai.get("ok")), "motivo": str(ai.get("motivo","")).strip()[:120]}
            if REC_VERBOSE and ai.get("mensagem"): payload["mensagem"] = ai["mensagem"]
            return payload
        except Exception:
            pass

    if REC_VERBOSE:
        payload["mensagem"] = msg_fallback
    return payload
