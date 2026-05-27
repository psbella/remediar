#!/usr/bin/env python3
import camelot
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

print("📊 Extrayendo tablas con Camelot...")
tables = camelot.read_pdf("temp.pdf", pages='all', flavor='lattice')

all_rows = []
for table in tables:
    df = table.df
    for idx, row in df.iterrows():
        if idx == 0:
            continue
        all_rows.append(row.tolist()[:5])

combined = pd.DataFrame(all_rows)
combined.columns = ['droga', 'marca', 'presentacion', 'laboratorio', 'precio']
combined = combined[~combined['droga'].str.contains('MONODROGA', na=False, case=False)]
combined = combined.dropna(subset=['precio'])

output_path = Path("data/medicamentos.csv")
combined.to_csv(output_path, index=False, encoding='utf-8')
print(f"✅ CSV guardado: {len(combined)} medicamentos")
