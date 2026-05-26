// filters.js — Filtros y ordenamiento con soporte de vigencia

function esValorCorrupto(valor) {
    if (!valor) return true;
    const limpio = valor.toString().trim();
    if (/^[\d\.,\$]+$/.test(limpio)) return true;
    if (/mg|ml|compr?|comp\.|rec\.|x\s?\d+|susp\.|sol\.|gts\.|crema|ung\.|iny\./i.test(limpio)) return true;
    if (/^\d+\s*(mg|ml|g|ui)/i.test(limpio)) return true;
    return false;
}

export function aplicarFiltros(lista, presentacion = '', laboratorio = '', mostrarSospechosos = true) {
    let r = [...lista];
    if (presentacion) r = r.filter(m => m.presentacion === presentacion);
    if (laboratorio) {
        r = r.filter(m => {
            const lab = m.laboratorio || '';
            return !esValorCorrupto(lab) && lab === laboratorio;
        });
    }
    // Opción: ocultar sospechosos al final (ya los ordena buscar(), pero el filtro es explícito)
    if (!mostrarSospechosos) {
        r = r.filter(m => (m.vigencia_score ?? 100) >= 50);
    }
    return r;
}

/**
 * Ordenamiento con conciencia de vigencia.
 * Nunca sube un producto sospechoso arriba de uno normal.
 */
export function ordenar(lista, modo = 'relevancia') {
    return [...lista].sort((a, b) => {
        const vigA = a.vigencia_score ?? 100;
        const vigB = b.vigencia_score ?? 100;
        const suspA = vigA < 50;
        const suspB = vigB < 50;

        // Sospechosos siempre al fondo
        if (suspA !== suspB) return suspA ? 1 : -1;

        if (modo === 'precio_asc') {
            return (a.precio || 0) - (b.precio || 0);
        }
        if (modo === 'precio_desc') {
            return (b.precio || 0) - (a.precio || 0);
        }
        // 'relevancia': mantener orden que viene del searchEngine
        return 0;
    });
}

// Compat: alias para el modo legacy
export function ordenarPorPrecio(lista, direccion = 'asc') {
    return ordenar(lista, direccion === 'asc' ? 'precio_asc' : 'precio_desc');
}

export function obtenerLaboratoriosValidos(lista) {
    const labs = new Set();
    lista.forEach(m => {
        const lab = m.laboratorio;
        if (lab && !esValorCorrupto(lab)) labs.add(lab);
    });
    return [...labs].sort();
}
