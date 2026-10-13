# -*- coding: utf-8 -*-
"""
MÓDULO A — Base de Conocimiento Legal Estructurada (RAG Normativo)
==================================================================
Base de conocimiento verificada para el aprovechamiento de recursos
forestales no maderables (RFNM) del género Yucca ("palmilla"/"yuca")
en Baja California, México.

Todas las disposiciones provienen de documentos oficiales descargados en
corpus/ (LGDFS, Reglamento LGDFS, NOM-005-SEMARNAT-1997, NOM-059-SEMARNAT-2010,
NOM-152-SEMARNAT-2023) y de literatura científica del INIFAP.

Cada PROVISION incluye: id, norma, articulo, titulo, texto (literal o
parafraseado y marcado), temas (tags de recuperación) y aplica_a.
"""

# ---------------------------------------------------------------------------
# 1. METADATOS DE LAS NORMAS
# ---------------------------------------------------------------------------
NORMAS = {
    "LGDFS": {
        "nombre": "Ley General de Desarrollo Forestal Sustentable",
        "tipo": "Ley Federal",
        "autoridad": "SEMARNAT / CONAFOR",
        "ultima_reforma": "DOF 01-04-2024",
        "fuente": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LGDFS.pdf",
        "relevancia": "Marco regulatorio principal; define RFNM y distingue aviso vs. autorización.",
    },
    "RLGDFS": {
        "nombre": "Reglamento de la Ley General de Desarrollo Forestal Sustentable",
        "tipo": "Reglamento",
        "autoridad": "SEMARNAT",
        "ultima_reforma": "DOF 31-10-2014",
        "fuente": "http://www.profepa.gob.mx/innovaportal/file/3269/1/reglamento_de_la_ley_general_de_desarrollo_forestal_sustentable.pdf",
        "relevancia": "Requisitos del aviso/autorización y contenido del Programa de Manejo Simplificado.",
    },
    "NOM-005": {
        "nombre": "NOM-005-SEMARNAT-1997 (antes NOM-005-RECNAT-1997)",
        "tipo": "Norma Oficial Mexicana",
        "autoridad": "SEMARNAT",
        "publicacion": "DOF 20-05-1997",
        "fuente": "https://www.profepa.gob.mx/innovaportal/file/3300/1/nom-005-semarnat-1997.pdf",
        "relevancia": "Procedimientos, criterios y especificaciones técnicas para aprovechamiento, transporte y almacenamiento de corteza, tallos y plantas completas. §4.1.4 y §4.1.10 son específicas para Yucca spp.",
    },
    "NOM-006": {
        "nombre": "NOM-006-SEMARNAT-1997 (antes NOM-006-RECNAT-1997)",
        "tipo": "Norma Oficial Mexicana",
        "autoridad": "SEMARNAT",
        "publicacion": "DOF 1997",
        "fuente": "Catálogo de Normas SEMARNAT",
        "relevancia": "Aplicable cuando sólo se extraen hojas/cogollos o follaje (no el tallo).",
    },
    "NOM-059": {
        "nombre": "NOM-059-SEMARNAT-2010",
        "tipo": "Norma Oficial Mexicana",
        "autoridad": "SEMARNAT",
        "publicacion": "DOF 30-12-2010",
        "fuente": "https://www.profepa.gob.mx/innovaportal/file/435/1/nom_059_semarnat_2010.pdf",
        "relevancia": "Categorías de riesgo (E, A, Pr, P) de flora/fauna; define si la especie requiere autorización adicional del INE/SEMARNAT.",
    },
    "NOM-152": {
        "nombre": "NOM-152-SEMARNAT-2023 (sustituye a NOM-152-SEMARNAT-2006)",
        "tipo": "Norma Oficial Mexicana",
        "autoridad": "SEMARNAT",
        "publicacion": "DOF 24-07-2023 (vigente 20-01-2024)",
        "fuente": "http://e-plagas.cnf.gob.mx/ContenidoPublico/10%20Material%20de%20Consulta/Normatividad%20Vigente/NOM_152_SEMARNAT_2023.pdf",
        "relevancia": "Criterios y estructura de los Programas de Manejo Forestal Sustentable. NOTA: la versión 2023 está enfocada a recursos MADERABLES; para no maderables rige el Reglamento LGDFS Art. 57 (PMF Simplificado).",
    },
    "LGEEPA": {
        "nombre": "Ley General del Equilibrio Ecológico y la Protección al Ambiente",
        "tipo": "Ley Federal",
        "autoridad": "SEMARNAT",
        "fuente": "https://www.diputados.gob.mx/LeyesBiblio/pdf/LGEEPA.pdf",
        "relevancia": "Impacto ambiental, ANP y especies en riesgo.",
    },
}

