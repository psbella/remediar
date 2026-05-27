#!/usr/bin/env python3
"""
pdf_to_csv_smart.py - Parsea PDF de SIAFAR usando heurística de derecha a izquierda.
No depende de extract_table(), usa palabras y coordenadas + diccionario de laboratorios.
"""

import re
import csv
import urllib.request
import ssl
from pathlib import Path
from datetime import datetime, timezone, timedelta
import fitz

# ============================================================
# CONFIGURACIÓN
# ============================================================

TZ_AR = timezone(timedelta(hours=-3))
PDF_BASE_URL = "https://siafar.com/precios/pdf/"

# Diccionario de laboratorios conocidos (para anclaje)
LABS_CONOCIDOS = {
    "abbott epd", "abbvie", "abbvie (ex alle) recalcine", "alcon",
    "alef medical argentina", "amgen", "andrómaco", "aponor", "ariston",
    "aspen", "aspen pharma", "astrazeneca", "austral", "b.braun", "bacon",
    "bagó", "baliarda", "bausch & lomb argentina", "baxter argentina",
    "bayer (ph)", "bayer consumer", "beta", "biocontrol", "biofactor",
    "biol", "biopas argentina", "bioprofarma bag", "biosidus s.a.u.",
    "biosintex", "biosintex retai", "biotechno pharm", "biotenk",
    "biotoscana", "boehringer ingelheim", "csl behring", "cabuchi",
    "casasco", "cassará", "celnova argentina", "celtyc", "cetus",
    "cevallos", "craveri", "dallas", "denver farma", "domínguez",
    "donato zurlo", "dr.madaus", "duncan", "e.j.gezzi", "eczane", "elea",
    "eriochem", "eurofarma", "eurolab", "everex", "excelentia", "fabra",
    "fada pharma", "fecofar", "ferring", "finadiet", "fortbenton",
    "francelab", "fresenius kabi", "gp pharm", "gador", "galderma",
    "gemabiotech", "genomma lab.", "glaxosmithkline", "glenmark", "gobbi",
    "gramón", "gray", "géminis farmacéutica", "hlb pharma", "hemoderivados",
    "ima", "isa", "imvi", "infinity pharma", "iraola", "isdin",
    "janssen-cilag", "jayor", "johnson & johnson", "kemex", "kilab",
    "klonal", "lkm", "lkm onco/especi", "laboratorio grafo",
    "laboratorio internacional", "laboratorio merck", "laboratorio valent",
    "laboratorios beta", "laboratorios ferrer", "laboratorios tuteur",
    "lafedar", "lagos", "lancaster pharma", "lazar", "lepetit", "lersan",
    "lundbeck", "mr pharma", "msd argentina", "mar", "max vision",
    "medipharma", "medisol", "merck serono", "merz", "microsules argentina",
    "monserrat", "montpellier", "mundipharma", "natufarma", "nolter",
    "northia", "novartis", "novo nordisk", "novoplos", "omicron",
    "opella healthcare", "organon argentina", "oxapharma", "panalab",
    "pfizer", "pharmadorf", "pharmalep s.a.", "pharmanove", "pharmatrix",
    "pierre fabre médicament", "pierre fabre oncologie", "poen", "pretoria",
    "procter & gamble", "química luar", "raffo", "raymos-megalabs",
    "reckitt benckiser", "richet", "richmond", "rivero", "roche",
    "roemmers", "ronnet", "rontag", "rospaw", "rossmore pharma",
    "roux ocefa", "sanitas", "sanofi pasteur argentina", "sanofi-aventis",
    "sant gall", "savant consumer", "savant generic", "savant pharma",
    "schafer", "scott pharma", "scott-cassará", "seqirus", "sertex",
    "servier", "sidus", "siegfried", "soubeiran chobe", "takeda argentina",
    "techsphere", "temis-lostaló", "teva argentina", "trb-pharma",
    "tuteur", "valmax", "valuge", "vannier", "vannier - grünenthal",
    "varifarma", "veinfar", "vent 3", "wunder pharm", "desconocido"
}

# Patrón de precio (formato argentino)
PRECIO_REGEX = re.compile(r'(\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2}|\d+\.\d+)')

# Patrón de presentación (unidades y formas farmacéuticas)
PRESENTACION_REGEX = re.compile(r'(mg|ml|g|ui|comp|caps|tabletas|comprimidos|suspension|solucion|jarabe|gotas|crema|unguento|aerosol|inyectable|cápsulas|comprimido|sobres|ampollas)', re.I)


def download_pdf(url: str, output_path: Path) -> Path:
    """Descarga el PDF si no existe localmente."""
    if output_path.exists():
        print(f"✅ Usando PDF existente: {output_path}")
        return output_path

    print(f"📥 Descargando: {url}")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60, context=ctx) as r:
        output_path.write_bytes(r.read())
    print(f"✅ PDF guardado: {output_path}")
    return output_path


def clean_price(price_str: str) -> float | None:
    """Convierte string de precio a float."""
    if not price_str:
        return None
    cleaned = re.sub(r'[^\d,.]', '', price_str)
    if ',' in cleaned and '.' in cleaned:
        if cleaned.rfind(',') > cleaned.rfind('.'):
            cleaned = cleaned.replace('.', '').replace(',', '.')
        else:
            cleaned = cleaned.replace(',', '')
    elif ',' in cleaned:
        cleaned = cleaned.replace(',', '.')
    try:
        return round(float(cleaned), 2)
    except ValueError:
        return None


def es_laboratorio(texto: str) -> bool:
    """Determina si un texto es un laboratorio conocido."""
    return texto.lower().strip() in LABS_CONOCIDOS


def es_presentacion(texto: str) -> bool:
    """Determina si un texto es una presentación (tiene mg/ml/etc)."""
    return bool(PRESENTACION_REGEX.search(texto))


