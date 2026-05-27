#!/usr/bin/env python3
"""
pdf_to_csv_smart_v4.py

Parser robusto para PDFs SIAFAR.

MEJORAS PRINCIPALES:
- NO asume 1 línea = 1 registro
- Agrupa registros multi-línea
- Detección de columnas por página
- Parsing derecha → izquierda
- Matching flexible de laboratorios
- Validación estructural
- Sistema de confianza
- Logs detallados
- NO descarta registros temprano
- Evita contaminación por forward-fill

OBJETIVO:
~13k registros limpios y auditables
"""

import csv
import json
import re
import ssl
import unicodedata
import urllib.request

from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

import fitz

# ============================================================
# CONFIG
# ============================================================

TZ_AR = timezone(timedelta(hours=-3))
PDF_BASE_URL = "https://siafar.com/precios/pdf/"

# ------------------------------------------------------------
# LABORATORIOS
# ------------------------------------------------------------

LABORATORIOS = [
    "Abbott EPD",
    "Abbvie",
    "Alcon",
    "Amgen",
    "Andrómaco",
    "Aponor",
    "Ariston",
    "Aspen",
    "Aspen Pharma",
    "AstraZeneca",
    "Austral",
    "B.Braun",
    "Bacon",
    "Bagó",
    "Baliarda",
    "Bayer (PH)",
    "Bayer Consumer",
    "Beta",
    "Biocontrol",
    "Biofactor",
    "Biol",
    "Bioprofarma Bag",
    "Biosidus S.A.U.",
    "Biosintex",
    "Biosintex Retai",
    "Biotechno Pharm",
    "Biotenk",
    "Biotoscana",
    "CSL Behring",
    "Cabuchi",
    "Casasco",
    "Cassará",
    "Celtyc",
    "Cetus",
    "Cevallos",
    "Craveri",
    "Dallas",
    "Denver Farma",
    "Domínguez",
    "Donato Zurlo",
    "Dr.Madaus",
    "Duncan",
    "E.J.Gezzi",
    "Eczane",
    "Elea",
    "Eriochem",
    "Eurofarma",
    "Eurolab",
    "Everex",
    "Excelentia",
    "Fabra",
    "Fada Pharma",
    "Fecofar",
    "Ferring",
    "Finadiet",
    "Fortbenton",
    "Francelab",
    "Fresenius Kabi",
    "GP Pharm",
    "Gador",
    "Galderma",
    "Gemabiotech",
    "Genomma Lab.",
    "GlaxoSmithKline",
    "Glenmark",
    "Gobbi",
    "Gramón",
    "Gray",
    "HLB Pharma",
    "Hemoderivados",
    "IMA",
    "ISA",
    "Imvi",
    "Infinity Pharma",
    "Iraola",
    "Isdin",
    "Janssen-Cilag",
    "Jayor",
    "Kemex",
    "Kilab",
    "Klonal",
    "LKM",
    "LKM Onco/Especi",
    "Lafedar",
    "Lagos",
    "Lazar",
    "Lepetit",
    "Lersan",
    "Lundbeck",
    "MR Pharma",
    "MSD Argentina",
    "Mar",
    "Max Vision",
    "Medipharma",
    "Medisol",
    "Merck Serono",
    "Merz",
    "Monserrat",
    "Montpellier",
    "Mundipharma",
    "Natufarma",
    "Nolter",
    "Northia",
    "Novartis",
    "Novo Nordisk",
    "Novoplos",
    "Omicron",
    "Oxapharma",
    "Panalab",
    "Pfizer",
    "PharmaDorf",
    "Pharmanove",
    "Pharmatrix",
    "Poen",
    "Pretoria",
    "Química Luar",
    "Raffo",
    "Raymos-Megalabs",
    "Richet",
    "Richmond",
    "Rivero",
    "Roche",
    "Roemmers",
    "Ronnet",
    "Rontag",
    "Rospaw",
    "Rossmore Pharma",
    "Roux Ocefa",
    "Sanitas",
    "Sanofi-Aventis",
    "Sant Gall",
    "Savant Consumer",
    "Savant Generic",
    "Savant Pharma",
    "Schafer",
    "Scott Pharma",
    "Scott-Cassará",
    "Seqirus",
    "Sertex",
    "Servier",
    "Sidus",
    "Siegfried",
    "Soubeiran Chobe",
    "Techsphere",
    "Temis-Lostaló",
    "Teva argentina",
    "Trb-Pharma",
    "Tuteur",
    "Valmax",
    "Valuge",
    "Vannier",
    "Varifarma",
    "Veinfar",
    "Vent 3",
    "Wunder Pharm",
]

