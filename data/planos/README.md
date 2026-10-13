# `data/planos/` — Datos de entrada del plano georreferenciado (Módulo D)

Esta carpeta contiene ejemplos de **datos de entrada** para el generador del
plano georreferenciado (`src/plano_geo.py`).

## Archivo de ejemplo

`ejemplo_predio.json` describe un predio demostrativo de ~100 ha en el matorral
desértico de Baja California, con **4 áreas de aprovechamiento** y **1 franja de
conservación**.

## Estructura del JSON

```jsonc
{
  "predio_nombre": "Predio Ejido San Quintín — Lote 7",
  "promovente": "Ejido San Quintín",
  "municipio": "San Quintín",
  "estado": "Baja California",
  "tecnico": "Ing. Forestal (Técnico Certificado)",
  "registro_tecnico": "RFN-0123",
  "fecha": "",
  "escala": "",
  "zona_utm": 11,

  // Polígono del predio en WGS 84: [[longitud, latitud], ...]
  "poligono": [
    [-115.9000, 30.5000],
    [-115.8896, 30.5000],
    [-115.8896, 30.5090],
    [-115.9000, 30.5090]
  ],

  // Áreas de aprovechamiento (sub-polígonos del predio)
  "areas": [
    {
      "nombre": "Área 1 — Cuadrante SO",
      "tipo": "Aprovechamiento",          // Aprovechamiento | Conservación | Exclusión | Amortiguamiento | Vialidad | Restauración
      "vertices": [[-115.8996, 30.5004], [-115.8950, 30.5004], [-115.8950, 30.5043], [-115.8996, 30.5043]],
      "densidad_ind_ha": 340,
      "tasa_cosecha_pct": 50,
      "anualidad": "Anualidad 1"
    }
  ],

  "observaciones": "Plano demostrativo generado por PalmillaBot (Módulo D)."
}
```

> **Nota:** las coordenadas del JSON se expresan en **WGS 84** con el orden
> `[longitud, latitud]` (formato GeoJSON). La interfaz web permite introducirlas
> en **latitud, longitud** o en **UTM 11N (Este, Norte)** y las convierte
> automáticamente.

## Uso por línea de comandos

```bash
cd src
python plano_geo.py --entrada ../data/planos/ejemplo_predio.json \
                    --out ../output --nombre plano_predio
```

Sin `--entrada`, se usa el ejemplo integrado:

```bash
python plano_geo.py --out ../output
```

## Productos generados

| Archivo | Descripción |
|---------|-------------|
| `*_georreferenciado.pdf` | **GeoPDF** georreferenciado (OGC / ISO 32000) |
| `*.png` | Vista previa del plano |
| `*.geojson` | Capa vectorial (WGS 84 / EPSG:4326) |
| `*_predio.shp` | Shapefile del polígono del predio (EPSG:32611) |
| `*_areas.shp` | Shapefile de las áreas de aprovechamiento (EPSG:32611) |
| `*.shp` | Shapefile combinado (predio + áreas) |
| `*_shapefile.zip` | ZIP con todos los Shapefiles y sus componentes |
