"""
Funções de visualização geoespacial com Plotly choropleth.
"""
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


def choropleth_uf(
    df: pd.DataFrame,
    geojson: dict,
    locations: str = "uf",
    values: str = "qtd_t",
    title: str = "",
    colorscale: str = "YlGn",
    featureidkey: str = "properties.sigla",
    height: int = 500,
    labels: dict | None = None,
) -> go.Figure:
    fig = px.choropleth(
        df,
        geojson=geojson,
        locations=locations,
        color=values,
        featureidkey=featureidkey,
        color_continuous_scale=colorscale,
        title=title,
        labels=labels or {values: values},
        height=height,
    )
    fig.update_geos(
        fitbounds="locations",
        visible=False,
    )
    fig.update_layout(margin=dict(t=50, r=0, l=0, b=0))
    return fig


def choropleth_pearson(
    df: pd.DataFrame,
    geojson: dict,
    value_col: str = "pearson_r",
    title: str = "Correlação Pearson por UF",
    height: int = 500,
) -> go.Figure:
    return choropleth_uf(
        df, geojson,
        values=value_col,
        colorscale="RdBu",
        title=title,
        height=height,
        labels={value_col: "Pearson r"},
    )
