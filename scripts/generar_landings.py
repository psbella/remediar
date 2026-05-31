#!/usr/bin/env python3
"""generar_landings.py — Tabla responsive con primera columna sticky en mobile."""
import json
from pathlib import Path
from datetime import datetime
import html as html_module   # para escapar contenido dinámico

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"

# Acciones terapéuticas SIN SIGLAS
ACCIONES = {
    "omeprazol": "Inhibidor de la bomba de protones",
    "metformina": "Antidiabético (biguanida)",
    "enalapril": "Antihipertensivo (inhibidor de la enzima convertidora de angiotensina)",
    "losartan": "Antihipertensivo (bloqueador del receptor de angiotensina II)",
    "levotiroxina": "Hormona tiroidea sintética",
    "clonazepam": "Benzodiazepina ansiolítica y anticonvulsivante",
    "alprazolam": "Benzodiazepina ansiolítica",
    "lorazepam": "Benzodiazepina ansiolítica",
    "sertralina": "Antidepresivo inhibidor selectivo de la recaptación de serotonina",
    "atorvastatina": "Hipolipemiante (inhibidor de la HMG-CoA reductasa)",
    "zolpidem": "Hipnótico no benzodiazepínico",
    "paracetamol": "Analgésico y antipirético",
    "ibuprofeno": "Antiinflamatorio no esteroide",
    "amoxicilina": "Antibiótico betalactámico",
    "acido-acetilsalicilico": "Antiplaquetario y antiinflamatorio no esteroide",
    "salbutamol": "Broncodilatador agonista beta-2 adrenérgico",
    "losartan-hidroclorotiazida": "Antihipertensivo combinado (bloqueador AT1 + diurético)",
    "prednisona": "Corticoesteroide antiinflamatorio",
    "escitalopram": "Antidepresivo inhibidor selectivo de la recaptación de serotonina",
    "diazepam": "Benzodiazepina ansiolítica y anticonvulsivante",
    "carbamazepina": "Anticonvulsivante y estabilizador del ánimo",
    "fenobarbital": "Anticonvulsivante (barbitúrico)",
    "betametasona": "Corticoesteroide",
    "naproxeno": "Antiinflamatorio no esteroide",
    "diclofenac": "Antiinflamatorio no esteroide",
    "amlodipina": "Antihipertensivo (bloqueante de los canales de calcio)",
    "carvedilol": "Antihipertensivo y betabloqueante",
    "clortalidona": "Diurético tiazídico",
    "furosemida": "Diurético de asa",
    "hidroclorotiazida": "Diurético tiazídico",
    "espironolactona": "Diurético ahorrador de potasio",
    "glibenclamida": "Antidiabético (sulfonilurea)",
    "insulina-glargina": "Insulina basal de acción prolongada",
    "insulina": "Hormona hipoglucemiante",
    "levodopa-carbidopa": "Antiparkinsoniano",
    "pregabalina": "Anticonvulsivante y analgésico neuropático",
    "gabapentina": "Anticonvulsivante y analgésico neuropático",
    "clozapina": "Antipsicótico atípico",
    "litio": "Estabilizador del ánimo",
    "valproato": "Anticonvulsivante y estabilizador del ánimo",
    "risperidona": "Antipsicótico atípico",
    "quetiapina": "Antipsicótico atípico",
    "olanzapina": "Antipsicótico atípico",
    "haloperidol": "Antipsicótico típico",
    "fluoxetina": "Antidepresivo inhibidor selectivo de la recaptación de serotonina",
    "venlafaxina": "Antidepresivo inhibidor de la recaptación de serotonina y noradrenalina",
    "levomepromazina": "Antipsicótico fenotiazínico",
    "metoclopramida": "Antiemético y procinético",
    "ipratropio": "Broncodilatador anticolinérgico",
    "sildenafil": "Inhibidor de la fosfodiesterasa tipo 5",
    "cetirizina": "Antihistamínico de segunda generación",
    "loratadina": "Antihistamínico de segunda generación",
    "pantoprazol": "Inhibidor de la bomba de protones",
    "aciclovir": "Antiviral (análogo de nucleósido)",
    "azitromicina": "Antibiótico macrólido",
    "bupropion": "Antidepresivo y coadyuvante para dejar de fumar",
}

