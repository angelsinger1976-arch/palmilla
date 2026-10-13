#!/usr/bin/env bash
# =============================================================================
#  🌵 PalmillaBot — Actualizador  «actualizate.sh»
# =============================================================================
#  Pone al día tu copia de PalmillaBot sin perder tu configuración:
#
#    1. Comprueba que sea un repositorio Git y trae los últimos cambios
#       (git pull) de la rama indicada.
#    2. Reutiliza el entorno virtual ./venv (lo crea si no existe).
#    3. Actualiza las dependencias de Python (requirements.txt).
#    4. Re-verifica GDAL y wkhtmltopdf (Módulos D y C).
#    5. Ejecuta una autoprueba de extremo a extremo (smoke test).
#    6. Muestra un resumen del antes/después.
#
#  Tu API key (config.json) NUNCA se toca ni se sube a Git.
#
#  Uso:
#      chmod +x actualizate.sh
#      ./actualizate.sh                 # actualización interactiva
#      ./actualizate.sh --yes           # sin preguntas
#      ./actualizate.sh --branch main   # rama a seguir (por defecto: main)
#      ./actualizate.sh --no-deps       # solo código, sin tocar dependencias
#      ./actualizate.sh --help
#
#  Es idempotente: si ya estás al día, no rompe nada.
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
LOG_FILE="$SCRIPT_DIR/actualizate.log"
INSTALADOR="$SCRIPT_DIR/llevatodo.sh"

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
ACTUALIZAR_DEPS=1
RAMA="main"

uso() {
  awk 'NR>1 && /^#/ {sub(/^# ?/,""); print} NR>1 && !/^#/ && !/^$/ {exit}' "${BASH_SOURCE[0]}"
  exit 0
}

while [ $# -gt 0 ]; do
  case "$1" in
    -y|--yes)       ASSUME_YES=1 ;;
    --no-deps)      ACTUALIZAR_DEPS=0 ;;
    --branch|-b)    RAMA="${2:-main}"; shift ;;
    -h|--help)      uso ;;
    *) err "Opción desconocida: $1"; echo "Usa ./actualizate.sh --help"; exit 2 ;;
  esac
  shift
done

# -----------------------------------------------------------------------------
#  Utilidades
# -----------------------------------------------------------------------------
confirmar() {
  local pregunta="$1"
  if [ "$ASSUME_YES" -eq 1 ]; then return 0; fi
  if [ ! -t 0 ]; then return 1; fi
  printf "${BOLD}%s [s/N]: ${RESET}" "$pregunta"
  local r; read -r r || r="n"
  case "$r" in s|S|si|Sí|sí|y|Y) return 0 ;; *) return 1 ;; esac
}

tiene() { command -v "$1" >/dev/null 2>&1; }

RESUMEN=()
resumen_add() { RESUMEN+=("$1|$2"); }
FALLOS=0

# -----------------------------------------------------------------------------
#  Encabezado
# -----------------------------------------------------------------------------
clear 2>/dev/null || true
printf "${BOLD}${CYAN}"
cat <<'BANNER'
  🌵  PalmillaBot — Actualizador «actualizate.sh»
  ────────────────────────────────────────────────
BANNER
printf "${RESET}"
printf "${DIM}Directorio del proyecto: %s${RESET}\n" "$SCRIPT_DIR"
printf "${DIM}Registro de actualización: %s${RESET}\n" "$LOG_FILE"
: > "$LOG_FILE" 2>/dev/null || true
log "Inicio de la actualización en $SCRIPT_DIR (rama: $RAMA)"

