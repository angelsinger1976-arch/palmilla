# Sistema de Agente IA para el Aprovechamiento Forestal No Maderable de Palmilla (*Yucca* spp.) en Baja California

## Documento Técnico de Arquitectura, Marco Normativo y Operación

---

## 1. Resumen ejecutivo

Este documento describe el diseño, la arquitectura y la operación de **PalmillaBot**, un sistema de agente de inteligencia artificial concebido para asistir a poseedores de terrenos forestales —ejidos, comunidades y pequeños propietarios— en la obtención de las **autorizaciones y permisos** exigidos por la Secretaría de Medio Ambiente y Recursos Naturales (SEMARNAT) para el aprovechamiento de **recursos forestales no maderables (RFNM)**, específicamente los **tallos del género *Yucca*** (palmilla o yuca) en el matorral desértico de **Baja California, México**.

El sistema no es una simple recopilación documental. Es una **herramienta funcional y ejecutable** que integra tres módulos de software —un motor de recuperación normativa (RAG), un motor de reglas condicionales y un generador de documentos técnicos— orquestados por un *system prompt* de rol ("Agente Ingeniero Forestal") y expuestos mediante una interfaz web operativa. El resultado es un asistente que, a partir de los datos de un predio, determina la vía de trámite aplicable, construye el checklist de requisitos, recupera y cita las disposiciones legales pertinentes, calcula los parámetros de inventario y cosecha, y **genera el Programa de Manejo Forestal Simplificado** listo para exportación en PDF, DOCX, HTML o Markdown.

Un hallazgo jurídico central motiva el diseño: el aprovechamiento de los **tallos de *Yucca*** **no se tramita por la vía del simple *aviso***, sino que **requiere autorización expresa** de la SEMARNAT conforme al **artículo 85, inciso b) de la Ley General de Desarrollo Forestal Sustentable (LGDFS)**. Esta distinción —aviso frente a autorización— es la columna vertebral del motor de reglas y del generador documental, y corrige un error frecuente en la práctica: suponer que los RFNM se aprovechan siempre mediante notificación.

---

## 2. Marco normativo de referencia

El sistema fundamenta cada una de sus determinaciones en disposiciones verificadas, descargadas de fuentes oficiales y almacenadas en un corpus local. La Tabla 1 sintetiza el cuerpo normativo.

**Tabla 1. Cuerpo normativo integrado al sistema.**

| Norma | Objeto | Relevancia para el sistema |
|---|---|---|
| Ley General de Desarrollo Forestal Sustentable (LGDFS) | Régimen general del aprovechamiento forestal | Arts. 84-85: distinción aviso/autorización; Art. 85(b): *Yucca* requiere autorización |
| Reglamento de la LGDFS | Detalle procedimental | Arts. 53-61: Programa de Manejo Forestal Simplificado; Art. 57: contenido obligatorio |
| NOM-005-SEMARNAT-1997 | Aprovechamiento de recursos no maderables | §4.1.4 (estudio para *Yucca*), §4.1.10 (criterios de cosecha), §4.1.14 (ANP) |
| NOM-059-SEMARNAT-2010 | Especies en riesgo | Anexo Normativo III: verificación de estatus de la especie |
| NOM-152-SEMARNAT-2023 | Estructura de programas de manejo | Referencia de estructura documental |
| LGEEPA | Áreas Naturales Protegidas | Autorización adicional cuando el predio se ubica en ANP |

La **LGDFS, artículo 85**, enumera los casos que **sí** requieren autorización. Entre ellos, el inciso b) contempla expresamente el aprovechamiento de los **tallos** de las especies del género *Yucca*, así como el de las familias Agavaceae, Cactaceae y Nolinaceae, y el de "tierra de monte". El **artículo 84**, por su parte, regula los supuestos de simple **aviso**. De esta arquitectura normativa se desprende la regla que gobierna el sistema: para la palmilla cuyo tallo se aprovecha, la vía es la **autorización**, con presentación de un **Programa de Manejo Forestal Simplificado** y del formato **FF-SEMARNAT-074** en el trámite **SEMARNAT-03-052**.

El **Reglamento de la LGDFS, artículo 57**, enumera el contenido obligatorio del Programa de Manejo Simplificado. La **NOM-005-SEMARNAT-1997, numeral 4.1.10**, establece los criterios técnicos específicos para *Yucca*: la madurez de cosecha se identifica cuando las colonias presentan individuos desprovistos de hojas verdes en **al menos el 80 %** de su longitud; se aprovecha **solo el 50 %** de los individuos maduros, evitando dañar brotes e individuos jóvenes; y el **ciclo de corta mínimo es de 15 años** en áreas no intervenidas. El **numeral 4.1.4** detalla el estudio técnico justificativo, que para *Yucca* añade requisitos específicos como el **estudio dasométrico** y la **descripción de accesos**.

