import pytest
from typing import cast

from sqlalchemy import Connection
from sqlalchemy.engine import make_url

from postgres_test_safety import (
    CONFIRMACION_POSTGRES_PRUEBAS,
    DestinoPostgresInseguro,
    validar_destino_postgres_pruebas,
    verificar_identidad_base_pruebas,
    verificar_marcador_base_pruebas,
)


URL_PRUEBAS = (
    "postgresql+psycopg://usuario_pruebas:clave@localhost:55432/"
    "puertotrack_integration_test"
)


def test_acepta_destino_postgres_identificado_como_pruebas() -> None:
    url = validar_destino_postgres_pruebas(
        URL_PRUEBAS,
        confirmacion=CONFIRMACION_POSTGRES_PRUEBAS,
        url_aplicacion=(
            "postgresql+psycopg://usuario_app:clave@localhost:5432/puertotrack"
        ),
    )

    assert url.database == "puertotrack_integration_test"


@pytest.mark.parametrize(
    ("url", "confirmacion", "url_aplicacion"),
    [
        (URL_PRUEBAS, "", None),
        ("sqlite+pysqlite:///:memory:", CONFIRMACION_POSTGRES_PRUEBAS, None),
        (
            "postgresql+psycopg://usuario:clave@localhost/puertotrack",
            CONFIRMACION_POSTGRES_PRUEBAS,
            None,
        ),
        (URL_PRUEBAS, CONFIRMACION_POSTGRES_PRUEBAS, URL_PRUEBAS),
    ],
)
def test_rechaza_destinos_no_confirmados_no_postgres_o_reales(
    url: str, confirmacion: str, url_aplicacion: str | None
) -> None:
    with pytest.raises(DestinoPostgresInseguro):
        validar_destino_postgres_pruebas(
            url,
            confirmacion=confirmacion,
            url_aplicacion=url_aplicacion,
        )


def test_rechaza_base_sin_marcador_sin_exponer_la_url() -> None:
    class ConexionSinMarcador:
        def scalar(self, *args: object, **kwargs: object) -> None:
            return None

    conexion = cast(Connection, ConexionSinMarcador())

    with pytest.raises(DestinoPostgresInseguro) as error:
        verificar_marcador_base_pruebas(conexion)

    assert "secreto" not in str(error.value)


def test_verifica_identidad_real_de_la_base() -> None:
    class ResultadoIdentidad:
        def one(self) -> tuple[str, str]:
            return "puertotrack_integration_test", "usuario_pruebas"

    class ConexionPruebas:
        def scalar(self, *args: object, **kwargs: object) -> str:
            return "puertotrack:integration-test-only"

        def execute(self, *args: object, **kwargs: object) -> ResultadoIdentidad:
            return ResultadoIdentidad()

    conexion = cast(Connection, ConexionPruebas())

    verificar_identidad_base_pruebas(
        conexion,
        make_url(URL_PRUEBAS),
    )


@pytest.mark.parametrize(
    ("nombre", "usuario"),
    [
        ("puertotrack", "usuario_pruebas"),
        ("puertotrack_integration_test", "usuario_app"),
    ],
)
def test_rechaza_identidad_real_distinta_sin_exponer_url(
    nombre: str,
    usuario: str,
) -> None:
    class ResultadoIdentidad:
        def one(self) -> tuple[str, str]:
            return nombre, usuario

    class ConexionEquivocada:
        def scalar(self, *args: object, **kwargs: object) -> str:
            return "puertotrack:integration-test-only"

        def execute(self, *args: object, **kwargs: object) -> ResultadoIdentidad:
            return ResultadoIdentidad()

    conexion = cast(Connection, ConexionEquivocada())

    with pytest.raises(DestinoPostgresInseguro) as error:
        verificar_identidad_base_pruebas(
            conexion,
            make_url(URL_PRUEBAS),
        )

    assert "clave" not in str(error.value)
