#!/usr/bin/env python3
"""
enriquecer.py — Agrega campos estructurados de presentación a normalizado.json.

Input:  data/normalizado.json  (generado por normalizar.py)
Output: data/medicamentos.json (dataset final de producción)
        data/presentaciones_debug.csv

Qué hace:
  - Parsea el campo `presentacion` con _parsear_presentacion()
  - Agrega pres_forma, pres_dosis, pres_unidad, pres_cantidad a cada registro
  - Fallbacks de dosis: marca → nombre de marca → PAMI
  - Marca categorías sin dosis estructural (pres_dosis_fuente: "no_aplica")
  - Genera presentaciones_debug.csv para auditoría
"""

import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

AR_TZ = timezone(timedelta(hours=-3))

BASE              = Path(__file__).parent.parent
NORMALIZADO_PATH  = BASE / "data" / "normalizado.json"
MEDICAMENTOS_PATH = BASE / "data" / "medicamentos.json"
PRES_DEBUG_PATH   = BASE / "data" / "presentaciones_debug.csv"
PAMI_PATH         = BASE / "data" / "pami.xlsx"

# ─────────────────────────────────────────────────────────────────────────────
# PARSER DE PRESENTACIONES (debug CSV)
# ─────────────────────────────────────────────────────────────────────────────

