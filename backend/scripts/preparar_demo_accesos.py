"""Crea usuarios de demostración solo en PostgreSQL de integración.

Las credenciales se reciben exclusivamente desde variables del proceso. El
módulo exige las mismas tres barreras que la suite PostgreSQL antes de escribir:
URL con sufijo ``_test``, confirmación explícita e identidad/marcador reales.
"""

import json
import os
import re

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from postgres_test_safety import (
    validar_destino_postgres_pruebas,
    verificar_identidad_base_pruebas,
)


PATRON_EMAIL_PRUEBA = re.compile(
    r"^[a-z0-9][a-z0-9._+-]{0,80}@puertotrack\.test$"
)


def _credencial(nombre: str) -> str:
    valor = os.getenv(nombre, "")
    if len(valor) < 16:
        raise ValueError(f"{nombre} debe contener al menos 16 caracteres.")
    return valor


def _email(nombre: str) -> str:
    valor = os.getenv(nombre, "").strip().lower()
    if not PATRON_EMAIL_PRUEBA.fullmatch(valor):
        raise ValueError(
            f"{nombre} debe usar un correo aislado @puertotrack.test."
        )
    return valor


def main() -> None:
    url_texto = os.getenv("PUERTOTRACK_TEST_DATABASE_URL", "")
    url = validar_destino_postgres_pruebas(
        url_texto,
        confirmacion=os.getenv("PUERTOTRACK_RUN_POSTGRES_TESTS", ""),
        url_aplicacion=os.getenv("DATABASE_URL"),
    )
    supervisor_email = _email("PUERTOTRACK_TEST_SUPERVISOR_EMAIL")
    operador_email = _email("PUERTOTRACK_TEST_OPERADOR_EMAIL")
    supervisor_password = _credencial(
        "PUERTOTRACK_TEST_SUPERVISOR_PASSWORD"
    )
    operador_password = _credencial("PUERTOTRACK_TEST_OPERADOR_PASSWORD")

    os.environ["DATABASE_URL"] = url_texto
    from models import Usuario
    from security import generar_password_hash

    motor = create_engine(url, pool_pre_ping=True)
    try:
        with motor.begin() as conexion:
            verificar_identidad_base_pruebas(conexion, url)
            session = Session(bind=conexion, expire_on_commit=False)
            try:
                usuarios = []
                for nombre, email, password, rol in (
                    (
                        "Supervisor demostración",
                        supervisor_email,
                        supervisor_password,
                        "supervisor",
                    ),
                    (
                        "Operador demostración",
                        operador_email,
                        operador_password,
                        "operador",
                    ),
                ):
                    usuario = session.scalar(
                        select(Usuario).where(Usuario.email == email)
                    )
                    if usuario is None:
                        usuario = Usuario(
                            nombre=nombre,
                            email=email,
                            password_hash=generar_password_hash(password),
                            rol=rol,
                            activo=True,
                        )
                        session.add(usuario)
                        session.flush()
                    usuarios.append(
                        {"id": usuario.id, "email": usuario.email, "rol": rol}
                    )
                print(json.dumps({"usuarios": usuarios}, sort_keys=True))
            finally:
                session.close()
    finally:
        motor.dispose()


if __name__ == "__main__":
    main()
