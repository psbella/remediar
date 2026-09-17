"""etl/pami.py - Crosswalk contra el vademecum PAMI para recuperar droga y laboratorio."""

from .config import PAMI_PATH
from .presentacion import _parsear_presentacion


def _build_pami_index():
    """Carga el vademécum PAMI (archivo versionado en el repo) y construye
    índices por marca+pres, por marca y por marca+dosis+unidad+cantidad.

    El vademécum de PAMI se actualiza ~1 vez por mes, así que en vez de
    descargarlo en cada corrida del ETL, se sube manualmente a data/pami.xlsx
    cuando cambia (ver README para el link de descarga). Esto evita depender
    de la disponibilidad de datos.pami.org.ar en cada ejecución de CI.
    """
    if not PAMI_PATH.exists():
        print(f"   PAMI: no se encontró {PAMI_PATH.name} en data/, se omite el crosswalk.")
        return None, None, None

    try:
        import openpyxl  # noqa: F401
        df = __import__('pandas').read_excel(PAMI_PATH)
    except Exception as e:
        print(f"   PAMI: error al cargar ({e})")
        return None, None, None

    df.columns = [c.strip() for c in df.columns]
    def _norm(s):
        import re as _re
        import unicodedata as _ud
        s_sin_acentos = _ud.normalize('NFKD', str(s or '')).encode('ascii', 'ignore').decode('utf-8')
        return _re.sub(r'\s+', ' ', s_sin_acentos.strip().upper())
        return _re.sub(r'\s+', ' ', str(s or '').strip().upper())

    by_marca_pres  = {}
    by_marca       = {}
    by_marca_dosis = {}

    # to_dict('records') convierte el DataFrame completo a una lista de
    # dicts en una sola operación vectorizada, en vez de reconstruir una
    # Series por fila como hace iterrows(). Los dicts resultantes soportan
    # el mismo acceso .get()/['clave'] que usa crosswalk_pami() más abajo,
    # así que no hace falta tocar el código que consume estos índices.
    for row in df.to_dict('records'):
        mk   = _norm(row.get('MARCA', ''))
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
        if p['dosis'] and p['cantidad']:
            key_dosis = (mk, p['dosis'], p['unidad'], p['cantidad'])
            if key_dosis not in by_marca_dosis:
                by_marca_dosis[key_dosis] = row
    import unicodedata as _ud

    def _norm(s):
        s_sin_acentos = _ud.normalize('NFKD', str(s or '')).encode('ascii', 'ignore').decode('utf-8')
        return _re.sub(r'\s+', ' ', s_sin_acentos.strip().upper())
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

    stats = {
        'match_exacto': 0, 'match_dosis_cantidad': 0, 'droga_recuperada': 0,
        'lab_corregido': 0, 'pami_cobertura': 0, 'pami_cobertura_invalida': 0,
    }

    by_marca_pres, by_marca, by_marca_dosis = _build_pami_index()
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

cat > scripts/etl/pami.py << 'EOF'
"""etl/pami.py - Crosswalk contra el vademecum PAMI para recuperar droga y laboratorio."""

from .config import PAMI_PATH
from .presentacion import _parsear_presentacion


def _build_pami_index():
    """Carga el vademécum PAMI (archivo versionado en el repo) y construye
    índices por marca+pres, por marca y por marca+dosis+unidad+cantidad.

    El vademécum de PAMI se actualiza ~1 vez por mes, así que en vez de
    descargarlo en cada corrida del ETL, se sube manualmente a data/pami.xlsx
    cuando cambia (ver README para el link de descarga). Esto evita depender
    de la disponibilidad de datos.pami.org.ar en cada ejecución de CI.
    """
    if not PAMI_PATH.exists():
        print(f"   PAMI: no se encontró {PAMI_PATH.name} en data/, se omite el crosswalk.")
        return None, None, None

    try:
        import openpyxl  # noqa: F401
        df = __import__('pandas').read_excel(PAMI_PATH)
    except Exception as e:
        print(f"   PAMI: error al cargar ({e})")
        return None, None, None

    df.columns = [c.strip() for c in df.columns]

    def _norm(s):
        import re as _re
        return _re.sub(r'\s+', ' ', str(s or '').strip().upper())

    by_marca_pres  = {}
    by_marca       = {}
    by_marca_dosis = {}

    # to_dict('records') convierte el DataFrame completo a una lista de
    # dicts en una sola operación vectorizada, en vez de reconstruir una
    # Series por fila como hace iterrows(). Los dicts resultantes soportan
    # el mismo acceso .get()/['clave'] que usa crosswalk_pami() más abajo,
    # así que no hace falta tocar el código que consume estos índices.
    for row in df.to_dict('records'):
        mk   = _norm(row.get('MARCA', ''))
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
        if p['dosis'] and p['cantidad']:
            key_dosis = (mk, p['dosis'], p['unidad'], p['cantidad'])
            if key_dosis not in by_marca_dosis:
                by_marca_dosis[key_dosis] = row

    return by_marca_pres, by_marca, by_marca_dosis

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

    stats = {
        'match_exacto': 0, 'match_dosis_cantidad': 0, 'droga_recuperada': 0,
        'lab_corregido': 0, 'pami_cobertura': 0, 'pami_cobertura_invalida': 0,
    }

    by_marca_pres, by_marca, by_marca_dosis = _build_pami_index()
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
        key_dosis = (mk, p['dosis'], p['unidad'], p['cantidad']) if p and p['dosis'] and p['cantidad'] else None
        if key_dosis and key_dosis in by_marca_dosis:
            stats['match_dosis_cantidad'] += 1
            _aplicar_row(m, by_marca_dosis[key_dosis], stats)
            continue

        # Estrategia 2: solo marca (presentacion vacía, droga vacía)
        if not pres and not m.get('droga', '').strip() and mk in by_marca:
            rows  = by_marca[mk]
            drogas = {str(r.get('DROGA', '')).strip().lower() for r in rows if str(r.get('DROGA', '')).strip()}
            if len(drogas) == 1:
                m['droga'] = drogas.pop()
                stats['droga_recuperada'] += 1

    return medicamentos, stats
