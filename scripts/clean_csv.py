#!/usr/bin/env python3
"""
Limpia el CSV generado por el parser v3/v4:
- Separa marca de presentación cuando están pegadas
- Limpia caracteres raros
- Estandariza formatos
"""

import csv
import re

def limpiar_campo(texto):
    """Limpia caracteres raros y espacios"""
    if not texto:
        return ""
    texto = re.sub(r'\s+', ' ', texto)
    texto = texto.strip()
    return texto

def extraer_presentacion_y_marca(marca_raw):
    """
    Intenta separar presentación de marca.
    Ejemplo: "TALPRAM 10 comp.rec.x 30" → ("TALPRAM", "10 comp.rec.x 30")
    """
    if not marca_raw:
        return marca_raw, ""
    
    # Buscar patrones de presentación (número + mg/ml + posible rec.x)
    patrones = [
        # 10 comp.rec.x 30
        r'(\d+\s+(?:comp\.?rec\.?x?\s*\d+))',
        # 10 mg comp.x 30
        r'(\d+\s*(?:mg|ml|g|ui|mcg)\s+(?:comp|caps|tabletas)\s*x?\s*\d*)',
        # 20 mg (solo dosis)
        r'(\d+\s*(?:mg|ml|g|ui|mcg))',
        # rec.x 30
        r'(rec\.?x?\s*\d+)',
    ]
    
    for patron in patrones:
        match = re.search(patron, marca_raw, re.I)
        if match:
            presentacion = match.group(1).strip()
            marca = marca_raw[:match.start()].strip()
            return marca, presentacion
    
    return marca_raw, ""

def arreglar_droga(droga):
    """Limpia y estandariza la droga"""
    if not droga:
        return ""
    # Eliminar números al final
    droga = re.sub(r'\s+\d+$', '', droga)
    # Eliminar puntos finales
    droga = re.sub(r'\.$', '', droga)
    # Poner en minúsculas
    droga = droga.lower()
    return droga

def main():
    input_file = 'data/medicamentos.csv'
    output_file = 'data/medicamentos_limpio.csv'
    
    with open(input_file, 'r', encoding='utf-8') as infile, \
         open(output_file, 'w', newline='', encoding='utf-8') as outfile:
        
        reader = csv.reader(infile)
        writer = csv.writer(outfile)
        
        header = next(reader)
        writer.writerow(['droga', 'marca', 'presentacion', 'laboratorio', 'precio'])
        
        for row in reader:
            if len(row) < 5:
                continue
            
            droga = limpiar_campo(row[0])
            marca_raw = limpiar_campo(row[1])
            presentacion_original = limpiar_campo(row[2])
            laboratorio = limpiar_campo(row[3])
            precio = limpiar_campo(row[4])
            
            droga = arreglar_droga(droga)
            
            # Si no hay presentación, intentar extraerla de la marca
            if not presentacion_original and marca_raw:
                marca, presentacion = extraer_presentacion_y_marca(marca_raw)
            else:
                marca = marca_raw
                presentacion = presentacion_original
            
            # Si la marca está vacía, intentar usar la droga como marca (último recurso)
            if not marca and droga:
                marca = droga.upper()
            
            writer.writerow([droga, marca, presentacion, laboratorio, precio])
    
    print(f"✅ CSV limpiado")

if __name__ == '__main__':
    main()
