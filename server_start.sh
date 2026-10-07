#!/usr/bin/env sh
# Señal TVN Media - arranque en Linux/macOS desde la raíz del repositorio.
# Solo requiere Python 3.12+ instalado.
set -eu
cd "$(dirname "$0")"

echo "[server_start] Iniciando Señal TVN Media. Verificando Python..."
PY=""
for candidato in python3.13 python3.12 python3 python; do
  if command -v "$candidato" >/dev/null 2>&1; then
    PY="$candidato"
    break
  fi
done

if [ -z "$PY" ]; then
  echo "[server_start] ERROR: no se encontro Python. Instala Python 3.12 o superior." >&2
  exit 1
fi

echo "[server_start] Ejecutando scripts de preparacion y arranque. Por favor espere..."
exec "$PY" scripts/server_start.py "$@"
