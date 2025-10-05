from __future__ import annotations
from typing import Dict, Any
from .config import TH_PPROB, TH_PMM, TH_TMAX, TH_WIND, TH_VIS, TH_HRAIN, TH_HTEMP

def decide_passeio_curto(hist: dict, prev: dict | None, data_evento: str, evento_tipo: str = "passeio") -> Dict[str, Any]:
    def _pega_prev_no_dia(prev, data_evento):
        import pandas as pd
        if not prev or not prev.get("ok"): return None
        try:
            de = pd.to_datetime(data_evento).date()
            return next((d for d in prev["daily"] if pd.to_datetime(d["date"]).date() == de), None)
        except Exception:
            return None

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
