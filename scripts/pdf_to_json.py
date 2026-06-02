#!/usr/bin/env python3
"""pdf_to_json.py - Descarga el PDF, filtra blacklist, detecta outliers, genera JSON."""

import re
import json
import sys
import statistics
import urllib.request
import ssl
from collections import defaultdict
from pathlib import Path
from datetime import datetime, timezone, timedelta

AR_TZ = timezone(timedelta(hours=-3))

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode   = ssl.CERT_NONE

try:
    import fitz
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pymupdf"])
    import fitz

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# CONFIG
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
OUTLIER_CONFIG = {
    "PRECIO_MINIMO_ARS":  1_800,
    "UMBRAL_CRITICO":     0.10,
    "UMBRAL_RELATIVO":    0.25,
    "MIN_REGISTROS":      3,
    "IQR_FACTOR":         1.5,
    "SCORE_OUTLIER":      20,
    "SCORE_NORMAL":       100,
}

BASE              = Path(__file__).parent.parent
BLACKLIST_PATH    = BASE / "data" / "blacklist.json"
OUTLIER_REPORT    = BASE / "data" / "outlier_report.json"
MEDICAMENTOS_PATH = BASE / "data" / "medicamentos.json"


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# HELPERS PARSEO
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def limpiar_precio(valor):
    if not valor or valor == '-':
        return None
    valor = str(valor).strip()
    valor = valor.replace('.', '').replace(',', '.')
    valor = re.sub(r'[^\d\.]', '', valor)
    try:
        return float(valor)
    except Exception:
        return None

def es_precio(texto):
    if not texto:
        return False
    limpio = re.sub(r'[\$\s]', '', texto)
    return bool(re.match(r'^[\d\.,]+$', limpio))


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# BLACKLIST
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def make_key(m):
    return '|'.join([
        (m.get('droga')        or '').strip().lower(),
        (m.get('marca')        or '').strip().lower(),
        (m.get('presentacion') or '').strip().lower(),
        (m.get('laboratorio')  or '').strip().lower(),
    ])

def cargar_blacklist():
    if BLACKLIST_PATH.exists():
        with open(BLACKLIST_PATH, encoding='utf-8') as f:
            bl = json.load(f)
        print(f"   Lista negra: {len(bl)} entradas cargadas")
        return bl
    print("   Lista negra: no encontrada, se usara vacia")
    return {}

