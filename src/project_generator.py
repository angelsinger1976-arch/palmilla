# -*- coding: utf-8 -*-
"""
MÓDULO C — Generador del Programa de Manejo Forestal Simplificado
=================================================================
Ensambla el documento técnico que exige SEMARNAT para el aprovechamiento de
recursos forestales no maderables (tallos de Yucca / palmilla), conforme a:

  * Reglamento LGDFS Art. 57 (contenido obligatorio)
  * NOM-005-SEMARNAT-1997 §4.1.4 (estudio técnico justificativo de Yucca)
  * NOM-005-SEMARNAT-1997 §4.1.10 (criterios técnicos de cosecha)
  * LGDFS Arts. 84-85

Genera Markdown listo para exportar a DOCX/PDF, con citas legales en cada
sección y cálculos de inventario/tasa de cosecha derivados de los inputs.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field, asdict
from typing import Dict, List

from legal_kb import PARAMETROS_TECNICOS


# ---------------------------------------------------------------------------
# Entrada de datos del programa
# ---------------------------------------------------------------------------
@dataclass
class DatosPrograma:
    # --- Promovente ---
    promovente: str = "Promovente por definir"
    rfc: str = ""
    domicilio: str = ""
    representante: str = ""
    tecnico: str = "Ing. Forestal (Técnico Certificado por definir)"
    registro_tecnico: str = "RFN-____"

    # --- Predio ---
    predio_nombre: str = "Predio por definir"
    municipio: str = "Ensenada"
    estado: str = "Baja California"
    superficie_ha: float = 100.0
    coordenadas_utm: str = "Zona 11N, X=____, Y=____"
    poligono_ref: str = "poligono_predio.shp"
    tipo_propietario: str = "privada"
    titulo_ref: str = "Escritura Pública No. ____"
    colindancias: str = "Norte: ____; Sur: ____; Oriente: ____; Poniente: ____"

    # --- Especie ---
    especie: str = "Yucca schidigera"
    nombre_comun: str = "palmilla / yuca"
    parte_aprovechada: str = "tallo"

    # --- Inventario ---
    densidad_ind_ha: float = 320.0
    pct_maduros: float = 0.55
    peso_tallo_kg: float = 18.0
    metodo_muestreo: str = "Sistemático (distribución uniforme)"
    tam_sitio_m2: int = 1000
    intensidad_pct: float = 3.0
    sitios_num: int = 30

    # --- Medio físico ---
    clima: str = "Muy árido, semicálido (BWk/BWh)"
    temperatura_media: str = "18–22 °C"
    precipitacion: str = "150–250 mm/año"
    suelo: str = "Regosol / Xerosol, somero, pedregoso"
    vegetacion: str = "Matorral desértico micrófilo y rosetófilo"
    vegetacion_asociada: str = ("Ambrosia, Larrea tridentata (gobernadora), Fouquieria, "
                                "Agave, Opuntia, Prosopis (mezquite), Jatropha")

    # --- Objetivos ---
    justificacion: str = ""

    # --- ANP / NOM-059 ---
    en_anp: bool = False
    anp_nombre: str = ""
    especie_nom059: bool = False
    categoria_nom059: str = ""

    # --- Vigencia ---
    vigencia_anios: int = 5


# ---------------------------------------------------------------------------
# Cálculos de inventario y cosecha
# ---------------------------------------------------------------------------
def calcular(d: DatosPrograma) -> Dict:
    P = PARAMETROS_TECNICOS
    poblacion_total = d.superficie_ha * d.densidad_ind_ha
    ind_maduros = poblacion_total * d.pct_maduros
    ind_aprovechables = ind_maduros * P["tasa_cosecha_max"]          # 50%
    biomasa_total_t = ind_aprovechables * d.peso_tallo_kg / 1000.0   # toneladas
    ciclo = P["ciclo_corta_anios"]
    # Predio pequeño (<250 ha): se puede cosechar en 1-2 anualidades
    if d.superficie_ha < P["umbral_predio_pequeno_ha"]:
        anualidades = 2
        cosecha_anual_t = biomasa_total_t / anualidades
    else:
        anualidades = ciclo
        cosecha_anual_t = biomasa_total_t / ciclo
    return {
        "poblacion_total": round(poblacion_total),
        "ind_maduros": round(ind_maduros),
        "ind_aprovechables": round(ind_aprovechables),
        "biomasa_total_t": round(biomasa_total_t, 2),
        "ciclo_corta": ciclo,
        "anualidades": anualidades,
        "cosecha_anual_t": round(cosecha_anual_t, 2),
        "tasa_cosecha_pct": int(P["tasa_cosecha_max"] * 100),
        "madurez_defoliacion_pct": int(P["madurez_cosecha_defoliacion"] * 100),
    }


# ---------------------------------------------------------------------------
# Generación del documento (Markdown)
# ---------------------------------------------------------------------------
def generar_markdown(d: DatosPrograma) -> str:
    c = calcular(d)
    just = d.justificacion or (
        f"El aprovechamiento de los tallos de {d.especie} ({d.nombre_comun}) constituye una alternativa "
        "productiva para el aprovechamiento sustentable de los recursos forestales no maderables (RFNM) "
        "del matorral desértico, generando ingresos complementarios para los poseedores del predio, "
        "conforme a los criterios de la NOM-005-SEMARNAT-1997 y del Reglamento de la LGDFS."
    )

    anp_txt = ""
    if d.en_anp:
        anp_txt = (f"\n> **Nota (ANP):** El predio se ubica dentro del Área Natural Protegida "
                   f"**{d.anp_nombre or 'por definir'}**, por lo que se requiere autorización previa de la "
                   "autoridad ecológica conforme a la LGEEPA (NOM-005 §4.1.14).\n")
    nom059_txt = ""
    if d.especie_nom059:
        nom059_txt = (f"\n> **Nota (NOM-059):** La especie se encuentra en la categoría "
                      f"**{d.categoria_nom059 or 'por confirmar'}** de la NOM-059-SEMARNAT-2010; se requiere "
                      "autorización adicional (NOM-005 §4.1.13).\n")

    md = f"""# PROGRAMA DE MANEJO FORESTAL SIMPLIFICADO
