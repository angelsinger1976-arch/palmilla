#!/usr/bin/env bash
# =============================================================================
#  🌵 PalmillaBot — Instalador integral  «llevatodo.sh»
# =============================================================================
#  Deja el sistema 100 % listo para ejecutar PalmillaBot SIN fallas.
#
#  Verifica e instala TODO lo que el proyecto necesita:
#    · Herramientas base .............. git, curl
#    · Python 3.9+ y entorno virtual .. ./venv
#    · Dependencias de Python ......... FastAPI, uvicorn, pydantic,
#                                       scikit-learn, numpy, python-docx,
#                                       Markdown, geopandas, shapely, pyproj,
#                                       matplotlib, requests
#    · GDAL ........................... GeoPDF georreferenciado (Módulo D)
#    · wkhtmltopdf .................... exportación del PMF a PDF (Módulo C)
#    · (Opcional) API key de Google Gemini
#    · Autoprueba de extremo a extremo (smoke test)
#
#  Uso:
#      chmod +x llevatodo.sh
#      ./llevatodo.sh                 # instalación interactiva
#      ./llevatodo.sh --yes           # sin preguntas: instala todo lo que falte
#      ./llevatodo.sh --skip-system   # no toca paquetes del sistema
#      ./llevatodo.sh --no-ia         # no configura la API key de Gemini
#      ./llevatodo.sh --help
#
#  Es idempotente: puedes ejecutarlo tantas veces como quieras.
# =============================================================================

set -uo pipefail

# -----------------------------------------------------------------------------
#  Presentación
# -----------------------------------------------------------------------------
BOLD=$'\033[1m'; DIM=$'\033[2m'; RESET=$'\033[0m'
GREEN=$'\033[32m'; YELLOW=$'\033[33m'; RED=$'\033[31m'
BLUE=$'\033[34m'; CYAN=$'\033[36m'; MAGENTA=$'\033[35m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
VENV_DIR="$SCRIPT_DIR/venv"
CONFIG_FILE="$SCRIPT_DIR/config.json"
REQ_FILE="$SCRIPT_DIR/requirements.txt"
LOG_FILE="$SCRIPT_DIR/llevatodo.log"

log() { printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >> "$LOG_FILE" 2>/dev/null || true; }
info()  { printf "${BLUE}ℹ️  %s${RESET}\n" "$*"; log "INFO  $*"; }
ok()    { printf "${GREEN}✅ %s${RESET}\n" "$*"; log "OK    $*"; }
warn()  { printf "${YELLOW}⚠️  %s${RESET}\n" "$*"; log "WARN  $*"; }
err()   { printf "${RED}❌ %s${RESET}\n" "$*" >&2; log "ERROR $*"; }
title() { printf "\n${BOLD}${CYAN}%s${RESET}\n" "$*"; log "---- $* ----"; }
paso()  { printf "\n${BOLD}${MAGENTA}▶ %s${RESET}\n" "$*"; log "== $* =="; }

# -----------------------------------------------------------------------------
#  Opciones
# -----------------------------------------------------------------------------
ASSUME_YES=0
SKIP_SYSTEM=0
CONFIG_IA=1

uso() {
  awk 'NR>1 && /^#/ {sub(/^# ?/,""); print} NR>1 && !/^#/ && !/^$/ {exit}' "${BASH_SOURCE[0]}"
  exit 0
}

while [ $# -gt 0 ]; do
  case "$1" in
    -y|--yes)        ASSUME_YES=1 ;;
    --skip-system)   SKIP_SYSTEM=1 ;;
    --no-ia)         CONFIG_IA=0 ;;
    -h|--help)       uso ;;
    *) err "Opción desconocida: $1"; echo "Usa ./llevatodo.sh --help"; exit 2 ;;
  esac
  shift
done

# -----------------------------------------------------------------------------
#  Utilidades
# -----------------------------------------------------------------------------
confirmar() {  # devuelve 0 si el usuario confirma
  local pregunta="$1"
  if [ "$ASSUME_YES" -eq 1 ]; then return 0; fi
  if [ ! -t 0 ]; then return 1; fi
  printf "${BOLD}%s [s/N]: ${RESET}" "$pregunta"
  local r; read -r r || r="n"
  case "$r" in s|S|si|Sí|sí|y|Y) return 0 ;; *) return 1 ;; esac
}

