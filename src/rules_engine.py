# -*- coding: utf-8 -*-
"""
MÓDULO B — Motor de Reglas (Checklist de Permisos)
==================================================
Recibe los inputs del predio y determina, con base en las disposiciones
verificadas (LGDFS Arts. 84-85, Reglamento Arts. 55-61, NOM-005 §4.1.x):

  * Vía de trámite: AVISO vs AUTORIZACIÓN
  * Fundamento legal aplicable
  * Documentos y formularios requeridos (checklist)
  * Autorizaciones adicionales (NOM-059, ANP)
  * Plazos, vigencia y reglas técnicas de cosecha
  * Advertencias y requisitos faltantes
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import List, Dict

from legal_kb import ESPECIES, PARAMETROS_TECNICOS, TRAMITES, FORMATOS


# ---------------------------------------------------------------------------
# Esquema de entrada
# ---------------------------------------------------------------------------
@dataclass
class PredioInput:
    nombre_promovente: str = ""
    tipo_propietario: str = "privada"          # privada | ejidal | comunal | posesion
    especie: str = "Yucca schidigera"
    parte_aprovechada: str = "tallo"           # tallo | hojas | planta_completa
    superficie_ha: float = 0.0
    fin: str = "comercial"                     # comercial | domestico | investigacion
    en_anp: bool = False
    especie_nom059: bool = False
    categoria_nom059: str = ""                 # E | A | Pr | P
    municipio: str = ""
    estado: str = "Baja California"
    tiene_tecnico: bool = False
    tiene_planos: bool = False

    # --- 1. Datos del titular (propietario o poseedor) ---
    titular_nombre: str = ""
    titular_curp: str = ""                     # identificación oficial o CURP
    titular_estado_civil: str = ""

    # --- 2. Datos técnicos y de ubicación del terreno ---
    superficie_escrita: str = ""               # p. ej. "1-00-00 ha (10,000 m²)"
    medidas: str = ""                          # medidas de cada lado
    colindancias: str = ""                     # con qué/quien limita
    coordenadas_geograficas: str = ""          # lat/lon (GPS)
    coordenadas_utm: str = ""                  # UTM
    localidad: str = ""
    ejido: str = ""
    sector: str = ""
    manzana: str = ""
    lote: str = ""

    # --- 3. Datos de identificación oficial y registro ---
    titulo_ref: str = ""                       # número de título o certificado
    registro_publico: str = ""                 # tomo/volumen/folio/libro (RPP o RAN)
    clave_catastral: str = ""

    # --- 4. Datos legales y de autoridad ---
    fecha_expedicion: str = ""                 # fecha de expedición del título
    fundamento_legal_titulo: str = ""          # artículos que validan el título
    firmas_sellos: str = ""                    # firmas/sellos de autoridad
    historial_origen: str = ""                 # herencia, compraventa, etc.


# ---------------------------------------------------------------------------
@dataclass
class ItemChecklist:
    requisito: str
    fundamento: str
    obligatorio: bool = True
    estado: str = "pendiente"   # pendiente | listo | no_aplica
    nota: str = ""


@dataclass
class ResultadoReglas:
    via_tramite: str
    tramite_clave: str
    tramite_nombre: str
    fundamento_principal: str
    requiere_pmf_simplificado: bool
    vigencia_anios: int
    checklist: List[ItemChecklist] = field(default_factory=list)
    autorizaciones_adicionales: List[str] = field(default_factory=list)
    reglas_tecnicas: List[str] = field(default_factory=list)
    formularios: List[Dict] = field(default_factory=list)
    advertencias: List[str] = field(default_factory=list)
    plazos: List[str] = field(default_factory=list)

    def to_dict(self):
        d = asdict(self)
        return d


# ---------------------------------------------------------------------------
# Motor
# ---------------------------------------------------------------------------
def evaluar(inp: PredioInput) -> ResultadoReglas:
    P = PARAMETROS_TECNICOS
    checklist: List[ItemChecklist] = []
    adicionales: List[str] = []
    reglas: List[str] = []
    advertencias: List[str] = []
    plazos: List[str] = []

    # ---- 1. Determinar la vía de trámite (LGDFS Art. 84 vs 85) ----
    es_yucca = inp.especie.lower().startswith("yucca")
    es_tallo_yucca = es_yucca and inp.parte_aprovechada in ("tallo",)
    es_planta_completa_fam = inp.parte_aprovechada == "planta_completa"  # Agavaceae/Cactaceae/Nolinaceae etc.
    es_tierra = inp.parte_aprovechada in ("tierra_de_monte", "tierra_de_hoja")

    if es_tallo_yucca or es_planta_completa_fam or es_tierra:
        via = "AUTORIZACIÓN"
        tramite = next(t for t in TRAMITES if t["clave"] == "SEMARNAT-03-052")
        fundamento = ("LGDFS Art. 85 inciso b) (tallos de Yucca) y Art. 68 fracc. IV; "
                      "Reglamento LGDFS Arts. 55 fracc. II y 56; NOM-005-SEMARNAT-1997 §4.1.4.")
        requiere_pmf = True
    else:
        via = "AVISO"
        tramite = next(t for t in TRAMITES if t["clave"] == "SEMARNAT-03-005")
        fundamento = ("LGDFS Art. 84 y Art. 69 fracc. III; Reglamento LGDFS Art. 53.")
        requiere_pmf = False

    # ---- 2. Checklist documental (Reglamento Art. 56 / NOM-005 §4.1.4) ----
    checklist.append(ItemChecklist(
        "Formato de solicitud FF-SEMARNAT-074 firmado por el propietario o representante legal",
        "Reglamento LGDFS Art. 56; NOM-005 §4.1.4",
        estado="pendiente",
    ))
    checklist.append(ItemChecklist(
        "Título de propiedad o posesión (original o copia certificada, inscrito en el Registro Público)",
        "Reglamento LGDFS Art. 56 fracc. I; NOM-005 §4.1.4 fracc. II",
    ))
    checklist.append(ItemChecklist(
        "Instrumento que acredite el derecho a realizar el aprovechamiento (vigencia ≥ a la del PMF)",
        "Reglamento LGDFS Art. 56 fracc. II",
    ))
    if inp.tipo_propietario in ("ejidal", "comunal"):
        checklist.append(ItemChecklist(
            "Acta de asamblea (ejidal/comunal) con el consentimiento para el aprovechamiento, "
            "inscrita o en trámite en el Registro Agrario Nacional",
            "Reglamento LGDFS Art. 56 fracc. III",
        ))
    else:
        checklist.append(ItemChecklist(
            "Acta de asamblea (aplica a ejidos/comunidades) — NO APLICA a propiedad privada",
            "Reglamento LGDFS Art. 56 fracc. III",
            obligatorio=False, estado="no_aplica",
        ))
    checklist.append(ItemChecklist(
        "Manifestación por escrito, bajo protesta de decir verdad, de la situación legal del predio "
        "y ausencia de conflictos de propiedad pendientes",
        "Reglamento LGDFS Art. 56 fracc. IV",
    ))
    checklist.append(ItemChecklist(
        "Plano georreferenciado (Shapefile/GeoPDF) del polígono con las áreas de aprovechamiento",
        "Reglamento LGDFS Art. 56 fracc. V",
        estado="listo" if inp.tiene_planos else "pendiente",
    ))
    if requiere_pmf:
        checklist.append(ItemChecklist(
            "Programa de Manejo Forestal Simplificado (PMF) — ver Módulo C",
            "Reglamento LGDFS Art. 56 fracc. VI y Art. 57; NOM-005 §4.1.4 fracc. III",
        ))
    checklist.append(ItemChecklist(
        "Datos de inscripción en el Registro Forestal Nacional del prestador de servicios técnicos "
        "forestales (Técnico Forestal Certificado) responsable de elaborar el estudio y dirigir la ejecución",
        "Reglamento LGDFS Art. 57 fracc. I inciso k; NOM-005 §4.1.5",
        estado="listo" if inp.tiene_tecnico else "pendiente",
    ))

    # ---- 3. Autorizaciones adicionales ----
    if inp.especie_nom059:
        adicionales.append(
            f"La especie está en NOM-059 ({inp.categoria_nom059 or 'categoría por confirmar'}): se requiere "
            "autorización adicional de la autoridad ecológica (hoy SEMARNAT/DGVS) conforme a la LGEEPA, "
            "anexa a la solicitud. NOM-005 §4.1.13; NOM-059-SEMARNAT-2010."
        )
        if inp.categoria_nom059 == "E":
            advertencias.append(
                "Especie EN PELIGRO DE EXTINCIÓN (E): NO se permite aprovechamiento extractivo salvo "
                "autorización especial. Revisar viabilidad del proyecto."
            )
    if inp.en_anp:
        adicionales.append(
            "El predio se ubica en un Área Natural Protegida: se requiere autorización previa de la "
            "autoridad ecológica conforme a la LGEEPA. NOM-005 §4.1.14. En B.C. verificar si aplica "
            "(p. ej., Valle de los Cirios, Sierra de San Pedro Mártir, etc.)."
        )
    if inp.fin == "investigacion":
        adicionales.append(
            "Fines de investigación/biotecnología: se requiere autorización de colecta y uso de recursos "
            "biológicos forestales con consentimiento previo, expreso e informado del poseedor. "
            "LGDFS Art. 86."
        )

    # ---- 4. Reglas técnicas de cosecha (NOM-005 §4.1.10 IV d) ----
    if es_yucca:
        reglas += [
            f"Madurez de cosecha: colonias con individuos desprovistos de hojas verdes en ≥ "
            f"{int(P['madurez_cosecha_defoliacion']*100)}% de su longitud (NOM-005 §4.1.10 IV d).",
            f"Tasa de cosecha máxima: {int(P['tasa_cosecha_max']*100)}% de los individuos maduros, "
            "evitando dañar brotes e individuos jóvenes (NOM-005 §4.1.10 IV d).",
            f"Ciclo de corta: no menor a {P['ciclo_corta_anios']} años en áreas no intervenidas "
            "(NOM-005 §4.1.10 IV d).",
            "Unidad de medida de la autorización para Yucca: TONELADAS (NOM-005 §4.1.8).",
        ]
        if inp.superficie_ha and inp.superficie_ha < P["umbral_predio_pequeno_ha"]:
            reglas.append(
                f"Predio < {P['umbral_predio_pequeno_ha']} ha: se puede proponer el aprovechamiento del "
                "50% de la población aprovechable en una o dos anualidades, sin otra intervención por un "
                "ciclo de corta (NOM-005 §4.1.10 IV d)."
            )
        reglas.append(
            "El PMF de Yucca debe incluir, además de lo general, la descripción de los accesos al área "
            "de aprovechamiento y el estudio dasométrico (Reglamento Art. 57 fracc. III)."
        )

    # ---- 5. Plazos y vigencia ----
    plazos += [
        "Vigencia máxima del PMF y de la autorización: 5 años (Reglamento Art. 59).",
        "SEMARNAT puede prevenir por información faltante dentro de 15 días hábiles (a desahogar en 15 días).",
        "Resolución dentro de 15 días hábiles tras concluir plazos; en caso de no emitirse, se entiende "
        "POSITIVA (silencio administrativo positivo). Reglamento Art. 60.",
        "Informes trimestrales de aprovechamiento (abril, julio, octubre y enero) avalados por el "
        "responsable técnico. NOM-005 §4.1.9.",
    ]

    # ---- 6. Advertencias generales ----
    advertencias.append(
        "El aprovechamiento de tallos de Yucca NO se realiza por 'aviso': requiere autorización expresa "
        "de SEMARNAT (LGDFS Art. 85 b)."
    )
    if not inp.tiene_tecnico:
        advertencias.append(
            "Debe contratarse un Técnico Forestal Certificado inscrito en el Registro Forestal Nacional "
            "para elaborar el estudio y dirigir el aprovechamiento."
        )
    if not inp.tiene_planos:
        advertencias.append(
            "Se requiere plano georreferenciado (Shapefile/GeoPDF) del polígono."
        )
    advertencias.append(
        "Verificar el Anexo Normativo III vigente de la NOM-059 para la especie exacta del predio; "
        "la lista se actualiza periódicamente."
    )

    # ---- 7. Formularios ----
    formularios = list(FORMATOS) if requiere_pmf else []

    return ResultadoReglas(
        via_tramite=via,
        tramite_clave=tramite["clave"],
        tramite_nombre=tramite["nombre"],
        fundamento_principal=fundamento,
        requiere_pmf_simplificado=requiere_pmf,
        vigencia_anios=P["vigencia_max_anios"],
        checklist=checklist,
        autorizaciones_adicionales=adicionales,
        reglas_tecnicas=reglas,
        formularios=formularios,
        advertencias=advertencias,
        plazos=plazos,
    )


if __name__ == "__main__":
    import json
    demo = PredioInput(
        nombre_promovente="Ejido Sierra de Juárez",
        tipo_propietario="ejidal",
        especie="Yucca schidigera",
        parte_aprovechada="tallo",
        superficie_ha=180,
        fin="comercial",
        en_anp=False,
        especie_nom059=False,
        municipio="Ensenada",
        estado="Baja California",
        tiene_tecnico=False,
        tiene_planos=False,
    )
    r = evaluar(demo)
    print(json.dumps(r.to_dict(), ensure_ascii=False, indent=2))
