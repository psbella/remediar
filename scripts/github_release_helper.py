"""
scripts/github_release_helper.py
Funciones compartidas para crear/obtener releases de GitHub y subir,
reemplazar o verificar assets. Usado por snapshot_semanal.py y
subir_debug.py.
"""
import json
import os
import urllib.request
import urllib.error
import urllib.parse

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO         = os.environ.get("GITHUB_REPOSITORY", "psbella/remediar")
API_BASE     = "https://api.github.com"


def _headers(content_type: str = "application/json") -> dict:
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept":        "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type":  content_type,
        "User-Agent":    "remediar-release-helper",
    }


def api(method: str, path: str, body: dict | None = None) -> dict:
    url  = f"{API_BASE}{path}"
    data = json.dumps(body).encode() if body else None
    req  = urllib.request.Request(url, data=data, method=method, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        detalle = e.read().decode()
        restante = e.headers.get("X-RateLimit-Remaining")
        if e.code in (403, 429) and restante == "0":
            reset = e.headers.get("X-RateLimit-Reset")
            raise RuntimeError(
                f"GitHub API rate limit agotado (reset epoch={reset}). "
                f"{method} {path} -> {e.code}: {detalle}"
            )
        raise RuntimeError(f"GitHub API {method} {path} -> {e.code}: {detalle}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"GitHub API {method} {path} -> sin respuesta (timeout/red): {e}")


def api_upload(upload_url: str, nombre: str, contenido: bytes, content_type: str) -> dict:
    """Sube un asset binario a una release."""
    url = upload_url.split("{")[0] + f"?name={urllib.parse.quote(nombre)}"
    req = urllib.request.Request(
        url, data=contenido, method="POST",
        headers=_headers(content_type),
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        detalle = e.read().decode()
        raise RuntimeError(f"GitHub API upload -> {e.code}: {detalle}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"GitHub API upload -> sin respuesta (timeout/red): {e}")


def obtener_o_crear_release(tag: str, nombre: str, body: str) -> dict:
    """Devuelve la release existente o la crea."""
    try:
        return api("GET", f"/repos/{REPO}/releases/tags/{tag}")
    except RuntimeError:
        print(f"   Release '{tag}' no existe, creando...")
        return api("POST", f"/repos/{REPO}/releases", {
            "tag_name":         tag,
            "name":             nombre,
            "body":             body,
            "draft":            False,
            "prerelease":       False,
            "target_commitish": "main",
        })


def asset_existe(release: dict, nombre_asset: str) -> dict | None:
    """Devuelve el asset si existe, None si no."""
    for a in release.get("assets", []):
        if a["name"] == nombre_asset:
            return a
    return None


def eliminar_asset(asset_id: int) -> None:
    url = f"{API_BASE}/repos/{REPO}/releases/assets/{asset_id}"
    req = urllib.request.Request(url, method="DELETE", headers=_headers())
    try:
        with urllib.request.urlopen(req):
            pass  # 204 No Content -- sin cuerpo
    except urllib.error.HTTPError as e:
        if e.code != 204:
            raise RuntimeError(f"GitHub API DELETE assets/{asset_id} -> {e.code}")


def subir_o_reemplazar_asset(release: dict, nombre: str, contenido: bytes, content_type: str) -> dict:
    """Si el asset ya existe lo borra y sube el nuevo (sobreescribe)."""
    existente = asset_existe(release, nombre)
    if existente:
        eliminar_asset(existente["id"])
        print(f"   Asset anterior '{nombre}' eliminado.")
    return api_upload(release["upload_url"], nombre, contenido, content_type)
