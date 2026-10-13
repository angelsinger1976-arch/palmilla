# -*- coding: utf-8 -*-
"""
MÓDULO GEOESPACIAL — Detección automática de Áreas Naturales Protegidas (ANP)
=============================================================================
Determina si una ubicación geográfica (coordenadas geográficas lat/lon o
coordenadas UTM) cae dentro de un Área Natural Protegida federal de México y,
de ser así, si el aprovechamiento forestal **NO PROCEDE** por estar prohibida
la extracción (p. ej. Zonas Núcleo de una Reserva de la Biósfera).

Fuentes y parámetros oficiales (CONANP / CONABIO / DOF):
  * Cartografía: Portal SIG de la CONANP y Geoportal de Metadatos de la CONABIO
    (capa "Áreas Naturales Protegidas Federales de México": polígono envolvente
    externo + subdivisiones de Zonas Núcleo).
  * Sistema de coordenadas: UTM — Zona 11 Norte (11N).
  * Datum horizontal / elipsoide: WGS84 o GRS80 (Marco Geoestadístico INEGI).
  * Código EPSG: EPSG:32611 (WGS 84 / UTM zone 11N).

Método de detección (en orden de prioridad):
  1. Polígono real en formato GeoJSON (si existe en `data/anp/`).
  2. Caja envolvente (bounding box) oficial — respaldo de amplio espectro.

AVISO: la caja envolvente (bounding box) es un filtro de acotamiento
conservador; puede marcar como "posiblemente dentro" puntos que en realidad
quedan fuera del polígono exacto. Para dictámenes definitivos debe usarse la
capa vectorial oficial de la CONANP/CONABIO (EPSG:32611).
"""
from __future__ import annotations

import json
import math
import os
import re
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Parámetros del elipsoide WGS84 y proyección UTM
# ---------------------------------------------------------------------------
_A = 6378137.0                     # semieje mayor (m)
_F = 1.0 / 298.257223563           # achatamiento
_K0 = 0.9996                       # factor de escala UTM
_E2 = _F * (2.0 - _F)              # excentricidad al cuadrado
_EP2 = _E2 / (1.0 - _E2)           # segunda excentricidad al cuadrado
_FALSE_EASTING = 500000.0          # falso este (m)
_FALSE_NORTHING_S = 10000000.0     # falso norte (hemisferio sur)


# ---------------------------------------------------------------------------
# Conversión UTM <-> geográficas (WGS84)
# ---------------------------------------------------------------------------
def latlon_a_utm(lat: float, lon: float, zona: Optional[int] = None) -> Dict:
    """Convierte lat/lon (grados, WGS84) a UTM. Devuelve zona, este y norte."""
    if zona is None:
        zona = int((lon + 180.0) / 6.0) + 1
    lon0 = math.radians((zona - 1) * 6 - 180 + 3)  # meridiano central
    phi = math.radians(lat)
    lam = math.radians(lon)

    n = _A / math.sqrt(1 - _E2 * math.sin(phi) ** 2)
    t = math.tan(phi) ** 2
    c = _EP2 * math.cos(phi) ** 2
    a = math.cos(phi) * (lam - lon0)

    m = _A * ((1 - _E2 / 4 - 3 * _E2 ** 2 / 64 - 5 * _E2 ** 3 / 256) * phi
              - (3 * _E2 / 8 + 3 * _E2 ** 2 / 32 + 45 * _E2 ** 3 / 1024) * math.sin(2 * phi)
              + (15 * _E2 ** 2 / 256 + 45 * _E2 ** 3 / 1024) * math.sin(4 * phi)
              - (35 * _E2 ** 3 / 3072) * math.sin(6 * phi))

    este = _K0 * n * (a + (1 - t + c) * a ** 3 / 6
                      + (5 - 18 * t + t ** 2 + 72 * c - 58 * _EP2) * a ** 5 / 120) + _FALSE_EASTING
    norte = _K0 * (m + n * math.tan(phi) * (a ** 2 / 2
                   + (5 - t + 9 * c + 4 * c ** 2) * a ** 4 / 24
                   + (61 - 58 * t + t ** 2 + 600 * c - 330 * _EP2) * a ** 6 / 720))
    hemisferio = "N" if lat >= 0 else "S"
    if lat < 0:
        norte += _FALSE_NORTHING_S
    return {"zona": zona, "hemisferio": hemisferio, "este": round(este, 2), "norte": round(norte, 2)}


