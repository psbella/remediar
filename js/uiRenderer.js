// uiRenderer.js — Renderizado con badges de vigencia y escape seguro.
import { formatearPrecio, escapeHtml, extraerFiltros, normalizarLaboratorio, parsearPresentacion } from './utils.js';

export function mostrarSkeleton() {
    const el = document.getElementById('resultados');
    if (!el || el.querySelector('.skeleton-card')) return;
    el.innerHTML = Array.from({length: 5}, () => `
        <div class="skeleton-card">
            <div class="sk sk-title"></div>
            <div class="sk sk-line"></div>
            <div class="sk sk-short"></div>
            <div class="sk sk-price"></div>
        </div>`).join('');
}

export function mostrarMensajeInicial() {
    const el = document.getElementById('resultados');
    if (!el) return;
    el.innerHTML = `
        <div class="mensaje-inicial">
            <svg width="36" height="36" fill="none" stroke="#c8d8d8" stroke-width="1.5" viewBox="0 0 24 24">
                <circle cx="10" cy="10" r="7"/><line x1="15" y1="15" x2="21" y2="21"/>
            </svg>
            <p>Buscá por nombre comercial, principio activo o laboratorio</p>
        </div>`;
    document.getElementById('contador').innerHTML = '';
    _ocultarChip();
}

export function mostrarError(msg) {
    const el = document.getElementById('resultados');
    if (!el) return;
    el.innerHTML = `
        <div class="mensaje-inicial">
            <svg width="32" height="32" fill="none" stroke="#e53935" stroke-width="1.5" viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="10"/>
                <line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            <p>${escapeHtml(msg)}</p>
            <button id="btnReintentar" class="btn-reintentar">Reintentar</button>
        </div>`;
    document.getElementById('contador').innerHTML = '';
    _ocultarChip();
}

export function cargarOpcionesFiltros(medicamentos, filtrosActivos = {}) {
    const { presentaciones, laboratorios } = extraerFiltros(medicamentos);
    const selP = document.getElementById('filtroPresentacion');
    const selL = document.getElementById('filtroLaboratorio');

    if (selP) {
        const presActual = filtrosActivos.presentacion || selP.value;
        selP.innerHTML = '<option value="">Presentación: Todas</option>';
        presentaciones.forEach(p => {
            const o = document.createElement('option');
            o.value = p;
            o.textContent = p.length > 60 ? p.slice(0,60)+'…' : p;
            if (p === presActual) o.selected = true;
            selP.appendChild(o);
        });
    }

    if (selL) {
        const labActual = filtrosActivos.laboratorio || selL.value;
        selL.innerHTML = '<option value="">Laboratorio: Todos</option>';
        laboratorios.forEach(l => {
            const o = document.createElement('option');
            o.value = l; o.textContent = l;
            if (l === labActual) o.selected = true;
            selL.appendChild(o);
        });
    }
}

export function actualizarFechaEnFooter(fecha) {
    const ids = ['fecha-actualizacion', 'fecha-actualizacion-footer'];
    ids.forEach(id => {
        const el = document.getElementById(id);
        if (!el) return;
        if (!fecha) { el.textContent = ''; return; }
        try {
            const d   = new Date(fecha);
            const pad = n => String(n).padStart(2, '0');
            el.textContent = `${pad(d.getDate())}/${pad(d.getMonth()+1)}/${d.getFullYear()} ${pad(d.getHours())}:${pad(d.getMinutes())} hs`;
        } catch { el.textContent = fecha; }
    });
}

export function actualizarSortChip(texto) {
    const chip  = document.getElementById('sortChip');
    const label = document.getElementById('sortChipLabel');
    if (!chip || !label) return;
    if (!texto) { chip.classList.remove('visible'); return; }
    label.textContent = texto;
    chip.classList.add('visible');
}

function _ocultarChip() {
    document.getElementById('sortChip')?.classList.remove('visible');
}

// ── Hash de medicamento para compartir ────────────────────────────────
export function hashMedicamento(med) {
    const slug = s => (s || '').toLowerCase()
        .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
        .replace(/\s+/g, '-')
        .replace(/[^a-z0-9-]/g, '');
    return `${slug(med.droga)}--${slug(med.marca)}--${slug(med.laboratorio)}--${slug(med.presentacion)}`;
}

