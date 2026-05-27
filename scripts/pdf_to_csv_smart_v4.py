#!/usr/bin/env python3
"""
pdf_to_csv_smart_v4.py - Mejora detección de drogas y ajuste de heurísticas.
- Reconoce drogas en minúscula al inicio de la línea
- Mejor separación droga/marca
- Menor cantidad de falsos positivos
"""

import re
import csv
import json
import urllib.request
import ssl
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import fitz

# ============================================================
# CONFIGURACIÓN
# ============================================================

TZ_AR = timezone(timedelta(hours=-3))
PDF_BASE_URL = "https://siafar.com/precios/pdf/"

# Mapa de laboratorios (mismo que v3)
LABS_MAP = {
    "abbott epd": "Abbott EPD",
    "abbvie": "Abbvie",
    "abbvie (ex alle) recalcine": "Abbvie (ex Alle) Recalcine",
    "alcon": "Alcon",
    "alef medical argentina": "Alef Medical Argentina",
    "amgen": "Amgen",
    "andrómaco": "Andrómaco",
    "aponor": "Aponor",
    "ariston": "Ariston",
    "aspen": "Aspen",
    "aspen pharma": "Aspen Pharma",
    "astrazeneca": "AstraZeneca",
    "austral": "Austral",
    "b.braun": "B.Braun",
    "bacon": "Bacon",
    "bagó": "Bagó",
    "baliarda": "Baliarda",
    "bausch & lomb argentina": "Bausch & Lomb Argentina",
    "baxter argentina": "Baxter Argentina",
    "bayer (ph)": "Bayer (PH)",
    "bayer consumer": "Bayer Consumer",
    "beta": "Beta",
    "biocontrol": "Biocontrol",
    "biofactor": "Biofactor",
    "biol": "Biol",
    "biopas argentina": "Biopas Argentina",
    "bioprofarma bag": "Bioprofarma Bag",
    "biosidus s.a.u.": "Biosidus S.A.U.",
    "biosintex": "Biosintex",
    "biosintex retai": "Biosintex Retai",
    "biotechno pharm": "Biotechno Pharm",
    "biotenk": "Biotenk",
    "biotoscana": "Biotoscana",
    "boehringer ingelheim": "Boehringer Ingelheim",
    "csl behring": "CSL Behring",
    "cabuchi": "Cabuchi",
    "casasco": "Casasco",
    "cassará": "Cassará",
    "celnova argentina": "Celnova Argentina",
    "celtyc": "Celtyc",
    "cetus": "Cetus",
    "cevallos": "Cevallos",
    "craveri": "Craveri",
    "dallas": "Dallas",
    "denver farma": "Denver Farma",
    "domínguez": "Domínguez",
    "donato zurlo": "Donato Zurlo",
    "dr.madaus": "Dr.Madaus",
    "duncan": "Duncan",
    "e.j.gezzi": "E.J.Gezzi",
    "eczane": "Eczane",
    "elea": "Elea",
    "eriochem": "Eriochem",
    "eurofarma": "Eurofarma",
    "eurolab": "Eurolab",
    "everex": "Everex",
    "excelentia": "Excelentia",
    "fabra": "Fabra",
    "fada pharma": "Fada Pharma",
    "fecofar": "Fecofar",
    "ferring": "Ferring",
    "finadiet": "Finadiet",
    "fortbenton": "Fortbenton",
    "francelab": "Francelab",
    "fresenius kabi": "Fresenius Kabi",
    "gp pharm": "GP Pharm",
    "gador": "Gador",
    "galderma": "Galderma",
    "gemabiotech": "Gemabiotech",
    "genomma lab.": "Genomma Lab.",
    "glaxosmithkline": "GlaxoSmithKline",
    "glenmark": "Glenmark",
    "gobbi": "Gobbi",
    "gramón": "Gramón",
    "gray": "Gray",
    "géminis farmacéutica": "Géminis Farmacéutica",
    "hlb pharma": "HLB Pharma",
    "hemoderivados": "Hemoderivados",
    "ima": "IMA",
    "isa": "ISA",
    "imvi": "Imvi",
    "infinity pharma": "Infinity Pharma",
    "iraola": "Iraola",
    "isdin": "Isdin",
    "janssen-cilag": "Janssen-Cilag",
    "jayor": "Jayor",
    "johnson & johnson": "Johnson & Johnson",
    "kemex": "Kemex",
    "kilab": "Kilab",
    "klonal": "Klonal",
    "lkm": "LKM",
    "lkm onco/especi": "LKM Onco/Especi",
    "laboratorio grafo": "Laboratorio Grafo",
    "laboratorio internacional": "Laboratorio Internacional",
    "laboratorio merck": "Laboratorio Merck",
    "laboratorio valent": "Laboratorio Valent",
    "laboratorios beta": "Laboratorios Beta",
    "laboratorios ferrer": "Laboratorios Ferrer",
    "laboratorios tuteur": "Laboratorios Tuteur",
    "lafedar": "Lafedar",
    "lagos": "Lagos",
    "lancaster pharma": "Lancaster Pharma",
    "lazar": "Lazar",
    "lepetit": "Lepetit",
    "lersan": "Lersan",
    "lundbeck": "Lundbeck",
    "mr pharma": "MR Pharma",
    "msd argentina": "MSD Argentina",
    "mar": "Mar",
    "max vision": "Max Vision",
    "medipharma": "Medipharma",
    "medisol": "Medisol",
    "merck serono": "Merck Serono",
    "merz": "Merz",
    "microsules argentina": "Microsules Argentina",
    "monserrat": "Monserrat",
    "montpellier": "Montpellier",
    "mundipharma": "Mundipharma",
    "natufarma": "Natufarma",
    "nolter": "Nolter",
    "northia": "Northia",
    "novartis": "Novartis",
    "novo nordisk": "Novo Nordisk",
    "novoplos": "Novoplos",
    "omicron": "Omicron",
    "opella healthcare": "Opella Healthcare",
    "organon argentina": "Organon Argentina",
    "oxapharma": "Oxapharma",
    "panalab": "Panalab",
    "pfizer": "Pfizer",
    "pharmadorf": "PharmaDorf",
    "pharmalep s.a.": "Pharmalep S.A.",
    "pharmanove": "Pharmanove",
    "pharmatrix": "Pharmatrix",
    "pierre fabre médicament": "Pierre Fabre Médicament",
    "pierre fabre oncologie": "Pierre Fabre Oncologie",
    "poen": "Poen",
    "pretoria": "Pretoria",
    "procter & gamble": "Procter & Gamble",
    "química luar": "Química Luar",
    "raffo": "Raffo",
    "raymos-megalabs": "Raymos-Megalabs",
    "reckitt benckiser": "Reckitt Benckiser",
    "richet": "Richet",
    "richmond": "Richmond",
    "rivero": "Rivero",
    "roche": "Roche",
    "roemmers": "Roemmers",
    "ronnet": "Ronnet",
    "rontag": "Rontag",
    "rospaw": "Rospaw",
    "rossmore pharma": "Rossmore Pharma",
    "roux ocefa": "Roux Ocefa",
    "sanitas": "Sanitas",
    "sanofi pasteur argentina": "Sanofi Pasteur Argentina",
    "sanofi-aventis": "Sanofi-Aventis",
    "sant gall": "Sant Gall",
    "savant consumer": "Savant Consumer",
    "savant generic": "Savant Generic",
    "savant pharma": "Savant Pharma",
    "schafer": "Schafer",
    "scott pharma": "Scott Pharma",
    "scott-cassará": "Scott-Cassará",
    "seqirus": "Seqirus",
    "sertex": "Sertex",
    "servier": "Servier",
    "sidus": "Sidus",
    "siegfried": "Siegfried",
    "soubeiran chobe": "Soubeiran Chobe",
    "takeda argentina": "Takeda Argentina",
    "techsphere": "Techsphere",
    "temis-lostaló": "Temis-Lostaló",
    "teva argentina": "Teva argentina",
    "trb-pharma": "Trb-Pharma",
    "tuteur": "Tuteur",
    "valmax": "Valmax",
    "valuge": "Valuge",
    "vannier": "Vannier",
    "vannier - grünenthal": "Vannier - Grünenthal",
    "varifarma": "Varifarma",
    "veinfar": "Veinfar",
    "vent 3": "Vent 3",
    "wunder pharm": "Wunder Pharm",
}

