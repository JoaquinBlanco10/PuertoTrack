import os
import secrets
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


# Impide que cualquier import de database.py apunte a PostgreSQL durante tests.
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["JWT_SECRET_KEY"] = secrets.token_urlsafe(48)
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"

from database import Base, obtener_sesion  # noqa: E402
from login_protection import limitador_login  # noqa: E402
import models  # noqa: E402, F401
from main import app  # noqa: E402


@pytest.fixture(autouse=True)
def aislar_limitador_login() -> Generator[None, None, None]:
    limitador_login.reiniciar()
    yield
    limitador_login.reiniciar()


@pytest.fixture
def session_prueba() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def activar_claves_foraneas(
        dbapi_connection: object, connection_record: object
    ) -> None:
        cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    creador_sesiones = sessionmaker(bind=engine, expire_on_commit=False)

    with creador_sesiones() as session:
        yield session
        session.rollback()

    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def cliente(
    session_prueba: Session,
) -> Generator[TestClient, None, None]:
    def usar_sesion_de_prueba() -> Generator[Session, None, None]:
        yield session_prueba

    app.dependency_overrides[obtener_sesion] = usar_sesion_de_prueba
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
