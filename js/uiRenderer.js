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

function renderPresentacion(med) {
    // Preferir campos pre-parseados del ETL (pres_forma/dosis/unidad/cantidad)
    // y caer al parser JS solo si no están disponibles.
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

function renderizarTarjeta(med, soloPami = false) {
    const esSosp = (med.vigencia_score ?? 100) < 50;

    return `
        <article class="tarjeta${esSosp ? ' tarjeta-sospechosa' : ''}">
            ${badgeVigencia(med)}
            <div class="tarjeta-header">
                <h3 class="marca-tarjeta">${escapeHtml(med.marca || 'N/A')}</h3>
                <span class="laboratorio-badge">${escapeHtml(normalizarLaboratorio(med.laboratorio) || "N/A")}</span>
            </div>
            <div class="fila-tabla">
                <span class="celda etiqueta">
                    <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24">
                        <path d="M2 15c6.667-6 13.333 0 20-6"/><path d="M2 9c6.667 6 13.333 0 20 6"/>
                    </svg>
                    Principio activo
                </span>
                <span class="celda valor" style="text-transform:uppercase">${escapeHtml(med.droga || 'N/A')}</span>
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
        </article>`;
}

export function mostrarResultados(lista, termino = '', soloPami = false) {
    const cont = document.getElementById('resultados');
    const ctr  = document.getElementById('contador');
    if (!cont) return;

    if (!lista?.length) {
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

    const MAX    = 300;
    const total  = lista.length;
    const suspCount = lista.filter(m => (m.vigencia_score ?? 100) < 50).length;
    const unidad = total === 1 ? 'resultado' : 'resultados';

    let ctrHtml = total > MAX
        ? `<strong>${total.toLocaleString('es-AR')} ${unidad}</strong> (mostrando los primeros ${MAX})`
        : `<strong>${total.toLocaleString('es-AR')} ${unidad}</strong>`;

    if (suspCount > 0) {
        ctrHtml += ` <span class="ctr-sospechosos">(${suspCount} con precio a verificar, al final)</span>`;
    }

    ctr.innerHTML = ctrHtml;
    cont.innerHTML = lista.slice(0, MAX).map(m => renderizarTarjeta(m, soloPami)).join('');
    _ocultarChip();
}
