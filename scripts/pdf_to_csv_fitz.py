#!/usr/bin/env python3
"""
Script para extraer tabla de precios de medicamentos de PDF usando PyMuPDF (fitz).
Procesa todas las páginas extrayendo filas por posición vertical.
"""

import os
import re
import csv
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import fitz  # PyMuPDF


def download_pdf(url: str, output_path: str) -> str:
    """Descarga el PDF desde la URL si no existe localmente."""
    if os.path.exists(output_path):
        print(f"✅ Usando PDF existente: {output_path}")
        return output_path
    
    print(f"📥 Descargando PDF desde: {url}")
    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        with urllib.request.urlopen(req, timeout=60) as response:
            with open(output_path, 'wb') as f:
                f.write(response.read())
        print(f"✅ PDF guardado: {output_path}")
        return output_path
    except Exception as e:
        print(f"❌ Error descargando PDF: {e}")
        raise


def clean_price(price_str: str) -> str:
    """Limpia el precio: reemplaza coma por punto, elimina puntos de miles."""
    if not price_str or price_str == '-':
        return ''
    # Eliminar todo excepto dígitos, comas y puntos
    cleaned = re.sub(r'[^\d,.]', '', price_str)
    # Si tiene coma y punto, asumir que coma es decimal (formato ARG)
    if ',' in cleaned and '.' in cleaned:
        # Última coma es decimal, puntos son miles
        if cleaned.rfind(',') > cleaned.rfind('.'):
            cleaned = cleaned.replace('.', '').replace(',', '.')
        else:
            cleaned = cleaned.replace(',', '')
    elif ',' in cleaned:
        cleaned = cleaned.replace(',', '.')
    return cleaned


def is_header_line(text: str) -> bool:
    """Determina si una línea es el encabezado de la tabla."""
    header_patterns = [
        'MONODROGA', 'NOMBRE', 'PRESENTACION', 'LABORATORIO', 'PRECIO',
        'Precio.Afil.PAMI', 'pag', 'Page'
    ]
    text_upper = text.upper()
    for pattern in header_patterns:
        if pattern.upper() in text_upper:
            return True
    return False


def extract_table_from_pdf(pdf_path: str) -> List[Dict[str, str]]:
    """
    Extrae la tabla del PDF usando coordenadas de texto.
    La tabla tiene 6 columnas: droga, nombre, presentacion, laboratorio, precio, precio_pami
    """
    doc = fitz.open(pdf_path)
    all_rows = []
    header_found = False
    page_num = 0
    
    # Coordenadas X aproximadas de las columnas (se ajustarán)
    # Orden: droga, nombre, presentacion, laboratorio, precio, pami
    x_cols = [72, 200, 310, 430, 500, 580]  # Valores iniciales
    
    # Para debug
    pages_with_data = 0
    
    for page_num, page in enumerate(doc, 1):
        # Obtener texto y bloques
        text = page.get_text()
        
        # Detectar estructura de columnas en la primera página con encabezado
        blocks = page.get_text("dict")
        
        # Buscar encabezado para determinar columnas
        page_header_found = False
        for block in blocks.get("blocks", []):
            if "lines" in block:
                for line in block["lines"]:
                    line_text = " ".join([span["text"] for span in line["spans"]])
                    if is_header_line(line_text) and not page_header_found:
                        page_header_found = True
                        header_found = True
                        # Extraer coordenadas X de las columnas del encabezado
                        x_coords = []
                        for span in line["spans"]:
                            if span["text"].strip():
                                x_coords.append(round(span["bbox"][0], 2))
                        
                        if len(x_coords) >= 5:
                            x_cols = x_coords[:6] if len(x_coords) >= 6 else x_coords + [x_coords[-1] + 80] * (6 - len(x_coords))
                            print(f"📐 Página {page_num}: Columnas X = {x_cols}")
                        break
        
        # Si no encontramos encabezado en esta página, intentar con valores por defecto
        if not page_header_found and not header_found:
            # Primera aproximación: buscar por patrones
            for block in blocks.get("blocks", []):
                if "lines" in block:
                    for line in block["lines"]:
                        spans = line["spans"]
                        if len(spans) >= 3:
                            first_span = spans[0]["text"].strip().upper()
                            if 'MONODROGA' in first_span or 'ACIDO' in first_span or 'ABACAVIR' in first_span:
                                page_header_found = True
                                header_found = True
                                x_coords = []
                                for span in spans:
                                    if span["text"].strip():
                                        x_coords.append(round(span["bbox"][0], 2))
                                if len(x_coords) >= 5:
                                    x_cols = x_coords[:6] if len(x_coords) >= 6 else x_coords + [x_coords[-1] + 80] * (6 - len(x_coords))
                                print(f"📐 Página {page_num}: Columnas X (alternativo) = {x_cols}")
                                break
                if page_header_found:
                    break
        
        # Extraer filas usando líneas de texto
        page_rows = []
        
        # Obtener todas las líneas de texto con sus posiciones Y
        lines_with_y = []
        for block in blocks.get("blocks", []):
            if "lines" in block:
                for line in block["lines"]:
                    if not line["spans"]:
                        continue
                    
                    # Calcular Y promedio de la línea
                    y_pos = sum(span["bbox"][1] for span in line["spans"]) / len(line["spans"])
                    line_text = " ".join([span["text"].strip() for span in line["spans"]])
                    
                    if line_text and not is_header_line(line_text):
                        lines_with_y.append((y_pos, line_text, line["spans"]))
        
        # Ordenar por posición Y
        lines_with_y.sort(key=lambda x: x[0])
        
        # Agrupar líneas en filas (si están muy cerca, son parte de la misma fila)
        rows = []
        current_row = []
        last_y = None
        
        for y_pos, line_text, spans in lines_with_y:
            if last_y is None or (y_pos - last_y) < 12:  # Mismo grupo si distancia < 12pt
                current_row.append((y_pos, line_text, spans))
            else:
                if current_row:
                    rows.append(current_row)
                current_row = [(y_pos, line_text, spans)]
            last_y = y_pos
        
        if current_row:
            rows.append(current_row)
        
        # Procesar cada fila
        for row_parts in rows:
            if not row_parts:
                continue
            
            # Combinar spans de la fila
            all_spans = []
            for _, _, spans in row_parts:
                all_spans.extend(spans)
            
            if not all_spans:
                continue
            
            # Ordenar spans por X
            all_spans.sort(key=lambda s: s["bbox"][0])
            
            # Asignar spans a columnas según su posición X
            col_values = [''] * 6
            
            for span in all_spans:
                span_x = span["bbox"][0]
                span_text = span["text"].strip()
                if not span_text:
                    continue
                
                # Determinar columna
                col_idx = 5  # Default a última columna
                for i, x_col in enumerate(x_cols):
                    if span_x < (x_col + 45):  # Tolerancia de 45px
                        col_idx = i
                        break
                
                if col_idx < 6:
                    if col_values[col_idx]:
                        col_values[col_idx] += " " + span_text
                    else:
                        col_values[col_idx] = span_text
            
            # Limpiar valores
            droga = col_values[0].lower().strip() if col_values[0] else ''
            marca = col_values[1].strip() if col_values[1] else ''
            presentacion = col_values[2].strip() if col_values[2] else ''
            laboratorio = col_values[3].strip() if col_values[3] else ''
            precio = clean_price(col_values[4]) if col_values[4] else ''
            
            # Validar: debe tener al menos droga y precio
            if droga and precio:
                # Verificar que no sea encabezado nuevamente
                if not is_header_line(droga) and not is_header_line(marca) and len(droga) < 100:
                    page_rows.append({
                        'droga': droga,
                        'marca': marca,
                        'presentacion': presentacion,
                        'laboratorio': laboratorio,
                        'precio': precio
                    })
        
        if page_rows:
            pages_with_data += 1
            all_rows.extend(page_rows)
            print(f"📄 Página {page_num:3d}: {len(page_rows)} registros (Total acumulado: {len(all_rows)})")
    
    doc.close()
    print(f"\n📊 Procesadas {page_num} páginas, {pages_with_data} páginas con datos, {len(all_rows)} registros extraídos")
    return all_rows


