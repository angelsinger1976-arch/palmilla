/* ==========================================================================
   PalmillaBot — Lógica del frontend
   ========================================================================== */
const API = ""; // mismo origen

/* ---------- Pestañas ---------- */
document.querySelectorAll(".tab").forEach((t) => {
  t.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((x) => x.classList.remove("active"));
    document.querySelectorAll(".panel").forEach((x) => x.classList.remove("active"));
    t.classList.add("active");
    document.getElementById("tab-" + t.dataset.tab).classList.add("active");
  });
});

function activarTab(nombre) {
  const t = document.querySelector(`.tab[data-tab="${nombre}"]`);
  if (t) t.click();
}

/* ---------- Utilidades ---------- */
function esc(s) {
  return String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
function num(n) {
  return Number(n || 0).toLocaleString("es-MX");
}

/* Mini-render de Markdown -> HTML (para la vista previa del documento) */
function mdToHtml(md) {
  const lines = String(md || "").split("\n");
  let html = "", inTable = false, inList = false, inQuote = false;
  const closeBlocks = () => {
    if (inTable) { html += "</tbody></table>"; inTable = false; }
    if (inList) { html += "</ul>"; inList = false; }
    if (inQuote) { html += "</blockquote>"; inQuote = false; }
  };
  const inline = (s) =>
    esc(s)
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.+?)\*/g, "<em>$1</em>")
      .replace(/`(.+?)`/g, "<code>$1</code>");

  for (let raw of lines) {
    const line = raw.replace(/\s+$/, "");
    if (!line.trim()) { closeBlocks(); continue; }
    if (/^\|/.test(line)) {
      const cells = line.split("|").slice(1, -1).map((c) => c.trim());
      if (/^[-: ]+$/.test(cells.join(""))) continue; // separador
      if (!inTable) { html += "<table><thead><tr>"; html += cells.map((c) => `<th>${inline(c)}</th>`).join(""); html += "</tr></thead><tbody>"; inTable = true; }
      else { html += "<tr>" + cells.map((c) => `<td>${inline(c)}</td>`).join("") + "</tr>"; }
      continue;
    } else { if (inTable) { html += "</tbody></table>"; inTable = false; } }
    if (/^### /.test(line)) { closeBlocks(); html += `<h3>${inline(line.slice(4))}</h3>`; continue; }
    if (/^## /.test(line)) { closeBlocks(); html += `<h2>${inline(line.slice(3))}</h2>`; continue; }
    if (/^# /.test(line)) { closeBlocks(); html += `<h1>${inline(line.slice(2))}</h1>`; continue; }
    if (/^> /.test(line)) { if (!inQuote) { html += "<blockquote>"; inQuote = true; } html += inline(line.slice(2)) + " "; continue; }
    else if (inQuote) { html += "</blockquote>"; inQuote = false; }
    if (/^[-*] /.test(line)) { if (!inList) { html += "<ul>"; inList = true; } html += `<li>${inline(line.slice(2))}</li>`; continue; }
    else if (inList) { html += "</ul>"; inList = false; }
    if (/^---+$/.test(line.trim())) { html += "<hr>"; continue; }
    html += `<p>${inline(line)}</p>`;
  }
  closeBlocks();
  return html;
}

/* ==========================================================================
   CONFIGURACIÓN DE GEMINI
   ========================================================================== */
let CFG = { configurado: false, modelo: "gemini-2.0-flash" };

function pintarEstadoIA() {
  const dot = document.getElementById("status-dot");
  const txt = document.getElementById("status-text");
  if (!dot || !txt) return;
  if (CFG.configurado) {
    dot.className = "dot dot-on";
    txt.textContent = "IA: Gemini activo";
  } else {
    dot.className = "dot dot-off";
    txt.textContent = "IA: sin configurar";
  }
}

async function cargarConfig() {
  try {
    const res = await fetch(API + "/api/config");
    CFG = await res.json();
  } catch (e) { /* servidor no disponible */ }
  pintarEstadoIA();
  const est = document.getElementById("cfg-estado");
  if (est) est.innerHTML = estadoConfigHtml(CFG);
  const sel = document.getElementById("cfg-modelo");
  if (sel && CFG.modelo) sel.value = CFG.modelo;
  return CFG;
}

function estadoConfigHtml(c) {
  if (!c) return "";
  if (c.configurado) {
    return `<div class="cfg-ok">✅ IA configurada · modelo <strong>${esc(c.modelo)}</strong>
      · clave <code>${esc(c.api_key_enmascarada || "definida")}</code>
      · origen: ${esc(c.fuente || "config")}</div>`;
  }
  return `<div class="cfg-warn">⚠️ No hay API key configurada. El sistema funciona en
    <strong>modo RAG offline</strong> (recupera y cita la ley, pero sin redacción por IA).</div>`;
}

async function guardarConfig() {
  const key = document.getElementById("cfg-apikey").value.trim();
  const modelo = document.getElementById("cfg-modelo").value;
  const est = document.getElementById("cfg-estado");
  est.innerHTML = `<div class="cfg-info"><span class="spinner spinner-dark"></span> Guardando…</div>`;
  try {
    const body = { modelo };
    if (key) body.api_key = key;
    const res = await fetch(API + "/api/config", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    CFG = await res.json();
    document.getElementById("cfg-apikey").value = "";
    pintarEstadoIA();
    est.innerHTML = estadoConfigHtml(CFG) +
      `<div class="cfg-info">Configuración guardada. Pulse «Validar conexión» para comprobar la clave.</div>`;
  } catch (e) {
    est.innerHTML = `<div class="cfg-warn">Error al guardar: ${esc(e.message)}</div>`;
  }
}

async function validarConfig() {
  const est = document.getElementById("cfg-estado");
  est.innerHTML = `<div class="cfg-info"><span class="spinner spinner-dark"></span> Validando conexión con Gemini…</div>`;
  try {
    const res = await fetch(API + "/api/config/validar", { method: "POST" });
    const data = await res.json();
    if (data.ok) {
      const n = (data.modelos || []).length;
      est.innerHTML = `<div class="cfg-ok">✅ ${esc(data.mensaje)} Se detectaron ${n} modelos disponibles.</div>`;
    } else {
      est.innerHTML = `<div class="cfg-warn">❌ ${esc(data.mensaje)}</div>`;
    }
  } catch (e) {
    est.innerHTML = `<div class="cfg-warn">Error al validar: ${esc(e.message)}</div>`;
  }
}

async function borrarConfig() {
  if (!confirm("¿Borrar la API key guardada? El sistema pasará a modo RAG offline.")) return;
  const est = document.getElementById("cfg-estado");
  try {
    const res = await fetch(API + "/api/config", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ api_key: "" }),
    });
    CFG = await res.json();
    pintarEstadoIA();
    est.innerHTML = `<div class="cfg-warn">🗑️ API key borrada. Modo RAG offline activo.</div>`;
  } catch (e) {
    est.innerHTML = `<div class="cfg-warn">Error: ${esc(e.message)}</div>`;
  }
}