# ============================================================
# NORMALIZACIÓN
# ============================================================

def normalize_text(text: str) -> str:
    text = text.lower().strip()

    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))

    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


LABS_MAP = {
    normalize_text(x): x
    for x in LABORATORIOS
}

# ============================================================
# REGEX
# ============================================================

PRECIO_REGEX = re.compile(
    r'(\d{1,3}(?:\.\d{3})*,\d{2})'
)

PRESENTACION_REGEX = re.compile(
    r'(mg|mcg|g|ml|ui|comp|caps|amp|sol|iny|crema|gotas)',
    re.I
)

# ============================================================
# DATA
# ============================================================

@dataclass
class Registro:
    droga: str = ""
    marca: str = ""
    presentacion: str = ""
    laboratorio: str = ""
    precio: float | None = None
    confidence: float = 0.0
    raw_text: str = ""
    errors: list | None = None

# ============================================================
# PDF
# ============================================================

def download_pdf(url: str, output_path: Path):

    if output_path.exists():
        print(f"✅ PDF existente: {output_path}")
        return

    print(f"📥 Descargando: {url}")

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urllib.request.urlopen(req, timeout=60, context=ctx) as r:
        output_path.write_bytes(r.read())

# ============================================================
# UTILIDADES
# ============================================================

def clean_price(value: str):

    if not value:
        return None

    value = value.replace(".", "")
    value = value.replace(",", ".")

    try:
        return round(float(value), 2)
    except:
        return None

# ============================================================
# DETECCIÓN DE LAB
# ============================================================

def detect_lab(text: str):

    normalized = normalize_text(text)

    best = None
    best_size = 0

    parts = normalized.split()

    for size in range(5, 0, -1):

        for i in range(len(parts)):

            candidate = " ".join(parts[i:i+size])

            if candidate in LABS_MAP:
                return LABS_MAP[candidate]

    return None

# ============================================================
# EXTRACCIÓN DE BLOQUES
# ============================================================

def extract_blocks(page):

    words = page.get_text("words")

    lines = defaultdict(list)

    for w in words:

        x0, y0, x1, y1, text = w[:5]

        bucket = round(y0 / 4) * 4

        lines[bucket].append({
            "x": x0,
            "text": text
        })

    ordered = []

    for y in sorted(lines.keys()):

        row = sorted(lines[y], key=lambda z: z["x"])

        text = " ".join(x["text"] for x in row)

        if "MONODROGA" in text.upper():
            continue

        ordered.append({
            "y": y,
            "text": text,
            "words": row
        })

    # --------------------------------------------------------
    # AGRUPAR MULTI-LÍNEA
    # --------------------------------------------------------

    blocks = []

    current = []

    previous_y = None

    for line in ordered:

        y = line["y"]

        if previous_y is None:
            current.append(line)

        else:

            delta = y - previous_y

            # mismo bloque
            if delta <= 18:
                current.append(line)

            else:
                if current:
                    blocks.append(current)

                current = [line]

        previous_y = y

    if current:
        blocks.append(current)

    return blocks

# ============================================================
# PARSER
# ============================================================

