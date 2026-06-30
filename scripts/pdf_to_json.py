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

import certifi
ssl_context = ssl.create_default_context(cafile=certifi.where())

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
PRES_DEBUG_PATH   = BASE / "data" / "presentaciones_debug.csv"


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
        # Corregir doble encoding en claves (latin-1 interpretado como utf-8)
        fixed = {}
        for key, val in bl.items():
            try:
                fixed_key = key.encode('latin-1').decode('utf-8')
            except (UnicodeDecodeError, UnicodeEncodeError):
                fixed_key = key
            fixed[fixed_key] = val
        print(f"   Lista negra: {len(fixed)} entradas cargadas")
        return fixed
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

    stats = {'match_exacto': 0, 'droga_recuperada': 0, 'lab_corregido': 0, 'pami_cobertura': 0}

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

            # Guardar cobertura PAMI como entero (ej: "55%" → 55)
            cobertura_raw = str(row.get('COBERTURA', '') or '')
            if cobertura_raw.strip().endswith('%'):
                try:
                    m['pami_cobertura'] = int(cobertura_raw.strip().rstrip('%'))
                    stats['pami_cobertura'] += 1
                except ValueError:
                    pass

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
    r'|BOLSA|VIAL|SPRAY|ESPUMA|LACA|POUCH|JALEA|POTE|FCO|TOALLITAS'
    r'|PCOMP'   # TRB-Pharma: "TRB PCOMP.rec.x 30" donde P precede COMP
)

_RE_EXTRAER_PRES = re.compile(
    r'^(.+?)\s+(\d[\d,./]*\s*(?:MG|MCG|G\b|ML|UI|%|U\b).*'
    r'|(?:' + _FORMAS_FARM + r')[\.\s].+)$',
    re.IGNORECASE
)


def _build_re_lab_pegado(medicamentos: list):
    """
    Construye un regex que detecta cuando un laboratorio conocido (de los
    que YA aparecen correctamente en el campo 'laboratorio' de otros
    registros del propio dataset) quedó pegado SIN espacio a la dosis o
    forma que le sigue dentro del campo 'marca'.

    Caso real (laboratorios que venden genéricos sin marca de fantasía,
    usando "DROGA LABORATORIO" como descripción comercial):
        "BICALUTAMIDA TECHSPHERE50 mg comp.x 30"
        "CARBOPLATINO MICROSULES150 mg iny.f.a.x 1"
        "LEVOMEPROMAZINA VANNIER25 mg comp.x 30"

    Sin este separador, _RE_EXTRAER_PRES se traga la dosis dentro de la
    marca (ej: marca="BICALUTAMIDA TECHSPHERE50 mg" en vez de
    "BICALUTAMIDA TECHSPHERE"), porque el \\s* antes de la unidad es
    opcional y el dígito pegado al laboratorio parece el inicio de la
    dosis igual.

    Se usa solo la ÚLTIMA PALABRA significativa de cada laboratorio
    conocido (no el nombre completo), porque es esa la que queda pegada
    a la dosis en el campo 'marca' — el PDF nunca repite ahí el nombre
    completo del laboratorio. Ej: laboratorio="Delta Farma" pero en la
    marca aparece "...DELTA FARMA500 mg..." (la dosis pegada a "FARMA",
    la última palabra, no a "DELTA"). También se ignoran sufijos
    legales/societarios cortos o puntuados (Arg., S.A.U., (PH), etc.)
    que tampoco se repiten ahí. Se exige un mínimo de 4 caracteres para
    evitar matches espurios con palabras cortas.

    El índice se construye desde el propio dataset (mismo patrón que
    usa rescatar_laboratorios()), no es una lista hardcodeada aparte.
    """
    ultimas_palabras = set()
    for m in medicamentos:
        lab = (m.get('laboratorio') or '').strip()
        if lab in ('', 'Desconocido'):
            continue
        palabras = [p for p in lab.split() if re.match(r'^[A-Za-zÁÉÍÓÚÑáéíóúñ]+$', p)]
        if palabras:
            ultima = palabras[-1]
            if len(ultima) >= 4:
                ultimas_palabras.add(ultima)

    if not ultimas_palabras:
        return None
    labs_validos = sorted(ultimas_palabras, key=len, reverse=True)
    patron_labs = '|'.join(re.escape(lab) for lab in labs_validos)
    # Un laboratorio conocido seguido directamente (sin espacio) de un
    # DÍGITO. Se exige dígito (no letra) a propósito: un lookahead más
    # laxo (cualquier letra) generaba falsos positivos graves en marcas
    # de fantasía que contienen el nombre de un laboratorio como
    # substring por coincidencia, ej. "RAFFOLUTIL" (contiene "Raffo",
    # laboratorio real) se partía en "RAFFO LUTIL" sin que hubiera
    # ningún pegado real que arreglar. Los pocos casos de forma
    # abreviada en mayúscula pegada sin dígito de por medio (ej.
    # "VANNIERAd.gts.x 20 ml") quedan fuera de este fix puntual.
    return re.compile(r'\b(' + patron_labs + r')(?=\d)', re.IGNORECASE)


# Separa formas farmacéuticas pegadas sin espacio al texto previo.
# "NUTRIFLEX OMEGA ESPECIALbolsa x 1250 ml" -> "NUTRIFLEX OMEGA ESPECIAL bolsa x 1250 ml"
_RE_FORMA_PEGADA = re.compile(
    r'(?<=[A-ZÁÉÍÓÚÑa-záéíóúñ])'
    r'(bolsa|vial|spray|espuma|laca|pouch|jalea|pote|fco|toallitas|gel'
    r'|comp\.|caps\.|cáps\.|cr\.|gts\.|jbe\.|sol\.|susp\.|iny\.|aer\.)'
    r'(?=[\sx\d])',
    re.IGNORECASE,
)

# Detecta el patrón TOKEN_MAYUSC + mismoToken_minus (ej. GELgel, BOLSAbolsa)
# para eliminar el duplicado en mayúsculas antes de insertar el espacio.
_RE_TOKEN_DUPLICADO = re.compile(
    r'\b(BOLSA|VIAL|SPRAY|ESPUMA|LACA|POUCH|JALEA|POTE|FCO|GEL)'
    r'(?=\1)',   # lookahead: mismo token inmediatamente después (case-insensitive handled below)
    re.IGNORECASE,
)


