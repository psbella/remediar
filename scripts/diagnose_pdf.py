#!/usr/bin/env python3
"""
diagnose_pdf.py — Herramienta de diagnóstico para el PDF de SIAFAR.

Uso:
    pip install pdfplumber
    python diagnose_pdf.py                     # descarga el PDF de hoy
    python diagnose_pdf.py /ruta/al/archivo.pdf  # usa un PDF local

Imprime las primeras filas detectadas por pdfplumber, las dimensiones de cada
columna y un conteo de celdas vacías, para que puedas verificar que el mapeo
de columnas es correcto antes de correr el extractor real.
"""

import ssl
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pdfplumber

TMP = Path("/tmp/diag_siafar.pdf")

def build_url():
    arg_tz = timezone(timedelta(hours=-3))
    hoy = datetime.now(arg_tz).strftime("%y%m%d")
    return f"https://siafar.com/precios/pdf/Precios{hoy}.pdf"

def download(url, dest):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60, context=ctx) as r:
        dest.write_bytes(r.read())

def main():
    if len(sys.argv) > 1:
        pdf_path = Path(sys.argv[1])
    else:
        url = build_url()
        print(f"Descargando {url} …")
        download(url, TMP)
        pdf_path = TMP

    settings = {
        "vertical_strategy": "lines",
        "horizontal_strategy": "lines",
        "snap_tolerance": 3,
        "join_tolerance": 3,
    }

    with pdfplumber.open(pdf_path) as pdf:
        print(f"\n{'='*70}")
        print(f"PDF: {pdf_path.name}  |  Páginas: {len(pdf.pages)}")
        print(f"{'='*70}\n")

        for page_num in range(min(3, len(pdf.pages))):  # inspeccionamos primeras 3 páginas
            page = pdf.pages[page_num]
            table = page.extract_table(settings)
            if not table:
                table = page.extract_table({
                    "vertical_strategy": "text",
                    "horizontal_strategy": "text",
                })

            print(f"--- Página {page_num + 1} ---")
            if not table:
                print("  (sin tabla detectada)")
                continue

            print(f"  Filas detectadas: {len(table)}")
            print(f"  Columnas en fila 0: {len(table[0]) if table else 0}\n")

            print(f"  {'IDX':>4}  {'COL0 (droga)':25} {'COL1 (marca)':20} {'COL2 (pres.)':20} {'COL3 (lab.)':20} {'COL4 (precio)':12}")
            print(f"  {'-'*105}")
            for i, row in enumerate(table[:15]):
                cells = [(c or "").replace("\n", " ")[:22] for c in row]
                while len(cells) < 5:
                    cells.append("")
                print(f"  {i:>4}  {cells[0]:25} {cells[1]:20} {cells[2]:20} {cells[3]:20} {cells[4]:12}")
            print()

        # Estadísticas globales
        print("\n--- Estadísticas globales (todas las páginas) ---")
        col_empty = [0] * 6
        total_data_rows = 0
        for page in pdf.pages:
            table = page.extract_table(settings) or []
            for row in table:
                cells = [c or "" for c in row]
                if len([c for c in cells if c]) < 2:
                    continue
                total_data_rows += 1
                for i in range(min(6, len(cells))):
                    if not cells[i].strip():
                        col_empty[i] += 1

        print(f"  Filas con datos: {total_data_rows}")
        labels = ["droga", "marca", "presentacion", "laboratorio", "precio", "pami"]
        for i, label in enumerate(labels):
            pct = (col_empty[i] / total_data_rows * 100) if total_data_rows else 0
            print(f"  Col {i} ({label:15}): {col_empty[i]:5} celdas vacías ({pct:.1f}%)")

if __name__ == "__main__":
    main()
