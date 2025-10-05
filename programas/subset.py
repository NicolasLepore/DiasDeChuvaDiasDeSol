from __future__ import annotations
import re, time
from urllib.parse import urlparse, parse_qs, unquote, urlsplit, urlunsplit
from pathlib import Path
from datetime import datetime, timedelta
from typing import List
import requests
import earthaccess as ea

def fix_gldas_url(u: str) -> str:
    u = re.sub(r"HTTP_s+er+v+ices\.cgi", "HTTP_services.cgi", u)
    u = u.replace("HTTP_service.cgi", "HTTP_services.cgi")
    return u

def prefer_data_host(u: str) -> str:
    parts = urlsplit(u)
    if "HTTP_services.cgi" in parts.path and parts.netloc != "data.gesdisc.earthdata.nasa.gov":
        parts = parts._replace(netloc="data.gesdisc.earthdata.nasa.gov")
        return urlunsplit(parts)
    return u

def autodiscover_subset_file(explicit: Path, root: Path) -> Path:
    if explicit and explicit.is_file():
        print(f"[OK] SUBSET_FILE: {explicit}")
        return explicit
    print(f"[AUTO] Procurando subset TXT em: {root}")
    patterns = ["subset_GLDAS*.txt", "*subset*GLDAS*.txt", "subset_*.txt"]
    cand: List[Path] = []
    for pat in patterns:
        cand += list(root.rglob(pat))
    if not cand:
        raise SystemExit("❌ subset TXT não encontrado.")
    cand.sort(key=lambda p: (p.stat().st_size, p.stat().st_mtime), reverse=True)
    print(f"[AUTO] Usando: {cand[0]}")
    return cand[0]

def read_links_from_txt(path: Path) -> list[str]:
    patt = re.compile(r"https?://\S+?\.nc4(?:\?\S+)?", re.I)
    links = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            links += patt.findall(line)
    out, seen = [], set()
    for u in links:
        u = prefer_data_host(fix_gldas_url(u))
        if u not in seen:
            seen.add(u)
            out.append(u)
    if not out:
        raise ValueError("Nenhum link .nc4 no subset TXT.")
    print(f"🔗 {len(out)} link(s) .nc4 encontrados. Ex.: {out[0]}")
    return out

def _try_fname_datetime(fname: str):
    m = re.search(r"A(\d{4})(\d{2})(\d{2})\.(\d{2})(\d{2})", fname)
    if not m: return None
    y, mo, da, hh, mm = map(int, m.groups())
    dt = datetime(y, mo, da, hh, mm)
    return y, int(dt.strftime("%j")), hh, mm

def parse_y_doy_hhmm_from_url(url: str) -> tuple[int,int,int,int]:
    p = urlparse(url)
    cand = _try_fname_datetime(Path(p.path).name)
    if cand: return cand
    qs = parse_qs(p.query)
    for key in ("LABEL", "label", "FILENAME", "filename"):
        vals = qs.get(key)
        if not vals: continue
        cand_name = Path(unquote(vals[0])).name
        cand = _try_fname_datetime(cand_name)
        if cand: return cand
    raise ValueError(f"Não consegui extrair data/hora: {url}")

def dt_from_year_doy(year: int, doy: int) -> datetime:
    return datetime(year, 1, 1) + timedelta(days=doy - 1)

def filter_links_for_event_window(links: list[str], data_evento: str, janela:int=1,
                                  anos=(2020,2021,2022,2023,2024)) -> list[str]:
    import pandas as pd
    target = pd.to_datetime(data_evento)
    md = (target.month, target.day)
    allow_dates = set()
    for y in anos:
        base = datetime(y, md[0], md[1])
        for d in range(-janela, janela+1):
            allow_dates.add((base + timedelta(days=d)).date())
    kept = []
    for u in links:
        try:
            y, doy, hh, mm = parse_y_doy_hhmm_from_url(u)
            dt = dt_from_year_doy(y, doy).date()
            if y in anos and dt in allow_dates:
                kept.append(u)
        except Exception:
            continue
    print(f"🎯 Filtro (±{janela}d, anos {anos}): {len(kept)} de {len(links)} links mantidos.")
    return kept

def derive_dest_name(url: str, for_direct: bool = False) -> str:
    invalid = '<>:"/\\|?*'
    def sanitize(s: str) -> str:
        for ch in invalid: s = s.replace(ch, "_")
        return s
    p = urlparse(url)
    if for_direct:
        base = Path(unquote(p.path)).name
        return sanitize(base if base.lower().endswith(".nc4") else base + ".nc4")
    qs = parse_qs(p.query)
    label = (qs.get("LABEL") or qs.get("label") or [None])[0]
    if label:
        cand = unquote(label)
        return sanitize(cand if cand.lower().endswith(".nc4") else cand + ".nc4")
    fn = (qs.get("FILENAME") or qs.get("filename") or [None])[0]
    if fn:
        base = Path(unquote(fn)).name
        return sanitize(base if base.lower().endswith(".nc4") else base + ".nc4")
    last = Path(p.path).name
    return sanitize(last + ".nc4")

def download_gldas(links: list[str], out_dir: Path, max_files: int) -> int:
    ea.login(strategy="environment", persist=True)
    sess = ea.get_requests_https_session()
    out_dir.mkdir(parents=True, exist_ok=True)
    total = len(links) if max_files == 0 else min(max_files, len(links))
    count = 0
    for raw_url in links[:total]:
        url = prefer_data_host(fix_gldas_url(raw_url))
        dest_name = derive_dest_name(url)
        dest = out_dir / dest_name
        if dest.exists():
            print(f"✅ Já existe: {dest.name}")
            continue
        print(f"⬇️ Baixando (OTF): {dest.name}")
        try:
            r = sess.get(url, stream=True, allow_redirects=True, timeout=300)
            if r.status_code >= 400:
                r.close()
                qs = parse_qs(urlparse(url).query)
                fn = (qs.get("FILENAME") or qs.get("filename") or [None])[0]
                if not fn:
                    raise requests.HTTPError(f"OTF {r.status_code} sem FILENAME.")
                direct = "https://data.gesdisc.earthdata.nasa.gov" + fn
                dest = out_dir / derive_dest_name(direct, for_direct=True)
                print(f"   ↪ OTF {r.status_code}. Direto: {direct}")
                r = sess.get(direct, stream=True, allow_redirects=True, timeout=600)
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_content(1024 * 1024):
                    if chunk: f.write(chunk)
            print(f"✔ Concluído: {dest.name}")
            count += 1
        except Exception as e:
            print(f"⚠️ Falha em {dest_name}: {e}")
        finally:
            try: r.close()
            except: pass
        time.sleep(0.5)
    print(f"🛰️ Total baixado nesta execução: {count}")
    return count
