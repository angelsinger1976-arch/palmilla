# -*- coding: utf-8 -*-
"""
MÓDULO D — Plano Georreferenciado (Shapefile / GeoPDF)
======================================================
Genera el **plano georreferenciado del polígono del predio con las áreas de
aprovechamiento**, en los formatos que exige la SEMARNAT para el Programa de
Manejo Forestal Simplificado (PMF) de recursos forestales no maderables
(tallos de *Yucca* / palmilla).

Salidas que produce
-------------------
  * **Shapefile** (.shp/.shx/.dbf/.prj/.cpg) — EPSG:32611 (WGS 84 / UTM 11N),
    en tres capas: predio, áreas de aprovechamiento y capa combinada.
  * **GeoPDF georreferenciado** (OGC GeoPDF / ISO 32000) — con retícula de
    coordenadas UTM, flecha de norte, escala gráfica, leyenda y cuadro de datos.
  * **GeoJSON** (EPSG:4326) — interoperable con SIG de escritorio y web.
  * **PNG** — vista previa del plano.

Fundamento legal
----------------
  * Reglamento de la LGDFS, Art. 57 — el PMF debe incluir el plano
    georreferenciado del área de aprovechamiento.
  * NOM-005-SEMARNAT-1997 — procedimientos y especificaciones para el
    aprovechamiento, transporte y almacenamiento de recursos forestales no
    maderables.
  * LGDFS, Arts. 84-85 — régimen de autorización.

Sistema de coordenadas
----------------------
  * Geográficas: WGS 84 (EPSG:4326), latitud/longitud en grados decimales.
  * Proyectadas: WGS 84 / UTM zona 11N (EPSG:32611), este/norte en metros.
  * Datum horizontal: WGS 84 (compatible con el Marco Geoestadístico INEGI).

Dependencias
------------
  * geopandas, shapely, pyproj, matplotlib, numpy (obligatorias).
  * GDAL (osgeo) — *opcional pero recomendada*: necesaria para generar un
    GeoPDF con georreferenciación OGC real. Si no está disponible, se genera
    un PDF normal (sin metadatos geoespaciales) y se avisa en el resultado.
"""
from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Sequence, Tuple

# Reutiliza la conversión y el parseo de coordenadas ya existentes en el sistema.
from geo_anp import latlon_a_utm, utm_a_latlon, parse_coordenadas, parse_utm

# ---------------------------------------------------------------------------
# Constantes de proyección
# ---------------------------------------------------------------------------
EPSG_GEO = 4326          # WGS 84 (lat/lon)
EPSG_UTM = 32611         # WGS 84 / UTM zone 11N
ZONA_UTM = 11

# Paleta por tipo de área (colores cartográficos)
COLORES_TIPO: Dict[str, str] = {
    "Aprovechamiento": "#7cb342",   # verde
    "Aprovechamiento Forestal": "#7cb342",
    "Conservación": "#1e88e5",      # azul
    "Protección": "#1e88e5",
    "Exclusión": "#e53935",         # rojo
    "Amortiguamiento": "#fb8c00",   # naranja
    "Vialidad": "#8e24aa",          # morado
    "Restauración": "#00897b",      # teal
}


# ---------------------------------------------------------------------------
# Carga perezosa de dependencias geoespaciales
# ---------------------------------------------------------------------------
def _require_geo():
    """Importa geopandas/shapely/pyproj con un mensaje claro si faltan."""
    try:
        import geopandas as gpd  # noqa: F401
        import shapely  # noqa: F401
        import pyproj  # noqa: F401
    except ImportError as e:  # pragma: no cover
        raise RuntimeError(
            "Faltan dependencias geoespaciales. Instale con:\n"
            "    pip install geopandas shapely pyproj matplotlib"
        ) from e


def _osgeo():
    """Devuelve los módulos de GDAL (osgeo) o None si no están disponibles."""
    try:
        from osgeo import gdal, ogr, osr
        return gdal, ogr, osr
    except ImportError:
        # En Debian/Ubuntu los bindings viven en dist-packages del sistema.
        for p in ("/usr/lib/python3/dist-packages",):
            if os.path.isdir(p) and p not in sys.path:
                sys.path.append(p)
        try:
            from osgeo import gdal, ogr, osr
            return gdal, ogr, osr
        except ImportError:
            return None, None, None


# ---------------------------------------------------------------------------
# Modelo de datos
# ---------------------------------------------------------------------------
@dataclass
class AreaAprovechamiento:
    """Un área (sub-polígono) dentro del predio."""
    nombre: str = "Área de aprovechamiento"
    tipo: str = "Aprovechamiento"
    # Vértices en WGS84 como [[lon, lat], ...]. Si se cargan en UTM se
    # convierten automáticamente antes de llegar aquí.
    vertices: List[List[float]] = field(default_factory=list)
    superficie_ha: Optional[float] = None
    densidad_ind_ha: Optional[float] = None
    tasa_cosecha_pct: Optional[float] = None
    color: Optional[str] = None
    anualidad: Optional[str] = None


