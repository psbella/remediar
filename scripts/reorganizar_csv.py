#!/usr/bin/env python3
"""
Reorganiza las columnas del CSV de SIAFAR.
Estructura original: droga, marca, presentacion, laboratorio, precio, pami
"""

import csv
import re

LABS = {
    "abbott epd", "abbvie", "alcon", "amgen", "andrómaco", "aponor",
    "ariston", "aspen", "aspen pharma", "astrazeneca", "austral",
    "b braun", "bacon", "bagó", "baliarda", "bayer (ph)", "bayer consumer",
    "beta", "biocontrol", "biofactor", "biol", "bioprofarma bag",
    "biosidus s.a.u.", "biosintex", "biosintex retai", "biotechno pharm",
    "biotenk", "biotoscana", "csl behring", "cabuchi", "casasco",
    "cassará", "celtyc", "cetus", "cevallos", "craveri", "dallas",
    "denver farma", "domínguez", "donato zurlo", "dr madaus", "duncan",
    "e j gezzi", "eczane", "elea", "eriochem", "eurofarma", "eurolab",
    "everex", "excelentia", "fabra", "fada pharma", "fecofar", "ferring",
    "finadiet", "fortbenton", "francelab", "fresenius kabi", "gp pharm",
    "gador", "galderma", "gemabiotech", "genomma lab", "glaxosmithkline",
    "glenmark", "gobbi", "gramón", "gray", "hlb pharma", "hemoderivados",
    "ima", "isa", "imvi", "infinity pharma", "iraola", "isdin",
    "janssen-cilag", "jayor", "kemex", "kilab", "klonal", "lkm",
    "lkm onco/especi", "lafedar", "lagos", "lazar", "lepetit", "lersan",
    "lundbeck", "mr pharma", "msd argentina", "mar", "max vision",
    "medipharma", "medisol", "merck serono", "merz", "monserrat",
    "montpellier", "mundipharma", "natufarma", "nolter", "northia",
    "novartis", "novo nordisk", "novoplos", "omicron", "oxapharma",
    "panalab", "pfizer", "pharmadorf", "pharmanove", "pharmatrix", "poen",
    "pretoria", "química luar", "raffo", "raymos-megalabs", "richet",
    "richmond", "rivero", "roche", "roemmers", "ronnet", "rontag",
    "rospaw", "rossmore pharma", "roux ocefa", "sanitas", "sanofi-aventis",
    "sant gall", "savant consumer", "savant generic", "savant pharma",
    "schafer", "scott pharma", "scott-cassará", "seqirus", "sertex",
    "servier", "sidus", "siegfried", "soubeiran chobe", "techsphere",
    "temis-lostaló", "teva argentina", "trb-pharma", "tuteur", "valmax",
    "valuge", "vannier", "varifarma", "veinfar", "vent 3", "wunder pharm"
}

def normalizar(texto):
    if not texto:
        return ""
    return re.sub(r'\s+', ' ', texto).strip()

def es_laboratorio(texto):
    return texto and texto.lower() in LABS

def es_marca_valida(texto):
    return texto and texto.isupper() and len(texto) > 1

def main():
    input_file = 'data/medicamentos.csv'
    output_file = 'data/medicamentos_reorganizado.csv'
    
    with open(input_file, 'r', encoding='utf-8') as infile, \
         open(output_file, 'w', newline='', encoding='utf-8') as outfile:
        
        reader = csv.reader(infile)
        writer = csv.writer(outfile)
        
        header = next(reader)
        writer.writerow(['droga', 'marca', 'presentacion', 'laboratorio', 'precio'])
        
        for row in reader:
            if len(row) < 5:
                continue
            
            # Índices: 0=droga, 1=marca, 2=presentacion, 3=laboratorio, 4=precio
            col0 = normalizar(row[0])
            col1 = normalizar(row[1])
            col2 = normalizar(row[2])
            col3 = normalizar(row[3])
            col4 = normalizar(row[4])
            
            # 1. Precio (col4)
            precio = col4
            
            # 2. Laboratorio (col3 o buscar en otras si está vacío)
            laboratorio = col3 if es_laboratorio(col3) else ""
            if not laboratorio:
                for col in [col2, col1, col0]:
                    if es_laboratorio(col):
                        laboratorio = col
                        break
            
            # 3. Marca (col1, debe ser MAYÚSCULAS)
            marca = col1 if es_marca_valida(col1) else ""
            if not marca and es_marca_valida(col2):
                marca = col2
            
            # 4. Presentación (col2, si no es marca ni laboratorio)
            presentacion = ""
            if col2 and col2 not in [marca, laboratorio]:
                presentacion = col2
            elif col1 and col1 not in [marca, laboratorio] and re.search(r'\d', col1):
                presentacion = col1
            
            # 5. Droga (col0, en minúsculas)
            droga = col0.lower() if col0 else ""
            if not droga and col1 and col1 not in [marca, presentacion, laboratorio]:
                droga = col1.lower()
            
            writer.writerow([droga, marca, presentacion, laboratorio, precio])
    
    print("✅ CSV reorganizado")

if __name__ == '__main__':
    main()
