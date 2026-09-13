#!/usr/bin/env python3
"""
scripts/diff_precios.py
Calcula el diff entre el data/medicamentos.json del ultimo commit (HEAD)
y el actual (recien regenerado por pdf_to_json.py en esta corrida), y
agrega solo las variaciones -- altas, bajas y cambios de precio -- a un
archivo historico incremental en data/historico/precios.json.

Reemplaza a snapshot_semanal.py: en vez de una foto completa semanal
(todos los "confiables", solo los viernes) subida como asset a GitHub
Releases, guarda unicamente lo que cambio, en cada corrida del workflow
(2 veces por dia habil), como parte del propio repo -- se commitea junto
con el resto de los datos (mismo git add de siempre en el workflow), sin
depender de la API de GitHub Releases ni de GITHUB_TOKEN.

Debe ejecutarse DESPUES de pdf_to_json.py y ANTES del commit de esta
corrida: en ese punto HEAD todavia apunta al commit anterior, asi que
`git show HEAD:...` da el estado previo sin necesidad de una copia aparte.

Formato de data/historico/precios.json:
  Lista de entradas, cada una con la misma forma que una fila de
  calcular_diff() (fecha, tipo, droga, marca, laboratorio, presentacion,
  precio_anterior, precio_nuevo, diferencia, variacion_pct). El archivo
  se lee, se le agregan las filas nuevas de esta corrida al final, y se
  vuelve a escribir completo (append logico, no reemplazo).

Solo compara medicamentos con vigencia_score >= 50 (mismo criterio de
"confiable" que usaba snapshot_semanal.py), para no meter ruido de
extracciones poco confiables al historico. El dataset tiene ~13000
medicamentos pero tipicamente solo una fraccion cambia de precio por
corrida, asi que el archivo historico crece por variaciones reales, no
por el tamano completo del dataset en cada corrida.
"""
import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

AR_TZ = timezone(timedelta(hours=-3))
BASE = Path(__file__).parent.parent
DATOS_PATH = BASE / "data" / "medicamentos.json"
HISTORICO_PATH = BASE / "data" / "historico" / "precios.json"
EPSILON = 0.005
CONFIABLE_MIN_SCORE = 50


def clave(m: dict) -> tuple:
    return (m.get("droga"), m.get("marca"), m.get("laboratorio"), m.get("presentacion"))


def _confiables(meds: list) -> dict:
    return {
        clave(m): m
        for m in meds
        if (m.get("vigencia_score") or 0) >= CONFIABLE_MIN_SCORE
    }


def cargar_anterior() -> dict:
    try:
        resultado = subprocess.run(
            ["git", "show", "HEAD:data/medicamentos.json"],
            cwd=BASE, capture_output=True, text=True, check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"   No se pudo leer HEAD anterior ({e}); se asume primera corrida, sin diff.")
        return {}
    data = json.loads(resultado.stdout)
    return _confiables(data.get("medicamentos", []))


def cargar_actual() -> dict:
    with open(DATOS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return _confiables(data.get("medicamentos", []))


def calcular_diff(anterior: dict, actual: dict, fecha_str: str) -> list[dict]:
    filas = []
    claves_anterior = set(anterior)
    claves_actual = set(actual)

    for k in sorted(claves_actual - claves_anterior):
        m = actual[k]
        filas.append({
            "fecha": fecha_str, "tipo": "alta",
            "droga": k[0], "marca": k[1], "laboratorio": k[2], "presentacion": k[3],
            "precio_anterior": None, "precio_nuevo": m.get("precio"),
            "diferencia": None, "variacion_pct": None,
        })

    for k in sorted(claves_anterior - claves_actual):
        m = anterior[k]
        filas.append({
            "fecha": fecha_str, "tipo": "baja",
            "droga": k[0], "marca": k[1], "laboratorio": k[2], "presentacion": k[3],
            "precio_anterior": m.get("precio"), "precio_nuevo": None,
            "diferencia": None, "variacion_pct": None,
        })

    for k in sorted(claves_actual & claves_anterior):
        p_nuevo = actual[k].get("precio")
        p_viejo = anterior[k].get("precio")
        if p_nuevo is None or p_viejo is None:
            continue
        diferencia = round(p_nuevo - p_viejo, 2)
        if abs(diferencia) < EPSILON:
            continue
        pct = round((diferencia / p_viejo) * 100, 2) if p_viejo else None
        filas.append({
            "fecha": fecha_str, "tipo": "cambio_precio",
            "droga": k[0], "marca": k[1], "laboratorio": k[2], "presentacion": k[3],
            "precio_anterior": p_viejo, "precio_nuevo": p_nuevo,
            "diferencia": diferencia, "variacion_pct": pct,
        })

    return filas


def cargar_historico() -> list:
    if not HISTORICO_PATH.exists():
        return []
    with open(HISTORICO_PATH, encoding="utf-8") as f:
        return json.load(f)


def guardar_historico(entradas: list) -> None:
    HISTORICO_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORICO_PATH, "w", encoding="utf-8") as f:
        json.dump(entradas, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main():
    ahora = datetime.now(AR_TZ)
    fecha_str = ahora.strftime("%Y-%m-%d %H:%M")
    print(f"\nDiff de precios - {fecha_str} AR")

    anterior = cargar_anterior()
    actual = cargar_actual()
    filas_nuevas = calcular_diff(anterior, actual, fecha_str)

    altas = sum(1 for f in filas_nuevas if f["tipo"] == "alta")
    bajas = sum(1 for f in filas_nuevas if f["tipo"] == "baja")
    cambios = sum(1 for f in filas_nuevas if f["tipo"] == "cambio_precio")
    print(f"   Anterior: {len(anterior)} | Actual: {len(actual)} confiables")
    print(f"   Altas: {altas} | Bajas: {bajas} | Cambios de precio: {cambios}")

    if not filas_nuevas:
        print("   Sin variaciones, no se modifica el historico.")
        return

    historico = cargar_historico()
    historico.extend(filas_nuevas)
    guardar_historico(historico)
    print(f"   {HISTORICO_PATH.relative_to(BASE)}: {len(filas_nuevas)} filas agregadas, {len(historico)} en total.")


if __name__ == "__main__":
    main()