# =============================================================================
#  1) Repositorio Git: traer los últimos cambios
# =============================================================================
paso "Paso 1/6 · Actualizando el código desde GitHub"
STASHED=0
if [ -d "$SCRIPT_DIR/.git" ] && tiene git; then
  cd "$SCRIPT_DIR"
  ANTES="$(git rev-parse --short HEAD 2>/dev/null || echo '¿?')"
  RAMA_ACTUAL="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo '')"
  ok "Repositorio Git detectado (rama actual: $RAMA_ACTUAL, commit: $ANTES)."

  # Archivos nuevos sin rastrear: se conservan intactos (no se tocan).
  NO_RASTREADOS="$(git ls-files --others --exclude-standard 2>/dev/null)"
  if [ -n "$NO_RASTREADOS" ]; then
    info "Archivos nuevos sin rastrear (se conservan):"
    printf '%s\n' "$NO_RASTREADOS" | head -8 | sed 's/^/     · /'
  fi

  # Solo guardamos modificaciones en archivos YA rastreados.
  CAMBIOS_TRACK="$(git status --porcelain --untracked-files=no 2>/dev/null)"
  if [ -n "$CAMBIOS_TRACK" ]; then
    warn "Tienes modificaciones locales en archivos rastreados."
    echo "   Se guardarán temporalmente (git stash) y se restaurarán al final."
    if confirmar "¿Continuar y guardar tus cambios locales?"; then
      if git stash push -m "actualizate.sh $(date '+%F %T')" >/dev/null 2>&1; then
        STASHED=1; ok "Cambios locales guardados (se restaurarán al terminar)."
      else
        warn "No se pudieron guardar los cambios locales."
      fi
    else
      warn "Actualización cancelada por el usuario."
      exit 0
    fi
  fi

  info "Descargando cambios de la rama '$RAMA' …"
  if git fetch origin "$RAMA" 2>&1 | tail -3; then
    if git checkout "$RAMA" >/dev/null 2>&1 || git checkout -B "$RAMA" "origin/$RAMA" >/dev/null 2>&1; then
      if git merge --ff-only "origin/$RAMA" 2>&1 | tail -3; then
        ok "Código actualizado (fast-forward)."
      else
        warn "No se pudo hacer fast-forward; puede haber divergencia de ramas."
        echo "   Tu rama local '$RAMA' y 'origin/$RAMA' han divergido."
        if confirmar "¿Forzar la actualización con 'git reset --hard origin/$RAMA'?"; then
          git reset --hard "origin/$RAMA" >/dev/null 2>&1 && ok "Rama reseteada a origin/$RAMA." || warn "No se pudo resetear."
        else
          warn "Se conserva tu versión local."
        fi
      fi
    else
      warn "No se pudo cambiar a la rama '$RAMA'."
    fi
  else
    warn "No se pudo contactar con el repositorio remoto (¿sin conexión?)."
    echo "   Se continuará con el código actual."
  fi

  # Restaurar las modificaciones locales que se guardaron al inicio.
  if [ "$STASHED" -eq 1 ]; then
    if git stash pop >/dev/null 2>&1; then
      ok "Tus cambios locales fueron restaurados."
    else
      warn "No se pudieron restaurar automáticamente tus cambios."
      echo "   Recupéralos manualmente con:  git stash list  &&  git stash pop"
    fi
  fi

  DESPUES="$(git rev-parse --short HEAD 2>/dev/null || echo '¿?')"
  if [ "$ANTES" = "$DESPUES" ]; then
    ok "Ya estabas en la última versión ($DESPUES)."
    resumen_add "Código (git)" "ya al día ($DESPUES)"
  else
    ok "Actualizado: $ANTES → $DESPUES"
    resumen_add "Código (git)" "$ANTES → $DESPUES"
  fi
else
  warn "No se detectó un repositorio Git (.git)."
  echo "   Si descargaste un ZIP, vuelve a descargar la última versión desde:"
  echo "   ${BOLD}https://github.com/angelsinger1976-arch/palmilla${RESET}"
  resumen_add "Código (git)" "sin repositorio Git"
fi

# =============================================================================
#  2) Entorno virtual
# =============================================================================
paso "Paso 2/6 · Comprobando el entorno virtual (./venv)"
if [ -x "$VENV_DIR/bin/python" ]; then
  ok "El entorno virtual existe."
  resumen_add "Entorno virtual" "OK"
else
  warn "No existe el entorno virtual."
  if [ -x "$INSTALADOR" ]; then
    if confirmar "¿Ejecutar el instalador integral (llevatodo.sh) para crearlo?"; then
      echo
      "$INSTALADOR" ${ASSUME_YES:+--yes} || warn "El instalador terminó con avisos."
      # Recargar tras el instalador
      [ -x "$VENV_DIR/bin/python" ] && ok "Entorno virtual creado por el instalador." || { err "No se pudo crear el entorno virtual."; FALLOS=1; }
    else
      err "Se necesita el entorno virtual para continuar."
      exit 1
    fi
  else
    err "No se encontró llevatodo.sh. Ejecútalo o crea el venv manualmente."
    exit 1
  fi
fi

if [ -x "$VENV_DIR/bin/python" ]; then
  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
  ok "Entorno virtual activado ($(python --version 2>&1))."
fi

# =============================================================================
#  3) Dependencias de Python
# =============================================================================
paso "Paso 3/6 · Actualizando dependencias de Python"
if [ "$ACTUALIZAR_DEPS" -eq 0 ]; then
  info "Omitido por --no-deps."
  resumen_add "Dependencias Python" "omitido (--no-deps)"
elif [ -x "$VENV_DIR/bin/python" ] && [ -f "$REQ_FILE" ]; then
  info "Actualizando pip, setuptools y wheel …"
  python -m pip install --quiet --upgrade pip setuptools wheel 2>&1 | tail -2 || warn "No se pudo actualizar pip."
  info "Actualizando dependencias desde requirements.txt …"
  if python -m pip install --upgrade -r "$REQ_FILE"; then
    ok "Dependencias actualizadas."
    resumen_add "Dependencias Python" "actualizadas"
  else
    warn "Algunas dependencias fallaron al actualizar."
    resumen_add "Dependencias Python" "con avisos"
  fi
else
  warn "No hay entorno virtual o requirements.txt; se omiten las dependencias."
  resumen_add "Dependencias Python" "omitido"
