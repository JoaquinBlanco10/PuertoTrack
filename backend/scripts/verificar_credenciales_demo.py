"""Comprueba credenciales demo sin mostrarlas y sin escribir en la base."""

import os

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from postgres_test_safety import (
    validar_destino_postgres_pruebas,
    verificar_identidad_base_pruebas,
)


def main() -> None:
    url_texto = os.getenv("PUERTOTRACK_TEST_DATABASE_URL", "")
    url = validar_destino_postgres_pruebas(
        url_texto,
        confirmacion=os.getenv("PUERTOTRACK_RUN_POSTGRES_TESTS", ""),
        url_aplicacion=os.getenv("DATABASE_URL"),
    )
    passwords = {
        "supervisor.demo@puertotrack.test": os.getenv(
            "PUERTOTRACK_DEMO_SUPERVISOR_PASSWORD", ""
        ),
        "operador.demo@puertotrack.test": os.getenv(
            "PUERTOTRACK_DEMO_OPERADOR_PASSWORD", ""
        ),
    }
    if any(len(password) < 16 for password in passwords.values()):
        raise ValueError("Faltan credenciales temporales para verificar.")

    os.environ["DATABASE_URL"] = url_texto
    from models import Usuario
    from security import verificar_password

    motor = create_engine(url, pool_pre_ping=True)
    try:
        with motor.connect() as conexion:
            verificar_identidad_base_pruebas(conexion, url)
            with Session(bind=conexion) as session:
                for email, password in passwords.items():
                    usuario = session.scalar(
                        select(Usuario).where(Usuario.email == email)
                    )
                    if usuario is None or not verificar_password(
                        password, usuario.password_hash
                    ):
                        raise RuntimeError(
                            f"La credencial demo de {email} no coincide con su hash."
                        )
        print("Credenciales demo verificadas en PostgreSQL aislado.")
    finally:
        motor.dispose()


if __name__ == "__main__":
    main()
