from __future__ import annotations
from typing import Dict, Any, Optional, List
import pandas as pd
from .utils import r0, r1, condicao_icone, indice_atividade, formatar_prev_diaria, c2f, mm2in, kmh2mph, km2mi, cond_pt_to_en
from .config import PERSON_NAME, PET_NAME, EVENT_TYPE, MENTION_PET, FRIENDLY_STYLE
from .rules import decide_passeio_curto

def compose_human_message(data_evento: str, event_type: str, person_name: str,
                          pet_name: Optional[str], hist: Dict[str,Any], decision: Dict[str,Any]) -> str:
    try: data_en = pd.to_datetime(data_evento).strftime("%Y-%m-%d")
    except Exception: data_en = str(data_evento)
    person = (person_name or "").strip()
    pet    = (pet_name or "").strip()
    say_pet = (MENTION_PET and bool(pet))
    t_mean = (hist.get("temp_mean_c") or {}).get("mean")
    r_mean = (hist.get("rain_mm_day") or {}).get("mean")
    hist_bits = []
    if t_mean is not None: hist_bits.append(f"{c2f(t_mean)}°F")
    if r_mean is not None: hist_bits.append(f"{mm2in(r_mean)} in/day")
    hist_txt = ("History: " + ", ".join(hist_bits) + ".") if hist_bits else ""
    ok = bool(decision.get("ok")); motivo = (decision.get("motivo") or "").strip()

    if FRIENDLY_STYLE in ("curto","curtinho"):
        base = f"{person or 'You'} will attend {event_type}" + (f" with {pet}" if say_pet else "") + f" on {data_en}? "
        fin  = "Looks okay." if ok else "Consider a plan B."
        return (base + (hist_txt + " " if hist_txt else "") + fin).strip()
    if FRIENDLY_STYLE in ("formal","neutro"):
        base = f"{person or 'User'} has {event_type}" + (f" with {pet}" if say_pet else "") + f" on {data_en}. "
        fin  = "Favorable scenario." if ok else f"Attention: {motivo or 'non-ideal conditions'}."
        return (base + (hist_txt + " " if hist_txt else "") + fin).strip()

    if ok:
        head = f"Nice, {person or 'you'}!"
        body = f" {data_en} looks good for {event_type}" + (f" with {pet}" if say_pet else "") + "."
        tail = " Keep an eye on the weekly forecast. 😉"
        extra = f" {hist_txt}" if hist_txt else ""
        return (head + body + extra + tail).strip()
    else:
        head = f"Hey, I'd be cautious:"
        body = f" for {event_type}" + (f" with {pet}" if say_pet else "") + f" on {data_en}, {motivo or 'conditions aren’t ideal'}."
        extra = f" {hist_txt}" if hist_txt else ""
        tail = " If possible, have a plan B. ✨"
        return (head + body + extra + tail).strip()

def _pega_prev_no_dia(prev: Optional[Dict[str,Any]], data_evento: str) -> Optional[Dict[str,Any]]:
    if not prev or not prev.get("ok"): return None
    try:
        de = pd.to_datetime(data_evento).date()
        return next((d for d in prev["daily"] if pd.to_datetime(d["date"]).date() == de), None)
    except Exception:
        return None

def formatar_card_evento(payload: dict) -> dict:
    lat = payload.get("coords", {}).get("lat")
    lon = payload.get("coords", {}).get("lon")
    data_evento = payload.get("data_evento")
    analise = payload.get("analise_evento", {}) or {}
    hist = analise.get("historico", {}) or {}
    prev = payload.get("painel_7dias", {}) or {}
    decisao = analise.get("decisao_binaria") or {"ok": False, "motivo": "insufficient data"}

    daily = prev.get("daily") or []
    item_prev = _pega_prev_no_dia(prev, data_evento)

    if item_prev:
        tmax = item_prev.get("tmax"); tmin = item_prev.get("tmin")
        temp_c = None
        if tmax is not None and tmin is not None: temp_c = (float(tmax) + float(tmin)) / 2.0
        elif tmax is not None: temp_c = float(tmax)
        sens_c = item_prev.get("apparent_max") or temp_c
        chuva_mm = item_prev.get("precip_mm"); vento_kmh = item_prev.get("wind_max")
        umid_pct = item_prev.get("humidity_mean"); vis_km = item_prev.get("visibility_km")
        cond_pt, icone = condicao_icone(chuva_mm=chuva_mm, vis_km=vis_km, prob_chuva=item_prev.get("precip_prob"))
        indice = indice_atividade(temp_c, chuva_mm, vento_kmh, umid_pct)
    else:
        temp_c = (hist.get("temp_mean_c") or {}).get("mean"); sens_c = temp_c
        chuva_mm = (hist.get("rain_mm_day") or {}).get("mean")
        vento_kmh = (hist.get("wind_mean_kmh") or {}).get("mean")
        umid_pct  = (hist.get("rh_mean_pct") or {}).get("mean")
        cond_pt, icone = condicao_icone(chuva_mm=chuva_mm)

        indice = indice_atividade(temp_c, chuva_mm, vento_kmh, umid_pct)

    card = {
        "units": "us",
        "date": str(pd.to_datetime(data_evento).date()) if data_evento else None,
        "location": {"lat": lat, "lon": lon},
        "summary": {
            "temperatureF": c2f(temp_c),
            "feelsLikeF": c2f(sens_c),
            "precipitationIn": mm2in(chuva_mm),
            "windMph": kmh2mph(vento_kmh),
            "humidityPct": r0(umid_pct),
            "condition": cond_pt_to_en(cond_pt),
            "icon": icone,
            "activityIndex": indice,
        },
        "recommendation": {
            "ok": bool(decisao.get("ok")),
            "reason": str(decisao.get("motivo","")).strip()[:120]
        }
    }
    if "mensagem" in decisao and decisao["mensagem"]:
        card["recommendation"]["message"] = decisao["mensagem"]
    return card