/* ---------- Formulario ---------- */
function leerFormulario() {
  const f = document.getElementById("form-predio");
  const data = {};
  new FormData(f).forEach((v, k) => { data[k] = v; });
  ["en_anp", "especie_nom059", "tiene_tecnico", "tiene_planos"].forEach((k) => {
    data[k] = f.querySelector(`[name="${k}"]`).checked;
  });
  ["superficie_ha", "densidad_ind_ha", "pct_maduros", "peso_tallo_kg", "vigencia_anios"].forEach((k) => {
    data[k] = parseFloat(data[k]);
  });
  return data;
}

/* ---------- Render de resultados ---------- */
function renderResultado(r) {
  const bloqueado = r.bloqueado || /NO PROCEDE/i.test(r.via_tramite);
  const esAuth = /AUTORIZ/i.test(r.via_tramite);
  let badge;
  if (bloqueado) badge = `<span class="badge badge-block">⛔ ${esc(r.via_tramite)}</span>`;
  else if (esAuth) badge = `<span class="badge badge-auth">⚖️ ${esc(r.via_tramite)}</span>`;
  else badge = `<span class="badge badge-aviso">✅ ${esc(r.via_tramite)}</span>`;
  const c = r.calculos;
  const anp = r.anp_detectada || [];

  let html = `
    <div class="result-head">
      <h2>Resultado del análisis</h2>${badge}
    </div>
    <p class="muted" style="margin-top:8px;">Trámite: <strong>${esc(r.tramite.clave)}</strong> — ${esc(r.tramite.nombre)}</p>
    <p class="muted">Fundamento: ${esc(r.tramite.fundamento)}</p>`;

  // --- Banner de detección geoespacial de ANP ---
  if (bloqueado) {
    html += `<div class="anp-block">
      <div class="anp-title">⛔ NO PROCEDE — Área Natural Protegida detectada</div>
      <div class="anp-msg">${esc(r.mensaje_bloqueo || "")}</div>
      <ul class="anp-list">${anp.map((a) => `<li><strong>${esc(a.nombre)}</strong> · ${esc(a.categoria)}${a.zona_nucleo_nombre ? " · Zona Núcleo: " + esc(a.zona_nucleo_nombre) : ""}<br><span class="anp-fund">${esc(a.fundamento)}</span></li>`).join("")}</ul>
      <div class="anp-src">Verificado con la cartografía de referencia (CONANP/CONABIO, EPSG:32611). Confirme con la capa oficial.</div>
    </div>`;
  } else if (anp.length) {
    html += `<div class="anp-warn">
      <div class="anp-title">⚠️ El predio cae dentro de un Área Natural Protegida</div>
      <div class="anp-msg">${esc((r.ubicacion && r.ubicacion.mensaje) || "")}</div>
      <ul class="anp-list">${anp.map((a) => `<li><strong>${esc(a.nombre)}</strong> · ${esc(a.categoria)}</li>`).join("")}</ul>
    </div>`;
  } else if (r.ubicacion && r.ubicacion.ok) {
    html += `<div class="anp-ok">✅ Ubicación verificada: no cae dentro de las ANP de referencia.</div>`;
  }

  if (bloqueado) {
    // No se muestran KPIs ni checklist: el aprovechamiento no puede autorizarse.
    if (r.advertencias && r.advertencias.length) {
      html += `<div class="section-title">Advertencias</div>`;
      r.advertencias.forEach((a) => { html += `<div class="advertencia">${esc(a)}</div>`; });
    }
    html += `<div class="section-title">Citas legales recuperadas (RAG)</div>`;
    (r.citas_legales || []).slice(0, 6).forEach((ct) => {
      html += `<div class="cita"><div class="fuente">${esc(ct.cita)}</div>
        <div class="txt">${esc(ct.texto).slice(0, 320)}…</div>
        <div class="score">relevancia ${ct.score}</div></div>`;
    });
    document.getElementById("resultado-card").innerHTML = html;
    return;
  }

  html += `
    <div class="kpis">
      <div class="kpi"><div class="v">${num(c.poblacion_total)}</div><div class="l">Población total</div></div>
      <div class="kpi"><div class="v">${num(c.ind_maduros)}</div><div class="l">Individuos maduros</div></div>
      <div class="kpi"><div class="v">${num(c.ind_aprovechables)}</div><div class="l">Aprovechables (${c.tasa_cosecha_pct}%)</div></div>
      <div class="kpi"><div class="v">${c.biomasa_total_t} t</div><div class="l">Biomasa total</div></div>
      <div class="kpi"><div class="v">${c.cosecha_anual_t} t</div><div class="l">Cosecha anual</div></div>
      <div class="kpi"><div class="v">${c.ciclo_corta} años</div><div class="l">Ciclo de corta</div></div>
    </div>`;

  if (r.advertencias && r.advertencias.length) {
    html += `<div class="section-title">Advertencias</div>`;
    r.advertencias.forEach((a) => { html += `<div class="advertencia">${esc(a)}</div>`; });
  }

  html += `<div class="section-title">Checklist de permisos y documentos</div><ul class="checklist">`;
  r.checklist.forEach((it) => {
    html += `<li class="${it.estado === "listo" ? "done" : ""}">
      <span class="box">${it.estado === "listo" ? "✓" : ""}</span>
      <span><span class="req">${esc(it.requisito)}</span>
      <span class="fund">${esc(it.fundamento)}</span></span></li>`;
  });
  html += `</ul>`;

  if (r.autorizaciones_adicionales && r.autorizaciones_adicionales.length) {
    html += `<div class="section-title">Autorizaciones adicionales</div>`;
    r.autorizaciones_adicionales.forEach((a) => { html += `<div class="advertencia">${esc(a)}</div>`; });
  }

  html += `<div class="section-title">Citas legales recuperadas (RAG)</div>`;
  (r.citas_legales || []).slice(0, 6).forEach((ct) => {
    html += `<div class="cita"><div class="fuente">${esc(ct.cita)}</div>
      <div class="txt">${esc(ct.texto).slice(0, 320)}…</div>
      <div class="score">relevancia ${ct.score}</div></div>`;
  });

  document.getElementById("resultado-card").innerHTML = html;
}

