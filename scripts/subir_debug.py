#!/usr/bin/env python3
"""
scripts/subir_debug.py
Sube medicamentos.pretty.json a la release "debug-latest" de GitHub,
sobreescribiendo el asset anterior en cada corrida.

No se commitea al repo ni se sirve desde el CDN — solo vive como
asset descargable bajo demanda en GitHub Releases.

URL fija de descarga:
  https://github.com/psbella/remediar/releases/download/debug-latest/medicamentos.pretty.json
"""
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

from github_release_helper import obtener_o_crear_release, subir_o_reemplazar_asset

AR_TZ      = timezone(timedelta(hours=-3))
BASE       = Path(__file__).parent.parent
PRETTY_SRC = BASE / ".debug" / "medicamentos.pretty.json"
TAG        = "debug-latest"
NOMBRE     = "Debug — Última corrida del ETL"
ASSET_NAME = "medicamentos.pretty.json"


def main():
    if not PRETTY_SRC.exists():
        print(f"ERROR: no se encontró {PRETTY_SRC}")
        sys.exit(1)

    ahora = datetime.now(AR_TZ)
    contenido = PRETTY_SRC.read_bytes()

    print(f"\nSubiendo debug — {ahora.strftime('%Y-%m-%d %H:%M')} AR")
    print(f"   Tamaño: {len(contenido) / 1024:.0f} KB")

    body = (
        f"JSON formateado (indent=2) de la última corrida del ETL, "
        f"para debug humano. Se sobreescribe en cada actualización.\n\n"
        f"Última actualización: {ahora.strftime('%Y-%m-%d %H:%M')} AR"
    )
    release = obtener_o_crear_release(TAG, NOMBRE, body)

    resultado = subir_o_reemplazar_asset(release, ASSET_NAME, contenido, "application/json")
    print(f"   ✅ Subido: {resultado['browser_download_url']}")


if __name__ == "__main__":
    main()