def separar_lab_pegado_de_marca(marca: str, re_lab_pegado) -> str:
    """
    Inserta un espacio entre un laboratorio conocido y la dosis/forma
    que le sigue sin separación, y también entre texto y formas
    farmacéuticas pegadas sin espacio.

    "BICALUTAMIDA TECHSPHERE50 mg comp.x 30"
        -> "BICALUTAMIDA TECHSPHERE 50 mg comp.x 30"
    "NUTRIFLEX OMEGA ESPECIALbolsa x 1250 ml"
        -> "NUTRIFLEX OMEGA ESPECIAL bolsa x 1250 ml"
    """
    nueva = _RE_TOKEN_DUPLICADO.sub('', marca)  # eliminar GELgel → gel, BOLSAbolsa → bolsa
    nueva = _RE_FORMA_PEGADA.sub(lambda m: ' ' + m.group(1), nueva)
    if re_lab_pegado is None:
        return nueva
    return re_lab_pegado.sub(lambda m: m.group(1) + ' ', nueva)


def extraer_presentacion_de_marca(medicamentos: list) -> tuple:
    """
    Para registros con presentacion vacía, intenta extraer la presentacion
    desde el campo marca cuando ambos campos quedaron fusionados.

    Antes de aplicar el regex de corte, separa los casos donde un
    laboratorio conocido quedó pegado sin espacio a la dosis/forma
    siguiente (ver separar_lab_pegado_de_marca), para que el corte caiga
    en el lugar correcto y no se trague la dosis dentro de la marca.

    Solo actúa cuando el nombre resultante tiene al menos 3 caracteres
    y no empieza con dígito (descarta falsos positivos).

    Retorna el dataset corregido y la cantidad de registros reparados.
    """
    re_lab_pegado = _build_re_lab_pegado(medicamentos)

    reparados = 0
    for m in medicamentos:
        if (m.get("presentacion") or "").strip():
            continue
        if m.get("laboratorio") in ("Desconocido", ""):
            continue

        marca = (m.get("marca") or "").strip()
        marca = separar_lab_pegado_de_marca(marca, re_lab_pegado)
        match = _RE_EXTRAER_PRES.match(marca)
        if match:
            nombre = match.group(1).strip()
            pres   = match.group(2).strip().lower()
            if len(nombre) >= 3 and not nombre[0].isdigit():
                m["marca"]        = nombre
                m["presentacion"] = pres
                reparados += 1

    return medicamentos, reparados


_RE_DOSIS_RESIDUAL = re.compile(
    r'\s+\d[\d,./]*\s*(?:MG|MCG|G|ML|UI|%|U)\b.*$',
    re.IGNORECASE
)