_FORMAS_NORM_PRES = {
    'comp.rec.ran': 'COMPRIMIDOS RECUBIERTOS RANURADOS',
    'comp.rec.gast': 'COMPRIMIDOS GASTRORRESISTENTES',
    'comp.rec.lib.prol': 'COMPRIMIDOS LIBERACIÓN PROLONGADA RECUBIERTOS',
    'comp.rec.acc.prol': 'COMPRIMIDOS ACCIÓN PROLONGADA RECUBIERTOS',
    'comp.rec.ap': 'COMPRIMIDOS ACCIÓN PROLONGADA RECUBIERTOS',
    'comp.lib.prol': 'COMPRIMIDOS LIBERACIÓN PROLONGADA',
    'comp.lib.cont': 'COMPRIMIDOS LIBERACIÓN CONTROLADA',
    'comp.lib.contr': 'COMPRIMIDOS LIBERACIÓN CONTROLADA',
    'comp.lib.modif': 'COMPRIMIDOS LIBERACIÓN MODIFICADA',
    'comp.rec': 'COMPRIMIDOS RECUBIERTOS',
    'comp. rec': 'COMPRIMIDOS RECUBIERTOS',
    'comp.ran': 'COMPRIMIDOS RANURADOS',
    'comp.ranur': 'COMPRIMIDOS RANURADOS',
    'comp.birranur': 'COMPRIMIDOS BIRRANURADOS',
    'comp.birran': 'COMPRIMIDOS BIRRANURADOS',
    'comp.trirran': 'COMPRIMIDOS TRIRRANURADOS',
    'comp.subl': 'COMPRIMIDOS SUBLINGUALES',
    'comp.mast': 'COMPRIMIDOS MASTICABLES',
    'comp.efer': 'COMPRIMIDOS EFERVESCENTES',
    'comp.ef': 'COMPRIMIDOS EFERVESCENTES',
    'comp.dispers': 'COMPRIMIDOS DISPERSABLES',
    'comp.acc.prol': 'COMPRIMIDOS ACCIÓN PROLONGADA',
    'comp.ap': 'COMPRIMIDOS ACCIÓN PROLONGADA',
    'comp': 'COMPRIMIDOS',
    'cáps.blandas': 'CÁPSULAS BLANDAS', 'caps.blandas': 'CÁPSULAS BLANDAS',
    'cáps.duras': 'CÁPSULAS DURAS', 'caps.duras': 'CÁPSULAS DURAS',
    'cáps.bl': 'CÁPSULAS BLANDAS', 'caps.bl': 'CÁPSULAS BLANDAS',
    'cáps. bl': 'CÁPSULAS BLANDAS', 'caps. bl': 'CÁPSULAS BLANDAS',
    'cáps.lib.cont': 'CÁPSULAS LIBERACIÓN CONTROLADA',
    'cáps.lib.contr': 'CÁPSULAS LIBERACIÓN CONTROLADA',
    'caps.lib.cont': 'CÁPSULAS LIBERACIÓN CONTROLADA',
    'cáps.lib.prol': 'CÁPSULAS LIBERACIÓN PROLONGADA',
    'caps.lib.prol': 'CÁPSULAS LIBERACIÓN PROLONGADA',
    'cáps.p/inhalar': 'CÁPSULAS PARA INHALACIÓN',
    'cáps.p/inh': 'CÁPSULAS PARA INHALACIÓN',
    'caps.p/inh': 'CÁPSULAS PARA INHALACIÓN',
    'cáps': 'CÁPSULAS', 'caps': 'CÁPSULAS',
    'iny.liof': 'INYECTABLE LIOFILIZADO',
    'iny.f.a': 'INYECTABLE FRASCO AMPOLLA',
    'iny.a': 'INYECTABLE AMPOLLA',
    'iny': 'INYECTABLE',
    'liof.f.a': 'LIOFILIZADO FRASCO AMPOLLA',
    'f.a.liof': 'FRASCO AMPOLLA LIOFILIZADO',
    'liof': 'LIOFILIZADO',
    'f.a': 'FRASCO AMPOLLA',
    'fco.a': 'FRASCO AMPOLLA', 'fco.gotero': 'FRASCO GOTERO', 'fco': 'FRASCO',
    'a.': 'AMPOLLA', 'a': 'AMPOLLA', 'amp': 'AMPOLLA',
    'vial': 'VIAL', 'bolsa': 'BOLSA',
    'jga.prell': 'JERINGA PRELLENADA', 'lap.prell': 'LAPICERA PRELLENADA',
    'jga': 'JERINGA', 'autoinyector': 'AUTOINYECTOR', 'autoin': 'AUTOINYECTOR',
    'lap': 'LAPICERA', 'pluma': 'LAPICERA', 'env': 'ENVASE',
    'sol.oft': 'SOLUCIÓN OFTÁLMICA', 'sol.of': 'SOLUCIÓN OFTÁLMICA',
    'sol.oral': 'SOLUCIÓN ORAL', 'sol. oral': 'SOLUCIÓN ORAL',
    'sol.top': 'SOLUCIÓN TÓPICA', 'sol.tópica': 'SOLUCIÓN TÓPICA',
    'sol.neb': 'SOLUCIÓN NEBULIZABLE', 'sol.p/neb': 'SOLUCIÓN NEBULIZABLE',
    'sol.p/nebulizar': 'SOLUCIÓN NEBULIZABLE', 'sol.iny': 'SOLUCIÓN INYECTABLE',
    'sol': 'SOLUCIÓN',
    'susp.oral': 'SUSPENSIÓN ORAL', 'susp.nasal': 'SUSPENSIÓN NASAL', 'susp': 'SUSPENSIÓN',
    'jbe': 'JARABE', 'jarabe': 'JARABE', 'liq': 'LÍQUIDO', 'elixir': 'ELIXIR',
    'gts.oft': 'GOTAS OFTÁLMICAS', 'gts.óticas': 'GOTAS ÓTICAS',
    'gts.ót': 'GOTAS ÓTICAS', 'gts.nas': 'GOTAS NASALES', 'gts': 'GOTAS',
    'colirio': 'COLIRIO',
    'cr.dérmica': 'CREMA DÉRMICA', 'cr.dérm': 'CREMA DÉRMICA', 'cr': 'CREMA',
    'gel': 'GEL', 'ung': 'UNGÜENTO', 'pomo': 'POMO', 'jalea': 'JALEA',
    'lot': 'LOCIÓN', 'loc': 'LOCIÓN', 'emuls': 'EMULSIÓN',
    'xamp': 'CHAMPÚ', 'shamp': 'CHAMPÚ',
    'roll-on': 'ROLL-ON', 'pda': 'PARCHE', 'parche': 'PARCHE',
    'aer.bronq': 'AEROSOL BRONQUIAL', 'aer': 'AEROSOL', 'aerosol': 'AEROSOL',
    'inhal': 'INHALADOR', 'spray': 'SPRAY', 'nasal': 'SPRAY NASAL', 'puff': 'PUFF',
    'ov.vag': 'ÓVULOS VAGINALES', 'óv.vag': 'ÓVULOS VAGINALES',
    'óv': 'ÓVULOS', 'ov': 'ÓVULOS', 'sup': 'SUPOSITORIOS',
    'polv.p/susp.oral': 'POLVO PARA SUSPENSIÓN ORAL',
    'polv.p/susp': 'POLVO PARA SUSPENSIÓN', 'polv.p/sol': 'POLVO PARA SOLUCIÓN',
    'pvo.p/susp': 'POLVO PARA SUSPENSIÓN', 'pvo.sob': 'POLVO SOBRES',
    'pvo': 'POLVO', 'polv': 'POLVO',
    'gran.sob': 'GRÁNULOS SOBRES', 'gran': 'GRÁNULOS',
    'blist.grag': 'BLÍSTER GRAGEAS', 'blist': 'BLÍSTER',
    'sob': 'SOBRES', 'sobre': 'SOBRES', 'sobres': 'SOBRES', 'sachet': 'SOBRES',
    'pouch': 'POUCH', 'kit': 'KIT',
    'grag': 'GRAGEAS', 'tab': 'TABLETAS', 'caram': 'CARAMELOS', 'film': 'FILM',
    # Formas adicionales no mapeadas previamente
    'caplets': 'TABLETAS',
    'laca': 'LACA',
    'laq': 'LACA',
    'espuma': 'ESPUMA',
    'espuma rectal': 'ESPUMA RECTAL',
    'expend.sob': 'SOBRES EXPENDEDOR',
    'polv.p/susp.oral': 'POLVO PARA SUSPENSIÓN ORAL',
    'pvo.liof': 'POLVO LIOFILIZADO',
    'pvo.vial': 'POLVO VIAL',
    'jer.prell': 'JERINGA PRELLENADA',
    'jer.pr': 'JERINGA PRELLENADA',
    'jga.pr': 'JERINGA PRELLENADA',
    'sol.f.a': 'SOLUCIÓN FRASCO AMPOLLA',
    'iny.sol': 'SOLUCIÓN INYECTABLE',
    'iny.liof': 'INYECTABLE LIOFILIZADO',
    'iv': 'INYECTABLE INTRAVENOSO',
    'tab.dis.inst': 'TABLETAS DISPERSABLES DE DISOLUCIÓN INSTANTÁNEA',
    'tab.disp': 'TABLETAS DISPERSABLES',
    'dis.inst': 'DISOLUCIÓN INSTANTÁNEA',
    'comp.gastr': 'COMPRIMIDOS GASTRORRESISTENTES',
    'comp.laq': 'COMPRIMIDOS LACADOS',
    'comp.rapirtd': 'COMPRIMIDOS LIBERACIÓN RÁPIDA',
    'comp.divis': 'COMPRIMIDOS DIVISIBLES',
    'comp.divids': 'COMPRIMIDOS DIVISIBLES',
    'comp.ran.divids': 'COMPRIMIDOS RANURADOS DIVISIBLES',
    'caps.bl.gastr': 'CÁPSULAS BLANDAS GASTRORRESISTENTES',
    'cáps.bl.gastr': 'CÁPSULAS BLANDAS GASTRORRESISTENTES',
    'sol.oft.esteril': 'SOLUCIÓN OFTÁLMICA ESTÉRIL',
    'sol.oft.estéril': 'SOLUCIÓN OFTÁLMICA ESTÉRIL',
    'fco.vial': 'FRASCO VIAL',
    'iny.vial': 'INYECTABLE VIAL',
    'liof.pvo.vial': 'LIOFILIZADO POLVO VIAL',
    'jbe': 'JARABE',
    'd.jbe': 'JARABE',
    # Formas añadidas en fix /ml+forma y nuevas (2026-06)
    'tabl':              'TABLETAS',
    'tabs':              'TABLETAS',
    'lapic.prell':       'LAPICERA PRELLENADA',
    'lapic':             'LAPICERA',
    'lapiceras prell':   'LAPICERAS PRELLENADAS',
    'lapiceras':         'LAPICERAS',
    'lapicera desc':     'LAPICERA DESCARTABLE',
    'lapicera':          'LAPICERA',
    'lap.prell':         'LAPICERA PRELLENADA',
    'autoiny':           'AUTOINYECTOR',
    'autoinyect':        'AUTOINYECTOR',
    'autoinyec':         'AUTOINYECTOR',
    'autoinyect.prell':  'AUTOINYECTOR PRELLENADO',
    'cart':              'CARTUCHO',
    'cart.prell':        'CARTUCHO PRELLENADO',
    'cartucho':          'CARTUCHO',
    'depot':             'DEPÓSITO',
    'vial':              'VIAL',
    'viales':            'VIALES',
    'fco':               'FRASCO',
    'apos':              'APÓSITO',
    'jab.liq':           'JABÓN LÍQUIDO',
    'jab.sol':           'JABÓN SÓLIDO',
    'inhalador hfa':     'INHALADOR HFA',
    'inh':               'INHALADOR',
    'spr.nasal':         'SPRAY NASAL',
    'spr':               'SPRAY',
    'sh':                'SHAMPOO',
    'shampoo':           'SHAMPOO',
    'pda':               'POMADA',
    'emul':              'EMULSIÓN',
    'emulsión':          'EMULSIÓN',
    'monods':            'MONODOSIS',
    'monodosis':         'MONODOSIS',
    'pomos':             'POMOS',
    'blis':              'BLÍSTER',
    'blister':           'BLÍSTER',
    'dispensador':       'DISPENSADOR',
    'dispenser':         'DISPENSADOR',
    'colir':             'COLIRIO',
    'granul.lp sob':     'GRÁNULOS LP SOBRES',
    'granul':            'GRÁNULOS',
    'divids':            'DIVISIBLES',
    'jgas.prell':        'JERINGAS PRELLENADAS',
    'jga.prell':         'JERINGA PRELLENADA',
    'jer.prell':         'JERINGA PRELLENADA',
    'jga.pr':            'JERINGA PRELLENADA',
    'j.prell':           'JERINGA PRELLENADA',
    'iny.prell':         'INYECTABLE PRELLENADO',
    'iny.a.ol':          'INYECTABLE OLEOSO',
    'sol.iny':           'SOLUCIÓN INYECTABLE',
    'parch.matriz':      'PARCHE MATRICIAL',
    'parch.transd':      'PARCHE TRANSDÉRMICO',
    'parches transdérmicos': 'PARCHES TRANSDÉRMICOS',
    'cap.lib.prol':      'CÁPSULAS LIBERACIÓN PROLONGADA',
    'ap.aplic.desc':     'APLICADOR DESCARTABLE',
    # Formas faltantes detectadas en debug (2024-06)
    'champu': 'CHAMPÚ',
    'sachets': 'SOBRES',
    'implante': 'IMPLANTE',
    'pasta': 'PASTA',
    'polvo': 'POLVO',
    'talquera': 'TALQUERA',
    'esp': 'ESPUMA',
    'got': 'GOTAS',
    'got.': 'GOTAS',
    'gotero incoloro': 'FRASCO GOTERO',
    'locion atomizador': 'LOCIÓN ATOMIZADOR',
    'pomada dérm': 'POMADA DÉRMICA',
    'pomada': 'POMADA',
    'colir': 'COLIRIO',
    'tubos': 'TUBOS',
    'viales': 'VIALES',
    'autoinyect.prell': 'AUTOINYECTOR PRELLENADO',
    'implante oft.intravítrea': 'IMPLANTE OFTÁLMICO INTRAVÍTREO',
    'gtas': 'GOTAS',
    'gotas': 'GOTAS',
    'pote': 'POTE',
    'colut': 'COLUTORIO',
    'past': 'PASTILLAS',
    'pastillas': 'PASTILLAS',
    'soluc': 'SOLUCIÓN',
    'parches': 'PARCHES',
    'caramelos': 'CARAMELOS',
    'blister caram': 'BLÍSTER CARAMELOS',
    'caram': 'CARAMELOS',
    'pasta dérm': 'PASTA DÉRMICA',
    'pasta derm': 'PASTA DÉRMICA',
    'unidosis': 'UNIDOSIS',
    'toallitas desc': 'TOALLITAS DESCARTABLES',
    'toallitas': 'TOALLITAS',
    'ap.aplic.desc': 'APLICADOR DESCARTABLE',
    'sistemas': 'SISTEMAS',
    'estuche': 'ESTUCHE',
    'frasco': 'FRASCO',
    'efer.gran.sob': 'GRÁNULOS EFERVESCENTES SOBRES',
    'gran.efer.sob': 'GRÁNULOS EFERVESCENTES SOBRES',
    'anillo vaginal sob': 'ANILLO VAGINAL SOBRES',
    'anillo vaginal': 'ANILLO VAGINAL',
    'crema': 'CREMA',
}

