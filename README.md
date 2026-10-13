# 🌵 PalmillaBot — Sistema de Agente IA para el Aprovechamiento Forestal No Maderable de Palmilla (*Yucca* spp.)

Agente de inteligencia artificial (rol: **Ingeniero Forestal**) que asiste en la obtención de permisos para el aprovechamiento de **recursos forestales no maderables (RFNM)** —tallos de *Yucca* (palmilla)— en **Baja California, México**, y que **genera el Programa de Manejo Forestal Simplificado** exigido por la SEMARNAT.

El sistema combina un **motor de reglas jurídicas**, un **RAG normativo** (recuperación y citación de la ley) y **IA generativa con Google Gemini** para redactar respuestas y documentos técnicos.

---

## ⚖️ Fundamento legal clave

El aprovechamiento de **tallos de *Yucca*** **NO** se realiza por simple **aviso**: requiere **AUTORIZACIÓN expresa** de la SEMARNAT conforme al **artículo 85, inciso b) de la LGDFS**, con **Programa de Manejo Forestal Simplificado** (Reglamento LGDFS Art. 57) y formato **FF-SEMARNAT-074** (trámite **SEMARNAT-03-052**).

---

## 🚀 Instalación y ejecución en Mac (rápida)

Requisitos: **macOS** y **Python 3.9+** (si no lo tienes: `brew install python@3.12` o descárgalo de [python.org](https://www.python.org/downloads/macos/)).

```bash
# 1. Entra a la carpeta del proyecto
cd palmilla/sistema_palmilla

# 2. Ejecuta el instalador (crea el entorno virtual e instala todo)
chmod +x install.sh run.sh "Iniciar PalmillaBot.command"
./install.sh

# 3. Inicia PalmillaBot
./run.sh
```

El instalador:
1. Verifica que exista **Python 3.9+**.
2. Crea un **entorno virtual** aislado en `./venv`.
3. Instala las **dependencias** de Python (`requirements.txt`).
4. Comprueba/instala **wkhtmltopdf** (para exportar el PMF a **PDF**).
5. Te permite **guardar tu API key de Gemini** (opcional).

Luego abre tu navegador en **http://localhost:8000**.

> 💡 **Alternativa con doble clic:** en el Finder, haz doble clic en **`Iniciar PalmillaBot.command`**. La primera vez instalará todo automáticamente y después arrancará el servidor y abrirá el navegador.

### Opciones de `run.sh`

```bash
./run.sh                 # puerto 8000 + abre el navegador
./run.sh --port 9000     # puerto personalizado
./run.sh --no-browser    # no abrir el navegador
```

---

## ✨ Integración con Google Gemini (IA)

PalmillaBot usa **Google Gemini** para redactar las respuestas del chat y el Programa de Manejo. Necesitas una **API key gratuita** de [Google AI Studio](https://aistudio.google.com/app/apikey).

Hay **tres formas** de configurarla (por orden de prioridad):

1. **Variable de entorno** `GEMINI_API_KEY` (tiene prioridad).
2. **Desde la interfaz web** → pestaña **⚙️ Configuración** (se guarda en `config.json`).
3. **Durante la instalación** (`./install.sh` te la pide).

```bash
# Ejemplo con variable de entorno
export GEMINI_API_KEY="AIza...tu_clave..."
./run.sh
```

**Sin API key**, el sistema sigue funcionando en **modo RAG offline**: recupera y cita la normatividad y genera el PMF con la plantilla determinista, pero sin redacción por IA.

> 🔒 **Privacidad:** la clave se guarda solo en tu computadora (`config.json`, permisos `600`) y **nunca se sube a GitHub** (está en `.gitignore`). Las consultas van directamente a la API de Google.

---

## 🧠 Arquitectura (4 módulos + IA)

| Módulo | Archivo | Función |
|---|---|---|
| **A — RAG Normativo** | `src/rag_engine.py` | Índice TF-IDF sobre 467 pasajes (disposiciones estructuradas + corpus legal). Recupera y **cita** artículos. |
| **B — Motor de Reglas** | `src/rules_engine.py` | Determina **vía de trámite**, **checklist**, autorizaciones adicionales (ANP/NOM-059) y reglas técnicas. |
| **C — Generador PMF** | `src/project_generator.py` | Calcula inventario/cosecha y **genera el Programa de Manejo** (6 secciones) → MD/HTML/DOCX/PDF. |
| **D — Plano Georreferenciado** | `src/plano_geo.py` | Genera el **plano del predio con las áreas de aprovechamiento** → **Shapefile** (EPSG:32611), **GeoPDF** georreferenciado, GeoJSON y PNG. |
| **Geoespacial ANP** | `src/geo_anp.py` | Detección automática de Áreas Naturales Protegidas por coordenadas (bloqueo *NO PROCEDE*). |
| **IA — Gemini** | `src/gemini_client.py` | Cliente REST de Google Gemini (redacción de respuestas y del PMF). |
| **Configuración** | `src/config.py` | Persistencia segura de la API key y del modelo. |
| System Prompt | `src/system_prompt.py` | Rol del agente y formato de salida de 6 secciones. |
| Orquestador | `src/agent_core.py` | Integra los 4 módulos + IA en una respuesta única. |
| Backend | `src/app.py` | API REST (FastAPI). |
| Frontend | `web/index.html`, `web/style.css`, `web/app.js` | Interfaz web (5 pestañas). |

---

## 🗺️ Plano georreferenciado (Shapefile / GeoPDF)

El **Módulo D** (`src/plano_geo.py`) produce el **plano georreferenciado del
polígono del predio con las áreas de aprovechamiento**, conforme al
**Reglamento de la LGDFS, Art. 57** y la **NOM-005-SEMARNAT-1997**. Genera:

| Producto | Formato | Sistema de referencia |
|---|---|---|
| **Shapefile** (predio, áreas y capa combinada) | `.shp/.shx/.dbf/.prj/.cpg` | WGS 84 / UTM 11N — **EPSG:32611** |
| **GeoPDF** georreferenciado | `.pdf` (OGC / ISO 32000) | EPSG:32611 |
| **GeoJSON** | `.geojson` | WGS 84 — EPSG:4326 |
| **Vista previa** | `.png` | EPSG:32611 |

El plano incluye retícula de coordenadas UTM, flecha de norte, escala gráfica,
leyenda, cuadro de datos del predio y las superficies calculadas en proyección
métrica. Se puede generar desde la pestaña **🗺️ Plano Georreferenciado** de la
interfaz web o por línea de comandos:

```bash
cd src
python3 plano_geo.py --out ../output                       # ejemplo integrado
python3 plano_geo.py --entrada ../data/planos/ejemplo_predio.json \
                     --out ../output --nombre plano_predio
```

> **Nota:** para el **GeoPDF** con georreferenciación OGC se requiere **GDAL**
> (`brew install gdal` en macOS o `apt install gdal-bin` en Linux). Sin GDAL, el
> Shapefile y el GeoJSON se generan igualmente, y el PDF se produce sin
> metadatos geoespaciales.

---

## 🖥️ Uso por línea de comandos

```bash
cd sistema_palmilla/src
python3 agent_core.py            # demo del orquestador (análisis + chat RAG)
python3 project_generator.py     # demo del generador de PMF
python3 rag_engine.py            # demo del RAG normativo
python3 gemini_client.py         # prueba de conexión con Gemini
python3 plano_geo.py --out ../output   # demo del plano georreferenciado (Módulo D)
```

---

## 🔌 API REST

| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/api/salud` | Estado del servicio |
| GET | `/api/normas` | Catálogo de normas, trámites y parámetros |
| POST | `/api/analizar` | Análisis completo del predio (Módulos A+B+C) |
| POST | `/api/chat` | Consulta libre al RAG + IA (`usar_ia: true/false`) |
| POST | `/api/generar` | Genera el PMF con la plantilla determinista |
| POST | `/api/generar-ia` | Genera el PMF redactado con **Gemini** |
| POST | `/api/exportar` | Exporta un Markdown (p. ej. de IA) a PDF/DOCX/HTML/MD |
| POST | `/api/plano` | Genera el **plano georreferenciado** (Shapefile + GeoPDF + GeoJSON + PNG) |
| GET | `/api/plano/ejemplo` | Genera el plano con los datos de ejemplo |
| GET | `/api/plano/descargar/{geopdf\|shp\|geojson\|png}` | Descarga los productos del plano |
| GET | `/api/descargar/{pdf\|docx\|md\|html}` | Descarga el PMF (plantilla) |
| GET/POST | `/api/config` | Consulta/guarda la API key y el modelo |
| POST | `/api/config/validar` | Valida la API key contra la API de Google |

---

## 📁 Estructura

```
sistema_palmilla/
├── corpus/            # PDFs y TXT oficiales (LGDFS, Reglamento, NOM-005/059/152)
├── src/               # Código de los 4 módulos + IA + backend
├── web/               # Frontend (HTML/CSS/JS)
├── data/
│   ├── anp/           # GeoJSON de Áreas Naturales Protegidas (detección)
│   └── planos/        # Datos de entrada del plano georreferenciado (Módulo D)
├── docs/              # Documento de arquitectura + PMF de ejemplo
├── output/            # Salidas generadas por la API (no se sube a GitHub)
├── install.sh         # Instalador para macOS
├── run.sh             # Iniciador (servidor + navegador)
├── Iniciar PalmillaBot.command   # Lanzador con doble clic (Finder)
├── requirements.txt   # Dependencias de Python
├── .env.example       # Ejemplo de variables de entorno
└── README.md
```

---

## 📄 Entregables (`docs/`)

- `ARQUITECTURA.pdf` / `ARQUITECTURA.html` — Documento técnico de arquitectura.
- `PMF_EJEMPLO.pdf` / `.docx` / `.html` / `.md` — Programa de Manejo de ejemplo (predio ejidal de 180 ha).

---

## 🛠️ Solución de problemas (Mac)

- **«command not found: python3»** → instala Python: `brew install python@3.12`.
- **No se genera el PDF** → instala wkhtmltopdf: `brew install --cask wkhtmltopdf`.
- **Aviso de seguridad al abrir el `.command`** → en *Ajustes del Sistema → Privacidad y seguridad* pulsa «Abrir igualmente», o ejecuta:
  `xattr -d com.apple.quarantine "Iniciar PalmillaBot.command"`.
- **«IA: sin configurar»** → añade tu API key en la pestaña **⚙️ Configuración** y pulsa **Validar conexión**.

---

## ⚠️ Responsabilidad

Los documentos generados son **borradores técnicos**. Deben ser **validados y firmados por un Técnico Forestal Certificado** inscrito en el Registro Forestal Nacional y presentados ante la SEMARNAT. El sistema no realiza muestreo de campo; las cifras dependen de los datos proporcionados.
