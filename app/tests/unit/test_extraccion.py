"""Extracción: tramos de fechas y reintentos ante límite de tasa, sin red real."""

import json
from datetime import UTC, datetime
from pathlib import Path

import httpx

from senal.extraccion import agregar_sbp, obtener_con_reintentos, tramos


def test_tramos_cubren_la_ventana_sin_solapes_ni_huecos() -> None:
    desde = datetime(2026, 7, 1, tzinfo=UTC)
    hasta = datetime(2026, 7, 31, tzinfo=UTC)

    resultado = tramos(desde, hasta, dias=15)

    assert resultado[0][0] == desde
    assert resultado[-1][1] == hasta
    assert all(a[1] == b[0] for a, b in zip(resultado, resultado[1:], strict=False))
    assert len(resultado) == 2


def test_reintenta_ante_429_y_devuelve_la_respuesta_exitosa() -> None:
    respuestas = iter([httpx.Response(429, text="Please limit"), httpx.Response(200, text="ok")])
    cliente = httpx.Client(transport=httpx.MockTransport(lambda _req: next(respuestas)))
    esperas: list[float] = []

    respuesta = obtener_con_reintentos(
        cliente, "https://ejemplo.test", {}, intentos=3, espera_base=1.0, dormir=esperas.append
    )

    assert respuesta.status_code == 200
    assert esperas == [1.0]


def test_tras_agotar_intentos_devuelve_la_ultima_respuesta_sin_lanzar() -> None:
    cliente = httpx.Client(transport=httpx.MockTransport(lambda _req: httpx.Response(429)))
    esperas: list[float] = []

    respuesta = obtener_con_reintentos(
        cliente, "https://ejemplo.test", {}, intentos=3, espera_base=2.0, dormir=esperas.append
    )

    assert respuesta.status_code == 429
    assert esperas == [2.0, 4.0]


def test_sbp_descarga_doce_informes_y_agrega_al_registro_sin_tocar_otras_fuentes(
    tmp_path: Path,
) -> None:
    registro = {
        "version": "v",
        "fecha_corte_utc": "2026-10-06T00:00:00+00:00",
        "solicitudes": [{"fuente": "tvn_rss", "estado": 200, "archivo": "tvn_rss.xml"}],
    }
    (tmp_path / "extraccion.json").write_text(json.dumps(registro), encoding="utf-8")
    pedidas: list[str] = []

    def responder(peticion: httpx.Request) -> httpx.Response:
        pedidas.append(str(peticion.url))
        if "IAB-0324" in str(peticion.url):
            return httpx.Response(404)
        return httpx.Response(200, content=b"%PDF-1.4 sintetico")

    nuevo = agregar_sbp(tmp_path, transporte=httpx.MockTransport(responder))

    sbp = [s for s in nuevo["solicitudes"] if s["fuente"].startswith("sbp:")]
    assert len(pedidas) == 12
    assert pedidas[0].endswith("/IAB/IAB-0124.pdf")
    assert len(sbp) == 12
    assert sum(s["estado"] == 200 for s in sbp) == 11
    exitosa = next(s for s in sbp if s["estado"] == 200)
    assert exitosa["archivo"].startswith("sbp/IAB-")
    assert len(exitosa["sha256"]) == 64
    assert (tmp_path / exitosa["archivo"]).exists()
    assert nuevo["solicitudes"][0]["fuente"] == "tvn_rss"
    guardado = json.loads((tmp_path / "extraccion.json").read_text("utf-8"))
    assert guardado == nuevo

    otra_vez = agregar_sbp(tmp_path, transporte=httpx.MockTransport(responder))
    assert len([s for s in otra_vez["solicitudes"] if s["fuente"].startswith("sbp:")]) == 12
