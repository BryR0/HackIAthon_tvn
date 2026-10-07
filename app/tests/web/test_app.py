"""Interfaz web: flujo completo sin red ni modelo (T10) sobre el snapshot real."""

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from senal.score import RULES_VERSION
from senal.web.app import Config, crear_app

PROCESADO = Path(__file__).resolve().parents[2] / "data" / "processed"


@pytest.fixture(scope="module")
def cliente(tmp_path_factory: pytest.TempPathFactory) -> TestClient:
    revisiones = tmp_path_factory.mktemp("rev") / "reviews.jsonl"
    config = Config(
        procesado=PROCESADO,
        revisiones=revisiones,
        usar_modelo=False,
        usar_llm=False,
        hosts_permitidos=("testserver", "127.0.0.1", "localhost"),
    )
    return TestClient(crear_app(config))


def _token(html: str) -> str:
    coincidencia = re.search(r'name="csrf" value="([^"]+)"', html)
    assert coincidencia
    return coincidencia.group(1)


def _primer_tema(cliente: TestClient) -> str:
    html = cliente.get("/").text
    coincidencia = re.search(r'href="/tema/([^"]+)"', html)
    assert coincidencia
    return coincidencia.group(1)


def test_bandeja_muestra_ranking_version_de_reglas_y_modo(cliente: TestClient) -> None:
    respuesta = cliente.get("/")

    assert respuesta.status_code == 200
    assert RULES_VERSION in respuesta.text
    assert "baseline:palabras_clave" in respuesta.text
    assert "Hora de Panamá" in respuesta.text


def test_ficha_expone_componentes_fuentes_y_accion(cliente: TestClient) -> None:
    respuesta = cliente.get(f"/tema/{_primer_tema(cliente)}")

    assert respuesta.status_code == 200
    for texto in ("Qué se reporta", "Quién lo reporta", "Qué está respaldado", "Qué falta"):
        assert texto in respuesta.text
    assert "30 × R" in respuesta.text
    assert "no habilita publicación" in respuesta.text


def test_borrador_extractivo_con_citas(cliente: TestClient) -> None:
    id_tema = _primer_tema(cliente)
    token = _token(cliente.get(f"/tema/{id_tema}").text)

    respuesta = cliente.post(f"/tema/{id_tema}/borrador", data={"csrf": token})

    assert respuesta.status_code == 200
    assert "Basado únicamente en titular/metadatos." in respuesta.text
    assert "extractivo" in respuesta.text


def test_revision_humana_queda_registrada(cliente: TestClient) -> None:
    id_tema = _primer_tema(cliente)
    token = _token(cliente.get(f"/tema/{id_tema}").text)

    respuesta = cliente.post(
        f"/tema/{id_tema}/revision",
        data={"csrf": token, "estado": "requiere_evidencia", "revisor": "Ana", "nota": "falta ACP"},
        follow_redirects=True,
    )

    assert respuesta.status_code == 200
    assert "requiere_evidencia" in respuesta.text
    assert "Ana" in respuesta.text


def test_post_sin_token_csrf_se_rechaza(cliente: TestClient) -> None:
    respuesta = cliente.post(f"/tema/{_primer_tema(cliente)}/borrador", data={"csrf": "x"})

    assert respuesta.status_code == 403


def test_consulta_sin_evidencia_se_abstiene(cliente: TestClient) -> None:
    respuesta = cliente.get("/consulta", params={"q": "precio del bitcoin en Japón"})

    assert respuesta.status_code == 200
    assert "Abstención" in respuesta.text


def test_tema_inexistente_da_404(cliente: TestClient) -> None:
    assert cliente.get("/tema/E-no-existe").status_code == 404


def test_calidad_muestra_manifest_y_desviaciones(cliente: TestClient) -> None:
    respuesta = cliente.get("/calidad")

    assert respuesta.status_code == 200
    assert "D6" in respuesta.text
    assert "SHA-256" in respuesta.text


def test_host_no_permitido_se_rechaza(cliente: TestClient) -> None:
    assert cliente.get("/", headers={"host": "evil.example"}).status_code == 400


def test_cabeceras_de_seguridad_y_no_cache(cliente: TestClient) -> None:
    respuesta = cliente.get("/")

    assert respuesta.headers["cache-control"] == "no-store"
    assert respuesta.headers["cross-origin-opener-policy"] == "same-origin"


def test_modales_y_assets_front_end(cliente: TestClient) -> None:
    # Asset estático de script existe y se sirve correctamente
    resp_js = cliente.get("/static/app.js")
    assert resp_js.status_code == 200
    assert "abrirModal" in resp_js.text

    # Página principal incluye modals y script
    resp_inicio = cliente.get("/")
    assert resp_inicio.status_code == 200
    assert "/static/app.js" in resp_inicio.text
    assert 'id="modal-tour"' in resp_inicio.text
    assert 'id="modal-consulta"' in resp_inicio.text
    assert 'id="modal-formula"' in resp_inicio.text
    assert "hero-banner" in resp_inicio.text

    # Ficha del tema incluye modal de revisión
    id_tema = _primer_tema(cliente)
    resp_tema = cliente.get(f"/tema/{id_tema}")
    assert resp_tema.status_code == 200
    assert 'id="modal-decision-revision"' in resp_tema.text