export function buscarPorHash(todos, hash) {
    return todos.find(m => hashMedicamento(m) === hash) || null;
}

// ── Compartir ─────────────────────────────────────────────────────────
export async function compartirMedicamento(med) {
    const hash = hashMedicamento(med);
    const url  = `${location.origin}${location.pathname}#${hash}`;
    const text = `${med.marca} (${med.droga}) — ${formatearPrecio(med.precio)} | remedi.ar`;

    // Tracker GA4
    if (typeof gtag === 'function') {
        gtag('event', 'share', {
            method: navigator.share ? 'native' : 'clipboard',
            content_type: 'medicamento',
            item_id: `${med.droga}--${med.marca}`,
        });
    }

    if (navigator.share) {
        try {
            await navigator.share({ title: med.marca, text, url });
            return;
        } catch (e) {
            if (e.name === 'AbortError') return;
        }
    }

    try {
        await navigator.clipboard.writeText(url);
        _mostrarToast('¡Link copiado!');
    } catch {
        _mostrarToast('No se pudo copiar el link');
    }
}

function _mostrarToast(msg) {
    let toast = document.getElementById('share-toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'share-toast';
        document.body.appendChild(toast);
    }
    toast.textContent = msg;
    toast.classList.add('visible');
    clearTimeout(toast._timeout);
    toast._timeout = setTimeout(() => toast.classList.remove('visible'), 2000);
}

// ── SVG íconos ────────────────────────────────────────────────────────
const SVG_SHARE = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/>
    <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>
</svg>`;

const SVG_COPY = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
</svg>`;

function renderBotonCompartir() {
    const tieneShare = !!navigator.share;
    const icono = tieneShare ? SVG_SHARE : SVG_COPY;
    const texto = tieneShare ? 'Compartir' : 'Copiar link';
    return `<button class="btn-compartir" aria-label="Compartir medicamento">
        ${icono}<span>${texto}</span>
    </button>`;
}

// ── Presentación y precios ────────────────────────────────────────────
function renderPresentacion(med) {
    const p = (med.pres_forma || med.pres_dosis)
        ? { forma: med.pres_forma || null, dosis: med.pres_dosis ? `${med.pres_dosis}${med.pres_unidad ? ' ' + med.pres_unidad : ''}` : null, cantidad: med.pres_cantidad || null }
        : parsearPresentacion(med.presentacion);
    if (!p) return `<span class="celda valor">${escapeHtml(med.presentacion || 'N/A')}</span>`;
    return `<div class="pres-tabla">
        ${p.dosis    ? `<span class="pres-chip pres-dosis">${escapeHtml(p.dosis)}</span>` : ''}
        ${p.forma    ? `<span class="pres-chip pres-forma">${escapeHtml(p.forma)}</span>` : ''}
        ${p.cantidad ? `<span class="pres-chip pres-cant">× ${escapeHtml(p.cantidad)}</span>` : ''}
    </div>`;
}

function renderPrecios(med, soloPami) {
    const copago = med.pami_cobertura
        ? Math.round(med.precio * (1 - med.pami_cobertura / 100))
        : null;
    if (soloPami && copago != null) {
        return `
        <span class="precio-publico precio-pami">${formatearPrecio(copago)}</span>
        <span class="precio-sin-cobertura">Precio sin cobertura ${formatearPrecio(med.precio)}</span>`;
    }
    return `
    <span class="precio-publico">${formatearPrecio(med.precio)}</span>
    ${med.pami_cobertura ? `
    <div class="pami-info">
        <span class="pami-chip">Cobertura PAMI ${med.pami_cobertura}% · ${formatearPrecio(copago)}</span>
    </div>` : ''}`;
}

