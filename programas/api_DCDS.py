# api.py
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from datetime import date
from evento_meteo_assistente import avaliar_evento, montar_blocos_front, formatar_card_evento

app = FastAPI(title="Evento Meteo API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

class CardResponse(BaseModel):
    data: str | None
    local: dict
    resumo: dict
    recomendacao: dict

@app.get("/v1/card", response_model=CardResponse)
def get_card(lat: float, lon: float, data_evento: date, titulo: str | None = None):
    payload = avaliar_evento(lat, lon, str(data_evento), event_title=(titulo or ""))
    return formatar_card_evento(payload)

@app.get("/v1/blocos")
def get_blocos(lat: float, lon: float, data_evento: date, titulo: str | None = None, dias: int = 7):
    payload = avaliar_evento(lat, lon, str(data_evento), event_title=(titulo or ""))
    return montar_blocos_front(payload, limitar_dias=dias)