_MODS_PRES = {
    'oft':      {'sol': 'SOLUCIÓN OFTÁLMICA',  'gts': 'GOTAS OFTÁLMICAS',  None: 'OFTÁLMICO'},
    'of':       {'sol': 'SOLUCIÓN OFTÁLMICA',  'gts': 'GOTAS OFTÁLMICAS',  None: 'OFTÁLMICO'},
    'oral':     {'sol': 'SOLUCIÓN ORAL', 'susp': 'SUSPENSIÓN ORAL',        None: 'ORAL'},
    'vag':      {'ov': 'ÓVULOS VAGINALES', 'óv': 'ÓVULOS VAGINALES', 'cr': 'CREMA VAGINAL', None: 'VAGINAL'},
    'nasal':    {'susp': 'SUSPENSIÓN NASAL', 'sol': 'SOLUCIÓN NASAL', 'spray': 'SPRAY NASAL', None: 'SPRAY NASAL'},
    'liof':     {'f.a': 'FRASCO AMPOLLA LIOFILIZADO', None: 'LIOFILIZADO'},
    'f.a':      {'iny': 'INYECTABLE FRASCO AMPOLLA', 'liof': 'LIOFILIZADO FRASCO AMPOLLA', None: 'FRASCO AMPOLLA'},
    'gotero':   {'fco': 'FRASCO GOTERO', None: 'FRASCO GOTERO'},
    'rec':      {'comp': 'COMPRIMIDOS RECUBIERTOS', None: 'RECUBIERTO'},
    'acc.prol': {'comp': 'COMPRIMIDOS ACCIÓN PROLONGADA', None: 'ACCIÓN PROLONGADA'},
    'ap':       {'comp': 'COMPRIMIDOS ACCIÓN PROLONGADA', None: 'ACCIÓN PROLONGADA'},
    'prell':    {'lap': 'LAPICERA PRELLENADA', 'jga': 'JERINGA PRELLENADA', None: 'PRELLENADO'},
    'duras':    {'cáps': 'CÁPSULAS DURAS', 'caps': 'CÁPSULAS DURAS', None: None},
    'ur': {None: None}, 'andas': {None: None}, 'solv': {None: None},
    's': {None: None}, 't': {None: None}, 'r': {None: None}, 'er': {None: None},
}