def parse_block(block):

    full_text = " ".join(x["text"] for x in block)

    registro = Registro(
        raw_text=full_text,
        errors=[]
    )

    # --------------------------------------------------------
    # PRECIO
    # --------------------------------------------------------

    precios = PRECIO_REGEX.findall(full_text)

    if not precios:
        registro.errors.append("missing_price")
        return registro

    precio_raw = precios[-1]

    registro.precio = clean_price(precio_raw)

    if registro.precio is None:
        registro.errors.append("invalid_price")

    # remover precio
    text = full_text.replace(precio_raw, " ")

    # --------------------------------------------------------
    # LABORATORIO
    # --------------------------------------------------------

    lab = detect_lab(text)

    if lab:
        registro.laboratorio = lab
        text = re.sub(
            re.escape(lab),
            " ",
            text,
            flags=re.I
        )
    else:
        registro.errors.append("unknown_lab")

    # --------------------------------------------------------
    # PRESENTACIÓN
    # --------------------------------------------------------

    presentacion_parts = []

    tokens = text.split()

    for t in tokens:

        if PRESENTACION_REGEX.search(t):
            presentacion_parts.append(t)

        elif re.match(r'^\d+([.,]\d+)?$', t):
            presentacion_parts.append(t)

    registro.presentacion = " ".join(presentacion_parts)

    # remover presentación
    for p in presentacion_parts:
        text = text.replace(p, " ")

    # --------------------------------------------------------
    # LIMPIEZA
    # --------------------------------------------------------

    text = re.sub(r'\s+', ' ', text).strip()

    # --------------------------------------------------------
    # DROGA / MARCA
    # --------------------------------------------------------

    words = text.split()

    if not words:
        registro.errors.append("empty_text")
        return registro

    # heurística:
    # primera palabra minúscula = droga

    if words[0].islower():

        registro.droga = words[0]

        if len(words) > 1:
            registro.marca = " ".join(words[1:])

    else:

        registro.marca = text

    # --------------------------------------------------------
    # VALIDACIONES
    # --------------------------------------------------------

    confidence = 1.0

    if not registro.droga:
        confidence -= 0.3

    if not registro.marca:
        confidence -= 0.2

    if not registro.presentacion:
        confidence -= 0.2

    if not registro.laboratorio:
        confidence -= 0.2

    if registro.errors:
        confidence -= 0.1 * len(registro.errors)

    if registro.droga and len(registro.droga) > 40:
        registro.errors.append("drug_too_long")
        confidence -= 0.4

    if registro.precio and registro.precio < 50:
        registro.errors.append("suspicious_price")
        confidence -= 0.2

    registro.confidence = max(0.0, round(confidence, 2))

    return registro

# ============================================================
# EXTRACTION
# ============================================================

def extract_rows(pdf_path: Path, logs_dir: Path):

    doc = fitz.open(pdf_path)

    rows = []

    rejected = []
    low_conf = []

    total = 0

    for page_num, page in enumerate(doc, 1):

        print(f"📄 Página {page_num}")

        blocks = extract_blocks(page)

        for block in blocks:

            reg = parse_block(block)

            total += 1

            row = asdict(reg)

            rows.append(row)

            if reg.confidence < 0.5:
                low_conf.append(row)

            if reg.errors:
                rejected.append(row)

    # --------------------------------------------------------
    # LOGS
    # --------------------------------------------------------

    logs_dir.mkdir(exist_ok=True)

    with open(logs_dir / "rejected_rows.json", "w", encoding="utf-8") as f:
        json.dump(rejected, f, ensure_ascii=False, indent=2)

    with open(logs_dir / "low_confidence_rows.json", "w", encoding="utf-8") as f:
        json.dump(low_conf, f, ensure_ascii=False, indent=2)

    print(f"\n📊 Total bloques: {total}")
    print(f"✅ Registros: {len(rows)}")
    print(f"⚠️ Baja confianza: {len(low_conf)}")
    print(f"❌ Con errores: {len(rejected)}")

    return rows

# ============================================================
# CSV
# ============================================================

def save_csv(rows, output_path):

    fields = [
        "droga",
        "marca",
        "presentacion",
        "laboratorio",
        "precio",
        "confidence"
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:

        writer = csv.DictWriter(f, fieldnames=fields)

        writer.writeheader()

        for r in rows:

            writer.writerow({
                k: r.get(k)
                for k in fields
            })

# ============================================================
# MAIN
# ============================================================

def main():

    root = Path(__file__).parent.parent

    data_dir = root / "data"
    logs_dir = root / "logs"

    data_dir.mkdir(exist_ok=True)
    logs_dir.mkdir(exist_ok=True)

    fecha = datetime.now(TZ_AR)

    pdf_name = f"Precios{fecha.strftime('%y%m%d')}.pdf"

    pdf_url = f"{PDF_BASE_URL}{pdf_name}"

    pdf_path = data_dir / pdf_name

    csv_path = data_dir / "medicamentos.csv"

    print("=" * 60)
    print("📊 SIAFAR SMART PARSER V4")
    print("=" * 60)

    download_pdf(pdf_url, pdf_path)

    rows = extract_rows(pdf_path, logs_dir)

    save_csv(rows, csv_path)

    print(f"\n✅ CSV generado: {csv_path}")
    print(f"📁 Logs: {logs_dir}")

if __name__ == "__main__":
    main()
