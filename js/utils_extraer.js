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
