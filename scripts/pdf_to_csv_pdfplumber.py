#!/usr/bin/env python3
"""
pdf_to_csv_pdfplumber.py — Extractor robusto de precios SIAFAR.

Estrategia: extract_words() + clasificación por coordenada X.
Esto evita que pdfplumber colapse celdas vacías y corra los índices.

Columnas del PDF: MONODROGA | NOMBRE | PRESENTACION | LABORATORIO | PRECIO | Precio.Afil.PAMI
Columnas del CSV: droga | marca | presentacion | laboratorio | precio
"""

import csv
import re
import ssl
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    import pdfplumber
except ModuleNotFoundError:  # pragma: no cover - depende del entorno
    pdfplumber = None

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

TMP_PDF   = Path("/tmp/precios_siafar.pdf")
OUTPUT_CSV = DATA_DIR / "medicamentos.csv"

FIELDNAMES = ["droga", "marca", "presentacion", "laboratorio", "precio"]

# Palabras que indican fila de encabezado (ignorar)
HEADER_WORDS = {"monodroga", "nombre", "presentacion", "laboratorio",
                "precio", "afil", "pami", "p.afil.pami"}


def build_pdf_url() -> str:
    arg_tz = timezone(timedelta(hours=-3))
    hoy = datetime.now(arg_tz).strftime("%y%m%d")
    return f"https://siafar.com/precios/pdf/Precios{hoy}.pdf"


