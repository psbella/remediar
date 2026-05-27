#!/usr/bin/env python3
import tabula
import pandas as pd
import urllib.request
import ssl
from pathlib import Path

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

pdf_url = "https://siafar.com/precios/pdf/Precios260527.pdf"
print(f"📥 Descargando: {pdf_url}")

req = urllib.request.Request(pdf_url, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=30, context=ssl_context) as r:
    with open("temp.pdf", "wb") as f:
        f.write(r.read())

print("📊 Extrayendo tablas del PDF...")

# Leer todas las tablas del PDF
tables = tabula.read_pdf("temp.pdf", pages='all', multiple_tables=True, lattice=True)

# Combinar todas las tablas
df = pd.concat(tables, ignore_index=True)

# Limpiar nombres de columnas (primeras filas suelen ser encabezados)
df.columns = ['droga', 'marca', 'presentacion', 'laboratorio', 'precio', 'copago_pami']

# Eliminar filas con encabezados repetidos
df = df[~df['droga'].str.contains('MONODROGA', na=False)]

# Convertir precios a números
df['precio'] = df['precio'].astype(str).str.replace('.', '').str.replace(',', '.').str.extract(r'(\d+\.\d+)').astype(float)
df['copago_pami'] = df['copago_pami'].astype(str).str.replace('.', '').str.replace(',', '.').str.extract(r'(\d+\.\d+)').astype(float)

# Guardar CSV
output_path = Path(__file__).parent.parent / "data" / "medicamentos.csv"
df.to_csv(output_path, index=False, encoding='utf-8')
print(f"✅ CSV guardado: {output_path}")
print(f"📊 Total: {len(df)} medicamentos")

# Limpiar
import os
os.remove("temp.pdf")
