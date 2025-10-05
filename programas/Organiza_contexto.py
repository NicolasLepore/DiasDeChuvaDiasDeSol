# combine_gldas_csvs.py
import pandas as pd
from pathlib import Path

IN_DIR = Path("outputs_gldas")
OUT_ALL_MULTI = IN_DIR / "all_multiindex.parquet"
OUT_ALL_FLAT  = IN_DIR / "all_flat.csv"
OUT_TIDY      = IN_DIR / "all_tidy.csv"
OUT_WIDE      = IN_DIR / "all_wide.csv"

def read_multi_csv(path: Path) -> pd.DataFrame:
    """
    Lê CSV gerado pelo pipeline (2 linhas de cabeçalho).
    Se não tiver MultiIndex (algum arquivo manual), cai no header normal.
    """
    try:
        df = pd.read_csv(path, header=[0,1])
    except Exception:
        df = pd.read_csv(path)
        # se vier simples, empacota em MultiIndex básico
        df.columns = pd.MultiIndex.from_tuples([("data", c) if c not in ("time","lat","lon") else ("coords", c) 
                                                for c in df.columns])
    return df

def flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Converte MultiIndex ('context','coords','data') para nomes com ponto: context.source, coords.time, data.Rainf_tavg."""
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = ["{}.{}".format(a,b) for (a,b) in df.columns]
    return df

def to_tidy(df: pd.DataFrame) -> pd.DataFrame:
    """
    Converte o DF (MultiIndex) para tidy:
    colunas fixas: time, lat?, lon?, source, mode, scope, var, unidade?
    valor: value
    """
    assert isinstance(df.columns, pd.MultiIndex), "Esperava MultiIndex de colunas"

    # separa blocos
    context_cols = [c for c in df.columns if c[0]=="context"]
    coords_cols  = [c for c in df.columns if c[0]=="coords"]
    data_cols    = [c for c in df.columns if c[0]=="data"]

    base = df.copy()

    # pega metadados úteis do contexto
    # scope = point_name ou bbox_name
    def get_col_safe(cols, name):
        col = ("context", name)
        return base[col] if col in cols else None

    source = base[("context","source")] if ("context","source") in base.columns else None
    mode   = base[("context","mode")]   if ("context","mode")   in base.columns else None
    point  = base[("context","point_name")] if ("context","point_name") in base.columns else None
    bboxn  = base[("context","bbox_name")]  if ("context","bbox_name")  in base.columns else None
    units  = base[("context","units")] if ("context","units") in base.columns else None

    # monta “scope” (nome do ponto ou bbox)
    scope = None
    if point is not None and bboxn is not None:
        scope = point.fillna(bboxn)
    elif point is not None:
        scope = point
    elif bboxn is not None:
        scope = bboxn

    # coords
    time_col = ("coords","time") if ("coords","time") in base.columns else None
    lat_col  = ("coords","lat")  if ("coords","lat")  in base.columns else None
    lon_col  = ("coords","lon")  if ("coords","lon")  in base.columns else None

    # empilha só as colunas de dados
    vals = base[data_cols].copy()
    vals.columns = [c[1] for c in vals.columns]  # só o nome da variável
    tidy = vals.melt(ignore_index=False, var_name="var", value_name="value").reset_index()

    # anexa colunas auxiliares
    if time_col: tidy["time"] = base[time_col].values
    if lat_col:  tidy["lat"]  = base[lat_col].values
    if lon_col:  tidy["lon"]  = base[lon_col].values
    if source is not None: tidy["source"] = source.values
    if mode   is not None: tidy["mode"]   = mode.values
    if scope  is not None: tidy["scope"]  = scope.values
    if units  is not None: tidy["units"]  = units.values

    # organiza ordem de colunas
    order = [c for c in ["time","lat","lon","source","mode","scope","var","units","value"] if c in tidy.columns]
    tidy = tidy[order]
    # tenta converter time pra datetime
    if "time" in tidy.columns:
        tidy["time"] = pd.to_datetime(tidy["time"], errors="coerce", utc=True)
    return tidy

def main():
    files = sorted(IN_DIR.glob("*.csv"))
    if not files:
        print("❌ Nenhum CSV encontrado em", IN_DIR)
        return

    dfs = []
    for f in files:
        df = read_multi_csv(f)
        dfs.append(df)

    # concatena mantendo MultiIndex
    df_all_multi = pd.concat(dfs, ignore_index=True)
    # normaliza time pra datetime
    if ("coords","time") in df_all_multi.columns:
        df_all_multi[("coords","time")] = pd.to_datetime(df_all_multi[("coords","time")], errors="coerce", utc=True)
        # ordena por tempo
        df_all_multi = df_all_multi.sort_values(("coords","time")).reset_index(drop=True)

    # salva multiindex em parquet (preserva índices e tipos)
    df_all_multi.to_parquet(OUT_ALL_MULTI, index=False)
    print("✅ all_multiindex.parquet salvo:", OUT_ALL_MULTI)

    # versão flatten (mais universal pra BI/Excel)
    df_all_flat = flatten_columns(df_all_multi)
    df_all_flat.to_csv(OUT_ALL_FLAT, index=False)
    print("✅ all_flat.csv salvo:", OUT_ALL_FLAT)

    # versão tidy (uma linha por observação)
    df_tidy = to_tidy(df_all_multi)
    df_tidy.to_csv(OUT_TIDY, index=False)
    print("✅ all_tidy.csv salvo:", OUT_TIDY)

    # exemplo de WIDE: índice=time, colunas= (mode, scope, var) e valores=value (média se duplicar)
    if not df_tidy.empty:
        has_scope = "scope" in df_tidy.columns
        cols = ["mode"]
        if has_scope: cols.append("scope")
        cols.append("var")

        wide = (df_tidy
                .pivot_table(index="time", columns=cols, values="value", aggfunc="mean"))
        wide = wide.sort_index()
        # salva
        wide.to_csv(OUT_WIDE)
        print("✅ all_wide.csv salvo:", OUT_WIDE)

if __name__ == "__main__":
    main()