DROGAS = list(ACCIONES.keys())

with open(DATA_DIR / "medicamentos.json", encoding='utf-8') as f:
    data = json.load(f)

medicamentos = data.get('medicamentos', [])
HOY      = datetime.now().strftime("%d/%m/%Y")
HORA     = datetime.now().strftime("%H:%M")
LASTMOD  = datetime.now().strftime("%Y-%m-%d")   # ← para sitemap

por_droga: dict[str, list] = {}
for m in medicamentos:
    d = m.get('droga', '').lower().strip()
    if d:
        por_droga.setdefault(d, []).append(m)


def esc(val) -> str:
    return html_module.escape(str(val)) if val else ''


def generar_filas_tabla(meds: list) -> str:
    filas = ""
    for m in meds[:60]:
        precio = m.get('precio', 0) or 0
        marca  = esc(m.get('marca', 'N/A'))
        pres   = esc(m.get('presentacion', 'N/A'))
        lab    = esc(m.get('laboratorio', 'N/A'))
        filas += (
            f'<tr>'
            f'<td class="col-marca">{marca}</td>'
            f'<td class="col-pres">{pres}</td>'
            f'<td class="col-lab">{lab}</td>'
            f'<td class="col-precio">${precio:,.2f}</td>'
            f'</tr>\n'
        )
    return filas


def generar_lista_marcas(meds: list) -> str:
    vistas: list[str] = []
    html = ""
    for m in meds:
        marca = m.get('marca', '')
        if marca and marca not in vistas:
            vistas.append(marca)
            html += f'<span class="marca-chip">{esc(marca)}</span>'
        if len(vistas) >= 15:
            break
    return html


# ── Generar landings ───────────────────────────────────────────────────
for droga_slug in DROGAS:
    nombre  = droga_slug.replace('-', ' ').replace('_', ' ').title()
    accion  = ACCIONES.get(droga_slug, "Medicamento")
    meds_dr = por_droga.get(droga_slug.replace('-', ' '), [])

    if not meds_dr:
        alt = droga_slug.rstrip('ao') + ('a' if droga_slug.endswith('o') else 'o')
        meds_dr = por_droga.get(alt.replace('-', ' '), [])

    meds_ordenados = sorted(meds_dr, key=lambda x: x.get('precio', 0) or 0)
    precios        = [m.get('precio', 0) or 0 for m in meds_dr if m.get('precio')]

    if precios:
        precio_min   = min(precios)
        precio_max   = max(precios)
        precio_rango = f"Precios desde ${precio_min:,.0f} hasta ${precio_max:,.0f} (ARS)."
    else:
        precio_rango = "Consultá los precios actualizados en la tabla."

    if meds_ordenados:
        filas_tabla  = generar_filas_tabla(meds_ordenados)
        lista_marcas = generar_lista_marcas(meds_ordenados)
    else:
        filas_tabla  = '<tr><td colspan="5" style="padding:40px;text-align:center;color:#999;">No se encontraron precios para este medicamento en la base de datos actual.</td></tr>'
        lista_marcas = '<p style="color:#999;font-size:13px;">Sin datos disponibles.</p>'

    fname = droga_slug + ".html"

    JS_INLINE = """<script>
(function() {
    var btn = document.getElementById('btnTop');
    if (!btn) return;
    window.addEventListener('scroll', function() {
        btn.classList.toggle('visible', window.scrollY > 300);
    }, { passive: true });
    btn.addEventListener('click', function() {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });
}());
(function() {
    var wrapper = document.getElementById('tablaWrapper');
    var scroll  = document.getElementById('tablaScroll');
    if (!wrapper || !scroll) return;
    function check() {
        wrapper.classList.toggle('no-overflow', scroll.scrollWidth <= scroll.clientWidth);
    }
    check();
    window.addEventListener('resize', check);
}());
(function() {
    var inp = document.getElementById('buscador-landing');
    var btn = document.getElementById('btnBuscar-landing');
    function ir() {
        var q = inp ? inp.value.trim() : '';
        if (q.length >= 2) window.location.href = 'index.html?q=' + encodeURIComponent(q);
    }
    if (btn) btn.addEventListener('click', ir);
    if (inp) inp.addEventListener('keydown', function(e) { if (e.key === 'Enter') ir(); });
}());
</script>"""

    html_content = f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{esc(nombre)}: precio en Argentina hoy | remedi.ar</title>
    <meta name="author" content="remedi.ar">
    <meta name="robots" content="index, follow">
    <link rel="canonical" href="https://remedi.ar/{droga_slug}">
    <link rel="stylesheet" href="style.css">
    <link rel="icon" type="image/svg+xml" href="img/favicon.svg">
    <link rel="manifest" href="manifest.json">
    <meta property="og:title" content="{esc(nombre)}: precio en Argentina — remedi.ar">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="{esc(nombre)}: precio en Argentina — remedi.ar">