def utm_a_latlon(este: float, norte: float, zona: int = 11, hemisferio: str = "N") -> Tuple[float, float]:
    """Convierte UTM a lat/lon (grados, WGS84)."""
    x = este - _FALSE_EASTING
    y = norte
    if hemisferio.upper().startswith("S"):
        y -= _FALSE_NORTHING_S
    lon0 = math.radians((zona - 1) * 6 - 180 + 3)

    m = y / _K0
    mu = m / (_A * (1 - _E2 / 4 - 3 * _E2 ** 2 / 64 - 5 * _E2 ** 3 / 256))
    e1 = (1 - math.sqrt(1 - _E2)) / (1 + math.sqrt(1 - _E2))

    phi1 = (mu + (3 * e1 / 2 - 27 * e1 ** 3 / 32) * math.sin(2 * mu)
            + (21 * e1 ** 2 / 16 - 55 * e1 ** 4 / 32) * math.sin(4 * mu)
            + (151 * e1 ** 3 / 96) * math.sin(6 * mu)
            + (1097 * e1 ** 4 / 512) * math.sin(8 * mu))

    n1 = _A / math.sqrt(1 - _E2 * math.sin(phi1) ** 2)
    t1 = math.tan(phi1) ** 2
    c1 = _EP2 * math.cos(phi1) ** 2
    r1 = _A * (1 - _E2) / (1 - _E2 * math.sin(phi1) ** 2) ** 1.5
    d = x / (n1 * _K0)

    lat = phi1 - (n1 * math.tan(phi1) / r1) * (
        d ** 2 / 2 - (5 + 3 * t1 + 10 * c1 - 4 * c1 ** 2 - 9 * _EP2) * d ** 4 / 24
        + (61 + 90 * t1 + 298 * c1 + 45 * t1 ** 2 - 252 * _EP2 - 3 * c1 ** 2) * d ** 6 / 720)
    lon = lon0 + (d - (1 + 2 * t1 + c1) * d ** 3 / 6
                  + (5 - 2 * c1 + 28 * t1 - 3 * c1 ** 2 + 8 * _EP2 + 24 * t1 ** 2) * d ** 5 / 120) / math.cos(phi1)
    return round(math.degrees(lat), 6), round(math.degrees(lon), 6)


# ---------------------------------------------------------------------------
# Parseo de coordenadas escritas por el usuario
# ---------------------------------------------------------------------------
def _a_grados(valor: float, hemisferio: str) -> float:
    """Aplica signo según hemisferio (N/E positivo; S/O negativo)."""
    h = (hemisferio or "").upper()[:1]
    if h in ("S", "O", "W"):
        return -abs(valor)
    return abs(valor)


