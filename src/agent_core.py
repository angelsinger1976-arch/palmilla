# -*- coding: utf-8 -*-
"""
AGENTE CORE — Orquestador de los 3 módulos
==========================================
Une los tres módulos del sistema en una sola respuesta coherente de agente:

  Módulo A (rag_engine.LegalRAG)      -> contexto legal citado
  Módulo B (rules_engine.evaluar)     -> vía de trámite + checklist
  Módulo C (project_generator)        -> Programa de Manejo (6 secciones)

Expone:
  * `analizar_predio(datos)`  -> análisis completo (reglas + checklist + RAG + PMF)
  * `responder_consulta(q)`   -> respuesta a una pregunta libre, con citas (chat RAG)
  * `estructura_6_secciones(datos)` -> vista resumida en las 6 secciones pedidas
"""
from __future__ import annotations

import json
from typing import Dict, List, Optional

from rag_engine import get_rag
from rules_engine import PredioInput, evaluar
from project_generator import DatosPrograma, calcular, generar_markdown
from system_prompt import SYSTEM_PROMPT, build_runtime_prompt


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _datos_a_predio_input(d: Dict) -> PredioInput:
    return PredioInput(
        nombre_promovente=d.get("promovente", ""),
        tipo_propietario=d.get("tipo_propietario", "privada"),
        especie=d.get("especie", "Yucca schidigera"),
        parte_aprovechada=d.get("parte_aprovechada", "tallo"),
        superficie_ha=float(d.get("superficie_ha", 0) or 0),
        fin=d.get("fin", "comercial"),
        en_anp=bool(d.get("en_anp", False)),
        especie_nom059=bool(d.get("especie_nom059", False)),
        categoria_nom059=d.get("categoria_nom059", ""),
        municipio=d.get("municipio", ""),
        estado=d.get("estado", "Baja California"),
        tiene_tecnico=bool(d.get("tiene_tecnico", False)),
        tiene_planos=bool(d.get("tiene_planos", False)),
        # 1. Titular
        titular_nombre=d.get("titular_nombre", ""),
        titular_curp=d.get("titular_curp", ""),
        titular_estado_civil=d.get("titular_estado_civil", ""),
        # 2. Terreno / ubicación
        superficie_escrita=d.get("superficie_escrita", ""),
        medidas=d.get("medidas", ""),
        colindancias=d.get("colindancias", ""),
        coordenadas_geograficas=d.get("coordenadas_geograficas", ""),
        coordenadas_utm=d.get("coordenadas_utm", ""),
        localidad=d.get("localidad", ""),
        ejido=d.get("ejido", ""),
        sector=d.get("sector", ""),
        manzana=d.get("manzana", ""),
        lote=d.get("lote", ""),
        # 3. Registro
        titulo_ref=d.get("titulo_ref", ""),
        registro_publico=d.get("registro_publico", ""),
        clave_catastral=d.get("clave_catastral", ""),
        # 4. Legal / autoridad
        fecha_expedicion=d.get("fecha_expedicion", ""),
        fundamento_legal_titulo=d.get("fundamento_legal_titulo", ""),
        firmas_sellos=d.get("firmas_sellos", ""),
        historial_origen=d.get("historial_origen", ""),
    )


def _datos_a_programa(d: Dict) -> DatosPrograma:
    campos = {f for f in DatosPrograma.__dataclass_fields__}
    kwargs = {k: v for k, v in d.items() if k in campos and v not in (None, "")}
    return DatosPrograma(**kwargs)


def _checklist_a_texto(res) -> str:
    lineas = [f"Vía de trámite: {res.via_tramite} ({res.tramite_clave})"]
    for it in res.checklist:
        marca = "[x]" if it.estado == "listo" else "[ ]"
        lineas.append(f"{marca} {it.requisito} ({it.fundamento})")
    return "\n".join(lineas)