tiene() { command -v "$1" >/dev/null 2>&1; }

# Resumen ordenado de componentes
RESUMEN=()
resumen_add() { RESUMEN+=("$1|$2"); }

FALLOS_CRITICOS=0

# -----------------------------------------------------------------------------
#  Encabezado
# -----------------------------------------------------------------------------
clear 2>/dev/null || true
printf "${BOLD}${CYAN}"
cat <<'BANNER'
  🌵  PalmillaBot — Instalador integral «llevatodo.sh»
  ──────────────────────────────────────────────────────
BANNER
printf "${RESET}"
printf "${DIM}Directorio del proyecto: %s${RESET}\n" "$SCRIPT_DIR"
printf "${DIM}Registro de instalación: %s${RESET}\n" "$LOG_FILE"
: > "$LOG_FILE" 2>/dev/null || true
log "Inicio de la instalación en $SCRIPT_DIR"

# =============================================================================
#  1) Sistema operativo y gestor de paquetes
# =============================================================================
paso "Paso 1/10 · Detectando el sistema operativo y el gestor de paquetes"
OS="$(uname -s)"
GESTOR=""
case "$OS" in
  Darwin)
    SO_NOMBRE="macOS $(sw_vers -productVersion 2>/dev/null || echo '')"
    if tiene brew; then GESTOR="brew"; ok "Homebrew detectado: $(brew --version 2>/dev/null | head -1)"; else warn "Homebrew no está instalado."; fi
    ;;
  Linux)
    SO_NOMBRE="Linux ($( (. /etc/os-release 2>/dev/null && printf '%s' "${PRETTY_NAME:-}") || echo 'desconocido'))"
    if tiene apt-get; then GESTOR="apt"; ok "apt-get detectado."; elif tiene dnf; then GESTOR="dnf"; ok "dnf detectado."; elif tiene yum; then GESTOR="yum"; ok "yum detectado."; else warn "No se detectó un gestor de paquetes conocido."; fi
    ;;
  *)
    SO_NOMBRE="$OS"; warn "Sistema no reconocido: $OS (se intentará continuar)."
    ;;
esac
ok "Sistema operativo: $SO_NOMBRE"
resumen_add "Sistema operativo" "$SO_NOMBRE"

# Instalar Homebrew si falta (solo macOS)
if [ "$OS" = "Darwin" ] && [ -z "$GESTOR" ]; then
  if confirmar "¿Instalar Homebrew ahora? (necesario para GDAL y wkhtmltopdf)"; then
    info "Instalando Homebrew (puede tardar unos minutos) …"
    if /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"; then
      # Cargar brew en el PATH (Apple Silicon e Intel)
      if [ -x /opt/homebrew/bin/brew ]; then eval "$(/opt/homebrew/bin/brew shellenv)"; fi
      if [ -x /usr/local/bin/brew ]; then eval "$(/usr/local/bin/brew shellenv)"; fi
      if tiene brew; then GESTOR="brew"; ok "Homebrew instalado."; else warn "Homebrew se instaló pero no está en el PATH de esta sesión."; fi
    else
      warn "No se pudo instalar Homebrew automáticamente. Instálalo desde https://brew.sh"
    fi
  else
    warn "Omitido. Sin Homebrew no se podrán instalar GDAL ni wkhtmltopdf automáticamente."
  fi
fi

# -----------------------------------------------------------------------------
#  Función de instalación de paquetes del sistema
# -----------------------------------------------------------------------------
instalar_paquete() {
  local pkg="$1"
  if [ "$SKIP_SYSTEM" -eq 1 ]; then warn "Omitido (--skip-system): $pkg"; return 1; fi
  case "$GESTOR" in
    brew) brew install "$pkg" ;;
    apt)  sudo apt-get update && sudo apt-get install -y "$pkg" ;;
    dnf)  sudo dnf install -y "$pkg" ;;
    yum)  sudo yum install -y "$pkg" ;;
    *)    err "No hay gestor de paquetes disponible para instalar '$pkg'."; return 1 ;;
  esac
}

