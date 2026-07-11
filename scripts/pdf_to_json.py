#!/usr/bin/env python3
"""pdf_to_json.py - Descarga el PDF, filtra blacklist, detecta outliers, genera JSON.

Orquestador del ETL: cada capa de parseo/reparación/enriquecimiento vive en
scripts/etl/ como un módulo independiente y testeable por separado. Este
archivo solo encadena los pasos en el orden correcto y persiste el resultado.
"""

import json
from datetime import datetime

from etl.config import AR_TZ, MEDICAMENTOS_PATH, BASE, DROGA_FIXES_PATH
from etl.parser import PDF_URL, descargar_pdf, parsear_pdf, deduplicar
from etl.blacklist import cargar_blacklist, filtrar_blacklist
from etl.reparaciones import (
    reparar_denver,
    reparar_marca_desplazada,
    reparar_presentacion_desplazada,
    rescatar_laboratorios,
)
from etl.droga_fixes import aplicar_droga_fixes, reparar_droga_faltante
from etl.pami import crosswalk_pami
from etl.presentacion import (
    _build_re_lab_pegado,
    extraer_presentacion_de_marca,
    limpiar_dosis_residual_en_marca,
    generar_debug_presentaciones,
)
from etl.outliers import calcular_vigencia
from etl.enriquecimiento import enriquecer_dosis


def main():
    pdf_bytes = descargar_pdf(PDF_URL)
    medicamentos = parsear_pdf(pdf_bytes)

    # ── Deduplicación de registros exactos ─────────────────────────────────
    # El PDF a veces repite la misma línea completa (droga+marca+presentación+
    # laboratorio+precio idénticos) — se descartan antes de correr las capas
    # de reparación, que de otro modo procesarían el mismo registro dos veces.
    medicamentos, n_duplicados = deduplicar(medicamentos)
    print(f"Duplicados exactos eliminados: {n_duplicados}")

    # ── CAPA 0: cargar fixes y reparar registros con droga faltante ───────
    fixes_droga = {}
    if DROGA_FIXES_PATH.exists():
        with open(DROGA_FIXES_PATH, encoding='utf-8') as f:
            fixes_droga = json.load(f)
    print("\nReparando registros con droga faltante (capa 0)...")
    medicamentos, n_capa0 = reparar_droga_faltante(medicamentos, fixes_droga)
    print(f"   Reparados: {n_capa0}")

    # ── CAPA 2: rescate post-parse con laboratorios conocidos ──────────────
    print("\nRescatando laboratorios desplazados...")
    medicamentos, n_rescatados = rescatar_laboratorios(medicamentos)
    n_desconocidos = sum(1 for m in medicamentos if m.get('laboratorio') == 'Desconocido')
    print(f"   Rescatados: {n_rescatados} | Sin recuperar: {n_desconocidos}")

    # ── CAPA 3: reparación de fusiones marca+presentacion de Denver Farma ──
    print("\nReparando registros Denver Farma...")
    medicamentos, n_denver = reparar_denver(medicamentos)
    print(f"   Reparados: {n_denver}")

    # ── CAPA 4: reparación de marca desplazada (nombre comercial en droga) ──
    print("\nReparando marcas desplazadas...")
    medicamentos, n_marca = reparar_marca_desplazada(medicamentos)
    print(f"   Reparados: {n_marca}")

    # ── CAPA 5: extraer presentacion fusionada en marca ───────────────────
    print("\nExtrayendo presentacion de marca fusionada...")
    # re_lab_pegado se construye una sola vez acá y se reutiliza en la
    # Capa 5c: depende solo del campo 'laboratorio', que ni esta capa ni
    # la 5b lo modifican con valores nuevos (ver docstring de
    # extraer_presentacion_de_marca).
    re_lab_pegado = _build_re_lab_pegado(medicamentos)
    medicamentos, n_extrac = extraer_presentacion_de_marca(medicamentos, re_lab_pegado)
    print(f"   Reparados: {n_extrac}")

    # ── CAPA 5b: reparar presentacion desplazada al campo lab ────────────
    print("\nReparando presentacion desplazada...")
    medicamentos, n_pres = reparar_presentacion_desplazada(medicamentos)
    print(f"   Reparados: {n_pres}")

    # ── CAPA 5c: limpiar dosis residual pegada a laboratorio en marca ────
    # Cubre el caso donde la Capa 5b ya separó la forma hacia
    # 'presentacion' pero dejó la dosis numérica pegada al laboratorio
    # dentro de 'marca' (ej. "CIPROFLOXACINA SANT GALL500 MG").
    print("\nLimpiando dosis residual en marca...")
    medicamentos, n_dosis_residual = limpiar_dosis_residual_en_marca(medicamentos, re_lab_pegado)
    print(f"   Reparados: {n_dosis_residual}")

    # ── CAPA 6: crosswalk PAMI → recuperar droga y corregir laboratorio ───
    print("\nCrosswalk PAMI...")
    medicamentos, stats_pami = crosswalk_pami(medicamentos)
    print(f"   Matches exactos: {stats_pami['match_exacto']} | "
          f"Drogas recuperadas: {stats_pami['droga_recuperada']} | "
          f"Labs corregidos: {stats_pami['lab_corregido']}")
    if stats_pami['pami_cobertura_invalida'] > 0:
        print(f"   ⚠️  Coberturas PAMI fuera de rango (0-100%) descartadas: {stats_pami['pami_cobertura_invalida']}")

    # ── CAPA 7: fixes manuales de droga ──────────────────────────────────
    print("\nAplicando fixes manuales de droga...")
    medicamentos, n_fixes = aplicar_droga_fixes(medicamentos)
    print(f"   Corregidos: {n_fixes}")

    print("\nAplicando lista negra...")
    blacklist          = cargar_blacklist()
    medicamentos, n_bl = filtrar_blacklist(medicamentos, blacklist)
    medicamentos       = calcular_vigencia(medicamentos)

    print("\nGenerando debug de presentaciones...")
    generar_debug_presentaciones(medicamentos)

    enriquecer_dosis(medicamentos)

    ahora_ar  = datetime.now(AR_TZ)
    fecha_str = ahora_ar.strftime("%Y-%m-%d %H:%M:%S")
    data = {
        "fecha":        fecha_str,
        "fuente":       PDF_URL,
        "total":        len(medicamentos),
        "blacklisted":  n_bl,
        "medicamentos": medicamentos,
    }

    MEDICAMENTOS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MEDICAMENTOS_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
    PRETTY_PATH = BASE / ".debug" / "medicamentos.pretty.json"
    PRETTY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PRETTY_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\nGuardado: {MEDICAMENTOS_PATH}")
    print(f"Total: {len(medicamentos)} | Excluidos (blacklist): {n_bl} | Fecha: {fecha_str}")


if __name__ == "__main__":
    main()
