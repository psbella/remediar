#!/usr/bin/env python3
"""pdf_to_json.py - Descarga el PDF, filtra blacklist, detecta outliers, genera JSON."""

import re
import json
import sys
import statistics
import urllib.request
import ssl
from collections import defaultdict
from pathlib import Path
from datetime import datetime, timezone, timedelta

AR_TZ = timezone(timedelta(hours=-3))

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode   = ssl.CERT_NONE

try:
    import fitz
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pymupdf"])
    import fitz

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────
OUTLIER_CONFIG = {
    "PRECIO_MINIMO_ARS":  1_800,
    "UMBRAL_CRITICO":     0.10,
    "UMBRAL_RELATIVO":    0.25,
    "MIN_REGISTROS":      3,
    "IQR_FACTOR":         1.5,
    "SCORE_OUTLIER":      20,
    "SCORE_NORMAL":       100,
}

BASE              = Path(__file__).parent.parent
BLACKLIST_PATH    = BASE / "data" / "blacklist.json"
OUTLIER_REPORT    = BASE / "data" / "outlier_report.json"
MEDICAMENTOS_PATH = BASE / "data" / "medicamentos.json"


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS PARSEO
# ─────────────────────────────────────────────────────────────────────────────
def limpiar_precio(valor):
    if not valor or valor == '-':
        return None
    valor = str(valor).strip()
    valor = valor.replace('.', '').replace(',', '.')
    valor = re.sub(r'[^\d\.]', '', valor)
    try:
        return float(valor)
    except Exception:
        return None

def es_precio(texto):
    if not texto:
        return False
    limpio = re.sub(r'[\$\s]', '', texto)
    return bool(re.match(r'^[\d\.,]+$', limpio))


# ─────────────────────────────────────────────────────────────────────────────
# BLACKLIST
# ─────────────────────────────────────────────────────────────────────────────
def make_key(m):
    return '|'.join([
        (m.get('droga')        or '').strip().lower(),
        (m.get('marca')        or '').strip().lower(),
        (m.get('presentacion') or '').strip().lower(),
        (m.get('laboratorio')  or '').strip().lower(),
    ])

def cargar_blacklist():
    if BLACKLIST_PATH.exists():
        with open(BLACKLIST_PATH, encoding='utf-8') as f:
            bl = json.load(f)
        print(f"   Lista negra: {len(bl)} entradas cargadas")
        return bl
    print("   Lista negra: no encontrada, se usara vacia")
    return {}

def filtrar_blacklist(medicamentos, blacklist):
    if not blacklist:
        return medicamentos, 0
    filtrados = [m for m in medicamentos if make_key(m) not in blacklist]
    n = len(medicamentos) - len(filtrados)
    if n:
        print(f"   Lista negra: {n} medicamento(s) excluidos")
    return filtrados, n


# ─────────────────────────────────────────────────────────────────────────────
# REPARACIÓN DENVER FARMA
# ─────────────────────────────────────────────────────────────────────────────

# Denver Farma usa el nombre comercial genérico "DROGA DENVER FARMA" sin marca
# propia, lo que hace que el parser fusione marca+presentacion en un solo token.
# Tres variantes según dónde ocurrió la fusión en el PDF:
#
#   Variante A — presentacion pegada al final de marca (caso más común):
#     PDF:    "ALPRAZOLAM DENVER FARMA\n1 MG COMP.X 60\n..."  → sin salto entre ambos
#     Parser: marca="ALPRAZOLAM DENVER FARMA1 MG COMP.X 60"  presentacion=""
#     Fix:    separar por el token "DENVER FARM(A)" + dígito/unidad siguiente
#
#   Variante B — "denver farma" absorbido en el campo droga:
#     PDF:    fusión distinta donde droga captura el lab
#     Parser: droga="betametasona...denvercrem denver farma"  marca="CR.X 20 G"
#     Fix:    limpiar droga, mover marca → presentacion
#
#   Variante C — abreviaturas DENCR. y DF como separador:
#     PDF:    "SULFADIAZINA DE PLATA DENCR.POMO X 30 G" o "BUDESONIDA DF AEROSOL..."
#     Fix:    mismo regex extendido con DENCR\. y DF como anclas de corte

_RE_MARCA_DENVER = re.compile(
    r'^(.*?(?:DENVER\s*FARM[A]?|DENCR\.|(?<!\w)DF(?!\w)))\s*'
    r'([A-Z]{2,}[\w\s\.,/%x\-áéíóúü]*|\d[\w\s\.,/%x\-áéíóúü]*)',
    re.IGNORECASE
)
_RE_DROGA_DENVER = re.compile(
    r'^(.*?)\s*(?:\w*denver\w*\s*)?denver\s*farma\s*$',
    re.IGNORECASE
)

def reparar_denver(medicamentos: list) -> tuple:
    """
    Corrige los registros de Denver Farma donde marca y presentacion
    quedaron fusionados por el parser.

    Retorna el dataset corregido y la cantidad de registros reparados.
    """
    reparados = 0

    for m in medicamentos:
        if (m.get("laboratorio") or "").lower() != "denver farma":
            continue

        marca        = (m.get("marca")        or "").strip()
        presentacion = (m.get("presentacion") or "").strip()
        droga        = (m.get("droga")        or "").strip()

        # Variante B: "denver farma" se coló dentro del campo droga
        if "denver" in droga.lower():
            match_droga = _RE_DROGA_DENVER.match(droga)
            if match_droga:
                droga_limpia   = match_droga.group(1).strip().rstrip(',').strip()
                m["droga"]        = droga_limpia.lower()
                m["presentacion"] = marca   # lo que era marca es en realidad la presentacion
                m["marca"]        = ""
                reparados += 1
            continue

        # Variantes A y C: presentacion vacía, todo fusionado en marca
        if not presentacion:
            match_marca = _RE_MARCA_DENVER.match(marca)
            if match_marca:
                m["marca"]        = match_marca.group(1).strip()
                m["presentacion"] = match_marca.group(2).strip().lower()
                reparados += 1

    return medicamentos, reparados


# ─────────────────────────────────────────────────────────────────────────────
# FIXES MANUALES DE DROGA
# ─────────────────────────────────────────────────────────────────────────────