def parse_coordenadas(texto: str) -> Optional[Tuple[float, float]]:
    """Extrae (lat, lon) de un texto libre.

    Formatos soportados:
      * "31.8667, -116.6000"        (decimal, lat primero)
      * "-116.6000 31.8667"          (decimal, lon primero si |lon|>90)
      * "31°52'N 115°30'O"           (grados/minutos/segundos)
    Devuelve (lat, lon) o None si no se puede interpretar.
    """
    if not texto:
        return None
    t = texto.strip()

    # --- Formato DMS (grados, minutos, segundos) ---
    dms = re.findall(r"(\d+(?:\.\d+)?)\s*[°º]\s*(?:(\d+(?:\.\d+)?)\s*['′]\s*)?(?:(\d+(?:\.\d+)?)\s*[\"″]\s*)?\s*([NSEOWnseow])", t)
    if len(dms) >= 2:
        vals = []
        for g, m, s, h in dms[:2]:
            v = float(g) + (float(m) / 60.0 if m else 0.0) + (float(s) / 3600.0 if s else 0.0)
            vals.append(_a_grados(v, h))
        # ordenar: la latitud tiene hemisferio N/S
        pares = list(zip([d[3].upper() for d in dms[:2]], vals))
        lat = lon = None
        for h, v in pares:
            if h in ("N", "S"):
                lat = v
            else:
                lon = v
        if lat is not None and lon is not None:
            return round(lat, 6), round(lon, 6)

    # --- Formato decimal ---
    nums = re.findall(r"[-+]?\d+(?:\.\d+)?", t)
    if len(nums) >= 2:
        a, b = float(nums[0]), float(nums[1])
        # Si el primero es claramente una longitud (|x|>90), invertir
        if abs(a) > 90 and abs(b) <= 90:
            return round(b, 6), round(a, 6)
        return round(a, 6), round(b, 6)
    return None


def parse_utm(texto: str) -> Optional[Dict]:
    """Extrae (zona, este, norte, hemisferio) de un texto libre tipo
    'Zona 11N, X=540123, Y=3526789' o '11N 540123 3526789'."""
    if not texto:
        return None
    t = texto.strip()
    zona = 11
    mz = re.search(r"(?:zona\s*)?(\d{1,2})\s*([NnSs])\b", t)
    hemisferio = "N"
    if mz:
        zona = int(mz.group(1))
        hemisferio = mz.group(2).upper()
    # Este (X) y Norte (Y)
    mx = re.search(r"[Xx]\s*=?\s*([-+]?\d+(?:\.\d+)?)", t)
    my = re.search(r"[Yy]\s*=?\s*([-+]?\d+(?:\.\d+)?)", t)
    if mx and my:
        return {"zona": zona, "hemisferio": hemisferio,
                "este": float(mx.group(1)), "norte": float(my.group(1))}
    # Sin etiquetas: tomar los dos números más grandes
    nums = [float(n) for n in re.findall(r"[-+]?\d+(?:\.\d+)?", t)]
    grandes = [n for n in nums if n > 1000]
    if len(grandes) >= 2:
        return {"zona": zona, "hemisferio": hemisferio, "este": grandes[0], "norte": grandes[1]}
    return None


# ---------------------------------------------------------------------------
# Geometría: punto en caja envolvente y punto en polígono
# ---------------------------------------------------------------------------
def en_bbox(lat: float, lon: float, bbox: Dict) -> bool:
    return (bbox["lat_min"] <= lat <= bbox["lat_max"]
            and bbox["lon_min"] <= lon <= bbox["lon_max"])


def punto_en_poligono(lat: float, lon: float, anillo: List[List[float]]) -> bool:
    """Ray casting. `anillo` es una lista de pares [lon, lat] (formato GeoJSON)."""
    dentro = False
    n = len(anillo)
    j = n - 1
    for i in range(n):
        xi, yi = anillo[i][0], anillo[i][1]
        xj, yj = anillo[j][0], anillo[j][1]
        if ((yi > lat) != (yj > lat)) and \
           (lon < (xj - xi) * (lat - yi) / (yj - yi + 1e-15) + xi):
            dentro = not dentro
        j = i
    return dentro


