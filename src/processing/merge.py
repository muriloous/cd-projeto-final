"""
Consolida os dados limpos de clima, PAM e IPCA em dois datasets finais.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parents[2]))
from src.config import ANOS, CULTURAS, PATH_PROCESSED, SAFRA_WINDOWS, UFS_ALVO


def _clima_safra(df_clima_mensal: pd.DataFrame, cultura: str, ano_colheita: int) -> pd.Series:
    """
    Agrega o clima pela janela da safra de uma cultura para um dado ano de colheita.

    Retorna série com colunas: chuva_mm_safra, temp_c_safra, anomalia_chuva_safra, anomalia_temp_safra
    """
    w = SAFRA_WINDOWS[cultura]
    start_month = w["start_month"]
    end_month = w["end_month"]
    start_year = ano_colheita + w["start_year_offset"]
    end_year = ano_colheita

    # Seleciona meses da janela de safra (pode cruzar a virada do ano)
    mask = (
        (
            (df_clima_mensal["ano"] == start_year) & (df_clima_mensal["mes"] >= start_month)
        ) | (
            (df_clima_mensal["ano"] == end_year) & (df_clima_mensal["mes"] <= end_month)
        )
    )
    subset = df_clima_mensal[mask]

    if subset.empty:
        return pd.Series(dtype=float)

    result = {}
    if "chuva_mm" in subset.columns:
        result["chuva_mm_safra"] = subset["chuva_mm"].sum()
    if "temp_c" in subset.columns:
        result["temp_c_safra"] = subset["temp_c"].mean()
    if "anomalia_chuva" in subset.columns:
        result["anomalia_chuva_safra"] = subset["anomalia_chuva"].mean()
    if "anomalia_temp" in subset.columns:
        result["anomalia_temp_safra"] = subset["anomalia_temp"].mean()

    return pd.Series(result)


def build_mensal(
    df_clima: pd.DataFrame,
    df_ipca: pd.DataFrame,
    ufs: list[str] = UFS_ALVO,
) -> pd.DataFrame:
    """
    Merge mensal: clima + IPCA por UF×ano×mês.

    Para UFs sem RM no IPCA, usa o IPCA nacional (uf="BR") como fallback.
    """
    df_c = df_clima[df_clima["uf"].isin(ufs)].copy()
    df_i = df_ipca.copy()

    df_merged = df_c.merge(df_i[df_i["uf"] != "BR"], on=["uf", "ano", "mes"], how="left")

    # Fallback nacional para UFs sem dados de RM
    ipca_br = df_ipca[df_ipca["uf"] == "BR"].drop(columns=["uf"]).rename(
        columns={c: f"{c}_nacional" for c in df_ipca.columns if c not in ("ano", "mes")}
    )
    df_merged = df_merged.merge(ipca_br, on=["ano", "mes"], how="left")

    # Preenche valores ausentes da RM com o nacional
    for col in ("ipca_var_mensal", "ipca_acum_ano"):
        col_nac = f"{col}_nacional"
        if col in df_merged.columns and col_nac in df_merged.columns:
            df_merged[col] = df_merged[col].fillna(df_merged[col_nac])
        df_merged.drop(columns=[c for c in (col_nac,) if c in df_merged.columns], inplace=True)

    return df_merged.sort_values(["uf", "ano", "mes"]).reset_index(drop=True)


def build_anual(
    df_clima: pd.DataFrame,
    df_pam: pd.DataFrame,
    df_ipca: pd.DataFrame,
    anos: list[int] = ANOS,
    ufs: list[str] = UFS_ALVO,
) -> pd.DataFrame:
    """
    Merge anual: clima da safra + PAM + IPCA acumulado por UF×ano×cultura.
    """
    records = []

    for cultura in CULTURAS:
        df_pam_c = df_pam[df_pam["cultura"] == cultura].copy()

        for ano in anos:
            for uf in ufs:
                df_uf_clima = df_clima[df_clima["uf"] == uf]
                clima_safra = _clima_safra(df_uf_clima, cultura, ano)

                pam_row = df_pam_c[(df_pam_c["uf"] == uf) & (df_pam_c["ano"] == ano)]

                # IPCA acumulado no ano: pega o valor de dezembro (ou o último mês disponível)
                ipca_row = df_ipca[
                    (df_ipca["uf"].isin([uf, "BR"])) &
                    (df_ipca["ano"] == ano) &
                    (df_ipca["mes"] == 12)
                ]
                ipca_row_uf = ipca_row[ipca_row["uf"] == uf]
                ipca_row_br = ipca_row[ipca_row["uf"] == "BR"]
                ipca_row_final = ipca_row_uf if not ipca_row_uf.empty else ipca_row_br

                rec = {"uf": uf, "ano": ano, "cultura": cultura}
                rec.update(clima_safra.to_dict())

                if not pam_row.empty:
                    for col in ("qtd_t", "area_plantada_ha", "area_colhida_ha", "rendimento_kg_ha"):
                        if col in pam_row.columns:
                            rec[col] = pam_row.iloc[0][col]

                if not ipca_row_final.empty:
                    for col in ("ipca_var_mensal", "ipca_acum_ano"):
                        if col in ipca_row_final.columns:
                            rec[col] = ipca_row_final.iloc[0][col]

                records.append(rec)

    return pd.DataFrame(records).sort_values(["cultura", "uf", "ano"]).reset_index(drop=True)


def save_datasets(df_mensal: pd.DataFrame, df_anual: pd.DataFrame) -> None:
    PATH_PROCESSED.mkdir(parents=True, exist_ok=True)
    path_m = PATH_PROCESSED / "consolidated_mensal.csv"
    path_a = PATH_PROCESSED / "consolidated_anual.csv"
    df_mensal.to_csv(path_m, index=False, encoding="utf-8")
    df_anual.to_csv(path_a, index=False, encoding="utf-8")
    print(f"  Mensal: {path_m} ({len(df_mensal):,} linhas)")
    print(f"  Anual:  {path_a} ({len(df_anual):,} linhas)")