instalar_cask() {  # solo macOS
  local pkg="$1"
  if [ "$SKIP_SYSTEM" -eq 1 ]; then warn "Omitido (--skip-system): $pkg"; return 1; fi
  case "$GESTOR" in
    brew) brew install --cask "$pkg" ;;
    *)    err "No se puede instalar el paquete de sistema '$pkg' en este SO."; return 1 ;;
  esac
}

# =============================================================================
#  2) Herramientas base: git y curl
# =============================================================================
paso "Paso 2/10 · Comprobando herramientas base (git, curl)"
for t in git curl; do
  if tiene "$t"; then
    ok "$t disponible ($(command -v "$t"))"
  else
    warn "$t no encontrado."
    if confirmar "¿Instalar $t?"; then
      if instalar_paquete "$t"; then ok "$t instalado."; else warn "No se pudo instalar $t (puede no ser imprescindible)."; fi
    fi
  fi
done

# =============================================================================
#  3) Python 3.9+
# =============================================================================
paso "Paso 3/10 · Buscando Python 3 (>= 3.9)"
PYTHON_BIN=""
detectar_python() {
  local cand
  for cand in python3.13 python3.12 python3.11 python3.10 python3.9 python3; do
    if tiene "$cand" && "$cand" -c 'import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)' 2>/dev/null; then
      PYTHON_BIN="$cand"; return 0
    fi
  done
  return 1
}

if detectar_python; then
  ok "Python encontrado: $PYTHON_BIN ($("$PYTHON_BIN" -c 'import platform; print(platform.python_version())'))"
else
  warn "No se encontró Python 3.9 o superior."
  if confirmar "¿Instalar Python 3 ahora?"; then
    if [ "$GESTOR" = "brew" ]; then instalar_paquete python@3.12
    elif [ "$GESTOR" = "apt" ]; then instalar_paquete python3 python3-venv python3-pip
    elif [ "$GESTOR" = "dnf" ] || [ "$GESTOR" = "yum" ]; then instalar_paquete python3
    fi
    hash -r 2>/dev/null || true
    detectar_python || true
  fi
fi

if [ -z "$PYTHON_BIN" ]; then
  err "Python 3.9+ es imprescindible y no está disponible."
  echo "   · macOS:  brew install python@3.12"
  echo "   · Linux:  sudo apt-get install python3 python3-venv python3-pip"
  echo "   · Web:    https://www.python.org/downloads/"
  resumen_add "Python 3.9+" "FALTA (crítico)"
  FALLOS_CRITICOS=1
else
  resumen_add "Python 3.9+" "$("$PYTHON_BIN" -c 'import platform; print(platform.python_version())') ($PYTHON_BIN)"
fi

# =============================================================================
#  4) Entorno virtual
# =============================================================================
paso "Paso 4/10 · Preparando el entorno virtual (./venv)"
if [ -x "$VENV_DIR/bin/python" ]; then
  ok "El entorno virtual ya existe (se reutiliza)."
  resumen_add "Entorno virtual" "reutilizado"
else
  if [ -z "$PYTHON_BIN" ]; then
    err "No se puede crear el entorno virtual sin Python."
    resumen_add "Entorno virtual" "FALTA (crítico)"
    FALLOS_CRITICOS=1
  else
    info "Creando entorno virtual en ./venv …"
    if "$PYTHON_BIN" -m venv "$VENV_DIR"; then
      ok "Entorno virtual creado."
      resumen_add "Entorno virtual" "creado"
    else
      err "No se pudo crear el entorno virtual."
      echo "   En Debian/Ubuntu puede faltar el paquete: sudo apt-get install python3-venv"
      resumen_add "Entorno virtual" "FALLO (crítico)"
      FALLOS_CRITICOS=1
    fi
  fi
fi

if [ -x "$VENV_DIR/bin/python" ]; then
  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
  ok "Entorno virtual activado ($(python --version 2>&1))."
fi

