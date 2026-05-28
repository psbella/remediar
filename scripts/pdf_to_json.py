import re
import json
import sys
import urllib.request
import ssl
from pathlib import Path
from datetime import datetime, timezone, timedelta

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

try:
    import fitz
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pymupdf"])
    import fitz

LAST_PDF_FILE = Path(__file__).parent.parent / "data" / "last_pdf.txt"

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

def obtener_ultima_fecha_exitosa():
    if LAST_PDF_FILE.exists():
        try:
            fecha_str = LAST_PDF_FILE.read_text().strip()
            return datetime.strptime(fecha_str, "%d%m%y")
        except:
            return None
    return None

def guardar_fecha_exitosa(fecha):
    LAST_PDF_FILE.write_text(fecha.strftime("%d%m%y"))

def encontrar_pdf():
    # 1. Intentar desde la última fecha exitosa (si existe)
    ultima_fecha = obtener_ultima_fecha_exitosa()
    
    fechas_a_probar = []
    
    if ultima_fecha:
        # Empezar desde la última fecha exitosa hacia adelante (buscar más nuevo)
        for dias in range(7):
            fecha = ultima_fecha + timedelta(days=dias)
            if fecha <= datetime.now():
                fechas_a_probar.append(fecha)
        # También incluir días anteriores por si acaso
        for dias in range(1, 8):
            fecha = ultima_fecha - timedelta(days=dias)
            if fecha not in fechas_a_probar:
                fechas_a_probar.append(fecha)
    else:
        # No hay registro, probar desde hoy hacia atrás
        for dias in range(7):
            fechas_a_probar.append(datetime.now() - timedelta(days=dias))
    
    # Eliminar duplicados y ordenar por fecha descendente (más reciente primero)
    fechas_a_probar = sorted(set(fechas_a_probar), reverse=True)
    
    for fecha in fechas_a_probar:
        fecha_str = fecha.strftime("%d%m%y")
        pdf_url = f"https://siafar.com/precios/pdf/Precios{fecha_str}.pdf"
        print(f"Intentando: {pdf_url}")
        
        try:
            req = urllib.request.Request(pdf_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30, context=ssl_context) as r:
                pdf_bytes = r.read()
                print(f"✅ Descargado: {pdf_url}")
                guardar_fecha_exitosa(fecha)
                return pdf_bytes, pdf_url
        except:
            print(f"   No disponible")
            continue
    
    raise Exception("No se encontró PDF en los últimos días")

def main():
    print(f"Descargando PDF...")
    pdf_bytes, pdf_url = encontrar_pdf()
    
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