UNIDADES = re.compile(r'\b(mg|ml|g|ui|mcg|mg/ml)\b', re.I)
FORMAS = re.compile(r'\b(comp|caps|tabletas|comprimidos|suspension|solucion|jarabe|gotas|crema|unguento|aerosol|inyectable|cápsulas|sobres|ampollas)\b', re.I)
PRECIO_REGEX = re.compile(r'\b(\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2}|\d+\.\d+)\b')
STOPWORDS_PRESENTACION = {'de', 'y', 'con', 'sin', 'para', 'por', 'en', 'a', 'al', 'del'}

# Palabras que suelen indicar DROGA (principio activo)
DROGA_INDICADORES = ['acetato', 'clorhidrato', 'sodico', 'potasico', 'magnesico', 'cloruro', 'sulfato', 'fumarato', 'maleato']


def download_pdf(url: str, output_path: Path) -> Path:
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


def match_laboratorio(palabras: list, start_idx: int, max_words: int = 4) -> tuple[str | None, int]:
    for size in range(min(max_words, len(palabras) - start_idx), 0, -1):
        candidate = " ".join(palabras[start_idx:start_idx + size]).lower().strip()
        if candidate in LABS_MAP:
            return LABS_MAP[candidate], size
    return None, 0


def expandir_presentacion(palabras: list, idx: int) -> tuple[list[str], int, int]:
    resultado = [palabras[idx]]
    start = idx
    end = idx + 1

    i = idx - 1
    while i >= 0:
        palabra = palabras[i]
        if (palabra[0].isupper() and len(palabra) > 2) or palabra.isupper():
            break
        if palabra.lower() in STOPWORDS_PRESENTACION:
            break
        if re.match(r'^[\d,\.]+$', palabra) or len(palabra) <= 2:
            resultado.insert(0, palabra)
            start = i
            i -= 1
        else:
            break

    i = idx + 1
    while i < len(palabras):
        palabra = palabras[i]
        if (palabra[0].isupper() and len(palabra) > 2) or palabra.isupper():
            break
        if palabra.lower() in STOPWORDS_PRESENTACION:
            break
        if FORMAS.search(palabra) or re.match(r'^[\d,\.x]+$', palabra):
            resultado.append(palabra)
            end = i + 1
            i += 1
        else:
            break

    return resultado, start, end


