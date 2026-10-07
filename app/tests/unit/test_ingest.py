"""T01 y reglas de integridad del contrato de datos (reto §7)."""

from datetime import UTC, datetime

from senal.ingest import (
    Ventana,
    completar_cuadricula,
    id_estable,
    normalizar_url,
    validar_indicadores,
    validar_noticias,
)

VENTANA = Ventana(
    desde=datetime(2026, 7, 1, tzinfo=UTC),
    hasta=datetime(2026, 10, 1, tzinfo=UTC),
)


def _noticia(**over: str | None) -> dict[str, str | None]:
    base: dict[str, str | None] = {
        "titulo": "Canal de Panamá amplía calado",
        "url": "https://www.tvn-2.com/nacionales/canal-calado/",
        "medio": "tvn-2.com",
        "idioma": "es",
        "fecha_publicacion": "2026-09-15T14:00:00Z",
        "fecha_deteccion": "2026-09-15T15:30:00Z",
        "fecha_extraccion": "2026-10-01T00:00:00Z",
        "origen": "tvn_rss",
        "alcance_texto": "titular_metadatos",
    }
    base.update(over)
    return base


def test_t01_fechas_invalidas_y_nulos_no_bloquean_la_carga() -> None:
    filas = [
        _noticia(),
        _noticia(url="https://x.com/a", fecha_publicacion="no-es-fecha"),
        _noticia(url="https://x.com/b", titulo=None),
        _noticia(url="ftp://x.com/c"),
        _noticia(url="https://x.com/d", fecha_publicacion="2020-01-01T00:00:00Z"),
    ]

    resultado = validar_noticias(filas, VENTANA)

    assert len(resultado.validas) == 1
    motivos = sorted(e.motivo for e in resultado.excluidos)
    assert motivos == ["campo_obligatorio", "fecha_invalida", "fuera_de_ventana", "url_invalida"]


def test_cada_exclusion_conserva_la_fila_original_para_auditoria() -> None:
    resultado = validar_noticias([_noticia(fecha_publicacion="31/02/2026")], VENTANA)

    exclusion = resultado.excluidos[0]
    assert exclusion.campo == "fecha_publicacion"
    assert exclusion.fila["fecha_publicacion"] == "31/02/2026"


def test_url_duplicada_se_excluye_como_duplicado() -> None:
    filas = [
        _noticia(url="https://www.tvn-2.com/a/?utm_source=x"),
        _noticia(url="https://WWW.tvn-2.com/a"),
    ]

    resultado = validar_noticias(filas, VENTANA)

    assert len(resultado.validas) == 1
    assert resultado.excluidos[0].motivo == "url_duplicada"


def test_fecha_deteccion_nula_se_conserva_como_nula_y_distinta_de_publicacion() -> None:
    resultado = validar_noticias([_noticia(fecha_deteccion=None)], VENTANA)

    noticia = resultado.validas[0]
    assert noticia.fecha_deteccion is None
    assert noticia.fecha_publicacion == datetime(2026, 9, 15, 14, 0, tzinfo=UTC)


def test_gdelt_sin_fecha_de_publicacion_usa_deteccion_sin_mezclarlas() -> None:
    fila = _noticia(
        url="https://prensa.com/a",
        origen="gdelt_doc",
        fecha_publicacion=None,
        fecha_deteccion="20260915T153000Z",
    )

    noticia = validar_noticias([fila], VENTANA).validas[0]

    assert noticia.fecha_publicacion is None
    assert noticia.fecha_deteccion == datetime(2026, 9, 15, 15, 30, tzinfo=UTC)
    assert noticia.fecha_referencia == noticia.fecha_deteccion


def test_sin_fecha_de_publicacion_ni_deteccion_se_excluye() -> None:
    fila = _noticia(fecha_publicacion=None, fecha_deteccion=None)

    resultado = validar_noticias([fila], VENTANA)

    assert resultado.excluidos[0].motivo == "campo_obligatorio"
    assert resultado.excluidos[0].campo == "fecha_publicacion"


def test_fechas_con_zona_se_normalizan_a_utc() -> None:
    resultado = validar_noticias(
        [_noticia(fecha_publicacion="Mon, 15 Sep 2026 09:00:00 -0500")], VENTANA
    )

    assert resultado.validas[0].fecha_publicacion == datetime(2026, 9, 15, 14, 0, tzinfo=UTC)


def test_normalizar_url_quita_tracking_barra_final_y_mayusculas_del_host() -> None:
    assert normalizar_url("https://WWW.TVN-2.com/a/b/?utm_medium=rss&id=3#top") == (
        "https://www.tvn-2.com/a/b?id=3"
    )


def test_id_estable_depende_solo_de_la_url_normalizada() -> None:
    assert id_estable("N", "https://www.tvn-2.com/a/?utm_source=x") == id_estable(
        "N", "https://www.tvn-2.com/a"
    )
    assert id_estable("N", "https://www.tvn-2.com/a").startswith("N-")


def _indicador(**over: str | None) -> dict[str, str | None]:
    base: dict[str, str | None] = {
        "pais_iso3": "PAN",
        "indicador_id": "FP.CPI.TOTL.ZG",
        "anio": "2023",
        "valor": "1.5",
        "unidad": "% anual",
        "fuente_url": "https://api.worldbank.org/v2/country/PAN/indicator/FP.CPI.TOTL.ZG",
        "fecha_extraccion": "2026-10-01T00:00:00Z",
        "licencia": "CC BY 4.0",
    }
    base.update(over)
    return base


def test_valor_faltante_del_banco_mundial_es_nulo_nunca_cero() -> None:
    resultado = validar_indicadores([_indicador(valor=None), _indicador(anio="2022", valor="")])

    assert [i.valor for i in resultado.validas] == [None, None]


def test_indicador_con_anio_no_numerico_se_excluye() -> None:
    resultado = validar_indicadores([_indicador(anio="dos mil")])

    assert resultado.validas == ()
    assert resultado.excluidos[0].motivo == "anio_invalido"


def test_cuadricula_completa_rellena_combinaciones_faltantes_con_nulo() -> None:
    parciales = validar_indicadores([_indicador()]).validas

    cuadricula = completar_cuadricula(
        parciales,
        paises=("PAN", "CRI"),
        indicadores=("FP.CPI.TOTL.ZG",),
        anios=range(2022, 2024),
        unidades={"FP.CPI.TOTL.ZG": "% anual"},
        fecha_extraccion=datetime(2026, 10, 1, tzinfo=UTC),
    )

    assert len(cuadricula) == 4
    presentes = {(i.pais_iso3, i.anio): i.valor for i in cuadricula}
    assert presentes[("PAN", 2023)] == 1.5
    assert presentes[("CRI", 2022)] is None
    assert all(i.unidad == "% anual" for i in cuadricula)
