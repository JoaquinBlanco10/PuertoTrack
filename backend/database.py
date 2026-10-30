
import os
from collections.abc import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# Cargar las variables del archivo .env
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("No se encontró DATABASE_URL en el archivo .env")

# Crear la conexión con PostgreSQL
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Crear sesiones para trabajar con la base de datos
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


class Base(DeclarativeBase):
    """Clase base para todos los modelos SQLAlchemy de la aplicación."""

    pass


def obtener_sesion() -> Generator[Session, None, None]:
    """Entrega una sesión por petición y garantiza que siempre se cierre."""

    with SessionLocal() as session:
        yield session


def comprobar_conexion():
    with engine.connect() as conexion:
        conexion.execute(text("SELECT 1"))
    return True