# ---------------------------------------------------------------------------
# Catálogo de ANP (polígonos oficiales de referencia)
# ---------------------------------------------------------------------------
# Nota: las cajas envolventes (bbox) se usan como respaldo cuando no hay
# polígono GeoJSON. Están basadas en los decretos y cartografía de la CONANP.
ANP_CATALOGO: List[Dict] = [
    {
        "clave": "RB-AGC-DRC",
        "nombre": "Reserva de la Biósfera del Alto Golfo de California y Delta del Río Colorado",
        "categoria": "Reserva de la Biósfera",
        "estado": "Baja California y Sonora",
        "restriccion": "prohibido",
        "bbox": {"lat_min": 31.000000, "lat_max": 32.166667,
                 "lon_min": -115.250000, "lon_max": -113.500000},
        "zonas_nucleo": [
            # Subzonas de protección estricta (extracción 100% prohibida).
            {"nombre": "Zona Núcleo Delta del Río Colorado", "bbox": {
                "lat_min": 31.500000, "lat_max": 32.166667,
                "lon_min": -115.100000, "lon_max": -114.400000}},
            {"nombre": "Zona Núcleo Roca Consag", "bbox": {
                "lat_min": 31.300000, "lat_max": 31.550000,
                "lon_min": -114.250000, "lon_max": -113.900000}},
        ],
        "fundamento": ("Decreto de creación (DOF 10/06/1993); LGEEPA Arts. 44-50 y 47 bis; "
                       "Reglamento LGEEPA en materia de ANP; NOM-005-SEMARNAT-1997 §4.1.14."),
        "nota": ("El límite terrestre occidental en Baja California corre a lo largo de la "
                 "Carretera Federal 5 (Mexicali–San Felipe), desde ~km 80 hasta la costa de "
                 "San Felipe, cerrando por Punta Machorro. En las Zonas Núcleo la extracción "
                 "de recursos forestales no maderables está PROHIBIDA (100%)."),
        "fuente": "CONANP — Portal SIG / CONABIO — Geoportal de Metadatos (EPSG:32611)",
    },
    {
        "clave": "RB-VC",
        "nombre": "Reserva de la Biósfera Valle de los Cirios",
        "categoria": "Reserva de la Biósfera",
        "estado": "Baja California",
        "restriccion": "restringido",
        "bbox": {"lat_min": 27.500000, "lat_max": 30.050000,
                 "lon_min": -115.500000, "lon_max": -113.000000},
        "zonas_nucleo": [],
        "fundamento": ("Decreto (DOF 02/02/1988); LGEEPA Arts. 44-50; "
                       "NOM-005-SEMARNAT-1997 §4.1.14."),
        "nota": ("Aprovechamiento sujeto a autorización y al Programa de Manejo; "
                 "verificar subzonificación vigente con la CONANP."),
        "fuente": "CONANP / CONABIO (bbox aproximado — verificar polígono exacto)",
    },
    {
        "clave": "PN-SSPM",
        "nombre": "Parque Nacional Sierra de San Pedro Mártir",
        "categoria": "Parque Nacional",
        "estado": "Baja California",
        "restriccion": "prohibido",
        "bbox": {"lat_min": 30.750000, "lat_max": 31.150000,
                 "lon_min": -115.650000, "lon_max": -115.150000},
        "zonas_nucleo": [],
        "fundamento": "Decreto (DOF 26/04/1947); LGEEPA Arts. 44-50; NOM-005 §4.1.14.",
        "nota": "En Parques Nacionales la extracción de recursos forestales está prohibida.",
        "fuente": "CONANP / CONABIO (bbox aproximado — verificar polígono exacto)",
    },
    {
        "clave": "PN-C1857",
        "nombre": "Parque Nacional Constitución de 1857",
        "categoria": "Parque Nacional",
        "estado": "Baja California",
        "restriccion": "prohibido",
        "bbox": {"lat_min": 31.930000, "lat_max": 32.070000,
                 "lon_min": -115.750000, "lon_max": -115.550000},
        "zonas_nucleo": [],
        "fundamento": "Decreto (DOF 27/04/1962); LGEEPA Arts. 44-50; NOM-005 §4.1.14.",
        "nota": "En Parques Nacionales la extracción de recursos forestales está prohibida.",
        "fuente": "CONANP / CONABIO (bbox aproximado — verificar polígono exacto)",
    },
]

