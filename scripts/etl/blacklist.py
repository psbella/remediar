"""etl/blacklist.py - Carga y filtrado de la lista negra de medicamentos."""

import json

from .config import BLACKLIST_PATH


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
