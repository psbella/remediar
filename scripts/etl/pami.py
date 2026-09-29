"""etl/pami.py - Crosswalk contra el vademecum PAMI para recuperar droga y laboratorio."""

import re as _re

from .config import PAMI_PATH
from .presentacion import _parsear_presentacion

# Marcas de PAMI que repiten la dosis como sufijo del propio nombre
# (ej. "GLIOTEN 10", "TRANQUINAL 0.5"), a diferencia de SIAFAR que deja
# la marca limpia ("GLIOTEN") y la dosis solo en la presentación.
_SUFIJO_DOSIS_RE = _re.compile(r'^(?P<base>.+?)\s+(?P<num>\d+(?:[.,]\d+)?)$')


def _build_pami_index():
    """Carga el vademécum PAMI (archivo versionado en el repo) y construye
    índices por marca+pres, por marca, por marca+dosis+unidad+cantidad y
    por marca-base (sin sufijo de dosis)+dosis+unidad+cantidad.

    El vademécum de PAMI se actualiza ~1 vez por mes, así que en vez de
    descargarlo en cada corrida del ETL, se sube manualmente a data/pami.xlsx
    cuando cambia (ver README para el link de descarga). Esto evita depender
    de la disponibilidad de datos.pami.org.ar en cada ejecución de CI.
    """
    if not PAMI_PATH.exists():
        print(f"   PAMI: no se encontró {PAMI_PATH.name} en data/, se omite el crosswalk.")
        return None, None, None, None

    try:
        import openpyxl  # noqa: F401
        df = __import__('pandas').read_excel(PAMI_PATH)
    except Exception as e:
        print(f"   PAMI: error al cargar ({e})")
        return None, None, None, None

    df.columns = [c.strip() for c in df.columns]

    def _norm(s):
        return _re.sub(r'\s+', ' ', str(s or '').strip().upper())

    by_marca_pres      = {}
    by_marca           = {}
    by_marca_dosis     = {}
    by_marca_base_dosis = {}

    # to_dict('records') convierte el DataFrame completo a una lista de
    # dicts en una sola operación vectorizada, en vez de reconstruir una
    # Series por fila como hace iterrows(). Los dicts resultantes soportan
    # el mismo acceso .get()/['clave'] que usa crosswalk_pami() más abajo,
    # así que no hace falta tocar el código que consume estos índices.
    for row in df.to_dict('records'):
        marca_raw = str(row.get('MARCA', '') or '').strip()
        mk   = _norm(marca_raw)
        pres_raw = str(row.get('PRESENTACION', '') or '')
        pres = _norm(pres_raw)
        key  = (mk, pres)
        if key not in by_marca_pres:
            by_marca_pres[key] = row
        by_marca.setdefault(mk, []).append(row)

        # Índice por dosis/unidad/cantidad estructurada: recupera casos donde
        # PAMI y SIAFAR describen la misma presentación con abreviaturas o
        # tildes distintas (ej. "tab.efer." vs "tab.eferv.", "caps" vs "cáps")
        # y el match de string exacto de arriba no captura por eso.
        p = _parsear_presentacion(pres_raw)
        dosis, unidad, cantidad = p['dosis'], p['unidad'], p['cantidad']
        if dosis and cantidad:
            key_dosis = (mk, dosis, unidad, cantidad)
            if key_dosis not in by_marca_dosis:
                by_marca_dosis[key_dosis] = row

            # Índice por marca-base: solo se arma cuando el sufijo numérico
            # de la marca coincide con la dosis parseada de esta misma fila,
            # para no pelar un número que en realidad sea parte del nombre
            # comercial y no una dosis (ej. "3M", una línea de producto, etc.).
            m_sufijo = _SUFIJO_DOSIS_RE.match(marca_raw)
            if m_sufijo:
                num_sufijo = m_sufijo.group('num').replace(',', '.')
                try:
                    coincide = float(str(dosis).replace(',', '.')) == float(num_sufijo)
                except ValueError:
                    coincide = False
                if coincide:
                    mk_base = _norm(m_sufijo.group('base'))
                    key_base = (mk_base, dosis, unidad, cantidad)
                    if key_base not in by_marca_base_dosis:
                        by_marca_base_dosis[key_base] = row

    return by_marca_pres, by_marca, by_marca_dosis, by_marca_base_dosis

