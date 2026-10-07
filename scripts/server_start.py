"""Lanzador multiplataforma de Señal TVN: solo requiere Python 3.12 instalado.

Pasos:
1. Verifica Python >= 3.12.
2. Crea ``.env`` desde ``.env.example`` si no existe.
3. Crea el entorno virtual ``.venv`` y asegura ``pip``.
4. Instala ``requirements.txt`` (solo si cambió desde la última instalación).
5. Libera el puerto (``SENAL_PUERTO``, 8765 por defecto) cerrando el proceso que lo escucha.
6. Inicia el servidor en http://127.0.0.1:<puerto>.

Usa solo la biblioteca estándar: se ejecuta antes de instalar dependencias.
Lo invocan ``server_start.bat`` (Windows) y ``server_start.sh`` (Linux/macOS).
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
VENV = RAIZ / ".venv"
APP_DIR = RAIZ / "app"
REQUISITOS = (APP_DIR / "requirements.txt") if (APP_DIR / "requirements.txt").exists() else (RAIZ / "requirements.txt")
MARCA = VENV / ".requirements.sha256"
PYTHON_MINIMO = (3, 12)
PUERTO_POR_DEFECTO = 8765
PUERTO_MINIMO = 1024
PUERTO_MAXIMO = 65535
HOST = "127.0.0.1"
ES_WINDOWS = os.name == "nt"
ESPERA_PUERTO_S = 10.0


def info(mensaje: str) -> None:
    print(f"[server_start] {mensaje}", flush=True)


def fallar(mensaje: str) -> None:
    print(f"[server_start] ERROR: {mensaje}", file=sys.stderr, flush=True)
    raise SystemExit(1)


def leer_env(ruta: Path) -> dict[str, str]:
    """Parser mínimo de .env (CLAVE=valor, comentarios con #, comillas opcionales)."""
    valores: dict[str, str] = {}
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        valores[clave.strip()] = valor.strip().strip('"').strip("'")
    return valores


def pids_netstat_windows(salida: str, puerto: int) -> set[int]:
    """PIDs en estado LISTENING exactamente en ``puerto`` según ``netstat -ano``."""
    pids: set[int] = set()
    for linea in salida.splitlines():
        partes = linea.split()
        if len(partes) < 5 or partes[0].upper() != "TCP" or partes[3].upper() != "LISTENING":
            continue
        if partes[1].rsplit(":", 1)[-1] == str(puerto) and partes[4].isdigit():
            pids.add(int(partes[4]))
    return pids


def pids_ss_linux(salida: str, puerto: int) -> set[int]:
    """PIDs en LISTEN exactamente en ``puerto`` según ``ss -ltnp``."""
    pids: set[int] = set()
    for linea in salida.splitlines():
        partes = linea.split()
        if len(partes) < 4 or partes[0] != "LISTEN":
            continue
        if partes[3].rsplit(":", 1)[-1] == str(puerto):
            pids.update(int(p) for p in re.findall(r"pid=(\d+)", linea))
    return pids


def validar_puerto(texto: str) -> int | None:
    """Puerto no privilegiado (1024–65535) escrito con dígitos ASCII; si no, ``None``.

    Evita que un valor como 80 o 5432 haga cerrar servicios del sistema."""
    if not (texto.isascii() and texto.isdigit()):
        return None
    puerto = int(texto)
    return puerto if PUERTO_MINIMO <= puerto <= PUERTO_MAXIMO else None


def _hash(ruta: Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def necesita_instalar(requisitos: Path, marca: Path) -> bool:
    return not marca.exists() or marca.read_text(encoding="utf-8").strip() != _hash(requisitos)


def registrar_instalacion(requisitos: Path, marca: Path) -> None:
    marca.parent.mkdir(parents=True, exist_ok=True)
    marca.write_text(_hash(requisitos), encoding="utf-8")


def python_del_venv() -> Path:
    return VENV / ("Scripts/python.exe" if ES_WINDOWS else "bin/python")


def ejecutar(comando: list[str], cwd: Path | None = None) -> None:
    resultado = subprocess.run(comando, cwd=cwd or RAIZ, check=False)  # noqa: S603
    if resultado.returncode != 0:
        fallar(f"falló el comando: {' '.join(comando)}")


def verificar_python() -> None:
    if sys.version_info < PYTHON_MINIMO:
        version = ".".join(map(str, sys.version_info[:3]))
        fallar(f"se requiere Python 3.12 o superior (encontrado {version}).")
    info(f"Python {sys.version.split()[0]} OK")


def preparar_env() -> dict[str, str]:
    env, ejemplo = RAIZ / ".env", RAIZ / ".env.example"
    if not env.exists():
        if not ejemplo.exists():
            fallar("no existe .env ni .env.example")
        shutil.copyfile(ejemplo, env)
        if not ES_WINDOWS:
            env.chmod(0o600)  # puede contener credenciales: solo lectura del dueño
        info(".env no existía: creado desde .env.example (edítalo para agregar credenciales).")
    else:
        info(".env encontrado")
    return leer_env(env)


def preparar_venv() -> Path:
    python = python_del_venv()
    if not python.exists():
        info("Creando entorno virtual .venv ...")
        creado = subprocess.run([sys.executable, "-m", "venv", str(VENV)], check=False)  # noqa: S603
        if creado.returncode != 0:
            fallar("no se pudo crear .venv (en Debian/Ubuntu instala python3-venv).")
    pip_ok = subprocess.run(  # noqa: S603
        [str(python), "-m", "pip", "--version"], capture_output=True, check=False
    )
    if pip_ok.returncode != 0:
        info("Instalando pip en .venv ...")
        ejecutar([str(python), "-m", "ensurepip", "--upgrade"])
    return python


def instalar_dependencias(python: Path) -> None:
    if not necesita_instalar(REQUISITOS, MARCA):
        info("Dependencias al día (requirements.txt sin cambios).")
        return
    info("Instalando dependencias de requirements.txt...")
    info(
        "  [!] AVISO: La instalación inicial puede tardar 1-3 minutos según la velocidad "
        "de red. Por favor espere..."
    )
    info("  -> Actualizando pip...")
    ejecutar([str(python), "-m", "pip", "install", "--upgrade", "pip"])
    info("  -> Descargando e instalando paquetes de Señal TVN (FastAPI, PyTorch, etc.)...")
    ejecutar([str(python), "-m", "pip", "install", "-r", str(REQUISITOS)], cwd=APP_DIR)
    if (APP_DIR / "pyproject.toml").exists():
        info("  -> Registrando paquete de la aplicación en modo editable...")
        ejecutar([str(python), "-m", "pip", "install", "--no-deps", "-e", str(APP_DIR)])
    registrar_instalacion(REQUISITOS, MARCA)
    info("Dependencias instaladas exitosamente.")


def _puerto_ocupado(puerto: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((HOST, puerto)) == 0


def _salida(comando: list[str]) -> str:
    resultado = subprocess.run(comando, capture_output=True, text=True, check=False)  # noqa: S603
    return resultado.stdout


def _pids_en_puerto(puerto: int) -> set[int]:
    if ES_WINDOWS:
        return pids_netstat_windows(_salida(["netstat", "-ano"]), puerto)
    if shutil.which("lsof"):
        salida = _salida(["lsof", "-nP", f"-iTCP:{puerto}", "-sTCP:LISTEN", "-t"])
        return {int(p) for p in salida.split() if p.isdigit()}
    if shutil.which("ss"):
        return pids_ss_linux(_salida(["ss", "-ltnp"]), puerto)
    return set()


def _terminar(pid: int, forzar: bool = False) -> None:
    if ES_WINDOWS:
        _salida(["taskkill", "/PID", str(pid), "/T", "/F"])
        return
    try:
        os.kill(pid, signal.SIGKILL if forzar else signal.SIGTERM)
    except ProcessLookupError:
        return


def _esperar_libre(puerto: int) -> bool:
    limite = time.monotonic() + ESPERA_PUERTO_S
    while _puerto_ocupado(puerto) and time.monotonic() < limite:
        time.sleep(0.3)
    return not _puerto_ocupado(puerto)


def liberar_puerto(puerto: int) -> None:
    pids = _pids_en_puerto(puerto) - {os.getpid()}
    if not pids and not _puerto_ocupado(puerto):
        info(f"Puerto {puerto} libre.")
        return
    if not pids:
        fallar(f"el puerto {puerto} está ocupado y no se pudo identificar el proceso.")
    for pid in sorted(pids):
        info(f"Cerrando proceso {pid} que escuchaba en el puerto {puerto}.")
        _terminar(pid)
    if not _esperar_libre(puerto):
        for pid in pids:
            _terminar(pid, forzar=True)
        if not _esperar_libre(puerto):
            fallar(f"no se pudo liberar el puerto {puerto}.")
    info(f"Puerto {puerto} liberado.")


def iniciar_servidor(python: Path, puerto: int) -> None:
    os.environ["SENAL_PUERTO"] = str(puerto)
    info(f"Servidor web configurado para http://{HOST}:{puerto} (Ctrl+C para detener)")
    info("Cargando modelo de embeddings y snapshot de Panamá...")
    info("  [!] Por favor espere: el motor está indexando las señales noticiosas...")
    comando = [
        str(python), "-m", "uvicorn", "senal.web.app:crear_app_desde_entorno",
        "--factory", "--host", HOST, "--port", str(puerto),
    ]  # fmt: skip
    env = os.environ.copy()
    env["SENAL_PUERTO"] = str(puerto)
    src_dir = APP_DIR / "src" if APP_DIR.exists() else RAIZ / "src"
    if src_dir.exists():
        existente = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{src_dir}{os.pathsep}{existente}" if existente else str(src_dir)
    try:
        subprocess.run(comando, cwd=RAIZ, env=env, check=False)  # noqa: S603
    except KeyboardInterrupt:
        info("Servidor detenido.")


def main() -> None:
    os.chdir(RAIZ)
    print("=" * 64, flush=True)
    print("  Señal TVN · Lanzador Automático de Servidor", flush=True)
    print("=" * 64, flush=True)
    info("Paso [1/6] Verificando versión de Python...")
    verificar_python()
    info("Paso [2/6] Comprobando archivo de configuración (.env)...")
    variables = preparar_env()
    info("Paso [3/6] Preparando entorno virtual (.venv)...")
    python = preparar_venv()
    info("Paso [4/6] Verificando dependencias instaladas...")
    instalar_dependencias(python)
    puerto_texto = variables.get("SENAL_PUERTO") or str(PUERTO_POR_DEFECTO)
    puerto = validar_puerto(puerto_texto)
    if puerto is None:
        fallar(f"SENAL_PUERTO inválido en .env: {puerto_texto!r} (usa 1024–65535).")
        return
    info(f"Paso [5/6] Verificando disponibilidad del puerto {puerto}...")
    liberar_puerto(puerto)
    info("Paso [6/6] Iniciando servidor web y motor de IA...")
    iniciar_servidor(python, puerto)


if __name__ == "__main__":
    main()
