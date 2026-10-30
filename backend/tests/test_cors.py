from fastapi.testclient import TestClient

from main import FRONTEND_ORIGIN


def test_cors_permite_el_frontend_configurado(cliente: TestClient) -> None:
    respuesta = cliente.options(
        "/auth/login",
        headers={
            "Origin": FRONTEND_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert respuesta.status_code == 200
    assert respuesta.headers["access-control-allow-origin"] == FRONTEND_ORIGIN
    assert "content-type" in respuesta.headers["access-control-allow-headers"].lower()


def test_cors_no_autoriza_origenes_no_configurados(cliente: TestClient) -> None:
    respuesta = cliente.options(
        "/auth/login",
        headers={
            "Origin": "https://origen-no-autorizado.example",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert respuesta.status_code == 400
    assert "access-control-allow-origin" not in respuesta.headers
