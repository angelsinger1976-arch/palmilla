#!/usr/bin/env bash
# =============================================================================
#  🌵 PalmillaBot — install.sh (compatibilidad)
# =============================================================================
#  Este instalador se conserva por compatibilidad con versiones anteriores.
#
#  Ahora TODO lo hace el instalador integral «llevatodo.sh», que verifica e
#  instala cualquier requerimiento que falte (Python, dependencias de Python,
#  GDAL, wkhtmltopdf, etc.) y ejecuta una autoprueba de extremo a extremo.
#
#  Uso:
#      ./install.sh            # equivale a  ./llevatodo.sh
#      ./install.sh --yes      # sin preguntas
#
#  Para actualizar una instalación existente usa:  ./actualizate.sh
# =============================================================================

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -x "$SCRIPT_DIR/llevatodo.sh" ]; then
  echo "ℹ️  install.sh delega en el instalador integral llevatodo.sh …"
  exec "$SCRIPT_DIR/llevatodo.sh" "$@"
else
  echo "❌ No se encontró llevatodo.sh en $SCRIPT_DIR" >&2
  echo "   Descarga de nuevo el proyecto o crea el entorno manualmente." >&2
  exit 1
fi
