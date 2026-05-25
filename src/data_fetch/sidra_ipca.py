"""
Coleta o IPCA do grupo Alimentação e Bebidas por Região Metropolitana via SIDRA/IBGE.

Tabela 7060: IPCA - Variação mensal, acumulada no ano, acumulada em 12 meses e
             peso mensal, do índice geral e por grupos.
Variável 63  – Variação mensal (%)
Variável 69  – Variação acumulada no ano (%)
Nível territorial 7 – Região metropolitana e município de referência
Grupo Alimentação e Bebidas: código 7170 (classificação c315)
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parents[2]))
from src.config import (
    ANOS,
    IPCA_GRUPO_ALIMENTACAO,
    IPCA_VAR_ACUM_ANO,
    IPCA_VAR_MENSAL,
    PATH_RAW_SIDRA,
    RM_UF_MAP,
)

try:
    import sidrapy
except ImportError as exc:
    raise SystemExit("sidrapy não instalado. Execute: pip install sidrapy") from exc


def fetch_ipca(anos: list[int] = ANOS) -> pd.DataFrame:
    # Monta range mensal: 201401 a 202412
    inicio = f"{min(anos)}01"
    fim = f"{max(anos)}12"
    periodos = f"{inicio}-{fim}"

    print("  SIDRA IPCA: consultando tabela 7060 ...", flush=True)
    df = sidrapy.get_table(
        table_code="7060",
        territorial_level="7",
        ibge_territorial_code="all",
        period=periodos,
        variable=f"{IPCA_VAR_MENSAL},{IPCA_VAR_ACUM_ANO}",
        classifications={"315": IPCA_GRUPO_ALIMENTACAO},
        header="y",
        format="pandas",
    )

    # Estrutura: D1C/D1N=RM, D2C=periodo_cod (YYYYMM), D2N=periodo_nome, D3C/D3N=variavel, V=valor
    df = df.iloc[1:].copy()  # remove linha de rótulos

    _VAR_COD_NOME = {
        IPCA_VAR_MENSAL: "IPCA variacao mensal",
        IPCA_VAR_ACUM_ANO: "IPCA acumulado ano",
    }

    df = df.rename(columns={
        "D1N": "rm",
        "D2C": "periodo_cod",
        "D3C": "var_cod",
        "D3N": "variavel_raw",
        "V": "valor",
    })

    df["variavel"] = df["var_cod"].map(_VAR_COD_NOME).fillna(df["variavel_raw"])
    df = df[["rm", "periodo_cod", "variavel", "valor"]].copy()
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")

    # Extrair ano e mês do código YYYYMM
    df["ano"] = df["periodo_cod"].str[:4].astype(int)
    df["mes"] = df["periodo_cod"].str[4:].astype(int)

    # Extrair UF do nome da RM — formato "Cidade - UF" (ex: "Belém - PA")
    df["uf"] = df["rm"].str.extract(r" - ([A-Z]{2})$")
    df = df.dropna(subset=["uf"])

    return df


def fetch_ipca_nacional(anos: list[int] = ANOS) -> pd.DataFrame:
    """IPCA nacional (índice geral + Alimentação) como fallback para UFs sem RM."""
    inicio = f"{min(anos)}01"
    fim = f"{max(anos)}12"
    periodos = f"{inicio}-{fim}"

    print("  SIDRA IPCA nacional: consultando tabela 7060 ...", flush=True)
    df = sidrapy.get_table(
        table_code="7060",
        territorial_level="1",
        ibge_territorial_code="all",
        period=periodos,
        variable=f"{IPCA_VAR_MENSAL},{IPCA_VAR_ACUM_ANO}",
        classifications={"315": IPCA_GRUPO_ALIMENTACAO},
        header="y",
        format="pandas",
    )

    _VAR_COD_NOME = {
        IPCA_VAR_MENSAL: "IPCA variacao mensal",
        IPCA_VAR_ACUM_ANO: "IPCA acumulado ano",
    }

    df = df.iloc[1:].copy()
    df = df.rename(columns={"D2C": "periodo_cod", "D3C": "var_cod", "V": "valor"})
    df["variavel"] = df["var_cod"].map(_VAR_COD_NOME).fillna(df["var_cod"])
    df = df[["periodo_cod", "variavel", "valor"]].copy()
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    df["ano"] = df["periodo_cod"].str[:4].astype(int)
    df["mes"] = df["periodo_cod"].str[4:].astype(int)
    df["uf"] = "BR"
    df["rm"] = "Brasil"
    return df


def save_ipca(df: pd.DataFrame, path: Path = PATH_RAW_SIDRA / "ipca_alimentacao.csv") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8")
    print(f"  IPCA salvo em {path} ({len(df):,} linhas)")


if __name__ == "__main__":
    df_rm = fetch_ipca()
    df_br = fetch_ipca_nacional()
    df_all = pd.concat([df_rm, df_br], ignore_index=True)
    save_ipca(df_all)