// ── Tarjeta ───────────────────────────────────────────────────────────
function renderizarTarjeta(med, soloPami = false, destacada = false) {
    const esSosp = (med.vigencia_score ?? 100) < 50;
    const clases = [
        'tarjeta',
        esSosp    ? 'tarjeta-sospechosa' : '',
        destacada ? 'tarjeta-destacada'  : '',
    ].filter(Boolean).join(' ');

    return `
        <article class="${clases}" data-hash="${escapeHtml(hashMedicamento(med))}">
            ${destacada ? '<div class="badge-compartida">Producto compartido</div>' : ''}
            ${badgeVigencia(med)}
            <div class="tarjeta-header">
                <h3 class="marca-tarjeta">${escapeHtml(med.marca || 'N/A')}</h3>
                <span class="laboratorio-badge">${escapeHtml(normalizarLaboratorio(med.laboratorio) || 'N/A')}</span>
            </div>
            <div class="fila-tabla">
                <span class="celda etiqueta">
                    <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24">
                        <path d="M2 15c6.667-6 13.333 0 20-6"/><path d="M2 9c6.667 6 13.333 0 20 6"/>
                    </svg>
                    Principio activo
                </span>
                <span class="celda valor uppercase">${escapeHtml(med.droga || 'N/A')}</span>
            </div>
            <div class="fila-tabla fila-presentacion">
                <span class="celda etiqueta">
                    <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24">
                        <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
                    </svg>
                    Presentación
                </span>
                ${renderPresentacion(med)}
            </div>
            <div class="fila-precios">
                ${renderPrecios(med, soloPami)}
            </div>
            <div class="tarjeta-footer">
                ${renderBotonCompartir()}
            </div>
        </article>`;
}

// ── Render principal ──────────────────────────────────────────────────
export function mostrarResultados(lista, termino = '', soloPami = false, medDestacada = null) {
    const cont = document.getElementById('resultados');
    const ctr  = document.getElementById('contador');
    if (!cont) return;

    if (!lista?.length && !medDestacada) {
        cont.innerHTML = `
            <div class="mensaje-inicial">
                <svg width="32" height="32" fill="none" stroke="#c8d8d8" stroke-width="1.5" viewBox="0 0 24 24">
                    <circle cx="10" cy="10" r="7"/><line x1="15" y1="15" x2="21" y2="21"/>
                </svg>
                <p>No se encontraron resultados${termino ? ` para "<strong>${escapeHtml(termino)}</strong>"` : ''}.</p>
            </div>`;
        ctr.innerHTML = '0 resultados';
        _ocultarChip();
        return;
    }

    const MAX       = 300;
    const total     = lista.length;
    const suspCount = lista.filter(m => (m.vigencia_score ?? 100) < 50).length;
    const unidad    = total === 1 ? 'resultado' : 'resultados';

    let ctrHtml = total > MAX
        ? `<strong>${total.toLocaleString('es-AR')} ${unidad}</strong> (mostrando los primeros ${MAX})`
        : `<strong>${total.toLocaleString('es-AR')} ${unidad}</strong>`;

    if (suspCount > 0) {
        ctrHtml += ` <span class="ctr-sospechosos">(${suspCount} con precio a verificar, al final)</span>`;
    }

    ctr.innerHTML = ctrHtml;

    const hashDest    = medDestacada ? hashMedicamento(medDestacada) : null;
    const similares   = hashDest ? lista.filter(m => hashMedicamento(m) !== hashDest) : lista;
    const htmlDest    = medDestacada ? renderizarTarjeta(medDestacada, soloPami, true) : '';
    const separador   = medDestacada && similares.length
        ? '<div class="separador-similares"><span>Productos similares</span></div>'
        : '';

    cont.innerHTML = htmlDest + separador + similares.slice(0, MAX).map(m => renderizarTarjeta(m, soloPami)).join('');

    _ocultarChip();
}

// Badge vigencia (definición movida después de las funciones que la usan)
function badgeVigencia(med) {
    const flags = med.flags || [];
    const score = med.vigencia_score ?? 100;

    if (score >= 70 && flags.length === 0) return '';

    let msg = '';
    let cls = '';

    if (flags.includes('precio_obsoleto') && score < 50) {
        msg = '⚠ Precio posiblemente desactualizado';
        cls = 'badge-sospechoso';
    } else if (flags.includes('precio_bajo') && score < 50) {
        msg = '⚠ Precio bajo - verificar';
        cls = 'badge-sospechoso';
    } else if (flags.includes('precio_bajo')) {
        msg = '⚠ Precio bajo';
        cls = 'badge-verificar';
    } else if (flags.includes('precio_sospechoso')) {
        msg = '⚠ Precio a verificar';
        cls = 'badge-verificar';
    } else {
        return '';
    }

    return `<div class="vigencia-badge ${escapeHtml(cls)}" title="Score: ${score}/100 — Flags: ${escapeHtml(flags.join(', '))}">
        ${escapeHtml(msg)}
    </div>`;
}
