"""
Funções de análise estatística: Pearson, cross-correlation, best lag.
"""
import pandas as pd
import numpy as np
from scipy import stats


def pearson_matrix(
    df: pd.DataFrame,
    var_clima: list[str],
    var_prod: list[str],
    group_by: str = "uf",
) -> pd.DataFrame:
    """
    Calcula correlação de Pearson entre variáveis de clima e produção por grupo.

    Retorna DataFrame com MultiIndex (grupo, var_prod) × var_clima com coeficientes r.
    """
    records = []
    for grupo, gdf in df.groupby(group_by):
        for vp in var_prod:
            row = {group_by: grupo, "var_prod": vp}
            for vc in var_clima:
                sub = gdf[[vc, vp]].dropna()
                if len(sub) >= 4:
                    r, _ = stats.pearsonr(sub[vc], sub[vp])
                    row[vc] = round(r, 3)
                else:
                    row[vc] = np.nan
            records.append(row)
    return pd.DataFrame(records)


def cross_correlation(
    s_x: pd.Series,
    s_y: pd.Series,
    max_lag: int = 12,
) -> pd.Series:
    """
    Correlação cruzada entre s_x (clima) e s_y (IPCA) para lags 0..max_lag.

    Retorna Series indexada por lag (meses).
    """
    s_x, s_y = s_x.align(s_y, join="inner")
    s_x = s_x.dropna()
    s_y = s_y.dropna()
    s_x, s_y = s_x.align(s_y, join="inner")

    lags = range(0, max_lag + 1)
    corrs = {}
    for lag in lags:
        s_y_lag = s_y.shift(-lag)
        sub = pd.concat([s_x, s_y_lag], axis=1).dropna()
        if len(sub) >= 4:
            r, _ = stats.pearsonr(sub.iloc[:, 0], sub.iloc[:, 1])
            corrs[lag] = round(r, 3)
        else:
            corrs[lag] = np.nan

    return pd.Series(corrs, name="pearson_r")


def best_lag(s_x: pd.Series, s_y: pd.Series, max_lag: int = 12) -> tuple[int, float]:
    """Retorna (lag_ótimo, r_máximo_absoluto) da cross-correlation."""
    cc = cross_correlation(s_x, s_y, max_lag)
    cc_abs = cc.abs().dropna()
    if cc_abs.empty:
        return 0, float("nan")
    lag_opt = int(cc_abs.idxmax())
    return lag_opt, float(cc.loc[lag_opt])


def resumo_lag_por_uf(
    df_mensal: pd.DataFrame,
    var_clima: str = "anomalia_chuva",
    var_ipca: str = "ipca_var_mensal",
    max_lag: int = 12,
) -> pd.DataFrame:
    """
    Para cada UF, calcula o melhor lag e r entre anomalia de chuva e IPCA.

    Retorna DataFrame: uf, melhor_lag, pearson_r
    """
    records = []
    for uf, gdf in df_mensal.groupby("uf"):
        gdf = gdf.sort_values(["ano", "mes"])
        gdf.index = pd.to_datetime(
            gdf["ano"].astype(str) + "-" + gdf["mes"].astype(str).str.zfill(2),
            format="%Y-%m",
        )
        if var_clima not in gdf.columns or var_ipca not in gdf.columns:
            continue
        lag, r = best_lag(gdf[var_clima], gdf[var_ipca], max_lag)
        records.append({"uf": uf, "melhor_lag": lag, "pearson_r": r})
    return pd.DataFrame(records)
