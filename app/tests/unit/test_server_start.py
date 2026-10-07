"""Partes puras del lanzador multiplataforma (scripts/server_start.py)."""

import importlib.util
from pathlib import Path
from types import ModuleType

RUTA = (
    Path(__file__).resolve().parents[3] / "scripts" / "server_start.py"
    if (Path(__file__).resolve().parents[3] / "scripts" / "server_start.py").exists()
    else Path(__file__).resolve().parents[2] / "scripts" / "server_start.py"
)


def _modulo() -> ModuleType:
    spec = importlib.util.spec_from_file_location("server_start", RUTA)
    assert spec and spec.loader
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


ss = _modulo()

NETSTAT = """
  Proto  Local Address          Foreign Address        State           PID
  TCP    0.0.0.0:135            0.0.0.0:0              LISTENING       1180
  TCP    127.0.0.1:8765         0.0.0.0:0              LISTENING       4242
  TCP    [::]:8765              [::]:0                 LISTENING       4243
  TCP    127.0.0.1:8765         127.0.0.1:50000        ESTABLISHED     4242
  TCP    127.0.0.1:18765        0.0.0.0:0              LISTENING       999
"""

SS = """State  Recv-Q Send-Q Local Address:Port Peer Address:Port Process
LISTEN 0      2048   127.0.0.1:8765     0.0.0.0:*     users:(("python",pid=777,fd=6))
LISTEN 0      128    0.0.0.0:22         0.0.0.0:*     users:(("sshd",pid=12,fd=3))
"""


def test_leer_env_ignora_comentarios_y_comillas(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text('# comentario\nSENAL_PUERTO=9000\nGEMINI_API_KEY="x"\nVACIA=\n', "utf-8")

    valores = ss.leer_env(env)

    assert valores == {"SENAL_PUERTO": "9000", "GEMINI_API_KEY": "x", "VACIA": ""}


def test_pids_de_netstat_solo_escuchando_en_el_puerto_exacto() -> None:
    assert ss.pids_netstat_windows(NETSTAT, 8765) == {4242, 4243}


def test_pids_de_ss_en_linux() -> None:
    assert ss.pids_ss_linux(SS, 8765) == {777}
    assert ss.pids_ss_linux(SS, 9999) == set()


def test_reinstala_solo_si_cambia_requirements(tmp_path: Path) -> None:
    req = tmp_path / "requirements.txt"
    marca = tmp_path / ".marca"
    req.write_text("fastapi==1\n", "utf-8")

    assert ss.necesita_instalar(req, marca)
    ss.registrar_instalacion(req, marca)
    assert not ss.necesita_instalar(req, marca)
    req.write_text("fastapi==2\n", "utf-8")
    assert ss.necesita_instalar(req, marca)


def test_puerto_valido_solo_ascii_y_no_privilegiado() -> None:
    assert ss.validar_puerto("8765") == 8765
    for invalido in ("80", "0", "70000", "８７６５", "abc", ""):
        assert ss.validar_puerto(invalido) is None
