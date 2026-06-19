// js/core/store.js — Estado Centralizado.
// Usa searchEngine para búsqueda real (índice invertido + ranking).
// Sin texto → resultados vacíos (mensaje inicial), no lista completa.

import { buscar } from '../searchEngine.js';
import { aplicarFiltros, ordenar } from '../filters.js';

// ── Estado inicial ────────────────────────────────────────────────────
let state = {
    todos:      [],
    resultados: [],

    filtros: {
        texto:        '',
        presentacion: '',
        laboratorio:  '',
        orden:        'relevancia',
    },

    estaCargando: true,
    error:        null,

    filtrosDisponibles: {
        presentaciones: [],
        laboratorios:   [],
    },
};

// ── Suscriptores ──────────────────────────────────────────────────────
const suscriptores = [];

export function suscribirse(fn) {
    suscriptores.push(fn);
}

function notificar() {
    suscriptores.forEach(fn => fn(state));
}

// ── Getters ───────────────────────────────────────────────────────────
export function getState()     { return { ...state }; }
export function getFiltros()   { return { ...state.filtros }; }
export function getResultados(){ return [...state.resultados]; }
export function getTodos()     { return [...state.todos]; }

// ── Recalcular resultados ─────────────────────────────────────────────
function recalcularResultados() {
    const { texto, presentacion, laboratorio, orden } = state.filtros;
    const hayTexto  = texto && texto.trim().length >= 2;
    const hayFiltro = !!(presentacion || laboratorio);

    // Sin texto ni filtro: no mostrar nada (mensaje inicial en UI)
    if (!hayTexto && !hayFiltro) {
        state.resultados = [];
        return;
    }

    // 1. Búsqueda: si hay texto usar el índice; si no, partir del dataset completo
    let resultados = hayTexto ? buscar(texto) : [...state.todos];

    // 2. Filtros adicionales
    resultados = aplicarFiltros(resultados, presentacion, laboratorio, true);

    // 3. Ordenamiento explícito si no es "relevancia"
    if (orden !== 'relevancia') {
        resultados = ordenar(resultados, orden);
    }

    state.resultados = resultados;
}

// ── Acciones ──────────────────────────────────────────────────────────
export function setFiltroTexto(texto) {
    state.filtros.texto = texto;
    recalcularResultados();
    notificar();
}

export function setFiltroPresentacion(presentacion) {
    state.filtros.presentacion = presentacion;
    recalcularResultados();
    notificar();
}

export function setFiltroLaboratorio(laboratorio) {
    state.filtros.laboratorio = laboratorio;
    recalcularResultados();
    notificar();
}

export function setFiltroOrden(orden) {
    state.filtros.orden = orden;
    recalcularResultados();
    notificar();
}

export function limpiarFiltros() {
    state.filtros = { texto: '', presentacion: '', laboratorio: '', orden: 'relevancia' };
    state.resultados = [];
    notificar();
}

export function setLoading(loading) {
    state.estaCargando = loading;
    notificar();
}

export function setError(error) {
    state.error        = error;
    state.estaCargando = false;
    notificar();
}

// ── Inicialización ────────────────────────────────────────────────────
export function initStore(medicamentos) {
    state.todos            = medicamentos;
    state.resultados       = [];   // ← vacío: muestra mensaje inicial
    state.estaCargando     = false;
    state.filtrosDisponibles = _extraerFiltros(medicamentos);
    notificar();
}

// Alias para compatibilidad con main.js
export function setTodos(medicamentos) {
    state.todos = medicamentos;
    state.filtrosDisponibles = _extraerFiltros(medicamentos);
    recalcularResultados();
    notificar();
}

// ── Privado ───────────────────────────────────────────────────────────
function _extraerFiltros(meds) {
    const presentaciones = new Set();
    const laboratorios   = new Set();
    for (const m of meds) {
        if (m.presentacion) presentaciones.add(m.presentacion);
        if (m.laboratorio && m.laboratorio !== 'Desconocido') laboratorios.add(m.laboratorio);
    }
    return {
        presentaciones: [...presentaciones].sort(),
        laboratorios:   [...laboratorios].sort(),
    };
}