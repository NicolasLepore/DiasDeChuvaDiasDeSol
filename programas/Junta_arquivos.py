# -*- coding: utf-8 -*-
"""
GLDAS -> DataFrames com MultiIndex (context/coords/data)
- Autentica via .env (earthaccess)
- Abre via OPeNDAP (testa endpoints) ou baixa autenticado (fallback)
- Gera CSVs: ponto, média de área, grade recorte e multi-variáveis
- Corrigido: latitude ascendente, dtype numérico, resample numeric_only
- Inclui CSV extra: chuva diária acumulada (a partir de Rainf_tavg)
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import xarray as xr
from dotenv import load_dotenv
import earthaccess as ea

# =========================
# ====== CONFIG GERAL =====
# =========================

# Arquivo alvo (exemplo do seu teste)
DATA_URL = (
    "https://data.gesdisc.earthdata.nasa.gov/data/GLDAS/"
    "GLDAS_NOAH025_3H.2.1/2020/182/GLDAS_NOAH025_3H.A20200630.0900.021.nc4"
)

# Candidatos OPeNDAP (ordem de tentativa)
OPENDAP_CANDIDATES = [
    "https://data.gesdisc.earthdata.nasa.gov/opendap/GLDAS/GLDAS_NOAH025_3H.2.1/2020/182/GLDAS_NOAH025_3H.A20200630.0900.021.nc4",
    "https://hydro1.gesdisc.eosdis.nasa.gov/opendap/GLDAS/GLDAS_NOAH025_3H.2.1/2020/182/GLDAS_NOAH025_3H.A20200630.0900.021.nc4",
    "https://hydro1.gesdisc.eosdis.nasa.gov/dods/GLDAS/GLDAS_NOAH025_3H.2.1/2020/182/GLDAS_NOAH025_3H.A20200630.0900.021.nc4",
]

# Variáveis de interesse (ajuste à vontade)
VARS = [
    "Rainf_tavg",       # chuva (kg m-2 s-1) ~ mm/s
    "Tair_f_inst",      # temperatura do ar (K)
    "SWdown_f_tavg"     # radiação de onda curta incidente (W m-2)
]

# Ponto (ex.: São Paulo)
POINT = {"name": "SaoPaulo", "lat": -23.55, "lon": -46.63}

# Bounding box (ex.: RMSP aproximada)
BBOX = {
    "name": "RMSP",
    "lat_min": -24.2,
    "lat_max": -23.2,
    "lon_min": -47.2,
    "lon_max": -46.2,
}

# Reamostragem temporal (None para desativar) — ex.: "1D"
RESAMPLE = "1D"

# Pasta de saída
OUTDIR = Path("outputs_gldas")
OUTDIR.mkdir(exist_ok=True)


# =========================
# ====== FUNÇÕES BASE =====
# =========================

def login_via_env():
    load_dotenv()
    user = os.getenv("EARTHDATA_USERNAME")
    pwd = os.getenv("EARTHDATA_PASSWORD")
    if not user or not pwd:
        sys.exit("❌ Defina EARTHDATA_USERNAME e EARTHDATA_PASSWORD no .env")
    ea.login(strategy="environment", persist=True)
    return ea.get_requests_https_session()


def probe_dds(session, url):
    """Verifica se o endpoint OPeNDAP responde ao .dds (metadados)."""
    import requests
    dds = url + ".dds" if not url.endswith(".dds") else url
    try:
        r = session.get(dds, timeout=20)
        r.raise_for_status()
        return True
    except Exception:
        return False


def open_dataset_streaming(session):
    """Tenta abrir via OPeNDAP (pydap). Testa https e dap4+https."""
    for url in OPENDAP_CANDIDATES:
        if not probe_dds(session, url):
            print(f"[OPeNDAP] .dds não disponível: {url}")
            continue

        try:
            ds = xr.open_dataset(url, engine="pydap", backend_kwargs={"session": session})
            print(f"[OPeNDAP] SUCESSO em: {url}")
            return ds, url
        except Exception as e1:
            print(f"[OPeNDAP] Falhou abrir (https): {url} -> {type(e1).__name__}: {e1}")

        # tenta dap4
        dap4_url = url.replace("https://", "dap4+https://")
        try:
            ds = xr.open_dataset(dap4_url, engine="pydap", backend_kwargs={"session": session})
            print(f"[OPeNDAP] SUCESSO em (DAP4): {dap4_url}")
            return ds, dap4_url
        except Exception as e2:
            print(f"[OPeNDAP] Falhou abrir (DAP4): {dap4_url} -> {type(e2).__name__}: {e2}")

    return None, None


def download_and_open():
    """Baixa autenticado e abre localmente (fallback garantido)."""
    local = ea.download(DATA_URL, local_path=str(OUTDIR))[0]
    ds = xr.open_dataset(local)
    print(f"[Local] SUCESSO ao abrir: {local}")
    return ds, local


def normalize_dataset(ds, vars_list):
    """Padroniza lat ascendente, decodifica CF e força dtype numérico das variáveis."""
    # decodifica CF (times como datetime, etc.)
    ds = xr.decode_cf(ds, use_cftime=False)

    # ordenar lat/lon para ascendente
    if "lat" in ds and ds.lat.size > 1 and ds.lat[0] > ds.lat[-1]:
        ds = ds.sortby("lat")
    if "lon" in ds and ds.lon.size > 1 and ds.lon[0] > ds.lon[-1]:
        ds = ds.sortby("lon")

    # garantir dtype numérico
    for v in vars_list:
        if v in ds:
            if ds[v].dtype == "O" or (not np.issubdtype(ds[v].dtype, np.number)):
                ds[v] = ds[v].astype("float32")

    return ds


def with_context_blocks(df, context: dict):
    """
    Retorna DataFrame com colunas MultiIndex:
    - ('context', <...>), ('coords', <time|lat|lon>), ('data', <variável>)
    """
    ctx_df = pd.DataFrame({k: [v] * len(df) for k, v in context.items()})

    def mkcols(prefix, cols):
        return pd.MultiIndex.from_tuples([(prefix, c) for c in cols])

    cols = list(df.columns)
    coords = [c for c in cols if c in ("time", "lat", "lon")]
    data_cols = [c for c in cols if c not in coords]

    df_coords = df[coords] if coords else pd.DataFrame(index=df.index)
    df_data = df[data_cols] if data_cols else pd.DataFrame(index=df.index)

    df_coords.columns = mkcols("coords", list(df_coords.columns))
    df_data.columns = mkcols("data", list(df_data.columns))
    ctx_df.columns = mkcols("context", list(ctx_df.columns))

    out = pd.concat([ctx_df, df_coords, df_data], axis=1)
    return out


def maybe_convert_units(df, varname):
    """Conversões úteis (ex.: chuva mm/h) adicionando coluna ('data', f'{var}_mm_h')."""
    df = df.copy()
    if isinstance(df.columns, pd.MultiIndex):
        # achar coluna de dados
        if ("data", varname) in df.columns and varname == "Rainf_tavg":
            df[("data", f"{varname}_mm_h")] = df[("data", varname)] * 3600.0
    else:
        if varname in df.columns and varname == "Rainf_tavg":
            df[f"{varname}_mm_h"] = df[varname] * 3600.0
    return df


def maybe_resample_mean(df, rule):
    """Reamostra com média (apenas colunas numéricas)."""
    if rule is None:
        return df
    df = df.copy()
    # identificar coluna tempo
    time_col = ("coords", "time") if isinstance(df.columns, pd.MultiIndex) else "time"
    if time_col not in df.columns:
        return df
    df = df.set_index(time_col, drop=True)
    df.index.name = "time"
    df = df.resample(rule).mean(numeric_only=True).reset_index()
    if isinstance(df.columns, pd.MultiIndex):
        # garantir ('coords','time') no retorno
        new_cols = []
        for c in df.columns:
            if c == "time":
                new_cols.append(("coords", "time"))
            elif isinstance(c, tuple) and len(c) == 2:
                new_cols.append(c)
            else:
                new_cols.append(("data", c))
        df.columns = pd.MultiIndex.from_tuples(new_cols)
    return df


def resample_precip_sum(df, rule, input_col=("data", "Rainf_tavg_mm_h"), hours_per_step=3.0):
    """
    Para chuva: soma no período.
    Converte mm/h (taxa média por passo) para mm do passo multiplicando por hours_per_step (GLDAS 3-hourly).
    Cria ('data','Rainf_tavg_mm_period_mm') e retorna reamostrado com soma (numeric_only).
    """
    if rule is None:
        return df
    df = df.copy()
    # identificar coluna tempo
    time_col = ("coords", "time") if isinstance(df.columns, pd.MultiIndex) else "time"
    if time_col not in df.columns:
        return df
    # só procede se tiver a coluna de mm/h
    if input_col not in df.columns:
        return df

    df = df.set_index(time_col, drop=True)
    df.index.name = "time"
    df[("data", "Rainf_tavg_mm_period_mm")] = df[input_col] * float(hours_per_step)
    out = df.resample(rule).sum(numeric_only=True).reset_index()

    if isinstance(out.columns, pd.MultiIndex):
        new_cols = []
        for c in out.columns:
            if c == "time":
                new_cols.append(("coords", "time"))
            elif isinstance(c, tuple) and len(c) == 2:
                new_cols.append(c)
            else:
                new_cols.append(("data", c))
        out.columns = pd.MultiIndex.from_tuples(new_cols)
    return out


# =========================
# ====== PIPE DE DFS ======
# =========================

def df_point_timeseries(ds, var, point):
    da = ds[var].sel(lat=point["lat"], lon=point["lon"], method="nearest").astype("float32")
    df = da.to_dataframe(name=var).reset_index()  # time, lat, lon, var
    df = with_context_blocks(df, {
        "source": "GLDAS_NOAH025_3H_v2.1",
        "var": var,
        "mode": "point",
        "point_name": point["name"],
        "units": str(getattr(da, "units", "")),
    })
    df = maybe_convert_units(df, var)
    df_mean = maybe_resample_mean(df, RESAMPLE)  # média (geral)
    return df, df_mean  # retorna bruto + reamostrado


def df_area_mean_timeseries(ds, var, bbox):
    lat_min, lat_max = bbox["lat_min"], bbox["lat_max"]
    lon_min, lon_max = bbox["lon_min"], bbox["lon_max"]
    da = ds[var].sel(lat=slice(lat_min, lat_max), lon=slice(lon_min, lon_max)).astype("float32")
    da_mean = da.mean(dim=("lat", "lon"), skipna=True)
    df = da_mean.to_dataframe(name=var).reset_index()  # time, var
    df = with_context_blocks(df, {
        "source": "GLDAS_NOAH025_3H_v2.1",
        "var": var,
        "mode": "area_mean",
        "bbox_name": bbox["name"],
        "bbox": f"{lat_min},{lat_max},{lon_min},{lon_max}",
        "units": str(getattr(da, "units", "")),
    })
    df = maybe_convert_units(df, var)
    df_mean = maybe_resample_mean(df, RESAMPLE)
    return df, df_mean


def df_grid_subset(ds, var, bbox):
    lat_min, lat_max = bbox["lat_min"], bbox["lat_max"]
    lon_min, lon_max = bbox["lon_min"], bbox["lon_max"]
    da = ds[var].sel(lat=slice(lat_min, lat_max), lon=slice(lon_min, lon_max)).astype("float32")
    df = da.to_dataframe(name=var).reset_index()  # time, lat, lon, var
    df = with_context_blocks(df, {
        "source": "GLDAS_NOAH025_3H_v2.1",
        "var": var,
        "mode": "grid_subset",
        "bbox_name": bbox["name"],
        "bbox": f"{lat_min},{lat_max},{lon_min},{lon_max}",
        "units": str(getattr(da, "units", "")),
    })
    # normalmente não reamostramos grade completa, mas pode aplicar:
    df_mean = maybe_resample_mean(df, RESAMPLE) if RESAMPLE else df
    df = maybe_convert_units(df, var)
    df_mean = maybe_convert_units(df_mean, var)
    return df, df_mean


def df_multi_point(ds, vars_, point):
    subset = ds[vars_].sel(lat=point["lat"], lon=point["lon"], method="nearest").astype("float32")
    df = subset.to_dataframe().reset_index()  # time, lat, lon, vars...
    df = with_context_blocks(df, {
        "source": "GLDAS_NOAH025_3H_v2.1",
        "vars": ",".join(vars_),
        "mode": "multi_point",
        "point_name": point["name"],
    })
    for v in vars_:
        df = maybe_convert_units(df, v)
    df_mean = maybe_resample_mean(df, RESAMPLE)
    return df, df_mean


def df_multi_area_mean(ds, vars_, bbox):
    lat_min, lat_max = bbox["lat_min"], bbox["lat_max"]
    lon_min, lon_max = bbox["lon_min"], bbox["lon_max"]
    subset = ds[vars_].sel(lat=slice(lat_min, lat_max), lon=slice(lon_min, lon_max)).astype("float32")
    meaned = subset.mean(dim=("lat", "lon"), skipna=True)
    df = meaned.to_dataframe().reset_index()  # time, vars...
    df = with_context_blocks(df, {
        "source": "GLDAS_NOAH025_3H_v2.1",
        "vars": ",".join(vars_),
        "mode": "multi_area_mean",
        "bbox_name": bbox["name"],
        "bbox": f"{lat_min},{lat_max},{lon_min},{lon_max}",
    })
    for v in vars_:
        df = maybe_convert_units(df, v)
    df_mean = maybe_resample_mean(df, RESAMPLE)
    return df, df_mean


# =========================
# ========= MAIN ==========
# =========================

def main():
    session = login_via_env()

    # tenta streaming
    ds, used_url = open_dataset_streaming(session)
    if ds is None:
        print("[INFO] OPeNDAP indisponível. Usando fallback local (download).")
        ds, used_url = download_and_open()
    else:
        print(f"[INFO] Dataset aberto via: {used_url}")

    # normalização: lat asc, dtype numérico, decode_cf
    ds = normalize_dataset(ds, VARS)

    print("Variáveis disponíveis:", list(ds.data_vars))

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    # 1) ponto (uma variável por vez)
    for v in VARS:
        try:
            df_raw, df_mean = df_point_timeseries(ds, v, POINT)
            out_raw = OUTDIR / f"{ts}_{v}_{POINT['name']}_point_raw.csv"
            out_mean = OUTDIR / f"{ts}_{v}_{POINT['name']}_point_{RESAMPLE or 'noresample'}.csv"
            df_raw.to_csv(out_raw, index=False)
            df_mean.to_csv(out_mean, index=False)
            print(f"[OK] Ponto -> {out_raw.name}, {out_mean.name}")

            # Se for chuva, gera também acumulado diário (mm)
            if v == "Rainf_tavg" and RESAMPLE:
                df_acc = resample_precip_sum(df_raw, RESAMPLE, input_col=("data","Rainf_tavg_mm_h"), hours_per_step=3.0)
                out_acc = OUTDIR / f"{ts}_{v}_{POINT['name']}_point_{RESAMPLE}_sum_mm.csv"
                df_acc.to_csv(out_acc, index=False)
                print(f"[OK] Ponto chuva acumulada -> {out_acc.name}")

        except Exception as e:
            print(f"[WARN] falhou ponto {v}: {e}")

    # 2) média na área (uma variável por vez)
    for v in VARS:
        try:
            df_raw, df_mean = df_area_mean_timeseries(ds, v, BBOX)
            out_raw = OUTDIR / f"{ts}_{v}_{BBOX['name']}_area_mean_raw.csv"
            out_mean = OUTDIR / f"{ts}_{v}_{BBOX['name']}_area_mean_{RESAMPLE or 'noresample'}.csv"
            df_raw.to_csv(out_raw, index=False)
            df_mean.to_csv(out_mean, index=False)
            print(f"[OK] Área média -> {out_raw.name}, {out_mean.name}")

            # chuva acumulada na área
            if v == "Rainf_tavg" and RESAMPLE:
                df_acc = resample_precip_sum(df_raw, RESAMPLE, input_col=("data","Rainf_tavg_mm_h"), hours_per_step=3.0)
                out_acc = OUTDIR / f"{ts}_{v}_{BBOX['name']}_area_mean_{RESAMPLE}_sum_mm.csv"
                df_acc.to_csv(out_acc, index=False)
                print(f"[OK] Área chuva acumulada -> {out_acc.name}")

        except Exception as e:
            print(f"[WARN] falhou area_mean {v}: {e}")

    # 3) grade recortada (uma variável por vez)
    for v in VARS:
        try:
            df_raw, df_mean = df_grid_subset(ds, v, BBOX)
            out_raw = OUTDIR / f"{ts}_{v}_{BBOX['name']}_grid_subset_raw.csv"
            df_raw.to_csv(out_raw, index=False)
            # (opcional) salvar o reamostrado também
            if RESAMPLE:
                out_mean = OUTDIR / f"{ts}_{v}_{BBOX['name']}_grid_subset_{RESAMPLE}.csv"
                df_mean.to_csv(out_mean, index=False)
                print(f"[OK] Grid subset -> {out_raw.name}, {out_mean.name}")
            else:
                print(f"[OK] Grid subset -> {out_raw.name}")

        except Exception as e:
            print(f"[WARN] falhou grid_subset {v}: {e}")

    # 4) multi-variáveis (ponto + área mean)
    try:
        df_raw, df_mean = df_multi_point(ds, VARS, POINT)
        out_raw = OUTDIR / f"{ts}_MULTI_{POINT['name']}_point_raw.csv"
        out_mean = OUTDIR / f"{ts}_MULTI_{POINT['name']}_point_{RESAMPLE or 'noresample'}.csv"
        df_raw.to_csv(out_raw, index=False)
        df_mean.to_csv(out_mean, index=False)
        print(f"[OK] Multi Point -> {out_raw.name}, {out_mean.name}")

        # chuva acumulada multi (se existir)
        if ("data","Rainf_tavg_mm_h") in df_raw.columns and RESAMPLE:
            df_acc = resample_precip_sum(df_raw, RESAMPLE, input_col=("data","Rainf_tavg_mm_h"), hours_per_step=3.0)
            out_acc = OUTDIR / f"{ts}_MULTI_{POINT['name']}_point_{RESAMPLE}_sum_mm.csv"
            df_acc.to_csv(out_acc, index=False)
            print(f"[OK] Multi Point chuva acumulada -> {out_acc.name}")

    except Exception as e:
        print(f"[WARN] falhou multi_point: {e}")

    try:
        df_raw, df_mean = df_multi_area_mean(ds, VARS, BBOX)
        out_raw = OUTDIR / f"{ts}_MULTI_{BBOX['name']}_area_mean_raw.csv"
        out_mean = OUTDIR / f"{ts}_MULTI_{BBOX['name']}_area_mean_{RESAMPLE or 'noresample'}.csv"
        df_raw.to_csv(out_raw, index=False)
        df_mean.to_csv(out_mean, index=False)
        print(f"[OK] Multi Area Mean -> {out_raw.name}, {out_mean.name}")

        if ("data","Rainf_tavg_mm_h") in df_raw.columns and RESAMPLE:
            df_acc = resample_precip_sum(df_raw, RESAMPLE, input_col=("data","Rainf_tavg_mm_h"), hours_per_step=3.0)
            out_acc = OUTDIR / f"{ts}_MULTI_{BBOX['name']}_area_mean_{RESAMPLE}_sum_mm.csv"
            df_acc.to_csv(out_acc, index=False)
            print(f"[OK] Multi Area chuva acumulada -> {out_acc.name}")

    except Exception as e:
        print(f"[WARN] falhou multi_area_mean: {e}")

    print("\n✅ Finalizado. Arquivos em:", OUTDIR.resolve())


if __name__ == "__main__":
    main()