# ---------------------------------------------------------------------------
# Análisis completo del predio
# ---------------------------------------------------------------------------
def analizar_predio(datos: Dict) -> Dict:
    """Ejecuta los 3 módulos y devuelve una respuesta unificada del agente."""
    # --- Módulo B: reglas ---
    res = evaluar(_datos_a_predio_input(datos))

    # --- Módulo A: contexto legal (varias consultas temáticas) ---
    rag = get_rag()
    consultas = [
        "autorización aprovechamiento tallos Yucca recursos forestales no maderables",
        "contenido del programa de manejo forestal simplificado",
        "criterios técnicos cosecha madurez ciclo de corta Yucca",
    ]
    if res.requiere_pmf_simplificado:
        consultas.append("vigencia e informes del programa de manejo")
    if datos.get("en_anp"):
        consultas.append("aprovechamiento en área natural protegida")
    if datos.get("especie_nom059"):
        consultas.append("especies con estatus de riesgo NOM-059")

    vistos, citas = set(), []
    for q in consultas:
        for p in rag.search(q, top_k=3):
            if p.id not in vistos and p.score > 0.05:
                vistos.add(p.id)
                citas.append({"cita": p.cita, "texto": p.texto, "score": round(p.score, 3)})
    contexto_legal = "\n\n".join(f"[{c['cita']}] {c['texto']}" for c in citas)

    # --- Módulo C: programa de manejo ---
    prog = _datos_a_programa(datos)
    calculos = calcular(prog)
    markdown = generar_markdown(prog)

    # --- Prompt de ejecución (para LLM) ---
    runtime_prompt = build_runtime_prompt(
        datos, contexto_legal=contexto_legal, checklist=_checklist_a_texto(res)
    )

    return {
        "via_tramite": res.via_tramite,
        "tramite": {"clave": res.tramite_clave, "nombre": res.tramite_nombre,
                    "fundamento": res.fundamento_principal},
        "requiere_pmf_simplificado": res.requiere_pmf_simplificado,
        "vigencia_anios": res.vigencia_anios,
        "checklist": [it.__dict__ for it in res.checklist],
        "autorizaciones_adicionales": res.autorizaciones_adicionales,
        "reglas_tecnicas": res.reglas_tecnicas,
        "formularios": res.formularios,
        "advertencias": res.advertencias,
        "plazos": res.plazos,
        "citas_legales": citas,
        "calculos": calculos,
        "programa_markdown": markdown,
        "secciones": estructura_6_secciones(datos),
        "runtime_prompt": runtime_prompt,
        "system_prompt": SYSTEM_PROMPT,
    }


# ---------------------------------------------------------------------------
# Estructura de 6 secciones (vista resumida)
# ---------------------------------------------------------------------------
def estructura_6_secciones(datos: Dict) -> List[Dict]:
    prog = _datos_a_programa(datos)
    c = calcular(prog)
    titular = prog.titular_nombre or prog.promovente
    registro = ""
    if prog.titulo_ref:
        registro += f"; título {prog.titulo_ref}"
    if prog.registro_publico:
        registro += f"; registro {prog.registro_publico}"
    if prog.clave_catastral:
        registro += f"; clave catastral {prog.clave_catastral}"
    return [
        {"n": 1, "titulo": "Datos Generales",
         "fundamento": "Reglamento LGDFS Art. 57 fracc. I; NOM-005 §4.1.4",
         "resumen": f"Titular: {titular} — predio {prog.predio_nombre}, {prog.municipio}, "
                    f"{prog.estado}; {prog.superficie_ha:.0f} ha; régimen {prog.tipo_propietario}"
                    f"{registro}."},
        {"n": 2, "titulo": "Objetivo",
         "fundamento": "Reglamento LGDFS Art. 57 fracc. I inciso a",
         "resumen": f"Aprovechamiento sustentable de tallos de {prog.especie} "
                    f"({prog.nombre_comun}) en {prog.superficie_ha:.0f} ha."},
        {"n": 3, "titulo": "Caracterización del Medio",
         "fundamento": "NOM-005 §4.1.4 fracc. III inciso a",
         "resumen": f"{prog.clima}; suelo {prog.suelo}; {prog.vegetacion}."},
        {"n": 4, "titulo": "Inventario y Muestreo",
         "fundamento": "Reglamento LGDFS Art. 57 fracc. I incisos b y e; NOM-005 §4.1.4",
         "resumen": f"Densidad {prog.densidad_ind_ha:.0f} ind/ha; población {c['poblacion_total']:,}; "
                    f"maduros {c['ind_maduros']:,}; aprovechables {c['ind_aprovechables']:,}; "
                    f"biomasa {c['biomasa_total_t']:.2f} t."},
        {"n": 5, "titulo": "Sistema de Aprovechamiento y Tasa de Cosecha",
         "fundamento": "NOM-005 §4.1.10",
         "resumen": f"Tallo; madurez {c['madurez_defoliacion_pct']}% defoliación; tasa "
                    f"{c['tasa_cosecha_pct']}%; ciclo {c['ciclo_corta']} años; "
                    f"cosecha anual {c['cosecha_anual_t']:.2f} t."},
        {"n": 6, "titulo": "Medidas de Protección y Restauración Ambiental",
         "fundamento": "Reglamento LGDFS Art. 57 fracc. I incisos h-j; NOM-005 §4.1.4 III",
         "resumen": "Prevención de incendios, protección de fauna, especies NOM-059, "
                    "control de erosión y mitigación de impactos."},
    ]


# ---------------------------------------------------------------------------
# Chat RAG: responder una consulta libre con citas
# ---------------------------------------------------------------------------
def responder_consulta(pregunta: str, top_k: int = 4) -> Dict:
    rag = get_rag()
    pasajes = rag.search(pregunta, top_k=top_k)
    fuentes = [{"cita": p.cita, "texto": p.texto, "score": round(p.score, 3),
                "norma": p.norma} for p in pasajes]
    return {"pregunta": pregunta, "fuentes": fuentes,
            "contexto": "\n\n".join(f"[{f['cita']}] {f['texto']}" for f in fuentes)}


