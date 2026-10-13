#!/usr/bin/env bash
# =============================================================================
#  🌵 PalmillaBot — Iniciador (macOS / Linux)
# =============================================================================
#  Activa el entorno virtual, arranca el servidor local y abre el navegador.
#  Detén el servidor con Ctrl+C.
#
#  Uso:
#      ./run.sh
#      ./run.sh --port 9000     (puerto personalizado)
#      ./run.sh --no-browser    (no abrir el navegador)
# =============================================================================

set -euo pipefail

BOLD=$'\033[1m'; RESET=$'\033[0m'
GREEN=$'\033[32m'; YELLOW=$'\033[33m'; RED=$'\033[31m'; CYAN=$'\033[36m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
VENV_DIR="$SCRIPT_DIR/venv"

PORT=8000
ABRIR_NAVEGADOR=1

# ---------- Argumentos ----------
while [ $# -gt 0 ]; do
  case "$1" in
    --port|-p) PORT="${2:-8000}"; shift 2 ;;
    --no-browser) ABRIR_NAVEGADOR=0; shift ;;
    -h|--help)
      echo "Uso: ./run.sh [--port N] [--no-browser]"; exit 0 ;;
    *) echo "Opción desconocida: $1"; exit 1 ;;
  esac
done

# ---------- Comprobaciones ----------
if [ ! -x "$VENV_DIR/bin/python" ]; then
  printf "${RED}❌ No se encontró el entorno virtual.${RESET}\n"
  echo "   Ejecuta primero el instalador:  ./install.sh"
  exit 1
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# ---------- Aviso de configuración de IA ----------
if [ -n "${GEMINI_API_KEY:-}" ]; then
  printf "${GREEN}✅ IA de Gemini activa (API key desde la variable de entorno).${RESET}\n"
elif [ -f "$SCRIPT_DIR/config.json" ] && grep -q '"gemini_api_key"[[:space:]]*:[[:space:]]*"[^"]' "$SCRIPT_DIR/config.json" 2>/dev/null; then
  printf "${GREEN}✅ IA de Gemini activa (API key guardada en config.json).${RESET}\n"
else
  printf "${YELLOW}⚠️  Sin API key de Gemini: modo RAG offline. Configúrala en ⚙️ Configuración.${RESET}\n"
fi

URL="http://localhost:$PORT"
printf "\n${BOLD}${CYAN}🌵 PalmillaBot iniciando…${RESET}\n"
printf "   Interfaz web: ${BOLD}%s${RESET}\n" "$URL"
printf "   Detén el servidor con ${BOLD}Ctrl+C${RESET}\n\n"

# ---------- Abrir el navegador tras un breve retardo ----------
if [ "$ABRIR_NAVEGADOR" -eq 1 ]; then
  (
    sleep 2
    if command -v open >/dev/null 2>&1; then
      open "$URL"            # macOS
    elif command -v xdg-open >/dev/null 2>&1; then
      xdg-open "$URL"        # Linux
    fi
  ) &
fi

# ---------- Arrancar el servidor ----------
cd "$SCRIPT_DIR/src"
exec python -m uvicorn app:app --host 127.0.0.1 --port "$PORT"