## Aprovechamiento de Recursos Forestales No Maderables — Tallos de *{d.especie}* ({d.nombre_comun})

**Predio:** {d.predio_nombre}
**Municipio:** {d.municipio} · **Estado:** {d.estado}
**Superficie:** {d.superficie_ha:.2f} ha
**Vigencia propuesta:** {d.vigencia_anios} años

---

> **Fundamento legal del trámite.** El aprovechamiento de los **tallos de las especies del género *Yucca***
> requiere **autorización** de la SEMARNAT (no sólo aviso), conforme al **artículo 85, inciso b) de la Ley
> General de Desarrollo Forestal Sustentable (LGDFS)** y a los **artículos 55 y 56 de su Reglamento**, así
> como a la **NOM-005-SEMARNAT-1997, numeral 4.1.4**. El presente documento se elabora conforme al
> **artículo 57 del Reglamento de la LGDFS** (contenido del Programa de Manejo Forestal Simplificado) y a
> la **NOM-005-SEMARNAT-1997**.
{anp_txt}{nom059_txt}
---

## 1. DATOS GENERALES DEL PROMOVENTE Y DEL PREDIO
*(Reglamento LGDFS Art. 57 fracc. I; NOM-005 §4.1.4 fracc. I y II)*

**1.1 Promovente**
- Nombre / razón social: **{d.promovente}**
- RFC: {d.rfc or '____'}
- Domicilio: {d.domicilio or '____'}
- Representante legal: {d.representante or '____'}
- Responsable técnico: **{d.tecnico}** (Registro Forestal Nacional: {d.registro_tecnico})

