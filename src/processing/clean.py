"""
Limpeza e transformação dos dados brutos de cada fonte.
"""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parents[2]))
from src.config import CULTURAS, PATH_RAW_INMET, RM_UF_MAP


# ── INMET ────────────────────────────────────────────────────────────────────

def _ler_uf_do_header(csv_path: Path) -> str:
    """Extrai a sigla da UF das 8 linhas de metadado do CSV do INMET."""
    try:
        header = pd.read_csv(
            csv_path, sep=";", nrows=8, header=None,
            encoding="latin-1", on_bad_lines="skip",
        )
        # Linha 1 (índice 1) contém "UF:;<SIGLA>"
        uf = str(header.iloc[1, 1]).strip().upper()
        if re.match(r"^[A-Z]{2}$", uf):
            return uf
    except Exception:
        pass
    return ""


def _ler_dados_estacao(csv_path: Path, uf: str) -> pd.DataFrame | None:
    """Lê os dados horários de uma estação e retorna DataFrame diário."""
    try:
        df = pd.read_csv(
            csv_path,
            sep=";",
            skiprows=8,
            decimal=",",
            encoding="latin-1",
            na_values=["-9999", "-9999.0", ""],
            on_bad_lines="skip",
        )
    except Exception:
        return None

    if df.empty or df.shape[1] < 3:
        return None

    # Identificar colunas por palavras-chave (nomes variam levemente entre anos)
    col_map = {}
    for col in df.columns:
        c = col.strip().upper()
        # Coluna de data: "Data" (2016+) ou "DATA (YYYY-MM-DD)" em formatos antigos
        if c == "DATA" or (c.startswith("DATA") and "HORA" not in c and "FUND" not in c):
            if "data" not in col_map:
                col_map["data"] = col
        elif "PRECIPITA" in c and "TOTAL" in c:
            col_map["chuva"] = col
        elif "TEMPERATURA DO AR" in c and "BULBO SECO" in c:
            col_map["temp"] = col

    if "data" not in col_map:
        return None

    df = df.rename(columns={v: k for k, v in col_map.items()})
    df["uf"] = uf

    cols = ["data", "uf"] + [c for c in ("chuva", "temp") if c in df.columns]
    df = df[cols].copy()

    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    for c in ("chuva", "temp"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    df = df.dropna(subset=["data"])

    # Agrega para diário por estação (chuva=soma, temp=média)
    agg = {"uf": "first"}
    if "chuva" in df.columns:
        agg["chuva"] = "sum"
    if "temp" in df.columns:
        agg["temp"] = "mean"

    df_dia = df.groupby("data").agg(agg).reset_index()
    return df_dia


def clean_inmet(anos: list[int] | None = None) -> pd.DataFrame:
    """
    Lê todos os CSVs das estações INMET e retorna série mensal por UF.

    Retorna colunas: uf, ano, mes, chuva_mm, temp_c
    """
    from src.config import ANOS
    if anos is None:
        anos = ANOS

    frames = []
    for ano in anos:
        pasta = PATH_RAW_INMET / str(ano)
        if not pasta.exists():
            print(f"  INMET {ano}: pasta não encontrada, pulando.")
            continue

        csvs = list(pasta.rglob("*.CSV")) + list(pasta.rglob("*.csv"))
        print(f"  INMET {ano}: {len(csvs)} estações ...", end=" ", flush=True)

        for csv_path in csvs:
            uf = _ler_uf_do_header(csv_path)
            if not uf:
                continue
            df_dia = _ler_dados_estacao(csv_path, uf)
            if df_dia is not None and not df_dia.empty:
                frames.append(df_dia)

        print("ok")

    if not frames:
        raise RuntimeError("Nenhum dado INMET encontrado. Execute scripts/fetch_inmet.py primeiro.")

    df_all = pd.concat(frames, ignore_index=True)
    df_all["ano"] = df_all["data"].dt.year
    df_all["mes"] = df_all["data"].dt.month

    # Agrega diário → mensal por UF (média entre estações)
    agg = {"uf": "first"}
    if "chuva" in df_all.columns:
        agg["chuva"] = "sum"
    if "temp" in df_all.columns:
        agg["temp"] = "mean"

    df_mensal = (
        df_all.groupby(["uf", "ano", "mes"])
        .agg({"chuva": "sum", "temp": "mean"} if "temp" in df_all.columns else {"chuva": "sum"})
        .reset_index()
        .rename(columns={"chuva": "chuva_mm", "temp": "temp_c"})
    )

    # Filtrar anos válidos
    df_mensal = df_mensal[df_mensal["ano"].isin(anos)]
    return df_mensal


def add_anomalias(df_mensal: pd.DataFrame) -> pd.DataFrame:
    """
    Adiciona colunas de anomalia climatológica (desvio em relação à média do período).

    Novas colunas: anomalia_chuva, anomalia_temp
    """
    # Climatologia: média de cada UF×mês no período completo
    cols_clima = [c for c in ("chuva_mm", "temp_c") if c in df_mensal.columns]
    climatologia = (
        df_mensal.groupby(["uf", "mes"])[cols_clima]
        .mean()
        .rename(columns={c: f"media_{c}" for c in cols_clima})
        .reset_index()
    )

    df = df_mensal.merge(climatologia, on=["uf", "mes"], how="left")

    if "chuva_mm" in df.columns and "media_chuva_mm" in df.columns:
        df["anomalia_chuva"] = df["chuva_mm"] - df["media_chuva_mm"]
    if "temp_c" in df.columns and "media_temp_c" in df.columns:
        df["anomalia_temp"] = df["temp_c"] - df["media_temp_c"]

    return df


# ── SIDRA PAM ────────────────────────────────────────────────────────────────

def clean_pam(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Pivota o DataFrame longo do PAM para formato largo por variável.

    Retorna: uf, ano, cultura, qtd_t, area_plantada_ha, area_colhida_ha, rendimento_kg_ha
    """
    VAR_MAP = {
        "Quantidade produzida": "qtd_t",
        "Area plantada": "area_plantada_ha",
        "Area colhida": "area_colhida_ha",
        "Rendimento medio": "rendimento_kg_ha",
    }

    df = df_raw.copy()
    df["variavel_norm"] = df["variavel"].map(VAR_MAP)
    df = df.dropna(subset=["variavel_norm", "valor"])

    df_pivot = df.pivot_table(
        index=["uf", "ano", "cultura"],
        columns="variavel_norm",
        values="valor",
        aggfunc="first",
    ).reset_index()

    df_pivot.columns.name = None
    return df_pivot


# ── SIDRA IPCA ───────────────────────────────────────────────────────────────

def clean_ipca(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Pivota o IPCA para formato largo com colunas ipca_var_mensal e ipca_acum_ano.
    """
    VAR_MAP = {
        "IPCA variacao mensal": "ipca_var_mensal",
        "IPCA acumulado ano": "ipca_acum_ano",
    }

    df = df_raw.copy()
    df["variavel_norm"] = df["variavel"].map(VAR_MAP)
    df = df.dropna(subset=["variavel_norm"])

    df_pivot = df.pivot_table(
        index=["uf", "ano", "mes"],
        columns="variavel_norm",
        values="valor",
        aggfunc="first",
    ).reset_index()

    df_pivot.columns.name = None
    return df_pivot
