"""Validación formal de estructura de data/medicamentos.json contra un JSON Schema.

A diferencia de test_etl_sanidad.py (que valida umbrales de calidad de negocio:
% de campos vacíos, rango de mediana, etc.), este archivo valida el CONTRATO
estructural del JSON: qué claves existen, qué tipos tienen, y cuáles son
opcionales. Si el ETL cambia la forma del output (agrega, saca o renombra un
campo), este test falla hasta que se actualice medicamentos.schema.json a
propósito — es una red de seguridad para el frontend, que asume esta forma
exacta en js/uiRenderer.js y js/utils.js.
"""
import json
from pathlib import Path

import jsonschema

DATA_PATH = Path(__file__).parent.parent / "data" / "medicamentos.json"
SCHEMA_PATH = Path(__file__).parent / "medicamentos.schema.json"

MAX_ERRORES_MOSTRADOS = 20


def _cargar():
    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        schema = json.load(f)
    return data, schema


def test_schema_valido():
    data, schema = _cargar()
    validador = jsonschema.Draft202012Validator(schema)
    errores = sorted(validador.iter_errors(data), key=lambda e: list(e.path))

    if errores:
        detalle = "\n".join(
            f"  - {'/'.join(str(p) for p in e.path) or '(raíz)'}: {e.message}"
            for e in errores[:MAX_ERRORES_MOSTRADOS]
        )
        restantes = len(errores) - MAX_ERRORES_MOSTRADOS
        extra = f"\n  ... y {restantes} más" if restantes > 0 else ""
        raise AssertionError(
            f"{len(errores)} error(es) de schema en medicamentos.json:\n{detalle}{extra}"
        )
