#!/usr/bin/env python3
"""
scripts/snapshot_semanal.py
Genera un CSV con los precios confiables de la semana y lo sube
como asset a la release mensual de GitHub.

Estructura:
  Release:  historial-YYYY-MM
  Asset:    YYYY-MM/semana-N-YYYY-MM-DD.csv

Solo incluye medicamentos con vigencia_score >= 50.
"""
import csv
import json
import os
import sys
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path

AR_TZ        = timezone(timedelta(hours=-3))
BASE         = Path(__file__).parent.parent
DATOS_PATH   = BASE / "data" / "medicamentos.json"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO         = "psbella/remediar"
API_BASE     = "https://api.github.com"

CAMPOS_CSV = ["fecha", "droga", "marca", "laboratorio", "presentacion", "precio", "pami_cobertura"]


def semana_del_mes(fecha: datetime) -> int:
    """Devuelve el número de semana dentro del mes (1-5)."""
    return (fecha.day - 1) // 7 + 1


def nombre_archivo(fecha: datetime) -> str:
    mes   = fecha.strftime("%Y-%m")
    sem   = semana_del_mes(fecha)
    dia   = fecha.strftime("%Y-%m-%d")
    return f"{mes}/semana-{sem}-{dia}.csv"


def generar_csv(fecha: datetime) -> tuple[str, bytes]:
    """Genera el CSV y devuelve (nombre_archivo, contenido_bytes)."""
    with open(DATOS_PATH, encoding="utf-8") as f:
        data = json.load(f)

    meds     = data.get("medicamentos", [])
    fecha_str = fecha.strftime("%Y-%m-%d")
    confiables = [m for m in meds if (m.get("vigencia_score") or 0) >= 50]

    print(f"   Total: {len(meds)} | Confiables (score ≥ 50): {len(confiables)}")

    import io
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CAMPOS_CSV, extrasaction="ignore")
    writer.writeheader()
    for m in confiables:
        writer.writerow({
            "fecha":           fecha_str,
            "droga":           m.get("droga", ""),
            "marca":           m.get("marca", ""),
            "laboratorio":     m.get("laboratorio", ""),
            "presentacion":    m.get("presentacion", ""),
            "precio":          m.get("precio", ""),
            "pami_cobertura":  m.get("pami_cobertura", ""),
        })

    nombre = nombre_archivo(fecha)
    return nombre, buf.getvalue().encode("utf-8")


def _api(method: str, path: str, body: dict | None = None) -> dict:
    url  = f"{API_BASE}{path}"
    data = json.dumps(body).encode() if body else None
    req  = urllib.request.Request(
        url, data=data, method=method,
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept":        "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type":  "application/json",
            "User-Agent":    "remediar-snapshot",
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        cuerpo = e.read().decode()
        restante = e.headers.get("X-RateLimit-Remaining")
        if e.code in (403, 429) and restante == "0":
            reset = e.headers.get("X-RateLimit-Reset")
            raise RuntimeError(
                f"GitHub API rate limit agotado (reset epoch={reset}). "
                f"{method} {path} → {e.code}: {cuerpo}"
            )
        raise RuntimeError(f"GitHub API {method} {path} → {e.code}: {cuerpo}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"GitHub API {method} {path} → sin respuesta (timeout/red): {e}")


def _api_upload(upload_url: str, nombre: str, contenido: bytes) -> dict:
    """Sube un asset binario a una release."""
    # upload_url viene con {?name,label} al final
    url = upload_url.split("{")[0] + f"?name={urllib.parse.quote(nombre)}"
    req = urllib.request.Request(
        url, data=contenido, method="POST",
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept":        "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type":  "text/csv",
            "User-Agent":    "remediar-snapshot",
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        cuerpo = e.read().decode()
        raise RuntimeError(f"GitHub API upload → {e.code}: {cuerpo}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"GitHub API upload → sin respuesta (timeout/red): {e}")


def obtener_o_crear_release(tag: str, nombre: str) -> dict:
    """Devuelve la release existente o la crea."""
    try:
        return _api("GET", f"/repos/{REPO}/releases/tags/{tag}")
    except RuntimeError:
        print(f"   Release '{tag}' no existe, creando...")
        return _api("POST", f"/repos/{REPO}/releases", {
            "tag_name":         tag,
            "name":             nombre,
            "body":             f"Snapshots semanales de precios — {nombre}",
            "draft":            False,
            "prerelease":       False,
            "target_commitish": "main",
        })


def asset_existe(release: dict, nombre_asset: str) -> bool:
    """Verifica si el asset ya fue subido."""
    assets = release.get("assets", [])
    return any(a["name"] == nombre_asset for a in assets)


def main():
    if not GITHUB_TOKEN:
        print("ERROR: GITHUB_TOKEN no disponible.")
        sys.exit(1)

    ahora  = datetime.now(AR_TZ)
    print(f"\nSnapshot semanal — {ahora.strftime('%Y-%m-%d %H:%M')} AR")

    nombre_csv, contenido = generar_csv(ahora)
    mes_tag    = ahora.strftime("historial-%Y-%m")
    mes_nombre = ahora.strftime("Historial %B %Y")
    solo_nombre = nombre_csv.split("/")[-1]  # el nombre del asset sin la carpeta

    print(f"   Archivo: {nombre_csv}")
    print(f"   Release: {mes_tag}")

    release = obtener_o_crear_release(mes_tag, mes_nombre)

    if asset_existe(release, solo_nombre):
        print(f"   Asset '{solo_nombre}' ya existe, saltando.")
        return

    resultado = _api_upload(release["upload_url"], solo_nombre, contenido)
    print(f"   ✅ Subido: {resultado['browser_download_url']}")


if __name__ == "__main__":
    main()
