#!/usr/bin/env python3
"""
pipeline.py — Orquestador del ETL de remedi.ar.

Ejecuta en orden:
  1. extraer.py     → data/raw.json
  2. normalizar.py  → data/normalizado.json
  3. enriquecer.py  → data/medicamentos.json + presentaciones_debug.csv

Uso:
  python scripts/pipeline.py              # pipeline completo
  python scripts/pipeline.py --normalizar # solo etapas 2 y 3 (sin bajar el PDF)
  python scripts/pipeline.py --enriquecer # solo etapa 3 (iterar el parser)
"""

import sys
import time
from pathlib import Path

# Importar los módulos directamente para evitar subprocess
sys.path.insert(0, str(Path(__file__).parent))

import extraer
import normalizar
import enriquecer


def correr_etapa(nombre: str, fn):
    print(f"\n{'═'*60}")
    print(f"  {nombre}")
    print(f"{'═'*60}")
    t0 = time.time()
    fn()
    print(f"\n  ✓ {nombre} completado en {time.time()-t0:.1f}s")


def main():
    args = set(sys.argv[1:])

    solo_normalizar = '--normalizar' in args
    solo_enriquecer = '--enriquecer' in args

    if solo_enriquecer:
        correr_etapa("ENRIQUECER", enriquecer.main)
    elif solo_normalizar:
        correr_etapa("NORMALIZAR", normalizar.main)
        correr_etapa("ENRIQUECER", enriquecer.main)
    else:
        correr_etapa("EXTRAER",    extraer.main)
        correr_etapa("NORMALIZAR", normalizar.main)
        correr_etapa("ENRIQUECER", enriquecer.main)

    print(f"\n{'═'*60}")
    print("  Pipeline completado")
    print(f"{'═'*60}\n")


if __name__ == "__main__":
    main()