# Diccionario curado manualmente: marca (upper) → droga (principio activo).
# Cubre marcas sin nombre genérico en el PDF de SIAFAR que no pueden
# resolverse automáticamente (nombres comerciales de laboratorios que no
# imprimen el principio activo en el PDF).
# Archivo: data/droga_fixes.json

DROGA_FIXES_PATH = BASE / "data" / "droga_fixes.json"

def aplicar_droga_fixes(medicamentos: list) -> tuple:
    """
    Aplica correcciones manuales de droga (principio activo) desde
    data/droga_fixes.json usando la marca como clave.

    Solo actúa cuando el campo droga está vacío.
    Si el archivo no existe, es un no-op con aviso.

    Retorna el dataset corregido y la cantidad de registros corregidos.
    """
    if not DROGA_FIXES_PATH.exists():
        print("   droga_fixes: archivo no encontrado, se omite")
        return medicamentos, 0

    with open(DROGA_FIXES_PATH, encoding='utf-8') as f:
        fixes = json.load(f)

    corregidos = 0
    for m in medicamentos:
        marca_upper = (m.get('marca') or '').strip().upper()
        droga_upper = (m.get('droga') or '').strip().upper()

        # Buscar fix por marca (cuando droga está vacía)
        clave = None
        if not m.get('droga', '').strip() and marca_upper in fixes:
            clave = marca_upper
        # Buscar fix por droga (cuando droga+marca están fusionadas en campo droga)
        elif droga_upper in fixes and isinstance(fixes[droga_upper], dict):
            clave = droga_upper

        if clave is None:
            continue

        valor = fixes[clave]
        if isinstance(valor, str):
            m['droga'] = valor
        elif isinstance(valor, dict):
            m['droga'] = valor.get('droga', '')
            if valor.get('marca'):
                m['marca'] = valor['marca']
            if valor.get('presentacion'):
                m['presentacion'] = valor['presentacion']
        corregidos += 1

    return medicamentos, corregidos


# ─────────────────────────────────────────────────────────────────────────────
# CROSSWALK PAMI
# ─────────────────────────────────────────────────────────────────────────────

# Usa el vademécum de PAMI como fuente de verdad para recuperar el campo droga
# (principio activo) en registros donde el PDF de SIAFAR no lo incluyó.
#
# Estrategia de match:
#   1. marca+presentacion exactos → recupera droga y corrige laboratorio
#   2. solo marca (cuando presentacion vacía) → recupera droga solo si es
#      unívoca (todas las filas PAMI para esa marca tienen la misma droga)
#
# El archivo de PAMI se descarga en cada run desde la ruta configurada.
# Si no está disponible, la función es un no-op con aviso.

PAMI_PATH = BASE / "data" / "pami.xlsx"

def _build_pami_index():
    """Carga el vademécum PAMI y construye índices por marca+pres y por marca."""
    if not PAMI_PATH.exists():
        return None, None

    try:
        import openpyxl  # noqa: F401
        df = __import__('pandas').read_excel(PAMI_PATH)
    except Exception as e:
        print(f"   PAMI: error al cargar ({e})")
        return None, None

    df.columns = [c.strip() for c in df.columns]

    def _norm(s):
        import re as _re
        return _re.sub(r'\s+', ' ', str(s or '').strip().upper())

    by_marca_pres = {}
    by_marca      = {}

    for _, row in df.iterrows():
        mk   = _norm(row.get('MARCA', ''))
        pres = _norm(row.get('PRESENTACION', ''))
        key  = (mk, pres)
        if key not in by_marca_pres:
            by_marca_pres[key] = row
        by_marca.setdefault(mk, []).append(row)

    return by_marca_pres, by_marca

def crosswalk_pami(medicamentos: list) -> tuple:
    """
    Enriquece registros de SIAFAR usando el vademécum de PAMI.

    - Recupera droga (principio activo) cuando está vacía.
    - Corrige laboratorio cuando es 'Desconocido' y PAMI lo tiene.

    Retorna el dataset enriquecido y un dict de estadísticas.
    """
    import re as _re

    def _norm(s):
        return _re.sub(r'\s+', ' ', str(s or '').strip().upper())

    stats = {'match_exacto': 0, 'droga_recuperada': 0, 'lab_corregido': 0}

    by_marca_pres, by_marca = _build_pami_index()
    if by_marca_pres is None:
        print("   PAMI: archivo no encontrado, se omite crosswalk")
        return medicamentos, stats

    for m in medicamentos:
        mk   = _norm(m.get('marca', ''))
        pres = _norm(m.get('presentacion', ''))

        # Estrategia 1: match exacto marca+presentacion
        if pres and (mk, pres) in by_marca_pres:
            row = by_marca_pres[(mk, pres)]
            stats['match_exacto'] += 1

            if not m.get('droga', '').strip() and str(row.get('DROGA', '')).strip():
                m['droga'] = str(row['DROGA']).strip().lower()
                stats['droga_recuperada'] += 1

            if m.get('laboratorio') == 'Desconocido' and str(row.get('LABORATORIO', '')).strip():
                m['laboratorio'] = str(row['LABORATORIO']).strip()
                stats['lab_corregido'] += 1

        # Estrategia 2: solo marca (presentacion vacía, droga vacía)
        elif not pres and not m.get('droga', '').strip() and mk in by_marca:
            rows  = by_marca[mk]
            drogas = {str(r.get('DROGA', '')).strip().lower() for r in rows if str(r.get('DROGA', '')).strip()}
            if len(drogas) == 1:
                m['droga'] = drogas.pop()
                stats['droga_recuperada'] += 1

    return medicamentos, stats


# ─────────────────────────────────────────────────────────────────────────────
# REPARACIÓN MARCA DESPLAZADA
# ─────────────────────────────────────────────────────────────────────────────

# Ocurre cuando el nombre comercial (marca) cayó en el campo droga durante
# el parsing, y la presentacion quedó en el slot de marca.
#
# Criterio de detección (ambas condiciones):
#   - marca empieza con dígito → es dosis/presentacion, no nombre comercial
#   - presentacion vacía
#
# Corrección:
#   marca → presentacion
#   droga → marca (en mayúsculas)
#   droga queda vacía (el principio activo no está disponible en el PDF para estos casos)
#
# Excluye correctamente marcas legítimas que empiezan con dígito
# como "3 TC", "5-ASA", "4 X 4", "8 HORAS" (tienen presentacion no vacía).

