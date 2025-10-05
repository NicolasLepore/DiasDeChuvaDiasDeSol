# api.py
# API fina para servir o output do evento_meteo_assistente.py
# Requisitos:
#   pip install fastapi uvicorn[standard] python-dotenv
# Execução:
#   uvicorn api:app --host 0.0.0.0 --port 8000 --reload

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Literal, Any, Dict
import os
from datetime import date
from pathlib import Path

# importa seu módulo (o arquivo que você já tem)
import evento_V4 as core

# ---------- CORS (ajuste a origem do seu front) ----------
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app = FastAPI(title="NASA Hackathon Weather Event API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in ALLOWED_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Normalizador/Validador de payload ----------
# Corrige typos do JSON (ex.: 'reaason' -> 'reason', etc.) e limpa um '{' solto.
def _fix_typos_in_blocks(payload: Dict[str, Any]) -> Dict[str, Any]:
    # corrige card.recommendation.reason
    card = payload.get("card") or {}
    rec = card.get("recommendation") or {}
    if "reaason" in rec and "reason" not in rec:
        rec["reason"] = rec.pop("reaason")
    card["recommendation"] = rec
    payload["card"] = card

    # corrige days7 array
    days = payload.get("days7") or []
    fixed = []
    for d in days:
        if not isinstance(d, dict):
            continue
        # typos vistos no dump
        if "tmaaxF" in d and "tmaxF" not in d:
            d["tmaxF"] = d.pop("tmaaxF")
        if "actiivityIndex" in d and "activityIndex" not in d:
            d["activityIndex"] = d.pop("actiivityIndex")
        if "preecipIn" in d and "precipIn" not in d:
            d["precipIn"] = d.pop("preecipIn")
        if "preecipProbPct" in d and "precipProbPct" not in d:
            d["precipProbPct"] = d.pop("preecipProbPct")
        if "ddate" in d and "date" not in d:
            d["date"] = d.pop("ddate")
        fixed.append(d)
    payload["days7"] = fixed

    return payload

def _fix_typos_in_card(payload: Dict[str, Any]) -> Dict[str, Any]:
    rec = payload.get("recommendation") or {}
    if "reaason" in rec and "reason" not in rec:
        rec["reason"] = rec.pop("reaason")
    payload["recommendation"] = rec
    return payload

def normalize_payload(format_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Garante consistência do JSON de acordo com o formato escolhido.
    format_name: 'blocks' | 'card' | 'friendly' | 'full' | 'compact'
    """
    if format_name == "blocks":
        return _fix_typos_in_blocks(data)
    if format_name == "card":
        return _fix_typos_in_card(data)
    return data

# ---------- Modelos de entrada ----------
class EventQuery(BaseModel):
    lat: float = Field(..., description="Latitude (decimal degrees)")
    lon: float = Field(..., description="Longitude (decimal degrees)")
    date: date = Field(..., description="Event date (YYYY-MM-DD)")
    title: Optional[str] = Field(None, description="Optional event title")
    # formato de saída, casando com seus flags: blocks | card | friendly | compact | full
    output: Literal["blocks", "card", "friendly", "compact", "full"] = "blocks"
    # timezone opcional
    timezone: Optional[str] = Field(None, description="IANA timezone, e.g. America/New_York")

# ---------- Rota principal ----------
@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/event")
def event_endpoint(q: EventQuery):
    # roda seu núcleo
    res = core.avaliar_evento(
        lat=q.lat,
        lon=q.lon,
        data_evento=str(q.date),
        event_title=q.title,
        timezone=q.timezone or os.getenv("TIMEZONE", "America/Sao_Paulo"),
        subset_txt=Path(os.getenv("SUBSET_FILE",  "") or core.SUBSET_FILE),
        gldas_raw_dir=Path(os.getenv("GLDAS_RAW_SUBDIR", str(core.GLDAS_RAW_DIR))),
        max_files=core.MAX_FILES,
        janela_hist=1,
    )

    # seleciona o formato de saída (espelhando seus flags, mas via API)
    if q.output == "compact":
        payload = res.get("analise_evento", {}).get("decisao_binaria", {"ok": False, "motivo": "insufficient data"})
    elif q.output == "blocks":
        payload = core.montar_blocos_front(res)
        payload = normalize_payload("blocks", payload)
    elif q.output == "card":
        payload = core.formatar_card_evento(res)
        payload = normalize_payload("card", payload)
    elif q.output == "friendly":
        payload = core.formatar_bem_amigavel(res)
    else:  # "full"
        payload = res

    return payload