document.getElementById("form-predio").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = document.getElementById("btn-analizar");
  btn.disabled = true; btn.innerHTML = `<span class="spinner"></span> Analizando…`;
  try {
    const res = await fetch(API + "/api/analizar", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(leerFormulario()),
    });
    if (!res.ok) throw new Error("Error " + res.status);
    renderResultado(await res.json());
  } catch (err) {
    document.getElementById("resultado-card").innerHTML =
      `<div class="advertencia">No se pudo completar el análisis: ${esc(err.message)}</div>`;
  } finally {
    btn.disabled = false; btn.innerHTML = "🔎 Analizar predio";
  }
});

/* ---------- Verificación puntual de ubicación (ANP) ---------- */
document.getElementById("btn-verificar-ubicacion").addEventListener("click", async () => {
  const btn = document.getElementById("btn-verificar-ubicacion");
  const out = document.getElementById("ubicacion-result");
  const f = document.getElementById("form-predio");
  const texto = (f.querySelector('[name="coordenadas_geograficas"]') || {}).value || "";
  const texto_utm = (f.querySelector('[name="coordenadas_utm"]') || {}).value || "";
  if (!texto.trim() && !texto_utm.trim()) {
    out.innerHTML = `<div class="advertencia">Ingrese coordenadas geográficas (lat, lon) o UTM para verificar la ubicación.</div>`;
    return;
  }
  btn.disabled = true; const prev = btn.innerHTML; btn.innerHTML = `<span class="spinner"></span> Verificando…`;
  try {
    const res = await fetch(API + "/api/ubicacion", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ texto, texto_utm }),
    });
    if (!res.ok) throw new Error("Error " + res.status);
    const u = await res.json();
    if (!u.ok) {
      out.innerHTML = `<div class="advertencia">${esc(u.error || "No se pudieron interpretar las coordenadas.")}</div>`;
    } else if (u.dentro_anp && u.prohibido) {
      out.innerHTML = `<div class="anp-block">
        <div class="anp-title">⛔ NO PROCEDE — Área Natural Protegida</div>
        <div class="anp-msg">${esc(u.mensaje)}</div>
        <ul class="anp-list">${(u.anp || []).map((a) => `<li><strong>${esc(a.nombre)}</strong> · ${esc(a.categoria)}</li>`).join("")}</ul>
        <div class="anp-src">Lat ${u.lat}, Lon ${u.lon} · UTM ${u.utm.zona}${u.utm.hemisferio} X=${u.utm.este} Y=${u.utm.norte} · ${esc(u.epsg)}</div>
      </div>`;
    } else if (u.dentro_anp) {
      out.innerHTML = `<div class="anp-warn">
        <div class="anp-title">⚠️ Dentro de ANP (restricción parcial)</div>
        <div class="anp-msg">${esc(u.mensaje)}</div>
      </div>`;
    } else {
      out.innerHTML = `<div class="anp-ok">✅ ${esc(u.mensaje)}<br><span class="anp-src">Lat ${u.lat}, Lon ${u.lon} · UTM ${u.utm.zona}${u.utm.hemisferio} X=${u.utm.este} Y=${u.utm.norte}</span></div>`;
    }
  } catch (err) {
    out.innerHTML = `<div class="advertencia">No se pudo verificar la ubicación: ${esc(err.message)}</div>`;
  } finally {
    btn.disabled = false; btn.innerHTML = prev;
  }
});