# =============================================================================
#  5) Dependencias de Python
# =============================================================================
paso "Paso 5/10 · Instalando dependencias de Python (requirements.txt)"
if [ -x "$VENV_DIR/bin/python" ]; then
  if [ -f "$REQ_FILE" ]; then
    info "Actualizando pip, setuptools y wheel …"
    python -m pip install --quiet --upgrade pip setuptools wheel 2>&1 | tail -3 || warn "No se pudo actualizar pip (se continúa)."
    info "Instalando dependencias (puede tardar varios minutos la primera vez) …"
    if python -m pip install --upgrade -r "$REQ_FILE"; then
      ok "Dependencias instaladas/actualizadas."
      resumen_add "Dependencias Python" "instaladas"
    else
      warn "Algunas dependencias fallaron; se reintentará individualmente en la verificación."
      resumen_add "Dependencias Python" "con avisos"
    fi
  else
    err "No se encontró requirements.txt en $SCRIPT_DIR"
    resumen_add "Dependencias Python" "FALTA requirements.txt"
    FALLOS_CRITICOS=1
  fi
else
  err "No hay entorno virtual; se omiten las dependencias de Python."
  resumen_add "Dependencias Python" "OMITIDO (sin venv)"
  FALLOS_CRITICOS=1
fi

# =============================================================================
#  6) Verificación de imports de Python
# =============================================================================
paso "Paso 6/10 · Verificando que cada librería de Python importe"
# módulo_import -> nombre_pip
MODULOS=(
  "fastapi:fastapi"
  "uvicorn:uvicorn"
  "pydantic:pydantic"
  "sklearn:scikit-learn"
  "numpy:numpy"
  "docx:python-docx"
  "markdown:Markdown"
  "geopandas:geopandas"
  "shapely:shapely"
  "pyproj:pyproj"
  "matplotlib:matplotlib"
  "requests:requests"
)
FALTAN=()
if [ -x "$VENV_DIR/bin/python" ]; then
  for par in "${MODULOS[@]}"; do
    mod="${par%%:*}"; pipname="${par##*:}"
    if python -c "import $mod" >/dev/null 2>&1; then
      printf "${GREEN}   ✅ %-12s${RESET} (pip: %s)\n" "$mod" "$pipname"
    else
      printf "${RED}   ❌ %-12s${RESET} (pip: %s)\n" "$mod" "$pipname"
      FALTAN+=("$pipname")
    fi
  done

  if [ ${#FALTAN[@]} -gt 0 ]; then
    warn "Faltan ${#FALTAN[@]} librería(s): ${FALTAN[*]}"
    info "Reintentando su instalación individual …"
    for pipname in "${FALTAN[@]}"; do
      python -m pip install --upgrade "$pipname" >/dev/null 2>&1 || warn "No se pudo instalar $pipname"
    done
    # Reverificar
    FALTAN2=()
    for par in "${MODULOS[@]}"; do
      mod="${par%%:*}"; pipname="${par##*:}"
      python -c "import $mod" >/dev/null 2>&1 || FALTAN2+=("$pipname")
    done
    if [ ${#FALTAN2[@]} -eq 0 ]; then
      ok "Todas las librerías quedaron instaladas tras el reintento."
      resumen_add "Librerías Python" "todas OK"
    else
      err "Aún faltan: ${FALTAN2[*]}"
      resumen_add "Librerías Python" "faltan: ${FALTAN2[*]}"
      FALLOS_CRITICOS=1
    fi
  else
    ok "Las 12 librerías de Python están presentes."
    resumen_add "Librerías Python" "todas OK"
  fi
else
  warn "Sin entorno virtual: no se pueden verificar las librerías."
  resumen_add "Librerías Python" "OMITIDO (sin venv)"
fi

# =============================================================================
#  7) GDAL (GeoPDF georreferenciado — Módulo D)
# =============================================================================
paso "Paso 7/10 · Comprobando GDAL (plano GeoPDF georreferenciado)"
gdal_cli=0; gdal_py=0
tiene gdal_translate && gdal_cli=1
[ -x "$VENV_DIR/bin/python" ] && python -c "from osgeo import gdal" >/dev/null 2>&1 && gdal_py=1

if [ "$gdal_cli" -eq 1 ] || [ "$gdal_py" -eq 1 ]; then
  [ "$gdal_cli" -eq 1 ] && ok "gdal_translate disponible: $(gdal_translate --version 2>/dev/null | head -1)"
  [ "$gdal_py" -eq 1 ] && ok "Bindings de Python (osgeo) disponibles."
  resumen_add "GDAL" "disponible"
else
  warn "GDAL no está instalado."
  echo "   Es necesario para el GeoPDF georreferenciado (Módulo D)."
  echo "   Sin GDAL, el Shapefile y el GeoJSON se generan igualmente."
  if confirmar "¿Instalar GDAL ahora?"; then
    if [ "$GESTOR" = "brew" ]; then
      instalar_paquete gdal && hash -r 2>/dev/null || true
    elif [ "$GESTOR" = "apt" ]; then
      instalar_paquete gdal-bin python3-gdal && hash -r 2>/dev/null || true
    elif [ "$GESTOR" = "dnf" ] || [ "$GESTOR" = "yum" ]; then
      instalar_paquete gdal && hash -r 2>/dev/null || true
    fi
    if tiene gdal_translate || { [ -x "$VENV_DIR/bin/python" ] && python -c "from osgeo import gdal" >/dev/null 2>&1; }; then
      ok "GDAL instalado correctamente."
      resumen_add "GDAL" "instalado"
    else
      warn "No se pudo confirmar la instalación de GDAL."
      resumen_add "GDAL" "no disponible (opcional)"
    fi
  else
    warn "Omitido. Instálalo cuando quieras: brew install gdal  (macOS)  |  sudo apt-get install gdal-bin python3-gdal  (Linux)"
    resumen_add "GDAL" "no disponible (opcional)"
  fi
fi

# =============================================================================
#  8) wkhtmltopdf (exportación del PMF a PDF — Módulo C)
# =============================================================================
paso "Paso 8/10 · Comprobando wkhtmltopdf (exportación del PMF a PDF)"
if tiene wkhtmltopdf; then
  ok "wkhtmltopdf disponible ($(wkhtmltopdf --version 2>/dev/null | head -1))."
  resumen_add "wkhtmltopdf" "disponible"
else
  warn "wkhtmltopdf no está instalado."
  echo "   Es necesario para exportar el Programa de Manejo a PDF."
  echo "   Sin él, podrás descargar en DOCX, HTML y Markdown."
  if confirmar "¿Instalar wkhtmltopdf ahora?"; then
    if [ "$GESTOR" = "brew" ]; then
      instalar_cask wkhtmltopdf
    elif [ "$GESTOR" = "apt" ]; then
      instalar_paquete wkhtmltopdf
    elif [ "$GESTOR" = "dnf" ] || [ "$GESTOR" = "yum" ]; then
      instalar_paquete wkhtmltopdf
    fi
    if tiene wkhtmltopdf; then
      ok "wkhtmltopdf instalado correctamente."
      resumen_add "wkhtmltopdf" "instalado"
    else
      warn "No se pudo confirmar la instalación de wkhtmltopdf."
      resumen_add "wkhtmltopdf" "no disponible (opcional)"
    fi
  else
    warn "Omitido. Instálalo cuando quieras: brew install --cask wkhtmltopdf  (macOS)  |  sudo apt-get install wkhtmltopdf  (Linux)"
    resumen_add "wkhtmltopdf" "no disponible (opcional)"
  fi
fi

# =============================================================================
#  9) API key de Google Gemini (opcional)
# =============================================================================
paso "Paso 9/10 · Configuración de la IA (Google Gemini)"
IA_ESTADO="modo RAG offline (sin IA)"
if [ "$CONFIG_IA" -eq 1 ]; then
  # ¿Ya hay una key configurada?
  KEY_EXISTE=0
  if [ -n "${GEMINI_API_KEY:-}" ]; then KEY_EXISTE=1; fi
  if [ -f "$CONFIG_FILE" ] && grep -q '"gemini_api_key"[[:space:]]*:[[:space:]]*"[^"]' "$CONFIG_FILE" 2>/dev/null; then KEY_EXISTE=1; fi

  if [ "$KEY_EXISTE" -eq 1 ]; then
    ok "Ya hay una API key de Gemini configurada (se conserva)."
    IA_ESTADO="configurada"
  else
    echo "   PalmillaBot puede usar la IA de Google Gemini para redactar respuestas"
    echo "   y el Programa de Manejo. La API key es GRATUITA (Google AI Studio)."
    if confirmar "¿Configurar la API key de Gemini ahora?"; then
      echo "   Obtén tu API key en: ${BOLD}https://aistudio.google.com/app/apikey${RESET}"
      printf "   Pega tu API key (o Enter para omitir): "
      read -r API_KEY || API_KEY=""
      if [ -n "${API_KEY:-}" ] && [ -x "$VENV_DIR/bin/python" ]; then
        python - "$CONFIG_FILE" "$API_KEY" <<'PYEOF'
import json, os, sys
path, key = sys.argv[1], sys.argv[2]
data = {}
if os.path.exists(path):
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh) or {}
    except Exception:
        data = {}
data["gemini_api_key"] = key.strip()
data.setdefault("gemini_model", "gemini-2.0-flash")
with open(path, "w", encoding="utf-8") as fh:
    json.dump(data, fh, ensure_ascii=False, indent=2)
os.chmod(path, 0o600)
PYEOF
        ok "API key guardada en config.json (permisos 600)."
        IA_ESTADO="configurada"
      else
        warn "No se guardó ninguna API key. Podrás añadirla desde la interfaz (⚙️ Configuración)."
      fi
    else
      info "Omitido. Podrás configurarla luego desde la interfaz (⚙️ Configuración)."
    fi
  fi
else
  info "Omitido por --no-ia."
fi
resumen_add "IA (Gemini)" "$IA_ESTADO"

# =============================================================================
#  10) Autoprueba (smoke test)
# =============================================================================
paso "Paso 10/10 · Autoprueba de extremo a extremo"
if [ -x "$VENV_DIR/bin/python" ]; then
  # 10a. Importar el backend
  if python -c "import sys; sys.path.insert(0,'src'); import app" >/dev/null 2>&1; then
    ok "El backend (src/app.py) importa correctamente."
    resumen_add "Backend FastAPI" "OK"
  else
    warn "El backend no importa; revisa las dependencias."
    resumen_add "Backend FastAPI" "con avisos"
  fi

  # 10b. Generar un plano de ejemplo (Módulo D)
  if python - <<'PYEOF' >/dev/null 2>&1
import sys, tempfile
sys.path.insert(0, "src")
from plano_geo import datos_ejemplo, generar_plano
r = generar_plano(datos_ejemplo(), tempfile.mkdtemp(), nombre="smoke")
sys.exit(0 if r.get("ok") else 1)
PYEOF
  then
    ok "El Módulo D genera un plano de ejemplo correctamente."
    resumen_add "Módulo D (plano)" "OK"
  else
    warn "El Módulo D no pudo generar el plano de ejemplo (revisa geopandas/shapely)."
    resumen_add "Módulo D (plano)" "con avisos"
  fi
else
  warn "Sin entorno virtual: se omite la autoprueba."
fi

# =============================================================================
#  Resumen final
# =============================================================================
title "🎉  Instalación finalizada — Resumen"
printf "${BOLD}%-24s %s${RESET}\n" "COMPONENTE" "ESTADO"
printf "%-24s %s\n" "────────────────────────" "──────────────────────────────"
for fila in "${RESUMEN[@]}"; do
  comp="${fila%%|*}"; est="${fila##*|}"
  color="$GREEN"
  case "$est" in
    *FALTA*|*FALLO*|*OMITIDO*) color="$RED" ;;
    *opcional*|*avisos*|*aviso*) color="$YELLOW" ;;
  esac
  printf "%-24s ${color}%s${RESET}\n" "$comp" "$est"
done

echo
if [ "$FALLOS_CRITICOS" -eq 0 ]; then
  printf "${GREEN}${BOLD}✅ Todo listo. PalmillaBot está instalado y verificado.${RESET}\n"
  cat <<EOF

  Para iniciar PalmillaBot, ejecuta:

      ${BOLD}./run.sh${RESET}

  …o haz doble clic en ${BOLD}Iniciar PalmillaBot.command${RESET} desde el Finder.

  Luego abre tu navegador en:  ${BOLD}http://localhost:8000${RESET}

  ${DIM}Registro completo de esta instalación: llevatodo.log${RESET}

EOF
  exit 0
else
  printf "${RED}${BOLD}⚠️  La instalación terminó con problemas críticos.${RESET}\n"
  echo "   Revisa el registro: $LOG_FILE"
  echo "   Corrige lo indicado y vuelve a ejecutar: ./llevatodo.sh"
  exit 1
fi
