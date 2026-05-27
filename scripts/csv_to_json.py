#!/usr/bin/env python3
import csv
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
CSV_PATH = DATA_DIR / "medicamentos.csv"
JSON_PATH = DATA_DIR / "medicamentos.json"

def get_argentina_time():
    utc_now = datetime.now(timezone.utc)
    argentina_tz = timezone(timedelta(hours=-3))
    return utc_now.astimezone(argentina_tz)

def csv_to_json():
    medicamentos = []
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            precio = float(row['precio']) if row.get('precio') else None
            copago_pami = float(row['copago_pami']) if row.get('copago_pami') and row['copago_pami'] != 'None' else None
            medicamentos.append({
                'droga': row.get('droga', ''),
                'marca': row.get('marca', ''),
                'presentacion': row.get('presentacion', ''),
                'laboratorio': row.get('laboratorio', 'Desconocido'),
                'precio': precio,
                'copago_pami': copago_pami
            })
    ahora = get_argentina_time()
    fecha_str = ahora.strftime("%Y-%m-%d %H:%M:%S")
    data = {
        "fecha": fecha_str,
        "fuente": "medicamentos.csv",
        "total": len(medicamentos),
        "medicamentos": medicamentos
    }
    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ JSON generado: {len(medicamentos)} registros")
    print(f"📅 Fecha: {fecha_str}")

if __name__ == "__main__":
    csv_to_json()