---

## 3. Arquitectura del sistema

El sistema se organiza en tres módulos funcionales que se comunican a través de un orquestador central y del *system prompt* del agente. La Figura conceptual es la siguiente:

```
                 ┌─────────────────────────────────────────────┐
   Datos del     │            ORQUESTADOR (agent_core)          │
   predio  ─────►│  analizar_predio() · responder_consulta()    │
                 └───────┬───────────────┬───────────────┬──────┘
                         │               │               │
                 ┌───────▼──────┐ ┌──────▼───────┐ ┌─────▼────────┐
                 │  MÓDULO A    │ │  MÓDULO B    │ │  MÓDULO C    │
                 │  RAG         │ │  Reglas      │ │  Generador   │
                 │  Normativo   │ │  Checklist   │ │  PMF         │
                 │ (TF-IDF)     │ │ (condicional)│ │ (plantilla)  │
                 └───────┬──────┘ └──────┬───────┘ └─────┬────────┘
                         │               │               │
                 ┌───────▼───────────────▼───────────────▼──────┐
                 │   Base de conocimiento legal (legal_kb.py)    │
                 │   + Corpus crudo (corpus/*.txt)               │
                 └──────────────────────────────────────────────┘
```

### 3.1 Módulo A — RAG Normativo

El **módulo A** implementa un sistema de *Retrieval-Augmented Generation* (RAG) totalmente **offline**, sin dependencia de servicios externos. Construye un índice vectorial sobre dos fuentes:

1. **Disposiciones estructuradas y verificadas** (`legal_kb.PROVISIONS`): un conjunto de aproximadamente 27 artículos y numerales extraídos manualmente y validados contra los documentos oficiales, cada uno con identificador, norma, artículo, título, texto, temas y ámbito de aplicación.
2. **Corpus legal crudo** (`corpus/*.txt`): los textos completos de la LGDFS, el Reglamento, la NOM-005, la NOM-059 y la NOM-152, divididos automáticamente en pasajes por artículo o numeral.

La recuperación se realiza mediante **TF-IDF** (frecuencia de término–frecuencia inversa de documento) con n-gramas de 1 y 2 palabras, seguido de **similitud coseno** entre la consulta y los pasajes. El motor aplica dos *boosts* de precisión: (i) una bonificación a las disposiciones estructuradas, que son las más confiables; y (ii) una bonificación por solapamiento de términos entre la consulta y los **temas** de cada disposición, con filtrado de palabras vacías del español. El resultado es un *ranking* que devuelve, para cada consulta, los pasajes más pertinentes con su **cita exacta** (norma y artículo/numeral) y una puntuación de relevancia.

El índice resultante comprende **467 pasajes**. A modo de verificación, las consultas clave devuelven sistemáticamente la disposición correcta en la primera posición: "¿Se necesita aviso o autorización para tallos de *Yucca*?" recupera la **LGDFS Art. 85**; "¿Cuál es el ciclo de corta?" recupera la **NOM-005 §4.1.10**; "¿Qué contenido debe tener el programa de manejo?" recupera el **Reglamento Art. 57**; y "¿Qué pasa si el predio está en un ANP?" recupera la **NOM-005 §4.1.14**.

### 3.2 Módulo B — Motor de Reglas (Checklist de permisos)

El **módulo B** recibe los datos del predio y, con base en las disposiciones verificadas, **determina dinámicamente**:

- La **vía de trámite**: *aviso* o *autorización*, aplicando la regla del artículo 85 de la LGDFS. Para tallos de *Yucca*, la salida es **AUTORIZACIÓN**.
- El **trámite y formato** correspondientes: **SEMARNAT-03-052** y **FF-SEMARNAT-074**.
- El **checklist de requisitos** (documentos, formularios, planos, acreditación del técnico), cada uno con su **fundamento legal**.
- Las **autorizaciones adicionales** cuando el predio se ubica en un **ANP** (LGEEPA) o cuando la especie tiene **estatus** en la NOM-059.
- Las **reglas técnicas** de cosecha (madurez, tasa, ciclo) y los **plazos** de resolución e informes.
- Las **advertencias** y requisitos faltantes, en función de las respuestas del usuario (por ejemplo, si aún no cuenta con técnico certificado o plano georreferenciado).