def crosswalk_pami(medicamentos: list) -> tuple:
    """
    Enriquece registros de SIAFAR usando el vademécum de PAMI.

    - Recupera droga (principio activo) cuando está vacía.
    - Corrige laboratorio cuando es 'Desconocido' y PAMI lo tiene.

    Retorna el dataset enriquecido y un dict de estadísticas.
    """
    def _norm(s):
        return _re.sub(r'\s+', ' ', str(s or '').strip().upper())

    stats = {
        'match_exacto': 0, 'match_dosis_cantidad': 0, 'match_dosis_marca_base': 0,
        'droga_recuperada': 0, 'lab_corregido': 0, 'pami_cobertura': 0,
        'pami_cobertura_invalida': 0,
    }

    by_marca_pres, by_marca, by_marca_dosis, by_marca_base_dosis = _build_pami_index()
    if by_marca_pres is None:
        print("   PAMI: archivo no encontrado, se omite crosswalk")
        return medicamentos, stats

    def _aplicar_row(m, row, stats):
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
                cobertura = int(cobertura_raw.strip().rstrip('%'))
                if 0 <= cobertura <= 100:
                    m['pami_cobertura'] = cobertura
                    stats['pami_cobertura'] += 1
                else:
                    stats['pami_cobertura_invalida'] += 1
            except ValueError:
                pass

    for m in medicamentos:
        mk   = _norm(m.get('marca', ''))
        pres_raw = m.get('presentacion', '') or ''
        pres = _norm(pres_raw)

        # Estrategia 1: match exacto marca+presentacion
        if pres and (mk, pres) in by_marca_pres:
            stats['match_exacto'] += 1
            _aplicar_row(m, by_marca_pres[(mk, pres)], stats)
            continue

        # Estrategia 1b: match por marca+dosis+unidad+cantidad estructurada.
        # Recupera presentaciones equivalentes que el string exacto no
        # matchea por diferencias de abreviatura ("efer" vs "eferv", "disp"
        # vs "dispers") o tildes ("caps" vs "cáps") entre SIAFAR y PAMI.
        p = _parsear_presentacion(pres_raw) if pres_raw else None
        dosis, unidad, cantidad = (p['dosis'], p['unidad'], p['cantidad']) if p else (None, None, None)
        key_dosis = (mk, dosis, unidad, cantidad) if dosis and cantidad else None
        if key_dosis and key_dosis in by_marca_dosis:
            stats['match_dosis_cantidad'] += 1
            _aplicar_row(m, by_marca_dosis[key_dosis], stats)
            continue

        # Estrategia 1c: PAMI a veces repite la dosis como sufijo del nombre
        # de marca (ej. "GLIOTEN 10" en vez de "GLIOTEN"), mientras SIAFAR
        # deja la marca limpia. by_marca_base_dosis ya viene filtrado en
        # _build_pami_index() para solo incluir sufijos que coinciden con
        # la dosis real de esa fila, así que el match acá es sobre la marca
        # de SIAFAR (que nunca lleva ese sufijo) + dosis + cantidad.
        if dosis and cantidad:
            key_base = (mk, dosis, unidad, cantidad)
            if key_base in by_marca_base_dosis:
                stats['match_dosis_marca_base'] += 1
                _aplicar_row(m, by_marca_base_dosis[key_base], stats)
                continue

        # Estrategia 2: solo marca (presentacion vacía, droga vacía)
        if not pres and not m.get('droga', '').strip() and mk in by_marca:
            rows  = by_marca[mk]
            drogas = {str(r.get('DROGA', '')).strip().lower() for r in rows if str(r.get('DROGA', '')).strip()}
            if len(drogas) == 1:
                m['droga'] = drogas.pop()
                stats['droga_recuperada'] += 1

    return medicamentos, stats
