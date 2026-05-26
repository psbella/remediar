#!/usr/bin/env python3
import csv
import json
import re
import statistics
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict

BASE_DIR = Path(__file__).parent.parent
CSV_PATH = BASE_DIR / "data" / "medicamentos.csv"
JSON_PATH = BASE_DIR / "data" / "medicamentos.json"


def droga_valida(texto):
    if not texto:
        return False
    if ',' in texto:
        return True
    if len(texto) > 25:
        return True
    return False


def corregir_registro(droga, marca, presentacion, laboratorio, precio):
    if re.match(r'^[-0\s]+$', droga) or droga == '':
        if marca:
            droga, marca = marca, droga
    if droga_valida(marca) and not droga_valida(droga):
        droga, marca = marca, droga
    
    droga = re.sub(r'^-\d+\s*', '', droga)
    droga = re.sub(r'^-\s*', '', droga)
    droga = droga.lower().strip()
    marca = marca.upper().strip()
    
    if re.search(r'\d+\s*(mg|ml|g|ui|comp|tableta|capsula|x\s*\d+)', laboratorio, re.I):
        laboratorio = 'Desconocido'
    else:
        laboratorio = laboratorio.strip()
    
    return droga, marca, presentacion.strip(), laboratorio, precio


def calcular_scores(medicamentos):
    """Solo marca precios ANORMALMENTE BAJOS (datos viejos/incorrectos)"""
    # Agrupar precios por droga
    precios_por_droga = defaultdict(list)
    for m in medicamentos:
        if m.get('precio') and m['precio'] > 0:
            precios_por_droga[m['droga']].append(m['precio'])
    
    # Calcular medianas por droga
    medianas = {}
    for droga, precios in precios_por_droga.items():
        if len(precios) >= 2:
            medianas[droga] = statistics.median(precios)
    
    sospechosos = 0
    for m in medicamentos:
        precio = m.get('precio', 0)
        droga = m['droga']
        mediana = medianas.get(droga)
        
        # Por defecto, no es sospechoso
        m['vigencia_score'] = 100
        m['flags'] = []
        
        # Solo marcar si el precio es ANORMALMENTE BAJO (menos del 30% de la mediana)
        if mediana and mediana > 0:
            if precio < mediana * 0.3:
                m['vigencia_score'] = 30
                m['flags'] = ['precio_obsoleto']
                sospechosos += 1
            elif precio < mediana * 0.5:
                m['vigencia_score'] = 60
                m['flags'] = ['precio_bajo']
                sospechosos += 1
        else:
            # Sin datos de referencia, marcar solo si es muy barato (< $1000)
            if precio < 1000 and precio > 0:
                m['vigencia_score'] = 40
                m['flags'] = ['precio_sospechoso']
                sospechosos += 1
    
    print(f"🔍 Medicamentos con precio obsoleto/bajo: {sospechosos}")
    return medicamentos


def main():
    medicamentos = []
    
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            droga = row.get('droga', '')
            marca = row.get('marca', '')
            presentacion = row.get('presentacion', '')
            laboratorio = row.get('laboratorio', '')
            
            try:
                precio = float(row['precio']) if row.get('precio') else None
            except (ValueError, TypeError):
                precio = None
            
            if not precio:
                continue
            
            droga, marca, presentacion, laboratorio, precio = corregir_registro(
                droga, marca, presentacion, laboratorio, precio
            )
            
            medicamentos.append({
                'droga': droga,
                'marca': marca,
                'presentacion': presentacion,
                'laboratorio': laboratorio if laboratorio else 'Desconocido',
                'precio': round(precio, 2),
            })
    
    print(f"📊 Registros leídos: {len(medicamentos)}")
    
    # Calcular scores (solo marca precios bajos)
    medicamentos = calcular_scores(medicamentos)
    
    output = {
        "fecha": datetime.now(timezone.utc).isoformat(),
        "fuente": "medicamentos.csv",
        "total": len(medicamentos),
        "medicamentos": medicamentos
    }
    
    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"✅ JSON generado: {len(medicamentos)} registros")

if __name__ == "__main__":
    main()