def reparar_marca_desplazada(medicamentos: list) -> tuple:
    """
    Corrige registros donde el nombre comercial cayó en el campo droga
    y la presentacion quedó en el slot de marca.

    Retorna el dataset corregido y la cantidad de registros reparados.
    """
    reparados = 0
    for m in medicamentos:
        marca        = (m.get("marca")        or "").strip()
        presentacion = (m.get("presentacion") or "").strip()
        droga        = (m.get("droga")        or "").strip()

        if marca and marca[0].isdigit() and not presentacion:
            m["presentacion"] = marca.lower()
            m["marca"]        = droga.upper()
            m["droga"]        = ""
            reparados += 1

    return medicamentos, reparados


# ─────────────────────────────────────────────────────────────────────────────
# EXTRACCIÓN DE PRESENTACIÓN DESDE MARCA FUSIONADA
# ─────────────────────────────────────────────────────────────────────────────

# Cuando presentacion está vacía y la marca contiene el nombre comercial
# seguido de la presentación sin separador explícito, este regex detecta
# el punto de corte: dosis numérica o forma farmacéutica conocida.
#
# Ejemplo:
#   "ALLOPURINOL 300 CRAVERI 300 MG COMP.X 60"
#   → marca: "ALLOPURINOL 300 CRAVERI"  presentacion: "300 mg comp.x 60"
#
# No resuelve los casos donde la marca desapareció completamente
# (ej: "COMP.X 30") ni las fusiones droga+marca sin separador.

_FORMAS_FARM = (
    r'COMP|CAPS|CÁPS|CR|GTS|JBE|SOL|SUSP|UNG|GEL|AER|INY|F\.A|LIOF|POMO'
    r'|SOB|OV|GRAG|ENV|COLIRIO|COLIRO|EMULS|AEROSOL'
)

_RE_EXTRAER_PRES = re.compile(
    r'^(.+?)\s+(\d[\d,./]*\s*(?:MG|MCG|G\b|ML|UI|%|U\b).*'
    r'|(?:' + _FORMAS_FARM + r')[\.\s].+)$',
    re.IGNORECASE
)

def extraer_presentacion_de_marca(medicamentos: list) -> tuple:
    """
    Para registros con presentacion vacía, intenta extraer la presentacion
    desde el campo marca cuando ambos campos quedaron fusionados.

    Solo actúa cuando el nombre resultante tiene al menos 3 caracteres
    y no empieza con dígito (descarta falsos positivos).

    Retorna el dataset corregido y la cantidad de registros reparados.
    """
    reparados = 0
    for m in medicamentos:
        if (m.get("presentacion") or "").strip():
            continue
        if m.get("laboratorio") in ("Desconocido", ""):
            continue

        marca = (m.get("marca") or "").strip()
        match = _RE_EXTRAER_PRES.match(marca)
        if match:
            nombre = match.group(1).strip()
            pres   = match.group(2).strip().lower()
            if len(nombre) >= 3 and not nombre[0].isdigit():
                m["marca"]        = nombre
                m["presentacion"] = pres
                reparados += 1

    return medicamentos, reparados


# ─────────────────────────────────────────────────────────────────────────────
# REPARACIÓN DE PRESENTACIÓN DESPLAZADA AL CAMPO LABORATORIO
# ─────────────────────────────────────────────────────────────────────────────

# Cuando el parser consume una línea extra, la presentacion cae en el slot
# del laboratorio. Tres variantes:
#
#   2A — lab tiene "presentacion + lab" fusionados:
#     lab: "10/134mg compx30+capsx30Teva argentina"
#     → presentacion: "10/134mg compx30+capsx30"  lab: "Teva argentina"
#
#   2B — marca+presentacion fusionadas sin espacio:
#     marca: "BAGOHEPAT RAPIDA ACCIONCÁPS.BL.X 20"
#     → marca: "BAGOHEPAT RAPIDA ACCION"  presentacion: "cáps.bl.x 20"
#
#   2C — marca real está al final del campo droga, marca actual es la presentacion:
#     droga: "alprazolam, domperidona, asoc.sidomal"  marca: "COMP.X 30"
#     → droga: "alprazolam, domperidona"  marca: "SIDOMAL"  presentacion: "comp.x 30"

_FORMAS_PAT2 = r'(?:COMP|CAPS|CÁPS|GRAG|SOL|OV|INY|LIOF|SOB|JGA|LAP|AERO|F\.A|INHAL)'

_RE_SOLO_FORMA2 = re.compile(
    r'^(?:COMP|CAPS|CÁPS|GRAG|SOL|OV|INY|LIOF|SOB|JGA|LAP|A\.X|F\.A|AEROSOL|INY\.)',
    re.IGNORECASE
)

# 2A: lab empieza con dígito o minúscula → tiene presentacion+lab
# No usamos regex para el corte porque el lab puede estar pegado sin espacio
# (ej: "10/134mg compx30+capsx30Teva argentina"). En su lugar cruzamos
# contra el set de laboratorios conocidos del propio dataset.
_RE_PRES_EN_LAB = None  # señal para usar el método por labs conocidos

# 2B: marca+pres fusionadas (forma farmacéutica o número pegado)
_RE_MARCA_FORMA2 = re.compile(r'^(.+?)(' + _FORMAS_PAT2 + r'[\.\s\-].+)$', re.IGNORECASE)
_RE_MARCA_NUM2   = re.compile(r'^(.+?[A-ZÁÉÍÓÚÜÑ])(\d[\d\.,/\s\w\+\(\)]+)$', re.IGNORECASE)

# 2C: marca al final del campo droga
_RE_DROGA_MARCA2 = re.compile(
    r'^(.*?(?:,\s*asoc\.|,\s*ác\.|fosf\.diso|peróxid|sulf\.|microniz|clorh\.|'
    r'rep\.|maleato|acetato|,\s*[a-záéíóúüñ]{1,6}\b))\s*'
    r'([a-záéíóúüñA-ZÁÉÍÓÚÜÑ][a-záéíóúüñA-ZÁÉÍÓÚÜÑ\s\d]+)$',
    re.IGNORECASE
)

