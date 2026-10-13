#!/usr/bin/env bash
# =============================================================================
#  🌵 PalmillaBot — Instalador para macOS
# =============================================================================
#  Este script deja el sistema listo para ejecutarse localmente en tu Mac:
#    1. Verifica que exista Python 3 (>= 3.9).
#    2. Crea un entorno virtual aislado en ./venv.
#    3. Instala las dependencias de Python (FastAPI, scikit-learn, etc.).
#    4. Verifica/instala wkhtmltopdf (para exportar el PMF a PDF).
#    5. Verifica/instala GDAL (para el GeoPDF georreferenciado del plano).
#    6. Te permite guardar tu API key de Google Gemini.
#
#  Uso:
#      chmod +x install.sh
#      ./install.sh
# =============================================================================

set -euo pipefail

# ---------- Utilidades de presentación ----------
BOLD=$'\033[1m'; DIM=$'\033[2m'; RESET=$'\033[0m'
GREEN=$'\033[32m'; YELLOW=$'\033[33m'; RED=$'\033[31m'; BLUE=$'\033[34m'; CYAN=$'\033[36m'

info()  { printf "${BLUE}ℹ️  %s${RESET}\n" "$*"; }
ok()    { printf "${GREEN}✅ %s${RESET}\n" "$*"; }
warn()  { printf "${YELLOW}⚠️  %s${RESET}\n" "$*"; }
err()   { printf "${RED}❌ %s${RESET}\n" "$*" >&2; }
title() { printf "\n${BOLD}${CYAN}%s${RESET}\n" "$*"; }

# ---------- Ubicación del proyecto ----------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
VENV_DIR="$SCRIPT_DIR/venv"
CONFIG_FILE="$SCRIPT_DIR/config.json"

title "🌵  PalmillaBot — Instalador para macOS"
printf "${DIM}Directorio del proyecto: %s${RESET}\n" "$SCRIPT_DIR"

# =============================================================================
# 1) Sistema operativo
# =============================================================================
title "1/6 · Comprobando el sistema operativo"
OS="$(uname -s)"
if [ "$OS" != "Darwin" ]; then
  warn "Este instalador está pensado para macOS, pero se detectó '$OS'."
  warn "Continuaré de todos modos (puede funcionar en Linux)."
else
  ok "macOS detectado ($(sw_vers -productVersion 2>/dev/null || echo 'versión desconocida'))."
fi

# =============================================================================
# 2) Python 3
# =============================================================================
title "2/6 · Buscando Python 3 (>= 3.9)"
PYTHON_BIN=""
for cand in python3 python3.13 python3.12 python3.11 python3.10 python3.9; do
  if command -v "$cand" >/dev/null 2>&1; then
    if "$cand" -c 'import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)' 2>/dev/null; then
      PYTHON_BIN="$cand"; break
    fi
  fi
done

if [ -z "$PYTHON_BIN" ]; then
  err "No se encontró Python 3.9 o superior."
  echo
  echo "   Instálalo de una de estas formas:"
  echo "     • Homebrew:   brew install python@3.12"
  echo "     • Sitio web:  https://www.python.org/downloads/macos/"
  echo
  exit 1
fi
PYVER="$("$PYTHON_BIN" -c 'import platform; print(platform.python_version())')"
ok "Python encontrado: $PYTHON_BIN (versión $PYVER)"

# =============================================================================
# 3) Entorno virtual
# =============================================================================
title "3/6 · Creando el entorno virtual (venv)"
if [ -d "$VENV_DIR" ] && [ -x "$VENV_DIR/bin/python" ]; then
  ok "El entorno virtual ya existe en ./venv (se reutiliza)."
else
  info "Creando entorno virtual en ./venv …"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
  ok "Entorno virtual creado."
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
ok "Entorno virtual activado ($(python --version))."

# =============================================================================
# 4) Dependencias de Python
# =============================================================================
title "4/7 · Instalando dependencias de Python"
info "Actualizando pip …"
python -m pip install --quiet --upgrade pip setuptools wheel
info "Instalando dependencias desde requirements.txt (puede tardar unos minutos) …"
python -m pip install --quiet -r "$SCRIPT_DIR/requirements.txt"
ok "Dependencias instaladas correctamente."

# =============================================================================
# 5) GDAL (para el GeoPDF georreferenciado del plano)
# =============================================================================
title "5/7 · Comprobando GDAL (plano GeoPDF georreferenciado)"
if command -v gdal_translate >/dev/null 2>&1 || python -c "from osgeo import gdal" >/dev/null 2>&1; then
  ok "GDAL disponible: el GeoPDF se generará con georreferenciación OGC."