/* ==========================================================================
   CHAT RAG + IA
   ========================================================================== */
const chatWin = document.getElementById("chat-window");
function addMsg(cls, html) {
  const d = document.createElement("div");
  d.className = "msg " + cls;
  d.innerHTML = html;
  chatWin.appendChild(d);
  chatWin.scrollTop = chatWin.scrollHeight;
  return d;
}

function fuentesHtml(fuentes) {
  let html = `<details class="fuentes"><summary>📎 Fuentes legales recuperadas (${(fuentes || []).length})</summary>`;
  (fuentes || []).forEach((f) => {
    html += `<div class="fuente">📌 ${esc(f.cita)} <span class="score">(${f.score})</span></div>
      <div class="txt">${esc(f.texto).slice(0, 360)}…</div>`;
  });
  html += `</details>`;
  return html;
}

async function preguntar(q) {
  if (!q.trim()) return;
  addMsg("user", esc(q));
  const usarIA = document.getElementById("chat-usar-ia").checked;
  const typing = addMsg("bot", `<span class="typing">${usarIA ? "Consultando la IA y el corpus normativo…" : "Buscando en el corpus normativo…"}</span>`);
  try {
    const res = await fetch(API + "/api/chat", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pregunta: q, usar_ia: usarIA }),
    });
    const data = await res.json();
    let html = "";

    if (data.modo === "gemini" && data.respuesta) {
      html += `<div class="ia-tag">✨ Respuesta generada con Gemini (${esc(CFG.modelo)})</div>`;
      html += `<div class="ia-respuesta">${mdToHtml(data.respuesta)}</div>`;
    } else if (data.modo === "error") {
      html += `<div class="advertencia">Error de la IA: ${esc(data.error || "desconocido")}. Se muestran las fuentes recuperadas.</div>`;
    } else if (data.modo === "offline" || !data.respuesta) {
      html += `<div class="ia-tag offline">📚 Modo RAG (sin IA). Estas son las disposiciones más relevantes del corpus legal:</div>`;
    }
    html += fuentesHtml(data.fuentes);
    typing.innerHTML = html;
  } catch (err) {
    typing.innerHTML = `<div class="advertencia">Error al consultar: ${esc(err.message)}</div>`;
  }
}