# ---------------------------------------------------------------------------
# 2. DISPOSICIONES VERIFICADAS (corazón del RAG)
# ---------------------------------------------------------------------------
PROVISIONS = [
    # ---------------- LGDFS ----------------
    {
        "id": "LGDFS-84",
        "norma": "LGDFS",
        "articulo": "Artículo 84",
        "titulo": "Aviso para RFNM (regla general)",
        "texto": "El aprovechamiento de recursos no maderables únicamente requerirá de un aviso "
                 "por escrito a la autoridad competente. El Reglamento establecerá los requisitos del aviso.",
        "temas": ["aviso", "recursos no maderables", "regla general", "RFNM"],
        "aplica_a": "Regla general para la mayoría de RFNM (NO aplica a Yucca tallos).",
    },
    {
        "id": "LGDFS-85",
        "norma": "LGDFS",
        "articulo": "Artículo 85",
        "titulo": "Casos que SÍ requieren AUTORIZACIÓN",
        "texto": "Se requiere autorización para el aprovechamiento en los casos siguientes: "
                 "a) Tierra de monte y de hoja; b) Tallos de las especies del género Yucca, y "
                 "c) Plantas completas de las familias Agavaceae, Cactaceae, Cyatheaceae, "
                 "Dicksoniaceae, Nolinaceae, Orchidaceae, Palmae y Zamiaceae provenientes de "
                 "vegetación forestal. El Reglamento establecerá los requisitos de la solicitud de autorización.",
        "temas": ["autorización", "Yucca", "tallos", "palmilla", "plantas completas", "cactáceas"],
        "aplica_a": "FUNDAMENTAL: los tallos de Yucca (palmilla) REQUIEREN AUTORIZACIÓN, no sólo aviso.",
    },
    {
        "id": "LGDFS-86",
        "norma": "LGDFS",
        "articulo": "Artículo 86",
        "titulo": "Colecta y uso de recursos biológicos forestales",
        "texto": "La colecta y uso de recursos biológicos forestales con fines de utilización en "
                 "investigación y/o biotecnología requiere de autorización por parte de la Secretaría. "
                 "La autorización sólo podrá otorgarse si se cuenta con el consentimiento escrito previo, "
                 "expreso e informado, del propietario o legítimo poseedor del predio.",
        "temas": ["colecta", "biotecnología", "investigación", "consentimiento"],
        "aplica_a": "Solo si el fin es investigación o biotecnología.",
    },
    {
        "id": "LGDFS-88",
        "norma": "LGDFS",
        "articulo": "Artículo 88",
        "titulo": "Aprovechamiento para uso doméstico",
        "texto": "El aprovechamiento de recursos y materias primas forestales para uso doméstico "
                 "se sujetarán a lo que establezca el Reglamento. En su caso podrán emitirse Normas "
                 "Oficiales Mexicanas en dichas materias.",
        "temas": ["uso doméstico", "autoconsumo"],
        "aplica_a": "Cuando el destino es autoconsumo (no comercial).",
    },
    {
        "id": "LGDFS-90",
        "norma": "LGDFS",
        "articulo": "Artículo 90",
        "titulo": "Especies en categoría de riesgo",
        "texto": "El aprovechamiento de los recursos forestales, para usos domésticos y colecta para "
                 "fines de investigación, en áreas que sean el hábitat de especies que se encuentren en "
                 "alguna categoría de riesgo, deberá hacerse de manera que no se alteren las condiciones "
                 "para la sobrevivencia, desarrollo y permanencia de dichas especies.",
        "temas": ["especies en riesgo", "NOM-059", "hábitat", "categoría de riesgo"],
        "aplica_a": "Si el predio alberga especies listadas en NOM-059.",
    },
    {
        "id": "LGDFS-91",
        "norma": "LGDFS",
        "articulo": "Artículo 91",
        "titulo": "Acreditación de la legal procedencia / trazabilidad",
        "texto": "Quienes realicen el aprovechamiento, transporte, almacenamiento, comercialización, "
                 "importación, exportación, transformación o posean materias primas y productos "
                 "forestales, deberán acreditar su legal procedencia. La autoridad establecerá los "
                 "mecanismos para garantizar la trazabilidad.",
        "temas": ["legal procedencia", "trazabilidad", "transporte", "remisión"],
        "aplica_a": "Transporte y comercialización del material.",
    },
    {
        "id": "LGDFS-68",
        "norma": "LGDFS",
        "articulo": "Artículo 68 (fracción IV)",
        "titulo": "Actos de la Secretaría",
        "texto": "Corresponderá a la Secretaría emitir, entre otras: IV. Autorización de aprovechamiento "
                 "de recursos forestales no maderables, en los casos previstos por el artículo 85 de esta Ley.",
        "temas": ["autorización", "SEMARNAT", "facultades"],
        "aplica_a": "Fundamento de la competencia de SEMARNAT.",
    },
    {
        "id": "LGDFS-69",
        "norma": "LGDFS",
        "articulo": "Artículo 69 (fracción III)",
        "titulo": "Avisos que recibe la Secretaría",
        "texto": "Corresponderá a la Secretaría recibir: III. Aviso de aprovechamiento de recursos "
                 "forestales no maderables no previstos en el artículo 85 de esta Ley.",
        "temas": ["aviso", "RFNM", "SEMARNAT"],
        "aplica_a": "Confirma que el aviso es residual (lo no listado en Art. 85).",
    },

    # ---------------- REGLAMENTO LGDFS ----------------
    {
        "id": "RLGDFS-53",
        "norma": "RLGDFS",
        "articulo": "Artículo 53",
        "titulo": "Requisitos del aviso de RFNM",
        "texto": "El aviso de aprovechamiento de RFNM se presenta mediante formato con nombre/razón social "
                 "y domicilio del propietario o poseedor. Junto con el aviso se presenta: I. Título de "
                 "propiedad o posesión; II. Instrumento que acredite el derecho al aprovechamiento; "
                 "III. Acta de asamblea (ejidos/comunidades); IV. Plano georreferenciado de las áreas de "
                 "aprovechamiento; V. Manifestación bajo protesta de la situación legal del predio; "
                 "VI. Vigencia; VII. Estudio técnico (ubicación, características físicas/biológicas, "
                 "existencias reales, madurez de cosecha, periodo de recuperación, criterios técnicos, "
                 "labores de fomento, y datos del prestador de servicios técnicos).",
        "temas": ["aviso", "requisitos", "plano georreferenciado", "título de propiedad", "acta asamblea", "estudio técnico"],
        "aplica_a": "Base de requisitos documentales (el de autorización es análogo y más exigente).",
    },
    {
        "id": "RLGDFS-55",
        "norma": "RLGDFS",
        "articulo": "Artículo 55",
        "titulo": "Casos que requieren Programa de Manejo Simplificado + Autorización",
        "texto": "Se requerirá la presentación de un programa de manejo forestal simplificado y la "
                 "autorización de la Secretaría, cuando se trate de aprovechamientos forestales no "
                 "maderables en los casos siguientes: I. Tierra de monte y de hoja; II. Tallos de las "
                 "especies del género Yucca; III. Plantas completas de las familias Agavaceae, Cactaceae, "
                 "Cyatheaceae, Dicksoniaceae, Nolinaceae, Orchidaceae, Palmae y Zamiaceae, y IV. Otros "
                 "casos determinados expresamente en las normas oficiales mexicanas.",
        "temas": ["programa de manejo simplificado", "autorización", "Yucca", "tallos"],
        "aplica_a": "CONFIRMA: Yucca tallos → PMF Simplificado + Autorización.",
    },
    {
        "id": "RLGDFS-56",
        "norma": "RLGDFS",
        "articulo": "Artículo 56",
        "titulo": "Documentos de la solicitud de autorización",
        "texto": "La solicitud se presenta mediante formato que expida la Secretaría (FF-SEMARNAT-074), con "
                 "datos del interesado y del responsable de dirigir la ejecución. Junto con la solicitud: "
                 "I. Título de propiedad o posesión (original/copia certificada); II. Instrumento del derecho "
                 "al aprovechamiento con vigencia ≥ a la del PMF; III. Acta de asamblea (ejidos/comunidades); "
                 "IV. Manifestación bajo protesta de la situación legal del predio; V. Plano georreferenciado; "
                 "VI. Programa de manejo forestal simplificado.",
        "temas": ["solicitud", "autorización", "FF-SEMARNAT-074", "requisitos", "plano georreferenciado", "acta asamblea"],
        "aplica_a": "Checklist documental exacto para Yucca.",
    },
    {
        "id": "RLGDFS-57",
        "norma": "RLGDFS",
        "articulo": "Artículo 57",
        "titulo": "Contenido del Programa de Manejo Simplificado",
        "texto": "Los programas de manejo simplificado de RFNM deberán contener: I. Tratándose de cualquier "
                 "especie: a) Diagnóstico general físico, biológico y ecológico; b) Análisis de aprovechamientos "
                 "anteriores y respuesta del recurso; c) Vigencia; d) Especies, productos, superficies y "
                 "cantidades por aprovechar anualmente (menores a la tasa de regeneración); e) Estimación de "
                 "existencias reales y tasa de regeneración; f) Periodo de recuperación; g) Criterios y "
                 "especificaciones técnicas; h) Labores de fomento y prácticas de cultivo; i) Medidas para "
                 "prevenir y controlar incendios; j) Medidas de prevención y mitigación de impactos ambientales; "
                 "k) Datos del responsable técnico. II. Cactaceae/Cyatheaceae/Dicksoniaceae/Orchidaceae/Zamiaceae: "
                 "estructura de población, distribución y número de plantas aprovechables, tasa de regeneración. "
                 "III. Si se trata de especies del género Yucca, además de las fracciones I y II: a) Descripción "
                 "de los accesos al área de aprovechamiento, y b) Estudio dasométrico.",
        "temas": ["programa de manejo simplificado", "contenido", "estructura", "Yucca", "estudio dasométrico", "accesos"],
        "aplica_a": "ESTRUCTURA OBLIGATORIA del documento a generar (Módulo C).",
    },
    {
        "id": "RLGDFS-58",
        "norma": "RLGDFS",
        "articulo": "Artículo 58",
        "titulo": "Criterios según ciclos de recuperación",
        "texto": "Los criterios, las especificaciones técnicas y los periodos de aprovechamiento de los RFNM "
                 "se determinarán de acuerdo con los ciclos de recuperación y regeneración de la especie y "
                 "sus partes por aprovechar.",
        "temas": ["ciclos de recuperación", "regeneración", "criterios técnicos"],
        "aplica_a": "Justifica el ciclo de corta de 15 años para Yucca.",
    },
    {
        "id": "RLGDFS-59",
        "norma": "RLGDFS",
        "articulo": "Artículo 59",
        "titulo": "Vigencia máxima",
        "texto": "Los avisos y autorizaciones de aprovechamiento de RFNM tendrán una vigencia máxima de cinco "
                 "años. Cuando se incluya el RFNM en un programa de manejo maderable, la vigencia máxima será "
                 "hasta un término igual al ciclo de corta del aprovechamiento maderable autorizado.",
        "temas": ["vigencia", "cinco años", "plazo"],
        "aplica_a": "Vigencia del PMF y de la autorización.",
    },
    {
        "id": "RLGDFS-60",
        "norma": "RLGDFS",
        "articulo": "Artículo 60",
        "titulo": "Procedimiento de resolución",
        "texto": "La Secretaría otorgará la autorización conforme a: I. Revisión y, en su caso, prevención al "
                 "interesado dentro de los 15 días hábiles siguientes para completar información, a presentarse "
                 "en 15 días hábiles; II. Transcurrido el plazo sin desahogar la prevención, se desechará el "
                 "trámite; III. Concluidos los plazos, la autoridad resolverá dentro de los 15 días hábiles "
                 "siguientes. En caso de que la Secretaría no emita resolución se entenderá que la misma es en "
                 "sentido POSITIVO (silencio administrativo positivo).",
        "temas": ["procedimiento", "plazos", "silencio positivo", "resolución"],
        "aplica_a": "Tiempos y garantía de silencio positivo.",
    },
    {
        "id": "RLGDFS-61",
        "norma": "RLGDFS",
        "articulo": "Artículo 61",
        "titulo": "Contenido de la autorización",
        "texto": "Las autorizaciones deberán contener: I. Nombre/razón social y domicilio del titular; "
                 "II. Denominación y ubicación del predio; III. Ubicación georreferenciada; IV. Superficie total "
                 "por aprovechar en hectáreas; V. Especies y partes a aprovechar; VI. Calendario de "
                 "aprovechamiento y cantidades por producto; VII. Vigencia.",
        "temas": ["autorización", "contenido", "calendario"],
        "aplica_a": "Qué debe reflejar la resolución (para el seguimiento del expediente).",
    },

    # ---------------- NOM-005 ----------------
    {
        "id": "NOM005-1.1",
        "norma": "NOM-005",
        "articulo": "Numeral 1.1",
        "titulo": "Objetivo y campo de aplicación",
        "texto": "La presente Norma es de observancia general en todo el territorio nacional y tiene por objeto "
                 "establecer los procedimientos, criterios y especificaciones técnicas y administrativas para "
                 "realizar el aprovechamiento sostenible, transporte y almacenamiento de corteza, tallos y "
                 "plantas completas en poblaciones naturales, con excepción de la Candelilla (Euphorbia spp.).",
        "temas": ["objetivo", "campo de aplicación", "tallos", "corteza", "plantas completas"],
        "aplica_a": "Aplica a tallos de Yucca.",
    },
    {
        "id": "NOM005-4.1.4",
        "norma": "NOM-005",
        "articulo": "Numeral 4.1.4",
        "titulo": "Aprovechamiento de Yucca spp. (solicitud de autorización)",
        "texto": "Para realizar el aprovechamiento de la Yucca spp., el dueño o poseedor del predio deberá "
                 "presentar una solicitud de autorización por escrito ante la Delegación Federal de la Secretaría, "
                 "acompañada de: I. Nombre y domicilio del dueño o poseedor; II. Título que acredite la propiedad "
                 "o posesión; III. Estudio técnico justificativo, cuya vigencia máxima será de 5 años, que "
                 "contendrá: a) Nombre y ubicación del predio y características físicas y biológicas; b) Técnicas "
                 "que se utilizarán en el aprovechamiento; c) Estudio dasométrico; d) Medidas de protección a la "
                 "fauna silvestre; e) Medidas de protección a las especies de flora y fauna silvestres con estatus; "
                 "f) Medidas para prevenir y controlar incendios, plagas y enfermedades; g) Medidas de prevención "
                 "y mitigación de impactos ambientales; h) Planeación de la infraestructura caminera para el "
                 "abastecimiento; i) Labores de fomento y prácticas culturales para la preservación del recurso.",
        "temas": ["Yucca", "solicitud", "autorización", "estudio técnico justificativo", "estudio dasométrico", "infraestructura caminera"],
        "aplica_a": "Requisitos específicos de Yucca (núcleo del Módulo C).",
    },
    {
        "id": "NOM005-4.1.10",
        "norma": "NOM-005",
        "articulo": "Numeral 4.1.10 (fracc. IV inciso d)",
        "titulo": "Criterios técnicos específicos para Yucca spp.",
        "texto": "Para el aprovechamiento de Yucca spp., la madurez de cosecha se identificará cuando las colonias "
                 "tengan individuos desprovistos de hojas verdes en un 80% de su longitud, y tratándose de grupos de "
                 "edad homogénea que cumplan con lo anterior, se deberá aprovechar sólo el 50% de los individuos "
                 "maduros, evitando dañar los brotes e individuos jóvenes. El ciclo de corta para los aprovechamientos "
                 "de la Yucca spp. en áreas no intervenidas no será menor a 15 años. Se podrá proponer el "
                 "aprovechamiento en una o dos anualidades del 50% de la población aprovechable, siempre que se trate "
                 "de predios con superficie menor de 250 hectáreas pobladas con Yucca spp., y no podrá tener otra "
                 "intervención el área aprovechada por un periodo equivalente a un ciclo de corta.",
        "temas": ["madurez de cosecha", "50%", "ciclo de corta", "15 años", "250 hectáreas", "Yucca", "anualidades"],
        "aplica_a": "Reglas de cosecha que el PMF debe respetar.",
    },
    {
        "id": "NOM005-4.1.8",
        "norma": "NOM-005",
        "articulo": "Numeral 4.1.8",
        "titulo": "Contenido de la autorización (Yucca)",
        "texto": "La autorización que expida la Delegación Federal deberá especificar: a) Nombre/razón social y "
                 "domicilio del titular; b) Nombre y ubicación del predio; c) Superficie en hectáreas y número de "
                 "individuos por aprovecharse por especie (cactáceas) y cantidad en TONELADAS para el caso de Yucca "
                 "spp.; d) Vigencia de la autorización; e) Restricciones de protección ecológica adicionales.",
        "temas": ["autorización", "toneladas", "Yucca", "vigencia"],
        "aplica_a": "Unidad de medida para Yucca: toneladas.",
    },
    {
        "id": "NOM005-4.1.9",
        "norma": "NOM-005",
        "articulo": "Numeral 4.1.9",
        "titulo": "Informes trimestrales",
        "texto": "El titular deberá presentar ante la Delegación Federal un informe trimestral, dentro de los "
                 "primeros 10 días hábiles de los meses de abril, julio, octubre y enero de cada año, y uno al final "
                 "del aprovechamiento, avalado por el responsable técnico.",
        "temas": ["informe trimestral", "seguimiento", "responsable técnico"],
        "aplica_a": "Obligación posterior a la autorización.",
    },
    {
        "id": "NOM005-4.1.13",
        "norma": "NOM-005",
        "articulo": "Numeral 4.1.13",
        "titulo": "Especies con estatus",
        "texto": "Las especies con estatus podrán incorporarse al aprovechamiento previa autorización que al efecto "
                 "emita el Instituto Nacional de Ecología (hoy SEMARNAT/DGVS), de conformidad con la LGEEPA. Dicha "
                 "autorización deberá entregarse anexa a la solicitud de autorización de aprovechamiento.",
        "temas": ["especies con estatus", "NOM-059", "autorización adicional", "INE"],
        "aplica_a": "Si la especie de Yucca está listada en NOM-059.",
    },
    {
        "id": "NOM005-4.1.14",
        "norma": "NOM-005",
        "articulo": "Numeral 4.1.14",
        "titulo": "Áreas Naturales Protegidas",
        "texto": "En terrenos comprendidos en zonas declaradas como áreas naturales protegidas, el aprovechamiento "
                 "podrá realizarse previa autorización que expida el Instituto Nacional de Ecología, de conformidad "
                 "con la LGEEPA.",
        "temas": ["ANP", "área natural protegida", "autorización adicional", "LGEEPA"],
        "aplica_a": "Si el predio está dentro de un ANP (ej. Valle de los Cirios, B.C.).",
    },
    {
        "id": "NOM005-4.1.1",
        "norma": "NOM-005",
        "articulo": "Numeral 4.1.1",
        "titulo": "Excepción: Yucca y cactáceas no usan notificación simple",
        "texto": "Con excepción de las plantas completas de cactáceas y la Yucca spp., para realizar el "
                 "aprovechamiento de corteza, tallos y plantas completas de vegetación forestal, el dueño o poseedor "
                 "del predio deberá presentar una notificación por escrito... misma que podrá ser anual o por un "
                 "periodo máximo de 5 años.",
        "temas": ["notificación", "excepción", "Yucca", "cactáceas"],
        "aplica_a": "Confirma que Yucca NO se tramita por notificación simple sino por autorización.",
    },

    # ---------------- NOM-059 ----------------
    {
        "id": "NOM059-general",
        "norma": "NOM-059",
        "articulo": "Numeral 5 y Anexo Normativo III",
        "titulo": "Categorías de riesgo",
        "texto": "Establece las categorías de riesgo: P (Probablemente extinta en el medio silvestre), "
                 "E (En peligro de extinción), A (Amenazada) y Pr (Sujeta a protección especial). La lista "
                 "definitiva se publica en el Anexo Normativo III. No se permite el aprovechamiento extractivo de "
                 "especies en peligro de extinción, salvo autorización especial; para especies amenazadas o con "
                 "protección especial se requieren planes de manejo y permisos específicos.",
        "temas": ["NOM-059", "categorías de riesgo", "E", "A", "Pr", "P", "Anexo III"],
        "aplica_a": "Determina si se requiere autorización adicional (numeral 4.1.13 de NOM-005).",
    },

    # ---------------- INIFAP (técnico-científico) ----------------
    {
        "id": "INIFAP-muestreo",
        "norma": "INIFAP",
        "articulo": "Rev. Mex. Cienc. For. 12(spe1) 2021",
        "titulo": "Técnicas de muestreo para RFNM",
        "texto": "El muestreo sistemático es útil en rodales con distribución uniforme de especies como "
                 "Yucca carnerosana y Nolina cespitifera (sitios de 100 m² o 1,000 m²; intensidad de 0.5% a 3%). "
                 "El muestreo aleatorio estratificado es factible para poblaciones de distribución heterogénea "
                 "(Agave lechuguilla, Euphorbia antisyphilitica, Lippia graveolens, Dasylirion spp.).",
        "temas": ["muestreo", "inventario", "sistemático", "estratificado", "100 m2", "1000 m2", "intensidad"],
        "aplica_a": "Metodología de inventario del Módulo C.",
    },
    {
        "id": "INIFAP-turno",
        "norma": "INIFAP",
        "articulo": "Rev. Mex. Cienc. For. 12(spe1) 2021",
        "titulo": "Turno técnico / época de aprovechamiento",
        "texto": "El turno técnico es el tiempo desde la extracción hasta la recuperación de la estructura vegetal. "
                 "Para Yucca carnerosana (palma samandoca) existe la 'Guía para la evaluación de existencias' "
                 "(Villavicencio & Franco, 1992). Los estudios de turno técnico sirven de base para las NOM de "
                 "especificaciones técnicas y para los Estudios Técnicos Justificativos.",
        "temas": ["turno técnico", "recuperación", "Yucca carnerosana", "palma samandoca"],
        "aplica_a": "Justificación técnica del ciclo de corta.",
    },
]

