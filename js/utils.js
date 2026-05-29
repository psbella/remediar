// utils.js

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
}

function esLaboratorioCorrupto(valor) {
    if (!valor) return true;
    const limpio = valor.toString().trim();
    
    const blacklist = [
        "20/134mg compx30+capsx30Teva argentina",
        "200/10mg comp.x60(30+30) Craveri",
        "35.486,17", "37.532,00", "41.931,16", "42.601,18", "9.938,36"
    ];
    if (blacklist.includes(limpio)) return true;
    
    if (/^\d/.test(limpio) && /mg|ml|g|ui|comp|tableta|capsula/i.test(limpio)) return true;
    
    const numeros = (limpio.match(/\d+/g) || []).length;
    if (numeros >= 2) return true;
    
    return false;
}

function corregirLaboratorio(nombre) {
    if (!nombre) return nombre;
    
    const correcciones = {
        "Abbvie (ex Alle": "Abbvie (ex Alle) Recalcine",
        "Alef Medical Ar": "Alef Medical Argentina",
        "Bausch & Lomb A": "Bausch & Lomb Argentina",
        "Baxter Argentin": "Baxter Argentina",
        "Biopas Argentin": "Biopas Argentina",
        "Boehringer Inge": "Boehringer Ingelheim",
        "Bristol": "Bristol-Myers Squibb",
        "Celnova Argenti": "Celnova Argentina",
        "Géminis Farmacé": "Géminis Farmacéutica",
        "Johnson & Johns": "Johnson & Johnson",
        "Lab Internacion": "Laboratorio Internacional",
        "Laboratorio Gra": "Laboratorio Grafo",
        "Laboratorio Mer": "Laboratorio Merck",
        "Laboratorio Val": "Laboratorio Valent",
        "Laboratorios Be": "Laboratorios Beta",
        "Laboratorios Fe": "Laboratorios Ferrer",
        "Laboratorios Ta": "Laboratorios Tuteur",
        "Lancaster Pharm": "Lancaster Pharma",
        "Microsules Arg.": "Microsules Argentina",
        "MSD Argentina S": "MSD Argentina",
        "Opella Healthca": "Opella Healthcare",
        "Organon Arg.": "Organon Argentina",
        "Pharmalep S.A": "Pharmalep S.A.",
        "Pierre Fabre Mé": "Pierre Fabre Médicament",
        "Pierre Fabre On": "Pierre Fabre Oncologie",
        "Procter & Gambl": "Procter & Gamble",
        "Reckitt Benckis": "Reckitt Benckiser",
        "Sanofi Pasteur": "Sanofi Pasteur Argentina",
        "Takeda Argentin": "Takeda Argentina",
        "Vannier - Grune": "Vannier - Grünenthal"
    };
    
    return correcciones[nombre] || nombre;
}

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
