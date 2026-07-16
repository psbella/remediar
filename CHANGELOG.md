# Changelog

Todos los cambios notables de remedi.ar se documentan en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es/1.0.0/) y el proyecto adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.2.3] - 2026-07-16

### 🐛 Corregido
- `scripts/etl/presentacion.py`: quedaban 15 claves duplicadas más en `_FORMAS_NORM_PRES` además de `'pda'` (`vial`, `fco`, `jbe`, `sol.iny`, `iny.liof`, `polv.p/susp.oral`, `caram`, `colir`, `ap.aplic.desc`, `autoinyect.prell`, `jga.prell`, `jga.pr`, `jer.prell`, `lap.prell`, `viales`) — todas con el mismo valor en ambas definiciones, detectadas con Ruff (`F601`) y no por revisión manual. Se elimina la entrada redundante en cada caso; el valor efectivo no cambia.
- Publicado el release de GitHub correspondiente a la 2.2.2, que había quedado documentada en este CHANGELOG y en `package.json` pero nunca tageada ni publicada como release.

## [2.2.2] - 2026-07-14

### 🐛 Corregido
- Los fixes que el CHANGELOG de la 2.2.1 declaraba (duplicado de `'pda'` en `presentacion.py`, indentación de `js/store.js`, `"type": "module"` en `package.json`) nunca se aplicaron al código real — quedaron documentados pero no commiteados. Se aplican ahora de verdad, con verificación explícita línea por línea antes de cada commit.
- README: corregido el conteo de tests de "13" a "28" en varios lugares, que habían quedado desactualizados desde que se agregaron los 15 tests unitarios del ETL modular.

## [2.2.1] - 2026-07-12

### ✨ Agregado
- 15 tests unitarios nuevos para las funciones puras de `scripts/etl/` (`utils`, `blacklist`, `outliers`, `droga_fixes`, `reparaciones`, `parser`) en `tests/test_etl_modulos.py` — 28 tests en total. Complementan a `test_etl_sanidad.py`/`test_schema.py`, que solo validan el JSON final agregado.
- Ruff (`pyproject.toml`) y ESLint (`eslint.config.js`) configurados — set inicial pragmático (errores reales, no preferencias de estilo), sin bloquear CI todavía.

### 🐛 Corregido
- `scripts/etl/presentacion.py`: `'pda'` estaba definido dos veces en `_FORMAS_NORM_PRES` (`PARCHE` y `POMADA`) — la segunda definición ganaba en silencio. Se confirma que `POMADA` es el valor correcto y se elimina la entrada muerta.
- `js/store.js`: indentación incorrecta en el cierre de `_extraerFiltros` (8 espacios de más).

### 📝 Documentado
- `## [2.2.0]` le faltaba el encabezado de versión en este archivo — el contenido (footer con versión dinámica, contraste WCAG, bump de `CACHE_NAME`) quedó flotando sin sección. Se corrige.

---

## [2.2.0] - 2026-07-11

### ✨ Agregado
- Footer: link a la licencia MIT (`opensource.org/license/mit`) y número de versión, leído dinámicamente desde `package.json`.