Las reglas son condicionales: varían según el **régimen de propiedad** (privada, ejidal, comunal, posesión), la **especie**, la **parte aprovechada**, la **superficie** (con régimen especial para predios menores a 250 ha) y la ubicación respecto de ANP o de la NOM-059.

### 3.3 Módulo C — Generador del Programa de Manejo

El **módulo C** ensambla el **Programa de Manejo Forestal Simplificado** con la estructura obligatoria del Reglamento (Art. 57) y de la NOM-005 (§4.1.4). El generador:

1. **Calcula** los parámetros de inventario y cosecha: población total, individuos maduros, individuos aprovechables (50 % de los maduros), biomasa total, ciclo de corta y cosecha anual. El régimen de anualidades se ajusta automáticamente: en predios menores a 250 ha la cosecha se concentra en 1-2 anualidades; en predios mayores se distribuye a lo largo del ciclo de 15 años.
2. **Ensambla** un documento de diez secciones que cubre datos generales, objetivo, caracterización del medio, inventario y muestreo, estudio dasométrico y accesos, sistema de aprovechamiento y tasa de cosecha, medidas de protección y restauración, análisis de aprovechamientos anteriores, vigencia y seguimiento, y anexos. Cada sección incorpora la **cita legal** que la fundamenta.
3. **Exporta** el documento en **Markdown, HTML, DOCX y PDF**. El PDF se produce mediante un *pipeline* robusto Markdown → HTML → `wkhtmltopdf`, con estilos imprimibles y numeración de páginas.

### 3.4 Orquestador y System Prompt

El **orquestador** (`agent_core.py`) une los tres módulos en una respuesta coherente: ejecuta el motor de reglas, recupera el contexto legal con el RAG (mediante varias consultas temáticas), genera el programa de manejo y ensambla un *runtime prompt* que inyecta los datos del predio, el checklist y el contexto legal citado.

El **System Prompt** (`system_prompt.py`) define el rol del agente como un **Ingeniero Forestal especialista en RFNM**, establece el marco normativo de referencia, fija la regla legal crítica (autorización para tallos de *Yucca*), enumera los criterios técnicos de la NOM-005 §4.1.10, describe el protocolo de razonamiento y **obliga a una salida estructurada de seis secciones**:

1. **Datos Generales**
2. **Objetivo**
3. **Caracterización del Medio**
4. **Inventario y Muestreo**
5. **Sistema de Aprovechamiento y Tasa de Cosecha**
6. **Medidas de Protección y Restauración Ambiental**

El prompt incorpora además **guardarraíles** explícitos: prohibición de inventar artículos o cifras, obligación de citar con formato normalizado, y advertencia de que el documento generado es un **borrador técnico** que debe ser validado y firmado por un **Técnico Forestal Certificado** inscrito en el Registro Forestal Nacional.

---

## 4. Flujo de operación

El flujo de extremo a extremo comprende las siguientes etapas:

1. **Captura de datos.** El usuario completa el formulario del predio (promovente, municipio, superficie, régimen de propiedad, especie, parte aprovechada, densidad, proporción de individuos maduros, peso del tallo, indicadores de ANP y NOM-059).
2. **Análisis.** El orquestador ejecuta el motor de reglas y el RAG, y calcula los parámetros de cosecha. La interfaz presenta la **vía de trámite**, el **checklist** con fundamentos, las **advertencias** y las **citas legales** recuperadas.
3. **Consulta normativa.** El usuario puede formular preguntas libres; el RAG devuelve las disposiciones más relevantes con su cita y puntuación de relevancia.
4. **Generación.** El usuario genera el **Programa de Manejo Forestal Simplificado**, visualiza una vista previa y lo descarga en PDF, DOCX, HTML o Markdown.
5. **Validación humana.** El borrador es revisado y firmado por un Técnico Forestal Certificado y presentado ante la SEMARNAT.

---

## 5. Interfaz y despliegue

La interfaz web consta de un **backend FastAPI** (`app.py`) que expone los tres módulos mediante una API REST —`/api/analizar`, `/api/chat`, `/api/generar`, `/api/descargar/{formato}`, `/api/normas`— y sirve el frontend estático. El **frontend** (HTML/CSS/JavaScript) ofrece tres pestañas —Análisis y Checklist, Consulta Normativa (RAG) y Generador de Programa de Manejo— con un diseño responsivo, imprimible y de temática forestal.

La Tabla 2 resume los componentes de software.

**Tabla 2. Componentes del sistema.**

