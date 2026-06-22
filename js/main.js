// js/main.js — Orquestador principal
import { cargarDatos }                            from './dataLoader.js';
import { construirIndice, buscar }                from './searchEngine.js';
import { aplicarFiltros, ordenar }               from './filters.js';
import {
    mostrarSkeleton, mostrarMensajeInicial, mostrarError,
    mostrarResultados, cargarOpcionesFiltros, actualizarFechaEnFooter,
} from './uiRenderer.js?v=2';
import {
    getState, getResultados, getFiltros, getTodos,
    setFiltroTexto, setFiltroPresentacion,
    setFiltroLaboratorio, setFiltroOrden, setSoloPami, limpiarFiltros,
    setLoading, setError, initStore, suscribirse,
} from './core/store.js';

let todos   = [];
let timeout = null;

// ── Suscripción al store ───────────────────────────────────────────────
suscribirse((state) => {
    const { resultados, filtros } = state;

    const hayTexto  = filtros.texto && filtros.texto.trim().length >= 2;
    const hayFiltro = !!(filtros.presentacion || filtros.laboratorio);

    if (!hayTexto && !hayFiltro) {
        mostrarMensajeInicial();
        return;
    }

    // Actualizar dropdowns con las opciones disponibles en los resultados actuales
    // Esto permite que al buscar "ibuprofeno" solo aparezcan las presentaciones
    // y laboratorios que existen para ese medicamento, no todos los del dataset
    cargarOpcionesFiltros(resultados.length > 0 ? resultados : todos, filtros);

    mostrarResultados(resultados, filtros.texto, filtros.soloPami);
});

// ── Handlers ──────────────────────────────────────────────────────────
function onInput() {
    clearTimeout(timeout);
    const q = document.getElementById('buscador').value.trim();

    // Mostrar/ocultar botón limpiar
    const btnLimpiar = document.getElementById('btnLimpiar');
    if (btnLimpiar) btnLimpiar.style.display = q ? 'flex' : 'none';

    if (!q || q.length < 2) {
        const hayFiltro = !!(document.getElementById('filtroPresentacion')?.value || document.getElementById('filtroLaboratorio')?.value);
        if (!hayFiltro) mostrarMensajeInicial();
        setFiltroTexto('');
        _actualizarURL('');
        return;
    }

    timeout = setTimeout(() => {
        setFiltroTexto(q);
        _actualizarURL(q);
    }, 250);
}

function onBuscar() {
    clearTimeout(timeout);
    const q = document.getElementById('buscador').value.trim();
    setFiltroTexto(q);
    _actualizarURL(q);
}

function onFiltroPresentacionChange() {
    setFiltroPresentacion(document.getElementById('filtroPresentacion')?.value || '');
}

function onFiltroLaboratorioChange() {
    setFiltroLaboratorio(document.getElementById('filtroLaboratorio')?.value || '');
}

function onOrdenChange() {
    setFiltroOrden(document.getElementById('ordenPrecio')?.value || 'relevancia');

    document.getElementById('togglePami')?.addEventListener('change', e => {
        setSoloPami(e.target.checked);
    });
}

function onLimpiar() {
    const ids = ['buscador', 'filtroPresentacion', 'filtroLaboratorio'];
    ids.forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
    const sel = document.getElementById('ordenPrecio');
    if (sel) sel.value = 'relevancia';

    limpiarFiltros();
    mostrarMensajeInicial();
    cargarOpcionesFiltros(getTodos());
    _actualizarURL('');

    // Ocultar botón limpiar
    const btnLimpiar = document.getElementById('btnLimpiar');
    if (btnLimpiar) btnLimpiar.style.display = 'none';

    // Foco al buscador
    document.getElementById('buscador')?.focus();
}

// ── Persistencia URL ──────────────────────────────────────────────────
function _actualizarURL(q) {
    const url = new URL(window.location.href);
    if (q) url.searchParams.set('q', q);
    else   url.searchParams.delete('q');
    history.replaceState(null, '', url.toString());
}

// ── Botón scroll-to-top ───────────────────────────────────────────────
function _initScrollTop() {
    // Inyectar botón si no existe en el HTML
    let btn = document.getElementById('btnTop');
    if (!btn) {
        btn = document.createElement('button');
        btn.id          = 'btnTop';
        btn.innerHTML   = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5"><polyline points="18 15 12 9 6 15"/></svg>`;
        btn.setAttribute('aria-label', 'Volver arriba');
        document.body.appendChild(btn);
    }
    window.addEventListener('scroll', () => {
        btn.classList.toggle('visible', window.scrollY > 300);
    }, { passive: true });
    btn.addEventListener('click', () => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });
}

// ── Init ──────────────────────────────────────────────────────────────
async function init() {
    mostrarSkeleton();
    setLoading(true);
    _initScrollTop();

    try {
        const data = await cargarDatos();
        todos = data.medicamentos || [];
        construirIndice(todos);
        initStore(todos);
        cargarOpcionesFiltros(todos);
        actualizarFechaEnFooter(data.fecha);

        // Restaurar búsqueda desde URL
        const q = new URLSearchParams(window.location.search).get('q');
        if (q && q.length >= 2) {
            document.getElementById('buscador').value = q;
            setFiltroTexto(q);
        } else {
            mostrarMensajeInicial();
        }

        setLoading(false);
    } catch (err) {
        console.error(err);
        const msg = 'No se pudieron cargar los datos. Intentá recargar la página.';
        setError(msg);
        mostrarError(msg);
        return;
    }

    // Event listeners
    document.getElementById('buscador')?.addEventListener('input', onInput);
    document.getElementById('buscador')?.addEventListener('keydown', e => {
        if (e.key === 'Enter') onBuscar();
    });
    document.getElementById('btnBuscar')?.addEventListener('click', onBuscar);
    document.getElementById('btnLimpiar')?.addEventListener('click', onLimpiar);
    document.getElementById('filtroPresentacion')?.addEventListener('change', onFiltroPresentacionChange);
    document.getElementById('filtroLaboratorio')?.addEventListener('change', onFiltroLaboratorioChange);
    document.getElementById('ordenPrecio')?.addEventListener('change', onOrdenChange);
}

init();

// Forzar recarga cuando la página se recupera del bfcache
window.addEventListener('pageshow', (event) => {
    if (event.persisted) {
        console.log('Página restaurada desde bfcache, recargando...');
        location.reload();
    }
});