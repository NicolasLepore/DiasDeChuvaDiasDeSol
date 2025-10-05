from __future__ import annotations
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

def _flag(name: str, default: str = "false") -> bool:
    return (os.getenv(name, default) or "").strip().lower() in ("1", "true", "yes", "y")

DATA_DIR      = Path(os.getenv("DATA_DIR", r"D:\NASA\programas\dados"))
SUBSET_FILE   = Path(os.getenv("SUBSET_FILE", "") or "")
GLDAS_RAW_DIR = DATA_DIR / os.getenv("GLDAS_RAW_SUBDIR", r"gldas\raw")
GLDAS_OUT_DIR = DATA_DIR / os.getenv("GLDAS_OUT_SUBDIR", r"gldas\out")

TIMEZONE      = os.getenv("TIMEZONE", "America/Sao_Paulo")
MAX_FILES     = int(os.getenv("MAX_FILES", "0"))

GOOGLE_WEATHER_API_KEY = (os.getenv("GOOGLE_WEATHER_API_KEY", "") or "").strip()

# IA (Ollama)
OLLAMA_ENABLE = _flag("OLLAMA_ENABLE", "false")
OLLAMA_MODEL  = os.getenv("OLLAMA_MODEL", "phi3")
OLLAMA_HOST   = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# contexto
EVENT_TYPE  = (os.getenv("EVENT_TYPE", "") or "").strip()
PERSON_NAME = (os.getenv("PERSON_NAME", "") or "").strip()
PET_NAME    = (os.getenv("PET_NAME", "") or "").strip()

# flags de saída
COMPACT_JSON    = _flag("COMPACT_JSON")
FRONT_MIN       = _flag("FRONT_MIN")
FRONT_BLOCKS    = _flag("FRONT_BLOCKS")
FRIENDLY_OUTPUT = _flag("FRIENDLY_OUTPUT")
FRIENDLY_STYLE  = (os.getenv("FRIENDLY_STYLE", "amigavel") or "amigavel").strip().lower()
MENTION_PET     = _flag("MENTION_PET")
PET_FROM_TITLE  = _flag("PET_FROM_TITLE")
FREE_EVENT_MODE = _flag("FREE_EVENT_MODE")
REC_VERBOSE     = _flag("REC_VERBOSE", "true")

# thresholds decisão
TH_PPROB = int(os.getenv("TH_PPROB", "50"))
TH_PMM   = float(os.getenv("TH_PMM", "10"))
TH_TMAX  = float(os.getenv("TH_TMAX", "35"))
TH_WIND  = float(os.getenv("TH_WIND", "40"))
TH_VIS   = float(os.getenv("TH_VIS", "5"))
TH_HRAIN = float(os.getenv("TH_HRAIN", "10"))
TH_HTEMP = float(os.getenv("TH_HTEMP", "30"))

# garantir diretórios
for p in (DATA_DIR, GLDAS_RAW_DIR, GLDAS_OUT_DIR):
    p.mkdir(parents=True, exist_ok=True)
