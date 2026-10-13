# -*- coding: utf-8 -*-
"""
BACKEND FastAPI — API del Agente PalmillaBot
============================================
Expone los 3 módulos del sistema vía HTTP y sirve el frontend estático.

Endpoints:
  GET  /                     -> frontend (web/index.html)
  GET  /api/salud            -> estado del servicio
  GET  /api/normas           -> catálogo de normas, trámites y parámetros
  POST /api/analizar         -> análisis completo del predio (Módulos A+B+C)
  POST /api/chat             -> consulta libre al RAG normativo (Módulo A)
  POST /api/generar          -> genera el PMF y devuelve markdown + enlaces
  GET  /api/descargar/{fmt}  -> descarga el PMF (pdf|docx|md|html)
"""
from __future__ import annotations

import os
import json
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent_core import (
    analizar_predio, responder_consulta, responder_consulta_ia, generar_programa_ia,
)
from project_generator import (
    DatosPrograma, exportar_markdown, exportar_docx, exportar_pdf, exportar_html,
)
from legal_kb import NORMAS, TRAMITES, FORMATOS, PARAMETROS_TECNICOS, ESPECIES
import config as cfg
from gemini_client import get_gemini, GeminiError
from geo_anp import evaluar_ubicacion, ANP_CATALOGO

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(BASE, "web")
OUT_DIR = os.path.join(BASE, "output")
os.makedirs(OUT_DIR, exist_ok=True)

app = FastAPI(title="PalmillaBot — Agente RFNM (Yucca)", version="1.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


# ---------------------------------------------------------------------------
class PredioPayload(BaseModel):
    promovente: str = ""
    predio_nombre: str = ""
    municipio: str = "Ensenada"
    estado: str = "Baja California"
    superficie_ha: float = 100
    tipo_propietario: str = "privada"
    especie: str = "Yucca schidigera"
    parte_aprovechada: str = "tallo"
    fin: str = "comercial"
    en_anp: bool = False
    anp_nombre: str = ""
    especie_nom059: bool = False
    categoria_nom059: str = ""
    densidad_ind_ha: float = 320
    pct_maduros: float = 0.55
    peso_tallo_kg: float = 18
    vigencia_anios: int = 5
    tiene_tecnico: bool = False
    tiene_planos: bool = False
    # --- 1. Datos del titular ---
    titular_nombre: str = ""
    titular_curp: str = ""
    titular_estado_civil: str = ""
    # --- 2. Datos técnicos y de ubicación del terreno ---
    superficie_escrita: str = ""
    medidas: str = ""
    colindancias: str = ""
    coordenadas_geograficas: str = ""
    coordenadas_utm: str = ""
    localidad: str = ""
    ejido: str = ""
    sector: str = ""
    manzana: str = ""
    lote: str = ""
    # --- 3. Datos de identificación oficial y registro ---
    titulo_ref: str = ""
    registro_publico: str = ""
    clave_catastral: str = ""
    # --- 4. Datos legales y de autoridad ---
    fecha_expedicion: str = ""
    fundamento_legal_titulo: str = ""
    firmas_sellos: str = ""
    historial_origen: str = ""


class ChatPayload(BaseModel):
    pregunta: str
    usar_ia: bool = True


class ConfigPayload(BaseModel):
    api_key: Optional[str] = None
    modelo: Optional[str] = None


class ExportarPayload(BaseModel):
    markdown: str
    formato: str = "pdf"
    nombre: str = "PMF_generado_ia"


class UbicacionPayload(BaseModel):
    lat: Optional[float] = None
    lon: Optional[float] = None
    texto: Optional[str] = None
    texto_utm: Optional[str] = None


# ---------------------------------------------------------------------------
@app.get("/api/salud")
def salud():
    return {"ok": True, "servicio": "PalmillaBot", "version": "1.0"}


@app.get("/api/normas")
def normas():
    return {
        "normas": NORMAS,
        "tramites": TRAMITES,
        "formatos": FORMATOS,
        "parametros": PARAMETROS_TECNICOS,
        "especies": ESPECIES,
    }


@app.get("/api/anp")
def listar_anp():
    """Catálogo de ANP verificadas (para consulta y transparencia)."""
    return {"epsg": "EPSG:32611 (WGS 84 / UTM zone 11N)", "anp": ANP_CATALOGO}


@app.post("/api/ubicacion")
def ubicacion(p: UbicacionPayload):
    """Detecta si una ubicación cae dentro de una ANP (bloqueo por coordenadas)."""
    try:
        return evaluar_ubicacion(lat=p.lat, lon=p.lon, texto=p.texto, texto_utm=p.texto_utm)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analizar")
def analizar(p: PredioPayload):
    try:
        return analizar_predio(p.model_dump())
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat")
def chat(p: ChatPayload):
    if not p.pregunta.strip():
        raise HTTPException(status_code=400, detail="Pregunta vacía")
    if p.usar_ia:
        return responder_consulta_ia(p.pregunta)
    return responder_consulta(p.pregunta)


# ---------------------------------------------------------------------------
# Configuración de la API key de Gemini
@app.get("/api/config")
def get_config():
    return cfg.estado()


@app.post("/api/config")
def set_config(p: ConfigPayload):
    if p.api_key is not None:
        cfg.set_api_key(p.api_key)
        get_gemini().set_api_key(p.api_key)
    if p.modelo is not None:
        cfg.set_model(p.modelo)
        get_gemini().model = cfg.get_model()
    return cfg.estado()


@app.post("/api/config/validar")
def validar_config():
    gem = get_gemini()
    if not gem.is_configured():
        return {"ok": False, "mensaje": "No hay API key configurada."}
    try:
        modelos = gem.listar_modelos()
        return {"ok": True, "mensaje": "API key válida.", "modelos": modelos[:20]}
    except GeminiError as e:
        return {"ok": False, "mensaje": str(e)}


@app.post("/api/generar-ia")
def generar_ia(p: PredioPayload):
    try:
        return generar_programa_ia(p.model_dump())
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))


