// dataLoader.js — Carga con cache y compresión
const CACHE_KEY = 'remedios_data_v2';
const CACHE_TTL_MS = 2 * 60 * 60 * 1000; // 2 horas

export async function cargarDatos() {
    // Intentar cache en sessionStorage (sin IndexedDB ni localStorage)
    try {
        const cached = sessionStorage.getItem(CACHE_KEY);
        if (cached) {
            const { ts, data } = JSON.parse(cached);
            if (Date.now() - ts < CACHE_TTL_MS) {
                console.info('[dataLoader] Usando cache (sessionStorage)');
                return data;
            }
        }
    } catch (_) { /* sessionStorage bloqueado: continuar */ }

    // Fetch con prioridad alta
    const res = await fetch('data/medicamentos.json', {
        priority: 'high',
        cache: 'default',
    });
    if (!res.ok) throw new Error(`Error al cargar datos: ${res.status}`);

    const data = await res.json();

    // Guardar en cache
    try {
        sessionStorage.setItem(CACHE_KEY, JSON.stringify({ ts: Date.now(), data }));
    } catch (_) { /* sessionStorage lleno: no es crítico */ }

    return data;
}
