import httpx
import pytest

from rfid_service.backend_client import (
    ClienteBackend,
    CodigoContenedorDesconocido,
    ErrorBackendOperacional,
)


def test_cliente_envia_clave_y_acepta_contrato_minimo() -> None:
    def responder(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-PuertoTrack-Internal-Key"] == "k" * 32
        assert request.url.path.endswith("/ABC-123")
        return httpx.Response(
            200,
            json={"existe": True, "id": 7, "codigo": "ABC-123"},
        )

    cliente_http = httpx.Client(
        base_url="http://backend.test",
        transport=httpx.MockTransport(responder),
    )
    cliente = ClienteBackend(
        api_url="http://backend.test",
        clave_interna="k" * 32,
        timeout=1,
        cliente=cliente_http,
    )

    resultado = cliente.identificar("ABC-123")

    assert resultado.id == 7
    assert resultado.codigo == "ABC-123"
    cliente_http.close()


def test_cliente_distingue_404_y_errores_del_backend() -> None:
    respuestas = iter(
        [
            httpx.Response(404, json={"detail": "no encontrado"}),
            httpx.Response(401, json={"detail": "credencial inválida"}),
        ]
    )
    cliente_http = httpx.Client(
        base_url="http://backend.test",
        transport=httpx.MockTransport(lambda request: next(respuestas)),
    )
    cliente = ClienteBackend(
        api_url="http://backend.test",
        clave_interna="k" * 32,
        timeout=1,
        cliente=cliente_http,
    )

    with pytest.raises(CodigoContenedorDesconocido):
        cliente.identificar("NOEXISTE")
    with pytest.raises(ErrorBackendOperacional):
        cliente.identificar("ABC123")
    cliente_http.close()