# ---------------------------------------------------------------------------
# 3. ESPECIES (Yucca y asociadas) — Baja California / zonas áridas
# ---------------------------------------------------------------------------
ESPECIES = {
    "Yucca schidigera": {
        "nombre_comun": "yuca / palmilla (Mojave yucca)",
        "parte_aprovechada": "tallo (y hojas)",
        "regimen": "AUTORIZACIÓN (LGDFS Art. 85b; NOM-005 §4.1.4)",
        "distribucion": "Baja California, Sonora; matorral desértico (Mojave/Sonorense)",
        "nota_nom059": "Verificar Anexo III vigente; típicamente NO listada, pero confirmar por predio.",
    },
    "Yucca valida": {
        "nombre_comun": "datilillo / palmilla",
        "parte_aprovechada": "tallo",
        "regimen": "AUTORIZACIÓN (LGDFS Art. 85b; NOM-005 §4.1.4)",
        "distribucion": "Baja California Sur, Baja California; matorral desértico",
        "nota_nom059": "Endémica de BCS/BC; verificar estatus en Anexo III vigente.",
    },
    "Yucca carnerosana": {
        "nombre_comun": "palma samandoca / yuca",
        "parte_aprovechada": "tallo / cogollo",
        "regimen": "AUTORIZACIÓN (LGDFS Art. 85b; NOM-005 §4.1.4)",
        "distribucion": "Norte de México (Coahuila, Chihuahua, etc.); zonas áridas",
        "nota_nom059": "Verificar Anexo III vigente.",
    },
    "Yucca brevifolia": {
        "nombre_comun": "árbol de Josué (Joshua tree)",
        "parte_aprovechada": "tallo",
        "regimen": "AUTORIZACIÓN (LGDFS Art. 85b; NOM-005 §4.1.4)",
        "distribucion": "Zonas desérticas (Mojave)",
        "nota_nom059": "VERIFICAR: frecuentemente listada como Amenazada/Protección especial en listas estatales/regionales.",
    },
}

