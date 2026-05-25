from pathlib import Path

# ── Escopo temporal ──────────────────────────────────────────────────────────
ANOS = list(range(2020, 2025))  # 2020–2024 (cobertura completa IPCA por RM)

# ── Culturas: nome exibido → código SIDRA (tabela 5457, classificação c81) ──
CULTURAS = {
    "Soja (em grão)": "40124",
    "Milho (em grão)": "40122",
    "Café (em grão) Total": "40139",
}

# ── UFs alvo: principais produtoras das três culturas ───────────────────────
UFS_ALVO = ["MT", "PR", "RS", "GO", "MS", "MG", "SP", "BA", "TO", "MA", "PA", "ES"]

# Mapeamento RM → UF para o IPCA (tabela 7060)
RM_UF_MAP = {
    "São Paulo": "SP",
    "Rio de Janeiro": "RJ",
    "Belo Horizonte": "MG",
    "Curitiba": "PR",
    "Porto Alegre": "RS",
    "Recife": "PE",
    "Fortaleza": "CE",
    "Salvador": "BA",
    "Belém": "PA",
    "Brasília": "DF",
    "Goiânia": "GO",
    "Vitória": "ES",
}

# ── Janelas de safra por cultura (mês de início relativo ao ano da colheita) ─
# start_year_offset: -1 significa que o plantio começa no ano anterior à colheita
SAFRA_WINDOWS = {
    "Soja (em grão)": {"start_month": 10, "start_year_offset": -1, "end_month": 4},
    "Milho (em grão)": {"start_month": 9, "start_year_offset": -1, "end_month": 7},
    "Café (em grão) Total": {"start_month": 9, "start_year_offset": -1, "end_month": 8},
}

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parents[1]
PATH_RAW_INMET = ROOT / "data" / "raw" / "inmet"
PATH_RAW_SIDRA = ROOT / "data" / "raw" / "sidra"
PATH_RAW_GEO = ROOT / "data" / "raw" / "geo"
PATH_PROCESSED = ROOT / "data" / "processed"

# ── SIDRA variáveis da tabela 5457 ──────────────────────────────────────────
SIDRA_PAM_VARS = "214,8331,216,112"  # qtd produzida, área plantada, área colhida, rendimento

# ── IPCA: código do grupo Alimentação e Bebidas (tabela 7060, c315) ─────────
IPCA_GRUPO_ALIMENTACAO = "7170"
IPCA_VAR_MENSAL = "63"
IPCA_VAR_ACUM_ANO = "69"
