# Pipeline de Remedios — Guía técnica

## Arquitectura v2.0

```
PDF farmacéutico → pdf_to_json.py → medicamentos.json (raw)
                                          ↓
                              pipeline.py (normalización + scoring)
                                          ↓
                          medicamentos.json (enriquecido con flags/scores)
                                    ↙           ↘
                     generar_landings.py      Frontend JS
                    (16 landing pages + sitemap)   (búsqueda + vigencia UI)
```

## Ejecutar el pipeline completo

```bash
# Solo procesar JSON existente (sin descargar PDF)
python scripts/pipeline.py

# Descargar PDF + procesar
python scripts/pipeline.py --pdf

# Solo generar reporte sin modificar JSON
python scripts/pipeline.py --report-only

# Pipeline completo + regenerar landings
python scripts/pipeline.py && python scripts/generar_landings.py
```

## Estructura de un medicamento enriquecido

```json
{
  "droga":         "ibuprofeno",
  "marca":         "IBUPIRAC",
  "presentacion":  "600 mg comprimidos x 20",
  "laboratorio":   "Pfizer",
  "precio":        12500.00,
  "copago_pami":   null,
  "fingerprint":   "a3f9b12c4d5e",
  "vigencia_score": 100,
  "flags":          []
}
```

## Flags posibles

| Flag | Significado | Penalización |
|------|-------------|--------------|
| `precio_anomalo` | Precio < 15% de la mediana de su droga | -45 pts |
| `laboratorio_sospechoso` | Mediana del lab < 8% de mediana global | -30 pts |
| `precio_minimo_absoluto` | Precio < $100 ARS | -20 pts |
| `sin_laboratorio` | Laboratorio "Desconocido" | -10 pts |
| `sin_presentacion` | Presentación vacía | -5 pts |
| `precio_congelado` | Sin cambio en ≥5 snapshots | -15 pts |

## vigencia_score

- **100**: sin flags, precio y datos completos
- **70–99**: datos menores faltantes (sin laboratorio, etc.)
- **50–69**: precio a verificar o lab poco frecuente
- **< 50**: precio marcadamente anómalo → degradado al fondo de resultados

## Snapshots

Se guardan en `snapshots/YYYY-MM-DD.json` automáticamente.
Permiten detectar precios congelados comparando con historial.

## Reportes

Los reportes de validación se guardan en `reports/validation_FECHA.txt`.
