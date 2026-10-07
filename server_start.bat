@echo off
rem Señal TVN Media - arranque en Windows desde la raíz del repositorio.
rem Solo requiere Python 3.12+ instalado.
setlocal
cd /d "%~dp0"

echo [server_start] Iniciando Señal TVN Media. Verificando Python...
set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY (
  where python >nul 2>&1 && set "PY=python"
)
if not defined PY (
  echo [server_start] ERROR: no se encontro Python. Instala Python 3.12 o superior desde https://www.python.org/downloads/
  exit /b 1
)

echo [server_start] Ejecutando scripts de preparacion y arranque. Por favor espere...
%PY% "%~dp0scripts\server_start.py" %*
exit /b %ERRORLEVEL%