def save_to_csv(data: List[Dict[str, str]], output_path: str) -> None:
    """Guarda los datos en un archivo CSV."""
    if not data:
        print("⚠️ No hay datos para guardar")
        return
    
    fieldnames = ['droga', 'marca', 'presentacion', 'laboratorio', 'precio']
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    
    print(f"✅ CSV guardado: {output_path}")
    print(f"   Registros: {len(data)}")


def generate_report(data: List[Dict[str, str]], output_path: str) -> None:
    """Genera un reporte con estadísticas básicas."""
    if not data:
        return
    
    # Estadísticas por droga
    droga_count = {}
    for row in data:
        droga = row['droga']
        droga_count[droga] = droga_count.get(droga, 0) + 1
    
    top_drogas = sorted(droga_count.items(), key=lambda x: x[1], reverse=True)[:20]
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("=== REPORTE DE EXTRACCIÓN ===\n\n")
        f.write(f"Total de registros extraídos: {len(data)}\n")
        f.write(f"Total de drogas únicas: {len(droga_count)}\n\n")
        f.write("=== TOP 20 DROGAS MÁS FRECUENTES ===\n\n")
        for droga, count in top_drogas:
            f.write(f"  {droga}: {count} presentaciones\n")
    
    print(f"✅ Reporte guardado: {output_path}")


def main():
    # Configuración
    pdf_url = "https://siafar.com/precios/pdf/Precios260527.pdf"
    script_dir = Path(__file__).parent.parent
    data_dir = script_dir / "data"
    data_dir.mkdir(exist_ok=True)
    
    pdf_path = data_dir / "Precios260527.pdf"
    csv_path = data_dir / "medicamentos.csv"
    report_path = data_dir / "extraction_report.txt"
    
    print("=" * 60)
    print("📊 EXTRACTOR DE PRECIOS DE MEDICAMENTOS - PyMuPDF")
    print("=" * 60)
    print(f"📁 Directorio: {script_dir}")
    print(f"📄 Salida CSV: {csv_path}")
    print()
    
    try:
        # Descargar PDF
        download_pdf(pdf_url, str(pdf_path))
        
        # Extraer tabla
        print("\n🔄 Procesando PDF con PyMuPDF...")
        data = extract_table_from_pdf(str(pdf_path))
        
        # Guardar resultados
        save_to_csv(data, str(csv_path))
        generate_report(data, str(report_path))
        
        # Mostrar primeras filas como muestra
        if data:
            print("\n📋 Muestra de datos extraídos (primeras 5 filas):")
            print("-" * 80)
            for i, row in enumerate(data[:5]):
                print(f"{i+1}. {row['droga']} | {row['marca'][:30]} | {row['presentacion'][:35]} | {row['laboratorio'][:25]} | ${row['precio']}")
        
        print("\n✅ Proceso completado exitosamente")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
