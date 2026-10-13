# Polígonos de Áreas Naturales Protegidas (ANP)

Esta carpeta contiene los **polígonos vectoriales** que PalmillaBot usa para
determinar, de forma automática, si una ubicación geográfica cae dentro de un
Área Natural Protegida (ANP). Si el predio cae dentro de una ANP con
restricción de extracción, el sistema **bloquea el trámite** ("NO PROCEDE").

El motor geoespacial (`src/geo_anp.py`) intenta primero leer los polígonos
reales aquí guardados (formato **GeoJSON**) y, si no existen, recurre a un
**catálogo interno con caja envolvente (bounding box)** como respaldo.

## Formato esperado

Cada archivo `*.geojson` (o `*.json`) debe ser un `FeatureCollection` (o un
`Feature` suelto) con geometría `Polygon` o `MultiPolygon` en **WGS 84
(EPSG:4326)** y coordenadas en orden GeoJSON `[longitud, latitud]`.

Propiedades reconocidas (opcionales, con valores por defecto):

| Propiedad     | Descripción                                                        |
|---------------|--------------------------------------------------------------------|
| `clave`       | Clave corta del ANP (p. ej. `RB-AGC-DRC`).                         |
| `nombre`      | Nombre oficial del ANP.                                            |
| `categoria`   | Categoría (Reserva de la Biósfera, Parque Nacional, etc.).         |
| `estado`      | Estado(s) donde se ubica.                                          |
| `restriccion` | `prohibido` (bloquea el trámite) o `restringido` (solo advierte).  |
| `fundamento`  | Fundamento legal (decreto, LGEEPA, NOM-005, etc.).                 |
| `nota`        | Nota adicional.                                                    |
| `fuente`      | Fuente del dato.                                                   |

Ejemplo mínimo:

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "clave": "RB-AGC-DRC",
        "nombre": "Reserva de la Biósfera del Alto Golfo de California y Delta del Río Colorado",
        "categoria": "Reserva de la Biósfera",
        "estado": "Baja California / Sonora",
        "restriccion": "prohibido",
        "fundamento": "LGEEPA Arts. 44-50; Decreto (DOF 07/06/1993)",
        "fuente": "CONANP / CONABIO"
      },
      "geometry": { "type": "Polygon", "coordinates": [[[lon, lat], ...]] }
    }
  ]
}
```

## Cómo obtener los polígonos oficiales

### Opción A — CONANP (Portal SIG / SIMEC)

1. Entra al portal de información geográfica de la **CONANP** (SIG) o al
   **SIMEC** (<https://simec.conanp.gob.mx/>).
2. Descarga la capa de **Áreas Naturales Protegidas** (Shapefile `.shp`).
3. Convierte el Shapefile a GeoJSON (por ejemplo con `ogr2ogr`):

   ```bash
   ogr2ogr -f GeoJSON -t_srs EPSG:4326 rb_alto_golfo.geojson \
     ANP_federales.shp -where "NOMBRE LIKE '%Alto Golfo%'"
   ```

### Opción B — CONABIO (Geoportal de Metadatos)

1. Entra al **Geoportal de Metadatos de CONABIO** y busca la capa
   **"Áreas Naturales Protegidas Federales de México"**.
2. Descarga el Shapefile. Incluye el **polígono de la caja envolvente
   (buffer externo)** y las subdivisiones de **Zonas Núcleo**.
3. Convierte a GeoJSON e inclúyelo en esta carpeta. Se recomienda guardar
   **dos archivos**:
   - `rb_alto_golfo.geojson` → polígono general (buffer externo).
   - `rb_alto_golfo_zonas_nucleo.geojson` → Zonas Núcleo (restricción 100 %).

## Sistema de referencia (CRS)

- **Geográfico:** WGS 84 (EPSG:4326) — usado en los GeoJSON.
- **Proyectado:** WGS 84 / UTM zona **11N** (**EPSG:32611**) — usado para
  capturar/reportar coordenadas en campo.
- **Datum:** WGS 84 o GRS 80.

## Caja envolvente de referencia (Alto Golfo)

La Reserva de la Biósfera del Alto Golfo de California y Delta del Río Colorado
abarca aproximadamente:

- **Latitud Norte:** entre 31°00'N y 32°10'N.
- **Longitud Oeste:** entre 113°30'O y 115°15'O.
- Límite terrestre en Baja California: marcado por la **Carretera Federal 5**
  (Mexicali–San Felipe), desde ~km 80 al sur hasta la costa de San Felipe,
  cerrando desde **Punta Machorro**.

> ⚠️ El archivo `rb_alto_golfo.geojson` incluido aquí es una **aproximación
> ilustrativa** (envolvente). Para producción, **reemplázalo** por el polígono
> oficial descargado de CONANP/CONABIO.
