"""etl/reparaciones.py - Capas de reparacion de campos mal parseados desde el PDF."""

import re


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