def reparar_presentacion_desplazada(medicamentos: list) -> tuple:
    """
    Corrige registros donde la presentacion quedó desplazada al campo
    laboratorio (o a la marca), separando correctamente los campos.

    Retorna el dataset corregido y la cantidad de registros reparados.
    """
    reparados = 0

    for m in medicamentos:
        if (m.get('presentacion') or '').strip():
            continue

        marca = (m.get('marca') or '').strip()
        lab   = (m.get('laboratorio') or '').strip()
        droga = (m.get('droga') or '').strip()

        # ── 2A: presentacion+lab en campo lab ────────────────────────────
        # El lab puede estar pegado sin espacio al final de la presentacion,
        # por lo que no usamos regex de separación. En su lugar construimos
        # el set de labs conocidos y buscamos sufijo.
        if lab and (lab[0].isdigit() or lab[0].islower() or
                    re.match(r'^[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+\s+\d', lab)):
            labs_conocidos = {
                (m2.get('laboratorio') or '').strip().lower(): (m2.get('laboratorio') or '').strip()
                for m2 in medicamentos
                if m2.get('laboratorio') and m2['laboratorio'] != 'Desconocido'
            }
            lab_lower = lab.lower()
            encontrado = False
            for ll, lo in labs_conocidos.items():
                if len(ll) >= 4 and lab_lower.endswith(ll):
                    pres = lab[:len(lab) - len(ll)].strip()
                    if pres:
                        m['presentacion'] = pres.lower()
                        m['laboratorio']  = lo
                        reparados += 1
                        encontrado = True
                        break
            if encontrado:
                continue

        # ── 2B: marca+pres fusionadas ─────────────────────────────────────
        if marca and not _RE_SOLO_FORMA2.match(marca):
            match = _RE_MARCA_FORMA2.search(marca) or _RE_MARCA_NUM2.search(marca)
            if match:
                nueva_marca = match.group(1).strip()
                pres        = match.group(2).strip().lower()
                if len(nueva_marca) >= 3 and not nueva_marca[-1].isdigit():
                    m['marca']        = nueva_marca
                    m['presentacion'] = pres
                    reparados += 1
                    continue

        # ── 2C: marca real al final del campo droga ───────────────────────
        if droga and droga != '-' and _RE_SOLO_FORMA2.match(marca):
            match = _RE_DROGA_MARCA2.match(droga)
            if match:
                droga_limpia = match.group(1).strip().rstrip(',').strip()
                nombre_marca = match.group(2).strip()
                if len(nombre_marca) >= 3 and len(droga_limpia) >= 3:
                    m['droga']        = droga_limpia.lower()
                    m['marca']        = nombre_marca.upper()
                    m['presentacion'] = marca.lower()
                    reparados += 1

    return medicamentos, reparados


# ─────────────────────────────────────────────────────────────────────────────
# RESCATE DE LABORATORIOS DESPLAZADOS
# ─────────────────────────────────────────────────────────────────────────────
def rescatar_laboratorios(medicamentos: list) -> tuple:
    """
    Capa 2 de rescate: para registros que escaparon al parser con
    laboratorio='Desconocido', intenta recuperar el laboratorio desde
    el campo 'presentacion' usando el set de laboratorios conocidos
    construido desde el propio dataset.

    Casos que resuelve:
      A) presentacion == laboratorio conocido exacto
         {"presentacion": "Denver Farma", "laboratorio": "Desconocido"}
         → {"presentacion": "Denver Farma", "laboratorio": "Denver Farma"}

      B) presentacion termina con laboratorio conocido
         {"presentacion": "crema x 30 g Bago", "laboratorio": "Desconocido"}
         → {"presentacion": "crema x 30 g", "laboratorio": "Bago"}

    El laboratorio recuperado usa la capitalización original del dataset.
    Mínimo de 4 caracteres para evitar matches espurios en el sufijo.
    """

    # Construir índice: lower → forma original (primera aparición)
    labs_conocidos: dict[str, str] = {}
    for m in medicamentos:
        lab = (m.get('laboratorio') or '').strip()
        if lab and lab != 'Desconocido':
            labs_conocidos.setdefault(lab.lower(), lab)

    rescatados = 0

    for m in medicamentos:
        if m.get('laboratorio') != 'Desconocido':
            continue

        presentacion       = (m.get('presentacion') or '').strip()
        presentacion_lower = presentacion.lower()

        lab_lower    = None
        lab_original = None

        # Caso A: presentacion es exactamente un laboratorio
        if presentacion_lower in labs_conocidos:
            lab_lower    = presentacion_lower
            lab_original = labs_conocidos[lab_lower]

        # Caso B: presentacion termina con un laboratorio (min 4 chars)
        else:
            for ll, lo in labs_conocidos.items():
                if len(ll) >= 4 and presentacion_lower.endswith(ll):
                    lab_lower    = ll
                    lab_original = lo
                    break

        if lab_original:
            m['laboratorio'] = lab_original

            # Limpiar presentacion: si era solo el lab, vaciar;
            # si tenía contenido antes, quitar el sufijo
            if presentacion_lower == lab_lower:
                m['presentacion'] = ''
            else:
                m['presentacion'] = presentacion[:len(presentacion) - len(lab_lower)].strip()

            rescatados += 1

    return medicamentos, rescatados


