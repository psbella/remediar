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

def _parece_corrupta(texto):
    """Heuristica simple para detectar mojibake tipico de un encoding mal
    interpretado. No repara nada -- solo avisa para revision manual.
    """
    return 'Ã' in texto or 'â€' in texto or any(0x80 <= ord(c) <= 0x9f for c in texto)


def cargar_blacklist():
    if BLACKLIST_PATH.exists():
        with open(BLACKLIST_PATH, encoding='utf-8') as f:
            bl = json.load(f)
        corruptas = [k for k in bl if _parece_corrupta(k)]
        if corruptas:
            print(f"   Lista negra: AVISO -- {len(corruptas)} clave(s) con encoding corrupto (no excluyen nada, revisar a mano):")
            for k in corruptas:
                print(f"      {k!r}")
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
