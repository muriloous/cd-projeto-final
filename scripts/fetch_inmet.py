"""
Baixa os arquivos bulk anuais de estações automáticas do INMET.

Fonte: https://portal.inmet.gov.br/dadoshistoricos
Formato: 1 ZIP por ano → CSVs horários por estação.

Uso:
    python scripts/fetch_inmet.py
    python scripts/fetch_inmet.py --anos 2020 2021 2022
"""
import argparse
import sys
import zipfile
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parents[1]))
from src.config import ANOS, PATH_RAW_INMET

BASE_URL = "https://portal.inmet.gov.br/uploads/dadoshistoricos/{ano}.zip"
TIMEOUT = 120


def download_ano(ano: int, destino: Path, force: bool = False) -> bool:
    zip_path = destino / f"{ano}.zip"
    pasta_ano = destino / str(ano)

    if pasta_ano.exists() and any(pasta_ano.iterdir()) and not force:
        print(f"  {ano}: já extraído em {pasta_ano}, pulando.")
        return True

    url = BASE_URL.format(ano=ano)
    print(f"  {ano}: baixando {url} ...", end=" ", flush=True)
    try:
        resp = requests.get(url, timeout=TIMEOUT, stream=True)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"ERRO: {exc}")
        return False

    zip_path.write_bytes(resp.content)
    print(f"ok ({len(resp.content) / 1e6:.1f} MB)")

    print(f"  {ano}: extraindo ...", end=" ", flush=True)
    pasta_ano.mkdir(exist_ok=True)
    try:
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(pasta_ano)
        print("ok")
    except zipfile.BadZipFile as exc:
        print(f"ERRO ao extrair: {exc}")
        return False

    zip_path.unlink(missing_ok=True)
    return True


def main():
    parser = argparse.ArgumentParser(description="Download dados históricos INMET")
    parser.add_argument("--anos", nargs="+", type=int, default=ANOS, help="Anos a baixar")
    parser.add_argument("--force", action="store_true", help="Re-baixar mesmo se já extraído")
    args = parser.parse_args()

    PATH_RAW_INMET.mkdir(parents=True, exist_ok=True)
    erros = []
    for ano in sorted(args.anos):
        ok = download_ano(ano, PATH_RAW_INMET, force=args.force)
        if not ok:
            erros.append(ano)

    if erros:
        print(f"\nAnos com falha: {erros}")
        sys.exit(1)
    print("\nDownload concluído.")


if __name__ == "__main__":
    main()
