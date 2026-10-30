"""Fixtures exclusivas de la suite PostgreSQL aislada.

Este archivo valida el destino antes de importar ``database`` y antes de que
Alembic pueda abrir una conexión. La suite normal, ubicada en ``tests/``, no
carga este módulo.
"""

import os
import secrets
from collections.abc import Generator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from postgres_test_safety import (
    CONFIRMACION_POSTGRES_PRUEBAS,
    DestinoPostgresInseguro,
    validar_destino_postgres_pruebas,
    verificar_identidad_base_pruebas,
)


DIRECTORIO_BACKEND = Path(__file__).resolve().parents[1]
URL_PRUEBAS = os.getenv("PUERTOTRACK_TEST_DATABASE_URL", "")
CONFIRMACION = os.getenv("PUERTOTRACK_RUN_POSTGRES_TESTS", "")
# Si el entorno ya expone la URL de la aplicación, también se rechaza una
# coincidencia exacta. No se abre ni se lee el archivo .env para obtenerla.
URL_APLICACION = os.getenv("DATABASE_URL")

try:
    url_validada = validar_destino_postgres_pruebas(
        URL_PRUEBAS,
        confirmacion=CONFIRMACION,
        url_aplicacion=URL_APLICACION,
    )
except DestinoPostgresInseguro as error:
    raise pytest.UsageError(
        "Suite PostgreSQL bloqueada por la protección de destino: "
        f"{error}"
    ) from error

# La segunda barrera se consulta en la propia base y debe existir antes de
# cualquier migración. La URL nunca se incluye en mensajes de error.
motor_verificacion = create_engine(URL_PRUEBAS, pool_pre_ping=True)
try:
    with motor_verificacion.connect() as conexion:
        verificar_identidad_base_pruebas(conexion, url_validada)
except DestinoPostgresInseguro as error:
    raise pytest.UsageError(
        "Suite PostgreSQL bloqueada por la protección de destino: "
        f"{error}"
    ) from error
finally:
    motor_verificacion.dispose()

# Debe ocurrir antes de importar database.py. load_dotenv no reemplaza una
# variable ya definida, por lo que la aplicación no puede apuntar a su base
# habitual dentro de este proceso de pytest.
os.environ["DATABASE_URL"] = URL_PRUEBAS
os.environ.setdefault("JWT_SECRET_KEY", secrets.token_urlsafe(48))
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")

from database import engine  # noqa: E402
import models  # noqa: E402, F401


@pytest.fixture(scope="session", autouse=True)
def esquema_alembic_postgres() -> Generator[None, None, None]:
    """Aplica ``upgrade head`` únicamente tras repetir las barreras."""

    with engine.connect() as conexion:
        verificar_identidad_base_pruebas(conexion, url_validada)

    configuracion = Config(str(DIRECTORIO_BACKEND / "alembic.ini"))
    command.upgrade(configuracion, "head")
    yield
    # No se ejecuta downgrade ni DROP. El contenedor usa tmpfs y su ciclo de
    # vida es el único mecanismo de descarte de la base de pruebas.


@pytest.fixture(scope="session")
def motor_postgres() -> Engine:
    return engine


@pytest.fixture
def session_postgres() -> Generator[Session, None, None]:
    """Aísla cada prueba aunque un servicio invoque ``commit()``."""

    conexion = engine.connect()
    transaccion_externa = conexion.begin()
    session = Session(
        bind=conexion,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    try:
        yield session
    finally:
        session.close()
        if transaccion_externa.is_active:
            transaccion_externa.rollback()
        conexion.close()