_RE_PP  = re.compile(r'^(?:ad|ped|rtd|hm|ap)\.?\s+', re.IGNORECASE)
# Prefijos que modifican la forma (se conservan como sufijo de forma)
_RE_PM  = re.compile(r'^(sr|lp|xr|er|mr|flash|niños|naranja|menta|frutal|clásico|clasico|vainilla|frutilla|tutti\s*frutti|limón|limon|forte|plus|duo|max)\s+', re.IGNORECASE)
_MODS_FORMA = {
    'sr': 'SR', 'lp': 'LP', 'xr': 'XR', 'er': 'ER', 'mr': 'MR',
    'flash': 'FLASH', 'niños': 'NIÑOS', 'forte': 'FORTE', 'plus': 'PLUS',
    'duo': 'DUO', 'max': 'MAX',
}
_RE_PD  = re.compile(r'^(\d[\d\.,/]*)\s*')
_RE_PU  = re.compile(r'^(mg|mcg|ug|g\b|ml|ui|iu|meq|mmol|kcal|%)\s*', re.IGNORECASE)
_RE_PPR = re.compile(r'^(?:hfa|cfc|/\d*\.?\d*(?:ml|h|24h))\s*', re.IGNORECASE)
_RE_PC  = re.compile(r'^(\d[\d\.,]*)\s*(mg|mcg|g)\s*/\s*(\d[\d\.,]*)\s*(ml|g)\s*', re.IGNORECASE)
_RE_PCT_MID = re.compile(r'^(.*?)(\d+[\.,]?\d*)\s*%\s+', re.IGNORECASE)   # "gel 0.1% " → dosis=0.1, unidad=%
_RE_CONC_BARE = re.compile(r'^(\d[\d\.,]*)\s*(mg|mcg|g|ui|meq)\s*/\s*(ml|g|dose|dosis|comp|amp)\s*$', re.IGNORECASE)  # "f.a.x 250 mg/ml" tail
_RE_PKV = re.compile(r'x\s*\d[\d\.,]*\s*(ml|g)\b', re.IGNORECASE)
_RE_PCO = re.compile(r'\(\d+\+\d+\)')
_RE_PCA = re.compile(r'x\s*(\d[\d\.,]*)\s*(ds\.?|dosis|ml|g\b|u\.?|unid\.?)?', re.IGNORECASE)
_RE_PAE = re.compile(r'(?:dosis\s+x\s+(\d+)|(\d+)\s+dosis)', re.IGNORECASE)
_formas_pres_re = '|'.join(re.escape(k) for k in sorted(_FORMAS_NORM_PRES.keys(), key=len, reverse=True))
_RE_PF  = re.compile(r'^(' + _formas_pres_re + r')(?=$|[\s\.])[\s\.]?', re.IGNORECASE)
_RE_PFF = re.compile(r'\b(' + _formas_pres_re + r')\.?$', re.IGNORECASE)
_UNI_MAP = {'mg':'MG','mcg':'MCG','ug':'MCG','g':'G','ml':'ML',
            'ui':'UI','iu':'UI','u':'U','meq':'MEQ','mmol':'MMOL','kcal':'KCAL','%':'%'}


