<p align="center">
  <img src="https://remedi.ar/img/favicon.svg" width="90" />
</p>

# remedi.ar — Buscador de precios de medicamentos en Argentina

<p align="center">
  <strong>Buscador de precios de medicamentos en Argentina</strong><br>
  <em>Sistema open source que procesa datos oficiales de SIAFAR/COFA/PAMI y genera un comparador de precios con actualización automática dos veces al día.</em>
</p>

<p align="center">
  <a href="https://remedi.ar">https://remedi.ar</a> ·
  <a href="https://github.com/psbella/remediar">GitHub</a>
</p>

---

<p align="center">

<!-- Hosting & License -->
<img src="https://img.shields.io/badge/hosted-Cloudflare%20Pages-F38020?logo=cloudflare&logoColor=white">
<img src="https://img.shields.io/badge/License-MIT-blue.svg">
<img src="https://img.shields.io/github/repo-size/psbella/remediar">
<img src="https://img.shields.io/github/last-commit/psbella/remediar">
<img src="https://img.shields.io/github/issues-raw/psbella/remediar">

<br>

<!-- Valores -->
<img src="https://img.shields.io/badge/Open_Source-Yes-brightgreen">
<img src="https://img.shields.io/badge/Ads-No-red">
<img src="https://img.shields.io/badge/Tracking-No-red">
<img src="https://img.shields.io/badge/Privacy_First-Yes-success">

<br>

<!-- Frontend -->
<img src="https://img.shields.io/badge/Responsive-Yes-brightgreen">
<img src="https://img.shields.io/badge/Mobile_First-Yes-brightgreen">
<img src="https://img.shields.io/badge/PWA-Enabled-5A0FC8?logo=pwa">
<img src="https://img.shields.io/badge/SEO-Optimized-success">
<img src="https://img.shields.io/badge/Lighthouse-94%2F100-success">
<img src="https://img.shields.io/badge/dependencies-0-success">
<img src="https://img.shields.io/badge/Static_Site-Yes-blue">

<br>

<!-- Tecnologías -->
<img src="https://img.shields.io/badge/HTML5-E34F26?logo=html5&logoColor=white">
<img src="https://img.shields.io/badge/CSS3-1572B6?logo=css3&logoColor=white">
<img src="https://img.shields.io/badge/JavaScript-ES6+-F7DF1E?logo=javascript&logoColor=black">
<img src="https://img.shields.io/badge/JSON-000000?logo=json&logoColor=white">
<img src="https://img.shields.io/badge/SVG-FF9800?logo=svg&logoColor=white">

<br>

<!-- Backend / Automation -->
<img src="https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white">
<img src="https://img.shields.io/badge/PyMuPDF-ee0000?logo=pypi&logoColor=white">
<img src="https://img.shields.io/badge/pandas-150458?logo=pandas&logoColor=white">
<img src="https://img.shields.io/badge/GitHub_Actions-2088FF?logo=github-actions">

<br>

<!-- Diagramas -->
<img src="https://img.shields.io/badge/diagrams-Mermaid-ff3670?logo=mermaid&logoColor=white">

</p>

---

# 📋 Tabla de Contenidos

