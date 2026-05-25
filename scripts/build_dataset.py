"""
Orquestrador ETL: lê os dados brutos e gera os CSVs processados.

Uso:
    python scripts/build_dataset.py
    python scripts/build_dataset.py --skip-inmet   # pula limpeza INMET (usa cache)
"""
import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parents[1]))
from src.config import ANOS, CULTURAS, PATH_PROCESSED, PATH_RAW_SIDRA, UFS_ALVO
from src.data_fetch.geo import download_geojson
from src.data_fetch.sidra_ipca import fetch_ipca, fetch_ipca_nacional, save_ipca
from src.data_fetch.sidra_pam import fetch_pam, save_pam
from src.processing.clean import add_anomalias, clean_inmet, clean_ipca, clean_pam
from src.processing.merge import build_anual, build_mensal, save_datasets


def parse_args():
    p = argparse.ArgumentParser(description="Build dataset processado a partir dos dados brutos")
    p.add_argument("--skip-inmet", action="store_true", help="Não reprocessar INMET (usa CSV já salvo)")
    p.add_argument("--skip-sidra", action="store_true", help="Não re-baixar SIDRA (usa CSV já salvo)")
    p.add_argument("--skip-geo", action="store_true", help="Não re-baixar GeoJSON")
    return p.parse_args()


def step(label: str):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")


def main():
    args = parse_args()
    t0 = time.time()

    PATH_PROCESSED.mkdir(parents=True, exist_ok=True)

    # ── 1. GeoJSON ────────────────────────────────────────────────────────────
    step("1/5  GeoJSON de UFs")
    if not args.skip_geo:
        download_geojson()
    else:
        print("  pulado (--skip-geo)")

    # ── 2. SIDRA: PAM e IPCA ─────────────────────────────────────────────────
    step("2/5  SIDRA: PAM e IPCA")
    pam_path = PATH_RAW_SIDRA / "pam.csv"
    ipca_path = PATH_RAW_SIDRA / "ipca_alimentacao.csv"

    if not args.skip_sidra:
        df_pam_raw = fetch_pam()
        save_pam(df_pam_raw)

        df_ipca_rm = fetch_ipca()
        df_ipca_br = fetch_ipca_nacional()
        df_ipca_raw = pd.concat([df_ipca_rm, df_ipca_br], ignore_index=True)
        save_ipca(df_ipca_raw)
    else:
        print("  Carregando PAM e IPCA do disco (--skip-sidra) ...")
        df_pam_raw = pd.read_csv(pam_path)
        df_ipca_raw = pd.read_csv(ipca_path)

    # ── 3. Limpeza SIDRA ─────────────────────────────────────────────────────
    step("3/5  Limpeza PAM e IPCA")
    df_pam = clean_pam(df_pam_raw)
    print(f"  PAM limpo: {len(df_pam):,} linhas, culturas: {df_pam['cultura'].unique().tolist()}")

    df_ipca = clean_ipca(df_ipca_raw)
    print(f"  IPCA limpo: {len(df_ipca):,} linhas, UFs: {sorted(df_ipca['uf'].unique())}")

    # ── 4. INMET: limpeza e anomalias ────────────────────────────────────────
    step("4/5  INMET: limpeza + anomalias")
    clima_cache = PATH_PROCESSED / "clima_mensal_raw.csv"

    if not args.skip_inmet:
        df_clima_raw = clean_inmet()
        df_clima = add_anomalias(df_clima_raw)
        df_clima.to_csv(clima_cache, index=False, encoding="utf-8")
        print(f"  Clima mensal: {len(df_clima):,} linhas, UFs: {sorted(df_clima['uf'].unique())}")
    else:
        if not clima_cache.exists():
            raise FileNotFoundError(f"Cache INMET não encontrado: {clima_cache}. Rode sem --skip-inmet.")
        print(f"  Carregando INMET do cache {clima_cache} (--skip-inmet) ...")
        df_clima = pd.read_csv(clima_cache)

    # ── 5. Merge e salvamento ────────────────────────────────────────────────
    step("5/5  Merge e salvamento dos datasets processados")
    df_mensal = build_mensal(df_clima, df_ipca)
    df_anual = build_anual(df_clima, df_pam, df_ipca)
    save_datasets(df_mensal, df_anual)

    # Metadata
    metadata = {
        "build_date": datetime.now().isoformat(),
        "anos": ANOS,
        "ufs_alvo": UFS_ALVO,
        "culturas": list(CULTURAS.keys()),
        "linhas_mensal": len(df_mensal),
        "linhas_anual": len(df_anual),
        "fontes": {
            "clima": "INMET - Instituto Nacional de Meteorologia (portal.inmet.gov.br/dadoshistoricos)",
            "producao": "IBGE - SIDRA Tabela 5457 (Produção Agrícola Municipal)",
            "ipca": "IBGE - SIDRA Tabela 7060 (IPCA Alimentação e Bebidas por Região Metropolitana)",
            "geojson": "codeforgermany/click_that_hood (github.com)",
        },
    }
    meta_path = PATH_PROCESSED / "metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    print(f"  Metadata salvo em {meta_path}")

    elapsed = time.time() - t0
    print(f"\n  ETL concluído em {elapsed:.1f}s")


if __name__ == "__main__":
    main()
