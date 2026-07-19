"""etl/droga_fixes.py - Correcciones manuales y reparacion de droga faltante."""

import re
import json

from .config import DROGA_FIXES_PATH


# ─────────────────────────────────────────────────────────────────────────────
# FIXES MANUALES DE DROGA
# ─────────────────────────────────────────────────────────────────────────────

# Diccionario curado manualmente: marca (upper) → droga (principio activo).
# Cubre marcas sin nombre genérico en el PDF de SIAFAR que no pueden
# resolverse automáticamente (nombres comerciales de laboratorios que no
# imprimen el principio activo en el PDF).
# Archivo: data/droga_fixes.json

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

