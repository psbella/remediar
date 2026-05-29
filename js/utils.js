// utils.js - Utilidades y normalización
export function normalizar(texto) {
    if (!texto) return '';
    return texto.toLowerCase()
        .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
        .trim();
}

export function formatearPrecio(precio) {
    if (precio == null || isNaN(precio)) return 'N/D';
    return precio.toLocaleString('es-AR', {
        style: 'currency', currency: 'ARS',
        minimumFractionDigits: 2, maximumFractionDigits: 2
    });
}

export function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

export function calcularAhorroPami(pub, pami) {
    if (!pub || !pami || pub <= 0 || pami >= pub) return null;
    return Math.round(((pub - pami) / pub) * 100).toString();
}

// ============================================================
// NORMALIZACIÓN DE LABORATORIOS TRUNCADOS
// ============================================================
const LAB_CORRECCIONES = {
    "abbvie (ex alle": "Abbvie / Recalcine",
    "alef medical ar": "Alef Medical Argentina",
    "bausch & lomb a": "Bausch & Lomb Argentina",
    "baxter argentin": "Baxter Argentina",
    "biopas argentin": "Biopas Argentina",
    "boehringer inge": "Boehringer Ingelheim",
    "bristol": "Bristol-Myers Squibb",
    "celnova argenti": "Celnova Argentina",
    "johnson & johns": "Johnson & Johnson",
    "lab internacion": "Laboratorio Internacional",
    "laboratorio gra": "Laboratorio Grafo",
    "laboratorio mer": "Laboratorio Merck",
    "laboratorio val": "Laboratorio Valent",
    "laboratorios be": "Laboratorios Beta",
    "laboratorios fe": "Laboratorios Ferrer",
    "laboratorios ta": "Laboratorios Tuteur",
    "lancaster pharm": "Lancaster Pharma",
    "microsules arg.": "Microsules Argentina",
    "msd argentina s": "MSD Argentina",
    "opella healthca": "Opella Healthcare",
    "organon arg.": "Organon Argentina",
    "pharmalep s.a": "Pharmalep S.A.",
    "pierre fabre me": "Pierre Fabre Médicament",
    "pierre fabre on": "Pierre Fabre Oncologie",
    "procter & gambl": "Procter & Gamble",
    "reckitt benckis": "Reckitt Benckiser",
    "sanofi pasteur": "Sanofi Pasteur Argentina",
    "takeda argentin": "Takeda Argentina",
    "vannier - grune": "Vannier - Grünenthal",
};

export function normalizarLaboratorio(lab) {
    if (!lab) return "Desconocido";
    const clave = lab.toLowerCase().trim().replace(/\.$/, '');
    return LAB_CORRECCIONES[clave] || lab;
}

// ============================================================
// EXTRACCIÓN DE FILTROS (usa normalizarLaboratorio)
// ============================================================
export function extraerFiltros(medicamentos) {
    const pres = new Set();
    const labs = new Set();
    for (const m of medicamentos) {
        if (m.presentacion) pres.add(m.presentacion);
        if (m.laboratorio && m.laboratorio !== "Desconocido") {
            labs.add(normalizarLaboratorio(m.laboratorio));
        }
    }
    return {
        presentaciones: [...pres].sort(),
        laboratorios: [...labs].sort()
    };
}

// Exponer globalmente para debugging
if (typeof window !== 'undefined') {
    window.normalizarLaboratorio = normalizarLaboratorio;
}