# ---------------------------------------------------------------------------
# Capa de IA generativa (Gemini) sobre el RAG — con respaldo offline
# ---------------------------------------------------------------------------
def _gemini_activo():
    from gemini_client import get_gemini, GeminiError  # import perezoso
    gem = get_gemini()
    return gem, GeminiError


def responder_consulta_ia(pregunta: str, top_k: int = 5) -> Dict:
    """Responde una consulta normativa usando Gemini + contexto RAG.

    Si no hay API key configurada, devuelve modo 'offline' con las fuentes
    recuperadas (comportamiento del Módulo A puro).
    """
    base = responder_consulta(pregunta, top_k=top_k)
    gem, GeminiError = _gemini_activo()

    if not gem.is_configured():
        return {**base, "modo": "offline", "respuesta": None,
                "aviso": "Sin API key de Gemini: se muestra solo el contexto legal recuperado (RAG). "
                         "Configure la API key en ⚙️ Configuración para respuestas redactadas por IA."}

    prompt = (
        "Con base EXCLUSIVAMENTE en el siguiente contexto legal recuperado, responde la "
        "consulta del usuario de forma clara, técnica y citando las disposiciones aplicables "
        "(formato: 'LGDFS Art. 85(b)', 'NOM-005 §4.1.10(IV)(d)'). Si el contexto no alcanza "
        "para responder, indícalo y pide los datos faltantes. No inventes normas ni cifras.\n\n"
        f"# CONSULTA\n{pregunta}\n\n"
        f"# CONTEXTO LEGAL\n{base['contexto']}\n"
    )
    try:
        texto = gem.generate(prompt, system_instruction=SYSTEM_PROMPT, temperature=0.2)
        return {**base, "modo": "gemini", "respuesta": texto}
    except GeminiError as e:
        return {**base, "modo": "error", "respuesta": None, "error": str(e)}


def generar_programa_ia(datos: Dict) -> Dict:
    """Genera el Programa de Manejo con Gemini (enriquecido con el RAG).

    Siempre incluye el documento base determinista (plantilla) como respaldo;
    si hay API key, Gemini redacta la versión narrativa completa.
    """
    from project_generator import generar_markdown
    prog = _datos_a_programa(datos)
    base_md = generar_markdown(prog)

    gem, GeminiError = _gemini_activo()
    if not gem.is_configured():
        return {"modo": "offline", "markdown": base_md, "base_markdown": base_md,
                "aviso": "Sin API key de Gemini: se generó el documento con la plantilla determinista."}

    analisis = analizar_predio(datos)
    contexto_legal = "\n\n".join(f"[{c['cita']}] {c['texto']}" for c in analisis["citas_legales"])
    runtime = build_runtime_prompt(
        datos, contexto_legal=contexto_legal, checklist=_checklist_a_texto(
            evaluar(_datos_a_predio_input(datos)))
    )
    prompt = (
        f"{runtime}\n\n"
        "# INSTRUCCIONES DE REDACCIÓN\n"
        "Redacta el Programa de Manejo Forestal Simplificado COMPLETO en Markdown, con la "
        "estructura de 6 secciones indicada. Fundamenta cada sección con la disposición legal "
        "correspondiente. Usa los siguientes datos y cálculos verificados (no los alteres):\n\n"
        f"# CÁLCULOS VERIFICADOS\n```json\n{json.dumps(analisis['calculos'], ensure_ascii=False, indent=2)}\n```\n\n"
        f"# DOCUMENTO BASE (plantilla; mejóralo y complétalo)\n{base_md}\n"
    )
    try:
        texto = gem.generate(prompt, system_instruction=SYSTEM_PROMPT, temperature=0.4, max_tokens=8192)
        return {"modo": "gemini", "markdown": texto, "base_markdown": base_md}
    except GeminiError as e:
        return {"modo": "error", "markdown": base_md, "base_markdown": base_md, "error": str(e)}


if __name__ == "__main__":
    demo = {
        "promovente": "Ejido Sierra de Juárez",
        "predio_nombre": "Predio El Cardonal",
        "municipio": "Ensenada",
        "superficie_ha": 180,
        "tipo_propietario": "ejidal",
        "especie": "Yucca schidigera",
        "densidad_ind_ha": 320,
        "pct_maduros": 0.55,
        "peso_tallo_kg": 18,
    }
    import json
    out = analizar_predio(demo)
    print("VÍA:", out["via_tramite"], "|", out["tramite"]["clave"])
    print("CHECKLIST:", len(out["checklist"]), "items")
    print("CITAS:", len(out["citas_legales"]))
    print("SECCIONES:", len(out["secciones"]))
    print("\n--- Chat RAG ---")
    r = responder_consulta("¿Se necesita aviso o autorización para tallos de Yucca?")
    for f in r["fuentes"][:2]:
        print(" ->", f["cita"], round(f["score"], 3))
