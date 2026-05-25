"""
Baixa e armazena o GeoJSON simplificado das Unidades Federativas do Brasil.

Fonte: click_that_hood (versão simplificada ~50 KB — adequada para Plotly choropleth).
"""
import json
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parents[2]))
from src.config import PATH_RAW_GEO

GEOJSON_URL = (
    "https://raw.githubusercontent.com/codeforgermany/click_that_hood"
    "/main/public/data/brazil-states.geojson"
)
GEOJSON_PATH = PATH_RAW_GEO / "ufs.geojson"

# Normaliza o campo de sigla para uso no Plotly (locations="sigla")
_NOME_PARA_SIGLA = {
    "Acre": "AC", "Alagoas": "AL", "Amapá": "AP", "Amazonas": "AM",
    "Bahia": "BA", "Ceará": "CE", "Distrito Federal": "DF",
    "Espírito Santo": "ES", "Goiás": "GO", "Maranhão": "MA",
    "Mato Grosso": "MT", "Mato Grosso do Sul": "MS", "Minas Gerais": "MG",
    "Pará": "PA", "Paraíba": "PB", "Paraná": "PR", "Pernambuco": "PE",
    "Piauí": "PI", "Rio de Janeiro": "RJ", "Rio Grande do Norte": "RN",
    "Rio Grande do Sul": "RS", "Rondônia": "RO", "Roraima": "RR",
    "Santa Catarina": "SC", "São Paulo": "SP", "Sergipe": "SE",
    "Tocantins": "TO",
}


def download_geojson(force: bool = False) -> dict:
    if GEOJSON_PATH.exists() and not force:
        print(f"  GeoJSON já existe em {GEOJSON_PATH}, carregando do disco.")
        with open(GEOJSON_PATH, encoding="utf-8") as f:
            return json.load(f)

    print(f"  Baixando GeoJSON de UFs ...", flush=True)
    resp = requests.get(GEOJSON_URL, timeout=30)
    resp.raise_for_status()
    geojson = resp.json()

    # Adiciona campo "sigla" em cada feature para uso como key no choropleth
    for feature in geojson.get("features", []):
        nome = feature.get("properties", {}).get("name", "")
        sigla = _NOME_PARA_SIGLA.get(nome, "")
        feature["properties"]["sigla"] = sigla

    GEOJSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(GEOJSON_PATH, "w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False)
    print(f"  GeoJSON salvo em {GEOJSON_PATH}")
    return geojson


def load_geojson() -> dict:
    if not GEOJSON_PATH.exists():
        return download_geojson()
    with open(GEOJSON_PATH, encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    download_geojson(force=True)