def normalizar_laboratorio(lab: str) -> str:
    if not lab:
        return "Desconocido"
    lab_lower = lab.lower().strip()
    return LABS_MAP.get(lab_lower, lab)


def heuristica_droga_marca(texto: str, posicion_inicial: bool = False) -> tuple[str, str, float]:
    """
    Determina droga y marca con scoring mejorado.
    posicion_inicial: True si este texto está al principio de la línea.
    """
    texto = texto.strip()
    palabras = texto.split()

    if not palabras:
        return "", "", 0.0

    # Si está al principio y la primera palabra está en minúsculas, es casi seguro droga
    if posicion_inicial and palabras[0].islower() and len(palabras[0]) > 2:
        # La primera palabra es droga, el resto es marca
        droga = palabras[0]
        marca = " ".join(palabras[1:]) if len(palabras) > 1 else ""
        return droga, marca, 0.9

    # Detectar droga por palabras indicadoras
    for i, p in enumerate(palabras):
        if any(ind in p.lower() for ind in DROGA_INDICADORES):
            droga = " ".join(palabras[:i+1])
            marca = " ".join(palabras[i+1:]) if i+1 < len(palabras) else ""
            return droga, marca, 0.85

    # Si hay comas, probablemente droga
    if ',' in texto:
        parts = texto.split(',', 1)
        droga = parts[0].strip()
        marca = parts[1].strip() if len(parts) > 1 else ""
        return droga, marca, 0.8

    # Si todo está en minúsculas, es droga
    if texto.islower() and len(texto) > 3:
        return texto, "", 0.7

    # Si empieza con minúscula y tiene mayúsculas después, primera palabra es droga
    if palabras[0].islower() and any(p[0].isupper() for p in palabras[1:]):
        droga = palabras[0]
        marca = " ".join(palabras[1:])
        return droga, marca, 0.75

    # Default: asumir que todo es marca
    return "", texto, 0.4