**1.2 Predio**
- Nombre del predio: **{d.predio_nombre}**
- Ubicación: {d.municipio}, {d.estado}
- Superficie total: **{d.superficie_ha:.2f} ha**
- Régimen de propiedad: **{d.tipo_propietario}** — {d.titulo_ref}
- Colindancias: {d.colindancias}
- Coordenadas UTM: {d.coordenadas_utm}
- Polígono georreferenciado: `{d.poligono_ref}` (Shapefile/GeoPDF, Reglamento Art. 56 fracc. V)

## 2. OBJETIVO DEL APROVECHAMIENTO
*(Reglamento Art. 57 fracc. I inciso a)*

**2.1 Objetivo general.** Solicitar autorización para el aprovechamiento sustentable de tallos de
*{d.especie}* en una superficie de {d.superficie_ha:.2f} ha, bajo un esquema de manejo que garantice la
persistencia del recurso conforme a la NOM-005-SEMARNAT-1997.

**2.2 Justificación técnica y económica.** {just}

## 3. CARACTERIZACIÓN DEL MEDIO FÍSICO Y BIOLÓGICO
*(Reglamento Art. 57 fracc. I inciso a; NOM-005 §4.1.4 fracc. III inciso a)*

| Variable | Descripción |
|---|---|
| Clima | {d.clima} |
| Temperatura media | {d.temperatura_media} |
| Precipitación | {d.precipitacion} |
| Tipo de suelo | {d.suelo} |
| Vegetación | {d.vegetacion} |
| Vegetación asociada | {d.vegetacion_asociada} |

El área corresponde a ecosistemas semiáridos/áridos del norte de México, caracterizados por su
vulnerabilidad a la desertificación y por albergar poblaciones rurales que aprovechan RFNM
(Villavicencio-Gutiérrez et al., 2021; Rev. Mex. Cienc. For. 12(spe1)).

## 4. INVENTARIO Y MUESTREO DE LA PALMILLA
*(Reglamento Art. 57 fracc. I incisos b y e; NOM-005 §4.1.4 fracc. III inciso c)*

**4.1 Metodología de muestreo.** Se aplicó un muestreo **{d.metodo_muestreo}**, con
**{d.sitios_num} sitios** de **{d.tam_sitio_m2} m²** e intensidad de muestreo del **{d.intensidad_pct}%**.
Para especies de distribución uniforme como *Yucca carnerosana* se recomienda el muestreo sistemático
(INIFAP, 2021).

**4.2 Estimación de existencias.**

| Parámetro | Valor |
|---|---|
| Densidad promedio | {d.densidad_ind_ha:.0f} ind/ha |
| Población total estimada | **{c['poblacion_total']:,} individuos** |
| Proporción de individuos maduros | {int(d.pct_maduros*100)} % |
| Individuos maduros | **{c['ind_maduros']:,}** |
| Individuos aprovechables (50 % de maduros) | **{c['ind_aprovechables']:,}** |
| Peso promedio de tallo | {d.peso_tallo_kg:.1f} kg |
| Biomasa aprovechable total | **{c['biomasa_total_t']:.2f} t** |

**4.3 Tasa de regeneración.** El aprovechamiento se sujeta al ciclo de corta de **{c['ciclo_corta']} años**
(NOM-005 §4.1.10 IV d), por lo que la cosecha anual ({c['cosecha_anual_t']:.2f} t) es **menor a la tasa de
regeneración** del recurso (Reglamento Art. 57 fracc. I inciso d).

## 5. ESTUDIO DASOMÉTRICO Y ACCESOS
*(Reglamento Art. 57 fracc. III — específico para Yucca)*

**5.1 Estudio dasométrico.** Se registraron las variables dasométricas de la población: altura total (AT),
diámetro basal del tallo (DB), diámetro promedio de cobertura (DPC) y número de tallos por individuo,
a fin de estimar existencias y madurez de cosecha.

**5.2 Descripción de accesos.** Se describen los caminos y brechas de acceso al área de aprovechamiento,
así como la infraestructura caminera para el abastecimiento (NOM-005 §4.1.4 fracc. III inciso h).