# ---------------------------------------------------------------------------
# 4. TRÁMITES Y FORMATOS
# ---------------------------------------------------------------------------
TRAMITES = [
    {
        "clave": "SEMARNAT-03-052",
        "nombre": "Autorización para el aprovechamiento de recursos forestales no maderables",
        "homoclave_url": "https://www.gob.mx/public/tramites/detalleTramite.xhtml?homoclave=SEMARNAT-03-052",
        "fundamento": "LGDFS Art. 68 fracc. IV y 85; Reglamento LGDFS Arts. 55-61; NOM-005-SEMARNAT-1997",
        "aplica_a": "Tallos de Yucca (palmilla) y demás casos del Art. 85.",
    },
    {
        "clave": "SEMARNAT-03-005",
        "nombre": "Aviso para el aprovechamiento de recursos forestales no maderables",
        "fundamento": "LGDFS Art. 84 y 69 fracc. III; Reglamento LGDFS Art. 53",
        "aplica_a": "RFNM NO previstos en el Art. 85 (no aplica a tallos de Yucca).",
    },
    {
        "clave": "SEMARNAT-03-003",
        "nombre": "Solicitud de autorización de aprovechamiento maderable",
        "aplica_a": "Recursos maderables (no aplica al caso palmilla).",
    },
]

FORMATOS = [
    {
        "clave": "FF-SEMARNAT-074",
        "nombre": "Formato oficial de solicitud (SEMARNAT-03-052)",
        "url": "http://dsiappsdev.semarnat.gob.mx/formatos/DGGFS/FF-SEMARNAT-074%20SEMARNAT-03-052%20editable.pdf",
    },
]

# ---------------------------------------------------------------------------
# 5. PARÁMETROS TÉCNICOS CLAVE (para el motor de reglas y el generador)
# ---------------------------------------------------------------------------
PARAMETROS_TECNICOS = {
    "tasa_cosecha_max": 0.50,          # 50% de individuos maduros (NOM-005 §4.1.10 IV d)
    "ciclo_corta_anios": 15,           # mínimo, áreas no intervenidas
    "vigencia_max_anios": 5,           # Reglamento Art. 59
    "umbral_predio_pequeno_ha": 250,   # NOM-005 §4.1.10 IV d
    "madurez_cosecha_defoliacion": 0.80,  # 80% desprovisto de hojas verdes
    "sitio_muestreo_m2": [100, 1000],
    "intensidad_muestreo_pct": [0.5, 3.0],
}