def limpiar_dosis_residual_en_marca(medicamentos: list) -> tuple:
    """
    Limpia el residuo de dosis que queda pegado a un laboratorio dentro
    de 'marca' incluso cuando 'presentacion' YA tiene contenido (por eso
    es una pasada aparte de extraer_presentacion_de_marca, que sólo
    actúa con presentacion vacía).

    Ocurre cuando otra capa (ej. reparar_presentacion_desplazada) separó
    correctamente la FORMA hacia 'presentacion' pero dejó la DOSIS
    pegada al laboratorio en 'marca':
        marca="CIPROFLOXACINA SANT GALL500 MG"  presentacion="comp.x 10"
        -> marca="CIPROFLOXACINA SANT GALL"     presentacion sin tocar

    Solo actúa cuando, tras separar el laboratorio pegado (mismo
    mecanismo que separar_lab_pegado_de_marca), el residuo eliminado es
    puramente una dosis numérica al final de la marca — nunca toca
    marcas que terminan en dosis por motivos propios sin laboratorio
    pegado de por medio, para no arriesgar falsos positivos.

    Retorna el dataset corregido y la cantidad de registros reparados.
    """
    re_lab_pegado = _build_re_lab_pegado(medicamentos)
    if re_lab_pegado is None:
        return medicamentos, 0

    reparados = 0
    for m in medicamentos:
        marca = (m.get("marca") or "").strip()
        if not marca:
            continue

        separada = separar_lab_pegado_de_marca(marca, re_lab_pegado)
        if separada == marca:
            continue  # no había laboratorio pegado a un dígito

        # Tras separar, si lo que queda después del laboratorio es
        # exclusivamente una dosis (no una forma farmacéutica completa
        # ni texto adicional con letras no numéricas), se recorta.
        sin_dosis = _RE_DOSIS_RESIDUAL.sub('', separada).strip()
        if sin_dosis != separada and len(sin_dosis) >= 3:
            m["marca"] = sin_dosis
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
_RE_DROGA_SPLIT_DOSIS_PEGADA = re.compile(
    r'^(.+?[A-ZÁÉÍÓÚÜÑ])(\d[\d,\.]*\s*(?:MG|MCG|G\b|ML|UI|%|U\b).+)$',
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
        # Caso: droga vacía y marca tiene principio_activo+nombre_comercial fusionados
        # El parser asigna marca=DROGA.upper() cuando el PDF omite el campo droga
        tiene_droga_en_marca = (not droga or droga == '-') and bool(marca)
        # Caso: droga tiene contenido pero marca está vacía (post-procesamiento anterior)
        tiene_marca_vacia    = not marca and droga

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
        # También: droga vacía y marca tiene principio_activo+nombre_comercial fusionados
        # (el parser asigna marca=DROGA.upper() cuando el PDF omite el campo droga)
        campo_fusionado = droga if not marca else marca.lower()
        if not marca or (not droga or droga == '-'):
            droga_completa, nombre_comercial = _separar_droga_marca(campo_fusionado)
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
            if not marca:
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

        # Caso A2: dosis pegada a la marca sin espacio
        match = _RE_DROGA_SPLIT_DOSIS_PEGADA.match(pres)
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
# PARSER DE PRESENTACIONES (debug CSV)
# ─────────────────────────────────────────────────────────────────────────────

_FORMAS_NORM_PRES = {
    'comp.rec.ran': 'COMPRIMIDOS RECUBIERTOS RANURADOS',
    'comp.rec.gast': 'COMPRIMIDOS GASTRORRESISTENTES',
    'comp.rec.lib.prol': 'COMPRIMIDOS LIBERACIÓN PROLONGADA RECUBIERTOS',
    'comp.rec.acc.prol': 'COMPRIMIDOS ACCIÓN PROLONGADA RECUBIERTOS',
    'comp.rec.ap': 'COMPRIMIDOS ACCIÓN PROLONGADA RECUBIERTOS',
    'comp.lib.prol': 'COMPRIMIDOS LIBERACIÓN PROLONGADA',
    'comp.lib.cont': 'COMPRIMIDOS LIBERACIÓN CONTROLADA',
    'comp.lib.contr': 'COMPRIMIDOS LIBERACIÓN CONTROLADA',
    'comp.lib.modif': 'COMPRIMIDOS LIBERACIÓN MODIFICADA',
    'comp.rec': 'COMPRIMIDOS RECUBIERTOS',
    'comp. rec': 'COMPRIMIDOS RECUBIERTOS',
    'comp.ran': 'COMPRIMIDOS RANURADOS',
    'comp.ranur': 'COMPRIMIDOS RANURADOS',
    'comp.birranur': 'COMPRIMIDOS BIRRANURADOS',
    'comp.birran': 'COMPRIMIDOS BIRRANURADOS',
    'comp.trirran': 'COMPRIMIDOS TRIRRANURADOS',
    'comp.subl': 'COMPRIMIDOS SUBLINGUALES',
    'comp.mast': 'COMPRIMIDOS MASTICABLES',
    'comp.efer': 'COMPRIMIDOS EFERVESCENTES',
    'comp.ef': 'COMPRIMIDOS EFERVESCENTES',
    'comp.dispers': 'COMPRIMIDOS DISPERSABLES',
    'comp.acc.prol': 'COMPRIMIDOS ACCIÓN PROLONGADA',
    'comp.ap': 'COMPRIMIDOS ACCIÓN PROLONGADA',
    'comp': 'COMPRIMIDOS',
    'cáps.blandas': 'CÁPSULAS BLANDAS', 'caps.blandas': 'CÁPSULAS BLANDAS',
    'cáps.duras': 'CÁPSULAS DURAS', 'caps.duras': 'CÁPSULAS DURAS',
    'cáps.bl': 'CÁPSULAS BLANDAS', 'caps.bl': 'CÁPSULAS BLANDAS',
    'cáps. bl': 'CÁPSULAS BLANDAS', 'caps. bl': 'CÁPSULAS BLANDAS',
    'cáps.lib.cont': 'CÁPSULAS LIBERACIÓN CONTROLADA',
    'cáps.lib.contr': 'CÁPSULAS LIBERACIÓN CONTROLADA',
    'caps.lib.cont': 'CÁPSULAS LIBERACIÓN CONTROLADA',
    'cáps.lib.prol': 'CÁPSULAS LIBERACIÓN PROLONGADA',
    'caps.lib.prol': 'CÁPSULAS LIBERACIÓN PROLONGADA',
    'cáps.p/inhalar': 'CÁPSULAS PARA INHALACIÓN',
    'cáps.p/inh': 'CÁPSULAS PARA INHALACIÓN',
    'caps.p/inh': 'CÁPSULAS PARA INHALACIÓN',
    'cáps': 'CÁPSULAS', 'caps': 'CÁPSULAS',
    'iny.liof': 'INYECTABLE LIOFILIZADO',
    'iny.f.a': 'INYECTABLE FRASCO AMPOLLA',
    'iny.a': 'INYECTABLE AMPOLLA',
    'iny': 'INYECTABLE',
    'liof.f.a': 'LIOFILIZADO FRASCO AMPOLLA',
    'f.a.liof': 'FRASCO AMPOLLA LIOFILIZADO',
    'liof': 'LIOFILIZADO',
    'f.a': 'FRASCO AMPOLLA',
    'fco.a': 'FRASCO AMPOLLA', 'fco.gotero': 'FRASCO GOTERO', 'fco': 'FRASCO',
    'a.': 'AMPOLLA', 'a': 'AMPOLLA', 'amp': 'AMPOLLA',
    'vial': 'VIAL', 'bolsa': 'BOLSA',
    'jga.prell': 'JERINGA PRELLENADA', 'lap.prell': 'LAPICERA PRELLENADA',
    'jga': 'JERINGA', 'autoinyector': 'AUTOINYECTOR', 'autoin': 'AUTOINYECTOR',
    'lap': 'LAPICERA', 'pluma': 'LAPICERA', 'env': 'ENVASE',
    'sol.oft': 'SOLUCIÓN OFTÁLMICA', 'sol.of': 'SOLUCIÓN OFTÁLMICA',
    'sol.oral': 'SOLUCIÓN ORAL', 'sol. oral': 'SOLUCIÓN ORAL',
    'sol.top': 'SOLUCIÓN TÓPICA', 'sol.tópica': 'SOLUCIÓN TÓPICA',
    'sol.neb': 'SOLUCIÓN NEBULIZABLE', 'sol.p/neb': 'SOLUCIÓN NEBULIZABLE',
    'sol.p/nebulizar': 'SOLUCIÓN NEBULIZABLE', 'sol.iny': 'SOLUCIÓN INYECTABLE',
    'sol': 'SOLUCIÓN',
    'susp.oral': 'SUSPENSIÓN ORAL', 'susp.nasal': 'SUSPENSIÓN NASAL', 'susp': 'SUSPENSIÓN',
    'jbe': 'JARABE', 'jarabe': 'JARABE', 'liq': 'LÍQUIDO', 'elixir': 'ELIXIR',
    'gts.oft': 'GOTAS OFTÁLMICAS', 'gts.óticas': 'GOTAS ÓTICAS',
    'gts.ót': 'GOTAS ÓTICAS', 'gts.nas': 'GOTAS NASALES', 'gts': 'GOTAS',
    'colirio': 'COLIRIO',
    'cr.dérmica': 'CREMA DÉRMICA', 'cr.dérm': 'CREMA DÉRMICA', 'cr': 'CREMA',
    'gel': 'GEL', 'ung': 'UNGÜENTO', 'pomo': 'POMO', 'jalea': 'JALEA',
    'lot': 'LOCIÓN', 'loc': 'LOCIÓN', 'emuls': 'EMULSIÓN',
    'xamp': 'CHAMPÚ', 'shamp': 'CHAMPÚ',
    'roll-on': 'ROLL-ON', 'pda': 'PARCHE', 'parche': 'PARCHE',
    'aer.bronq': 'AEROSOL BRONQUIAL', 'aer': 'AEROSOL', 'aerosol': 'AEROSOL',
    'inhal': 'INHALADOR', 'spray': 'SPRAY', 'nasal': 'SPRAY NASAL', 'puff': 'PUFF',
    'ov.vag': 'ÓVULOS VAGINALES', 'óv.vag': 'ÓVULOS VAGINALES',
    'óv': 'ÓVULOS', 'ov': 'ÓVULOS', 'sup': 'SUPOSITORIOS',
    'polv.p/susp.oral': 'POLVO PARA SUSPENSIÓN ORAL',
    'polv.p/susp': 'POLVO PARA SUSPENSIÓN', 'polv.p/sol': 'POLVO PARA SOLUCIÓN',
    'pvo.p/susp': 'POLVO PARA SUSPENSIÓN', 'pvo.sob': 'POLVO SOBRES',
    'pvo': 'POLVO', 'polv': 'POLVO',
    'gran.sob': 'GRÁNULOS SOBRES', 'gran': 'GRÁNULOS',
    'blist.grag': 'BLÍSTER GRAGEAS', 'blist': 'BLÍSTER',
    'sob': 'SOBRES', 'sobre': 'SOBRES', 'sobres': 'SOBRES', 'sachet': 'SOBRES',
    'pouch': 'POUCH', 'kit': 'KIT',
    'grag': 'GRAGEAS', 'tab': 'TABLETAS', 'caram': 'CARAMELOS', 'film': 'FILM',
    # Formas adicionales no mapeadas previamente
    'caplets': 'TABLETAS',
    'laca': 'LACA',
    'laq': 'LACA',
    'espuma': 'ESPUMA',
    'espuma rectal': 'ESPUMA RECTAL',
    'expend.sob': 'SOBRES EXPENDEDOR',
    'polv.p/susp.oral': 'POLVO PARA SUSPENSIÓN ORAL',
    'pvo.liof': 'POLVO LIOFILIZADO',
    'pvo.vial': 'POLVO VIAL',
    'jer.prell': 'JERINGA PRELLENADA',
    'jer.pr': 'JERINGA PRELLENADA',
    'jga.pr': 'JERINGA PRELLENADA',
    'sol.f.a': 'SOLUCIÓN FRASCO AMPOLLA',
    'iny.sol': 'SOLUCIÓN INYECTABLE',
    'iny.liof': 'INYECTABLE LIOFILIZADO',
    'iv': 'INYECTABLE INTRAVENOSO',
    'tab.dis.inst': 'TABLETAS DISPERSABLES DE DISOLUCIÓN INSTANTÁNEA',
    'tab.disp': 'TABLETAS DISPERSABLES',
    'dis.inst': 'DISOLUCIÓN INSTANTÁNEA',
    'comp.gastr': 'COMPRIMIDOS GASTRORRESISTENTES',
    'comp.laq': 'COMPRIMIDOS LACADOS',
    'comp.rapirtd': 'COMPRIMIDOS LIBERACIÓN RÁPIDA',
    'comp.divis': 'COMPRIMIDOS DIVISIBLES',
    'comp.divids': 'COMPRIMIDOS DIVISIBLES',
    'comp.ran.divids': 'COMPRIMIDOS RANURADOS DIVISIBLES',
    'caps.bl.gastr': 'CÁPSULAS BLANDAS GASTRORRESISTENTES',
    'cáps.bl.gastr': 'CÁPSULAS BLANDAS GASTRORRESISTENTES',
    'sol.oft.esteril': 'SOLUCIÓN OFTÁLMICA ESTÉRIL',
    'sol.oft.estéril': 'SOLUCIÓN OFTÁLMICA ESTÉRIL',
    'fco.vial': 'FRASCO VIAL',
    'iny.vial': 'INYECTABLE VIAL',
    'liof.pvo.vial': 'LIOFILIZADO POLVO VIAL',
    'jbe': 'JARABE',
    'd.jbe': 'JARABE',
    # Formas vaginales
    'vaginal':           'VAGINAL',
    'caps.vag':          'CÁPSULAS VAGINALES',
    'cap.vag':           'CÁPSULAS VAGINALES',
    'caps.blandas vag':  'CÁPSULAS BLANDAS VAGINALES',
    'caps.bl.vag':       'CÁPSULAS BLANDAS VAGINALES',
    'comp.vag':          'COMPRIMIDOS VAGINALES',
    'tab.vag':           'TABLETAS VAGINALES',
    'ovulo':             'ÓVULO',
    'ovulos':            'ÓVULOS',
    'ovul':              'ÓVULO',
    'crema vag':         'CREMA VAGINAL',
    'cr.vag':            'CREMA VAGINAL',
    'gel vag':           'GEL VAGINAL',
    'sol.vag':           'SOLUCIÓN VAGINAL',
    # Formas añadidas en fix /ml+forma y nuevas (2026-06)
    'tabl':              'TABLETAS',
    'tabs':              'TABLETAS',
    'lapic.prell':       'LAPICERA PRELLENADA',
    'lapic':             'LAPICERA',
    'lapiceras prell':   'LAPICERAS PRELLENADAS',
    'lapiceras':         'LAPICERAS',
    'lapicera desc':     'LAPICERA DESCARTABLE',
    'lapicera':          'LAPICERA',
    'lap.prell':         'LAPICERA PRELLENADA',
    'autoiny':           'AUTOINYECTOR',
    'autoinyect':        'AUTOINYECTOR',
    'autoinyec':         'AUTOINYECTOR',
    'autoinyect.prell':  'AUTOINYECTOR PRELLENADO',
    'cart':              'CARTUCHO',
    'cart.prell':        'CARTUCHO PRELLENADO',
    'cartucho':          'CARTUCHO',
    'depot':             'DEPÓSITO',
    'vial':              'VIAL',
    'viales':            'VIALES',
    'fco':               'FRASCO',
    'apos':              'APÓSITO',
    'jab.liq':           'JABÓN LÍQUIDO',
    'jab.sol':           'JABÓN SÓLIDO',
    'inhalador hfa':     'INHALADOR HFA',
    'inh':               'INHALADOR',
    'spr.nasal':         'SPRAY NASAL',
    'spr':               'SPRAY',
    'sh':                'SHAMPOO',
    'shampoo':           'SHAMPOO',
    'pda':               'POMADA',
    'emul':              'EMULSIÓN',
    'emulsión':          'EMULSIÓN',
    'monods':            'MONODOSIS',
    'monodosis':         'MONODOSIS',
    'pomos':             'POMOS',
    'blis':              'BLÍSTER',
    'blister':           'BLÍSTER',
    'dispensador':       'DISPENSADOR',
    'dispenser':         'DISPENSADOR',
    'colir':             'COLIRIO',
    'granul.lp sob':     'GRÁNULOS LP SOBRES',
    'granul':            'GRÁNULOS',
    'divids':            'DIVISIBLES',
    'jgas.prell':        'JERINGAS PRELLENADAS',
    'jga.prell':         'JERINGA PRELLENADA',
    'jer.prell':         'JERINGA PRELLENADA',
    'jga.pr':            'JERINGA PRELLENADA',
    'j.prell':           'JERINGA PRELLENADA',
    'iny.prell':         'INYECTABLE PRELLENADO',
    'iny.a.ol':          'INYECTABLE OLEOSO',
    'sol.iny':           'SOLUCIÓN INYECTABLE',
    'parch.matriz':      'PARCHE MATRICIAL',
    'parch.transd':      'PARCHE TRANSDÉRMICO',
    'parches transdérmicos': 'PARCHES TRANSDÉRMICOS',
    'cap.lib.prol':      'CÁPSULAS LIBERACIÓN PROLONGADA',
    'ap.aplic.desc':     'APLICADOR DESCARTABLE',
    # Formas faltantes detectadas en debug (2024-06)
    'champu': 'CHAMPÚ',
    'sachets': 'SOBRES',
    'implante': 'IMPLANTE',
    'pasta': 'PASTA',
    'polvo': 'POLVO',
    'talquera': 'TALQUERA',
    'esp': 'ESPUMA',
    'got': 'GOTAS',
    'got.': 'GOTAS',
    'gotero incoloro': 'FRASCO GOTERO',
    'locion atomizador': 'LOCIÓN ATOMIZADOR',
    'pomada dérm': 'POMADA DÉRMICA',
    'pomada': 'POMADA',
    'colir': 'COLIRIO',
    'tubos': 'TUBOS',
    'viales': 'VIALES',
    'autoinyect.prell': 'AUTOINYECTOR PRELLENADO',
    'implante oft.intravítrea': 'IMPLANTE OFTÁLMICO INTRAVÍTREO',
    'gtas': 'GOTAS',
    'gotas': 'GOTAS',
    'pote': 'POTE',
    'colut': 'COLUTORIO',
    'past': 'PASTILLAS',
    'pastillas': 'PASTILLAS',
    'soluc': 'SOLUCIÓN',
    'parches': 'PARCHES',
    'caramelos': 'CARAMELOS',
    'blister caram': 'BLÍSTER CARAMELOS',
    'caram': 'CARAMELOS',
    'pasta dérm': 'PASTA DÉRMICA',
    'pasta derm': 'PASTA DÉRMICA',
    'unidosis': 'UNIDOSIS',
    'toallitas desc': 'TOALLITAS DESCARTABLES',
    'toallitas': 'TOALLITAS',
    'ap.aplic.desc': 'APLICADOR DESCARTABLE',
    'sistemas': 'SISTEMAS',
    'estuche': 'ESTUCHE',
    'frasco': 'FRASCO',
    'efer.gran.sob': 'GRÁNULOS EFERVESCENTES SOBRES',
    'gran.efer.sob': 'GRÁNULOS EFERVESCENTES SOBRES',
    'anillo vaginal sob': 'ANILLO VAGINAL SOBRES',
    'anillo vaginal': 'ANILLO VAGINAL',
    'crema': 'CREMA',
}

_MODS_PRES = {
    'oft':      {'sol': 'SOLUCIÓN OFTÁLMICA',  'gts': 'GOTAS OFTÁLMICAS',  None: 'OFTÁLMICO'},
    'of':       {'sol': 'SOLUCIÓN OFTÁLMICA',  'gts': 'GOTAS OFTÁLMICAS',  None: 'OFTÁLMICO'},
    'oral':     {'sol': 'SOLUCIÓN ORAL', 'susp': 'SUSPENSIÓN ORAL',        None: 'ORAL'},
    'vag':      {'ov': 'ÓVULOS VAGINALES', 'óv': 'ÓVULOS VAGINALES', 'cr': 'CREMA VAGINAL', None: 'VAGINAL'},
    'nasal':    {'susp': 'SUSPENSIÓN NASAL', 'sol': 'SOLUCIÓN NASAL', 'spray': 'SPRAY NASAL', None: 'SPRAY NASAL'},
    'liof':     {'f.a': 'FRASCO AMPOLLA LIOFILIZADO', None: 'LIOFILIZADO'},
    'f.a':      {'iny': 'INYECTABLE FRASCO AMPOLLA', 'liof': 'LIOFILIZADO FRASCO AMPOLLA', None: 'FRASCO AMPOLLA'},
    'gotero':   {'fco': 'FRASCO GOTERO', None: 'FRASCO GOTERO'},
    'rec':      {'comp': 'COMPRIMIDOS RECUBIERTOS', None: 'RECUBIERTO'},
    'acc.prol': {'comp': 'COMPRIMIDOS ACCIÓN PROLONGADA', None: 'ACCIÓN PROLONGADA'},
    'ap':       {'comp': 'COMPRIMIDOS ACCIÓN PROLONGADA', None: 'ACCIÓN PROLONGADA'},
    'prell':    {'lap': 'LAPICERA PRELLENADA', 'jga': 'JERINGA PRELLENADA', None: 'PRELLENADO'},
    'duras':    {'cáps': 'CÁPSULAS DURAS', 'caps': 'CÁPSULAS DURAS', None: None},
    'ur': {None: None}, 'andas': {None: None}, 'solv': {None: None},
    's': {None: None}, 't': {None: None}, 'r': {None: None}, 'er': {None: None},
}

_RE_PP  = re.compile(r'^(?:ad|ped|rtd|hm|ap)\.?\s+', re.IGNORECASE)
# Prefijos que modifican la forma (se conservan como sufijo de forma)
_RE_PM  = re.compile(r'^(sr|lp|xr|er|mr|flash|niños|naranja|menta|frutal|clásico|clasico|vainilla|frutilla|tutti\s*frutti|limón|limon|forte|plus|duo|max)\s+', re.IGNORECASE)
_MODS_FORMA = {
    'sr': 'SR', 'lp': 'LP', 'xr': 'XR', 'er': 'ER', 'mr': 'MR',
    'flash': 'FLASH', 'niños': 'NIÑOS', 'forte': 'FORTE', 'plus': 'PLUS',
    'duo': 'DUO', 'max': 'MAX',
}
_RE_PD  = re.compile(r'^(\d[\d\.,/]*)\s*')
_RE_PU  = re.compile(r'^(mg|mcg|ug|g\b|ml|ui|iu|meq|mmol|kcal|%)\s*', re.IGNORECASE)
_RE_PPR = re.compile(r'^(?:hfa|cfc|/\d*\.?\d*(?:ml|h|24h))\s*', re.IGNORECASE)
_RE_PC  = re.compile(r'^(\d[\d\.,]*)\s*(mg|mcg|g)\s*/\s*(\d[\d\.,]*)\s*(ml|g)\s*', re.IGNORECASE)
_RE_PCT_MID = re.compile(r'^(.*?)(\d+[\.,]?\d*)\s*%\s+', re.IGNORECASE)   # "gel 0.1% " → dosis=0.1, unidad=%
_RE_CONC_BARE = re.compile(r'^(\d[\d\.,]*)\s*(mg|mcg|g|ui|meq)\s*/\s*(ml|g|dose|dosis|comp|amp)\s*$', re.IGNORECASE)  # "f.a.x 250 mg/ml" tail
_RE_PKV = re.compile(r'x\s*\d[\d\.,]*\s*(ml|g)\b', re.IGNORECASE)
_RE_PCO = re.compile(r'\(\d+\+\d+\)')
_RE_PCA = re.compile(r'x\s*(\d[\d\.,]*)\s*(ds\.?|dosis|ml|g\b|u\.?|unid\.?)?', re.IGNORECASE)
_RE_PAE = re.compile(r'(?:dosis\s+x\s+(\d+)|(\d+)\s+dosis)', re.IGNORECASE)
_formas_pres_re = '|'.join(re.escape(k) for k in sorted(_FORMAS_NORM_PRES.keys(), key=len, reverse=True))
_RE_PF  = re.compile(r'^(' + _formas_pres_re + r')(?=$|[\s\.])[\s\.]?', re.IGNORECASE)
_RE_PFF = re.compile(r'\b(' + _formas_pres_re + r')\.?$', re.IGNORECASE)
_UNI_MAP = {'mg':'MG','mcg':'MCG','ug':'MCG','g':'G','ml':'ML',
            'ui':'UI','iu':'UI','u':'U','meq':'MEQ','mmol':'MMOL','kcal':'KCAL','%':'%'}


def _parsear_presentacion(pres: str) -> dict:
    r = {'forma': None, 'dosis': None, 'unidad': None, 'cantidad': None, 'resto': None}
    s = pres.strip().lower()
    # Capturar modificador de forma antes de strippear prefijos (SR, LP, Flash, Niños, etc.)
    _mod_forma = None
    m_mod = _RE_PM.match(s)
    if m_mod:
        _mod_forma = _MODS_FORMA.get(m_mod.group(1).lower())  # None si es sabor (naranja, menta…)
        s = s[m_mod.end():]
    s = _RE_PP.sub('', s).strip()
    m = _RE_PC.match(s)
    if m:
        r['dosis']  = f"{m.group(1)}{m.group(2)}/{m.group(3)}{m.group(4)}"
        r['unidad'] = 'MG/ML'
        s = s[m.end():]
        # Capturar forma que sigue a la concentración (ej: "0.5 mg/ml a.x 1")
        m2 = _RE_PF.match(s.strip())
        if m2:
            fkr2 = m2.group(1).lower().rstrip('. ')
            r['forma'] = _FORMAS_NORM_PRES.get(fkr2, fkr2.upper())
            s = s[m2.end():]
    else:
        m = _RE_PD.match(s)
        if m: r['dosis'] = m.group(1); s = s[m.end():]
        m = _RE_PU.match(s)
        if m: r['unidad'] = _UNI_MAP.get(m.group(1).lower(), m.group(1).upper()); s = s[m.end():]
    # Patrón "forma N% x cantidad" → ej: "gel 0.1% x 30 g"
    # El % aparece DESPUÉS de la forma: primero buscamos la forma, luego el %
    if not r['dosis']:
        m = re.search(r'(\d+[\.,]?\d*)\s*%(?:\s+|$)', s)
        if m:
            r['dosis'] = m.group(1).replace(',', '.')
            r['unidad'] = '%'
            s = (s[:m.start()] + s[m.end():]).strip()
    # Patrón "mg/ml" al final sin cantidad previa → ej: "f.a.x 50 mg/ml"
    # Solo aplica si la cantidad ya capturada en realidad era la concentración
    if not r['dosis'] and r['cantidad']:
        m = re.search(r'(mg|mcg|g|ui|meq)\s*/\s*(ml|g)\s*$', s, re.IGNORECASE)
        if m:
            # la cantidad capturada es la dosis, la unidad es mg/ml
            r['dosis']    = r['cantidad']
            r['unidad']   = _UNI_MAP.get(m.group(1).lower(), m.group(1).upper()) + '/' + m.group(2).upper()
            r['cantidad'] = None
    # Caso "x 250 mg/ml" → cantidad fue capturada pero resto contiene la unidad
    if not r['dosis'] and r['cantidad'] and r.get('resto'):
        m = re.match(r'^(mg|mcg|g|ui|meq)\s*/\s*(ml|g)\s*$', (r['resto'] or ''), re.IGNORECASE)
        if m:
            r['dosis']    = r['cantidad']
            r['unidad']   = _UNI_MAP.get(m.group(1).lower(), m.group(1).upper()) + '/' + m.group(2).upper()
            r['cantidad'] = None
            r['resto']    = None
    s = _RE_PPR.sub('', s).strip()
    fkr = None
    m = _RE_PF.match(s.strip())
    if m:
        fkr = m.group(1).lower().rstrip('. ')
        r['forma'] = _FORMAS_NORM_PRES.get(fkr, fkr.upper())
        s = s[m.end():]
    if not r['forma']:
        m = _RE_PFF.search(s.strip())
        if m:
            fk = m.group(1).lower().rstrip('. ')
            r['forma'] = _FORMAS_NORM_PRES.get(fk, fk.upper())
            s = s[:m.start()].strip()
    # Fallback: si hay una palabra descriptiva antes de la forma (ej: "aspirina prev.comp.x 60",
    # "clásico comp.mast.x 6", "mentol gts.x 120 ml") buscar forma en cualquier posición.
    if not r['forma']:
        m = re.search(r'\b(' + _formas_pres_re + r')(?=$|[\s.x])', s, re.IGNORECASE)
        if m:
            fk = m.group(1).lower().rstrip('. ')
            r['forma'] = _FORMAS_NORM_PRES.get(fk, fk.upper())
            # Descartar la parte previa a la forma (es texto descriptivo, no dato útil)
            s = s[m.end():]
    s_sk = _RE_PKV.sub('', s)
    m = _RE_PCA.search(s_sk)
    if m:
        cant = m.group(1); uc = (m.group(2) or '').strip().rstrip('.')
        if uc == 'dosis': uc = 'ds.'
        r['cantidad'] = (cant + (' ' + uc if uc else '')).strip()
        s = (s_sk[:m.start()] + s_sk[m.end():]).strip(' .,+')
    else:
        s = s_sk
        m = _RE_PAE.search(s)
        if m:
            n = m.group(1) or m.group(2)
            r['cantidad'] = n + ' ds.'
            s = (s[:m.start()] + s[m.end():]).strip(' .,+')
    s = _RE_PCO.sub('', s).strip(' .,+')
    if s and fkr:
        mod = s.strip(' .')
        if mod in _MODS_PRES:
            mapa = _MODS_PRES[mod]
            fr = mapa.get(fkr) or mapa.get(None)
            if fr: r['forma'] = fr; s = ''
            elif mapa.get(None) is None: s = ''
    s = s.strip(' .,+-')
    if not r['forma'] and not s and r['cantidad']:
        if r['unidad'] == 'ML': r['forma'] = 'LÍQUIDO'
        elif r['unidad'] == 'G': r['forma'] = 'TÓPICO'
    # Appendear modificador a la forma si corresponde (SR, LP, Flash, Niños…)
    if _mod_forma and r['forma']:
        r['forma'] = f"{r['forma']} {_mod_forma}"
    if s: r['resto'] = s
    # Si el string original contiene 'vial' explícito pero la forma capturada es
    # un modificador (liof, pvo, IV, fco, sol), forzar forma = VIAL
    _FORMAS_VIAL_OVERRIDE = {
        'LIOFILIZADO', 'POLVO LIOFILIZADO', 'POLVO', 'FRASCO',
        'INYECTABLE INTRAVENOSO', 'SOLUCIÓN',
    }
    if (r['forma'] in _FORMAS_VIAL_OVERRIDE and
            re.search(r'\bvial\b', pres.lower())):
        r['forma'] = 'VIAL'
    # Caso "f.a.x 250 mg/ml" → cantidad capturada pero resto es "mg/ml" (la unidad)
    if not r['dosis'] and r['cantidad'] and r.get('resto'):
        m = re.match(r'^(mg|mcg|g|ui|meq)\s*/\s*(ml|g)\s*$', r['resto'], re.IGNORECASE)
        if m:
            r['dosis']    = r['cantidad']
            r['unidad']   = _UNI_MAP.get(m.group(1).lower(), m.group(1).upper()) + '/' + m.group(2).upper()
            r['cantidad'] = None
            r['resto']    = None
    return r


def generar_debug_presentaciones(medicamentos: list) -> None:
    import csv as _csv
    PRES_DEBUG_PATH.parent.mkdir(parents=True, exist_ok=True)
    debug_generado = datetime.now(AR_TZ).strftime("%Y-%m-%d %H:%M:%S")
    campos = ['debug_generado', 'droga', 'marca', 'presentacion_original', 'forma', 'dosis', 'unidad', 'cantidad', 'resto']
    sin_forma = con_resto = total = 0
    with open(PRES_DEBUG_PATH, 'w', newline='', encoding='utf-8') as f:
        writer = _csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        for m in medicamentos:
            pres = (m.get('presentacion') or '').strip()
            if not pres: continue
            r = _parsear_presentacion(pres)
            if not r['forma']:   sin_forma += 1
            if r['resto']:       con_resto += 1
            total += 1
            writer.writerow({
                'debug_generado': debug_generado,
                'droga': m.get('droga', ''), 'marca': m.get('marca', ''),
                'presentacion_original': pres,
                'forma': r['forma'] or '', 'dosis': r['dosis'] or '',
                'unidad': r['unidad'] or '', 'cantidad': r['cantidad'] or '',
                'resto': r['resto'] or '',
            })
    limpios = total - sin_forma - con_resto
    print(f"   Total: {total} | Limpio: {limpios} ({100*limpios/max(total,1):.1f}%) | "
          f"Sin forma: {sin_forma} | Con resto: {con_resto}")
    print(f"   Debug: {PRES_DEBUG_PATH}")


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

            # ── CAPA 1: detección de desplazamiento en tiempo de parse ──
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

    # ── CAPA 5c: limpiar dosis residual pegada a laboratorio en marca ────
    # Cubre el caso donde la Capa 5b ya separó la forma hacia
    # 'presentacion' pero dejó la dosis numérica pegada al laboratorio
    # dentro de 'marca' (ej. "CIPROFLOXACINA SANT GALL500 MG").
    print("\nLimpiando dosis residual en marca...")
    medicamentos, n_dosis_residual = limpiar_dosis_residual_en_marca(medicamentos)
    print(f"   Reparados: {n_dosis_residual}")

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

    print("\nGenerando debug de presentaciones...")
    generar_debug_presentaciones(medicamentos)

    # ── Promover campos parseados de presentación a cada registro ────────
    print("\nEnriqueciendo registros con campos de presentación...")
    _RE_DOSIS_MARCA = re.compile(
        r'(\d+[\.,]?\d*)\s*/\s*(\d+[\.,]?\d*)\s*(mg|mcg|g|ui|%)|'  # "750/15 mg"
        r'(\d+[\.,]?\d*)\s*(mg|mcg|µg|g\b|ui|iu|%|meq)',             # "1000 MG" / "1.5%"
        re.IGNORECASE
    )
    # Número al final del nombre sin unidad: ATORMAX 10, LISOVYR 400, BIOCLAVID 875/125
    # Excluye B12, B6, etc. y requiere ≥2 dígitos si no hay unidad
    _RE_DOSIS_NOMBRE = re.compile(
        r'(?<![A-Za-z\d])(\d+[\.,]?\d*)\s*/\s*(\d+[\.,]?\d*)\s*(?:U\.I\.?|UI|MG|MCG|%)?\s*$|'
        r'(?<![A-Za-z])(\d+[\.,]?\d*)\s*(U\.I\.?|UI|MG|MCG|%)\s*$|'
        r'(?<![A-Za-z\d/])(\d{2,})\s*$',
        re.IGNORECASE
    )
    # Categorías donde la dosis no aplica estructuralmente
    _RE_DROGA_SIN_DOSIS = re.compile(
        r'\bvacun|antigen|antigripal|vitamina[^s]|multivitamin|'
        r'anticonceptiv|levonorgestrel|etinil|dienogest|drospirenon|noretisterona|'
        r'acido folic\b|folico\b|herbal|fitoterapia|preparacion herbaria|'
        r'hepatalgina|suero oral|solucion de rehidratacion|'
        r'agua oxigenada|alcohol etilico\b|cloruro de sodio.*0\.9',
        re.IGNORECASE
    )
    _FORMAS_SIN_DOSIS = {
        'CREMA', 'GEL', 'POMADA', 'SHAMPOO', 'LOCIÓN', 'COLIRIO',
        'SOLUCIÓN OFTÁLMICA', 'JABÓN LÍQUIDO', 'PASTA DÉRMICA',
        'ESPUMA', 'TOALLITAS', 'TALQUERA', 'LACA', 'EMULSIÓN',
        'LOCIÓN ATOMIZADOR', 'POTE',
    }
    n_enriquecidos = 0
    n_dosis_marca  = 0
    for m in medicamentos:
        pres = (m.get('presentacion') or '').strip()
        if not pres:
            continue
        r = _parsear_presentacion(pres)
        if r['forma'] or r['dosis']:
            if r['forma']:    m['pres_forma']    = r['forma']
            if r['dosis']:    m['pres_dosis']    = r['dosis']
            if r['unidad']:   m['pres_unidad']   = r['unidad']
            if r['cantidad']: m['pres_cantidad'] = r['cantidad']
            n_enriquecidos += 1
        # Fallback: buscar dosis en el nombre de marca si presentacion no la tiene
        if not m.get('pres_dosis'):
            marca = (m.get('marca') or '').strip()
            hm = _RE_DOSIS_MARCA.search(marca)
            if hm:
                if hm.group(1) and hm.group(2):  # patrón barra: 750/15 mg
                    m['pres_dosis']  = f"{hm.group(1)}/{hm.group(2)}"
                    m['pres_unidad'] = hm.group(3).upper()
                elif hm.group(4):                 # patrón simple: 1000 MG
                    m['pres_dosis']  = hm.group(4).replace(',', '.')
                    m['pres_unidad'] = hm.group(5).upper()
                m['pres_dosis_fuente'] = 'marca'
                n_dosis_marca += 1
        # Fallback: dosis al final del nombre de marca (ATORMAX 10, BIOCLAVID 875/125)
        if not m.get('pres_dosis'):
            marca = (m.get('marca') or '').strip()
            hn = _RE_DOSIS_NOMBRE.search(marca)
            if hn:
                if hn.group(1) and hn.group(2):   # barra: 875/125
                    m['pres_dosis']  = f"{hn.group(1)}/{hn.group(2)}"
                    m['pres_unidad'] = 'MG'
                elif hn.group(3):                  # con unidad: 1000 U.I.
                    m['pres_dosis']  = hn.group(3).replace(',', '.')
                    m['pres_unidad'] = re.sub(r'\.', '', hn.group(4)).upper()
                else:                              # solo número: ATORMAX 10
                    m['pres_dosis']  = hn.group(5)
                    m['pres_unidad'] = 'MG'
                m['pres_dosis_fuente'] = 'nombre'
                n_dosis_marca += 1
        # Marcar categorías donde la dosis no aplica estructuralmente
        if not m.get('pres_dosis'):
            droga = (m.get('droga') or '').strip()
            forma = m.get('pres_forma') or ''
            if _RE_DROGA_SIN_DOSIS.search(droga) or forma in _FORMAS_SIN_DOSIS:
                m['pres_dosis_fuente'] = 'no_aplica'
    print(f"   Enriquecidos: {n_enriquecidos}/{len(medicamentos)} ({100*n_enriquecidos/max(len(medicamentos),1):.1f}%)")
    print(f"   Dosis rescatadas de marca: {n_dosis_marca}")

    # ── Fallback dosis desde PAMI (marca+forma+cantidad compatibles) ──────
    _RE_DOSIS_CONC_PAMI = re.compile(r'(\d+[\.,]?\d*)\s*(mg|mcg|µg|ui|iu|%|meq)\b', re.IGNORECASE)
    _RE_FORMA_PAMI      = re.compile(r'(comp|caps|susp|sol|jbe|gts|cr|gel|ung|pomo|sob|a\b|f\.a|vial|amp)', re.IGNORECASE)
    _RE_CANT_PAMI       = re.compile(r'x\s*(\d+)', re.IGNORECASE)

    pami_dosis_idx: dict = {}
    if PAMI_PATH.exists():
        import pandas as _pd
        pami_df = _pd.read_excel(PAMI_PATH)
        pami_df.columns = [c.strip() for c in pami_df.columns]
        for _, row in pami_df.iterrows():
            marca_p = str(row['MARCA']).strip().upper()
            pres_p  = str(row['PRESENTACION']).strip().lower()
            hit     = _RE_DOSIS_CONC_PAMI.search(pres_p)
            if hit:
                pami_dosis_idx.setdefault(marca_p, []).append((pres_p, hit))

    def _forma_compat(ps, pp):
        f1 = _RE_FORMA_PAMI.search(ps.lower())
        f2 = _RE_FORMA_PAMI.search(pp.lower())
        return bool(f1 and f2 and f1.group(1).lower()[:3] == f2.group(1).lower()[:3])

    def _cant_compat(ps, pp):
        c1 = _RE_CANT_PAMI.search(ps); c2 = _RE_CANT_PAMI.search(pp)
        return (c1.group(1) == c2.group(1)) if (c1 and c2) else True

    n_dosis_pami = 0
    for m in medicamentos:
        if m.get('pres_dosis'):
            continue
        marca_up    = (m.get('marca') or '').strip().upper()
        pres_siafar = (m.get('presentacion') or '').strip().lower()
        for pres_p, hit in pami_dosis_idx.get(marca_up, []):
            if _forma_compat(pres_siafar, pres_p) and _cant_compat(pres_siafar, pres_p):
                m['pres_dosis']        = hit.group(1).replace(',', '.')
                m['pres_unidad']       = hit.group(2).upper()
                m['pres_dosis_fuente'] = 'pami'
                n_dosis_pami += 1
                break
    print(f"   Dosis rescatadas de PAMI: {n_dosis_pami}")

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
    PRETTY_PATH = BASE / ".debug" / "medicamentos.pretty.json"
    PRETTY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PRETTY_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\nGuardado: {MEDICAMENTOS_PATH}")
    print(f"Total: {len(medicamentos)} | Excluidos (blacklist): {n_bl} | Fecha: {fecha_str}")
if __name__ == "__main__":
    main()