### 🐛 Corregido
- `style.css`: contraste de `--text-5` (#999999 → #6c6c6c) para cumplir WCAG AA en placeholder del buscador e íconos de filtros/footer.
- `style.css`: elimina otra reaparición de la declaración duplicada de `.celda.valor.uppercase`.
- `sw.js`: bump de `CACHE_NAME` (v3 → v6) para forzar actualización de assets estáticos cacheados.

---

## [2.1.9] - 2026-07-10

### ♻️ Refactor
- `pdf_to_json.py` modularizado: de 2024 a 138 líneas. La lógica se movió a 10 módulos nuevos en `scripts/etl/` (`config`, `parser`, `blacklist`, `reparaciones`, `droga_fixes`, `pami`, `presentacion`, `outliers`, `enriquecimiento`, `utils`) — `pdf_to_json.py` ahora solo orquesta el orden de ejecución.

### 🐛 Corregido
- `scripts/github_release_helper.py`: corrige referencia de repo.
- `style.css`: elimina declaración duplicada de `.celda.valor.uppercase`.

### 📝 Documentado
- README actualizado con la nueva estructura de `scripts/etl/` (diagrama, tabla de funciones, árbol de archivos).

---

## [2.1.8] - 2026-07-07

### 🔒 Seguridad
- CSP: `style-src` sin `unsafe-inline` — cierra el ítem M1, pendiente desde el inicio de la auditoría técnica. Se migraron los 12 `style="..."` inline de `index.html`/`admin.html` a clases CSS, y los bloques `<style>` embebidos de `admin.html` y `mantenimiento.html` se movieron a `admin.css`/`mantenimiento.css` nuevos. Un `style=` generado dinámicamente en `js/uiRenderer.js` (dentro de un template literal) se escapó del primer pase y se corrigió al detectarse en la consola del navegador en producción.
- Actualizada la Response Header Transform Rule de Cloudflare con la CSP sin `unsafe-inline` (cambio de dashboard, no versionado en el repo).
- Desactivado Cloudflare Web Analytics (no se usaba; generaba un bloqueo de CSP en consola por `static.cloudflareinsights.com`).

### ✨ Agregado
- Validación formal de schema (`tests/test_schema.py` + `tests/medicamentos.schema.json`) para `medicamentos.json` — valida el contrato estructural (claves, tipos, opcionalidad), separado de los umbrales de calidad de negocio que ya cubre `test_etl_sanidad.py`. `additionalProperties: false` a propósito: si el ETL cambia la forma del output, el test avisa hasta que el schema se actualice también.

### 📝 Documentado
- README: cuenta de tests actualizada de 12 a 13, con la salida de ejemplo real.

---

## [2.1.7] - 2026-07-05

### ✨ Agregado
- Deduplicación de registros exactos del PDF de SIAFAR antes de las capas de reparación del ETL.

### 🐛 Corregido
- `js/main.js`: el listener de `pageshow` leía `timestamp` en vez de `ts` del cache en `sessionStorage` — la limpieza de cache vieja al volver con el botón "atrás" nunca se ejecutaba.
- `.gitignore`: línea `data/pami.xlsx.wrangler/` era dos patrones concatenados sin salto de línea — ninguno de los dos se aplicaba. Separados correctamente.
- `snapshot_semanal.py`: agrega timeout (30s) y manejo explícito de rate limit / errores de red en las llamadas a la API de GitHub — antes podían colgarse sin límite propio ni mensaje claro.

### ♻️ Refactor
- Unificadas `esValorCorrupto` (`filters.js`) y `esLaboratorioCorrupto` (`utils.js`) en una sola función — evita que las dos heurísticas diverjan con el tiempo.

### 🧹 Eliminado
- `pami.xlsx` y `scripts/__pycache__/` destrackeados de git (ya estaban en `.gitignore`, pero seguían en el índice desde antes de esa regla).

### 🔒 Seguridad
- Confirmado: `remedi.ar` y `www.remedi.ar` (GitHub Pages, fuente de verdad) entregan CSP, `X-Frame-Options: DENY` y el resto de los headers de seguridad vía Cloudflare Response Header Transform Rules, con ambos hosts en modo Proxied. Antes dependían de `_headers`, que GitHub Pages nunca procesó. Verificado en producción con `curl -I`.
- `Strict-Transport-Security: max-age=31536000` sumado a `_headers`.

### ♿ Accesibilidad
- Contraste de texto teal corregido a `--teal-dark` en 7 selectores de `style.css` — cumple WCAG AA (antes ~3.54:1, insuficiente).

### ⚙️ CI/CD
- `timeout-minutes` y `concurrency` en los 4 workflows — antes ninguno tenía límite de tiempo ni protección contra corridas superpuestas.

### 📝 Documentado
- README y `_headers`: se documenta que los headers de seguridad de producción se manejan vía Cloudflare, no vía `_headers` (exclusivo del mirror de Workers).

---

## [2.1.6] - 2026-07-04

### 🔒 Seguridad
- Bloque `permissions: contents: write` explícito en `maintenance-on.yml` — quedó afuera cuando se aplicó el mismo fix a `update_prices.yml` y `maintenance-off.yml` en la 2.1.4. Cierra el último de los tres workflows sin permisos acotados del `GITHUB_TOKEN`.
- Se versiona `.github/workflows/codeql.yml` (antes CodeQL corría vía configuración de la pestaña Security sin quedar reflejado en el código del repo). Cubre JS, Python y los propios workflows de Actions.
### 🔍 SEO
- `robots.txt` ya no bloquea `/data/` ni `/js/` — esos paths son
  necesarios para que Googlebot renderice el contenido real del sitio
  (el fetch a `medicamentos.json` desde `main.js`). El bloqueo previo
  probablemente resultaba en indexación de una página sin contenido
  de producto.
  ### 📝 Documentado
- `SECURITY.md` — política de reporte de vulnerabilidades y canal de contacto directo.

---

## [2.1.5] - 2026-07-02

### 🐛 Corregido
- `onLimpiar()` no reseteaba el checkbox visual de `#togglePami` — el estado interno del store sí se resetea vía `limpiarFiltros()`, pero el DOM quedaba desincronizado. Variante del bug C2 original, ahora del lado de la UI en vez del store
- Badge de versión del README y `package.json` desincronizados con el CHANGELOG (2.1.2 vs 2.1.4 real) — mismo problema que ya se había corregido en la 2.1.2, volvió a colarse

### 🧹 Eliminado
- Variable de módulo `todos` en `main.js`, que duplicaba `state.todos` del store — reemplazada por `getTodos()` en los 5 lugares donde se leía

### ♻️ Refactor
- `js/core/store.js` → `js/store.js` — la carpeta `core/` solo contenía ese archivo, anticipaba una estructura que nunca se materializó. Actualizado el import en `main.js` y la ruta cacheada en `sw.js`

### ♿ Mejorado
- Skip navigation link ("Saltar al contenido principal") — oculto por defecto, visible al recibir foco de teclado, salta a `#main-content`

### 🔒 Seguridad
- `admin.html` ya no carga Google Fonts externas — reemplazadas por system font stacks equivalentes, sin request externa y consistente con la CSP `font-src 'self'`

---

## [2.1.4] - 2026-07-02

### 🐛 Corregido
- `update_prices.yml` seguía agregando `data/pami.xlsx` y `data/droga_fixes.json` al commit en cada corrida pese a que la entrada 2.1.2 de este changelog ya lo daba por resuelto — el cambio no había quedado aplicado en el YAML. Ahora ninguno de los dos se toca en el paso de commit.

### 🔒 Seguridad
- Bloque `permissions: contents: write` explícito en `update_prices.yml` (hallazgo de CodeQL: el workflow no limitaba los permisos del `GITHUB_TOKEN`).

### ⚡ Mejorado
- `_build_re_lab_pegado()` ya no se reconstruye dos veces sobre el dataset completo en `pdf_to_json.py` — se cachea una sola vez y se reutiliza entre `extraer_presentacion_de_marca()` y `limpiar_dosis_residual_en_marca()`.
- Reemplazado `iterrows()` por `to_dict('records')`/`itertuples()` en los dos loops del crosswalk PAMI (`_build_pami_index()` y el fallback de dosis desde nombre de marca).

### 📝 Documentado retroactivamente
- `data/pami.xlsx` no se versiona en git desde algún punto entre 2.1.0 y 2.1.2 (fecha exacta no registrada en este changelog): se descarga fresco en cada corrida del ETL desde el portal de datos abiertos de PAMI (CKAN), con retry y backoff (`_descargar_pami()` en `pdf_to_json.py`), y está listado en `.gitignore`. Si la descarga falla, el crosswalk PAMI se omite sin bloquear el resto del pipeline. Esto corresponde al ítem de roadmap de la auditoría técnica "migrar pami.xlsx fuera de git → URL de descarga directa desde PAMI en cada corrida del ETL", que en los hechos ya estaba resuelto pero nunca quedó asentado acá.

---

## [2.1.2] - 2026-07-01

### 🐛 Corregido
- Badge de versión del README desincronizado con `package.json` (2.1.0 → 2.1.1)
- `import urllib.parse` duplicado en `snapshot_semanal.py` — consolidado en el bloque de imports del módulo
- `<nav class="footer-links">` estaba duplicado (dos aperturas, un cierre) — HTML inválido que además creaba un landmark de navegación repetido para lectores de pantalla

> ⚠️ **Nota de corrección (agregada 2026-07-02):** este release originalmente incluía un ítem "`update_prices.yml` agregaba `data/pami.xlsx` y `data/droga_fixes.json` al commit... (Corregido)" que resultó no estar aplicado en el código. Se movió a la entrada 2.1.4, que es donde el fix realmente se aplicó.

### 🔒 Seguridad
- `connect-src` de la CSP ahora incluye `https://www.googletagmanager.com`, además de `google-analytics.com` — gtag.js puede hacer llamadas de red a ambos dominios en runtime

### ♿ Mejorado
- `aria-hidden="true"` en los 21 SVGs decorativos de `index.html` (todos acompañan texto visible o labels ya existentes; se excluyó el sprite de `<symbol>`, ya oculto por `display:none`)
- `prefers-reduced-motion: reduce` en `@keyframes pulse` del `update-pill`, para respetar la preferencia de accesibilidad del sistema operativo

### 🧹 Eliminado
- `setTodos()` en `store.js` — alias sin ninguna referencia en el repo
- `ordenarPorPrecio()` en `filters.js` — alias legacy sin ninguna referencia en el repo

---

## [2.1.1] - 2026-06-29

### 🐛 Corregido
- Service Worker registrado en `index.html` — PWA operativa
- `limpiarFiltros()` ahora resetea `soloPami` correctamente
- Eliminado `window.normalizarLaboratorio` del namespace global en producción
- Doble `;;` en `utils.js` línea 24
- `admin.html` con `noindex, nofollow` para evitar indexación
- `bfcache`: reemplazado `location.reload()` por invalidación de caché por timestamp
- Badge de instalación PWA en footer con `beforeinstallprompt`

### ✨ Añadido
- `.gitignore` con `__pycache__/`, `*.pyc`, `.env`, `tests/debug_update_failed.txt`

---

## [2.1.0] - 2026-06-29

### ✨ Añadido
- Botón "Compartir" en cada tarjeta — menú nativo en mobile, copia al portapapeles en desktop
- Deep links por medicamento: URL única con hash `remedi.ar/#droga--marca--laboratorio--presentacion`
- Tarjeta destacada con glow teal y badge "Producto compartido" al abrir un link compartido
- Separador "Productos similares" entre tarjeta destacada y resultados por droga
- Hover glow en todas las tarjetas (desktop) y tap glow en mobile
- Evento `share` en GA4 con método (`native` / `clipboard`) e `item_id`
- Snapshot semanal de precios cada viernes en GitHub Releases (`historial-YYYY-MM`)
- `scripts/snapshot_semanal.py` — genera CSV con precios confiables (`vigencia_score ≥ 50`) y sube a GitHub Releases via API
- Badges de versión, estado del ETL, pytest, SSL, GA4, SIAFAR/COFA, PAMI, CSP, historial, share, idioma y país en README

### 🔧 Modificado
- `uiRenderer.js` — `renderPresentacion()` y `renderPrecios()` extraídos como funciones nombradas (sin IIFEs)
- `main.js` — soporte de hash en URL al cargar, manejo de medicamento destacado
- `style.css` — estilos de hover glow, tarjeta destacada, botón compartir y toast
- `update_prices.yml` — step de snapshot semanal los viernes
- README — badges reorganizados a la izquierda, secciones de compartir y snapshot

---

## [2.0.5] - 2026-06-28

### 🐛 Corregido
- Doble encoding UTF-8 en claves de `blacklist.json` — medicamentos con acentos no estaban siendo filtrados
- Query string `?v=2` inconsistente en importación de `uiRenderer.js` impedía cacheo del Service Worker
- `</footer>` sin apertura en `index.html`
- `git add index.html.bak` en `maintenance-off.yml` sobre archivo ya borrado
- Indentación YAML rota en `update_prices.yml`
- Escape de comilla simple faltante en `escapeHtml()` de `utils.js`

### ✨ Añadido
- `Access-Control-Allow-Origin: *` en `_headers` para el JSON público
- CSP movido de meta tag a header HTTP con hash SHA256 del script inline de GA
- Caché de dependencias pip (`cache: 'pip'`) en `setup-python@v5`
- `requirements.txt` al repositorio
- Íconos PNG 192×192 y 512×512 generados y agregados al manifest PWA
- `medicamentos.pretty.json` con `indent=2` generado en cada run
- 12 tests de sanidad con pytest (`tests/test_etl_sanidad.py`)
- `tests/conftest.py` — genera `debug_update_failed.txt` si algún test falla
- SSL reemplazado por `certifi` en descarga del PDF de SIAFAR
- Service Worker bumpeado a `remediar-v3`
- Bloque de auto-instalación de pymupdf eliminado del ETL

### ⚡ Mejorado
- TTL de caché de datos reducido de 4 a 2 horas
- README completamente reescrito con diagramas Mermaid, referencia de componentes y documentación de workflows

---

## [2.0.0] - 2026-06-22

### ✨ Añadido
- Toggle "Solo PAMI" en filtros con chip de cobertura y copago estimado
- Modo precio PAMI: muestra copago como precio principal y PVP como referencia
- `store.js` — estado centralizado con patrón pub/sub
- `getResultadosSinFiltros()` para dropdowns contextuales correctos
- Panel admin de outliers con lista negra
- Normalización de laboratorios truncados en frontend (`normalizarLaboratorio()`)
- Open Graph y Twitter Cards en `index.html`
- Service Worker y Web App Manifest (PWA)
- Sitemap.xml generado automáticamente
- Página de mantenimiento con countdown y workflows `maintenance-on/off`
- `og-image.png` para shares en redes sociales
- `package.json` con metadatos del proyecto
- Workflow de precios con horario `30 13,21 * * 1-5` (10:30 y 18:30 AR)

### 🔧 Modificado
- Layout de resultados migrado de grid a flex
- Ancho máximo del contenedor ampliado a 1024px
- robots.txt simplificado con crawl-delay para bots agresivos
- README actualizado con arquitectura real del frontend y ETL

---

## [Sin versión formal] - 2026-06-15 a 2026-06-21

### ETL — Parser de presentaciones
- Chips de presentación (`pres_forma`, `pres_dosis`, `pres_unidad`, `pres_cantidad`)
- `presentaciones_debug.csv` generado en cada run
- Parser de formas farmacéuticas con 60+ entradas en `FORMAS_MAP`
- Soporte de formas vaginales, viales y formas especiales
- Extracción de dosis desde nombre de marca (`pres_*` rescatados de marca)
- Fallback de dosis desde PAMI

### ETL — Correcciones de estructura del PDF
- Capa 5: `extraer_presentacion_de_marca()` con pre-limpieza en 3 pasos
- Capa 5b: `reparar_presentacion_desplazada()` con 3 sub-patrones
- Capa 5c: `limpiar_dosis_residual_en_marca()`
- `_build_re_lab_pegado()` dinámico por dataset
- `_RE_FORMA_PEGADA` y `_RE_TOKEN_DUPLICADO`
- Revert de pipeline modular — vuelta a script monolítico

### Frontend
- Filtrado sin texto de búsqueda (solo por dropdowns)
- Dropdowns contextuales actualizados según resultados actuales
- Chips de presentación en tarjetas

---

## [Sin versión formal] - 2026-06-04 a 2026-06-14

### ETL — Pipeline de normalización
- Capa 0: `reparar_droga_faltante()` — 461 registros con droga+marca fusionadas
- Capa 3: `reparar_denver()` — Denver Farma con marca+presentacion fusionadas
- Capa 4: `reparar_marca_desplazada()` — marca con dígito inicial
- Capa 6: `crosswalk_pami()` — cruce con `data/pami.xlsx`
- Capa 7: `aplicar_droga_fixes()` — correcciones manuales desde `droga_fixes.json`
- Blacklist de precios obsoletos (`data/blacklist.json`)
- Detección de outliers con IQR + `vigencia_score` (0-100)
- `outlier_report.json` generado en cada run
- `data/pami.xlsx` — vademécum PAMI para crosswalk
- `data/droga_fixes.json` — correcciones manuales editables

### ETL — Correcciones menores
- Capa 2: `rescatar_laboratorios()` — lab "Desconocido" recuperado desde presentacion
- PR fixes de laboratorios desplazados, Denver Farma, presentación desplazada

### Frontend
- Cobertura PAMI en tarjetas (`pami_cobertura`)
- Botón limpiar búsqueda
- `btn-limpiar` con estilos

---

## [Sin versión formal] - 2026-05-27 a 2026-06-03

### Inicio del proyecto
- Commit inicial con refactor completo
- Parser PDF con PyMuPDF (reemplazó tabula-py y Camelot)
- Script directo PDF → JSON (sin CSV intermedio)
- Workflow GitHub Actions con cron
- CNAME para dominio `remedi.ar`
- Cloudflare Pages como hosting principal, GitHub Pages como backup
- `_headers` con headers de seguridad y estrategia de caché
- SEO básico: meta tags, JSON-LD, BreadcrumbList
- Landings SEO por principio activo (luego eliminadas)
- Sitemap.xml
- `privacidad.html` y `terminos.html`
- `index.html` SPA con búsqueda, filtros y ordenamiento
- Índice invertido de prefijos en `searchEngine.js`
- Ranking por relevancia + vigencia + precio
- Debounce de 250ms en búsqueda
- `sessionStorage` con TTL para caché de datos

---

## Próximos pasos

- Filtro por forma farmacéutica en la UI (`pres_forma`)
- Visualización de historial de precios en el frontend
- Integración con API REST de ANMAT (trámite en curso — respuesta esperada 10/07/2026)
- IOMA como segunda fuente de crosswalk (pendiente acceso al dataset)
- Dashboard estadístico de variación de precios
- Instagram con contenido generado automáticamente