#!/usr/bin/env bash
# =============================================================================
#  🌵 Iniciar PalmillaBot.command
# =============================================================================
#  Haz DOBLE CLIC en este archivo desde el Finder para iniciar PalmillaBot.
#  Si es la primera vez, instalará automáticamente lo necesario y luego
#  arrancará el servidor y abrirá el navegador.
#
#  NOTA (macOS): si al hacer doble clic aparece un aviso de seguridad, ve a
#  «Ajustes del Sistema → Privacidad y seguridad» y pulsa «Abrir igualmente»,
#  o ejecuta en Terminal:  xattr -d com.apple.quarantine "Iniciar PalmillaBot.command"
# =============================================================================

cd "$(dirname "$0")" || exit 1

BOLD=$'\033[1m'; RESET=$'\033[0m'; CYAN=$'\033[36m'

clear
printf "${BOLD}${CYAN}🌵 PalmillaBot${RESET}\n"
printf "──────────────────────────────────────────────\n\n"

# Si no existe el entorno virtual, ejecutar el instalador primero.
if [ ! -x "./venv/bin/python" ]; then
  printf "Primera ejecución detectada: iniciando la instalación…\n\n"
  chmod +x ./llevatodo.sh ./run.sh 2>/dev/null || true
  ./llevatodo.sh || { echo "La instalación falló. Revisa los mensajes anteriores."; read -r -p "Pulsa Enter para cerrar…"; exit 1; }
  printf "\n"
fi

chmod +x ./run.sh 2>/dev/null || true
./run.sh

# Mantener la ventana abierta si el servidor se detiene con error.
printf "\nEl servidor se ha detenido.\n"
read -r -p "Pulsa Enter para cerrar esta ventana…"