def montar_blocos_front(payload: dict, limitar_dias: int = 7) -> dict:
    prev = payload.get("painel_7dias", {}) or {}
    hist = (payload.get("analise_evento", {}) or {}).get("historico", {}) or {}
    daily = prev.get("daily") or []
    try:
        daily_sorted = sorted(daily, key=lambda x: pd.to_datetime(x.get("date")))
    except Exception:
        daily_sorted = daily
    dias_fmt = [formatar_prev_diaria(d) for d in (daily_sorted[:limitar_dias] if limitar_dias else daily_sorted)]
    return {
        "units": "us",
        "card": formatar_card_evento(payload),
        "days7": dias_fmt,
        "meta": {
            "forecast_source": prev.get("provider"),
            "history_source": hist.get("fonte") or (payload.get("analise_evento", {}) or {}).get("fonte_historico")
        }
    }

def formatar_bem_amigavel(payload: dict) -> dict:
    lat = payload.get("coords", {}).get("lat")
    lon = payload.get("coords", {}).get("lon")
    data_evento = payload.get("data_evento")
    analise = payload.get("analise_evento", {}) or {}
    hist = analise.get("historico", {}) or {}
    prev = payload.get("painel_7dias", {}) or {}
    decisao = analise.get("decisao_binaria") or {"ok": False, "motivo": "insufficient data"}

    daily = prev.get("daily") or []
    item_prev = _pega_prev_no_dia(prev, data_evento)

    if item_prev:
        tmax = item_prev.get("tmax"); tmin = item_prev.get("tmin")
        temp_c = (float(tmax)+float(tmin))/2.0 if (tmax is not None and tmin is not None) else (float(tmax) if tmax is not None else None)
        sens_c = item_prev.get("apparent_max") or temp_c
        chuva_mm = item_prev.get("precip_mm"); vento_kmh = item_prev.get("wind_max")
        umid_pct = item_prev.get("humidity_mean"); vis_km = item_prev.get("visibility_km")
        cond_pt, icone = condicao_icone(chuva_mm=chuva_mm, vis_km=vis_km, prob_chuva=item_prev.get("precip_prob"))
        indice = indice_atividade(temp_c, chuva_mm, vento_kmh, umid_pct)
    else:
        temp_c = (hist.get("temp_mean_c") or {}).get("mean")
        sens_c = temp_c
        chuva_mm = (hist.get("rain_mm_day") or {}).get("mean")
        vento_kmh = (hist.get("wind_mean_kmh") or {}).get("mean")
        umid_pct  = (hist.get("rh_mean_pct") or {}).get("mean")
        cond_pt, icone = condicao_icone(chuva_mm=chuva_mm)
        indice = indice_atividade(temp_c, chuva_mm, vento_kmh, umid_pct)

    summary = {
        "temperatureF": c2f(temp_c),
        "feelsLikeF": c2f(sens_c),
        "precipitationIn": mm2in(chuva_mm),
        "windMph": kmh2mph(vento_kmh),
        "humidityPct": r0(umid_pct),
        "condition": cond_pt_to_en(cond_pt),
        "icon": icone,
        "activityIndex": indice,
    }

    next7 = []
    if isinstance(daily, list) and daily:
        try:
            daily_sorted = sorted(daily, key=lambda x: pd.to_datetime(x.get("date")))
        except Exception:
            daily_sorted = daily
        for d in daily_sorted[:7]:
            next7.append(formatar_prev_diaria(d))

    ctx = (analise.get("contexto_detectado") or {})
    event_type_final = (ctx.get("event_type") or EVENT_TYPE or "event")
    person_final = (PERSON_NAME or "")
    pet_final = (ctx.get("pet_name") or PET_NAME)

    try:
        mensagem = compose_human_message(
            data_evento=data_evento, event_type=event_type_final,
            person_name=person_final, pet_name=pet_final,
            hist=hist, decision=decisao
        )
    except Exception:
        mensagem = None

    return {
        "units": "us",
        "date": str(pd.to_datetime(data_evento).date()) if data_evento else None,
        "location": {"lat": lat, "lon": lon},
        "summary": summary,
        "recommendation": {
            "ok": bool(decisao.get("ok")),
            "reason": str(decisao.get("motivo", "")).strip()[:120],
            "message": mensagem
        },
        "next7days": next7,
        "forecast_source": prev.get("provider"),
        "history_source": hist.get("fonte") or analise.get("fonte_historico"),
    }