@dataclass
class DatosPlano:
    """Entrada completa para generar el plano."""
    predio_nombre: str = "Predio por definir"
    promovente: str = ""
    municipio: str = "Ensenada"
    estado: str = "Baja California"
    tecnico: str = ""
    registro_tecnico: str = ""
    fecha: str = ""
    escala: str = ""                       # vacío = escala automática
    sistema_coordenadas: str = "WGS84"     # "WGS84" | "UTM11N"
    zona_utm: int = ZONA_UTM
    # Polígono del predio en WGS84 [[lon, lat], ...]
    poligono: List[List[float]] = field(default_factory=list)
    areas: List[AreaAprovechamiento] = field(default_factory=list)
    # ANP opcional (dict con "nombre" y "vertices" en WGS84)
    anp: Optional[Dict] = None
    incluir_anp: bool = True
    observaciones: str = ""


# ---------------------------------------------------------------------------
# Parseo de coordenadas
# ---------------------------------------------------------------------------
def _cerrar_anillo(vertices: Sequence[Sequence[float]]) -> List[List[float]]:
    """Asegura que el anillo esté cerrado y sin duplicados consecutivos."""
    v = [[float(p[0]), float(p[1])] for p in vertices]
    limpio: List[List[float]] = []
    for p in v:
        if not limpio or limpio[-1] != p:
            limpio.append(p)
    if len(limpio) >= 3 and limpio[0] != limpio[-1]:
        limpio.append(list(limpio[0]))
    return limpio


def vertices_desde_texto(texto: str, sistema: str = "WGS84",
                         zona: int = ZONA_UTM) -> List[List[float]]:
    """Convierte un bloque de texto en una lista de vértices WGS84 [[lon, lat], ...].

    Formatos aceptados (un vértice por línea, o separados por ';'):
      * WGS84: ``31.8500, -116.6000``  (lat, lon)  o  ``-116.6 31.85`` (lon, lat)
      * UTM11N: ``540123, 3526789``    (este X, norte Y)  o  ``X=540123 Y=3526789``
    Las líneas vacías y las que empiezan con ``#`` se ignoran.
    """
    if not texto:
        return []
    sistema = (sistema or "WGS84").upper()
    crudo = texto.replace(";", "\n")
    salida: List[List[float]] = []
    for linea in crudo.splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            continue
        if sistema.startswith("UTM"):
            d = parse_utm(linea)
            if d is None:
                # intenta "este, norte" simple
                partes = [p for p in linea.replace("\t", " ").split() if p]
                nums = []
                for p in partes:
                    try:
                        nums.append(float(p.replace(",", "")))
                    except ValueError:
                        pass
                if len(nums) >= 2:
                    d = {"zona": zona, "hemisferio": "N",
                         "este": nums[0], "norte": nums[1]}
            if d is not None:
                lat, lon = utm_a_latlon(d["este"], d["norte"],
                                        d.get("zona", zona), d.get("hemisferio", "N"))
                salida.append([round(lon, 7), round(lat, 7)])
        else:
            par = parse_coordenadas(linea)
            if par is not None:
                lat, lon = par
                salida.append([round(lon, 7), round(lat, 7)])
    return salida


def poligono_rectangular(lat: float, lon: float, superficie_ha: float,
                         aspecto: float = 1.0) -> List[List[float]]:
    """Genera un polígono rectangular (WGS84) centrado en (lat, lon).

    Útil como respaldo cuando el usuario sólo proporciona un punto y una
    superficie. ``aspecto`` = ancho/alto del rectángulo.
    """
    area_m2 = max(float(superficie_ha), 0.01) * 10000.0
    alto = math.sqrt(area_m2 / max(aspecto, 1e-6))
    ancho = alto * aspecto
    dlat = (alto / 2.0) / 110574.0
    dlon = (ancho / 2.0) / (111320.0 * math.cos(math.radians(lat)))
    return [
        [round(lon - dlon, 7), round(lat - dlat, 7)],
        [round(lon + dlon, 7), round(lat - dlat, 7)],
        [round(lon + dlon, 7), round(lat + dlat, 7)],
        [round(lon - dlon, 7), round(lat + dlat, 7)],
        [round(lon - dlon, 7), round(lat - dlat, 7)],
    ]


# ---------------------------------------------------------------------------
# Construcción de capas (GeoDataFrames)
# ---------------------------------------------------------------------------
def _gdf_predio(datos: DatosPlano):
    import geopandas as gpd
    from shapely.geometry import Polygon

    if not datos.poligono or len(datos.poligono) < 3:
        raise ValueError("El polígono del predio requiere al menos 3 vértices.")
    anillo = _cerrar_anillo(datos.poligono)
    geom = Polygon(anillo)
    if not geom.is_valid:
        geom = geom.buffer(0)
    gdf = gpd.GeoDataFrame(
        [{
            "capa": "predio",
            "nombre": datos.predio_nombre,
            "promovente": datos.promovente,
            "municipio": datos.municipio,
            "estado": datos.estado,
        }],
        geometry=[geom], crs=f"EPSG:{EPSG_GEO}",
    )
    return gdf