_DIR_POLIGONOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "anp")


def _cargar_poligonos_geojson() -> List[Dict]:
    """Carga polígonos GeoJSON desde data/anp/*.geojson (si existen)."""
    poligonos: List[Dict] = []
    ruta = os.path.abspath(_DIR_POLIGONOS)
    if not os.path.isdir(ruta):
        return poligonos
    for archivo in sorted(os.listdir(ruta)):
        if not archivo.lower().endswith((".geojson", ".json")):
            continue
        try:
            with open(os.path.join(ruta, archivo), encoding="utf-8") as fh:
                gj = json.load(fh)
        except Exception:  # noqa: BLE001
            continue
        features = gj.get("features", [gj]) if isinstance(gj, dict) else []
        for feat in features:
            geom = (feat or {}).get("geometry") or {}
            props = (feat or {}).get("properties") or {}
            if geom.get("type") == "Polygon":
                anillos = [geom["coordinates"][0]]
            elif geom.get("type") == "MultiPolygon":
                anillos = [p[0] for p in geom["coordinates"]]
            else:
                continue
            poligonos.append({
                "clave": props.get("clave", archivo),
                "nombre": props.get("nombre", archivo),
                "categoria": props.get("categoria", "ANP"),
                "estado": props.get("estado", ""),
                "restriccion": props.get("restriccion", "restringido"),
                "anillos": anillos,
                "fundamento": props.get("fundamento", "LGEEPA Arts. 44-50."),
                "nota": props.get("nota", ""),
                "fuente": props.get("fuente", "GeoJSON local"),
            })
    return poligonos