def _programa_desde_payload(p: PredioPayload) -> DatosPrograma:
    campos = set(DatosPrograma.__dataclass_fields__)
    d = p.model_dump()
    kwargs = {k: v for k, v in d.items() if k in campos and v not in (None, "")}
    return DatosPrograma(**kwargs)


@app.post("/api/generar")
def generar(p: PredioPayload):
    prog = _programa_desde_payload(p)
    try:
        md_path = exportar_markdown(prog, os.path.join(OUT_DIR, "PMF_generado.md"))
        html_path = exportar_html(prog, os.path.join(OUT_DIR, "PMF_generado.html"))
        pdf_path = exportar_pdf(prog, os.path.join(OUT_DIR, "PMF_generado.pdf"))
        docx_path = exportar_docx(prog, os.path.join(OUT_DIR, "PMF_generado.docx"))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))
    with open(md_path, encoding="utf-8") as fh:
        md = fh.read()
    return {
        "markdown": md,
        "descargas": {
            "pdf": "/api/descargar/pdf",
            "docx": "/api/descargar/docx",
            "md": "/api/descargar/md",
            "html": "/api/descargar/html",
        },
    }


@app.get("/api/descargar/{fmt}")
def descargar(fmt: str):
    fmt = fmt.lower()
    mapa = {
        "pdf": ("PMF_generado.pdf", "application/pdf"),
        "docx": ("PMF_generado.docx",
                 "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        "md": ("PMF_generado.md", "text/markdown"),
        "html": ("PMF_generado.html", "text/html"),
    }
    if fmt not in mapa:
        raise HTTPException(status_code=404, detail="Formato no soportado")
    nombre, media = mapa[fmt]
    path = os.path.join(OUT_DIR, nombre)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Genere primero el programa")
    return FileResponse(path, media_type=media, filename=nombre)


@app.post("/api/exportar")
def exportar(p: ExportarPayload):
    """Exporta un documento Markdown arbitrario (p. ej. generado por IA) a
    PDF/DOCX/HTML/MD y lo devuelve como archivo descargable."""
    from project_generator import (
        exportar_markdown_texto, exportar_html_texto,
        exportar_pdf_texto, exportar_docx_texto,
    )
    fmt = (p.formato or "").lower()
    nombre = os.path.basename(p.nombre or "PMF_generado_ia") or "PMF_generado_ia"
    base = os.path.join(OUT_DIR, nombre)
    try:
        if fmt == "md":
            path, media = exportar_markdown_texto(p.markdown, base + ".md"), "text/markdown"
        elif fmt == "html":
            path, media = exportar_html_texto(p.markdown, base + ".html"), "text/html"
        elif fmt == "pdf":
            path, media = exportar_pdf_texto(p.markdown, base + ".pdf"), "application/pdf"
        elif fmt == "docx":
            path, media = exportar_docx_texto(p.markdown, base + ".docx"), (
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        else:
            raise HTTPException(status_code=400, detail="Formato no soportado")
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e))
    return FileResponse(path, media_type=media, filename=os.path.basename(path))


# ---------------------------------------------------------------------------
# Frontend estático
@app.get("/", response_class=HTMLResponse)
def index():
    idx = os.path.join(WEB_DIR, "index.html")
    if os.path.exists(idx):
        with open(idx, encoding="utf-8") as fh:
            return HTMLResponse(fh.read())
    return HTMLResponse("<h1>PalmillaBot</h1><p>Frontend no encontrado.</p>")


if os.path.isdir(WEB_DIR):
    app.mount("/web", StaticFiles(directory=WEB_DIR), name="web")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