# ---------------------------------------------------------------------------
# Descarga
# ---------------------------------------------------------------------------
def download_pdf(url: str, dest: Path) -> None:
    print(f"📥 Descargando: {url}")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept":          "application/pdf,*/*",
        "Accept-Language": "es-AR,es;q=0.9",
        "Referer":         "https://siafar.com/",
    })
    with urllib.request.urlopen(req, timeout=60, context=ctx) as r:
        dest.write_bytes(r.read())
    print(f"   → {dest.stat().st_size / 1024:.1f} KB")


# ---------------------------------------------------------------------------
# Detección de límites de columna a partir del encabezado
# ---------------------------------------------------------------------------
HEADER_LABELS = ["monodroga", "nombre", "presentacion", "laboratorio", "precio"]

def detect_column_boundaries(page) -> list[float] | None:
    """
    Busca la fila de encabezado en la página y devuelve las coordenadas X
    del borde izquierdo de cada columna [c0, c1, c2, c3, c4, c5_pami].
    Retorna None si no se encuentra encabezado en esta página.
    """
    words = page.extract_words(x_tolerance=3, y_tolerance=3)
    if not words:
        return None

    # Agrupar palabras por línea (misma y0 ± 4 px)
    lines: dict[int, list] = {}
    for w in words:
        key = round(w["top"] / 4) * 4
        lines.setdefault(key, []).append(w)

    for y_key in sorted(lines):
        line_words = sorted(lines[y_key], key=lambda w: w["x0"])
        text_lower = " ".join(w["text"].lower() for w in line_words)
        # Encabezado tiene al menos "monodroga" y "nombre" y "precio"
        if "monodroga" in text_lower and "nombre" in text_lower and "precio" in text_lower:
            # Extraer x0 de cada palabra de encabezado
            bounds = [w["x0"] for w in line_words
                      if w["text"].lower() not in {"afil.", "pami", "p.afil.pami"}]
            if len(bounds) >= 5:
                return bounds[:6]   # hasta 6 columnas

    return None


# ---------------------------------------------------------------------------
# Clasificar una palabra en una columna según los límites detectados
# ---------------------------------------------------------------------------
def classify_col(x0: float, boundaries: list[float]) -> int:
    """Devuelve el índice de columna (0-5) para una palabra en x0."""
    col = 0
    for i, bound in enumerate(boundaries):
        if x0 >= bound - 4:
            col = i
    return col


# ---------------------------------------------------------------------------
# Extracción por coordenadas
# ---------------------------------------------------------------------------
def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _parse_price(text: str) -> str:
    """Parsea precios en formato AR (ej: 1.234,56 o 1234.56)."""
    cleaned = re.sub(r"[^0-9,.-]", "", text).strip()
    if not cleaned:
        return ""

    # Si hay coma y punto, asumir AR: punto miles + coma decimal
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    # Solo coma: usarla como decimal
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    # Solo punto: puede ser decimal o miles. Si parece miles (grupos de 3), eliminar puntos.
    elif cleaned.count(".") > 1 or re.fullmatch(r"\d{1,3}(?:\.\d{3})+", cleaned):
        cleaned = cleaned.replace(".", "")

    # Mantener un único signo negativo al inicio si existiera
    cleaned = re.sub(r"(?!^)-", "", cleaned)

    try:
        return f"{float(cleaned):.2f}"
    except ValueError:
        return ""


def _is_header_line(cells: dict) -> bool:
    combined = " ".join(cells.values()).lower()
    return sum(1 for kw in HEADER_WORDS if kw in combined) >= 2


def extract_rows(pdf_path: Path) -> list[dict]:
    rows: list[dict] = []
    last_droga = ""
    col_boundaries: list[float] | None = None

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        print(f"   → {total_pages} páginas")

        for page_num, page in enumerate(pdf.pages, 1):
            # ── 1. Detectar límites de columna (una vez por página que tenga encabezado) ──
            new_bounds = detect_column_boundaries(page)
            if new_bounds:
                col_boundaries = new_bounds

            if col_boundaries is None:
                # Todavía no encontramos encabezado; intentar con extract_table como fallback
                continue

            # ── 2. Extraer palabras y agrupar por línea ──
            words = page.extract_words(x_tolerance=3, y_tolerance=3)
            if not words:
                continue

            lines: dict[int, list] = {}
            for w in words:
                key = round(w["top"] / 2) * 2   # agrupa por bloques de 2px
                lines.setdefault(key, []).append(w)

            # ── 3. Por cada línea, reconstruir las 6 celdas ──
            for y_key in sorted(lines):
                line_words = sorted(lines[y_key], key=lambda w: w["x0"])

                # Armar celdas indexadas por columna
                cells: dict[int, list[str]] = {i: [] for i in range(6)}
                for w in line_words:
                    col_idx = classify_col(w["x0"], col_boundaries)
                    cells[col_idx].append(w["text"])

                # Convertir a texto por columna
                cell_text = {i: _clean(" ".join(cells[i])) for i in range(6)}

                # Saltar encabezado y líneas vacías
                if _is_header_line(cell_text):
                    continue
                if not any(cell_text.values()):
                    continue

                col0 = cell_text[0]   # MONODROGA
                col1 = cell_text[1]   # NOMBRE / MARCA
                col2 = cell_text[2]   # PRESENTACION
                col3 = cell_text[3]   # LABORATORIO
                col4 = cell_text[4]   # PRECIO
                col5 = cell_text[5]   # Precio Afil. PAMI (a veces se corre)

                # Forward-fill de droga
                if col0:
                    last_droga = col0
                droga = last_droga

                # Necesitamos al menos precio para que la fila sea válida
                precio = _parse_price(col4) or _parse_price(col5)
                if not precio:
                    continue

                # Sanidad: marca no puede ser un número
                try:
                    float(col1.replace(",", "."))
                    continue  # marca numérica → fila corrida
                except ValueError:
                    pass

                if not col1:
                    continue  # sin marca → fila sin datos útiles

                rows.append({
                    "droga":        droga.lower(),
                    "marca":        col1.upper(),
                    "presentacion": col2,
                    "laboratorio":  col3 if col3 else "Desconocido",
                    "precio":       precio,
                })

            if page_num % 20 == 0:
                print(f"   → página {page_num}/{total_pages} — {len(rows)} filas acumuladas")

    return rows


# ---------------------------------------------------------------------------
# Guardar CSV
# ---------------------------------------------------------------------------
def save_csv(rows: list[dict], dest: Path) -> None:
    with open(dest, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    print(f"✅ {dest} → {len(rows)} medicamentos")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def _ensure_dependencies() -> None:
    if pdfplumber is None:
        print("❌ Falta dependencia: pdfplumber")
        print("   Instalá con: python -m pip install pdfplumber")
        print("   Si usás virtualenv: source .venv/bin/activate && python -m pip install pdfplumber")
        sys.exit(2)


def main() -> None:
    _ensure_dependencies()

    if len(sys.argv) > 1:
        pdf_path = Path(sys.argv[1])
        print(f"🔧 PDF local: {pdf_path}")
    else:
        url = build_pdf_url()
        download_pdf(url, TMP_PDF)
        pdf_path = TMP_PDF

    print("📊 Extrayendo con pdfplumber (coordenadas X)...")
    rows = extract_rows(pdf_path)

    if not rows:
        print("❌ Sin filas. Revisá el PDF o los límites de columna.")
        sys.exit(1)

    save_csv(rows, OUTPUT_CSV)


if __name__ == "__main__":
    main()