fi

# =============================================================================
#  4) Verificación de librerías clave
# =============================================================================
paso "Paso 4/6 · Verificando librerías clave"
if [ -x "$VENV_DIR/bin/python" ]; then
  MODULOS=(fastapi uvicorn pydantic sklearn numpy docx markdown geopandas shapely pyproj matplotlib requests)
  FALTAN=()
  for mod in "${MODULOS[@]}"; do
    python -c "import $mod" >/dev/null 2>&1 || FALTAN+=("$mod")
  done
  if [ ${#FALTAN[@]} -eq 0 ]; then
    ok "Las 12 librerías están presentes."
    resumen_add "Librerías Python" "todas OK"
  else
    warn "Faltan: ${FALTAN[*]}. Reintentando …"
    python -m pip install --upgrade -r "$REQ_FILE" >/dev/null 2>&1 || true
    FALTAN2=()
    for mod in "${MODULOS[@]}"; do
      python -c "import $mod" >/dev/null 2>&1 || FALTAN2+=("$mod")
    done
    if [ ${#FALTAN2[@]} -eq 0 ]; then
      ok "Resuelto tras el reintento."
      resumen_add "Librerías Python" "todas OK"
    else
      err "Aún faltan: ${FALTAN2[*]}"
      resumen_add "Librerías Python" "faltan: ${FALTAN2[*]}"
      FALLOS=1
    fi
  fi
else
  resumen_add "Librerías Python" "omitido"
fi

# =============================================================================
#  5) GDAL y wkhtmltopdf
# =============================================================================
paso "Paso 5/6 · Re-verificando GDAL y wkhtmltopdf"
if tiene gdal_translate || { [ -x "$VENV_DIR/bin/python" ] && python -c "from osgeo import gdal" >/dev/null 2>&1; }; then
  ok "GDAL disponible (GeoPDF georreferenciado)."
  resumen_add "GDAL" "disponible"
else
  warn "GDAL no disponible (el Shapefile y el GeoJSON se generan igualmente)."
  echo "   Para el GeoPDF: brew install gdal  |  sudo apt-get install gdal-bin python3-gdal"
  resumen_add "GDAL" "no disponible (opcional)"
fi

if tiene wkhtmltopdf; then
  ok "wkhtmltopdf disponible (exportación del PMF a PDF)."
  resumen_add "wkhtmltopdf" "disponible"
else
  warn "wkhtmltopdf no disponible (podrás exportar en DOCX, HTML y Markdown)."
  echo "   Para el PDF: brew install --cask wkhtmltopdf  |  sudo apt-get install wkhtmltopdf"
  resumen_add "wkhtmltopdf" "no disponible (opcional)"
fi

# =============================================================================
#  6) Autoprueba (smoke test)
# =============================================================================
paso "Paso 6/6 · Autoprueba de extremo a extremo"
if [ -x "$VENV_DIR/bin/python" ]; then
  if python -c "import sys; sys.path.insert(0,'src'); import app" >/dev/null 2>&1; then
    ok "El backend (src/app.py) importa correctamente."
    resumen_add "Backend FastAPI" "OK"
  else
    warn "El backend no importa; revisa las dependencias."
    resumen_add "Backend FastAPI" "con avisos"
    FALLOS=1
  fi

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
    warn "El Módulo D no pudo generar el plano de ejemplo."
    resumen_add "Módulo D (plano)" "con avisos"
  fi
else
  warn "Sin entorno virtual: se omite la autoprueba."
fi

# =============================================================================
#  Resumen final
# =============================================================================
title "🎉  Actualización finalizada — Resumen"
printf "${BOLD}%-24s %s${RESET}\n" "COMPONENTE" "ESTADO"
printf "%-24s %s\n" "────────────────────────" "──────────────────────────────"
for fila in "${RESUMEN[@]}"; do
  comp="${fila%%|*}"; est="${fila##*|}"
  color="$GREEN"
  case "$est" in
    *faltan*|*FALLO*|*con\ avisos*) color="$YELLOW" ;;
    *no\ disponible*) color="$YELLOW" ;;
  esac
  printf "%-24s ${color}%s${RESET}\n" "$comp" "$est"
done

echo
if [ "$FALLOS" -eq 0 ]; then
  printf "${GREEN}${BOLD}✅ Actualización completada. PalmillaBot está al día.${RESET}\n"
  cat <<EOF

  Para iniciar PalmillaBot, ejecuta:

      ${BOLD}./run.sh${RESET}

  Luego abre tu navegador en:  ${BOLD}http://localhost:8000${RESET}

  ${DIM}Registro completo de esta actualización: actualizate.log${RESET}

EOF
  exit 0
else
  printf "${YELLOW}${BOLD}⚠️  Actualización terminada con avisos.${RESET}\n"
  echo "   Revisa el registro: $LOG_FILE"
  echo "   Si algo falta, ejecuta el instalador integral: ./llevatodo.sh"
  exit 1
fi
