#!/usr/bin/env python3
"""pdf_to_json_fijo.py - Versión robusta con detección de campos, SIN PAMI"""

import re
import json
import sys
import urllib.request
from pathlib import Path
from datetime import datetime, timezone

try:
    import fitz
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pymupdf"])
    import fitz

def limpiar_precio(valor):
    if not valor or valor == '-':
        return None
    valor = str(valor).strip()
    valor = valor.replace('.', '').replace(',', '.')
    valor = re.sub(r'[^\d\.]', '', valor)
    try:
        return float(valor)
    except:
        return None

def es_precio(texto):
    if not texto:
        return False
    limpio = re.sub(r'[\$\s]', '', texto)
    return bool(re.match(r'^[\d\.,]+$', limpio))

def main():
    # URL con fecha dinámica
    fecha = datetime.now().strftime("%d%m%y")
    pdf_url = f"https://siafar.com/precios/pdf/Precios{fecha}.pdf"
    print(f"Descargando: {pdf_url}")

    req = urllib.request.Request(pdf_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        pdf_bytes = r.read()

    print(f"Tamaño: {len(pdf_bytes)} bytes")
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    medicamentos = []

    for pagina_num in range(len(doc)):
        texto = doc[pagina_num].get_text()
        lineas = [l.strip() for l in texto.split('\n') if l.strip()]

        i = 0
        while i < len(lineas):
            linea = lineas[i]

            if 'MONODROGA' in linea or 'pag' in linea.lower():
                i += 1
                continue

            if es_precio(linea):
                i += 1
                continue

            if i + 4 < len(lineas):
                droga = linea
                marca = lineas[i+1]
                presentacion = lineas[i+2]
                laboratorio = lineas[i+3]
                precio_str = lineas[i+4]

                if es_precio(precio_str):
                    precio = limpiar_precio(precio_str)

                    if precio and droga:
                        medicamentos.append({
                            'droga': droga.lower(),
                            'marca': marca.upper(),
                            'presentacion': presentacion,
                            'laboratorio': laboratorio if not es_precio(laboratorio) else 'Desconocido',
                            'precio': precio
                        })
                    i += 5
                    continue
            i += 1

        if (pagina_num + 1) % 10 == 0:
            print(f"Página {pagina_num + 1}: {len(medicamentos)} medicamentos")

    doc.close()
    print(f"\nTotal extraído: {len(medicamentos)}")

    if medicamentos:
        output_path = Path(__file__).parent.parent / "data" / "medicamentos.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "fecha": datetime.now(timezone.utc).isoformat(),
            "fuente": pdf_url,
            "total": len(medicamentos),
            "medicamentos": medicamentos
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, separators=(',', ':'))

        print(f"✅ Guardado: {output_path}")
        print(f"\n📊 ESTADÍSTICAS:")
        print(f"   Total: {len(medicamentos)} medicamentos")
    else:
        print("\n❌ No se extrajo ningún medicamento")
        sys.exit(1)

if __name__ == "__main__":
    main()
