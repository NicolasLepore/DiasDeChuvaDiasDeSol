import os, json, sys
from evento_V4 import avaliar_evento, formatar_card_evento, montar_blocos_front, formatar_bem_amigavel
from evento_V4.config import COMPACT_JSON, FRONT_MIN, FRONT_BLOCKS, FRIENDLY_OUTPUT

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

LAT = float(os.getenv("LAT", "-23.62"))
LON = float(os.getenv("LON", "-46.55"))
DATA_EVENTO = os.getenv("TARGET_DATE", "2025-10-07")
EVENT_TITLE = os.getenv("EVENT_TITLE", "")

# CLI flags
if any(a in ("--compact","-c") for a in sys.argv[1:]): compact = True
else: compact = COMPACT_JSON
if any(a in ("--min","--card") for a in sys.argv[1:]): front_min = True
else: front_min = FRONT_MIN
if any(a in ("--blocks","--blocos") for a in sys.argv[1:]): front_blocks = True
else: front_blocks = FRONT_BLOCKS
if any(a in ("--friendly","--amigavel") for a in sys.argv[1:]): friendly = True
else: friendly = FRIENDLY_OUTPUT

res = avaliar_evento(LAT, LON, DATA_EVENTO, event_title=EVENT_TITLE)

if compact:
    payload = res.get("analise_evento", {}).get("decisao_binaria", {"ok": False, "motivo": "insufficient data"})
    print(json.dumps(payload, ensure_ascii=False))
elif front_blocks:
    print(json.dumps(montar_blocos_front(res), ensure_ascii=False))
elif front_min:
    print(json.dumps(formatar_card_evento(res), ensure_ascii=False))
elif friendly:
    print(json.dumps(formatar_bem_amigavel(res), ensure_ascii=False))
else:
    print(json.dumps(res, ensure_ascii=False, indent=2))
