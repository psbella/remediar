"""
tests/test_etl_sanidad.py
Verifica que el output del ETL tiene la estructura y valores esperados.
Se ejecuta en el workflow de GitHub Actions después de pdf_to_json.py
y antes del commit, para evitar publicar datos rotos silenciosamente.
"""
import json
import statistics
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent / "data" / "medicamentos.json"


def cargar_medicamentos():
    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("medicamentos", [])


MEDICAMENTOS = cargar_medicamentos()


# ── Cantidad ──────────────────────────────────────────────────────────────────

def test_cantidad_minima():
    """El dataset nunca debería tener menos de 10.000 registros."""
    assert len(MEDICAMENTOS) > 10_000, (
        f"Solo {len(MEDICAMENTOS)} registros — el PDF puede haber cambiado de estructura."
    )


def test_cantidad_maxima():
    """Un salto brusco hacia arriba también es sospechoso."""
    assert len(MEDICAMENTOS) < 50_000, (
        f"{len(MEDICAMENTOS)} registros — valor inusualmente alto."
    )


# ── Campos obligatorios ───────────────────────────────────────────────────────

def test_campos_presentes():
    """Todos los registros deben tener los campos mínimos."""
    campos = ["droga", "marca", "presentacion", "laboratorio", "precio"]
    faltantes = []
    for i, m in enumerate(MEDICAMENTOS):
        for campo in campos:
            if campo not in m:
                faltantes.append(f"[{i}] falta '{campo}' en {m.get('marca', '?')}")
    assert not faltantes, f"Campos faltantes:\n" + "\n".join(faltantes[:20])


def test_precios_positivos():
    """Todos los precios deben ser positivos."""
    invalidos = [m for m in MEDICAMENTOS if not isinstance(m.get("precio"), (int, float)) or m["precio"] <= 0]
    assert len(invalidos) == 0, (
        f"{len(invalidos)} registros con precio inválido. Ejemplos: {invalidos[:3]}"
    )


# ── Rangos razonables ─────────────────────────────────────────────────────────

def test_precio_mediana_razonable():
    """La mediana de precios debe estar en un rango razonable para ARS."""
    precios = [m["precio"] for m in MEDICAMENTOS if isinstance(m.get("precio"), (int, float))]
    mediana = statistics.median(precios)
    assert mediana > 1_000, f"Mediana de precios muy baja: ${mediana:.0f} — posible error de escala."
    assert mediana < 10_000_000, f"Mediana de precios muy alta: ${mediana:.0f} — posible error de escala."


def test_precio_maximo_razonable():
    """Ningún precio debería ser más de 1000x la mediana del dataset."""
    precios = [m["precio"] for m in MEDICAMENTOS if isinstance(m.get("precio"), (int, float))]
    mediana = statistics.median(precios)
    MAX_RATIO = 1000
    outliers = [m for m in MEDICAMENTOS if m.get("precio", 0) > mediana * MAX_RATIO]
    assert len(outliers) == 0, (
        f"{len(outliers)} registros con precio > {MAX_RATIO}x la mediana (${mediana:,.0f}). Ejemplos: {outliers[:3]}"
    )


# ── Calidad de datos ──────────────────────────────────────────────────────────

def test_drogas_vacias():
    """Menos del 1% de registros puede tener droga vacía."""
    vacias = [m for m in MEDICAMENTOS if not m.get("droga", "").strip()]
    ratio = len(vacias) / len(MEDICAMENTOS)
    assert ratio < 0.01, (
        f"{len(vacias)} registros sin droga ({ratio:.1%}) — supera el umbral del 1%."
    )


def test_laboratorios_desconocidos():
    """Menos del 5% de registros puede tener laboratorio 'Desconocido'."""
    desconocidos = [m for m in MEDICAMENTOS if m.get("laboratorio", "").strip() == "Desconocido"]
    ratio = len(desconocidos) / len(MEDICAMENTOS)
    assert ratio < 0.05, (
        f"{len(desconocidos)} registros con lab 'Desconocido' ({ratio:.1%}) — supera el umbral del 5%."
    )


def test_marcas_vacias():
    """Menos del 0.5% de registros puede tener marca vacía."""
    vacias = [m for m in MEDICAMENTOS if not m.get("marca", "").strip()]
    ratio = len(vacias) / len(MEDICAMENTOS)
    assert ratio < 0.005, (
        f"{len(vacias)} registros sin marca ({ratio:.1%}) — supera el umbral del 0.5%."
    )


def test_vigencia_score_rango():
    """vigencia_score debe estar entre 0 y 100."""
    invalidos = [
        m for m in MEDICAMENTOS
        if not isinstance(m.get("vigencia_score"), (int, float))
        or not (0 <= m["vigencia_score"] <= 100)
    ]
    assert len(invalidos) == 0, (
        f"{len(invalidos)} registros con vigencia_score fuera de rango. Ejemplos: {invalidos[:3]}"
    )


def test_pami_cobertura_rango():
    """pami_cobertura debe ser None o un número entre 0 y 100."""
    invalidos = [
        m for m in MEDICAMENTOS
        if m.get("pami_cobertura") is not None
        and not (0 <= m["pami_cobertura"] <= 100)
    ]
    assert len(invalidos) == 0, (
        f"{len(invalidos)} registros con pami_cobertura fuera de rango. Ejemplos: {invalidos[:3]}"
    )


# ── Estructura del JSON raíz ──────────────────────────────────────────────────

def test_estructura_raiz():
    """El JSON debe tener los campos raíz esperados."""
    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)
    for campo in ["medicamentos", "fecha", "fuente"]:
        assert campo in data, f"Falta el campo raíz '{campo}' en medicamentos.json"


def test_fecha_presente():
    """El campo fecha no debe estar vacío."""
    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)
    assert data.get("fecha"), "El campo 'fecha' está vacío en medicamentos.json"