else
  warn "GDAL no está instalado."
  echo "   Es necesario para el GeoPDF georreferenciado del plano (Módulo D)."
  echo "   (El Shapefile y el GeoJSON se generan igualmente sin GDAL.)"
  if command -v brew >/dev/null 2>&1; then
    printf "${BOLD}¿Deseas instalarlo ahora con Homebrew? [s/N]: ${RESET}"
    read -r RESP || RESP="n"
    case "$RESP" in
      s|S|si|Sí|y|Y)
        info "Instalando GDAL con Homebrew (puede tardar unos minutos) …"
        if brew install gdal; then
          ok "GDAL instalado."
        else
          warn "No se pudo instalar GDAL. Puedes hacerlo luego: brew install gdal"
        fi
        ;;
      *) warn "Omitido. Instálalo cuando quieras con: brew install gdal" ;;
    esac
  else
    warn "Homebrew no está instalado. Instálalo desde https://brew.sh y luego:"
    echo "       brew install gdal"
  fi
fi

# =============================================================================
# 6) wkhtmltopdf (para exportar el PMF a PDF)
# =============================================================================
title "6/7 · Comprobando wkhtmltopdf (exportación a PDF)"
if command -v wkhtmltopdf >/dev/null 2>&1; then
  ok "wkhtmltopdf ya está instalado ($(wkhtmltopdf --version 2>/dev/null | head -1))."
else
  warn "wkhtmltopdf no está instalado."
  echo "   Es necesario para exportar el Programa de Manejo a PDF."
  echo "   (El sistema funciona sin él: podrás descargar en DOCX, HTML y Markdown)."
  if command -v brew >/dev/null 2>&1; then
    printf "${BOLD}¿Deseas instalarlo ahora con Homebrew? [s/N]: ${RESET}"
    read -r RESP || RESP="n"
    case "$RESP" in
      s|S|si|Sí|y|Y)
        info "Instalando wkhtmltopdf con Homebrew …"
        if brew install --cask wkhtmltopdf; then
          ok "wkhtmltopdf instalado."
        else
          warn "No se pudo instalar wkhtmltopdf. Puedes hacerlo luego: brew install --cask wkhtmltopdf"
        fi
        ;;
      *) warn "Omitido. Instálalo cuando quieras con: brew install --cask wkhtmltopdf" ;;
    esac
  else
    warn "Homebrew no está instalado. Instálalo desde https://brew.sh y luego:"
    echo "       brew install --cask wkhtmltopdf"
  fi
fi

# =============================================================================
# 7) API key de Google Gemini (opcional)
# =============================================================================
title "7/7 · Configuración de la IA (Google Gemini)"
echo "   PalmillaBot puede usar la IA de Google Gemini para redactar respuestas"
echo "   y el Programa de Manejo. Necesitas una API key GRATUITA de Google AI Studio."
echo
printf "   ¿Deseas configurarla ahora? [s/N]: "
read -r CONFIG_IA || CONFIG_IA="n"

if [[ "$CONFIG_IA" =~ ^[sSyY] ]]; then
  echo
  echo "   Obtén tu API key en: ${BOLD}https://aistudio.google.com/app/apikey${RESET}"
  printf "   Pega tu API key de Gemini (o Enter para omitir): "
  read -r API_KEY || API_KEY=""
  if [ -n "${API_KEY:-}" ]; then
    # Guardar de forma segura en config.json (permisos 600)
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
  else
    warn "No se guardó ninguna API key. Podrás añadirla luego desde la interfaz (⚙️ Configuración)."
  fi
else
  info "Omitido. Podrás configurar la API key más tarde desde la interfaz (⚙️ Configuración)."
fi

# =============================================================================
# Listo
# =============================================================================
title "🎉  ¡Instalación completada!"
cat <<EOF

  Para iniciar PalmillaBot, ejecuta:

      ${BOLD}./run.sh${RESET}

  …o haz doble clic en ${BOLD}Iniciar PalmillaBot.command${RESET} desde el Finder.

  Luego abre tu navegador en:  ${BOLD}http://localhost:8000${RESET}

  ${DIM}Sin API key de Gemini, el sistema funciona en modo RAG offline:
  recupera y cita la normatividad y genera el PMF con la plantilla
  determinista. Con la API key, además redacta con IA.${RESET}

EOF