</head>
<body>
<div class="container">
    <a href="index.html" style="text-decoration:none;color:inherit;">
        <header class="header">
            <div class="header-logo-circle">
                <img src="img/favicon.svg" alt="remedi.ar" width="38" height="38">
            </div>
            <div class="header-texto">
                <h1>remedi.ar - Precios de medicamentos</h1>
            </div>
        </header>
    </a>

    <main>
        <nav style="margin:10px 0;font-size:12px;color:#777;">
            <a href="index.html" style="color:#008B8B;">Inicio</a>
            <span style="margin:0 4px;">›</span>
            <span style="color:#555;">{esc(nombre)}</span>
        </nav>

        <div style="margin-bottom:25px;">
            <h1 style="color:#008B8B;font-size:28px;margin-bottom:8px;">Precio de {esc(nombre)} en Argentina</h1>
            <p style="color:#555;font-size:16px;">{esc(accion)}</p>
            <p style="color:#008B8B;font-size:14px;font-weight:500;margin-top:8px;">{precio_rango}</p>
        </div>

        <div style="margin-bottom:20px;background:#e8f4f4;padding:12px 16px;border-radius:10px;">
            <p style="font-size:13px;color:#005f5f;">
                <strong>Información:</strong> Los precios mostrados son públicos según SIAFAR/COFA.
            </p>
        </div>

        <div style="margin-bottom:35px;">
            <h2 style="color:#008B8B;margin-bottom:16px;font-size:20px;">Precios actualizados de {esc(nombre)}</h2>

            <p class="scroll-hint">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="9 18 15 12 9 6"/>
                </svg>
                Deslizá para ver más columnas
            </p>

            <div class="tabla-wrapper" id="tablaWrapper">
                <div class="tabla-scroll" id="tablaScroll">
                    <table class="tabla-precios">
                        <thead>
                            <tr>
                                <th>Marca</th>
                                <th>Presentación</th>
                                <th>Laboratorio</th>
                                <th>Precio público</th>
                            </tr>
                        </thead>
                        <tbody>
{filas_tabla}
                        </tbody>
                    </table>
                </div>
            </div>
            <p style="font-size:11px;color:#777;margin-top:10px;">
                Fuente: SIAFAR / COFA | Los precios son orientativos. Actualizado {HOY} {HORA} hs.
            </p>
        </div>

        <div style="margin-bottom:35px;">
            <h2 style="color:#008B8B;margin-bottom:12px;font-size:18px;">Marcas comerciales de {esc(nombre)}</h2>
            <div style="display:flex;flex-wrap:wrap;gap:10px;">
{lista_marcas}
            </div>
        </div>

        <div style="background:#f0f5f5;padding:25px;border-radius:16px;margin-top:20px;">
            <h2 style="color:#008B8B;margin-bottom:10px;font-size:18px;">Buscar otro medicamento</h2>
            <p style="margin-bottom:15px;font-size:14px;">Encontrá precios de cualquier medicamento en Argentina</p>
            <div class="busqueda-section" style="margin-bottom:0;">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="10" cy="10" r="7"/><line x1="15" y1="15" x2="21" y2="21"/>
                </svg>
                <input type="search" id="buscador-landing"
                    placeholder="Ej: Paracetamol, Amoxicilina, Ibuprofeno..."
                    style="flex:1;border:none;outline:none;background:none;font-size:14px;"
                    autocomplete="off">
                <button id="btnBuscar-landing"
                    style="background:#008B8B;color:white;border:none;border-radius:8px;padding:10px 24px;cursor:pointer;font-weight:500;">
                    Buscar
                </button>
            </div>
        </div>

        <section style="margin-top:35px;">
            <h2 style="color:#008B8B;margin-bottom:16px;font-size:18px;">Preguntas frecuentes sobre {esc(nombre)}</h2>

            <details style="margin-bottom:15px;background:#f9f9f9;border-radius:8px;padding:14px;" open>
                <summary style="font-weight:600;cursor:pointer;">¿Cuál es la acción terapéutica de {esc(nombre)}?</summary>
                <p style="font-size:14px;margin-top:8px;">{esc(accion)}</p>
            </details>

            <details style="margin-bottom:15px;background:#f9f9f9;border-radius:8px;padding:14px;" open>
                <summary style="font-weight:600;cursor:pointer;">¿Cuánto cuesta {esc(nombre)} en Argentina?</summary>
                <p style="font-size:14px;margin-top:8px;">{precio_rango} Consultá la tabla actualizada arriba con todos los precios públicos.</p>
            </details>
        </section>
    </main>

    <footer class="footer">
        <div class="footer-aviso">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                <circle cx="12" cy="12" r="10"/>
                <line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            Datos: <a href="https://siafar.com/datos" target="_blank" rel="noopener">Siafar / COFA</a> — Precios orientativos. Verificá en tu farmacia.
        </div>
        <nav class="footer-links">
            <a href="privacidad.html">Privacidad</a>
            <a href="terminos.html">Términos</a>
            <a href="mailto:pablo.s.bella@gmail.com?subject=remedi.ar%20-%20Consulta">Contacto</a>
        </nav>
    </footer>
