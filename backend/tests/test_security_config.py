import secrets

import pytest
from fastapi.testclient import TestClient

from main import app
from security import (
    crear_access_token,
    decodificar_access_token,
    validar_configuracion_seguridad,
)


@pytest.mark.parametrize(
    "secreto",
    [
        "",
        "secret",
        "changeme" * 8,
        "a" * 64,
        "01234567890123456789012345678901",
    ],
)
def test_rechaza_secretos_jwt_vacios_debiles_o_conocidos(
    monkeypatch: pytest.MonkeyPatch, secreto: str
) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", secreto)

    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY") as error:
        validar_configuracion_seguridad()

    if secreto:
        assert secreto not in str(error.value)


def test_aplicacion_valida_el_secreto_durante_el_arranque(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JWT_SECRET_KEY", "debil")

    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        with TestClient(app):
            pass


def test_secreto_fuerte_conserva_codificacion_y_decodificacion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secreto = secrets.token_urlsafe(48)
    monkeypatch.setenv("JWT_SECRET_KEY", secreto)

    validar_configuracion_seguridad()
    token = crear_access_token(123)

    assert decodificar_access_token(token)["sub"] == "123"