# ─────────────────────────────────────────────────────────────────────────────
# DETECCION DE OUTLIERS
# ─────────────────────────────────────────────────────────────────────────────
def calcular_stats_por_droga(medicamentos):
    grupos = defaultdict(list)
    for m in medicamentos:
        droga  = (m.get('droga') or '').strip().lower()
        precio = m.get('precio')
        if droga and precio and precio > 0:
            grupos[droga].append(precio)

    stats = {}
    for droga, precios in grupos.items():
        n        = len(precios)
        mediana  = statistics.median(precios)
        sorted_p = sorted(precios)
        q1  = statistics.median(sorted_p[:n // 2])     if n >= 2 else sorted_p[0]
        q3  = statistics.median(sorted_p[(n+1) // 2:]) if n >= 2 else sorted_p[-1]
        iqr = q3 - q1
        stats[droga] = {
            "n":         n,
            "mediana":   round(mediana, 2),
            "q1":        round(q1, 2),
            "q3":        round(q3, 2),
            "iqr":       round(iqr, 2),
            "fence_low": round(q1 - OUTLIER_CONFIG["IQR_FACTOR"] * iqr, 2),
        }
    return stats

def evaluar_outlier(med, stats_droga):
    precio   = med.get('precio')
    droga    = (med.get('droga') or '').strip().lower()
    flags    = []
    score    = OUTLIER_CONFIG["SCORE_NORMAL"]
    tipo     = None
    razones  = []

    if not precio or precio <= 0:
        return OUTLIER_CONFIG["SCORE_OUTLIER"], ['precio_obsoleto'], 'invalido', ['precio_invalido_o_cero']

    stats    = stats_droga.get(droga, {})
    n        = stats.get("n", 0)
    mediana  = stats.get("mediana", 0)
    fence_lw = stats.get("fence_low", 0)

    if precio < OUTLIER_CONFIG["PRECIO_MINIMO_ARS"]:
        flags.append('precio_bajo')
        score = min(score, 45)
        tipo  = tipo or 'bajo_absoluto'
        razones.append(f"precio ${precio:,.2f} < minimo ${OUTLIER_CONFIG['PRECIO_MINIMO_ARS']:,}")

    if mediana > 0 and precio < mediana * OUTLIER_CONFIG["UMBRAL_CRITICO"]:
        flags.append('precio_obsoleto')
        score = min(score, OUTLIER_CONFIG["SCORE_OUTLIER"])
        tipo  = 'bajo_critico'
        razones.append(f"precio ${precio:,.2f} < 10% mediana ${mediana:,.2f}")

    elif n >= OUTLIER_CONFIG["MIN_REGISTROS"] and mediana > 0:
        if precio < mediana * OUTLIER_CONFIG["UMBRAL_RELATIVO"]:
            flags.append('precio_sospechoso')
            score = min(score, 35)
            tipo  = tipo or 'bajo_relativo'
            razones.append(f"precio ${precio:,.2f} < 25% mediana ${mediana:,.2f} (n={n})")
        elif fence_lw > 0 and precio < fence_lw:
            flags.append('precio_sospechoso')
            score = min(score, 40)
            tipo  = tipo or 'bajo_iqr'
            razones.append(f"precio ${precio:,.2f} < fence_low ${fence_lw:,.2f}")

    return score, flags, tipo, razones

def detectar_escala(medicamentos, stats_droga):
    def extraer_cant(pres):
        nums = re.findall(r'\b(\d+)\b', str(pres or ''))
        return int(nums[0]) if nums else None

    grupos = defaultdict(list)
    for i, m in enumerate(medicamentos):
        droga  = (m.get('droga') or '').strip().lower()
        marca  = (m.get('marca') or '').strip().upper()
        precio = m.get('precio')
        cant   = extraer_cant(m.get('presentacion'))
        if precio and precio > 0 and cant and cant > 0:
            grupos[(droga, marca)].append({'idx': i, 'precio': precio, 'cantidad': cant, 'ppu': precio / cant})

    marcados = 0
    for items in grupos.values():
        if len(items) < 2:
            continue
        med_ppu = statistics.median([it['ppu'] for it in items])
        if med_ppu <= 0:
            continue
        for item in items:
            if item['ppu'] < med_ppu * 0.20:
                m = medicamentos[item['idx']]
                if 'precio_obsoleto' not in m.get('flags', []):
                    m.setdefault('flags', [])
                    if 'precio_sospechoso' not in m['flags']:
                        m['flags'].append('precio_sospechoso')
                    m['vigencia_score'] = min(m.get('vigencia_score', 100), 35)
                    m.setdefault('outlier_razones', []).append(
                        f"ppu ${item['ppu']:,.2f} << mediana_grupo ${med_ppu:,.2f}"
                    )
                    if not m.get('precio_outlier_tipo'):
                        m['precio_outlier_tipo'] = 'inconsistencia_escala'
                    marcados += 1
    return marcados

def calcular_vigencia(medicamentos):
    print("\nCalculando estadisticas de outliers...")
    stats = calcular_stats_por_droga(medicamentos)
    print(f"   {len(stats)} drogas distintas")

    for m in medicamentos:
        droga = (m.get('droga') or '').strip().lower()
        score, flags, tipo, razones = evaluar_outlier(m, stats)
        m['vigencia_score']      = score
        m['flags']               = flags
        m['precio_outlier_tipo'] = tipo
        m['outlier_razones']     = razones

    n_escala = detectar_escala(medicamentos, stats)

    outliers = [m for m in medicamentos if m.get('flags')]
    reporte  = {
        "timestamp":       datetime.now(AR_TZ).isoformat(),
        "total_registros": len(medicamentos),
        "total_outliers":  len(outliers),
        "outliers": [
            {
                "droga":             m.get('droga'),
                "marca":             m.get('marca'),
                "presentacion":      m.get('presentacion'),
                "laboratorio":       m.get('laboratorio'),
                "precio":            m.get('precio'),
                "precio_outlier_tipo": m.get('precio_outlier_tipo'),
                "razones":           m.get('outlier_razones', []),
                "mediana_droga":     stats.get((m.get('droga') or '').strip().lower(), {}).get('mediana'),
                "n_droga":           stats.get((m.get('droga') or '').strip().lower(), {}).get('n'),
            }
            for m in outliers
        ]
    }

    OUTLIER_REPORT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTLIER_REPORT, 'w', encoding='utf-8') as f:
        json.dump(reporte, f, ensure_ascii=False, indent=2)

    total    = len(medicamentos)
    criticos = [o for o in reporte['outliers'] if o['precio_outlier_tipo'] == 'bajo_critico']
    print(f"\nOUTLIERS: {len(outliers)}/{total} ({100*len(outliers)/total:.1f}%) | Escala: +{n_escala} | Criticos: {len(criticos)}")
    for o in sorted(criticos, key=lambda x: x['precio'] or 0)[:10]:
        print(f"   {o['marca']} ({o['droga']}): ${o['precio']:,.2f}  [mediana: ${o['mediana_droga']:,.2f}]")
    print(f"   Reporte: {OUTLIER_REPORT}")

    return medicamentos


# ─────────────────────────────────────────────────────────────────────────────
# REPARACIÓN DE REGISTROS CON DROGA FALTANTE (CAPA 0)
# ─────────────────────────────────────────────────────────────────────────────

# Cuando el PDF de SIAFAR omite la línea del principio activo, el parser
# produce registros donde:
#   droga       = '-'  (vacío / guión)
#   marca       = principio activo real  ← desplazado
#   presentacion= marca + presentacion fusionadas
#   laboratorio = correcto
#
# Esta función invierte el desplazamiento:
#   1. Mueve marca → droga
#   2. Separa presentacion en marca_real + presentacion_real usando:
#      A) Dosis numérica como punto de corte
#      B) Forma farmacéutica con espacio previo
#      C) Forma farmacéutica pegada sin espacio (minúscula abrupta)
#      D) Solo presentacion (empieza con minúscula/dígito) → marca queda vacía
#      E) droga_fixes.json para casos especiales
#   3. Para los 5 casos con pres+lab fusionados en lab, extrae pres del lab
#      usando el set de labs conocidos.

_RE_DROGA_SPLIT_DOSIS = re.compile(
    r'^(.+?)\s+(\d[\d,\.]*\s*(?:MG|MCG|G\b|ML|UI|%|U\b).+)$',
    re.IGNORECASE
)
_RE_DROGA_SPLIT_FORMA = re.compile(
    r'^(.+?)\s+((?:comp|caps|cáps|cr\b|gts|jbe|sol\b|susp|ung|gel\b|aer|iny|liof|pomo|'
    r'sob\b|ov\b|grag|env|colirio|emuls|aerosol|pvo|caram|gran|tab\b|film|amp|vial|'
    r'bolsa|sobre|spray|parche|inhal|polvo|sach|fco|frasco|kit|lap\b|sup\b|pouch|'
    r'sachet|perlas|elixir|soluc|a\.x|f\.a|pda\b|liq\b|rollo|cr\.x)[\.\s\-x].+)$',
    re.IGNORECASE
)
_RE_DROGA_SPLIT_PEGADO = re.compile(
    r'^(.+[A-ZÁÉÍÓÚÜÑ\d])([a-záéíóúüñ]{2,}[\.\s].+)$'
)

# Prefijos de droga truncada por el PDF → droga completa correcta.
# Cuando el PDF omite la droga, el campo droga del parser queda con
# principio_activo_truncado + nombre_comercial (en minúsculas) concatenados.
# Este diccionario identifica el prefijo truncado y devuelve la droga completa,
# permitiendo separar correctamente el nombre comercial.
_PREFIJOS_DROGA = {
    'ácido omega 3-ésteres etílicos':          'ácido omega 3-ésteres etílicos',
    'albutrepenonacog alfa - factor':           'albutrepenonacog alfa',
    'albutrepenonacog alfa':                    'albutrepenonacog alfa',
    'bacilo calmette-guerin (bcg)':             'bacilo calmette-guerin',
    'benzocaína, permetrina, bencil':           'benzocaína, permetrina, bencilbenzoato',
    'betametasona (acet.y fosf.diso':           'betametasona (acet. y fosf. disódico)',
    'betametasona (diprop.y f.disod':           'betametasona (diprop. y fosf. disódico)',
    'betametasona, gentamic., micon':           'betametasona, gentamicina, miconazol',
    'activador tisular plasminógeno':           'alteplasa',
    'betametasona, gentamic.':                  'betametasona, gentamicina',
    'betametasona, gentamicina, aso':           'betametasona, gentamicina, asoc.',
    'calamina, difenhidramina, asoc':           'calamina, difenhidramina, asoc.',
    'carbocisteína, dextrometorfano':           'carbocisteína, dextrometorfano',
    'clindamicina, benzoílo,peróxid':           'clindamicina, benzoílo, peróxido',
    'clorfeniramina, dextrometorfan':           'clorfeniramina, dextrometorfano',
    'colagenasa, cloranfenicol, aso':           'colagenasa, cloranfenicol, asoc.',
    'decametrina, piperonilbutóxido':           'decametrina, piperonilbutóxido',
    'desloratadina, pseudoefedrina':            'desloratadina, pseudoefedrina',
    'dexametasona, clorfeniramina':             'dexametasona, clorfeniramina',
    'dexametasona, neomicina, asoc.':           'dexametasona, neomicina, asoc.',
    'dextrometorfano, difenhidramin':           'dextrometorfano, difenhidramina',
    'diclofenac potásico, betametas':           'diclofenac potásico, betametasona',
    'diclofenac potásico, paracetam':           'diclofenac potásico, paracetamol',
    'diclofenac sódico, paracetamol':           'diclofenac sódico, paracetamol',
    'diclofenac sódico, tobramicina':           'diclofenac sódico, tobramicina',
    'diosmina, hesperidina microniz':           'diosmina, hesperidina micronizada',
    'empagliflozina, metformina clo':           'empagliflozina, metformina clorhidrato',
    'eritropoyetina recomb.humana':             'eritropoyetina recombinante humana',
    'ext.seco de ruscus, hesperidin':           'ext. seco de ruscus, hesperidina',
    'factor viii coagulación recomb':           'factor viii de coagulación recombinante',
    'gammaglobulina antitetán., tox':           'gammaglobulina antitetánica',
    'gentamicina, benzocaína, asoc.':           'gentamicina, benzocaína, asoc.',
    'haemophilus influenz.b, dpt, a':           'haemophilus influenzae b, dpt, antipolio',
    'ibuprofeno, ergotamina, cafeín':           'ibuprofeno, ergotamina, cafeína',
    'lamivudina, zidovudina, nevira':           'lamivudina, zidovudina, nevirapina',
    'miconazol, metronidazol, asoc.':           'miconazol, metronidazol, asoc.',
    'nomegestrol,acetato, estradiol':           'nomegestrol acetato, estradiol',
    'nonacog beta pegol - factor ix':           'nonacog beta pegol (factor ix)',
    'oximetazolina, hialuronato sód':           'oximetazolina, hialuronato sódico',
    'paracetamol, clorfeniramina, a':           'paracetamol, clorfeniramina, asoc.',
    'paracetamol, difenhidramina, a':           'paracetamol, difenhidramina, asoc.',
    'paracetamol, pseudoefedrina, a':           'paracetamol, pseudoefedrina, asoc.',
    'plántago ovata, cassia angusti':           'plántago ovata, cassia angustifolia',
    'polisac.meningocóc.a-c-y-w135':           'polisacáridos meningocócicos a-c-y-w135',
    'polisacáridos de s.pneumoniae':            'polisacáridos de streptococcus pneumoniae',
    'ruscogenina, hesperidina, asoc':           'ruscogenina, hesperidina, asoc.',
    'sodio,acexamato, cetrimonio,br':           'sodio acexamato, cetrimonio bromuro',
    'sodio,acexamato, gentamicina':             'sodio acexamato, gentamicina',
    'takadiastasa, pancreatina, pep':           'takadiastasa, pancreatina, pepsina',
    'vacuna dpt, antipoliomielítica':           'vacuna dpt, antipoliomielítica',
}

def _separar_droga_marca(droga_raw: str) -> tuple:
    """
    Dado el campo droga fusionado (principio_activo_truncado + nombre_comercial),
    retorna (droga_completa, nombre_comercial) usando el diccionario de prefijos.
    Si no hay match, retorna (None, None).
    """
    droga_lower = droga_raw.lower()
    # Ordenar de mayor a menor longitud para matchear el prefijo más específico
    for prefijo, droga_completa in sorted(_PREFIJOS_DROGA.items(), key=lambda x: -len(x[0])):
        if droga_lower.startswith(prefijo.lower()):
            resto = droga_raw[len(prefijo):].strip()
            return droga_completa, resto
    return None, None

def reparar_droga_faltante(medicamentos: list, fixes: dict) -> tuple:
    """
    Capa 0: corrige registros donde la droga (principio activo) falta en el
    PDF y todos los campos se desplazaron un slot hacia arriba.

    Retorna el dataset corregido y la cantidad de registros reparados.
    """
    # Set de labs conocidos para separar pres+lab fusionados en campo lab
    labs_conocidos = {
        (m.get('laboratorio') or '').strip().lower(): (m.get('laboratorio') or '').strip()
        for m in medicamentos
        if m.get('laboratorio') and m['laboratorio'] != 'Desconocido'
    }

    reparados = 0

    for m in medicamentos:
        droga = (m.get('droga') or '').strip()
        marca = (m.get('marca') or '').strip()

        # Procesar cuando:
        # a) droga está vacía o es '-' (campo desplazado)
        # b) marca está vacía y droga tiene droga+marca fusionadas (246 casos)
        tiene_droga_vacia  = not droga or droga == '-'
        tiene_marca_vacia  = not marca and droga  # droga tiene contenido fusionado

        if not tiene_droga_vacia and not tiene_marca_vacia:
            continue

        pres  = (m.get('presentacion') or '').strip()
        lab   = (m.get('laboratorio') or '').strip()

        # ── Verificar si hay fix especial para este caso ──────────────────
        fix = fixes.get(pres.upper()) or fixes.get(marca.upper())
        if fix and isinstance(fix, dict) and fix.get('laboratorio_pres'):
            # pres+lab fusionados en lab → extraer pres del lab
            m['droga'] = fix['droga']
            m['marca'] = fix['marca']
            lab_lower  = lab.lower()
            for ll, lo in labs_conocidos.items():
                if len(ll) >= 4 and lab_lower.endswith(ll):
                    m['presentacion'] = lab[:len(lab) - len(ll)].strip().lower()
                    m['laboratorio']  = lo
                    break
            reparados += 1
            continue

        # ── Caso especial: marca vacía → droga tiene droga+marca fusionadas ──
        # El campo droga contiene principio_activo_truncado + nombre_comercial.
        # Usamos el diccionario de prefijos para separar correctamente.
        if not marca:
            droga_completa, nombre_comercial = _separar_droga_marca(droga)
            if droga_completa and nombre_comercial:
                m['droga'] = droga_completa

                # nombre_comercial puede tener marca+pres pegadas — separar
                match_pres = re.search(
                    r'^(.+?)\s*([a-záéíóúüñ]{2,}[\.\s].+|\d.+)$',
                    nombre_comercial, re.IGNORECASE
                )
                if match_pres and not pres:
                    m['marca']        = match_pres.group(1).strip().upper()
                    m['presentacion'] = match_pres.group(2).strip().lower()
                else:
                    m['marca'] = nombre_comercial.strip().upper()
                reparados += 1
            continue

        # ── La droga real está en marca, moverla ─────────────────────────
        m['droga'] = marca.lower()

        # ── Separar presentacion en marca_real + presentacion_real ───────

        # Caso D: ya es solo presentacion (empieza con minúscula o dígito)
        if pres and (pres[0].islower() or pres[0].isdigit()):
            m['marca']        = ''
            m['presentacion'] = pres.lower()
            reparados += 1
            continue

        # Caso A: dosis como punto de corte
        match = _RE_DROGA_SPLIT_DOSIS.match(pres)
        if match:
            m['marca']        = match.group(1).strip()
            m['presentacion'] = match.group(2).strip().lower()
            reparados += 1
            continue

        # Caso B: forma farmacéutica con espacio
        match = _RE_DROGA_SPLIT_FORMA.match(pres)
        if match:
            m['marca']        = match.group(1).strip()
            m['presentacion'] = match.group(2).strip().lower()
            reparados += 1
            continue

        # Caso C: forma farmacéutica pegada sin espacio (minúscula abrupta)
        match = _RE_DROGA_SPLIT_PEGADO.match(pres)
        if match:
            m['marca']        = match.group(1).strip()
            m['presentacion'] = match.group(2).strip().lower()
            reparados += 1
            continue

        # Sin resolver: mover igual la droga, dejar presentacion como está
        m['marca'] = pres
        reparados += 1

    # ── Fixes puntuales post-loop ─────────────────────────────────────────
    # Casos que el diccionario de prefijos no cubre por su estructura especial

    for m in medicamentos:
        droga = (m.get('droga') or '').strip()
        marca = (m.get('marca') or '').strip()

        # HISTAGLOBIN: marca contiene la presentacion (kit complejo)
        if 'histamihistaglobin' in droga and marca == 'LIOF.F.A.+A.DIL.+JER.+AG':
            m['presentacion'] = marca.lower()
            m['marca']        = 'HISTAGLOBIN TRIPLEX' if 'triplex' in droga else 'HISTAGLOBIN'
            m['droga']        = 'gammaglobulina humana, histamina'
            reparados += 1

        # DIABESIL AP 1000: lab tiene pres+lab fusionados
        elif marca == 'DIABESIL AP 1000' and not (m.get('presentacion') or '').strip():
            lab = (m.get('laboratorio') or '').strip()
            match = re.match(r'^(.+?)\s+(Gador.*)$', lab)
            if match:
                m['presentacion'] = match.group(1).strip().lower()
                m['laboratorio']  = match.group(2).strip()
                reparados += 1

        # VAXNEUVANCE: lab truncado
        elif marca == 'VAXNEUVANCE':
            m['laboratorio'] = 'MSD Argentina S.A.'

    return medicamentos, reparados


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    pdf_url = "https://siafar.com/precios/pdf/"
    print(f"Descargando: {pdf_url}")

    req = urllib.request.Request(pdf_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30, context=ssl_context) as r:
        pdf_bytes = r.read()
    print(f"Tamano: {len(pdf_bytes)} bytes")

    doc          = fitz.open(stream=pdf_bytes, filetype="pdf")
    medicamentos = []

    for pagina_num in range(len(doc)):
        texto  = doc[pagina_num].get_text()
        lineas = [l.strip() for l in texto.split('\n') if l.strip()]
        i = 0
        while i < len(lineas):
            linea = lineas[i]
            if 'MONODROGA' in linea or 'pag' in linea.lower():
                i += 1; continue
            if es_precio(linea):
                i += 1; continue

            # ── CAPA 1: detección de desplazamiento en tiempo de parse 
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
            #   i+2  laboratorio  ← ocupa el slot de presentacion
            #   i+3  precio       ← sube un lugar
            #
            # Detección: si lineas[i+3] ya es precio, el laboratorio
            # se desplazó a lineas[i+2] y no hay presentacion separada.

            if i + 3 < len(lineas) and es_precio(lineas[i+3]):
                # Estructura de 4 campos: lab en slot de presentacion
                droga        = linea
                marca        = lineas[i+1]
                presentacion = ''
                laboratorio  = lineas[i+2]
                precio_str   = lineas[i+3]
                avance       = 4
            elif i + 4 < len(lineas):
                # Estructura normal de 5 campos
                droga        = linea
                marca        = lineas[i+1]
                presentacion = lineas[i+2]
                laboratorio  = lineas[i+3]
                precio_str   = lineas[i+4]
                avance       = 5
            else:
                i += 1; continue

            if es_precio(precio_str):
                precio = limpiar_precio(precio_str)
                if precio and droga:
                    medicamentos.append({
                        'droga':        droga.lower(),
                        'marca':        marca.upper(),
                        'presentacion': presentacion,
                        'laboratorio':  laboratorio if not es_precio(laboratorio) else 'Desconocido',
                        'precio':       precio,
                    })
                i += avance; continue

            i += 1

        if (pagina_num + 1) % 10 == 0:
            print(f"Pagina {pagina_num + 1}: {len(medicamentos)} medicamentos")

    doc.close()
    print(f"\nTotal extraido: {len(medicamentos)}")

    if not medicamentos:
        print("No se extrajo ningun medicamento")
        sys.exit(1)

    # ── CAPA 0: cargar fixes y reparar registros con droga faltante ───────
    fixes_droga = {}
    if DROGA_FIXES_PATH.exists():
        with open(DROGA_FIXES_PATH, encoding='utf-8') as f:
            fixes_droga = json.load(f)
    print("\nReparando registros con droga faltante (capa 0)...")
    medicamentos, n_capa0 = reparar_droga_faltante(medicamentos, fixes_droga)
    print(f"   Reparados: {n_capa0}")

    # ── CAPA 2: rescate post-parse con laboratorios conocidos ──────────────
    print("\nRescatando laboratorios desplazados...")
    medicamentos, n_rescatados = rescatar_laboratorios(medicamentos)
    n_desconocidos = sum(1 for m in medicamentos if m.get('laboratorio') == 'Desconocido')
    print(f"   Rescatados: {n_rescatados} | Sin recuperar: {n_desconocidos}")

    # ── CAPA 3: reparación de fusiones marca+presentacion de Denver Farma ──
    print("\nReparando registros Denver Farma...")
    medicamentos, n_denver = reparar_denver(medicamentos)
    print(f"   Reparados: {n_denver}")

    # ── CAPA 4: reparación de marca desplazada (nombre comercial en droga) ──
    print("\nReparando marcas desplazadas...")
    medicamentos, n_marca = reparar_marca_desplazada(medicamentos)
    print(f"   Reparados: {n_marca}")

    # ── CAPA 5: extraer presentacion fusionada en marca ───────────────────
    print("\nExtrayendo presentacion de marca fusionada...")
    medicamentos, n_extrac = extraer_presentacion_de_marca(medicamentos)
    print(f"   Reparados: {n_extrac}")

    # ── CAPA 5b: reparar presentacion desplazada al campo lab ────────────
    print("\nReparando presentacion desplazada...")
    medicamentos, n_pres = reparar_presentacion_desplazada(medicamentos)
    print(f"   Reparados: {n_pres}")

    # ── CAPA 6: crosswalk PAMI → recuperar droga y corregir laboratorio ───
    print("\nCrosswalk PAMI...")
    medicamentos, stats_pami = crosswalk_pami(medicamentos)
    print(f"   Matches exactos: {stats_pami['match_exacto']} | "
          f"Drogas recuperadas: {stats_pami['droga_recuperada']} | "
          f"Labs corregidos: {stats_pami['lab_corregido']}")

    # ── CAPA 7: fixes manuales de droga ──────────────────────────────────
    print("\nAplicando fixes manuales de droga...")
    medicamentos, n_fixes = aplicar_droga_fixes(medicamentos)
    print(f"   Corregidos: {n_fixes}")

    print("\nAplicando lista negra...")
    blacklist            = cargar_blacklist()
    medicamentos, n_bl   = filtrar_blacklist(medicamentos, blacklist)
    medicamentos         = calcular_vigencia(medicamentos)

    ahora_ar  = datetime.now(AR_TZ)
    fecha_str = ahora_ar.strftime("%Y-%m-%d %H:%M:%S")
    data = {
        "fecha":        fecha_str,
        "fuente":       pdf_url,
        "total":        len(medicamentos),
        "blacklisted":  n_bl,
        "medicamentos": medicamentos,
    }

    MEDICAMENTOS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MEDICAMENTOS_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))

    print(f"\nGuardado: {MEDICAMENTOS_PATH}")
    print(f"Total: {len(medicamentos)} | Excluidos (blacklist): {n_bl} | Fecha: {fecha_str}")

if __name__ == "__main__":
    main()