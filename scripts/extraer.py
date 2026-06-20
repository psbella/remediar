#!/usr/bin/env python3
"""
extraer.py — Descarga el PDF de SIAFAR y extrae los registros crudos.

Output: data/raw.json
  {
    "fecha":         "2026-06-19 05:13:35",
    "fuente":        "https://siafar.com/precios/pdf/",
    "total_extraido": 12400,
    "medicamentos":  [ { droga, marca, presentacion, laboratorio, precio }, ... ]
  }

No aplica ninguna corrección ni normalización. Lo que sale del PDF entra al JSON.
"""

import json
import re
import ssl
import sys
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

AR_TZ = timezone(timedelta(hours=-3))

try:
    import fitz
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pymupdf"])
    import fitz

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode   = ssl.CERT_NONE

BASE    = Path(__file__).parent.parent
RAW_PATH = BASE / "data" / "raw.json"

PDF_URL = "https://siafar.com/precios/pdf/"


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def limpiar_precio(valor: str) -> float | None:
    """Convierte string de precio a float. Retorna None si no es válido."""
    try:
        return float(valor.replace("$", "").replace(".", "").replace(",", ".").strip())
    except Exception:
        return None


def es_precio(texto: str) -> bool:
    """True si el texto es una línea de precio del PDF."""
    t = texto.strip().lstrip("$").replace(".", "").replace(",", "")
    return bool(re.match(r"^\d{1,10}$", t)) and float(t.replace(",", ".")) > 0


# ─────────────────────────────────────────────────────────────────────────────
# EXTRACCIÓN
# ─────────────────────────────────────────────────────────────────────────────

def descargar_pdf(url: str = PDF_URL) -> bytes:
    print(f"Descargando: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30, context=ssl_context) as r:
        data = r.read()
    print(f"Tamaño: {len(data):,} bytes")
    return data


def extraer_registros(pdf_bytes: bytes) -> list[dict]:
    """
    Parsea el PDF página a página y devuelve lista de registros crudos.
    Aplica solo la detección de desplazamiento de Capa 1 (estructura 4 vs 5 campos).
    """
    doc          = fitz.open(stream=pdf_bytes, filetype="pdf")
    medicamentos = []

    for pagina_num in range(len(doc)):
        texto  = doc[pagina_num].get_text()
        lineas = [l.strip() for l in texto.split("\n") if l.strip()]
        i = 0

        while i < len(lineas):
            linea = lineas[i]

            if "MONODROGA" in linea or "pag" in linea.lower():
                i += 1
                continue
            if es_precio(linea):
                i += 1
                continue

            # ── CAPA 1: detección de desplazamiento en tiempo de parse ──────
            #
            # Estructura normal (5 campos):
            #   i+0  droga
            #   i+1  marca
            #   i+2  presentacion
            #   i+3  laboratorio
            #   i+4  precio
            #
            # Estructura desplazada (4 campos, lab ausente en PDF):
            #   i+0  droga
            #   i+1  marca
            #   i+2  laboratorio   ← ocupa el slot de presentacion
            #   i+3  precio        ← sube un lugar

            if i + 3 < len(lineas) and es_precio(lineas[i + 3]):
                droga        = linea
                marca        = lineas[i + 1]
                presentacion = ""
                laboratorio  = lineas[i + 2]
                precio_str   = lineas[i + 3]
                avance       = 4
            elif i + 4 < len(lineas):
                droga        = linea
                marca        = lineas[i + 1]
                presentacion = lineas[i + 2]
                laboratorio  = lineas[i + 3]
                precio_str   = lineas[i + 4]
                avance       = 5
            else:
                i += 1
                continue

            if es_precio(precio_str):
                precio = limpiar_precio(precio_str)
                if precio and droga:
                    medicamentos.append({
                        "droga":        droga.lower(),
                        "marca":        marca.upper(),
                        "presentacion": presentacion,
                        "laboratorio":  laboratorio if not es_precio(laboratorio) else "Desconocido",
                        "precio":       precio,
                    })
                i += avance
                continue

            i += 1

        if (pagina_num + 1) % 10 == 0:
            print(f"  Página {pagina_num + 1}: {len(medicamentos)} registros")

    doc.close()
    return medicamentos


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    pdf_bytes    = descargar_pdf()
    medicamentos = extraer_registros(pdf_bytes)

    print(f"\nTotal extraído: {len(medicamentos)}")

    if not medicamentos:
        print("No se extrajo ningún medicamento.")
        sys.exit(1)

    ahora    = datetime.now(AR_TZ)
    raw_data = {
        "fecha":          ahora.strftime("%Y-%m-%d %H:%M:%S"),
        "fuente":         PDF_URL,
        "total_extraido": len(medicamentos),
        "medicamentos":   medicamentos,
    }

    RAW_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RAW_PATH, "w", encoding="utf-8") as f:
        json.dump(raw_data, f, ensure_ascii=False, separators=(",", ":"))

    print(f"Guardado: {RAW_PATH}")


if __name__ == "__main__":
    main()