# ---------------------------------------------------------------------------
# Evaluación de una ubicación
# ---------------------------------------------------------------------------
def evaluar_ubicacion(lat: Optional[float] = None, lon: Optional[float] = None,
                      utm: Optional[Dict] = None, texto: Optional[str] = None,
                      texto_utm: Optional[str] = None) -> Dict:
    """Determina si la ubicación cae dentro de alguna ANP del catálogo.

    Acepta coordenadas geográficas (lat/lon), UTM (dict o texto) o un texto
    libre con coordenadas. Devuelve un dict con el veredicto.
    """
    origen = "desconocido"
    if lat is None or lon is None:
        if utm is None and texto_utm:
            utm = parse_utm(texto_utm)
        if utm is None and texto:
            # ¿el texto es UTM o geográfico?
            if re.search(r"[Xx]\s*=|[Zz]ona\s*\d", texto) or re.search(r"\b\d{5,7}\b", texto):
                utm = parse_utm(texto)
            if utm is None:
                ll = parse_coordenadas(texto)
                if ll:
                    lat, lon = ll
                    origen = "geograficas"
        if utm and (lat is None or lon is None):
            lat, lon = utm_a_latlon(utm["este"], utm["norte"], utm.get("zona", 11),
                                    utm.get("hemisferio", "N"))
            origen = "utm"

    if lat is None or lon is None:
        return {"ok": False, "error": "No se pudieron interpretar las coordenadas.",
                "dentro_anp": False, "procede": True, "anp": [], "mensaje": ""}

    if origen == "desconocido":
        origen = "geograficas"

    utm_calc = latlon_a_utm(lat, lon, zona=11)
    hallazgos: List[Dict] = []
    claves_vistas: set = set()

    # 1) Polígonos reales (GeoJSON) — mayor precisión cuando existen.
    for pol in _cargar_poligonos_geojson():
        for anillo in pol["anillos"]:
            if punto_en_poligono(lat, lon, anillo):
                if pol["clave"] in claves_vistas:
                    break
                claves_vistas.add(pol["clave"])
                hallazgos.append({k: pol[k] for k in
                                  ("clave", "nombre", "categoria", "estado",
                                   "restriccion", "fundamento", "nota", "fuente")}
                                 | {"metodo": "poligono", "zona_nucleo": False})
                break

    # 2) Catálogo con caja envolvente — SIEMPRE se evalúa como piso de
    #    seguridad (evita falsos negativos si el GeoJSON es incompleto).
    for anp in ANP_CATALOGO:
        if en_bbox(lat, lon, anp["bbox"]):
            zn = None
            for z in anp.get("zonas_nucleo", []):
                if en_bbox(lat, lon, z["bbox"]):
                    zn = z["nombre"]
                    break
            if anp["clave"] in claves_vistas:
                # Ya detectado por polígono: sólo enriquece la zona núcleo.
                for h in hallazgos:
                    if h["clave"] == anp["clave"] and zn:
                        h["zona_nucleo"] = True
                        h["zona_nucleo_nombre"] = zn
                        h["restriccion"] = "prohibido"
                continue
            claves_vistas.add(anp["clave"])
            hallazgos.append({
                "clave": anp["clave"], "nombre": anp["nombre"],
                "categoria": anp["categoria"], "estado": anp["estado"],
                "restriccion": "prohibido" if zn else anp["restriccion"],
                "fundamento": anp["fundamento"], "nota": anp["nota"],
                "fuente": anp["fuente"], "metodo": "bbox",
                "zona_nucleo": bool(zn), "zona_nucleo_nombre": zn,
            })

    dentro = bool(hallazgos)
    prohibido = any(h["restriccion"] == "prohibido" for h in hallazgos)
    procede = not dentro

    if not dentro:
        mensaje = ("La ubicación NO cae dentro de las Áreas Naturales Protegidas "
                   "verificadas. Continúa el trámite ordinario (verificar igualmente "
                   "con la cartografía oficial de la CONANP).")
    elif prohibido:
        zn = next((h.get("zona_nucleo_nombre") for h in hallazgos if h.get("zona_nucleo")), None)
        detalle = f" (Zona Núcleo: {zn})" if zn else ""
        mensaje = ("NO PROCEDE. La ubicación cae dentro de una ANP con restricción de "
                   "extracción" + detalle + ". El aprovechamiento de recursos forestales "
                   "no maderables está PROHIBIDO conforme a la LGEEPA (Arts. 44-50) y al "
                   "decreto del área; no puede autorizarse el PMF.")
    else:
        mensaje = ("ATENCIÓN. La ubicación cae dentro de una ANP con restricción parcial. "
                   "Se requiere autorización previa de la autoridad ecológica (CONANP/SEMARNAT) "
                   "y apego al Programa de Manejo del área (NOM-005 §4.1.14).")

    return {
        "ok": True,
        "lat": lat, "lon": lon, "origen": origen,
        "utm": utm_calc,
        "epsg": "EPSG:32611 (WGS 84 / UTM zone 11N)",
        "dentro_anp": dentro,
        "prohibido": prohibido,
        "procede": procede,
        "anp": hallazgos,
        "mensaje": mensaje,
    }


if __name__ == "__main__":
    import sys
    ejemplos = [
        (31.86, -114.90),   # dentro de la reserva (delta)
        (32.05, -115.00),   # dentro (zona núcleo delta)
        (31.30, -114.05),   # dentro (Roca Consag)
        (31.86, -116.60),   # Ensenada (fuera)
        (29.00, -114.00),   # centro de B.C. (fuera)
    ]
    for la, lo in ejemplos:
        r = evaluar_ubicacion(lat=la, lon=lo)
        print(f"({la}, {lo}) -> dentro={r['dentro_anp']} procede={r['procede']} "
              f"anp={[a['clave'] for a in r['anp']]}")
    print("\n--- Prueba UTM ---")
    print(evaluar_ubicacion(texto_utm="Zona 11N, X=540123, Y=3526789")["mensaje"])
    print("\n--- Prueba texto geográfico ---")
    print(evaluar_ubicacion(texto="31°52'N 114°54'O")["lat"], evaluar_ubicacion(texto="31°52'N 114°54'O")["lon"])