| Componente | Archivo | Función |
|---|---|---|
| Base de conocimiento legal | `src/legal_kb.py` | Normas, disposiciones, especies, trámites, parámetros técnicos |
| Módulo A — RAG | `src/rag_engine.py` | Índice TF-IDF y recuperación con citas |
| Módulo B — Reglas | `src/rules_engine.py` | Vía de trámite, checklist, reglas técnicas |
| Módulo C — Generador | `src/project_generator.py` | Cálculo y documento PMF + exportadores |
| System Prompt | `src/system_prompt.py` | Rol del agente y formato de salida |
| Orquestador | `src/agent_core.py` | Integración de los tres módulos |
| Backend | `src/app.py` | API REST (FastAPI) |
| Frontend | `web/index.html`, `style.css`, `app.js` | Interfaz de usuario |
| Corpus legal | `corpus/*.pdf`, `*.txt` | Textos oficiales de las normas |

---

## 6. Parámetros técnicos incorporados

La Tabla 3 recoge los parámetros técnicos verificados que el sistema aplica de forma automática.

**Tabla 3. Parámetros técnicos (NOM-005 §4.1.10 y afines).**

| Parámetro | Valor | Fuente |
|---|---|---|
| Tasa de cosecha máxima | 50 % de individuos maduros | NOM-005 §4.1.10(IV)(d) |
| Ciclo de corta mínimo | 15 años | NOM-005 §4.1.10(IV)(d) |
| Umbral de predio pequeño | 250 ha | NOM-005 §4.1.10 |
| Madurez de cosecha (defoliación) | 80 % de la longitud | NOM-005 §4.1.10(IV)(d) |
| Unidad de medida | toneladas | NOM-005 §4.1.8 |
| Vigencia máxima | 5 años | Reglamento LGDFS Art. 59 |

---

## 7. Ejemplo de salida

A partir de un predio ejidal de 180 ha con *Yucca schidigera* (densidad de 320 individuos/ha, 55 % de individuos maduros y 18 kg de peso promedio por tallo), el sistema produce las siguientes cifras: población total de 57,600 individuos; 31,680 individuos maduros; 15,840 individuos aprovechables (50 %); biomasa aprovechable de 285.12 toneladas; y una cosecha anual de 142.56 toneladas distribuidas en 2 anualidades, con un ciclo de corta de 15 años. La vía de trámite determinada es **AUTORIZACIÓN** mediante el trámite **SEMARNAT-03-052**, y el documento resultante consta de diez secciones con citas legales en cada una.

---

## 8. Limitaciones y responsabilidad

El sistema genera **borradores técnicos**. No sustituye la validación de un **Técnico Forestal Certificado** ni la resolución de la autoridad. Las cifras de inventario dependen de los datos de campo que el usuario proporcione; el sistema no realiza muestreo de campo. La vigencia de las normas se verifica a la fecha de construcción del corpus, por lo que se recomienda confirmar el **Anexo Normativo III** vigente de la NOM-059 y las reformas recientes de la LGDFS antes de presentar cualquier solicitud.

---

## 9. Referencias normativas y bibliográficas

- Ley General de Desarrollo Forestal Sustentable (LGDFS), arts. 68-69, 84-86, 88, 90-91. Cámara de Diputados, *LeyesBiblio*.
- Reglamento de la LGDFS, arts. 53-61. PROFEPA.
- NOM-005-SEMARNAT-1997, "Que establece los procedimientos, criterios y especificaciones para realizar el aprovechamiento, transporte y almacenamiento de recursos forestales no maderables". PROFEPA.
- NOM-059-SEMARNAT-2010, "Protección ambiental—Especies nativas de México de flora y fauna silvestres—Categorías de riesgo". PROFEPA.
- NOM-152-SEMARNAT-2023, estructura de programas de manejo. CONAFOR.
- Ley General del Equilibrio Ecológico y la Protección al Ambiente (LGEEPA).
- Trámite SEMARNAT-03-052, "Autorización para el aprovechamiento de recursos forestales no maderables"; formato FF-SEMARNAT-074.
- Villavicencio-Gutiérrez, E. E. et al. (2021). Manejo forestal sustentable de los recursos forestales no maderables en el semidesierto del norte de México. *Revista Mexicana de Ciencias Forestales*, 12(spe1). https://doi.org/10.29298/rmcf.v12iespecial-1.1083
- INIFAP (2021). Metodologías de muestreo para recursos forestales no maderables.

---

*Documento generado por PalmillaBot — Sistema de Agente IA para RFNM (Yucca).*
