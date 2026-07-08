"""etl/config.py - Constantes y paths compartidos por todos los módulos del ETL."""

import ssl
from pathlib import Path
from datetime import timezone, timedelta

import certifi

AR_TZ = timezone(timedelta(hours=-3))
ssl_context = ssl.create_default_context(cafile=certifi.where())

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG OUTLIERS
# ─────────────────────────────────────────────────────────────────────────────
OUTLIER_CONFIG = {
    "PRECIO_MINIMO_ARS":  1_800,
    "UMBRAL_CRITICO":     0.10,
    "UMBRAL_RELATIVO":    0.25,
    "MIN_REGISTROS":      3,
    "IQR_FACTOR":         1.5,
    "SCORE_OUTLIER":      20,
    "SCORE_NORMAL":       100,
}

# ─────────────────────────────────────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────────────────────────────────────
BASE              = Path(__file__).parent.parent.parent
BLACKLIST_PATH    = BASE / "data" / "blacklist.json"
OUTLIER_REPORT    = BASE / "data" / "outlier_report.json"
MEDICAMENTOS_PATH = BASE / "data" / "medicamentos.json"
PRES_DEBUG_PATH   = BASE / "data" / "presentaciones_debug.csv"
DROGA_FIXES_PATH  = BASE / "data" / "droga_fixes.json"

PAMI_PATH        = BASE / "data" / "pami.xlsx"
PAMI_RESOURCE_ID = "92ad6862-af8e-4047-b2cb-4bfef705feb3"
PAMI_API_URL     = f"https://datos.pami.org.ar/api/3/action/resource_show?id={PAMI_RESOURCE_ID}"