document.getElementById("btn-chat").addEventListener("click", () => {
  const inp = document.getElementById("chat-q");
  preguntar(inp.value); inp.value = "";
});
document.getElementById("chat-q").addEventListener("keydown", (e) => {
  if (e.key === "Enter") { preguntar(e.target.value); e.target.value = ""; }
});
document.querySelectorAll("[data-q]").forEach((b) =>
  b.addEventListener("click", () => preguntar(b.dataset.q)));

/* ==========================================================================
   GENERADOR (plantilla + IA)
   ========================================================================== */
let ULTIMO_MD = "";      // último markdown generado (plantilla o IA)
let ULTIMO_ES_IA = false;

function botonesDescarga() {
  const fmt = ["pdf", "docx", "html", "md"];
  const etq = { pdf: "PDF", docx: "DOCX", html: "HTML", md: "Markdown" };
  const ico = { pdf: "⬇️", docx: "⬇️", html: "⬇️", md: "⬇️" };
  return fmt.map((f) => `<button class="btn ${f === "pdf" ? "btn-primary" : "btn-ghost"}" data-dl="${f}">${ico[f]} ${etq[f]}</button>`).join("");
}

function renderDocumento(md, esIA) {
  ULTIMO_MD = md; ULTIMO_ES_IA = esIA;
  const area = document.getElementById("doc-area");
  const tag = esIA
    ? `<div class="ia-tag">✨ Documento redactado con IA (Gemini · ${esc(CFG.modelo)})</div>`
    : `<div class="ia-tag offline">📄 Documento generado con la plantilla determinista</div>`;
  area.innerHTML = `
    ${tag}
    <div class="download-bar">${botonesDescarga()}</div>
    <div class="section-title">Vista previa del documento</div>
    <div class="doc-preview">${mdToHtml(md)}</div>`;
  area.querySelectorAll("[data-dl]").forEach((b) =>
    b.addEventListener("click", () => descargarDoc(b.dataset.dl)));
}