def _parsear_presentacion(pres: str) -> dict:
    r = {'forma': None, 'dosis': None, 'unidad': None, 'cantidad': None, 'resto': None}
    s = pres.strip().lower()
    # Capturar modificador de forma antes de strippear prefijos (SR, LP, Flash, Niños, etc.)
    _mod_forma = None
    m_mod = _RE_PM.match(s)
    if m_mod:
        _mod_forma = _MODS_FORMA.get(m_mod.group(1).lower())  # None si es sabor (naranja, menta…)
        s = s[m_mod.end():]
    s = _RE_PP.sub('', s).strip()
    m = _RE_PC.match(s)
    if m:
        r['dosis']  = f"{m.group(1)}{m.group(2)}/{m.group(3)}{m.group(4)}"
        r['unidad'] = 'MG/ML'
        s = s[m.end():]
        # Capturar forma que sigue a la concentración (ej: "0.5 mg/ml a.x 1")
        m2 = _RE_PF.match(s.strip())
        if m2:
            fkr2 = m2.group(1).lower().rstrip('. ')
            r['forma'] = _FORMAS_NORM_PRES.get(fkr2, fkr2.upper())
            s = s[m2.end():]
    else:
        m = _RE_PD.match(s)
        if m: r['dosis'] = m.group(1); s = s[m.end():]
        m = _RE_PU.match(s)
        if m: r['unidad'] = _UNI_MAP.get(m.group(1).lower(), m.group(1).upper()); s = s[m.end():]
    # Patrón "forma N% x cantidad" → ej: "gel 0.1% x 30 g"
    # El % aparece DESPUÉS de la forma: primero buscamos la forma, luego el %
    if not r['dosis']:
        m = re.search(r'(\d+[\.,]?\d*)\s*%(?:\s+|$)', s)
        if m:
            r['dosis'] = m.group(1).replace(',', '.')
            r['unidad'] = '%'
            s = (s[:m.start()] + s[m.end():]).strip()
    # Patrón "mg/ml" al final sin cantidad previa → ej: "f.a.x 50 mg/ml"
    # Solo aplica si la cantidad ya capturada en realidad era la concentración
    if not r['dosis'] and r['cantidad']:
        m = re.search(r'(mg|mcg|g|ui|meq)\s*/\s*(ml|g)\s*$', s, re.IGNORECASE)
        if m:
            # la cantidad capturada es la dosis, la unidad es mg/ml
            r['dosis']    = r['cantidad']
            r['unidad']   = _UNI_MAP.get(m.group(1).lower(), m.group(1).upper()) + '/' + m.group(2).upper()
            r['cantidad'] = None
    # Caso "x 250 mg/ml" → cantidad fue capturada pero resto contiene la unidad
    if not r['dosis'] and r['cantidad'] and r.get('resto'):
        m = re.match(r'^(mg|mcg|g|ui|meq)\s*/\s*(ml|g)\s*$', (r['resto'] or ''), re.IGNORECASE)
        if m:
            r['dosis']    = r['cantidad']
            r['unidad']   = _UNI_MAP.get(m.group(1).lower(), m.group(1).upper()) + '/' + m.group(2).upper()
            r['cantidad'] = None
            r['resto']    = None
    s = _RE_PPR.sub('', s).strip()
    fkr = None
    m = _RE_PF.match(s.strip())
    if m:
        fkr = m.group(1).lower().rstrip('. ')
        r['forma'] = _FORMAS_NORM_PRES.get(fkr, fkr.upper())
        s = s[m.end():]
    if not r['forma']:
        m = _RE_PFF.search(s.strip())
        if m:
            fk = m.group(1).lower().rstrip('. ')
            r['forma'] = _FORMAS_NORM_PRES.get(fk, fk.upper())
            s = s[:m.start()].strip()
    # Fallback: si hay una palabra descriptiva antes de la forma (ej: "aspirina prev.comp.x 60",
    # "clásico comp.mast.x 6", "mentol gts.x 120 ml") buscar forma en cualquier posición.
    if not r['forma']:
        m = re.search(r'\b(' + _formas_pres_re + r')(?=$|[\s.x])', s, re.IGNORECASE)
        if m:
            fk = m.group(1).lower().rstrip('. ')
            r['forma'] = _FORMAS_NORM_PRES.get(fk, fk.upper())
            # Descartar la parte previa a la forma (es texto descriptivo, no dato útil)
            s = s[m.end():]
    s_sk = _RE_PKV.sub('', s)
    m = _RE_PCA.search(s_sk)
    if m:
        cant = m.group(1); uc = (m.group(2) or '').strip().rstrip('.')
        if uc == 'dosis': uc = 'ds.'
        r['cantidad'] = (cant + (' ' + uc if uc else '')).strip()
        s = (s_sk[:m.start()] + s_sk[m.end():]).strip(' .,+')
    else:
        s = s_sk
        m = _RE_PAE.search(s)
        if m:
            n = m.group(1) or m.group(2)
            r['cantidad'] = n + ' ds.'
            s = (s[:m.start()] + s[m.end():]).strip(' .,+')
    s = _RE_PCO.sub('', s).strip(' .,+')
    if s and fkr:
        mod = s.strip(' .')
        if mod in _MODS_PRES:
            mapa = _MODS_PRES[mod]
            fr = mapa.get(fkr) or mapa.get(None)
            if fr: r['forma'] = fr; s = ''
            elif mapa.get(None) is None: s = ''
    s = s.strip(' .,+-')
    if not r['forma'] and not s and r['cantidad']:
        if r['unidad'] == 'ML': r['forma'] = 'LÍQUIDO'
        elif r['unidad'] == 'G': r['forma'] = 'TÓPICO'
    # Appendear modificador a la forma si corresponde (SR, LP, Flash, Niños…)
    if _mod_forma and r['forma']:
        r['forma'] = f"{r['forma']} {_mod_forma}"
    if s: r['resto'] = s
    # Caso "f.a.x 250 mg/ml" → cantidad capturada pero resto es "mg/ml" (la unidad)
    if not r['dosis'] and r['cantidad'] and r.get('resto'):
        m = re.match(r'^(mg|mcg|g|ui|meq)\s*/\s*(ml|g)\s*$', r['resto'], re.IGNORECASE)
        if m:
            r['dosis']    = r['cantidad']
            r['unidad']   = _UNI_MAP.get(m.group(1).lower(), m.group(1).upper()) + '/' + m.group(2).upper()
            r['cantidad'] = None
            r['resto']    = None
    return r