# --- Extensión bancaria: misma app, modalidad "banca" (TB09, TB11, TB13) ------------

CU05 = "¿Qué señales públicas del entorno logístico debo revisar?"


def _primer_tema_banca(cliente: TestClient) -> str:
    html = cliente.get("/", params={"modalidad": "banca"}).text
    coincidencia = re.search(r'href="/tema/([^"?]+)\?modalidad=banca"', html)
    assert coincidencia
    return coincidencia.group(1)


def test_tb09_modalidad_por_lista_permitida_y_defecto_editorial(cliente: TestClient) -> None:
    banca = cliente.get("/", params={"modalidad": "banca"}).text
    invalida = cliente.get("/", params={"modalidad": "<script>"}).text
    defecto = cliente.get("/").text

    assert 'data-modalidad="banca"' in banca
    assert "no una opinión oficial de la SBP" in banca
    assert 'data-modalidad="editorial"' in invalida
    assert "<script>" not in invalida.split("<body>")[1].split("</header>")[0]
    assert 'data-modalidad="editorial"' in defecto


def test_tb09_ficha_bancaria_muestra_contexto_sbp_como_hipotesis(cliente: TestClient) -> None:
    id_tema = _primer_tema_banca(cliente)

    html = cliente.get(f"/tema/{id_tema}", params={"modalidad": "banca"}).text

    assert "Crédito local SBN" in html
    assert "hipótesis" in html
    assert f'action="/tema/{id_tema}/boletin"' in html


def test_tb09_boletin_con_citas_aviso_y_csrf(cliente: TestClient) -> None:
    id_tema = _primer_tema_banca(cliente)
    token = _token(cliente.get(f"/tema/{id_tema}", params={"modalidad": "banca"}).text)

    sin_token = cliente.post(f"/tema/{id_tema}/boletin", data={"csrf": "x"})
    respuesta = cliente.post(f"/tema/{id_tema}/boletin", data={"csrf": token})

    assert sin_token.status_code == 403
    assert respuesta.status_code == 200
    assert "Boletín de entorno" in respuesta.text
    assert "no una opinión oficial de la SBP" in respuesta.text
    assert "Basado únicamente en titular/metadatos." in respuesta.text
    assert "SBP:credito_local:" in respuesta.text
    assert "Hipótesis de impacto" in respuesta.text


def test_tb13_revision_bancaria_separada_de_la_editorial(cliente: TestClient) -> None:
    id_tema = _primer_tema_banca(cliente)
    token = _token(cliente.get(f"/tema/{id_tema}", params={"modalidad": "banca"}).text)

    invalida = cliente.post(
        f"/tema/{id_tema}/revision",
        data={"csrf": token, "estado": "descartado", "revisor": "Beto", "modalidad": "otra"},
    )
    banca = cliente.post(
        f"/tema/{id_tema}/revision",
        data={"csrf": token, "estado": "descartado", "revisor": "Beto Analista",
              "nota": "sin dato", "modalidad": "banca"},
        follow_redirects=True,
    )  # fmt: skip
    editorial = cliente.get(f"/tema/{id_tema}").text

    assert invalida.status_code == 422
    assert banca.status_code == 200
    assert "Beto Analista" in banca.text
    assert "Beto Analista" not in editorial


def test_tb11_cu05_literal_en_la_web_entrega_boletin_sin_abstenerse(cliente: TestClient) -> None:
    respuesta = cliente.get("/consulta", params={"q": CU05, "modalidad": "banca"})

    assert respuesta.status_code == 200
    assert "Abstención" not in respuesta.text
    assert "Boletín de entorno" in respuesta.text
    assert "SBP:credito_local:comercio:" in respuesta.text
    assert "SBP:credito_local:industria:" in respuesta.text


def test_consulta_editorial_no_usa_series_sbp(cliente: TestClient) -> None:
    respuesta = cliente.get("/consulta", params={"q": "tránsitos del Canal de Panamá"})

    assert "SBP:credito_local" not in respuesta.text


def test_generar_todo_360_genera_ambos_paquetes(cliente: TestClient) -> None:
    id_tema = _primer_tema_banca(cliente)
    token = _token(cliente.get(f"/tema/{id_tema}").text)

    respuesta = cliente.post(f"/tema/{id_tema}/generar_todo", data={"csrf": token})

    assert respuesta.status_code == 200
    assert "Paquete Editorial" in respuesta.text
    assert "Boletín de Entorno" in respuesta.text
    assert "Factores de Prioridad Algorítmica" in respuesta.text
    assert "Exposición Crediticia SBP de Panamá" in respuesta.text
