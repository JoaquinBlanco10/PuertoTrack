import httpx
import pytest

from access_service.backend_client import (
    BackendNoDisponible,
    ClienteBackend,
    ContenedorDesconocido,
)


CLAVE = "a" * 40


def _cliente(handler):
    transporte = httpx.MockTransport(handler)
    http = httpx.Client(base_url="http://backend.test", transport=transporte)
    return ClienteBackend(
        api_url="http://backend.test",
        clave_interna=CLAVE,
        timeout=1,
        cliente=http,
    )


def test_consulta_hechos_minimos_con_clave_independiente() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-PuertoTrack-Access-Key"] == CLAVE
        assert request.url.path.endswith("/CONT123")
        return httpx.Response(
            200,
            json={
                "existe": True,
                "id": 9,
                "codigo": "CONT123",
                "estado": "disponible",
                "situacion": "presencia_sin_confirmar",
                "coherencia_operacional": "sin_confirmar",
                "ubicacion_actual_id": None,
                "tiene_movimientos": False,
                "tiene_salida_previa": False,
                "etiqueta_entrada": "primera_entrada",
            },
        )

    hechos = _cliente(handler).consultar_hechos("CONT123")

    assert hechos.id == 9
    assert hechos.tiene_movimientos is False


def test_distingue_desconocido_de_falla_o_contrato_incompatible() -> None:
    desconocido = _cliente(lambda request: httpx.Response(404))
    with pytest.raises(ContenedorDesconocido):
        desconocido.consultar_hechos("NOEXISTE")

    incompatible = _cliente(lambda request: httpx.Response(200, json={}))
    with pytest.raises(BackendNoDisponible):
        incompatible.consultar_hechos("CONT123")