def parsear_linea(palabras: list, current_droga: str) -> dict | None:
    """
    Parsea una lista de palabras de derecha a izquierda.
    Retorna dict con droga, marca, presentacion, laboratorio, precio.
    """
    if not palabras:
        return None

    texto_completo = " ".join(palabras)

    # 1. Extraer PRECIO (último token que coincide con regex)
    precio_token = None
    precio_valor = None
    for i in range(len(palabras) - 1, -1, -1):
        match = PRECIO_REGEX.search(palabras[i])
        if match:
            precio_token = match.group()
            precio_valor = clean_price(precio_token)
            if precio_valor is not None:
                palabras = palabras[:i] + palabras[i+1:]
                break

    if precio_valor is None:
        return None

    # 2. Extraer LABORATORIO (último token que es laboratorio conocido)
    laboratorio = None
    for i in range(len(palabras) - 1, -1, -1):
        if es_laboratorio(palabras[i]):
            laboratorio = palabras[i]
            palabras = palabras[:i] + palabras[i+1:]
            break

    # Si no hay laboratorio conocido, el último token puede serlo
    if laboratorio is None and palabras:
        laboratorio = palabras[-1]
        palabras = palabras[:-1]

    # 3. Extraer PRESENTACION (tokens que contienen mg/ml/etc)
    presentacion_tokens = []
    for i in range(len(palabras) - 1, -1, -1):
        if es_presentacion(palabras[i]):
            presentacion_tokens.insert(0, palabras[i])
            palabras = palabras[:i] + palabras[i+1:]

    presentacion = " ".join(presentacion_tokens) if presentacion_tokens else ""

    # 4. Todo lo que queda es MARCA + DROGA
    resto = " ".join(palabras).strip()

    # Separar marca y droga
    marca = resto
    droga = current_droga

    # Si el resto tiene más de una palabra, la primera puede ser droga
    if len(palabras) > 1:
        # La primera palabra es candidata a droga
        droga_candidata = palabras[0]
        if len(droga_candidata) > 2 and not es_presentacion(droga_candidata):
            droga = droga_candidata
            marca = " ".join(palabras[1:]) if len(palabras) > 1 else ""

    # Si no hay droga, usar la anterior
    if not droga or len(droga) < 2:
        droga = current_droga

    # Limpiar valores
    droga = droga.lower().strip()
    marca = marca.strip()
    presentacion = presentacion.strip()
    laboratorio = laboratorio.strip() if laboratorio else "Desconocido"

    # Validación final
    if not droga or not marca or not precio_valor:
        return None

    return {
        "droga": droga,
        "marca": marca,
        "presentacion": presentacion,
        "laboratorio": laboratorio,
        "precio": precio_valor,
    }


def extract_rows(pdf_path: Path) -> list[dict]:
    """Extrae todas las filas del PDF."""
    doc = fitz.open(pdf_path)
    all_rows = []
    current_droga = ""
    total_pages = len(doc)
    pages_with_data = 0

    print(f"📄 Procesando {total_pages} páginas...")

    for page_num, page in enumerate(doc, 1):
        # Extraer palabras con coordenadas
        words = page.get_text("words")
        if not words:
            continue

        # Agrupar palabras por línea (mismo Y, tolerancia ±5)
        lines = {}
        for w in words:
            y = round(w[1] / 5) * 5  # w[1] es y0
            lines.setdefault(y, []).append(w[4])  # w[4] es el texto

        page_rows = 0
        for y in sorted(lines.keys()):
            palabras = lines[y]
            if not palabras:
                continue

            # Saltar encabezado (línea con MONODROGA)
            if any("MONODROGA" in p.upper() for p in palabras):
                continue

            # Unir palabras que están muy cerca (para evitar splits)
            # (mejorable, pero funciona)

            # Parsear línea
            row = parsear_linea(palabras, current_droga)
            if row:
                current_droga = row["droga"]
                all_rows.append(row)
                page_rows += 1

        if page_rows > 0:
            pages_with_data += 1
            print(f"   Página {page_num:3d}: {page_rows:3d} registros (total: {len(all_rows):5d})")

    doc.close()
    print(f"\n📊 Resumen: {pages_with_data} páginas con datos, {len(all_rows)} registros extraídos")
    return all_rows


def save_to_csv(rows: list[dict], output_path: Path) -> None:
    """Guarda los datos en CSV."""
    if not rows:
        print("⚠️ No hay datos para guardar")
        return

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["droga", "marca", "presentacion", "laboratorio", "precio"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"✅ CSV guardado: {output_path} ({len(rows)} registros)")


def main():
    script_dir = Path(__file__).parent.parent
    data_dir = script_dir / "data"
    data_dir.mkdir(exist_ok=True)

    # Generar URL del PDF según fecha actual
    fecha = datetime.now(TZ_AR)
    pdf_url = f"{PDF_BASE_URL}Precios{fecha.strftime('%y%m%d')}.pdf"
    pdf_path = data_dir / f"Precios{fecha.strftime('%y%m%d')}.pdf"
    csv_path = data_dir / "medicamentos.csv"

    print("=" * 60)
    print("📊 EXTRACTOR DE PRECIOS - MODO SMART (derecha a izquierda)")
    print("=" * 60)

    try:
        download_pdf(pdf_url, pdf_path)
        rows = extract_rows(pdf_path)
        save_to_csv(rows, csv_path)

        # Mostrar muestra
        if rows:
            print("\n📋 Muestra (primeros 5 registros):")
            for i, row in enumerate(rows[:5], 1):
                print(f"  {i}. {row['droga']} | {row['marca']} | {row['presentacion'][:30]} | {row['laboratorio']} | ${row['precio']}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
