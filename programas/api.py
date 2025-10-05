from datetime import date
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from meteo_event import avaliar_evento, formatar_card_evento, montar_blocos_front, formatar_bem_amigavel
import os

app = FastAPI(title="Evento Meteo API", version="1.0.0")
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware, allow_origins=CORS_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

class CardResponse(BaseModel):
    data: Optional[str] = None
    local: Dict[str, Any] | None = None  # compat com versões antigas — se não usar, remova
    resumo: Dict[str, Any] | None = None
    recomendacao: Dict[str, Any] | None = None

class BlocosResponse(BaseModel):
    card: Dict[str, Any]
    days7: List[Dict[str, Any]]
    meta: Dict[str, Any]

@app.exception_handler(Exception)
async def _unhandled(request, exc):
    return JSONResponse(status_code=500, content={"ok": False, "error": str(exc)})

@app.get("/health")
def health(): return {"ok": True}

@app.get("/v1/card")
def get_card(lat: float, lon: float, data_evento: date, titulo: Optional[str] = None):
    try:
        payload = avaliar_evento(lat, lon, str(data_evento), event_title=(titulo or ""))
        return formatar_card_evento(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/blocos")
def get_blocos(lat: float, lon: float, data_evento: date, titulo: Optional[str] = None, dias: int = 7):
    try:
        payload = avaliar_evento(lat, lon, str(data_evento), event_title=(titulo or ""))
        return montar_blocos_front(payload, limitar_dias=dias)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/amigavel")
def get_amigavel(lat: float, lon: float, data_evento: date, titulo: Optional[str] = None):
    try:
        payload = avaliar_evento(lat, lon, str(data_evento), event_title=(titulo or ""))
        return formatar_bem_amigavel(payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host=os.getenv("HOST","127.0.0.1"), port=int(os.getenv("PORT","8000")), reload=True)