## 6. SISTEMA DE APROVECHAMIENTO Y TASA DE COSECHA
*(Reglamento Art. 57 fracc. I incisos c, d, f, g; NOM-005 §4.1.10)*

- **Parte aprovechada:** {d.parte_aprovechada} (tallo).
- **Madurez de cosecha:** colonias con individuos desprovistos de hojas verdes en ≥ **{c['madurez_defoliacion_pct']}%**
  de su longitud (NOM-005 §4.1.10 IV d).
- **Tasa de cosecha:** **{c['tasa_cosecha_pct']}%** de los individuos maduros, evitando dañar brotes e
  individuos jóvenes (NOM-005 §4.1.10 IV d).
- **Ciclo de corta:** **{c['ciclo_corta']} años** en áreas no intervenidas (NOM-005 §4.1.10 IV d).
- **Anualidades propuestas:** **{c['anualidades']}** {'(predio < 250 ha)' if d.superficie_ha < 250 else ''}.
- **Volumen anual solicitado:** **{c['cosecha_anual_t']:.2f} toneladas/año** (unidad para Yucca: toneladas,
  NOM-005 §4.1.8).
- **Técnica de corte:** corte de tallos maduros a la base, sin afectar la zona de crecimiento apical ni
  los brotes; extracción manual/mecanizada ligera.
- **Periodo de recuperación:** las áreas intervenidas quedan excluidas de nuevo aprovechamiento por un
  periodo equivalente a un ciclo de corta (NOM-005 §4.1.10 IV d).

## 7. MEDIDAS DE PROTECCIÓN Y RESTAURACIÓN AMBIENTAL
*(Reglamento Art. 57 fracc. I incisos h, i, j; NOM-005 §4.1.4 fracc. III incisos d-g)*

**7.1 Prevención y control de incendios.** {d.vegetacion} — se establecen brechas cortafuego, vigilancia en
época de estiaje y un programa de prevención (NOM-005 §4.1.4 III f).

**7.2 Protección de la fauna silvestre.** Se respetan madrigueras, nidos y corredores biológicos
(NOM-005 §4.1.4 III d).

**7.3 Especies con estatus (NOM-059).** Se identifican y protegen las especies listadas en la
NOM-059-SEMARNAT-2010 presentes en el predio (NOM-005 §4.1.4 III e).

**7.4 Control de erosión y restauración.** Se evita la remoción de suelo; se realizan labores de fomento y
prácticas culturales para la preservación del recurso, incluyendo reforestación/restauración de zonas
degradadas (NOM-005 §4.1.4 III i).

**7.5 Mitigación de impactos.** Se describen y programan las medidas de prevención y mitigación de impactos
ambientales negativos en las distintas etapas (NOM-005 §4.1.4 III g; Reglamento Art. 57 I j).

## 8. ANÁLISIS DE APROVECHAMIENTOS ANTERIORES
*(Reglamento Art. 57 fracc. I inciso b)*

{d.predio_nombre} {'no registra' if True else ''} aprovechamientos previos documentados de RFNM; se
analiza la respuesta del recurso a tratamientos previos con datos comparativos de existencias reales.

## 9. VIGENCIA Y SEGUIMIENTO
*(Reglamento Arts. 59-61; NOM-005 §4.1.9)*

- **Vigencia solicitada:** {d.vigencia_anios} años (máximo legal: 5 años, Reglamento Art. 59).
- **Informes:** trimestrales (abril, julio, octubre, enero) y uno final, avalados por el responsable
  técnico (NOM-005 §4.1.9).
- **Resolución:** la SEMARNAT resuelve en 15 días hábiles; de no emitirse, se entiende en sentido
  **positivo** (silencio administrativo positivo, Reglamento Art. 60).

