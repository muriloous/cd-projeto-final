"""
Funções reutilizáveis de visualização com Plotly.
"""
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


def linha_temporal(
    df: pd.DataFrame,
    x: str,
    y: str,
    color: str | None = None,
    title: str = "",
    xlab: str = "",
    ylab: str = "",
    height: int = 400,
) -> go.Figure:
    fig = px.line(
        df, x=x, y=y, color=color,
        title=title, labels={x: xlab or x, y: ylab or y},
        height=height,
    )
    fig.update_traces(mode="lines+markers", marker_size=4)
    fig.update_layout(legend_title_text="", margin=dict(t=50, b=20))
    return fig


def barchart_top_ufs(
    df: pd.DataFrame,
    x: str,
    y: str,
    color: str | None = None,
    title: str = "",
    xlab: str = "",
    ylab: str = "",
    n: int = 12,
    height: int = 400,
) -> go.Figure:
    top = df.nlargest(n, y)
    fig = px.bar(
        top, x=x, y=y, color=color or x,
        title=title, labels={x: xlab or x, y: ylab or y},
        height=height,
    )
    fig.update_layout(showlegend=False, margin=dict(t=50, b=20))
    return fig


def heatmap_anomalia(
    df: pd.DataFrame,
    x: str = "mes",
    y: str = "uf",
    z: str = "anomalia_chuva",
    title: str = "Anomalia de Chuva por UF e Mês",
    height: int = 450,
) -> go.Figure:
    pivot = df.pivot_table(index=y, columns=x, values=z, aggfunc="mean")
    fig = px.imshow(
        pivot,
        color_continuous_scale="RdBu",
        color_continuous_midpoint=0,
        title=title,
        labels={"x": "Mês", "y": "UF", "color": z},
        height=height,
    )
    fig.update_layout(margin=dict(t=50, b=20))
    return fig


def scatter_correlacao(
    df: pd.DataFrame,
    x: str,
    y: str,
    color: str = "uf",
    title: str = "",
    xlab: str = "",
    ylab: str = "",
    trendline: bool = True,
    height: int = 450,
) -> go.Figure:
    kwargs = dict(trendline="ols") if trendline else {}
    fig = px.scatter(
        df, x=x, y=y, color=color,
        title=title, labels={x: xlab or x, y: ylab or y},
        hover_data=df.columns.tolist(),
        height=height,
        **kwargs,
    )
    fig.update_layout(margin=dict(t=50, b=20))
    return fig


def barchart_lag(
    cc_series: pd.Series,
    title: str = "Cross-correlation por Defasagem",
    height: int = 350,
) -> go.Figure:
    df_plot = cc_series.reset_index()
    df_plot.columns = ["lag", "pearson_r"]
    df_plot["cor"] = df_plot["pearson_r"].apply(lambda v: "positivo" if v >= 0 else "negativo")

    fig = px.bar(
        df_plot, x="lag", y="pearson_r",
        color="cor",
        color_discrete_map={"positivo": "#1a7abf", "negativo": "#d94e4e"},
        title=title,
        labels={"lag": "Defasagem (meses)", "pearson_r": "Pearson r"},
        height=height,
    )
    fig.add_hline(y=0, line_dash="dash", line_color="black", line_width=1)
    fig.update_layout(showlegend=False, margin=dict(t=50, b=20))
    return fig


def heatmap_pearson(
    df_pearson: pd.DataFrame,
    index_col: str = "uf",
    title: str = "Correlação de Pearson: Clima × Produção",
    height: int = 450,
) -> go.Figure:
    numeric_cols = df_pearson.select_dtypes("number").columns.tolist()
    pivot = df_pearson.set_index(index_col)[numeric_cols]

    fig = px.imshow(
        pivot,
        color_continuous_scale="RdBu",
        color_continuous_midpoint=0,
        zmin=-1, zmax=1,
        title=title,
        labels={"color": "r"},
        text_auto=".2f",
        height=height,
    )
    fig.update_layout(margin=dict(t=50, b=20))
    return fig


def linha_ipca(
    df: pd.DataFrame,
    title: str = "IPCA Alimentação e Bebidas (variação mensal %)",
    height: int = 400,
) -> go.Figure:
    fig = go.Figure()

    if "ipca_var_mensal" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["periodo"], y=df["ipca_var_mensal"],
            name="Alimentação e Bebidas",
            line=dict(color="#e07b39", width=2),
            mode="lines",
        ))

    # Linha de referência em 0
    fig.add_hline(y=0, line_dash="dot", line_color="gray", line_width=1)

    fig.update_layout(
        title=title, height=height,
        xaxis_title="Mês/Ano", yaxis_title="Variação mensal (%)",
        legend_title_text="",
        margin=dict(t=50, b=20),
    )
    return fig
