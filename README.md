<p align="center">
  <img src="https://psbella.github.io/remediar/img/favicon.svg" width="90" />
</p>

#  remediar — Buscador de precios de medicamentos en Argentina

<!-- SEO -->
<p align="center">
  <strong>Buscador de precios de medicamentos en Argentina</strong><br>
  <em>Sistema open source que procesa datos oficiales de SIAFAR/COFA y genera un comparador de precios de medicamentos con actualización automática dos veces al día.</em>
</p>

<p align="center">
  <a href="https://remedi.ar">https://remedi.ar</a> ·
  <a href="https://github.com/psbella/remediar">GitHub</a>
</p>

---
<p align="center">

<!-- Hosting & License -->
<img src="https://img.shields.io/badge/hosted-GitHub%20Pages-brightgreen">
<img src="https://img.shields.io/badge/hosted-Cloudflare%20Pages-F38020?logo=cloudflare&logoColor=white">
<img src="https://img.shields.io/badge/License-MIT-blue.svg">
<img src="https://img.shields.io/github/repo-size/psbella/remedi.ar">
<img src="https://img.shields.io/github/last-commit/psbella/remedi.ar">
<img src="https://img.shields.io/github/issues-raw/psbella/remedi.ar">

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
<img src="https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white">
<img src="https://img.shields.io/badge/PyMuPDF-ee0000?logo=pypi&logoColor=white">
<img src="https://img.shields.io/badge/pandas-150458?logo=pandas&logoColor=white">
<img src="https://img.shields.io/badge/Git-F05032?logo=git&logoColor=white">
<img src="https://img.shields.io/badge/GitHub-181717?logo=github&logoColor=white">
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
- [📚 Documentación Completa](#-documentación-completa)
- [🔌 API No Oficial](#-api-no-oficial)
- [👥 Guía de Contribución](#-guía-de-contribución)
- [📊 Diagramas de Flujo Detallados](#-diagramas-de-flujo-detallados)
- [🧩 Referencia de Componentes Frontend](#-referencia-de-componentes-frontend)
- [🎨 Guía de Estilos CSS](#-guía-de-estilos-css)
- [🔧 Documentación de Workflows](#-documentación-de-workflows)
- [❓ Preguntas Frecuentes (FAQ)](#-preguntas-frecuentes-faq)
- [🗺️ Roadmap](#️-roadmap)
- [📄 Licencia](#-licencia)
- [🙏 Fuente de Datos](#-fuente-de-datos)

---

# ✨ Demo en Vivo

| Entorno | URL | Propósito |
|---|---|---|
| GitHub Pages | https://psbella.github.io/remediar/ | Desarrollo y respaldo |
| Cloudflare Pages | https://remedi.ar | Producción principal |

---

# 📊 Dataset actual

| Métrica | Valor |
|---|---|
| Registros | ~12.100 |
| Drogas únicas | ~460 |
| Landings SEO | 56+ |
| Tamaño JSON | ~2.5 MB |
| Tamaño gzip | ~520 KB |
| Actualizaciones | 2 veces/día (lunes a viernes) |

---

# 🎯 Funcionamiento General

El sistema se compone de tres capas principales:

## 1️⃣ Extracción y procesamiento

- GitHub Actions ejecuta un workflow automático dos veces al día (lunes a viernes)
- Se descarga el PDF oficial desde SIAFAR / COFA
- Python extrae y normaliza los registros mediante un pipeline de 8 capas
- Se cruzan los datos con el vademécum de PAMI para enriquecer cobertura
- Se genera `medicamentos.json`
- Se crean 56+ landings HTML estáticas SEO

---

## 2️⃣ Distribución

- El proyecto es 100% estático
- GitHub Pages funciona como backup
- Cloudflare Pages distribuye el contenido globalmente mediante CDN
- No existe backend persistente ni base de datos tradicional

---

## 3️⃣ Frontend SPA

- `index.html` carga la aplicación
- Los datos se descargan una sola vez
- Se indexan en memoria
- La búsqueda ocurre completamente del lado cliente
- El estado UI es reactivo mediante `store.js`

---

# 🧭 Principios del Proyecto

- Acceso libre a información de medicamentos
- Sin publicidad invasiva
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

    alt Caché válida (< 4 horas)
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

```javascript
function buildSearchIndex(medicamentos) {
  const drogasSet = new Set();
  const drogaToIndices = new Map();

  medicamentos.forEach((item, idx) => {
    const droga = normalizeString(item.droga);

    drogasSet.add(droga);

    if (!drogaToIndices.has(droga)) {
      drogaToIndices.set(droga, []);
    }

    drogaToIndices.get(droga).push(idx);
  });

  return { drogasSet, drogaToIndices };
}
```

---

## Debounce

```javascript
let debounceTimer;

searchInput.addEventListener('input', (e) => {
  clearTimeout(debounceTimer);

  debounceTimer = setTimeout(() => {
    performSearch(e.target.value);
  }, 250);
});
```

---

## Filtrado principal

```javascript
function performSearch(query, filters) {
  let results = [...store.rawData];

  if (query) {
    const normalized = normalizeString(query);

    results = results.filter(item =>
      normalizeString(item.droga).includes(normalized) ||
      normalizeString(item.laboratorio).includes(normalized)
    );
  }

  if (filters.pamiOnly) {
    results = results.filter(item => item.pami_cobertura > 0);
  }

  if (filters.sortBy === 'price_asc') {
    results.sort((a, b) => a.precio - b.precio);
  }

  renderResults(results.slice(0, 50));
}
```

---

## Complejidades

| Operación | Complejidad | Tiempo estimado |
|---|---|---|
| Indexación | O(n) | ~80ms |
| Búsqueda | O(n) | ~25-50ms |
| Ordenamiento | O(n log n) | ~60ms |
| Filtro PAMI | O(n) | ~15ms |

---

# 🔄 Actualización Automática de Datos

## Workflow

```mermaid
flowchart TD

    A[⏰ Cron GitHub Actions]
    B[📥 Descargar PDF SIAFAR]
    C[📄 Extraer registros por página]
    D[🧹 Limpiar y normalizar]
    N1[🔧 Pipeline de normalización 8 capas]
    BL[🛡️ Aplicar lista negra]
    E[🔍 Detectar outliers]
    F[💾 Generar medicamentos.json]
    R[📋 Generar outlier_report.json]
    G[🌐 Generar landings HTML + sitemap.xml]
    H[📤 Commit automático]
    I[🚀 GitHub Pages actualizado]

    A --> B
    B --> C
    C --> D
    D --> N1
    N1 --> BL
    BL --> E
    E --> F
    E --> R
    F --> G
    G --> H
    H --> I
```

---

## Pipeline de normalización (8 capas)

El parser aplica correcciones en cascada para resolver los problemas estructurales del PDF de SIAFAR:

| Capa | Función | Descripción |
|---|---|---|
| 0 | `reparar_droga_faltante()` | Cuando el PDF omite la línea del principio activo, todos los campos se desplazan. Separa droga+marca fusionadas usando un diccionario de 50 prefijos truncados |
| 1 | Detección en parse | Detecta registros con 4 campos en lugar de 5 durante la extracción del PDF |
| 2 | `rescatar_laboratorios()` | Recupera `laboratorio="Desconocido"` buscando el lab como sufijo en `presentacion` |
| 3 | `reparar_denver()` | Denver Farma usa droga+lab como nombre comercial; separa marca y presentacion fusionadas (variantes DENCR., DF) |
| 4 | `reparar_marca_desplazada()` | Cuando `marca` empieza con dígito y `presentacion` está vacía, invierte el desplazamiento |
| 5 | `extraer_presentacion_de_marca()` | Extrae la presentacion fusionada en el campo marca usando regex de dosis y formas farmacéuticas |
| 5b | `reparar_presentacion_desplazada()` | Separa presentacion+lab fusionados en el campo lab (3 sub-patrones: 2A, 2B, 2C) |
| 6 | `crosswalk_pami()` | Cruza contra `data/pami.xlsx` por marca+presentacion: recupera droga vacía, corrige lab, agrega `pami_cobertura` |
| 7 | `aplicar_droga_fixes()` | Aplica correcciones manuales desde `data/droga_fixes.json` (marca → droga, con soporte para corrección simultánea de marca) |

---

## Workflow GitHub Actions

```yaml
name: Actualizar precios

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

      - run: |
          python -m pip install --upgrade pip
          pip install pymupdf pandas openpyxl

      - run: python scripts/pdf_to_json.py

      - run: python scripts/generar_landings.py

      - name: Commit y push
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "actions@github.com"
          git pull --rebase origin main
          git add data/medicamentos.json
          git add data/outlier_report.json
          git add data/droga_fixes.json
          git add data/pami.xlsx
          git add *.html
          git add sitemap.xml
          git commit -m "Actualizar precios $(date +'%Y-%m-%d')" || echo "No changes"
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
| `vigencia_score` | number | Score de confiabilidad del precio (0-100). < 50 = outlier |
| `flags` | array | Etiquetas de anomalía (`precio_bajo`, `precio_sospechoso`, `precio_obsoleto`) |
| `precio_outlier_tipo` | string\|null | Categoría del outlier detectado |
| `outlier_razones` | array | Descripción de por qué es outlier |

---

## Archivos de referencia

| Archivo | Descripción |
|---|---|
| `data/pami.xlsx` | Vademécum PAMI con cobertura por marca+presentacion |
| `data/droga_fixes.json` | Correcciones manuales marca→droga para casos no resolubles con regex |
| `data/blacklist.json` | Registros excluidos manualmente del dataset |
| `data/outlier_report.json` | Reporte detallado de outliers de la última corrida |

---

# ⚡ Optimizaciones Implementadas

## ✅ Búsqueda en memoria

El JSON se carga una sola vez y se indexa.

---

## ✅ Estado centralizado

`store.js` controla búsqueda, filtros, ordenamiento y render reactivo.

---

## ✅ Debounce

La búsqueda espera 250ms luego de la última tecla.

---

## ✅ Caché

Los datos se almacenan en `sessionStorage` durante 4 horas.

---

## ✅ Dropdowns contextuales

Al buscar un medicamento, los filtros de presentación y laboratorio se actualizan para mostrar solo las opciones disponibles en los resultados actuales.

---

## ✅ Mobile first

CSS optimizado para móviles, tablets y desktop.

---

## ✅ Renderizado progresivo

50 resultados iniciales con botón "Ver más" para evitar bloquear el hilo principal.

---

## ✅ Landings SEO sin outliers

Las páginas estáticas por droga filtran automáticamente los registros con `vigencia_score < 50` para no mostrar precios obsoletos.

---

# ⏱️ Tiempos de Respuesta

| Métrica | Valor |
|---|---|
| FCP | 0.8 - 1.2s |
| LCP | 1.5 - 2.0s |
| TTI | 1.8 - 2.5s |
| Búsqueda | 25 - 100ms |
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
        C["⏰ Cron GitHub Actions"]
        D["🔄 Workflow manual"]
    end

    subgraph THREE["🐍 ETL Python"]
        E["pdf_to_json.py\n8 capas normalización"]
        F["generar_landings.py"]
        G["📊 medicamentos.json"]
    end

    subgraph REF["📋 REFERENCIA"]
        H["pami.xlsx"]
        I["droga_fixes.json"]
        J["blacklist.json"]
    end

    subgraph FIVE["🌐 FRONTEND"]
        K["index.html"]
        L["store.js"]
        M["searchEngine.js"]
        N["uiRenderer.js"]
    end

    subgraph SIX["📈 SEO"]
        O["Landings HTML"]
        P["sitemap.xml"]
    end

    subgraph SEVEN["☁️ HOSTING"]
        Q["GitHub Pages"]
        R["Cloudflare Pages"]
    end

    A --> B
    B --> C
    D --> C
    C --> E
    H --> E
    I --> E
    J --> E
    E --> G
    G --> F
    F --> O
    F --> K
    K --> L
    L --> M
    M --> N
    O --> P
    K --> Q
    Q --> R
```

---

# 📁 Estructura del Repositorio

```text
remediar/
├── index.html
├── style.css
├── manifest.json
├── robots.txt
├── sitemap.xml
├── privacidad.html
├── terminos.html
├── README.md
├── _headers
├── .nojekyll
│
├── img/
│   └── favicon.svg
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
│   ├── outlier_report.json
│   ├── blacklist.json
│   ├── droga_fixes.json
│   └── pami.xlsx
│
├── scripts/
│   ├── pdf_to_json.py
│   └── generar_landings.py
│
├── .github/workflows/
│   └── update-prices.yml
│
└── [56+ landings HTML]
```

---

# 🧰 Stack Tecnológico

| Capa | Tecnología |
|---|---|
| Frontend | HTML5 + CSS3 + Vanilla JS |
| Backend ETL | Python 3.11 |
| Parsing PDF | PyMuPDF |
| Crosswalk PAMI | pandas + openpyxl |
| Datos | JSON |
| CI/CD | GitHub Actions |
| Hosting | GitHub Pages + Cloudflare |
| SEO | JSON-LD + Open Graph |
| Caché | sessionStorage |

---

# 🧠 Decisiones Técnicas

## ¿Por qué Vanilla JS?

- Menor tamaño final
- Mejor tiempo de carga
- Sin dependencias pesadas
- SEO más simple
- Mantenimiento sencillo

## ¿Por qué JSON plano y no base de datos?

- Hosting estático
- Costos prácticamente cero
- CDN extremadamente eficiente
- Menor complejidad operacional

## ¿Por qué 8 capas de normalización?

El PDF de SIAFAR no tiene un esquema tabular estricto. Distintos laboratorios omiten campos, fusionan droga+marca sin separador, o desplazan la presentación al campo laboratorio. Las capas se aplican en cascada de menor a mayor complejidad, garantizando que cada corrección no interfiera con las anteriores.

## ¿Por qué Cloudflare Pages?

- CDN global
- Excelente latencia en Argentina
- Deploy automático
- HTTPS gratuito

---

# 💻 Ejecución Local

## Python

```bash
git clone https://github.com/psbella/remediar.git
cd remediar
python -m http.server 8000
```

## Node.js

```bash
npx http-server -p 8000 --cors -c-1
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
| `pdf_to_json.py` | Descarga PDF; aplica pipeline de 8 capas de normalización; crosswalk con PAMI (`pami_cobertura`); aplica blacklist; detecta outliers; genera `medicamentos.json` y `outlier_report.json` |
| `generar_landings.py` | Crea landings SEO estáticas por droga (filtrando outliers), regenera `sitemap.xml` con fecha del día |

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

- JSON-LD (Drug, Offer, BreadcrumbList)
- Open Graph
- Twitter Cards
- Sitemap.xml
- robots.txt
- Landings estáticas indexables por droga

---

## Ejemplo JSON-LD

```json
{
  "@context": "https://schema.org",
  "@type": "Drug",
  "name": "Ibuprofeno",
  "activeIngredient": "Ibuprofeno"
}
```

---

# 🔒 Seguridad y Privacidad

- No se recopilan datos personales
- No se utilizan cookies de tracking
- No existe autenticación en el frontend
- No existe backend persistente
- No se comparte información con terceros
- Todo el frontend puede auditarse públicamente

---

# 📚 Documentación Completa

| Documento | Descripción | Link |
|---|---|---|
| API No Oficial | Consumo externo de `medicamentos.json` | [Ver sección](#-api-no-oficial) |
| Guía de Contribución | Cómo colaborar con el proyecto | [Ver sección](#-guía-de-contribución) |
| Diagramas Mermaid | Arquitectura y flujos internos | [Ver sección](#-diagramas-de-flujo-detallados) |
| Referencia Frontend | Componentes y módulos JS | [Ver sección](#-referencia-de-componentes-frontend) |
| Guía CSS | Variables, breakpoints y estilos | [Ver sección](#-guía-de-estilos-css) |
| Workflows | Automatización y CI/CD | [Ver sección](#-documentación-de-workflows) |
| FAQ | Preguntas frecuentes | [Ver sección](#-preguntas-frecuentes-faq) |
| Roadmap | Funcionalidades futuras | [Ver sección](#️-roadmap) |

---

## 🌐 Enlaces del Proyecto

| Recurso | URL |
|---|---|
| Producción | https://remedi.ar |
| GitHub Pages | https://psbella.github.io/remediar/ |
| Repositorio GitHub | https://github.com/psbella/remediar |
| Actions / CI | https://github.com/psbella/remediar/actions |
| medicamentos.json (CDN) | https://remedi.ar/data/medicamentos.json |
| medicamentos.json (GitHub Raw) | https://raw.githubusercontent.com/psbella/remediar/main/data/medicamentos.json |
| Sitemap | https://remedi.ar/sitemap.xml |
| robots.txt | https://remedi.ar/robots.txt |
| Política de privacidad | https://remedi.ar/privacidad.html |
| Términos y condiciones | https://remedi.ar/terminos.html |

---

## 📦 Archivos Importantes

| Archivo | Función |
|---|---|
| `index.html` | SPA principal |
| `style.css` | Estilos globales |
| `js/core/store.js` | Estado reactivo |
| `js/searchEngine.js` | Motor de búsqueda |
| `js/uiRenderer.js` | Renderizado frontend + badge PAMI |
| `data/medicamentos.json` | Dataset principal |
| `data/pami.xlsx` | Vademécum PAMI (cobertura por marca+presentacion) |
| `data/droga_fixes.json` | Correcciones manuales de droga |
| `data/blacklist.json` | Registros excluidos |
| `scripts/pdf_to_json.py` | ETL principal (pipeline de 8 capas) |
| `scripts/generar_landings.py` | Generador de landings SEO |
| `.github/workflows/update-prices.yml` | Automatización |

---

# 🔌 API No Oficial

## Endpoints

| Método | URL |
|---|---|
| GET | https://remedi.ar/data/medicamentos.json |
| GET | https://raw.githubusercontent.com/psbella/remediar/main/data/medicamentos.json |

---

## JavaScript

```javascript
const response = await fetch('https://remedi.ar/data/medicamentos.json');
const { medicamentos } = await response.json();

// Filtrar por droga con cobertura PAMI
const conPami = medicamentos.filter(m => m.pami_cobertura > 0);

// Calcular copago PAMI
const copago = m => Math.round(m.precio * (1 - m.pami_cobertura / 100));
```

---

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
git checkout -b feature/nueva-funcion
git commit -m "feat: agregar filtro"
git push
```

## Convenciones de commits

| Tipo | Ejemplo |
|---|---|
| `feat` | Nueva funcionalidad |
| `fix` | Corrección de bug |
| `docs` | Documentación |
| `perf` | Performance |

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
    C6[Capa 6: crosswalk_pami]
    C7[Capa 7: aplicar_droga_fixes]
    BL[Blacklist]
    OUT[Detección de outliers]
    JSON[medicamentos.json]

    A --> B
    B --> C0
    C0 --> C1
    C1 --> C2
    C2 --> C3
    C3 --> C4
    C4 --> C5
    C5 --> C5B
    C5B --> C6
    C6 --> C7
    C7 --> BL
    BL --> OUT
    OUT --> JSON
```

---

## Frontend

```mermaid
flowchart LR

    A[Usuario]
    B[index.html]
    C[store.js]
    D[searchEngine.js]
    E[uiRenderer.js]

    A --> B
    B --> C
    C --> D
    D --> E
```

---

# 🧩 Referencia de Componentes Frontend

## store.js

- Estado global reactivo
- Filtros (texto, laboratorio, presentacion, pamiOnly)
- Ordenamiento
- Suscripciones

## uiRenderer.js

- Render tarjetas con badge PAMI (`pami_cobertura`)
- Actualización contextual de dropdowns según resultados
- Skeleton loaders
- Mensajes de error/vacío

## dataLoader.js

- Caché con `sessionStorage`
- Timestamp de vencimiento (4 horas)
- Refresh manual

## searchEngine.js

- Índice en memoria por droga
- Búsqueda normalizada (sin tildes, lowercase)
- Filtrado por laboratorio y presentacion

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

| Parámetro | Valor |
|---|---|
| Schedule | 10:30 y 18:30 ARG (lunes a viernes) |
| Runtime | Ubuntu latest |
| Python | 3.11 |
| Dependencias | pymupdf, pandas, openpyxl |
| Trigger manual | Sí (`workflow_dispatch`) |
| Pull antes de commit | Sí (`git pull --rebase`) |

---

# ❓ Preguntas Frecuentes (FAQ)

## ¿De dónde salen los datos?

Del PDF oficial publicado por SIAFAR / COFA dos veces al día.

## ¿Qué es el vigencia_score?

Un score de 0 a 100 que indica la confiabilidad del precio. Un score < 50 indica que el precio es probable outlier (obsoleto, cero, o estadísticamente anómalo respecto a la mediana de la droga). Las landings SEO y el frontend filtran estos registros automáticamente.

## ¿Qué significa el badge PAMI?

Muestra el porcentaje de cobertura del medicamento en el vademécum de PAMI y calcula el copago estimado aplicando ese porcentaje sobre el PVP actual de SIAFAR. Es una aproximación — el copago real puede variar.

## ¿Cada cuánto se actualiza?

Dos veces al día, de lunes a viernes.

## ¿Tiene publicidad?

No.

## ¿Tiene tracking?

No.

## ¿Se puede usar el JSON libremente?

Sí, bajo licencia MIT.

---

# 🗺️ Roadmap

## Corto plazo

- Historial de precios
- IOMA como segunda fuente de crosswalk
- Normalización de presentaciones en campos estructurados (forma, dosis, unidad, cantidad)

## Mediano plazo

- API REST pública
- Dashboard estadístico
- Evolución histórica de precios

## Largo plazo

- Integración farmacias tiempo real
- App móvil
- Geolocalización

---

# 📄 Licencia

MIT License. Uso libre para proyectos personales y comerciales.

---

# 🙏 Fuente de Datos

Datos proporcionados por SIAFAR / COFA. Cobertura PAMI desde el vademécum oficial del PAMI.

---

<p align="center">
  <strong>Hecho con ❤️ para que los medicamentos sean más accesibles en Argentina.</strong>
</p>
