#!/usr/bin/env python3
"""Saca la navegacion interna de about.html (nav.about-nav) y el CSS que queda sin uso.

Correr desde la raiz del repo:   py aplicar_sacar_nav_about.py
- Cada reemplazo exige exactamente 1 coincidencia; si algo no calza, aborta
  sin haber escrito ningun archivo.
- Respeta el fin de linea de cada archivo (LF o CRLF).
- No es idempotente a proposito: si se corre dos veces, la segunda aborta.
"""
import sys
from pathlib import Path

RAIZ = Path.cwd()
cambios = {}


def tomar(ruta):
    p = RAIZ / ruta
    if p in cambios:
        return p, cambios[p][0], cambios[p][1]
    if not p.exists():
        sys.exit(f"ERROR: no existe {ruta} (correr desde la raiz del repo)")
    crudo = p.read_bytes().decode("utf-8")
    return p, crudo.replace("\r\n", "\n"), "\r\n" in crudo


def reemplazar(ruta, viejo, nuevo, descripcion):
    p, texto, crlf = tomar(ruta)
    n = texto.count(viejo)
    if n != 1:
        sys.exit(f"ERROR en {ruta}: '{descripcion}' tiene {n} coincidencias (se esperaba 1)")
    cambios[p] = (texto.replace(viejo, nuevo), crlf)


reemplazar("about.html", '''    <!-- Navegación interna -->
    <nav class="about-nav">
        <a href="#que-es">Qué es</a>
        <a href="#como-funciona">Cómo funciona</a>
        <a href="#lo-diferente">Lo diferente</a>
        <a href="#lo-que-no-hace">Lo que NO hace</a>
        <a href="#numeros">Números</a>
        <a href="#faq">Preguntas frecuentes</a>
        <a href="#quien-sostiene">Quién lo sostiene</a>
    </nav>

''', "", "bloque nav.about-nav")

CSS = "css/style.css"
reemplazar(CSS, '''.about-nav {
    background: var(--white);
    border: 0.5px solid var(--border);
    border-radius: var(--r-md);
    padding: 12px 16px;
    margin-bottom: 24px;
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    position: sticky;
    top: 12px;
    z-index: 100;
}

.about-nav a {
    font-size: 12px;
    font-weight: 500;
    color: var(--teal);
    text-decoration: none;
    padding: 6px 12px;
    border-radius: var(--r-sm);
    transition: background 0.2s;
    white-space: nowrap;
}

.about-nav a:hover {
    background: var(--teal-light);
    color: var(--teal-darker);
}

''', "", "reglas .about-nav")
reemplazar(CSS, '''    .about-nav {
        position: relative;
        top: 0;
        gap: 8px;
    }

''', "", "regla movil de .about-nav")

reemplazar("sw.js", "const CACHE_NAME   = 'remediar-v35';", "const CACHE_NAME   = 'remediar-v36';", "CACHE_NAME")

reemplazar("CHANGELOG.md",
    "  precache. `sw.js`: `CACHE_NAME` sube a `v35`.\n",
    "  precache. `sw.js`: `CACHE_NAME` sube a `v35`.\n"
    "- `about.html`: se elimina la navegación interna (la barra con 7 links a las\n"
    "  secciones) y su CSS (`.about-nav`). Los `id` de las secciones se conservan,\n"
    "  así que los links con ancla (`about.html#faq`, etc.) siguen funcionando.\n"
    "  `sw.js`: `CACHE_NAME` sube a `v36`.\n",
    "entrada de CHANGELOG")

for p, (texto, crlf) in cambios.items():
    p.write_bytes((texto.replace("\n", "\r\n") if crlf else texto).encode("utf-8"))
    print("OK", p.relative_to(RAIZ))
print(f"\n{len(cambios)} archivos modificados.")