def _gdf_areas(datos: DatosPlano):
    import geopandas as gpd
    from shapely.geometry import Polygon

    filas, geoms = [], []
    for i, a in enumerate(datos.areas, start=1):
        if not a.vertices or len(a.vertices) < 3:
            continue
        anillo = _cerrar_anillo(a.vertices)
        geom = Polygon(anillo)
        if not geom.is_valid:
            geom = geom.buffer(0)
        filas.append({
            "capa": "aprovechamiento",
            "id": i,
            "nombre": a.nombre,
            "tipo": a.tipo,
            "anualidad": a.anualidad or "",
            "densidad_ind_ha": a.densidad_ind_ha,
            "tasa_cosecha_pct": a.tasa_cosecha_pct,
            "color": a.color or COLORES_TIPO.get(a.tipo, "#7cb342"),
        })
        geoms.append(geom)
    if not filas:
        return gpd.GeoDataFrame(
            {"capa": [], "id": [], "nombre": [], "tipo": [],
             "anualidad": [], "densidad_ind_ha": [], "tasa_cosecha_pct": [],
             "color": []},
            geometry=[], crs=f"EPSG:{EPSG_GEO}",
        )
    return gpd.GeoDataFrame(filas, geometry=geoms, crs=f"EPSG:{EPSG_GEO}")


def construir_capas(datos: DatosPlano) -> Dict[str, "object"]:
    """Devuelve las capas en EPSG:4326 y EPSG:32611, con superficies calculadas."""
    _require_geo()
    gdf_predio = _gdf_predio(datos)
    gdf_areas = _gdf_areas(datos)

    predio_utm = gdf_predio.to_crs(EPSG_UTM)
    areas_utm = gdf_areas.to_crs(EPSG_UTM)

    # Superficie real (ha) calculada en proyección métrica
    sup_predio = [round(g.area / 10000.0, 2) for g in predio_utm.geometry]
    gdf_predio["superficie_ha"] = sup_predio
    predio_utm["superficie_ha"] = sup_predio
    if len(gdf_areas):
        sup_areas = [round(g.area / 10000.0, 2) for g in areas_utm.geometry]
        gdf_areas["superficie_ha"] = sup_areas
        areas_utm["superficie_ha"] = sup_areas

    return {
        "predio": gdf_predio,
        "areas": gdf_areas,
        "predio_utm": predio_utm,
        "areas_utm": areas_utm,
    }


# ---------------------------------------------------------------------------
# Exportación vectorial
# ---------------------------------------------------------------------------
def exportar_geojson(capas: Dict[str, "object"], path: str) -> str:
    """Escribe un GeoJSON (EPSG:4326) con las capas predio + áreas."""
    import geopandas as gpd

    predio = capas["predio"].copy()
    predio["superficie_ha"] = predio["superficie_ha"]
    partes = [predio]
    if len(capas["areas"]):
        partes.append(capas["areas"].copy())
    gdf = gpd.GeoDataFrame(
        __import__("pandas").concat(partes, ignore_index=True),
        crs=f"EPSG:{EPSG_GEO}",
    )
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    gdf.to_file(path, driver="GeoJSON", encoding="utf-8")
    return path


def _columnas_cortas(gdf):
    """Renombra columnas a <=10 caracteres (límite del Shapefile ESRI)."""
    mapa = {
        "superficie_ha": "sup_ha",
        "densidad_ind_ha": "dens_ind",
        "tasa_cosecha_pct": "tasa_cosec",
    }
    ren = {c: mapa[c] for c in gdf.columns if c in mapa}
    return gdf.rename(columns=ren) if ren else gdf


def exportar_shapefile(gdf, path: str, epsg: int = EPSG_UTM) -> str:
    """Escribe un Shapefile en la proyección indicada (por defecto UTM 11N)."""
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    g = _columnas_cortas(gdf.to_crs(epsg))
    # pyogrio/fiona escriben .shp/.shx/.dbf/.prj/.cpg
    g.to_file(path, driver="ESRI Shapefile", encoding="utf-8")
    return path


def _archivos_shapefile(shp_path: str) -> List[str]:
    base = os.path.splitext(shp_path)[0]
    return [base + ext for ext in (".shp", ".shx", ".dbf", ".prj", ".cpg", ".qix")
            if os.path.exists(base + ext)]