async function generarDoc(conIA) {
  const btn = document.getElementById(conIA ? "btn-generar-ia" : "btn-generar");
  const orig = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = `<span class="spinner"></span> ${conIA ? "Redactando con IA…" : "Generando…"}`;
  const area = document.getElementById("doc-area");
  try {
    const url = conIA ? "/api/generar-ia" : "/api/generar";
    const res = await fetch(API + url, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(leerFormulario()),
    });
    if (!res.ok) throw new Error("Error " + res.status);
    const data = await res.json();
    const md = data.markdown || data.base_markdown || "";
    const esIA = data.modo === "gemini";
    renderDocumento(md, esIA);
    if (data.aviso) {
      area.insertAdjacentHTML("afterbegin", `<div class="advertencia">${esc(data.aviso)}</div>`);
    }
    if (data.error) {
      area.insertAdjacentHTML("afterbegin", `<div class="advertencia">Error de la IA: ${esc(data.error)}. Se usó la plantilla.</div>`);
    }
  } catch (err) {
    area.innerHTML = `<div class="advertencia">No se pudo generar el documento: ${esc(err.message)}</div>`;
  } finally {
    btn.disabled = false; btn.innerHTML = orig;
  }
}

async function descargarDoc(fmt) {
  if (!ULTIMO_MD) return;
  // Para documentos de plantilla, usar los enlaces directos del backend.
  if (!ULTIMO_ES_IA && fmt !== "md") {
    window.location.href = API + "/api/descargar/" + fmt;
    return;
  }
  // Para documentos IA (o Markdown), exportar el texto por POST y descargar blob.
  try {
    const res = await fetch(API + "/api/exportar", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ markdown: ULTIMO_MD, formato: fmt, nombre: "PMF_generado_ia" }),
    });
    if (!res.ok) throw new Error("Error " + res.status);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "PMF_generado_ia." + fmt;
    document.body.appendChild(a); a.click(); a.remove();
    URL.revokeObjectURL(url);
  } catch (err) {
    alert("No se pudo descargar el documento: " + err.message);
  }
}

document.getElementById("btn-generar").addEventListener("click", () => generarDoc(false));
document.getElementById("btn-generar-ia").addEventListener("click", () => generarDoc(true));

/* ==========================================================================
   CONFIGURACIÓN — listeners
   ========================================================================== */
document.getElementById("btn-status").addEventListener("click", () => activarTab("config"));
document.getElementById("btn-guardar-cfg").addEventListener("click", guardarConfig);
document.getElementById("btn-validar-cfg").addEventListener("click", validarConfig);
document.getElementById("btn-borrar-cfg").addEventListener("click", borrarConfig);
document.getElementById("btn-toggle-key").addEventListener("click", () => {
  const inp = document.getElementById("cfg-apikey");
  inp.type = inp.type === "password" ? "text" : "password";
});
document.getElementById("cfg-apikey").addEventListener("keydown", (e) => {
  if (e.key === "Enter") guardarConfig();
});

/* ==========================================================================
   MÓDULO D — Plano georreferenciado (Shapefile / GeoPDF)
   ========================================================================== */
const EJEMPLO_POLIGONO = `30.5000, -115.9000
30.5000, -115.8896
30.5090, -115.8896
30.5090, -115.9000`;

const EJEMPLO_AREAS = `# Área 1 — Cuadrante SO | Aprovechamiento | Anualidad 1
30.5004, -115.8996
30.5004, -115.8950
30.5043, -115.8950
30.5043, -115.8996

# Área 2 — Cuadrante SE | Aprovechamiento | Anualidad 1
30.5004, -115.8946
30.5004, -115.8900
30.5043, -115.8900
30.5043, -115.8946

# Área 3 — Cuadrante NE | Aprovechamiento | Anualidad 2
30.5047, -115.8946
30.5047, -115.8900
30.5086, -115.8900
30.5086, -115.8946

# Área 4 — Cuadrante NO | Aprovechamiento | Anualidad 2
30.5047, -115.8996
30.5047, -115.8950
30.5086, -115.8950
30.5086, -115.8996

# Franja de conservación (arroyo) | Conservación |
30.5004, -115.8950
30.5004, -115.8946
30.5086, -115.8946
30.5086, -115.8950`;

