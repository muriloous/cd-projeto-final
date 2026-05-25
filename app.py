"""
Dashboard: Impacto do Clima na Produção Agrícola e Inflação no Brasil (2014–2024)

Execução:
    streamlit run app.py
"""
import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))
from src.config import CULTURAS, PATH_PROCESSED, UFS_ALVO
from src.data_fetch.geo import load_geojson
from src.processing.analysis import cross_correlation, pearson_matrix, resumo_lag_por_uf
from src.viz.charts import (
    barchart_lag,
    barchart_top_ufs,
    heatmap_anomalia,
    heatmap_pearson,
    linha_ipca,
    linha_temporal,
    scatter_correlacao,
)
from src.viz.maps import choropleth_pearson, choropleth_uf

# ── Configuração da página ───────────────────────────────────────────────────
st.set_page_config(
    page_title="Clima × Agro × Inflação",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Carregamento de dados ────────────────────────────────────────────────────
@st.cache_data
def load_mensal() -> pd.DataFrame:
    path = PATH_PROCESSED / "consolidated_mensal.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


@st.cache_data
def load_anual() -> pd.DataFrame:
    path = PATH_PROCESSED / "consolidated_anual.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


@st.cache_resource
def load_geo() -> dict:
    return load_geojson()


@st.cache_data
def load_metadata() -> dict:
    path = PATH_PROCESSED / "metadata.json"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


df_mensal = load_mensal()
df_anual = load_anual()
geojson = load_geo()
metadata = load_metadata()

# ── Verificação de dados ─────────────────────────────────────────────────────
dados_ok = not df_mensal.empty and not df_anual.empty

# ── Sidebar: filtros globais ─────────────────────────────────────────────────
st.sidebar.title("🔍 Filtros")

culturas_disp = list(CULTURAS.keys())
if dados_ok and "cultura" in df_anual.columns:
    culturas_disp = sorted(df_anual["cultura"].dropna().unique().tolist())

cultura_sel = st.sidebar.selectbox("Cultura", culturas_disp, index=0)

anos_min, anos_max = 2014, 2024
if dados_ok and "ano" in df_anual.columns:
    anos_min = int(df_anual["ano"].min())
    anos_max = int(df_anual["ano"].max())

ano_range = st.sidebar.slider(
    "Período (anos)",
    min_value=anos_min, max_value=anos_max,
    value=(anos_min, anos_max),
)

ufs_disp = UFS_ALVO
if dados_ok and "uf" in df_anual.columns:
    ufs_disp = sorted(df_anual["uf"].dropna().unique().tolist())

ufs_sel = st.sidebar.multiselect("UFs", ufs_disp, default=ufs_disp[:8])
if not ufs_sel:
    ufs_sel = ufs_disp

# ── Aplicar filtros ──────────────────────────────────────────────────────────
def filtrar_anual(df):
    if df.empty:
        return df
    mask = (
        df["uf"].isin(ufs_sel) &
        df["ano"].between(ano_range[0], ano_range[1])
    )
    if "cultura" in df.columns:
        mask &= df["cultura"] == cultura_sel
    return df[mask]


def filtrar_mensal(df):
    if df.empty:
        return df
    mask = (
        df["uf"].isin(ufs_sel) &
        df["ano"].between(ano_range[0], ano_range[1])
    )
    return df[mask]


df_a = filtrar_anual(df_anual)
df_m = filtrar_mensal(df_mensal)

# ── Helpers ──────────────────────────────────────────────────────────────────
def sem_dados():
    st.warning(
        "Dados ainda não gerados. Execute o pipeline ETL primeiro:\n\n"
        "```bash\n"
        "python scripts/fetch_inmet.py\n"
        "python scripts/build_dataset.py\n"
        "```"
    )


def periodo_label():
    return f"{ano_range[0]}–{ano_range[1]}"


# ── Abas principais ──────────────────────────────────────────────────────────
tabs = st.tabs([
    "🏠 Visão Geral",
    "🌧️ Clima",
    "🌾 Produção Agrícola",
    "📈 Inflação Alimentos",
    "🔬 Correlações & Insights",
])


# ════════════════════════════════════════════════════════════════════════════
# ABA 1 — VISÃO GERAL
# ════════════════════════════════════════════════════════════════════════════
with tabs[0]:
    st.title("Impacto do Clima na Produção Agrícola e Inflação no Brasil")
    st.markdown(
        f"""
        Este dashboard analisa como **variações climáticas** (precipitação e temperatura)
        influenciam a **produção de soja, milho e café** e, consequentemente, o
        **IPCA do grupo Alimentação e Bebidas** no Brasil entre {anos_min} e {anos_max}.

        Use os filtros na barra lateral para explorar por **cultura**, **período** e **estados (UFs)**.
        """,
        unsafe_allow_html=False,
    )

    if not dados_ok:
        sem_dados()
    else:
        col1, col2, col3, col4 = st.columns(4)

        qtd_total = df_a["qtd_t"].sum() / 1e6 if "qtd_t" in df_a.columns else 0
        col1.metric(
            f"Produção total — {cultura_sel.split()[0]}",
            f"{qtd_total:,.1f} Mt",
            help=f"Soma da quantidade produzida no período {periodo_label()} (mega-toneladas)",
        )

        if "qtd_t" in df_a.columns and len(df_a["ano"].unique()) >= 2:
            anos_ord = sorted(df_a["ano"].unique())
            qtd_ini = df_a[df_a["ano"] == anos_ord[0]]["qtd_t"].sum()
            qtd_fim = df_a[df_a["ano"] == anos_ord[-1]]["qtd_t"].sum()
            var_prod = (qtd_fim / qtd_ini - 1) * 100 if qtd_ini > 0 else 0
        else:
            var_prod = 0
        col2.metric(
            "Variação de produção",
            f"{var_prod:+.1f}%",
            help=f"Variação entre {ano_range[0]} e {ano_range[1]}",
        )

        ipca_acum = df_m["ipca_acum_ano"].dropna().iloc[-1] if "ipca_acum_ano" in df_m.columns and not df_m.empty else 0
        col3.metric(
            "IPCA Alimentação (últ. ano)",
            f"{ipca_acum:.1f}%",
            help="Variação acumulada no último ano disponível (grupo Alimentação e Bebidas)",
        )

        if "qtd_t" in df_a.columns and not df_a.empty:
            top_uf = df_a.groupby("uf")["qtd_t"].sum().idxmax()
        else:
            top_uf = "—"
        col4.metric(
            "Top UF produtora",
            top_uf,
            help=f"Estado com maior produção acumulada de {cultura_sel.split()[0]} no período",
        )

        st.divider()
        st.subheader("Perguntas que este dashboard responde")
        st.markdown(
            """
            1. **Quais estados** concentram a produção de soja, milho e café?
            2. **Secas e excesso de chuva** reduzem a produtividade nas principais regiões?
            3. **Com que defasagem** (lag) uma anomalia climática se reflete na inflação de alimentos?
            4. **A correlação** entre chuva na safra e produção é estatisticamente significativa?
            5. **Como evoluiu** o IPCA de Alimentação em relação às variações climáticas extremas?
            """,
        )

        with st.expander("📋 Sobre os dados"):
            if metadata:
                st.json(metadata)
            else:
                st.info("Metadata não disponível. Rode `python scripts/build_dataset.py` primeiro.")


# ════════════════════════════════════════════════════════════════════════════
# ABA 2 — CLIMA
# ════════════════════════════════════════════════════════════════════════════
with tabs[1]:
    st.header("🌧️ Padrões Climáticos por Estado")
    st.markdown(
        "Analise a **precipitação acumulada** e a **temperatura média** mensal por UF, "
        "além das **anomalias** em relação à climatologia histórica do período."
    )

    if not dados_ok or df_m.empty:
        sem_dados()
    else:
        c1, c2 = st.columns(2)

        with c1:
            st.subheader("Precipitação Mensal por UF")
            if "chuva_mm" in df_m.columns:
                df_plot = df_m.copy()
                df_plot["periodo"] = (
                    df_plot["ano"].astype(str) + "-" + df_plot["mes"].astype(str).str.zfill(2)
                )
                fig = linha_temporal(
                    df_plot, x="periodo", y="chuva_mm", color="uf",
                    title="Precipitação Mensal (mm)",
                    ylab="Precipitação (mm)",
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Dados de chuva não disponíveis.")

        with c2:
            st.subheader("Temperatura Média Mensal por UF")
            if "temp_c" in df_m.columns:
                df_plot = df_m.copy()
                df_plot["periodo"] = (
                    df_plot["ano"].astype(str) + "-" + df_plot["mes"].astype(str).str.zfill(2)
                )
                fig = linha_temporal(
                    df_plot, x="periodo", y="temp_c", color="uf",
                    title="Temperatura Média (°C)",
                    ylab="Temperatura (°C)",
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Dados de temperatura não disponíveis.")

        st.divider()
        st.subheader("Mapa de Calor: Anomalia de Chuva (UF × Mês)")
        st.markdown(
            "Vermelho = menos chuva que a média histórica; Azul = mais chuva. "
            "Identifique padrões sazonais e anos de seca/excesso."
        )

        c3, c4 = st.columns(2)
        with c3:
            if "anomalia_chuva" in df_m.columns:
                fig = heatmap_anomalia(
                    df_m, x="mes", y="uf", z="anomalia_chuva",
                    title="Anomalia de Precipitação (mm, média do período selecionado)",
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Anomalias de chuva não disponíveis.")

        with c4:
            if "anomalia_temp" in df_m.columns:
                fig = heatmap_anomalia(
                    df_m, x="mes", y="uf", z="anomalia_temp",
                    title="Anomalia de Temperatura (°C, média do período selecionado)",
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Anomalias de temperatura não disponíveis.")


# ════════════════════════════════════════════════════════════════════════════
# ABA 3 — PRODUÇÃO AGRÍCOLA
# ════════════════════════════════════════════════════════════════════════════
with tabs[2]:
    st.header("🌾 Produção Agrícola por Estado")
    st.markdown(
        f"Explore a evolução da produção de **{cultura_sel.split()[0]}** "
        f"no período **{periodo_label()}**. "
        "A produtividade (rendimento em kg/ha) é um indicador mais robusto que a área total."
    )

    if not dados_ok or df_a.empty:
        sem_dados()
    else:
        c1, c2 = st.columns(2)

        with c1:
            st.subheader("Top UFs por Quantidade Produzida")
            if "qtd_t" in df_a.columns:
                df_top = df_a.groupby("uf")["qtd_t"].sum().reset_index()
                fig = barchart_top_ufs(
                    df_top, x="uf", y="qtd_t",
                    title=f"Produção Total de {cultura_sel.split()[0]} por UF ({periodo_label()})",
                    ylab="Quantidade (t)",
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Dados de produção não disponíveis.")

        with c2:
            st.subheader("Evolução do Rendimento Médio (kg/ha)")
            if "rendimento_kg_ha" in df_a.columns:
                df_rend = df_a.groupby(["uf", "ano"])["rendimento_kg_ha"].mean().reset_index()
                fig = linha_temporal(
                    df_rend, x="ano", y="rendimento_kg_ha", color="uf",
                    title=f"Rendimento Médio — {cultura_sel.split()[0]} (kg/ha)",
                    ylab="Rendimento (kg/ha)",
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Dados de rendimento não disponíveis.")

        st.divider()
        st.subheader(f"Mapa de Produção — {cultura_sel.split()[0]} ({ano_range[1]})")
        st.markdown("Distribuição geográfica da quantidade produzida no último ano selecionado.")

        if "qtd_t" in df_a.columns:
            df_mapa = df_a[df_a["ano"] == ano_range[1]].groupby("uf")["qtd_t"].sum().reset_index()
            fig_mapa = choropleth_uf(
                df_mapa, geojson, values="qtd_t",
                title=f"Quantidade Produzida de {cultura_sel.split()[0]} em {ano_range[1]} (t)",
                labels={"qtd_t": "Quantidade (t)"},
            )
            st.plotly_chart(fig_mapa, use_container_width=True)


# ════════════════════════════════════════════════════════════════════════════
# ABA 4 — INFLAÇÃO
# ════════════════════════════════════════════════════════════════════════════
with tabs[3]:
    st.header("📈 IPCA — Alimentação e Bebidas")
    st.markdown(
        "O **IPCA do grupo Alimentação e Bebidas** é o canal pelo qual variações climáticas "
        "e de produção se transmitem ao consumidor final. "
        "Dados por Região Metropolitana — UFs sem RM usam o índice nacional como referência."
    )

    if not dados_ok or df_m.empty:
        sem_dados()
    else:
        if "ipca_var_mensal" in df_m.columns:
            df_ipca_plot = df_m.copy()
            df_ipca_plot["periodo"] = (
                df_ipca_plot["ano"].astype(str) + "-" +
                df_ipca_plot["mes"].astype(str).str.zfill(2)
            )

            # Agrega por período (média entre UFs selecionadas)
            df_ipca_agg = (
                df_ipca_plot.groupby("periodo")["ipca_var_mensal"]
                .mean()
                .reset_index()
            )

            fig = linha_ipca(
                df_ipca_agg,
                title="IPCA Alimentação e Bebidas — Variação Mensal (%) — Média das UFs Selecionadas",
            )
            # Destacar meses com variação > 2%
            picos = df_ipca_agg[df_ipca_agg["ipca_var_mensal"] > 2]
            if not picos.empty:
                import plotly.graph_objects as go
                fig.add_trace(go.Scatter(
                    x=picos["periodo"], y=picos["ipca_var_mensal"],
                    mode="markers", name="Variação > 2%",
                    marker=dict(color="red", size=8, symbol="x"),
                ))

            st.plotly_chart(fig, use_container_width=True)

            st.divider()
            c1, c2 = st.columns(2)

            with c1:
                st.subheader("IPCA Mensal por UF (série completa)")
                fig2 = linha_temporal(
                    df_ipca_plot, x="periodo", y="ipca_var_mensal", color="uf",
                    title="Variação Mensal (%) por UF",
                    ylab="Variação (%)",
                )
                st.plotly_chart(fig2, use_container_width=True)

            with c2:
                st.subheader("IPCA Acumulado no Ano por UF")
                if "ipca_acum_ano" in df_m.columns:
                    df_acum = df_ipca_plot.groupby(["uf", "ano"])["ipca_acum_ano"].last().reset_index()
                    fig3 = linha_temporal(
                        df_acum, x="ano", y="ipca_acum_ano", color="uf",
                        title="Variação Acumulada no Ano (%) por UF",
                        ylab="Acumulado (%)",
                    )
                    st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("Dados de IPCA não disponíveis.")


# ════════════════════════════════════════════════════════════════════════════
# ABA 5 — CORRELAÇÕES & INSIGHTS
# ════════════════════════════════════════════════════════════════════════════
with tabs[4]:
    st.header("🔬 Correlações & Insights")
    st.markdown(
        """
        Esta aba é o coração analítico do projeto. Aqui verificamos **se e como**
        as anomalias climáticas se correlacionam com a produção agrícola e,
        com qual **defasagem temporal (lag)**, impactam a inflação de alimentos.
        """
    )

    if not dados_ok:
        sem_dados()
    else:
        # ── 5.1 Scatter clima × produção ────────────────────────────────────
        st.subheader("1. Anomalia de Chuva na Safra × Quantidade Produzida")
        st.markdown(
            "Cada ponto é um UF-ano. A reta de tendência (OLS) indica a direção da relação: "
            "mais chuva na safra → mais produção?"
        )

        if "anomalia_chuva_safra" in df_a.columns and "qtd_t" in df_a.columns:
            fig_scatter = scatter_correlacao(
                df_a.dropna(subset=["anomalia_chuva_safra", "qtd_t"]),
                x="anomalia_chuva_safra", y="qtd_t", color="uf",
                title=f"Anomalia de Chuva na Safra vs Produção — {cultura_sel.split()[0]}",
                xlab="Anomalia de Chuva (mm, vs climatologia)",
                ylab="Quantidade Produzida (t)",
            )
            st.plotly_chart(fig_scatter, use_container_width=True)
        else:
            st.info(
                "Coluna `anomalia_chuva_safra` não encontrada. "
                "Verifique se o ETL foi executado com dados INMET disponíveis."
            )

        st.divider()

        # ── 5.2 Matriz de Pearson ────────────────────────────────────────────
        st.subheader("2. Matriz de Correlação de Pearson: Clima × Produção")
        st.markdown(
            "Cada célula mostra o coeficiente de Pearson (r) entre uma variável de clima e uma "
            "variável de produção por UF. Valores próximos de ±1 indicam correlação forte."
        )

        vars_clima = [c for c in ("chuva_mm_safra", "anomalia_chuva_safra", "temp_c_safra", "anomalia_temp_safra") if c in df_a.columns]
        vars_prod = [c for c in ("qtd_t", "rendimento_kg_ha") if c in df_a.columns]

        if vars_clima and vars_prod and not df_a.empty:
            df_pearson = pearson_matrix(df_a.dropna(subset=vars_clima + vars_prod), vars_clima, vars_prod)
            if not df_pearson.empty:
                fig_heat = heatmap_pearson(
                    df_pearson,
                    title=f"Pearson r — Clima × Produção ({cultura_sel.split()[0]})",
                )
                st.plotly_chart(fig_heat, use_container_width=True)

                st.subheader("Mapa de Pearson por UF (Chuva Safra × Produção)")
                if "chuva_mm_safra" in df_pearson.columns:
                    df_mapa_p = df_pearson[["uf", "chuva_mm_safra"]].rename(
                        columns={"chuva_mm_safra": "pearson_r"}
                    )
                    fig_mapa_p = choropleth_pearson(
                        df_mapa_p, geojson,
                        title=f"Pearson r: Chuva Safra × Produção {cultura_sel.split()[0]}",
                    )
                    st.plotly_chart(fig_mapa_p, use_container_width=True)
        else:
            st.info("Dados insuficientes para calcular a matriz de Pearson.")

        st.divider()

        # ── 5.3 Análise de Lag ───────────────────────────────────────────────
        st.subheader("3. Defasagem Temporal (Lag): Clima → Inflação")
        st.markdown(
            "Investiga **com quantos meses de atraso** uma anomalia de chuva se reflete "
            "no IPCA de Alimentação. Ajuste o slider para explorar diferentes defasagens."
        )

        lag_max = st.slider("Defasagem máxima (meses)", min_value=3, max_value=24, value=12, step=1)

        if "anomalia_chuva" in df_m.columns and "ipca_var_mensal" in df_m.columns:
            col_lag1, col_lag2 = st.columns(2)

            with col_lag1:
                uf_lag = st.selectbox(
                    "Selecione uma UF para análise de lag",
                    sorted(df_m["uf"].dropna().unique()),
                    key="uf_lag_select",
                )
                df_uf = df_m[df_m["uf"] == uf_lag].sort_values(["ano", "mes"])
                df_uf.index = pd.to_datetime(
                    df_uf["ano"].astype(str) + "-" + df_uf["mes"].astype(str).str.zfill(2),
                    format="%Y-%m",
                )

                cc = cross_correlation(
                    df_uf["anomalia_chuva"].dropna(),
                    df_uf["ipca_var_mensal"].dropna(),
                    max_lag=lag_max,
                )
                fig_lag = barchart_lag(
                    cc,
                    title=f"Cross-correlation: Anomalia Chuva → IPCA Alimentação ({uf_lag})",
                )
                st.plotly_chart(fig_lag, use_container_width=True)

                best_l = int(cc.abs().dropna().idxmax()) if not cc.dropna().empty else 0
                best_r = cc.loc[best_l] if best_l in cc.index else float("nan")
                st.info(
                    f"**Melhor lag para {uf_lag}:** {best_l} meses "
                    f"(r = {best_r:.3f})"
                )

            with col_lag2:
                st.subheader("Resumo de Melhor Lag por UF")
                df_lag_resumo = resumo_lag_por_uf(df_m, max_lag=lag_max)
                if not df_lag_resumo.empty:
                    st.dataframe(
                        df_lag_resumo.sort_values("pearson_r", ascending=False)
                        .reset_index(drop=True)
                        .rename(columns={
                            "uf": "UF",
                            "melhor_lag": "Melhor Lag (meses)",
                            "pearson_r": "Pearson r",
                        }),
                        use_container_width=True,
                    )
                    st.markdown(
                        "**Interpretação:** Um lag positivo indica que a anomalia de chuva "
                        "precede a variação do IPCA em N meses. Lags de 3–9 meses são "
                        "esperados (tempo entre safra, processamento e prateleira)."
                    )
        else:
            st.info(
                "Dados de anomalia de chuva ou IPCA não disponíveis. "
                "Execute o pipeline ETL completo (incluindo dados INMET)."
            )