def comprimir_shapefile(shp_paths: Sequence[str], zip_path: str) -> str:
    """Comprime todos los componentes de los Shapefiles en un único ZIP."""
    os.makedirs(os.path.dirname(os.path.abspath(zip_path)) or ".", exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for shp in shp_paths:
            for f in _archivos_shapefile(shp):
                z.write(f, os.path.basename(f))
    return zip_path


# ---------------------------------------------------------------------------
# Render del mapa (matplotlib)
# ---------------------------------------------------------------------------
def _paso_rejilla(rango: float) -> float:
    """Elige un intervalo 'redondo' de retícula para un rango dado (metros)."""
    candidatos = [5, 10, 20, 25, 50, 100, 200, 250, 500,
                  1000, 2000, 2500, 5000, 10000, 20000, 50000]
    objetivo = rango / 6.0
    for c in candidatos:
        if c >= objetivo:
            return float(c)
    return float(candidatos[-1])


def _miles(v: float) -> str:
    return f"{int(round(v)):,}".replace(",", " ")


def _dibujar_mapa(datos: DatosPlano, capas: Dict[str, "object"],
                  out_png: str, dpi: int = 150) -> Dict:
    """Renderiza el plano a PNG y devuelve geotransform + extensión (UTM)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch, Rectangle
    import numpy as np

    gdf_predio = capas["predio_utm"]
    gdf_areas = capas["areas_utm"]

    fig = plt.figure(figsize=(11.0, 8.5), dpi=dpi, facecolor="white")
    ax = fig.add_axes([0.055, 0.135, 0.655, 0.745])
    side = fig.add_axes([0.725, 0.135, 0.255, 0.745])
    side.axis("off")
    side.set_xlim(0, 1)
    side.set_ylim(0, 1)

    # --- Extensión de datos (UTM) ---
    minx, miny, maxx, maxy = gdf_predio.total_bounds
    if len(gdf_areas):
        b = gdf_areas.total_bounds
        minx, miny = min(minx, b[0]), min(miny, b[1])
        maxx, maxy = max(maxx, b[2]), max(maxy, b[3])
    if datos.incluir_anp and datos.anp and datos.anp.get("vertices"):
        anp_v = _cerrar_anillo(datos.anp["vertices"])
        anp_utm = [latlon_a_utm(p[1], p[0], datos.zona_utm) for p in anp_v]
        xs = [d["este"] for d in anp_utm]
        ys = [d["norte"] for d in anp_utm]
        minx, miny = min(minx, min(xs)), min(miny, min(ys))
        maxx, maxy = max(maxx, max(xs)), max(maxy, max(ys))

    cx, cy = (minx + maxx) / 2.0, (miny + maxy) / 2.0
    dxd, dyd = (maxx - minx), (maxy - miny)

    # --- Ajuste de extensión al aspecto de la caja del mapa (escala uniforme) ---
    W = fig.get_figwidth() * dpi
    H = fig.get_figheight() * dpi
    box_ar = (0.655 * W) / (0.745 * H)
    rx = max(dxd * 1.18, 1.0)
    ry = max(dyd * 1.18, 1.0)
    if rx / ry < box_ar:
        rx = ry * box_ar
    else:
        ry = rx / box_ar
    xlim = (cx - rx / 2.0, cx + rx / 2.0)
    ylim = (cy - ry / 2.0, cy + ry / 2.0)
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    ax.set_aspect("auto")           # la extensión ya respeta el aspecto => escala uniforme
    ax.set_facecolor("#fcfcf8")

    # --- Retícula UTM ---
    paso = _paso_rejilla(rx)
    xt = np.arange(math.floor(xlim[0] / paso) * paso, xlim[1] + paso / 2, paso)
    yt = np.arange(math.floor(ylim[0] / paso) * paso, ylim[1] + paso / 2, paso)
    for x in xt:
        ax.axvline(x, color="#cfcfcf", lw=0.5, zorder=1)
    for y in yt:
        ax.axhline(y, color="#cfcfcf", lw=0.5, zorder=1)
    for x in xt:
        ax.text(x, ylim[0], _miles(x), ha="center", va="top", fontsize=5.5,
                color="#666", clip_on=False)
    for y in yt:
        ax.text(xlim[0], y, _miles(y), ha="right", va="center", fontsize=5.5,
                color="#666", clip_on=False)

    # --- ANP (si aplica) ---
    leyenda: List = []
    if datos.incluir_anp and datos.anp and datos.anp.get("vertices"):
        anp_v = _cerrar_anillo(datos.anp["vertices"])
        anp_utm = [latlon_a_utm(p[1], p[0], datos.zona_utm) for p in anp_v]
        ax.fill([d["este"] for d in anp_utm], [d["norte"] for d in anp_utm],
                facecolor="#e53935", alpha=0.12, edgecolor="#b71c1c",
                hatch="//", lw=1.0, zorder=2)
        leyenda.append(Patch(facecolor="#e53935", alpha=0.15, edgecolor="#b71c1c",
                             hatch="//", label=f'ANP: {datos.anp.get("nombre", "")}'))

    # --- Áreas de aprovechamiento ---
    for _, row in gdf_areas.iterrows():
        geom = row.geometry
        color = row.get("color") or COLORES_TIPO.get(row.get("tipo"), "#7cb342")
        polys = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
        for p in polys:
            xs, ys = p.exterior.xy
            ax.fill(xs, ys, facecolor=color, edgecolor="#333333",
                    lw=0.8, alpha=0.55, zorder=3)
        c = geom.representative_point()
        etiqueta = str(row.get("nombre", ""))
        if row.get("anualidad"):
            etiqueta += f"\n({row['anualidad']})"
        ax.annotate(etiqueta, (c.x, c.y), ha="center", va="center",
                    fontsize=6.8, zorder=6, color="#141414",
                    bbox=dict(boxstyle="round,pad=0.15", fc="white",
                              ec="none", alpha=0.6))
        sup = row.get("superficie_ha")
        etq_leg = f'{row.get("nombre","")} — {sup:.1f} ha' if sup is not None else str(row.get("nombre", ""))
        leyenda.append(Patch(facecolor=color, edgecolor="#333", alpha=0.55, label=etq_leg))

    # --- Polígono del predio ---
    for _, row in gdf_predio.iterrows():
        geom = row.geometry
        polys = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
        for p in polys:
            xs, ys = p.exterior.xy
            ax.plot(xs, ys, color="#b71c1c", lw=2.0, zorder=5)
    leyenda.append(Patch(facecolor="none", edgecolor="#b71c1c", lw=2.0,
                         label="Polígono del predio"))

    # --- Flecha de norte ---
    nx = xlim[1] - 0.055 * rx
    ax.annotate("", xy=(nx, ylim[1] - 0.03 * ry), xytext=(nx, ylim[1] - 0.16 * ry),
                arrowprops=dict(arrowstyle="-|>", color="#222", lw=2.2), zorder=9)
    ax.text(nx, ylim[1] - 0.185 * ry, "N", ha="center", va="top",
            fontsize=11, fontweight="bold", color="#222", zorder=9)

    # --- Escala gráfica ---
    m_per_px = rx / (0.655 * W)
    barra_m = _paso_rejilla(rx / 4.0)
    x0 = xlim[0] + 0.03 * rx
    y0 = ylim[0] + 0.045 * ry
    h_bar = 0.010 * ry
    ax.add_patch(Rectangle((x0, y0), barra_m / 2, h_bar, facecolor="#222",
                           edgecolor="#222", zorder=9))
    ax.add_patch(Rectangle((x0 + barra_m / 2, y0), barra_m / 2, h_bar,
                           facecolor="#fff", edgecolor="#222", zorder=9))
    ax.text(x0, y0 + 0.016 * ry, "0", ha="center", va="bottom", fontsize=6)
    ax.text(x0 + barra_m, y0 + 0.016 * ry, f"{int(barra_m)} m",
            ha="center", va="bottom", fontsize=6)
    ax.text(x0 + barra_m / 2, y0 - 0.018 * ry, "Escala gráfica",
            ha="center", va="top", fontsize=5.5, color="#555")

    # --- Encabezado ---
    fig.text(0.5, 0.962, "PLANO GEORREFERENCIADO DEL PREDIO Y ÁREAS DE APROVECHAMIENTO",
             ha="center", va="center", fontsize=12.5, fontweight="bold", color="#14351a")
    fig.text(0.5, 0.932,
             "Aprovechamiento de recursos forestales no maderables — tallos de Yucca (palmilla) · SEMARNAT",
             ha="center", va="center", fontsize=8, color="#444")
    fig.text(0.055, 0.905, f"Predio: {datos.predio_nombre}",
             ha="left", va="center", fontsize=9.5, fontweight="bold", color="#222")

    # --- Cuadro de datos (panel derecho) ---
    sup_predio = float(gdf_predio["superficie_ha"].iloc[0])
    sup_aprov = 0.0
    if len(gdf_areas):
        mask = gdf_areas["tipo"].str.lower().str.contains("aprovech", na=False)
        sup_aprov = float(gdf_areas.loc[mask, "superficie_ha"].sum()) if mask.any() else float(gdf_areas["superficie_ha"].sum())

    # Escala numérica
    if datos.escala:
        escala_txt = datos.escala
    else:
        denom = (m_per_px * dpi) / 0.0254
        if denom > 0:
            mag = 10 ** (math.floor(math.log10(denom)) - 1)
            denom = round(denom / mag) * mag
        escala_txt = f"1:{int(denom):,}".replace(",", " ")

    filas_datos = [
        ("DATOS DEL PREDIO", ""),
        ("Nombre", datos.predio_nombre),
        ("Promovente", datos.promovente or "—"),
        ("Municipio", datos.municipio),
        ("Estado", datos.estado),
        ("Superficie total", f"{sup_predio:,.2f} ha".replace(",", " ")),
        ("Superficie aprovechamiento", f"{sup_aprov:,.2f} ha".replace(",", " ")),
        ("", ""),
        ("SISTEMA DE REFERENCIA", ""),
        ("Proyección", f"UTM Zona {datos.zona_utm}N"),
        ("Datum", "WGS 84"),
        ("EPSG", f"{EPSG_UTM}"),
        ("Coordenadas", "Este (X) / Norte (Y) [m]"),
        ("", ""),
        ("CARTOGRAFÍA", ""),
        ("Escala aprox.", escala_txt),
        ("Fecha", datos.fecha or "—"),
        ("Técnico", datos.tecnico or "—"),
        ("Reg. técnico", datos.registro_tecnico or "—"),
    ]
    y = 0.985
    for etq, val in filas_datos:
        if etq and not val:
            side.text(0.0, y, etq, ha="left", va="top", fontsize=7.6,
                      fontweight="bold", color="#14351a")
            y -= 0.030
            side.plot([0.0, 1.0], [y + 0.008, y + 0.008], color="#bbb", lw=0.6,
                      clip_on=False)
            y -= 0.006
        elif etq:
            side.text(0.0, y, etq + ":", ha="left", va="top", fontsize=6.8, color="#555")
            side.text(1.0, y, str(val), ha="right", va="top", fontsize=6.8, color="#111")
            y -= 0.026
        else:
            y -= 0.012

    # --- Leyenda ---
    y -= 0.010
    side.text(0.0, y, "LEYENDA", ha="left", va="top", fontsize=7.6,
              fontweight="bold", color="#14351a")
    y -= 0.032
    for patch in leyenda:
        side.add_patch(Rectangle((0.0, y - 0.012), 0.055, 0.020,
                                 transform=side.transAxes,
                                 facecolor=patch.get_facecolor(),
                                 edgecolor=patch.get_edgecolor(),
                                 alpha=patch.get_alpha() or 1.0))
        side.text(0.075, y, patch.get_label(), ha="left", va="center",
                  fontsize=6.4, color="#222", wrap=True)
        y -= 0.030

    if datos.observaciones:
        y -= 0.008
        side.text(0.0, y, "OBSERVACIONES", ha="left", va="top", fontsize=7.0,
                  fontweight="bold", color="#14351a")
        y -= 0.026
        side.text(0.0, y, datos.observaciones, ha="left", va="top",
                  fontsize=6.2, color="#333", wrap=True)

    # --- Pie ---
    fig.text(0.055, 0.055,
             "Sistema de referencia: WGS 84 / UTM Zona 11N (EPSG:32611). "
             "Elaborado conforme al Reglamento de la LGDFS, Art. 57 y la NOM-005-SEMARNAT-1997.",
             ha="left", va="center", fontsize=6.4, color="#666")
    fig.text(0.945, 0.055, "PalmillaBot · Módulo D — Plano georreferenciado",
             ha="right", va="center", fontsize=6.4, color="#888")

    # --- Geotransform para georreferenciación ---
    fig.canvas.draw()
    bb = ax.get_window_extent()
    px0, px1 = bb.x0, bb.x1
    py_top = H - bb.y1
    py_bot = H - bb.y0
    dx = (xlim[1] - xlim[0]) / (px1 - px0)
    dy = (ylim[1] - ylim[0]) / (py_bot - py_top)
    gt = (xlim[0] - px0 * dx, dx, 0.0, ylim[1] + py_top * dy, 0.0, -dy)

    os.makedirs(os.path.dirname(os.path.abspath(out_png)) or ".", exist_ok=True)
    fig.savefig(out_png, dpi=dpi, facecolor="white")
    plt.close(fig)

    return {
        "png": out_png,
        "gt": gt,
        "epsg": EPSG_UTM,
        "extent": [xlim[0], ylim[0], xlim[1], ylim[1]],
        "dpi": dpi,
        "escala": escala_txt,
    }


# ---------------------------------------------------------------------------
# GeoPDF
# ---------------------------------------------------------------------------
def _png_size(path: str) -> Tuple[int, int]:
    """Lee ancho y alto (px) de la cabecera IHDR de un PNG."""
    with open(path, "rb") as fh:
        head = fh.read(26)
    return int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")


def _geopdf_por_cli(png_path: str, out_pdf: str, gt: Sequence[float],
                    epsg: int, dpi: int) -> bool:
    """Genera el GeoPDF con el ejecutable ``gdal_translate`` (respaldo para macOS)."""
    if shutil.which("gdal_translate") is None:
        return False
    try:
        w, h = _png_size(png_path)
        x0, dx, _, y0, _, dy = gt
        bandas = ""
        for i, ci in enumerate(("Red", "Green", "Blue"), start=1):
            bandas += (
                f'  <VRTRasterBand dataType="Byte" band="{i}">\n'
                f"    <ColorInterp>{ci}</ColorInterp>\n"
                "    <SimpleSource>\n"
                f'      <SourceFilename relativeToVRT="1">{os.path.basename(png_path)}</SourceFilename>\n'
                f"      <SourceBand>{i}</SourceBand>\n"
                f'      <SrcRect xOff="0" yOff="0" xSize="{w}" ySize="{h}"/>\n'
                f'      <DstRect xOff="0" yOff="0" xSize="{w}" ySize="{h}"/>\n'
                "    </SimpleSource>\n"
                "  </VRTRasterBand>\n"
            )
        vrt = (
            f'<VRTDataset rasterXSize="{w}" rasterYSize="{h}">\n'
            f"  <SRS>EPSG:{epsg}</SRS>\n"
            f"  <GeoTransform>{x0}, {dx}, 0.0, {y0}, 0.0, {dy}</GeoTransform>\n"
            f"{bandas}</VRTDataset>\n"
        )
        vrt_path = os.path.join(
            os.path.dirname(os.path.abspath(png_path)),
            os.path.basename(os.path.splitext(out_pdf)[0]) + ".vrt")
        with open(vrt_path, "w", encoding="utf-8") as fh:
            fh.write(vrt)
        try:
            subprocess.run(
                ["gdal_translate", "-of", "PDF", "-co", "GEO_ENCODING=OGC_BP",
                 "-co", f"DPI={dpi}", "-co", "COMPRESS=DEFLATE", vrt_path, out_pdf],
                check=True, capture_output=True,
            )
        finally:
            if os.path.exists(vrt_path):
                os.unlink(vrt_path)
        return os.path.exists(out_pdf) and os.path.getsize(out_pdf) > 0
    except Exception:  # noqa: BLE001
        return False


def png_a_geopdf(png_path: str, out_pdf: str, gt: Sequence[float],
                 epsg: int = EPSG_UTM, dpi: int = 150) -> Tuple[str, bool]:
    """Convierte un PNG + geotransform en un GeoPDF georreferenciado.

    Devuelve ``(ruta_pdf, georreferenciado)``. Estrategia:
      1. Bindings de Python de GDAL (``osgeo``) — georreferenciación OGC.
      2. Ejecutable ``gdal_translate`` — respaldo habitual en macOS (Homebrew).
      3. PDF normal con matplotlib — ``georreferenciado=False``.
    """
    gdal, _ogr, osr = _osgeo()
    os.makedirs(os.path.dirname(os.path.abspath(out_pdf)) or ".", exist_ok=True)

    if gdal is not None:
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(epsg)
        tmp_tif = tempfile.NamedTemporaryFile(suffix=".tif", delete=False).name
        gdal.PushErrorHandler("CPLQuietErrorHandler")
        try:
            src = gdal.Open(png_path)
            ds = gdal.Translate(tmp_tif, src, format="GTiff")
            ds.SetGeoTransform(tuple(gt))
            ds.SetProjection(srs.ExportToWkt())
            ds = None
            src = None
            gdal.Translate(
                out_pdf, tmp_tif, format="PDF",
                creationOptions=[
                    "GEO_ENCODING=OGC_BP",
                    f"DPI={dpi}",
                    "COMPRESS=DEFLATE",
                    "STREAM_COMPRESS=DEFLATE",
                ],
            )
        except Exception:  # noqa: BLE001
            pass
        finally:
            gdal.PopErrorHandler()
            if os.path.exists(tmp_tif):
                os.unlink(tmp_tif)
        if os.path.exists(out_pdf) and os.path.getsize(out_pdf) > 0:
            return out_pdf, True

    # Respaldo 1: gdal_translate por línea de comandos
    if _geopdf_por_cli(png_path, out_pdf, gt, epsg, dpi):
        return out_pdf, True

    # Respaldo 2: PDF normal (sin georreferenciación)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.image as mpimg
    img = mpimg.imread(png_path)
    fig = plt.figure(figsize=(11.0, 8.5), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.imshow(img)
    ax.axis("off")
    fig.savefig(out_pdf, dpi=dpi, facecolor="white")
    plt.close(fig)
    return out_pdf, False


# ---------------------------------------------------------------------------
# Orquestador
# ---------------------------------------------------------------------------
def generar_plano(datos: DatosPlano, out_dir: str,
                  nombre: str = "plano_predio", dpi: int = 150) -> Dict:
    """Genera todos los productos del plano y devuelve un diccionario de rutas.

    Productos:
      * ``shp_predio``, ``shp_areas``, ``shp_completo`` — Shapefiles (UTM 11N)
      * ``shp_zip`` — ZIP con los Shapefiles
      * ``geojson`` — GeoJSON (WGS84)
      * ``png`` — vista previa
      * ``geopdf`` — GeoPDF georreferenciado
    """
    _require_geo()
    import pandas as pd

    os.makedirs(out_dir, exist_ok=True)
    base = os.path.join(out_dir, nombre)

    capas = construir_capas(datos)

    # --- GeoJSON ---
    geojson = exportar_geojson(capas, base + ".geojson")

    # --- Shapefiles ---
    shp_predio = exportar_shapefile(capas["predio"], base + "_predio.shp")
    shp_areas = None
    if len(capas["areas"]):
        shp_areas = exportar_shapefile(capas["areas"], base + "_areas.shp")

    # Capa combinada (predio + áreas) con campo 'capa'
    partes = [capas["predio"].to_crs(EPSG_UTM)]
    if len(capas["areas"]):
        partes.append(capas["areas"].to_crs(EPSG_UTM))
    combinado = __import__("geopandas").GeoDataFrame(
        pd.concat(partes, ignore_index=True), crs=f"EPSG:{EPSG_UTM}")
    shp_completo = exportar_shapefile(combinado, base + ".shp")

    shps = [shp_predio, shp_completo] + ([shp_areas] if shp_areas else [])
    shp_zip = comprimir_shapefile(shps, base + "_shapefile.zip")

    # --- Mapa PNG + GeoPDF ---
    info = _dibujar_mapa(datos, capas, base + ".png", dpi=dpi)
    geopdf, georref = png_a_geopdf(base + ".png", base + "_georreferenciado.pdf",
                                   info["gt"], info["epsg"], dpi=dpi)
    # Limpia los sidecar .aux.xml que GDAL puede dejar al leer el raster/PDF.
    for extra in (base + ".png.aux.xml", geopdf + ".aux.xml"):
        if os.path.exists(extra):
            os.unlink(extra)

    sup_predio = float(capas["predio"]["superficie_ha"].iloc[0])
    sup_aprov = 0.0
    if len(capas["areas"]):
        mask = capas["areas"]["tipo"].str.lower().str.contains("aprovech", na=False)
        sup_aprov = float(capas["areas"].loc[mask, "superficie_ha"].sum()) if mask.any() \
            else float(capas["areas"]["superficie_ha"].sum())

    return {
        "ok": True,
        "nombre": nombre,
        "predio_nombre": datos.predio_nombre,
        "epsg": EPSG_UTM,
        "sistema": f"WGS 84 / UTM Zona {datos.zona_utm}N (EPSG:{EPSG_UTM})",
        "escala": info["escala"],
        "georreferenciado": georref,
        "superficie_predio_ha": round(sup_predio, 2),
        "superficie_aprovechamiento_ha": round(sup_aprov, 2),
        "num_areas": int(len(capas["areas"])),
        "archivos": {
            "geopdf": geopdf,
            "png": info["png"],
            "geojson": geojson,
            "shp_predio": shp_predio,
            "shp_areas": shp_areas,
            "shp_completo": shp_completo,
            "shp_zip": shp_zip,
        },
        "areas": (
            capas["areas"][["nombre", "tipo", "superficie_ha"]]
            .to_dict(orient="records") if len(capas["areas"]) else []
        ),
    }


# ---------------------------------------------------------------------------
# Datos de ejemplo
# ---------------------------------------------------------------------------
def datos_ejemplo() -> DatosPlano:
    """Predio de ejemplo (~100 ha) en el matorral desértico de Baja California."""
    # Rectángulo base ~1 000 m x 1 000 m centrado cerca de San Quintín, B.C.
    lat0, lon0 = 30.5045, -115.8948
    predio = poligono_rectangular(lat0, lon0, 100.0, aspecto=1.0)

    # Subdivide el predio en 4 cuadrantes de aprovechamiento + franja de conservación
    lon_min, lon_max = -115.9000, -115.8896
    lat_min, lat_max = 30.5000, 30.5090
    lon_mid = (lon_min + lon_max) / 2
    lat_mid = (lat_min + lat_max) / 2
    b = 0.0004  # ~40 m de margen

    def rect(a, c, d, e):
        return [[a, c], [d, c], [d, e], [a, e], [a, c]]

    areas = [
        AreaAprovechamiento(
            nombre="Área 1 — Cuadrante SO", tipo="Aprovechamiento",
            vertices=rect(lon_min + b, lat_min + b, lon_mid - b / 2, lat_mid - b / 2),
            densidad_ind_ha=340, tasa_cosecha_pct=50, anualidad="Anualidad 1"),
        AreaAprovechamiento(
            nombre="Área 2 — Cuadrante SE", tipo="Aprovechamiento",
            vertices=rect(lon_mid + b / 2, lat_min + b, lon_max - b, lat_mid - b / 2),
            densidad_ind_ha=310, tasa_cosecha_pct=50, anualidad="Anualidad 1"),
        AreaAprovechamiento(
            nombre="Área 3 — Cuadrante NE", tipo="Aprovechamiento",
            vertices=rect(lon_mid + b / 2, lat_mid + b / 2, lon_max - b, lat_max - b),
            densidad_ind_ha=300, tasa_cosecha_pct=45, anualidad="Anualidad 2"),
        AreaAprovechamiento(
            nombre="Área 4 — Cuadrante NO", tipo="Aprovechamiento",
            vertices=rect(lon_min + b, lat_mid + b / 2, lon_mid - b / 2, lat_max - b),
            densidad_ind_ha=330, tasa_cosecha_pct=45, anualidad="Anualidad 2"),
        AreaAprovechamiento(
            nombre="Franja de conservación (arroyo)", tipo="Conservación",
            vertices=rect(lon_mid - 0.0002, lat_min + b, lon_mid + 0.0002, lat_max - b),
            densidad_ind_ha=0, tasa_cosecha_pct=0),
    ]

    return DatosPlano(
        predio_nombre="Predio Ejido San Quintín — Lote 7",
        promovente="Ejido San Quintín",
        municipio="San Quintín",
        estado="Baja California",
        tecnico="Ing. Forestal (Técnico Certificado)",
        registro_tecnico="RFN-0123",
        fecha="",
        poligono=predio,
        areas=areas,
        observaciones="Plano demostrativo generado por PalmillaBot (Módulo D).",
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _main(argv: Optional[List[str]] = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Genera el plano georreferenciado (Shapefile/GeoPDF).")
    ap.add_argument("--out", default="output", help="Directorio de salida.")
    ap.add_argument("--nombre", default="plano_predio", help="Nombre base de los archivos.")
    ap.add_argument("--entrada", default=None,
                    help="JSON con los datos del plano (si se omite, usa el ejemplo).")
    ap.add_argument("--dpi", type=int, default=150)
    args = ap.parse_args(argv)

    if args.entrada:
        with open(args.entrada, encoding="utf-8") as fh:
            raw = json.load(fh)
        areas = [AreaAprovechamiento(**a) for a in raw.pop("areas", [])]
        datos = DatosPlano(areas=areas, **raw)
    else:
        datos = datos_ejemplo()

    res = generar_plano(datos, args.out, nombre=args.nombre, dpi=args.dpi)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
