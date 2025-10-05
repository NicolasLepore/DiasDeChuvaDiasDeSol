from __future__ import annotations
import os, shlex, subprocess, json, re
from typing import Dict, Any, Optional
from .config import OLLAMA_ENABLE, OLLAMA_MODEL, OLLAMA_HOST, MENTION_PET

def _ollama_run(model: str, prompt: str, host: str = OLLAMA_HOST, timeout: int = 30) -> str:
    cmd = f'ollama run {shlex.quote(model)} {shlex.quote(prompt)}'
    try:
        proc = subprocess.run(
            cmd, shell=True, capture_output=True, text=False, timeout=timeout,
            env={**os.environ, "OLLAMA_HOST": host},
        )
        stdout = (proc.stdout or b"").decode("utf-8", errors="replace")
        stderr = (proc.stderr or b"").decode("utf-8", errors="replace")
        if proc.returncode != 0:
            raise RuntimeError(stderr.strip() or "Falha desconhecida no Ollama.")
        return stdout.strip()
    except Exception as e:
        return f"[Ollama erro] {e}"

def gerar_recomendacao_contextual_ollama(hist: Dict[str,Any], prev: Optional[Dict[str,Any]],
                                         data_evento: str, evento_tipo: str, person_name: str,
                                         pet_name: str, mensagem_fallback: str, model: str = OLLAMA_MODEL) -> Dict[str, Any]:
    # pega item do dia
    import pandas as pd
    def _pega_prev_no_dia(prev, data_evento):
        if not prev or not prev.get("ok"): return None
        try:
            de = pd.to_datetime(data_evento).date()
            return next((d for d in prev["daily"] if pd.to_datetime(d["date"]).date() == de), None)
        except Exception: return None
    item_prev = _pega_prev_no_dia(prev, data_evento)
    contexto = {
        "data_evento": str(pd.to_datetime(data_evento).date()),
        "evento_tipo": evento_tipo or "event",
        "person_name": person_name or "",
        "pet_name": (pet_name or "") if MENTION_PET else "",
        "historico": {
            "temp_mean_c": (hist.get("temp_mean_c") or {}).get("mean"),
            "rain_mm_day": (hist.get("rain_mm_day") or {}).get("mean"),
            "resumo": hist.get("resumo"),
        },
        "previsao_dia": item_prev or {},
    }
    instrucoes = (
        "Responda SOMENTE com um JSON de UM objeto (sem texto extra), assim:\n"
        '{"ok": true|false, "motivo": "up to 8 words", "mensagem": "up to 220 characters in ENGLISH"}\n'
        "Regras ok=false: (prob_chuva>=50 ou chuva_mm>=10) OU (tmax>=35 ou sensacao_max>=35) "
        "OU (vento_max>=40) OU (vis_km<=5)."
    )
    prompt = f"INSTRUCOES:\n{instrucoes}\n\nCONTEXTO:\n{json.dumps(contexto, ensure_ascii=False)}\n\nRESPOSTA:"
    raw = _ollama_run(model, prompt).strip().strip("`").strip()
    m = re.search(r"\{[^{}]*\}", raw, flags=re.S)
    if not m:
        return {"ok": True, "motivo": "favorable conditions", "mensagem": mensagem_fallback}
    try:
        obj = json.loads(m.group(0))
        ok = bool(obj.get("ok"))
        motivo = str(obj.get("motivo","")).strip() or ("favorable conditions" if ok else "unfavorable conditions")
        mensagem = str(obj.get("mensagem","")).strip() or mensagem_fallback
        if len(mensagem) > 220: mensagem = mensagem[:220].rstrip()
        return {"ok": ok, "motivo": motivo, "mensagem": mensagem}
    except Exception:
        return {"ok": True, "motivo": "favorable conditions", "mensagem": mensagem_fallback}