def parsear_linea(palabras: list, current_droga: str, current_conf: float) -> tuple[dict | None, str, float]:
    if not palabras:
        return None, current_droga, current_conf

    textos = [w.get("text", "") for w in palabras] if isinstance(palabras[0], dict) else palabras
    xs = [w.get("x", 0) for w in palabras] if isinstance(palabras[0], dict) else [0] * len(palabras)

    if not textos:
        return None, current_droga, current_conf

    precio_valor = None
    precio_idx = -1
    precio_x = None

    for i in range(len(textos) - 1, -1, -1):
        match = PRECIO_REGEX.search(textos[i])
        if match:
            precio_valor = clean_price(match.group())
            if precio_valor is not None:
                precio_idx = i
                precio_x = xs[i] if i < len(xs) else 0
                break

    if precio_valor is None:
        return None, current_droga, current_conf

    score = 0.5
    laboratorio = None
    laboratorio_start = -1
    laboratorio_end = -1

    for i in range(min(precio_idx - 1, len(textos) - 1), -1, -1):
        lab, size = match_laboratorio(textos, i)
        if lab:
            laboratorio = lab
            laboratorio_start = i
            laboratorio_end = i + size
            score += 0.3
            break

    presentacion_tokens = []
    pres_start = -1
    pres_end = -1
    for i in range(precio_idx - 1, -1, -1):
        if UNIDADES.search(textos[i]):
            expanded, start, end = expandir_presentacion(textos, i)
            presentacion_tokens = expanded
            pres_start = start
            pres_end = end
            score += 0.2
            break

    used_indices = {precio_idx}
    if laboratorio_start >= 0:
        for j in range(laboratorio_start, laboratorio_end):
            used_indices.add(j)
    if pres_start >= 0:
        for j in range(pres_start, pres_end):
            used_indices.add(j)

    resto_indices = [i for i in range(len(textos)) if i not in used_indices and i < precio_idx]
    resto = [textos[i] for i in resto_indices]

    droga = ""
    marca = ""
    conf = score

    if resto:
        texto_resto = " ".join(resto)
        posicion_inicial = (resto_indices[0] == 0) if resto_indices else False
        droga_cand, marca_cand, droga_conf = heuristica_droga_marca(texto_resto, posicion_inicial)

        if droga_cand and droga_conf > 0.5:
            droga = droga_cand
            marca = marca_cand
            conf = (score + droga_conf) / 2
        elif marca_cand:
            marca = marca_cand
            conf = score * 0.8
        elif droga_cand:
            droga = droga_cand
            conf = (score + droga_conf) / 2

    if not droga and current_conf >= 0.8:
        droga = current_droga
        conf = score * 0.7

    if not marca and resto:
        marca = " ".join(resto)

    if not droga or not marca or not precio_valor:
        return {
            "droga": droga or current_droga,
            "marca": marca,
            "presentacion": " ".join(presentacion_tokens),
            "laboratorio": normalizar_laboratorio(laboratorio),
            "precio": precio_valor,
            "confidence": conf * 0.5,
            "errors": ["missing_field"]
        }, droga or current_droga, conf * 0.5

    return {
        "droga": droga.lower(),
        "marca": marca,
        "presentacion": " ".join(presentacion_tokens),
        "laboratorio": normalizar_laboratorio(laboratorio),
        "precio": precio_valor,
        "confidence": conf,
        "errors": []
    }, droga, conf


