#!/usr/bin/env python3
"""about, privacidad y terminos: header igual al de la home/landings + boton "volver arriba".

Correr desde la raiz del repo:   py aplicar_header_arriba.py
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


HEADER = '''    <a href="index.html" class="header-link">
        <header class="header">
            <div class="header-logo-circle">
                <img src="img/favicon.svg" alt="remedi.ar" width="38" height="38">
            </div>
            <div class="header-texto">
                <h1>remedi.ar - Precios de medicamentos</h1>
            </div>
        </header>
    </a>
'''
BOTON = '''<button id="btnTop" aria-label="Volver arriba">
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5">
        <polyline points="18 15 12 9 6 15"/>
    </svg>
</button>
'''
SCRIPT = '<script src="js/landing.js" defer></script>\n'

# ---- privacidad.html y terminos.html
LEGAL_VIEJO = '''    <header class="header legal-header">
        <a href="/" class="header-logo-circle" aria-label="Volver al inicio">
            <img src="img/favicon.svg" alt="remedi.ar" width="38" height="38">
        </a>
        <div class="header-texto">
            <h1>remedi.ar</h1>
        </div>
    </header>
'''
for f in ("privacidad.html", "terminos.html"):
    reemplazar(f, LEGAL_VIEJO, HEADER, f"header legal de {f}")
    reemplazar(f, "</div>\n</body>\n", "</div>\n\n" + BOTON + "\n" + SCRIPT + "</body>\n", f"cierre de body en {f}")

# ---- about.html
reemplazar("about.html", '''    <!-- Header -->
    <header class="header">
        <div class="header-logo-circle">
    <img src="img/favicon.svg" alt="remedi.ar" width="38" height="38">
</div>
        <div class="header-texto">
            <h1>Sobre remedi.ar</h1>
            <p>Cómo funciona el buscador</p>
        </div>
        <div class="header-right">
            <a href="index.html" class="about-back-link">
                <span>← Volver</span>
            </a>
        </div>
    </header>

    <main id="main-content">
''', '''    <!-- Header -->
''' + HEADER + '''
    <main id="main-content">

    <nav class="breadcrumb">
        <a href="index.html">Inicio</a>
        <span class="breadcrumb-sep">›</span>
        <span class="breadcrumb-actual">Sobre remedi.ar</span>
    </nav>
''', "header de about.html")
reemplazar("about.html",
    '<script type="module" src="js/about.js"></script>\n\n</body>',
    '<script type="module" src="js/about.js"></script>\n' + SCRIPT + '\n' + BOTON + '\n</body>',
    "scripts y cierre de body en about.html")

# ---- CSS: reglas que quedan sin uso
CSS = "css/style.css"
reemplazar(CSS,
    "/* ── Override para páginas legales (privacidad.html, terminos.html) ── */\n"
    ".legal-header { border-bottom: 1px solid var(--border); margin-bottom: 0; }\n"
    ".legal-header .header-texto h1 { font-size: 18px; }\n\n",
    "", "reglas .legal-header")
reemplazar(CSS,
    ".about-back-link {\n    color: white;\n    text-decoration: none;\n    font-size: 13px;\n    display: flex;\n    align-items: center;\n    gap: 6px;\n}\n\n",
    "", "regla .about-back-link")

# ---- sw.js (about, privacidad, terminos y css estan en el precache)
reemplazar("sw.js", "const CACHE_NAME   = 'remediar-v34';", "const CACHE_NAME   = 'remediar-v35';", "CACHE_NAME")

# ---- changelog
reemplazar("CHANGELOG.md",
    "`.about-link-btn`). `sw.js`: `CACHE_NAME` sube a `v34`.\n",
    "`.about-link-btn`). `sw.js`: `CACHE_NAME` sube a `v34`.\n"
    "- `about.html`, `privacidad.html` y `terminos.html`: el header pasa a ser el\n"
    "  mismo que el de la home y las landings (logo, \"remedi.ar - Precios de\n"
    "  medicamentos\" y toda la barra clickeable hacia el inicio). Antes about\n"
    "  tenía otro título con subtítulo y un \"← Volver\", y las páginas legales\n"
    "  tenían el título más chico, solo \"remedi.ar\" y un borde inferior. About\n"
    "  suma el breadcrumb \"Inicio › Sobre remedi.ar\" que ya usan las landings.\n"
    "  Se quitan `.legal-header` y `.about-back-link`, que quedan sin uso.\n"
    "- Las tres páginas suman el botón de volver arriba (`#btnTop`, mismo que la\n"
    "  home y las landings) cargando `js/landing.js`, que ya estaba en el\n"
    "  precache. `sw.js`: `CACHE_NAME` sube a `v35`.\n",
    "entrada de CHANGELOG")

for p, (texto, crlf) in cambios.items():
    p.write_bytes((texto.replace("\n", "\r\n") if crlf else texto).encode("utf-8"))
    print("OK", p.relative_to(RAIZ))
print(f"\n{len(cambios)} archivos modificados.")
