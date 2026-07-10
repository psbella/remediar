"""etl/pami.py - Crosswalk contra el vademecum PAMI para recuperar droga y laboratorio."""

import json
import time
import urllib.request
import urllib.error

from .config import PAMI_PATH, PAMI_API_URL, ssl_context


def _descargar_pami(max_reintentos=3, backoff_segundos=30) -> bool:
    """Descarga el vademécum PAMI vigente a PAMI_PATH. Devuelve True si tuvo éxito."""
    for intento in range(1, max_reintentos + 1):
        try:
            req = urllib.request.Request(PAMI_API_URL, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30, context=ssl_context) as r:
                meta = json.loads(r.read())
            download_url = meta["result"]["url"]

            req = urllib.request.Request(download_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60, context=ssl_context) as r:
                xlsx_bytes = r.read()

            PAMI_PATH.parent.mkdir(parents=True, exist_ok=True)
            PAMI_PATH.write_bytes(xlsx_bytes)
            print(f"   PAMI: descargado ({len(xlsx_bytes)} bytes) desde {download_url.split('/')[-1]}")
            return True
        except (urllib.error.URLError, TimeoutError, ConnectionError, KeyError, ValueError) as e:
            print(f"   PAMI: intento {intento}/{max_reintentos} fallido ({e})")
            if intento < max_reintentos:
                time.sleep(backoff_segundos)
    print("   PAMI: no se pudo descargar el vademécum tras todos los reintentos — se omite el crosswalk.")
    return False

def _build_pami_index():
    """Carga el vademécum PAMI y construye índices por marca+pres y por marca."""
    # Siempre se intenta la descarga fresca — no alcanza con chequear si
    # PAMI_PATH ya existe, porque en GitHub Actions el checkout trae el
    # archivo del último commit en el que se haya versionado (p.ej. antes
    # de migrar a descarga dinámica), y ese archivo nunca se actualizaría.
    habia_archivo_previo = PAMI_PATH.exists()
    if not _descargar_pami():
        if habia_archivo_previo:
            print("   PAMI: se usa el archivo existente en disco como fallback (puede estar desactualizado).")
        else:
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

    # to_dict('records') convierte el DataFrame completo a una lista de
    # dicts en una sola operación vectorizada, en vez de reconstruir una
    # Series por fila como hace iterrows(). Los dicts resultantes soportan
    # el mismo acceso .get()/['clave'] que usa crosswalk_pami() más abajo,
    # así que no hace falta tocar el código que consume estos índices.
    for row in df.to_dict('records'):
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

    stats = {'match_exacto': 0, 'droga_recuperada': 0, 'lab_corregido': 0, 'pami_cobertura': 0, 'pami_cobertura_invalida': 0}

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
                    cobertura = int(cobertura_raw.strip().rstrip('%'))
                    if 0 <= cobertura <= 100:
                        m['pami_cobertura'] = cobertura
                        stats['pami_cobertura'] += 1
                    else:
                        stats['pami_cobertura_invalida'] += 1
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