## 10. ANEXOS
1. Formato **FF-SEMARNAT-074** (solicitud SEMARNAT-03-052).
2. Título de propiedad / documento de posesión.
3. Acta de asamblea (ejidos/comunidades).
4. Plano georreferenciado (Shapefile/GeoPDF).
5. Estudio dasométrico (tablas de campo).
6. Manifestación de situación legal del predio.
7. Constancia de inscripción del prestador de servicios técnicos forestales.

---
### Referencias normativas
- Ley General de Desarrollo Forestal Sustentable (LGDFS), Arts. 68, 69, 84, 85, 86, 88, 90, 91.
- Reglamento de la LGDFS, Arts. 53-61.
- NOM-005-SEMARNAT-1997, §4.1.1, §4.1.4, §4.1.8, §4.1.9, §4.1.10, §4.1.13, §4.1.14.
- NOM-059-SEMARNAT-2010 (Anexo Normativo III).
- NOM-152-SEMARNAT-2023 (estructura de PMF; referencia).
- Villavicencio-Gutiérrez et al. (2021). Manejo forestal sustentable de los RFNM en el semidesierto del
  norte de México. Rev. Mex. Cienc. For. 12(spe1). https://doi.org/10.29298/rmcf.v12iespecial-1.1083

*Documento generado automáticamente por el Sistema de Agente IA para Aprovechamiento de Palmilla (Yucca).*
"""
    return md


# ---------------------------------------------------------------------------
# Exportadores
# ---------------------------------------------------------------------------
def exportar_markdown(d: DatosPrograma, path: str) -> str:
    md = generar_markdown(d)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(md)
    return path


# ---------------------------------------------------------------------------
# Exportadores genéricos a partir de un texto Markdown (para docs generados por IA)
# ---------------------------------------------------------------------------
def md_a_html(md_text: str) -> str:
    import markdown as _md
    body = _md.markdown(md_text, extensions=["tables", "sane_lists", "nl2br"])
    return _HTML_TEMPLATE.format(body=body)


def exportar_markdown_texto(md_text: str, path: str) -> str:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(md_text)
    return path


def exportar_html_texto(md_text: str, path: str) -> str:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(md_a_html(md_text))
    return path


def exportar_pdf_texto(md_text: str, path: str) -> str:
    import subprocess
    import tempfile
    html = md_a_html(md_text)
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as fh:
        fh.write(html)
        html_path = fh.name
    try:
        subprocess.run(
            ["wkhtmltopdf", "--enable-local-file-access", "--quiet",
             "--encoding", "utf-8", "-s", "Letter",
             "--margin-top", "18mm", "--margin-bottom", "20mm",
             "--margin-left", "18mm", "--margin-right", "18mm",
             "--footer-center", "Programa de Manejo Forestal Simplificado — Palmilla (Yucca) — página [page] de [topage]",
             "--footer-font-size", "7", "--footer-spacing", "6",
             html_path, path],
            check=True, capture_output=True,
        )
    finally:
        os.unlink(html_path)
    return path


def exportar_docx_texto(md_text: str, path: str) -> str:
    from docx import Document
    doc = Document()
    for line in md_text.split("\n"):
        if line.startswith("# "):
            doc.add_heading(line[2:], level=1)
        elif line.startswith("## "):
            doc.add_heading(line[3:], level=2)
        elif line.startswith("### "):
            doc.add_heading(line[4:], level=3)
        elif line.strip().startswith("|"):
            doc.add_paragraph(line)
        elif line.strip().startswith("---"):
            continue
        else:
            doc.add_paragraph(line)
    doc.save(path)
    return path


def exportar_docx(d: DatosPrograma, path: str) -> str:
    from docx import Document
    from docx.shared import Pt
    doc = Document()
    for line in generar_markdown(d).split("\n"):
        if line.startswith("# "):
            doc.add_heading(line[2:], level=1)
        elif line.startswith("## "):
            doc.add_heading(line[3:], level=2)
        elif line.startswith("### "):
            doc.add_heading(line[4:], level=3)
        elif line.strip().startswith("|"):
            doc.add_paragraph(line)  # tablas simples como texto
        elif line.strip().startswith("---"):
            continue
        else:
            doc.add_paragraph(line)
    doc.save(path)
    return path


_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<style>
  @page {{ size: Letter; margin: 2cm 2cm 2.2cm 2cm; }}
  body {{ font-family: "DejaVu Serif", Georgia, "Times New Roman", serif; font-size: 10.5pt;
          line-height: 1.5; color: #1a1a1a; }}
  h1 {{ font-family: "DejaVu Sans", Arial, sans-serif; font-size: 17pt; color: #14532d;
        border-bottom: 3px solid #14532d; padding-bottom: 6px; margin-top: 0; }}
  h2 {{ font-family: "DejaVu Sans", Arial, sans-serif; font-size: 13pt; color: #166534;
        margin-top: 20px; border-bottom: 1px solid #bbf7d0; padding-bottom: 3px; }}
  h3 {{ font-family: "DejaVu Sans", Arial, sans-serif; font-size: 11pt; color: #15803d; margin-top: 14px; }}
  table {{ border-collapse: collapse; width: 100%; margin: 10px 0; font-size: 9.5pt; }}
  th, td {{ border: 1px solid #cbd5e1; padding: 5px 8px; text-align: left; vertical-align: top; }}
  th {{ background: #dcfce7; color: #14532d; }}
  tr:nth-child(even) td {{ background: #f8fafc; }}
  blockquote {{ background: #f0fdf4; border-left: 4px solid #16a34a; margin: 12px 0;
                padding: 8px 14px; color: #14532d; }}
  code {{ background: #f1f5f9; padding: 1px 4px; border-radius: 3px; font-size: 9pt; }}
  hr {{ border: none; border-top: 1px solid #e2e8f0; margin: 16px 0; }}
  ul, ol {{ margin: 6px 0 6px 18px; }}
  li {{ margin: 2px 0; }}
  a {{ color: #15803d; }}
</style></head><body>
{body}
</body></html>"""