def filtrar_blacklist(medicamentos, blacklist):
    if not blacklist:
        return medicamentos, 0
    filtrados = [m for m in medicamentos if make_key(m) not in blacklist]
    n = len(medicamentos) - len(filtrados)
    if n:
        print(f"   Lista negra: {n} medicamento(s) excluidos")
    return filtrados, n


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# RESCATE DE LABORATORIOS DESPLAZADOS
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def rescatar_laboratorios(medicamentos: list) -> tuple:
    """
    Capa 2 de rescate: para registros que escaparon al parser con
    laboratorio='Desconocido', intenta recuperar el laboratorio desde
    el campo 'presentacion' usando el set de laboratorios conocidos
    construido desde el propio dataset.

    Casos que resuelve:
      A) presentacion == laboratorio conocido exacto
         {"presentacion": "Denver Farma", "laboratorio": "Desconocido"}
         â†’ {"presentacion": "Denver Farma", "laboratorio": "Denver Farma"}

      B) presentacion termina con laboratorio conocido
         {"presentacion": "crema x 30 g Bago", "laboratorio": "Desconocido"}
         â†’ {"presentacion": "crema x 30 g", "laboratorio": "Bago"}

    El laboratorio recuperado usa la capitalizaciÃ³n original del dataset.
    MÃ­nimo de 4 caracteres para evitar matches espurios en el sufijo.
    """

    # Construir Ã­ndice: lower â†’ forma original (primera apariciÃ³n)
    labs_conocidos: dict[str, str] = {}
    for m in medicamentos:
        lab = (m.get('laboratorio') or '').strip()
        if lab and lab != 'Desconocido':
            labs_conocidos.setdefault(lab.lower(), lab)

    rescatados = 0

    for m in medicamentos:
        if m.get('laboratorio') != 'Desconocido':
            continue

        presentacion       = (m.get('presentacion') or '').strip()
        presentacion_lower = presentacion.lower()

        lab_lower    = None
        lab_original = None

        # Caso A: presentacion es exactamente un laboratorio
        if presentacion_lower in labs_conocidos:
            lab_lower    = presentacion_lower
            lab_original = labs_conocidos[lab_lower]

        # Caso B: presentacion termina con un laboratorio (min 4 chars)
        else:
            for ll, lo in labs_conocidos.items():
                if len(ll) >= 4 and presentacion_lower.endswith(ll):
                    lab_lower    = ll
                    lab_original = lo
                    break

        if lab_original:
            m['laboratorio'] = lab_original

            # Limpiar presentacion: si era solo el lab, vaciar;
            # si tenÃ­a contenido antes, quitar el sufijo
            if presentacion_lower == lab_lower:
                m['presentacion'] = ''
            else:
                m['presentacion'] = presentacion[:len(presentacion) - len(lab_lower)].strip()

            rescatados += 1

    return medicamentos, rescatados


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# DETECCION DE OUTLIERS
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def calcular_stats_por_droga(medicamentos):
    grupos = defaultdict(list)
    for m in medicamentos:
        droga  = (m.get('droga') or '').strip().lower()
        precio = m.get('precio')
        if droga and precio and precio > 0:
            grupos[droga].append(precio)

    stats = {}
    for droga, precios in grupos.items():
        n        = len(precios)
        mediana  = statistics.median(precios)
        sorted_p = sorted(precios)
        q1  = statistics.median(sorted_p[:n // 2])     if n >= 2 else sorted_p[0]
        q3  = statistics.median(sorted_p[(n+1) // 2:]) if n >= 2 else sorted_p[-1]
        iqr = q3 - q1
        stats[droga] = {
            "n":         n,
            "mediana":   round(mediana, 2),
            "q1":        round(q1, 2),
            "q3":        round(q3, 2),
            "iqr":       round(iqr, 2),
            "fence_low": round(q1 - OUTLIER_CONFIG["IQR_FACTOR"] * iqr, 2),
        }
    return stats

def evaluar_outlier(med, stats_droga):
    precio   = med.get('precio')
    droga    = (med.get('droga') or '').strip().lower()
    flags    = []
    score    = OUTLIER_CONFIG["SCORE_NORMAL"]
    tipo     = None
    razones  = []

    if not precio or precio <= 0:
        return OUTLIER_CONFIG["SCORE_OUTLIER"], ['precio_obsoleto'], 'invalido', ['precio_invalido_o_cero']

    stats    = stats_droga.get(droga, {})
    n        = stats.get("n", 0)
    mediana  = stats.get("mediana", 0)
    fence_lw = stats.get("fence_low", 0)

    if precio < OUTLIER_CONFIG["PRECIO_MINIMO_ARS"]:
        flags.append('precio_bajo')
        score = min(score, 45)
        tipo  = tipo or 'bajo_absoluto'
        razones.append(f"precio ${precio:,.2f} < minimo ${OUTLIER_CONFIG['PRECIO_MINIMO_ARS']:,}")

    if mediana > 0 and precio < mediana * OUTLIER_CONFIG["UMBRAL_CRITICO"]:
        flags.append('precio_obsoleto')
        score = min(score, OUTLIER_CONFIG["SCORE_OUTLIER"])
        tipo  = 'bajo_critico'
        razones.append(f"precio ${precio:,.2f} < 10% mediana ${mediana:,.2f}")

    elif n >= OUTLIER_CONFIG["MIN_REGISTROS"] and mediana > 0:
        if precio < mediana * OUTLIER_CONFIG["UMBRAL_RELATIVO"]:
            flags.append('precio_sospechoso')
            score = min(score, 35)
            tipo  = tipo or 'bajo_relativo'
            razones.append(f"precio ${precio:,.2f} < 25% mediana ${mediana:,.2f} (n={n})")
        elif fence_lw > 0 and precio < fence_lw:
            flags.append('precio_sospechoso')
            score = min(score, 40)
            tipo  = tipo or 'bajo_iqr'
            razones.append(f"precio ${precio:,.2f} < fence_low ${fence_lw:,.2f}")

    return score, flags, tipo, razones

def detectar_escala(medicamentos, stats_droga):
    def extraer_cant(pres):
        nums = re.findall(r'\b(\d+)\b', str(pres or ''))
        return int(nums[0]) if nums else None

    grupos = defaultdict(list)
    for i, m in enumerate(medicamentos):
        droga  = (m.get('droga') or '').strip().lower()
        marca  = (m.get('marca') or '').strip().upper()
        precio = m.get('precio')
        cant   = extraer_cant(m.get('presentacion'))
        if precio and precio > 0 and cant and cant > 0:
            grupos[(droga, marca)].append({'idx': i, 'precio': precio, 'cantidad': cant, 'ppu': precio / cant})

    marcados = 0
    for items in grupos.values():
        if len(items) < 2:
            continue
        med_ppu = statistics.median([it['ppu'] for it in items])
        if med_ppu <= 0:
            continue
        for item in items:
            if item['ppu'] < med_ppu * 0.20:
                m = medicamentos[item['idx']]
                if 'precio_obsoleto' not in m.get('flags', []):
                    m.setdefault('flags', [])
                    if 'precio_sospechoso' not in m['flags']:
                        m['flags'].append('precio_sospechoso')
                    m['vigencia_score'] = min(m.get('vigencia_score', 100), 35)
                    m.setdefault('outlier_razones', []).append(
                        f"ppu ${item['ppu']:,.2f} << mediana_grupo ${med_ppu:,.2f}"
                    )
                    if not m.get('precio_outlier_tipo'):
                        m['precio_outlier_tipo'] = 'inconsistencia_escala'
                    marcados += 1
    return marcados

def calcular_vigencia(medicamentos):
    print("\nCalculando estadisticas de outliers...")
    stats = calcular_stats_por_droga(medicamentos)
    print(f"   {len(stats)} drogas distintas")

    for m in medicamentos:
        droga = (m.get('droga') or '').strip().lower()
        score, flags, tipo, razones = evaluar_outlier(m, stats)
        m['vigencia_score']      = score
        m['flags']               = flags
        m['precio_outlier_tipo'] = tipo
        m['outlier_razones']     = razones

    n_escala = detectar_escala(medicamentos, stats)

    outliers = [m for m in medicamentos if m.get('flags')]
    reporte  = {
        "timestamp":       datetime.now(AR_TZ).isoformat(),
        "total_registros": len(medicamentos),
        "total_outliers":  len(outliers),
        "outliers": [
            {
                "droga":             m.get('droga'),
                "marca":             m.get('marca'),
                "presentacion":      m.get('presentacion'),
                "laboratorio":       m.get('laboratorio'),
                "precio":            m.get('precio'),
                "precio_outlier_tipo": m.get('precio_outlier_tipo'),
                "razones":           m.get('outlier_razones', []),
                "mediana_droga":     stats.get((m.get('droga') or '').strip().lower(), {}).get('mediana'),
                "n_droga":           stats.get((m.get('droga') or '').strip().lower(), {}).get('n'),
            }
            for m in outliers
        ]
    }

    OUTLIER_REPORT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTLIER_REPORT, 'w', encoding='utf-8') as f:
        json.dump(reporte, f, ensure_ascii=False, indent=2)

    total    = len(medicamentos)
    criticos = [o for o in reporte['outliers'] if o['precio_outlier_tipo'] == 'bajo_critico']
    print(f"\nOUTLIERS: {len(outliers)}/{total} ({100*len(outliers)/total:.1f}%) | Escala: +{n_escala} | Criticos: {len(criticos)}")
    for o in sorted(criticos, key=lambda x: x['precio'] or 0)[:10]:
        print(f"   {o['marca']} ({o['droga']}): ${o['precio']:,.2f}  [mediana: ${o['mediana_droga']:,.2f}]")
    print(f"   Reporte: {OUTLIER_REPORT}")

    return medicamentos


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# MAIN
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def main():
    pdf_url = "https://siafar.com/precios/pdf/"
    print(f"Descargando: {pdf_url}")

    req = urllib.request.Request(pdf_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30, context=ssl_context) as r:
        pdf_bytes = r.read()
    print(f"Tamano: {len(pdf_bytes)} bytes")

    doc          = fitz.open(stream=pdf_bytes, filetype="pdf")
    medicamentos = []

    for pagina_num in range(len(doc)):
        texto  = doc[pagina_num].get_text()
        lineas = [l.strip() for l in texto.split('\n') if l.strip()]
        i = 0
        while i < len(lineas):
            linea = lineas[i]
            if 'MONODROGA' in linea or 'pag' in linea.lower():
                i += 1; continue
            if es_precio(linea):
                i += 1; continue

            # â”€â”€ CAPA 1: detecciÃ³n de desplazamiento en tiempo de parse â”€â”€
            #
            # Estructura normal (5 campos):
            #   i+0  droga
            #   i+1  marca
            #   i+2  presentacion
            #   i+3  laboratorio
            #   i+4  precio
            #
            # Estructura desplazada (4 campos, lab ausente en PDF):
            #   i+0  droga
            #   i+1  marca
            #   i+2  laboratorio  â† ocupa el slot de presentacion
            #   i+3  precio       â† sube un lugar
            #
            # DetecciÃ³n: si lineas[i+3] ya es precio, el laboratorio
            # se desplazÃ³ a lineas[i+2] y no hay presentacion separada.

            if i + 3 < len(lineas) and es_precio(lineas[i+3]):
                # Estructura de 4 campos: lab en slot de presentacion
                droga        = linea
                marca        = lineas[i+1]
                presentacion = ''
                laboratorio  = lineas[i+2]
                precio_str   = lineas[i+3]
                avance       = 4
            elif i + 4 < len(lineas):
                # Estructura normal de 5 campos
                droga        = linea
                marca        = lineas[i+1]
                presentacion = lineas[i+2]
                laboratorio  = lineas[i+3]
                precio_str   = lineas[i+4]
                avance       = 5
            else:
                i += 1; continue

            if es_precio(precio_str):
                precio = limpiar_precio(precio_str)
                if precio and droga:
                    medicamentos.append({
                        'droga':        droga.lower(),
                        'marca':        marca.upper(),
                        'presentacion': presentacion,
                        'laboratorio':  laboratorio if not es_precio(laboratorio) else 'Desconocido',
                        'precio':       precio,
                    })
                i += avance; continue

            i += 1

        if (pagina_num + 1) % 10 == 0:
            print(f"Pagina {pagina_num + 1}: {len(medicamentos)} medicamentos")

    doc.close()
    print(f"\nTotal extraido: {len(medicamentos)}")

    if not medicamentos:
        print("No se extrajo ningun medicamento")
        sys.exit(1)

    # â”€â”€ CAPA 2: rescate post-parse con laboratorios conocidos â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("\nRescatando laboratorios desplazados...")
    medicamentos, n_rescatados = rescatar_laboratorios(medicamentos)
    n_desconocidos = sum(1 for m in medicamentos if m.get('laboratorio') == 'Desconocido')
    print(f"   Rescatados: {n_rescatados} | Sin recuperar: {n_desconocidos}")

    print("\nAplicando lista negra...")
    blacklist            = cargar_blacklist()
    medicamentos, n_bl   = filtrar_blacklist(medicamentos, blacklist)
    medicamentos         = calcular_vigencia(medicamentos)

    ahora_ar  = datetime.now(AR_TZ)
    fecha_str = ahora_ar.strftime("%Y-%m-%d %H:%M:%S")
    data = {
        "fecha":        fecha_str,
        "fuente":       pdf_url,
        "total":        len(medicamentos),
        "blacklisted":  n_bl,
        "medicamentos": medicamentos,
    }

    MEDICAMENTOS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MEDICAMENTOS_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))

    print(f"\nGuardado: {MEDICAMENTOS_PATH}")
    print(f"Total: {len(medicamentos)} | Excluidos (blacklist): {n_bl} | Fecha: {fecha_str}")

if __name__ == "__main__":
    main()