function parseAreasTexto(texto) {
  const areas = [];
  let actual = null;
  (texto || "").split("\n").forEach((linea) => {
    const l = linea.trim();
    if (!l) return;
    if (l.startsWith("#")) {
      const p = l.replace(/^#\s*/, "").split("|").map((s) => s.trim());
      actual = { nombre: p[0] || "Área", tipo: p[1] || "Aprovechamiento", anualidad: p[2] || "", vertices_texto: "" };
      areas.push(actual);
    } else {
      if (!actual) {
        actual = { nombre: "Área", tipo: "Aprovechamiento", anualidad: "", vertices_texto: "" };
        areas.push(actual);
      }
      actual.vertices_texto += l + "\n";
    }
  });
  return areas;
}

function cargarEjemploPlano() {
  document.getElementById("pl-poligono").value = EJEMPLO_POLIGONO;
  document.getElementById("pl-areas").value = EJEMPLO_AREAS;
}

function renderPlano(d) {
  const out = document.getElementById("plano-resultado");
  const geo = d.georreferenciado ? "✅ Sí (OGC GeoPDF)" : "⚠️ PDF sin georreferenciación (GDAL no disponible)";
  const areas = (d.areas || [])
    .map((a) => `<li>${esc(a.nombre)} — <b>${a.superficie_ha} ha</b> (${esc(a.tipo)})</li>`)
    .join("");
  out.innerHTML = `
    <div class="plano-meta">
      <div><b>Predio:</b> ${esc(d.predio_nombre || d.nombre)}</div>
      <div><b>Sistema:</b> ${esc(d.sistema)}</div>
      <div><b>Escala aprox.:</b> ${esc(d.escala)}</div>
      <div><b>Superficie del predio:</b> ${d.superficie_predio_ha} ha</div>
      <div><b>Superficie de aprovechamiento:</b> ${d.superficie_aprovechamiento_ha} ha</div>
      <div><b>Georreferenciado:</b> ${geo}</div>
    </div>
    <h3 style="font-size:.95rem;color:var(--verde-700);margin:12px 0 6px;">Áreas (${d.num_areas})</h3>
    <ul style="font-size:.82rem;color:var(--gris-700);margin-left:18px;">${areas}</ul>
    <div class="actions" style="margin-top:14px;">
      <button class="btn btn-primary" data-pl="${d.descargas.geopdf}">🗺️ GeoPDF</button>
      <button class="btn btn-ghost" data-pl="${d.descargas.shp}">📦 Shapefile (ZIP)</button>
      <button class="btn btn-ghost" data-pl="${d.descargas.geojson}">🌐 GeoJSON</button>
      <button class="btn btn-ghost" data-pl="${d.descargas.png}">🖼️ PNG</button>
    </div>
    <img class="plano-preview" src="${API}${d.descargas.png}?t=${Date.now()}" alt="Vista previa del plano">
  `;
  out.querySelectorAll("[data-pl]").forEach((b) =>
    b.addEventListener("click", () => { window.location.href = API + b.dataset.pl; }));
}

async function generarPlano() {
  const btn = document.getElementById("btn-plano");
  const est = document.getElementById("plano-estado");
  const payload = {
    predio_nombre: document.getElementById("pl-predio").value,
    promovente: document.getElementById("pl-promovente").value,
    municipio: document.getElementById("pl-municipio").value,
    estado: "Baja California",
    tecnico: document.getElementById("pl-tecnico").value,
    registro_tecnico: document.getElementById("pl-registro").value,
    sistema_coordenadas: document.getElementById("pl-sistema").value,
    poligono_texto: document.getElementById("pl-poligono").value,
    areas: parseAreasTexto(document.getElementById("pl-areas").value),
  };
  if (!payload.poligono_texto.trim()) {
    est.textContent = "⚠️ Ingrese los vértices del polígono del predio.";
    return;
  }
  btn.disabled = true;
  est.textContent = "⏳ Generando plano (Shapefile + GeoPDF)…";
  try {
    const res = await fetch(API + "/api/plano", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || ("Error " + res.status));
    est.textContent = "✅ Plano generado correctamente.";
    renderPlano(data);
  } catch (err) {
    est.textContent = "❌ " + err.message;
  } finally {
    btn.disabled = false;
  }
}

document.getElementById("btn-plano").addEventListener("click", generarPlano);
document.getElementById("btn-plano-ejemplo").addEventListener("click", cargarEjemploPlano);
cargarEjemploPlano();

/* ---------- Init ---------- */
cargarConfig();