- [✨ Demo en Vivo](#-demo-en-vivo)
- [📊 Dataset actual](#-dataset-actual)
- [🎯 Funcionamiento General](#-funcionamiento-general)
- [🧭 Principios del Proyecto](#-principios-del-proyecto)
- [👤 Flujo del Usuario](#-flujo-del-usuario)
- [🧠 Algoritmo de Búsqueda y Filtrado](#-algoritmo-de-búsqueda-y-filtrado)
- [🔄 Actualización Automática de Datos](#-actualización-automática-de-datos)
- [📦 Estructura de Datos JSON](#-estructura-de-datos-json)
- [⚡ Optimizaciones Implementadas](#-optimizaciones-implementadas)
- [⏱️ Tiempos de Respuesta](#️-tiempos-de-respuesta)
- [🏗️ Arquitectura del Sistema](#️-arquitectura-del-sistema)
- [📁 Estructura del Repositorio](#-estructura-del-repositorio)
- [🧰 Stack Tecnológico](#-stack-tecnológico)
- [🧠 Decisiones Técnicas](#-decisiones-técnicas)
- [💻 Ejecución Local](#-ejecución-local)
- [🐍 Scripts Python](#-scripts-python)
- [📊 Métricas y Rendimiento](#-métricas-y-rendimiento)
- [🔍 SEO y Metadatos](#-seo-y-metadatos)
- [🔒 Seguridad y Privacidad](#-seguridad-y-privacidad)
- [🔌 API No Oficial](#-api-no-oficial)
- [👥 Guía de Contribución](#-guía-de-contribución)
- [📊 Diagramas de Flujo Detallados](#-diagramas-de-flujo-detallados)
- [🧩 Referencia de Componentes Frontend](#-referencia-de-componentes-frontend)
- [🎨 Guía de Estilos CSS](#-guía-de-estilos-css)
- [🔧 Documentación de Workflows](#-documentación-de-workflows)
- [❓ Preguntas Frecuentes (FAQ)](#-preguntas-frecuentes-faq)
- [⚠️ Limitaciones conocidas](#️-limitaciones-conocidas)
- [🗺️ Roadmap](#️-roadmap)
- [📄 Licencia](#-licencia)
- [🙏 Fuente de Datos](#-fuente-de-datos)

---

# ✨ Demo en Vivo

| Entorno | URL | Propósito |
|---|---|---|
| Cloudflare Pages | https://remedi.ar | Producción principal |
| GitHub Pages | https://psbella.github.io/remediar/ | Respaldo |

---

# 📊 Dataset actual

| Métrica | Valor |
|---|---|
| Registros | ~12.100 |
| Drogas únicas | ~1.740 |
| Tamaño JSON | ~2.5 MB |
| Tamaño gzip | ~520 KB |
| Con cobertura PAMI | ~5.900 (49%) |
| Entradas en blacklist | 569 |
| Cobertura parser de presentaciones | ~99.5% |
| Actualizaciones | 2 veces/día (lunes a viernes) |

---

# 🎯 Funcionamiento General

El sistema se compone de tres capas principales:

## 1️⃣ Extracción y procesamiento

- GitHub Actions ejecuta un workflow automático dos veces al día (lunes a viernes)
- Se descarga el PDF oficial desde SIAFAR / COFA
- Python extrae y normaliza los registros mediante un pipeline de 8+ capas
- Se cruzan los datos con el vademécum de PAMI para enriquecer cobertura
- Se genera `medicamentos.json` y `medicamentos.pretty.json`

---

## 2️⃣ Distribución

- El proyecto es 100% estático
- Cloudflare Pages distribuye el contenido globalmente mediante CDN
- GitHub Pages funciona como backup
- No existe backend persistente ni base de datos

---

## 3️⃣ Frontend SPA

- `index.html` carga la aplicación
- Los datos se descargan una sola vez y se indexan en memoria
- La búsqueda ocurre completamente del lado cliente
- El estado UI es reactivo mediante `store.js` (patrón pub/sub)

---

# 🧭 Principios del Proyecto

- Acceso libre a información de medicamentos
- Sin publicidad
- Sin tracking
- Performance primero
- Mobile first
- Open source
- Infraestructura simple y transparente
- Datos públicos y auditables

---

# 👤 Flujo del Usuario

```mermaid
sequenceDiagram
    autonumber

    participant U as 👤 Usuario
    participant B as 🌐 Navegador
    participant CDN as ⚡ Cloudflare CDN
    participant CACHE as 💾 sessionStorage
    participant JSON as 📦 medicamentos.json
    participant STORE as 🧠 store.js
    participant UI as 🖥️ uiRenderer.js

    U->>B: Ingresa a remedi.ar

    B->>CDN: GET /index.html
    CDN-->>B: HTML + CSS + JS

    B->>B: Render inicial (skeleton)
    B->>STORE: Inicializar estado

    alt Caché válida (< 2 horas)
        B->>CACHE: Leer medicamentos.json
        CACHE-->>B: Datos cacheados
    else Caché vacía o vencida
        B->>CDN: GET /data/medicamentos.json
        CDN-->>B: JSON comprimido (~520KB gzip)
        B->>CACHE: Guardar datos + timestamp
    end

    B->>STORE: Indexar medicamentos
    STORE->>UI: Render primeros resultados

    U->>B: Escribe "ibuprofeno"

    B->>B: Debounce 250ms
    B->>STORE: Ejecutar búsqueda

    STORE->>STORE: Filtrar + ordenar
    STORE->>UI: Actualizar resultados + dropdowns

    U->>B: Activa filtro PAMI
    STORE->>STORE: Recalcular filtros
    STORE->>UI: Render reactivo

    U->>B: Click en medicamento
    UI-->>U: Mostrar detalles + badge PAMI
```

---

# 🧠 Algoritmo de Búsqueda y Filtrado

## Indexación inicial

`searchEngine.js` construye un índice invertido de prefijos sobre `droga`, `marca` y `laboratorio`. Por cada token de 2 o más caracteres se generan todos sus prefijos, mapeados a conjuntos de índices del array de medicamentos.

```javascript
for (const palabra of txt.split(/\s+/)) {
    for (let k = 2; k <= palabra.length; k++) {
        const pref = palabra.slice(0, k);
        if (!indice[pref]) indice[pref] = new Set();
        indice[pref].add(i);
    }
}
```

La búsqueda realiza una intersección AND entre todos los términos ingresados — "ibuprofeno bago" devuelve solo registros que contengan ambos tokens.

---

## Ranking de relevancia

Los resultados se ordenan por tres criterios en cascada:

1. **Relevancia textual** — score basado en el campo donde ocurre el match:

| Match | Score |
|---|---|
| Droga exacta | +100 |
| Droga empieza con el término | +80 |
| Droga contiene el término | +50 |
| Marca exacta | +40 |
| Marca empieza con el término | +25 |
| Marca contiene el término | +15 |
| Laboratorio contiene el término | +5 |

2. **vigencia_score** — productos con precios confiables primero
3. **precio** — ascendente como desempate final

Los registros con `vigencia_score < 50` siempre van al fondo, independientemente del score de relevancia.

---

# 🔄 Actualización Automática de Datos

## Workflow

```mermaid
flowchart TD

    A[⏰ Cron GitHub Actions]
    B[📥 Descargar PDF SIAFAR]
    C[📄 Extraer registros por página]
    D[🧹 Limpiar y normalizar]
    N1[🔧 Pipeline de normalización 8+ capas]
    BL[🛡️ Aplicar blacklist]
    E[🔍 Detectar outliers]
    F[💾 Generar medicamentos.json]
    FP[📋 Generar medicamentos.pretty.json]
    R[📋 Generar outlier_report.json]
    CSV[🔬 Generar presentaciones_debug.csv]
    H[📤 Commit automático]
    I[🚀 Cloudflare Pages actualizado]

    A --> B
    B --> C
    C --> D
    D --> N1
    N1 --> BL
    BL --> E
    E --> F
    E --> FP
    E --> R
    E --> CSV
    F --> H
    FP --> H
    R --> H
    CSV --> H
    H --> I
```

---

## Pipeline de normalización (8+ capas)

El parser aplica correcciones en cascada para resolver los problemas estructurales del PDF de SIAFAR:

| Capa | Función | Descripción |
|---|---|---|
| 0 | `reparar_droga_faltante()` | Cuando el PDF omite la línea del principio activo, todos los campos se desplazan. Separa droga+marca fusionadas usando un diccionario de prefijos truncados |
| 1 | Detección en parse | Detecta registros con 4 campos en lugar de 5 durante la extracción del PDF |
| 2 | `rescatar_laboratorios()` | Recupera `laboratorio="Desconocido"` buscando el lab como sufijo en `presentacion` |
| 3 | `reparar_denver()` | Denver Farma usa droga+lab como nombre comercial; separa marca y presentacion fusionadas (variantes DENCR., DF) |
| 4 | `reparar_marca_desplazada()` | Cuando `marca` empieza con dígito y `presentacion` está vacía, invierte el desplazamiento |
| 5 | `extraer_presentacion_de_marca()` | Extrae la presentacion fusionada en el campo marca. Antes del regex de corte: (1) separa laboratorios pegados sin espacio (`_build_re_lab_pegado()`, dinámico por dataset); (2) separa formas farmacéuticas pegadas (`_RE_FORMA_PEGADA`); (3) elimina duplicados mayúscula+minúscula (`_RE_TOKEN_DUPLICADO`) |
| 5b | `reparar_presentacion_desplazada()` | Separa presentacion+lab fusionados en el campo lab (3 sub-patrones: 2A, 2B, 2C) |
| 5c | `limpiar_dosis_residual_en_marca()` | Limpia la dosis numérica que queda pegada al nombre del laboratorio en `marca` |
| 6 | `crosswalk_pami()` | Cruza contra `data/pami.xlsx`: recupera droga vacía, corrige laboratorio, normaliza `presentacion`, agrega `pami_cobertura` |
| 7 | `aplicar_droga_fixes()` | Aplica correcciones manuales desde `data/droga_fixes.json` |

---

## Workflow GitHub Actions

```yaml
name: 🔃 Actualizar precios

on:
  schedule:
    - cron: '30 13,21 * * 1-5'
  workflow_dispatch:

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - run: pip install -r requirements.txt

      - run: python scripts/pdf_to_json.py

      - name: Commit y push
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "actions@github.com"
          git add data/medicamentos.json
          git add data/medicamentos.pretty.json
          git add data/outlier_report.json
          git add data/droga_fixes.json
          git add data/pami.xlsx
          git add data/presentaciones_debug.csv
          git commit -m "Actualizar precios $(date +'%Y-%m-%d')" || echo "No changes"
          git pull --rebase origin main
          git push origin main
```

---

# 📦 Estructura de Datos JSON

## Ejemplo de registro

```json
{
  "droga": "ibuprofeno",
  "marca": "IBUPIRAC",
  "presentacion": "400 mg comp.x 20",
  "laboratorio": "Pfizer",
  "precio": 9800.50,
  "pami_cobertura": 55,
  "pres_forma": "COMPRIMIDOS",
  "pres_dosis": "400",
  "pres_unidad": "MG",
  "pres_cantidad": "20",
  "vigencia_score": 100,
  "flags": [],
  "precio_outlier_tipo": null,
  "outlier_razones": []
}
```

---

## Campos

| Campo | Tipo | Descripción |
|---|---|---|
| `droga` | string | Principio activo (nombre genérico) |
| `marca` | string | Nombre comercial |
| `presentacion` | string | Dosis, forma farmacéutica y cantidad |
| `laboratorio` | string | Laboratorio fabricante |
| `precio` | number | PVP en ARS (fuente: SIAFAR) |
| `pami_cobertura` | number\|null | Porcentaje de cobertura PAMI (ej: 55). Null si no está en el vademécum |
| `pres_forma` | string\|null | Forma farmacéutica parseada (ej: `"COMPRIMIDOS RECUBIERTOS"`, `"JARABE"`) |
| `pres_dosis` | string\|null | Dosis numérica (ej: `"400"`, `"500"`) |
| `pres_unidad` | string\|null | Unidad de la dosis (ej: `"MG"`, `"ML"`, `"UI"`) |
| `pres_cantidad` | string\|null | Cantidad de unidades (ej: `"20"`, `"100 ml"`) |
| `vigencia_score` | number | Score de confiabilidad del precio (0-100). < 50 = outlier |
| `flags` | array | Etiquetas de anomalía (`precio_bajo`, `precio_sospechoso`, `precio_obsoleto`) |
| `precio_outlier_tipo` | string\|null | Categoría del outlier detectado |
| `outlier_razones` | array | Descripción de por qué es outlier |

---

## Archivos de referencia

| Archivo | Descripción |
|---|---|
| `data/pami.xlsx` | Vademécum PAMI. Usado para: (1) cobertura por marca+presentacion, (2) recuperar droga faltante, (3) corregir laboratorio, (4) normalizar el campo `presentacion` |
| `data/droga_fixes.json` | Correcciones manuales marca→droga para casos no resolubles con regex |
| `data/blacklist.json` | 569 registros excluidos manualmente. Las claves usan el formato `droga\|marca\|presentacion\|laboratorio` en minúsculas |
| `data/outlier_report.json` | Reporte detallado de outliers de la última corrida |
| `data/presentaciones_debug.csv` | Auditoría del parser: `presentacion_original` vs. campos parseados (`forma`, `dosis`, `unidad`, `cantidad`) |
| `data/medicamentos.pretty.json` | Versión formateada con `indent=2` del dataset, para debug humano |

### Cómo agregar una corrección a `droga_fixes.json`

`droga_fixes.json` es editable manualmente — no hace falta tocar el código para cubrir nuevas marcas sin principio activo en el PDF.

Dos formatos soportados:

```json
// Solo droga (la marca ya está bien parseada)
"FORXIGA": "dapagliflozina"

// Droga + corrección de marca (droga y marca estaban fusionadas)
"DICLOFENAC POTÁSICO, PARACETAM KINALGIN P": {
  "droga": "diclofenac potásico, paracetamol",
  "marca": "KINALGIN P"
}
```

La clave es siempre el valor del campo `marca` o `droga` en mayúsculas tal como aparece en el JSON. El workflow lo aplica automáticamente en cada corrida.

---

# ⚡ Optimizaciones Implementadas

## ✅ Búsqueda en memoria

El JSON se carga una sola vez y se indexa en memoria con un índice invertido de prefijos. Sin requests adicionales para cada búsqueda.

## ✅ Estado centralizado

`store.js` controla búsqueda, filtros, ordenamiento y render reactivo con un patrón pub/sub manual — sin dependencias externas.

## ✅ Debounce

La búsqueda espera 250ms luego de la última tecla para no saturar el índice.

## ✅ Caché sessionStorage

Los datos se almacenan en `sessionStorage` con TTL de 2 horas. La clave `remedios_data_v2` permite invalidar el caché en deploys sin romper sesiones activas.

## ✅ Dropdowns contextuales

Al buscar un medicamento, los filtros de presentación y laboratorio se actualizan para mostrar solo las opciones disponibles en los resultados actuales.

## ✅ Mobile first

CSS optimizado para móviles, tablets y desktop sin frameworks externos.

## ✅ Renderizado progresivo

300 resultados por render para no bloquear el hilo principal. Los outliers (`vigencia_score < 50`) siempre aparecen al final, independientemente del orden seleccionado.

## ✅ Filtros sin texto

Seleccionar laboratorio o presentación desde el desplegable muestra resultados aunque el campo de búsqueda esté vacío.

## ✅ PWA completa

Service Worker con estrategia network-first para datos y cache-first para assets estáticos. Íconos en SVG + PNG (192×192 y 512×512) para instalación en todos los dispositivos.

## ✅ Seguridad en headers HTTP

CSP via header HTTP (no meta tag) con hash SHA256 del script inline de GA. `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy` y `Access-Control-Allow-Origin: *` para el JSON público.

---

# ⏱️ Tiempos de Respuesta

| Métrica | Valor |
|---|---|
| FCP | 0.8 - 1.2s |
| LCP | 1.5 - 2.0s |
| TTI | 1.8 - 2.5s |
| Búsqueda en índice | 25 - 100ms |
| TTFB | 50 - 150ms |

---

# 🏗️ Arquitectura del Sistema

```mermaid
flowchart LR

    subgraph ONE["🌐 FUENTE EXTERNA"]
        A[("SIAFAR / COFA\nPDF Oficial")]
        B["📄 Publicación diaria"]
    end

    subgraph TWO["⚙️ AUTOMATIZACIÓN"]
        C["⏰ Cron GitHub Actions\n10:30 y 18:30 AR"]
        D["🔄 Workflow manual"]
    end

    subgraph THREE["🐍 ETL Python"]
        E["pdf_to_json.py\n8+ capas normalización"]
        G["📊 medicamentos.json\nmedicamentos.pretty.json"]
    end

    subgraph REF["📋 REFERENCIA"]
        H["pami.xlsx"]
        I["droga_fixes.json"]
        J["blacklist.json (569)"]
    end

    subgraph FIVE["🌐 FRONTEND"]
        K["index.html"]
        L["store.js (pub/sub)"]
        M["searchEngine.js\n(índice invertido)"]
        N["uiRenderer.js"]
    end

    subgraph SEVEN["☁️ HOSTING"]
        Q["GitHub Pages\n(backup)"]
        R["Cloudflare Pages\n(producción)"]
    end

    A --> B
    B --> C
    D --> C
    C --> E
    H --> E
    I --> E
    J --> E
    E --> G
    G --> K
    K --> L
    L --> M
    M --> N
    G --> Q
    Q --> R
```

---

# 📁 Estructura del Repositorio

```text
remediar/
├── index.html
├── style.css
├── manifest.json
├── requirements.txt
├── robots.txt
├── sitemap.xml
├── sw.js
├── privacidad.html
├── terminos.html
├── README.md
├── _headers
├── .nojekyll
│
├── img/
│   ├── favicon.svg
│   ├── logo_banner.svg
│   ├── icon-192.png
│   ├── icon-512.png
│   └── og-image.png
│
├── js/
│   ├── main.js
│   ├── dataLoader.js
│   ├── filters.js
│   ├── searchEngine.js
│   ├── uiRenderer.js
│   ├── utils.js
│   └── core/
│       └── store.js
│
├── data/
│   ├── medicamentos.json
│   ├── medicamentos.pretty.json
│   ├── outlier_report.json
│   ├── presentaciones_debug.csv
│   ├── blacklist.json
│   ├── droga_fixes.json
│   └── pami.xlsx
│
├── scripts/
│   └── pdf_to_json.py
│
└── .github/workflows/
    ├── update_prices.yml
    ├── maintenance-on.yml
    └── maintenance-off.yml
```

---

# 🧰 Stack Tecnológico

| Capa | Tecnología |
|---|---|
| Frontend | HTML5 + CSS3 + Vanilla JS (ES Modules) |
| Estado UI | Patrón pub/sub manual (`store.js`) |
| Backend ETL | Python 3.11 |
| Parsing PDF | PyMuPDF |
| Crosswalk PAMI | pandas + openpyxl |
| Datos | JSON estático |
| CI/CD | GitHub Actions |
| Hosting | Cloudflare Pages + GitHub Pages |
| SEO | JSON-LD + Open Graph + Twitter Cards |
| Caché | sessionStorage (TTL 2h) + Service Worker |
| Seguridad | CSP via header HTTP + SHA256 hash |
| PWA | Service Worker + Web App Manifest |

---

# 🧠 Decisiones Técnicas

## ¿Por qué Vanilla JS?

- Cero dependencias en runtime
- Mejor tiempo de carga
- Sin actualizaciones de seguridad por dependencias transitivas
- Mantenimiento sencillo a largo plazo

## ¿Por qué JSON plano y no base de datos?

- Hosting estático con costo prácticamente cero
- CDN extremadamente eficiente
- Menor complejidad operacional
- El dataset (~12.000 registros) cabe perfectamente en memoria

## ¿Por qué 8+ capas de normalización?

El PDF de SIAFAR no tiene un esquema tabular estricto. Distintos laboratorios omiten campos, fusionan droga+marca sin separador, o desplazan la presentación al campo laboratorio. Las capas se aplican en cascada de menor a mayor complejidad, garantizando que cada corrección no interfiera con las anteriores.

## ¿Por qué Cloudflare Pages?

- CDN global con excelente latencia en Argentina
- Deploy automático en cada push
- HTTPS gratuito
- Soporte nativo de `_headers` para headers HTTP personalizados

---

# 💻 Ejecución Local

## Python (servidor de desarrollo)

```bash
git clone https://github.com/psbella/remediar.git
cd remediar
python -m http.server 8000
```

## Node.js

```bash
npx http-server -p 8000 --cors -c-1
```

## Ejecutar el ETL manualmente

```bash
pip install -r requirements.txt
python scripts/pdf_to_json.py
```

## Docker

```dockerfile
FROM nginx:alpine
COPY . /usr/share/nginx/html
```

```bash
docker build -t remediar .
docker run -p 8080:80 remediar
```

---

# 🐍 Scripts Python

| Script | Función |
|---|---|
| `scripts/pdf_to_json.py` | Descarga PDF; aplica pipeline de 8+ capas de normalización; crosswalk con PAMI; aplica blacklist; detecta outliers; genera `medicamentos.json`, `medicamentos.pretty.json`, `outlier_report.json` y `presentaciones_debug.csv` |

---

# 📊 Métricas y Rendimiento

| Métrica | Valor |
|---|---|
| Lighthouse Performance | 94-96 |
| Accessibility | 98 |
| Best Practices | 100 |
| SEO | 100 |
| CLS | 0.02 |
| FID | 12ms |

---

# 🔍 SEO y Metadatos

## Implementaciones

- JSON-LD (`WebSite` + `SearchAction`)
- Open Graph
- Twitter Cards
- Sitemap.xml
- robots.txt con `crawl-delay` para bots agresivos

## Ejemplo JSON-LD

```json
{
  "@context": "https://schema.org",
  "@type": "WebSite",
  "name": "remedi.ar",
  "potentialAction": {
    "@type": "SearchAction",
    "target": "https://remedi.ar/?q={search_term_string}",
    "query-input": "required name=search_term_string"
  }
}
```

---

# 🔒 Seguridad y Privacidad

- No se recopilan datos personales
- No se utilizan cookies de tracking
- No existe backend persistente
- Todo el frontend es auditable públicamente
- **Content Security Policy** via header HTTP con hash SHA256 del único script inline (Google Analytics): `script-src 'self' 'sha256-...' https://www.googletagmanager.com`
- **CORS** habilitado en `/data/medicamentos.json` para consumo externo (`Access-Control-Allow-Origin: *`)
- `robots.txt` bloquea explícitamente GPTBot y ClaudeBot
- Google Analytics configurado en modo anónimo — ver [política de privacidad](https://remedi.ar/privacidad.html)

---

# 🔌 API No Oficial

El JSON de medicamentos es público y accesible libremente bajo licencia MIT.

## Endpoints

| Método | URL |
|---|---|
| GET | https://remedi.ar/data/medicamentos.json |
| GET | https://raw.githubusercontent.com/psbella/remediar/main/data/medicamentos.json |
| GET (legible) | https://remedi.ar/data/medicamentos.pretty.json |

## JavaScript

```javascript
const response = await fetch('https://remedi.ar/data/medicamentos.json');
const { medicamentos } = await response.json();

// Filtrar por droga con cobertura PAMI
const conPami = medicamentos.filter(m => m.pami_cobertura > 0);

// Calcular copago PAMI
const copago = m => Math.round(m.precio * (1 - m.pami_cobertura / 100));

// Filtrar por forma farmacéutica
const comprimidos = medicamentos.filter(m => m.pres_forma?.includes('COMPRIMIDOS'));
```

## Python

```python
import pandas as pd

df = pd.read_json("https://remedi.ar/data/medicamentos.json")
meds = pd.json_normalize(df['medicamentos'])

# Filtrar solo los que tienen cobertura PAMI
con_pami = meds[meds['pami_cobertura'].notna()]
```

---

# 👥 Guía de Contribución

## Flujo

```bash
git clone https://github.com/psbella/remediar.git
git checkout -b feature/nueva-funcion
# hacer cambios
git commit -m "feat: descripción del cambio"
git push origin feature/nueva-funcion
# abrir Pull Request
```

## Convenciones de commits

| Tipo | Uso |
|---|---|
| `feat` | Nueva funcionalidad |
| `fix` | Corrección de bug |
| `docs` | Documentación |
| `perf` | Performance |
| `chore` | Mantenimiento / limpieza |
| `security` | Cambios de seguridad |

---

# 📊 Diagramas de Flujo Detallados

## Pipeline ETL completo

```mermaid
flowchart TD

    A[PDF SIAFAR]
    B[Descarga + extracción por página]
    C0[Capa 0: reparar_droga_faltante]
    C1[Capa 1: desplazamiento en parse]
    C2[Capa 2: rescatar_laboratorios]
    C3[Capa 3: reparar_denver]
    C4[Capa 4: reparar_marca_desplazada]
    C5[Capa 5: extraer_presentacion_de_marca]
    C5B[Capa 5b: reparar_presentacion_desplazada]
    C5C[Capa 5c: limpiar_dosis_residual_en_marca]
    C6[Capa 6: crosswalk_pami]
    C7[Capa 7: aplicar_droga_fixes]
    BL[Blacklist 569 entradas]
    OUT[Detección de outliers IQR]
    PRES[Parser de presentaciones]
    JSON[medicamentos.json]
    PRETTY[medicamentos.pretty.json]
    DEBUG[presentaciones_debug.csv]
    REPORT[outlier_report.json]

    A --> B
    B --> C0
    C0 --> C1
    C1 --> C2
    C2 --> C3
    C3 --> C4
    C4 --> C5
    C5 --> C5B
    C5B --> C5C
    C5C --> C6
    C6 --> C7
    C7 --> BL
    BL --> OUT
    OUT --> PRES
    PRES --> JSON
    JSON --> PRETTY
    PRES --> DEBUG
    OUT --> REPORT
```

---

## Detalle de la Capa 5: extraer_presentacion_de_marca

```mermaid
flowchart TD
    IN["marca='CARBOPLATINO MICROSULES150 mg iny.f.a.x 1'\npresentacion=''"]

    subgraph PRE["Pre-limpieza (en orden)"]
        A["1. _RE_TOKEN_DUPLICADO\nElimina token mayúscula duplicado\nGELgel → gel\nBOLSAbolsa → bolsa"]
        B["2. _RE_FORMA_PEGADA\nInserta espacio antes de forma pegada\nBENZOCAINA GELgel → BENZOCAINA gel"]
        C["3. _build_re_lab_pegado (dinámico)\nInserta espacio entre lab conocido y dosis pegada\nMICROSULES150 → MICROSULES 150"]
    end

    D{"¿_RE_EXTRAER_PRES\nhace match?"}
    E["marca = grupo 1\npresentacion = grupo 2"]
    F["Registro sin cambios\n(caso no resuelto)"]

    IN --> A --> B --> C --> D
    D -- Sí --> E
    D -- No --> F

    style PRE fill:#f0f8f0,stroke:#aaa
```

El regex `_build_re_lab_pegado` se construye dinámicamente en cada corrida a partir de los laboratorios ya presentes en el dataset. Esto evita mantener una lista hardcodeada que se desactualiza.

---

## Parser de presentaciones

```mermaid
flowchart TD
    P["presentacion: '400 mg comp.rec.x 20'"]
    P1["Normalizar prefijos: Ad. Ped. Rtd."]
    P2["Extraer dosis + unidad"]
    P3["Buscar forma farmacéutica en FORMAS_MAP (60+ entradas)"]
    P4{"¿Forma encontrada?"}
    P5["Fallback: scan en cualquier posición"]
    P6["Extraer cantidad"]
    P7["pres_forma / pres_dosis / pres_unidad / pres_cantidad"]

    P --> P1 --> P2 --> P3 --> P4
    P4 -- Sí --> P6
    P4 -- No --> P5 --> P6
    P6 --> P7
```

| Campo generado | Ejemplo |
|---|---|
| `pres_forma` | `"COMPRIMIDOS RECUBIERTOS"` |
| `pres_dosis` | `"400"` |
| `pres_unidad` | `"MG"` |
| `pres_cantidad` | `"20"` |

Cobertura actual: **~99.5%**. El archivo `data/presentaciones_debug.csv` permite auditar los casos no resueltos después de cada corrida.

---

## Ciclo de vida de una búsqueda

```mermaid
sequenceDiagram
    participant U as 👤 Usuario
    participant M as main.js
    participant S as store.js
    participant SE as searchEngine.js
    participant F as filters.js
    participant R as uiRenderer.js

    U->>M: input "ibuprofeno bago"
    M->>M: debounce 250ms
    M->>S: setFiltroTexto("ibuprofeno bago")

    S->>SE: buscar("ibuprofeno bago")
    Note over SE: Normaliza → ["ibuprofeno","bago"]
    Note over SE: Intersección AND de índices de prefijos
    Note over SE: Ordena por relevancia + vigencia + precio
    SE-->>S: resultados ordenados

    S->>F: aplicarFiltros(resultados, presentacion, laboratorio, soloPami)
    F-->>S: resultados filtrados

    S->>S: notificar()
    S->>R: suscribirse callback

    R->>R: cargarOpcionesFiltros(resultados)
    Note over R: Dropdowns muestran solo opciones del resultado actual
    R->>R: mostrarResultados(resultados)
    Note over R: parsearPresentacion() si no hay pres_*
    R-->>U: Tarjetas con chips de presentación + badge PAMI
```

---

## Flujo reactivo del store

```mermaid
flowchart TD
    subgraph ACCIONES["Acciones"]
        A1[setFiltroTexto]
        A2[setFiltroPresentacion]
        A3[setFiltroLaboratorio]
        A4[setFiltroOrden]
        A5[setSoloPami]
        A6[limpiarFiltros]
    end

    subgraph RECALC["recalcularResultados()"]
        R1{"¿hay texto\no filtro activo?"}
        R2["buscar(texto)\n→ índice invertido"]
        R3["todos los medicamentos"]
        R4["aplicarFiltros()"]
        R5{"orden ≠\n'relevancia'?"}
        R6["ordenar()"]
        R7["state.resultados = …"]
    end

    subgraph UI["UI (suscriptores)"]
        U1["cargarOpcionesFiltros()"]
        U2["mostrarResultados()"]
        U3["mostrarMensajeInicial()"]
    end

    ACCIONES --> RECALC
    R1 -- No --> U3
    R1 -- hayTexto --> R2 --> R4
    R1 -- soloFiltros --> R3 --> R4
    R4 --> R5
    R5 -- Sí --> R6 --> R7
    R5 -- No --> R7
    R7 --> notificar
    notificar --> U1
    notificar --> U2
```

---

## Anatomía de un registro

```mermaid
flowchart LR
    subgraph SIAFAR["📄 SIAFAR / PDF"]
        S1[droga]
        S2[marca]
        S3[presentacion]
        S4[laboratorio]
        S5[precio]
    end

    subgraph PAMI["📋 pami.xlsx"]
        P1[pami_cobertura]
        P2["droga (recuperación)"]
        P3["laboratorio (corrección)"]
        P4["presentacion (normalización)"]
    end

    subgraph PARSER["🔧 _parsear_presentacion()"]
        PR1[pres_forma]
        PR2[pres_dosis]
        PR3[pres_unidad]
        PR4[pres_cantidad]
    end

    subgraph OUTLIER["📊 Detección outliers (IQR)"]
        O1[vigencia_score]
        O2[flags]
        O3[precio_outlier_tipo]
        O4[outlier_razones]
    end

    subgraph JSON["📦 medicamentos.json"]
        J[Registro final]
    end

    S1 & S2 & S3 & S4 & S5 --> J
    P1 & P2 & P3 & P4 --> J
    PR1 & PR2 & PR3 & PR4 --> J
    O1 & O2 & O3 & O4 --> J
```

---

# 🧩 Referencia de Componentes Frontend

## store.js

- Estado global reactivo con patrón pub/sub (`suscribirse` / `notificar`)
- Filtros: texto, laboratorio, presentacion, orden, soloPami
- Sin texto ni filtros activos → `resultados = []` (muestra mensaje inicial)
- Con filtros activos y sin texto → parte del dataset completo y aplica filtros
- Ordenamiento con conciencia de vigencia: `vigencia_score < 50` siempre al fondo

## uiRenderer.js

- Render de tarjetas con principio activo en mayúsculas
- Chips de presentación: usa `pres_forma` / `pres_dosis` / `pres_unidad` / `pres_cantidad` del JSON cuando están disponibles; cae a `parsearPresentacion()` (JS) como fallback
- En modo PAMI activo, muestra el copago estimado como precio principal y el PVP como referencia secundaria
- Chip PAMI con formato "Cobertura PAMI 55% · $4.500"
- Skeleton loaders + mensajes de error/vacío
- Scroll-to-top automático al superar 300px de scroll

## utils.js

- `normalizar()`: lowercase + quita tildes para búsqueda
- `formatearPrecio()`: formato ARS con `toLocaleString`
- `escapeHtml()`: escape de `&`, `<`, `>`, `"`, `'` para prevenir XSS
- `normalizarLaboratorio()`: resuelve laboratorios truncados por el PDF
- `parsearPresentacion()`: parser JS de fallback (60+ formas en `FORMAS_MAP`)
- `extraerFiltros()`: construye sets de presentaciones y laboratorios válidos para dropdowns

## dataLoader.js

- Caché con `sessionStorage` (clave `remedios_data_v2`, TTL 2 horas)
- Fetch con `priority: 'high'`
- Fallback silencioso si `sessionStorage` está bloqueado

## searchEngine.js

- Índice invertido de prefijos sobre `droga`, `marca` y `laboratorio`
- Búsqueda AND multi-término normalizada (sin tildes, lowercase)
- Ranking por relevancia textual (droga > marca > lab), `vigencia_score` y precio
- Registros con `vigencia_score < 50` degradados al fondo

## filters.js

- `aplicarFiltros()`: filtrado por presentación, laboratorio y PAMI
- `ordenar()`: ordenamiento con conciencia de vigencia (`vigencia_score < 50` siempre al fondo)
- `esValorCorrupto()`: detección de laboratorios con valores numéricos o de presentación en el campo lab

---

# 🎨 Guía de Estilos CSS

## Variables principales

```css
:root {
  --teal:        #00bfa5;
  --teal-light:  #e0f7f4;
  --teal-darker: #00897b;
  --text-1:      #1a2e2e;
  --text-4:      #7a9696;
  --border-radius: 12px;
}
```

## Responsive

| Breakpoint | Tamaño |
|---|---|
| Mobile | < 640px |
| Tablet | 641px - 1024px |
| Desktop | > 1024px |

---

# 🔧 Documentación de Workflows

| Workflow | Trigger | Función |
|---|---|---|
| `update_prices.yml` | Cron `30 13,21 * * 1-5` + manual | ETL principal: descarga PDF, genera JSON, hace commit |
| `maintenance-on.yml` | Manual | Reemplaza `index.html` con página de mantenimiento |
| `maintenance-off.yml` | Manual | Restaura `index.html` desde backup |

| Parámetro | Valor |
|---|---|
| Schedule | 10:30 y 18:30 AR (lunes a viernes) |
| Runtime | Ubuntu latest |
| Python | 3.11 |
| Caché de dependencias | `cache: 'pip'` en `setup-python@v5` |
| Dependencias | Ver `requirements.txt` |
| Trigger manual | Sí (`workflow_dispatch`) |
| Pull antes de push | Sí (`git pull --rebase`) |

---

# ❓ Preguntas Frecuentes (FAQ)

## ¿De dónde salen los datos?

Del PDF oficial publicado por SIAFAR / COFA dos veces al día, de lunes a viernes.

## ¿Qué es el vigencia_score?

Un score de 0 a 100 que indica la confiabilidad del precio. Se calcula usando estadística IQR (rango intercuartílico) por droga + detección de inconsistencias de escala. Un score < 50 indica que el precio es probable outlier (obsoleto, cero, o estadísticamente anómalo respecto a la mediana de la droga).

## ¿Qué significa el chip PAMI?

Muestra la cobertura y el copago estimado en un solo chip: **"Cobertura PAMI 55% · $4.500"**.

El copago se calcula como `precio × (1 - cobertura / 100)`.

```
PVP SIAFAR:       $10.000
Cobertura PAMI:   55%
Copago estimado:  $10.000 × (1 - 0.55) = $4.500
```

Es una aproximación — el copago real puede variar porque el porcentaje de cobertura es del vademécum PAMI y el precio base es el PVP actualizado de SIAFAR.

## ¿Cada cuánto se actualiza?

Dos veces al día, de lunes a viernes (10:30 y 18:30 hora Argentina).

## ¿Tiene publicidad?

No.

## ¿Tiene tracking?

No. Usamos Google Analytics en modo anónimo para entender el uso del sitio.

## ¿Se puede usar el JSON libremente?

Sí, bajo licencia MIT. El endpoint está habilitado con `Access-Control-Allow-Origin: *`.

---

# ⚠️ Limitaciones conocidas

| Limitación | Descripción |
|---|---|
| ~9 registros sin presentación | El PDF de SIAFAR no incluye la presentación para estas marcas (KETOSTERIL, FRENALER D, DEXALERGIN, VIXALERG, KINALGIN P, ASFARADIL, FEMIDEN, SIGNORINA, VAXNEUVANCE). No son errores del parser — el dato simplemente no está en la fuente. |
| `pami_cobertura` es aproximado | El porcentaje proviene del vademécum PAMI (que se actualiza con menor frecuencia) aplicado sobre el PVP actual de SIAFAR. El copago real puede diferir. |
| Precios de SIAFAR en ARS | Con la inflación argentina, los precios pueden quedar desactualizados entre corridas. El `vigencia_score` ayuda a identificar los registros más sospechosos. |
| PDF de SIAFAR sin esquema fijo | Distintos laboratorios aplican su propia semántica al PDF. El pipeline de 8+ capas resuelve los patrones conocidos; pueden aparecer casos nuevos en futuras corridas. |
| SSL de SIAFAR | El servidor de SIAFAR tiene un certificado con chain incompleta. La verificación SSL usa `certifi` como CA bundle. |
---

# 🗺️ Roadmap

## Corto plazo

- Filtro por forma farmacéutica en la UI (usando `pres_forma`, ya disponible en el JSON)
- Historial de precios
- Corrección de verificación SSL en descarga de SIAFAR (bundlear CA)
- Corrección de verificación SSL en descarga de SIAFAR (bundlear CA)
  
## Mediano plazo

- IOMA como segunda fuente de crosswalk
- API REST pública documentada
- Dashboard estadístico de variación de precios

## Largo plazo

- Evolución histórica de precios
- App móvil nativa
- Integración con farmacias en tiempo real

---

# 📄 Licencia

MIT License. Uso libre para proyectos personales y comerciales con atribución.

---

# 🙏 Fuente de Datos

Datos proporcionados por [SIAFAR / COFA](https://siafar.com/precios/pdf/). Cobertura PAMI desde el [vademécum oficial del PAMI](https://datos.pami.org.ar/dataset/medicamentos-para-afiliados).

---

## 🌐 Enlaces del Proyecto

| Recurso | URL |
|---|---|
| Producción | https://remedi.ar |
| GitHub Pages | https://psbella.github.io/remediar/ |
| Repositorio | https://github.com/psbella/remediar |
| Actions / CI | https://github.com/psbella/remediar/actions |
| medicamentos.json | https://remedi.ar/data/medicamentos.json |
| medicamentos.pretty.json | https://remedi.ar/data/medicamentos.pretty.json |
| Sitemap | https://remedi.ar/sitemap.xml |
| Política de privacidad | https://remedi.ar/privacidad.html |
| Términos y condiciones | https://remedi.ar/terminos.html |

---

<p align="center">
  <strong>Hecho con ❤️ para que los medicamentos sean más accesibles en Argentina.</strong>
</p>