def generar_html(d: DatosPrograma, titulo: str | None = None) -> str:
    """Convierte el Markdown del programa a un HTML con estilo imprimible."""
    import markdown as _md
    md_text = generar_markdown(d)
    body = _md.markdown(md_text, extensions=["tables", "sane_lists", "nl2br"])
    return _HTML_TEMPLATE.format(body=body)


def exportar_html(d: DatosPrograma, path: str) -> str:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(generar_html(d))
    return path


def exportar_pdf(d: DatosPrograma, path: str) -> str:
    """Genera el PDF vía Markdown -> HTML -> wkhtmltopdf (pipeline robusto)."""
    import subprocess
    import tempfile
    html = generar_html(d)
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as fh:
        fh.write(html)
        html_path = fh.name
    try:
        subprocess.run(
            ["wkhtmltopdf", "--enable-local-file-access", "--quiet",
             "--encoding", "utf-8", "-s", "Letter",
             "--margin-top", "18mm", "--margin-bottom", "20mm",
             "--margin-left", "18mm", "--margin-right", "18mm",
             "--footer-center", "Programa de Manejo Forestal Simplificado — Palmilla (Yucca) — página [page] de [topage]",
             "--footer-font-size", "7", "--footer-spacing", "6",
             html_path, path],
            check=True, capture_output=True,
        )
    finally:
        os.unlink(html_path)
    return path


if __name__ == "__main__":
    d = DatosPrograma(
        promovente="Ejido Sierra de Juárez",
        predio_nombre="Predio El Cardonal",
        municipio="Ensenada",
        superficie_ha=180,
        tipo_propietario="ejidal",
        densidad_ind_ha=320,
        pct_maduros=0.55,
        peso_tallo_kg=18,
    )
    print(generar_markdown(d)[:1500])
    print("\n\n--- CÁLCULOS ---")
    import json
    print(json.dumps(calcular(d), ensure_ascii=False, indent=2))