def extract_rows(pdf_path: Path, logs_dir: Path) -> list[dict]:
    doc = fitz.open(pdf_path)
    all_rows = []
    current_droga = ""
    current_conf = 1.0
    total_pages = len(doc)
    rejected_rows = []
    low_confidence_rows = []
    page_stats = {}

    print(f"📄 Procesando {total_pages} páginas...")

    for page_num, page in enumerate(doc, 1):
        words = page.get_text("words")
        if not words:
            continue

        lines = defaultdict(list)
        for w in words:
            y = round(w[1] / 5) * 5
            lines[y].append({"x": w[0], "text": w[4]})

        page_rows = 0
        page_low_conf = 0

        for y in sorted(lines.keys()):
            palabras = sorted(lines[y], key=lambda w: w["x"])

            if any("MONODROGA" in w["text"].upper() for w in palabras):
                continue

            row, new_droga, conf = parsear_linea(palabras, current_droga, current_conf)
            if row and row.get("precio") is not None:
                current_droga = new_droga
                current_conf = conf
                all_rows.append(row)
                page_rows += 1
                if row.get("confidence", 1) < 0.6:
                    page_low_conf += 1
                    low_confidence_rows.append({
                        "page": page_num,
                        "row": row,
                        "text": " ".join([w["text"] for w in palabras])
                    })
                if row.get("errors"):
                    rejected_rows.append({
                        "page": page_num,
                        "row": row,
                        "text": " ".join([w["text"] for w in palabras])
                    })

        page_stats[page_num] = {"rows": page_rows, "low_confidence": page_low_conf}
        if page_rows > 0:
            print(f"   Página {page_num:3d}: {page_rows:3d} registros (total: {len(all_rows):5d})")

    logs_dir.mkdir(exist_ok=True)
    with open(logs_dir / "rejected_rows.json", "w", encoding="utf-8") as f:
        json.dump(rejected_rows, f, ensure_ascii=False, indent=2)
    with open(logs_dir / "low_confidence_rows.json", "w", encoding="utf-8") as f:
        json.dump(low_confidence_rows, f, ensure_ascii=False, indent=2)
    with open(logs_dir / "page_stats.json", "w", encoding="utf-8") as f:
        json.dump(page_stats, f, ensure_ascii=False, indent=2)

    doc.close()
    print(f"\n📊 Resumen: {len(all_rows)} registros extraídos")
    return all_rows


def save_to_csv(rows: list[dict], output_path: Path) -> None:
    if not rows:
        print("⚠️ No hay datos para guardar")
        return
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["droga", "marca", "presentacion", "laboratorio", "precio"])
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "droga": row.get("droga", ""),
                "marca": row.get("marca", ""),
                "presentacion": row.get("presentacion", ""),
                "laboratorio": row.get("laboratorio", "Desconocido"),
                "precio": row.get("precio", "")
            })
    print(f"✅ CSV guardado: {output_path} ({len(rows)} registros)")


def main():
    script_dir = Path(__file__).parent.parent
    data_dir = script_dir / "data"
    logs_dir = script_dir / "logs"
    data_dir.mkdir(exist_ok=True)

    fecha = datetime.now(TZ_AR)
    pdf_url = f"{PDF_BASE_URL}Precios{fecha.strftime('%y%m%d')}.pdf"
    pdf_path = data_dir / f"Precios{fecha.strftime('%y%m%d')}.pdf"
    csv_path = data_dir / "medicamentos.csv"

    print("=" * 60)
    print("📊 EXTRACTOR DE PRECIOS - SMART V4")
    print("   (mejor detección de drogas, mejor separación droga/marca)")
    print("=" * 60)

    try:
        download_pdf(pdf_url, pdf_path)
        rows = extract_rows(pdf_path, logs_dir)
        save_to_csv(rows, csv_path)

        if rows:
            print("\n📋 Muestra (primeros 5 registros):")
            for i, row in enumerate(rows[:5], 1):
                conf = row.get("confidence", 1)
                conf_marker = "✓" if conf >= 0.7 else "⚠️" if conf >= 0.4 else "❌"
                print(f"  {i}. {conf_marker} {row['droga']} | {row['marca'][:25]} | {row['presentacion'][:25]} | {row['laboratorio'][:20]} | ${row['precio']}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
