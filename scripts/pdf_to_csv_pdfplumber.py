#!/usr/bin/env python3
"""
Extractor de precios de medicamentos desde SIAFAR.
Usa pdfplumber para extraer tablas sin depender de Java ni OpenCV.

Columnas del PDF: MONODROGA | NOMBRE | PRESENTACION | LABORATORIO | PRECIO | Precio.Afil.PAMI
Columnas del CSV: droga | marca | presentacion | laboratorio | precio
"""

import csv
import ssl
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pdfplumber

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

TMP_PDF = Path("/tmp/precios_siafar.pdf")
OUTPUT_CSV = DATA_DIR / "medicamentos.csv"

# La URL cambia a diario: Precios AAMMDD .pdf  (ej: Precios260527.pdf)
def build_pdf_url() -> str:
    arg_tz = timezone(timedelta(hours=-3))
    hoy = datetime.now(arg_tz).strftime("%y%m%d")   # 260527
    return f"https://siafar.com/precios/pdf/Precios{hoy}.pdf"

# ---------------------------------------------------------------------------
# Descarga
# ---------------------------------------------------------------------------
def download_pdf(url: str, dest: Path) -> None:
    print(f"📥 Descargando: {url}")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60, context=ctx) as r:
        dest.write_bytes(r.read())
    print(f"   → {dest.stat().st_size / 1024:.1f} KB descargados")

# ---------------------------------------------------------------------------
# Detección de encabezado
# ---------------------------------------------------------------------------
HEADER_KEYWORDS = {"monodroga", "nombre", "presentacion", "laboratorio", "precio"}

def _is_header_row(cells: list[str]) -> bool:
    joined = " ".join(cells).lower()
    hits = sum(1 for kw in HEADER_KEYWORDS if kw in joined)
    return hits >= 3

# ---------------------------------------------------------------------------
# Normalización de fila
# ---------------------------------------------------------------------------
def _clean(text: str) -> str:
    return (text or "").replace("\n", " ").strip()

def _parse_price(text: str) -> str:
    """Devuelve el precio como string numérico o vacío."""
    cleaned = text.replace("$", "").replace(",", ".").replace(" ", "").strip()
    try:
        val = float(cleaned)
        return f"{val:.2f}"
    except ValueError:
        return ""

# ---------------------------------------------------------------------------
# Extracción principal
# ---------------------------------------------------------------------------
def extract_rows(pdf_path: Path) -> list[dict]:
    """
    Estrategia:
    1. pdfplumber.extract_table() con configuraciones explícitas de bordes.
    2. Fallback a extract_words() agrupado por línea si la tabla no detecta columnas.

    El PDF SIAFAR tiene 6 columnas:
      [0] MONODROGA  [1] NOMBRE  [2] PRESENTACION  [3] LABORATORIO  [4] PRECIO  [5] PAMI (ignorar)

    El campo MONODROGA puede estar vacío en filas que son continuación de la misma
    droga → propagamos el valor anterior (forward-fill).
    """
    rows: list[dict] = []
    last_droga = ""

    table_settings = {
        "vertical_strategy": "lines",
        "horizontal_strategy": "lines",
        "snap_tolerance": 3,
        "join_tolerance": 3,
        "edge_min_length": 10,
    }

    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        print(f"   → {total} páginas en el PDF")

        for page_num, page in enumerate(pdf.pages, 1):
            table = page.extract_table(table_settings)

            if not table:
                # Fallback: algunas páginas no tienen bordes visibles
                table = page.extract_table({
                    "vertical_strategy": "text",
                    "horizontal_strategy": "text",
                    "snap_tolerance": 5,
                })

            if not table:
                continue

            for raw_row in table:
                # pdfplumber puede devolver None en celdas vacías
                cells = [_clean(c) if c else "" for c in raw_row]

                # Saltear filas muy cortas o con pocas celdas útiles
                non_empty = [c for c in cells if c]
                if len(non_empty) < 2:
                    continue

                # Saltear encabezados
                if _is_header_row(cells):
                    continue

                # Aseguramos al menos 5 posiciones
                while len(cells) < 6:
                    cells.append("")

                droga        = cells[0]
                marca        = cells[1]
                presentacion = cells[2]
                laboratorio  = cells[3]
                precio_raw   = cells[4]
                # cells[5] = PAMI → ignorado

                # Forward-fill de droga (filas de continuación)
                if droga:
                    last_droga = droga
                else:
                    droga = last_droga

                precio = _parse_price(precio_raw)
                if not precio:
                    # Si el campo precio está vacío probablemente sea ruido
                    continue

                # Validación básica: marca no puede ser numérica pura
                try:
                    float(marca.replace(",", "."))
                    # Si marca es un número, las columnas están corridas → skip
                    continue
                except ValueError:
                    pass

                rows.append({
                    "droga":        droga.lower(),
                    "marca":        marca.upper(),
                    "presentacion": presentacion,
                    "laboratorio":  laboratorio if laboratorio else "Desconocido",
                    "precio":       precio,
                })

    return rows

# ---------------------------------------------------------------------------
# Persistencia
# ---------------------------------------------------------------------------
def save_csv(rows: list[dict], dest: Path) -> None:
    fieldnames = ["droga", "marca", "presentacion", "laboratorio", "precio"]
    with open(dest, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"✅ CSV guardado en {dest} → {len(rows)} medicamentos")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    url = build_pdf_url()

    # Permitir override por argumento (útil para testear con un PDF local)
    if len(sys.argv) > 1:
        pdf_path = Path(sys.argv[1])
        print(f"🔧 Usando PDF local: {pdf_path}")
    else:
        download_pdf(url, TMP_PDF)
        pdf_path = TMP_PDF

    print("📊 Extrayendo tabla con pdfplumber...")
    rows = extract_rows(pdf_path)

    if not rows:
        print("❌ No se extrajeron filas. Revisar el PDF manualmente.")
        sys.exit(1)

    save_csv(rows, OUTPUT_CSV)

if __name__ == "__main__":
    main()
