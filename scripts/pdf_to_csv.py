#!/usr/bin/env python3
import re
import csv
import sys
import urllib.request
from pathlib import Path

try:
    import fitz
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pymupdf"])
    import fitz

BASE_DIR = Path(__file__).parent.parent
CSV_PATH = BASE_DIR / "data" / "medicamentos.csv"
CSV_COLUMNS = ["droga", "marca", "presentacion", "laboratorio", "precio"]


def obtener_url_pdf():
    base_url = "https://siafar.com/precios/pdf/"
    req = urllib.request.Request(base_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        final_url = response.geturl()
        if final_url == base_url:
            html = response.read().decode('utf-8')
            match = re.search(r'href="([^"]*Precios\d+\.pdf)"', html)
            if match:
                final_url = match.group(1)
        return final_url


def limpiar_precio(valor):
    if not valor or valor == '-':
        return None
    limpio = re.sub(r'[^\d,\.]', '', str(valor).strip())
    limpio = limpio.replace('.', '').replace(',', '.')
    try:
        return float(limpio)
    except:
        return None


def es_precio(texto):
    if not texto:
        return False
    limpio = re.sub(r'[\$\s\.]', '', texto.strip())
    limpio = limpio.replace(',', '.')
    return bool(re.match(r'^\d[\d\.]*$', limpio))


def es_laboratorio(texto):
    if not texto:
        return False
    t = texto.strip()
    if es_precio(t):
        return False
    if re.search(r'\b(mg|ml|g|ui|comp|caps|tabletas|comprimidos|suspensión|solución|jarabe|gotas|crema|ungüento|inyectable)\b', t, re.I):
        return False
    if re.search(r'\d+\s*(mg|ml|g|ui)', t, re.I):
        return False
    return True


def extraer_medicamentos(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    meds = []

    for pagina_num in range(len(doc)):
        texto = doc[pagina_num].get_text()
        lineas = [l.strip() for l in texto.split('\n') if l.strip()]

        i = 0
        while i < len(lineas):
            if 'MONODROGA' in lineas[i] or 'pag' in lineas[i].lower():
                i += 1
                continue
            if es_precio(lineas[i]):
                i += 1
                continue

            droga = lineas[i]
            i += 1
            if i >= len(lineas):
                break

            marca = lineas[i]
            i += 1
            if i >= len(lineas):
                break

            presentacion = ""
            while i < len(lineas) and not es_laboratorio(lineas[i]) and not es_precio(lineas[i]):
                if presentacion:
                    presentacion += " "
                presentacion += lineas[i]
                i += 1

            if i >= len(lineas):
                break

            laboratorio = lineas[i] if es_laboratorio(lineas[i]) else "Desconocido"
            if es_laboratorio(lineas[i]):
                i += 1

            if i >= len(lineas):
                break

            precio_str = lineas[i]
            if not es_precio(precio_str):
                continue
            precio = limpiar_precio(precio_str)
            i += 1

            if precio and droga:
                meds.append({
                    'droga': droga.lower().strip(),
                    'marca': marca.upper().strip(),
                    'presentacion': presentacion.strip(),
                    'laboratorio': laboratorio.strip() if laboratorio else 'Desconocido',
                    'precio': precio,
                })

        if (pagina_num + 1) % 10 == 0:
            print(f"   Página {pagina_num + 1}: {len(meds):,} medicamentos")

    doc.close()
    return meds


def main():
    pdf_url = obtener_url_pdf()
    print(f"⬇  Descargando: {pdf_url}")
    req = urllib.request.Request(pdf_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        pdf_bytes = r.read()
    print(f"   Tamaño: {len(pdf_bytes):,} bytes")
    print("📄 Extrayendo medicamentos...")
    meds = extraer_medicamentos(pdf_bytes)

    if not meds:
        print("❌ No se extrajo ningún medicamento.")
        sys.exit(1)

    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CSV_PATH, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(meds)

    print(f"\n✅ CSV guardado: {CSV_PATH}")
    print(f"   Total: {len(meds):,} medicamentos")


if __name__ == "__main__":
    main()