</div>

<button id="btnTop" aria-label="Volver arriba">
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5">
        <polyline points="18 15 12 9 6 15"/>
    </svg>
</button>

{JS_INLINE}
</body>
</html>'''

    out = BASE_DIR / fname
    out.write_text(html_content, encoding='utf-8')
    print(f"✅ {fname}")

print(f"\n✅ {len(DROGAS)} landings generadas.")


# ── Generar sitemap ────────────────────────────────────────────────────
def generar_sitemap():
    urls = []

    # Home
    urls.append(f"""  <url>
    <loc>https://remedi.ar/</loc>
    <lastmod>{LASTMOD}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>""")

    # Landings por droga
    for droga_slug in DROGAS:
        urls.append(f"""  <url>
    <loc>https://remedi.ar/{droga_slug}.html</loc>
    <lastmod>{LASTMOD}</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.9</priority>
  </url>""")

    # Páginas estáticas
    for slug, freq, pri in [("privacidad", "monthly", "0.3"), ("terminos", "monthly", "0.3")]:
        urls.append(f"""  <url>
    <loc>https://remedi.ar/{slug}.html</loc>
    <lastmod>{LASTMOD}</lastmod>
    <changefreq>{freq}</changefreq>
    <priority>{pri}</priority>
  </url>""")

    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n'
    sitemap += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sitemap += '\n'.join(urls)
    sitemap += '\n</urlset>'

    out = BASE_DIR / "sitemap.xml"
    out.write_text(sitemap, encoding='utf-8')
    print(f"✅ sitemap.xml generado con {len(urls)} URLs ({LASTMOD})")

generar_sitemap()