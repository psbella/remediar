// js/about.js — Carga los números dinámicos de about.html
import { calcularEstadisticas } from './utils.js';

(async () => {
    try {
        const response = await fetch('data/medicamentos.json');
        if (!response.ok) throw new Error(`Error al cargar datos: ${response.status}`);
        const data = await response.json();

        const medicamentos = data.medicamentos || [];
        const { total, drogas, conPami, pctPami } = calcularEstadisticas(medicamentos);

        // Formato fecha
        const fecha = new Date(data.fecha).toLocaleDateString('es-AR', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });

        // Inyectar números
        document.getElementById('stat-total').textContent = total.toLocaleString('es-AR');
        document.getElementById('stat-drogas').textContent = drogas.toLocaleString('es-AR');
        document.getElementById('stat-pami').textContent = conPami.toLocaleString('es-AR');
        document.getElementById('stat-pami-pct').textContent = pctPami + '%';
        document.getElementById('fecha-actualizacion').textContent = fecha;
    } catch (error) {
        console.error('Error al cargar datos:', error);
        document.getElementById('stat-total').textContent = '~12.900';
        document.getElementById('stat-drogas').textContent = '~1.800';
        document.getElementById('stat-pami').textContent = '~6.400';
        document.getElementById('stat-pami-pct').textContent = '~48%';
        document.getElementById('fecha-actualizacion').textContent = 'última actualización';
    }
})();
