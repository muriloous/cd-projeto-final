"""
Coleta dados da Produção Agrícola Municipal (PAM) via SIDRA/IBGE.

Tabela 5457: Área plantada, área colhida, quantidade produzida, rendimento médio
             e valor da produção das lavouras temporárias e permanentes.
Variáveis:
  214  – Quantidade produzida (Toneladas)
  112  – Área plantada (Hectares)
  2306 – Área colhida (Hectares)
  216  – Rendimento médio da produção (Kg/Hectare)
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parents[2]))
from src.config import ANOS, CULTURAS, PATH_RAW_SIDRA, SIDRA_PAM_VARS, UFS_ALVO

try:
    import sidrapy
except ImportError as exc:
    raise SystemExit("sidrapy não instalado. Execute: pip install sidrapy") from exc

# Mapeamento código IBGE de UF → sigla
_IBGE_UF_SIGLA = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA",
    "16": "AP", "17": "TO", "21": "MA", "22": "PI", "23": "CE",
    "24": "RN", "25": "PB", "26": "PE", "27": "AL", "28": "SE",
    "29": "BA", "31": "MG", "32": "ES", "33": "RJ", "35": "SP",
    "41": "PR", "42": "SC", "43": "RS", "50": "MS", "51": "MT",
    "52": "GO", "53": "DF",
}


def fetch_pam(
    culturas: dict = CULTURAS,
    ufs_ibge: str = "all",
    anos: list[int] = ANOS,
) -> pd.DataFrame:
    periodos = ",".join(str(a) for a in anos)
    codigos_cultura = ",".join(culturas.values())

    print("  SIDRA PAM: consultando tabela 5457 ...", flush=True)
    df = sidrapy.get_table(
        table_code="5457",
        territorial_level="3",
        ibge_territorial_code=ufs_ibge,
        period=periodos,
        variable=SIDRA_PAM_VARS,
        classifications={"782": codigos_cultura},
        header="y",
        format="pandas",
    )

    # sidrapy retorna linha 0 com os rótulos das colunas como dado; colunas reais são D1C/D1N/...
    # Estrutura: D1C=UF_cod, D1N=UF_nome, D2C=ano_cod, D2N=ano, D3C=var_cod, D3N=variavel,
    #            D4C=cultura_cod, D4N=cultura, V=valor
    df = df.iloc[1:].copy()  # remove linha de cabeçalho

    df = df.rename(columns={
        "D1C": "uf_cod",
        "D1N": "uf_nome",
        "D2C": "ano_cod",
        "D2N": "ano",
        "D3C": "var_cod",
        "D3N": "variavel",
        "D4C": "cultura_cod",
        "D4N": "cultura",
        "V": "valor",
    })

    # Mapeia código de variável para nome limpo (evita problemas de encoding nos nomes da API)
    _VAR_COD_NOME = {
        "214": "Quantidade produzida",
        "8331": "Area plantada",
        "216": "Area colhida",
        "112": "Rendimento medio",
    }
    df["variavel"] = df["var_cod"].map(_VAR_COD_NOME).fillna(df["variavel"])

    df = df[["uf_cod", "uf_nome", "ano", "cultura", "cultura_cod", "var_cod", "variavel", "valor"]].copy()
    df["uf"] = df["uf_cod"].map(_IBGE_UF_SIGLA)
    df["ano"] = pd.to_numeric(df["ano"], errors="coerce")
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    df = df.dropna(subset=["ano", "uf"])

    return df


def save_pam(df: pd.DataFrame, path: Path = PATH_RAW_SIDRA / "pam.csv") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8")
    print(f"  PAM salvo em {path} ({len(df):,} linhas)")


if __name__ == "__main__":
    df = fetch_pam()
    save_pam(df)
