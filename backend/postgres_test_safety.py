from sqlalchemy import Connection, text
from sqlalchemy.engine import URL, make_url


CONFIRMACION_POSTGRES_PRUEBAS = "PUERTOTRACK_POSTGRES_TEST_ONLY"
MARCADOR_BASE_PRUEBAS = "puertotrack:integration-test-only"


class DestinoPostgresInseguro(RuntimeError):
    """La configuración no identifica inequívocamente una base de pruebas."""


def validar_destino_postgres_pruebas(
    url_pruebas: str,
    *,
    confirmacion: str,
    url_aplicacion: str | None = None,
) -> URL:
    if confirmacion != CONFIRMACION_POSTGRES_PRUEBAS:
        raise DestinoPostgresInseguro(
            "Falta la confirmación explícita para pruebas PostgreSQL."
        )
    try:
        url = make_url(url_pruebas)
    except Exception as error:
        raise DestinoPostgresInseguro(
            "La URL de pruebas PostgreSQL no es válida."
        ) from error

    nombre = (url.database or "").casefold()
    if not url.drivername.startswith("postgresql"):
        raise DestinoPostgresInseguro(
            "La suite de integración requiere PostgreSQL."
        )
    if not nombre.startswith("puertotrack") or not nombre.endswith("_test"):
        raise DestinoPostgresInseguro(
            "La base debe identificarse como puertotrack..._test."
        )
    if nombre in {"postgres", "template0", "template1"}:
        raise DestinoPostgresInseguro(
            "No se permite usar una base administrativa."
        )

    if url_aplicacion:
        try:
            aplicacion = make_url(url_aplicacion)
        except Exception:
            aplicacion = None
        if aplicacion is not None and _mismo_destino(url, aplicacion):
            raise DestinoPostgresInseguro(
                "La base de pruebas coincide con la base de la aplicación."
            )
    return url


def verificar_marcador_base_pruebas(conexion: Connection) -> None:
    marcador = conexion.scalar(
        text(
            "SELECT shobj_description(oid, 'pg_database') "
            "FROM pg_database WHERE datname = current_database()"
        )
    )
    if marcador != MARCADOR_BASE_PRUEBAS:
        raise DestinoPostgresInseguro(
            "La base no contiene el marcador de integración requerido."
        )


def verificar_identidad_base_pruebas(
    conexion: Connection,
    url_esperada: URL,
) -> None:
    """Comprueba el destino real conectado antes de permitir escrituras.

    La URL se valida antes de abrir la conexión. Esta segunda comprobación
    evita confiar únicamente en variables de entorno: exige que PostgreSQL
    confirme el nombre, el usuario y el marcador de la base efímera.
    """

    verificar_marcador_base_pruebas(conexion)
    nombre_actual, usuario_actual = conexion.execute(
        text("SELECT current_database(), current_user")
    ).one()
    if (
        str(nombre_actual).casefold()
        != (url_esperada.database or "").casefold()
        or usuario_actual != url_esperada.username
    ):
        raise DestinoPostgresInseguro(
            "La identidad de la conexión no coincide con el destino de pruebas."
        )


def _mismo_destino(primera: URL, segunda: URL) -> bool:
    return (
        (primera.host or "").casefold(),
        primera.port,
        (primera.database or "").casefold(),
        primera.username,
    ) == (
        (segunda.host or "").casefold(),
        segunda.port,
        (segunda.database or "").casefold(),
        segunda.username,
    )