def generar_debug_presentaciones(medicamentos: list) -> None:
    import csv as _csv
    PRES_DEBUG_PATH.parent.mkdir(parents=True, exist_ok=True)
    debug_generado = datetime.now(AR_TZ).strftime("%Y-%m-%d %H:%M:%S")
    campos = ['debug_generado', 'droga', 'marca', 'presentacion_original', 'forma', 'dosis', 'unidad', 'cantidad', 'resto']
    sin_forma = con_resto = total = 0
    with open(PRES_DEBUG_PATH, 'w', newline='', encoding='utf-8') as f:
        writer = _csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        for m in medicamentos:
            pres = (m.get('presentacion') or '').strip()
            if not pres: continue
            r = _parsear_presentacion(pres)
            if not r['forma']:   sin_forma += 1
            if r['resto']:       con_resto += 1
            total += 1
            writer.writerow({
                'debug_generado': debug_generado,
                'droga': m.get('droga', ''), 'marca': m.get('marca', ''),
                'presentacion_original': pres,
                'forma': r['forma'] or '', 'dosis': r['dosis'] or '',
                'unidad': r['unidad'] or '', 'cantidad': r['cantidad'] or '',
                'resto': r['resto'] or '',
            })
    limpios = total - sin_forma - con_resto
    print(f"   Total: {total} | Limpio: {limpios} ({100*limpios/max(total,1):.1f}%) | "
          f"Sin forma: {sin_forma} | Con resto: {con_resto}")
    print(f"   Debug: {PRES_DEBUG_PATH}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    if not NORMALIZADO_PATH.exists():
        print(f"ERROR: {NORMALIZADO_PATH} no encontrado. Ejecutá primero normalizar.py")
        sys.exit(1)

    with open(NORMALIZADO_PATH, encoding="utf-8") as f:
        data = json.load(f)

    medicamentos = data["medicamentos"]
    print(f"Registros a enriquecer: {len(medicamentos)}")

    # ── Debug CSV ─────────────────────────────────────────────────────────
    print("\nGenerando debug de presentaciones...")
    generar_debug_presentaciones(medicamentos)

    # ── Parser de presentaciones → campos pres_* ──────────────────────────
    print("\nEnriqueciendo registros con campos de presentación...")

    _RE_DOSIS_MARCA = re.compile(
        r'(\d+[\.,]?\d*)\s*/\s*(\d+[\.,]?\d*)\s*(mg|mcg|g|ui|%)|'
        r'(\d+[\.,]?\d*)\s*(mg|mcg|µg|g\b|ui|iu|%|meq)',
        re.IGNORECASE
    )
    _RE_DOSIS_NOMBRE = re.compile(
        r'(?<![A-Za-z\d])(\d+[\.,]?\d*)\s*/\s*(\d+[\.,]?\d*)\s*(?:U\.I\.?|UI|MG|MCG|%)?\s*$|'
        r'(?<![A-Za-z])(\d+[\.,]?\d*)\s*(U\.I\.?|UI|MG|MCG|%)\s*$|'
        r'(?<![A-Za-z\d/])(\d{2,})\s*$',
        re.IGNORECASE
    )
    _RE_DROGA_SIN_DOSIS = re.compile(
        r'\bvacun|antigen|antigripal|vitamina[^s]|multivitamin|'
        r'anticonceptiv|levonorgestrel|etinil|dienogest|drospirenon|noretisterona|'
        r'acido folic\b|folico\b|herbal|fitoterapia|preparacion herbaria|'
        r'hepatalgina|suero oral|solucion de rehidratacion|'
        r'agua oxigenada|alcohol etilico\b|cloruro de sodio.*0\.9',
        re.IGNORECASE
    )
    _FORMAS_SIN_DOSIS = {
        'CREMA', 'GEL', 'POMADA', 'SHAMPOO', 'LOCIÓN', 'COLIRIO',
        'SOLUCIÓN OFTÁLMICA', 'JABÓN LÍQUIDO', 'PASTA DÉRMICA',
        'ESPUMA', 'TOALLITAS', 'TALQUERA', 'LACA', 'EMULSIÓN',
        'LOCIÓN ATOMIZADOR', 'POTE',
    }

    n_enriquecidos = 0
    n_dosis_marca  = 0

    for m in medicamentos:
        pres = (m.get('presentacion') or '').strip()
        if not pres:
            continue
        r = _parsear_presentacion(pres)
        if r['forma'] or r['dosis']:
            if r['forma']:    m['pres_forma']    = r['forma']
            if r['dosis']:    m['pres_dosis']    = r['dosis']
            if r['unidad']:   m['pres_unidad']   = r['unidad']
            if r['cantidad']: m['pres_cantidad'] = r['cantidad']
            n_enriquecidos += 1

        # Fallback 1: dosis con unidad en nombre de marca
        if not m.get('pres_dosis'):
            marca = (m.get('marca') or '').strip()
            hm = _RE_DOSIS_MARCA.search(marca)
            if hm:
                if hm.group(1) and hm.group(2):
                    m['pres_dosis']  = f"{hm.group(1)}/{hm.group(2)}"
                    m['pres_unidad'] = hm.group(3).upper()
                elif hm.group(4):
                    m['pres_dosis']  = hm.group(4).replace(',', '.')
                    m['pres_unidad'] = hm.group(5).upper()
                m['pres_dosis_fuente'] = 'marca'
                n_dosis_marca += 1

        # Fallback 2: número al final del nombre (ATORMAX 10, BIOCLAVID 875/125)
        if not m.get('pres_dosis'):
            marca = (m.get('marca') or '').strip()
            hn = _RE_DOSIS_NOMBRE.search(marca)
            if hn:
                if hn.group(1) and hn.group(2):
                    m['pres_dosis']  = f"{hn.group(1)}/{hn.group(2)}"
                    m['pres_unidad'] = 'MG'
                elif hn.group(3):
                    m['pres_dosis']  = hn.group(3).replace(',', '.')
                    m['pres_unidad'] = re.sub(r'\.', '', hn.group(4)).upper()
                else:
                    m['pres_dosis']  = hn.group(5)
                    m['pres_unidad'] = 'MG'
                m['pres_dosis_fuente'] = 'nombre'
                n_dosis_marca += 1

        # Marcar categorías donde la dosis no aplica estructuralmente
        if not m.get('pres_dosis'):
            droga = (m.get('droga') or '').strip()
            forma = m.get('pres_forma') or ''
            if _RE_DROGA_SIN_DOSIS.search(droga) or forma in _FORMAS_SIN_DOSIS:
                m['pres_dosis_fuente'] = 'no_aplica'

    print(f"   Enriquecidos: {n_enriquecidos}/{len(medicamentos)} "
          f"({100*n_enriquecidos/max(len(medicamentos),1):.1f}%)")
    print(f"   Dosis rescatadas de marca/nombre: {n_dosis_marca}")

    # ── Fallback 3: dosis desde PAMI ─────────────────────────────────────
    _RE_DOSIS_CONC_PAMI = re.compile(r'(\d+[\.,]?\d*)\s*(mg|mcg|µg|ui|iu|%|meq)\b', re.IGNORECASE)
    _RE_FORMA_PAMI      = re.compile(r'(comp|caps|susp|sol|jbe|gts|cr|gel|ung|pomo|sob|a\b|f\.a|vial|amp)', re.IGNORECASE)
    _RE_CANT_PAMI       = re.compile(r'x\s*(\d+)', re.IGNORECASE)

    pami_dosis_idx: dict = {}
    if PAMI_PATH.exists():
        import pandas as _pd
        pami_df = _pd.read_excel(PAMI_PATH)
        pami_df.columns = [c.strip() for c in pami_df.columns]
        for _, row in pami_df.iterrows():
            mp = str(row['MARCA']).strip().upper()
            pp = str(row['PRESENTACION']).strip().lower()
            h  = _RE_DOSIS_CONC_PAMI.search(pp)
            if h:
                pami_dosis_idx.setdefault(mp, []).append((pp, h))

    def _fc(ps, pp):
        f1 = _RE_FORMA_PAMI.search(ps.lower())
        f2 = _RE_FORMA_PAMI.search(pp.lower())
        return bool(f1 and f2 and f1.group(1).lower()[:3] == f2.group(1).lower()[:3])

    def _cc(ps, pp):
        c1 = _RE_CANT_PAMI.search(ps); c2 = _RE_CANT_PAMI.search(pp)
        return (c1.group(1) == c2.group(1)) if (c1 and c2) else True

    n_dosis_pami = 0
    for m in medicamentos:
        if m.get('pres_dosis'):
            continue
        mu = (m.get('marca') or '').strip().upper()
        ps = (m.get('presentacion') or '').strip().lower()
        for pp, hit in pami_dosis_idx.get(mu, []):
            if _fc(ps, pp) and _cc(ps, pp):
                m['pres_dosis']        = hit.group(1).replace(',', '.')
                m['pres_unidad']       = hit.group(2).upper()
                m['pres_dosis_fuente'] = 'pami'
                n_dosis_pami += 1
                break
    print(f"   Dosis rescatadas de PAMI: {n_dosis_pami}")

    # ── Guardar medicamentos.json ─────────────────────────────────────────
    out = {
        "fecha":        data["fecha"],
        "fuente":       data["fuente"],
        "total":        len(medicamentos),
        "blacklisted":  data.get("blacklisted", 0),
        "medicamentos": medicamentos,
    }

    MEDICAMENTOS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MEDICAMENTOS_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))

    print(f"\nGuardado: {MEDICAMENTOS_PATH}")
    print(f"Total: {len(medicamentos)}")


if __name__ == "__main__":
    main()
