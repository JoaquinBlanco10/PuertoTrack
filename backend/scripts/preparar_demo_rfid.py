"""Verifica y prepara datos RFID solo en PostgreSQL de integración.

Este módulo no utiliza ``SessionLocal``. La conexión se construye únicamente
desde ``PUERTOTRACK_TEST_DATABASE_URL`` y cualquier escritura ocurre después
de validar la URL y la identidad confirmada por PostgreSQL.
"""

import argparse
import json
import os
import re

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from postgres_test_safety import (
    DestinoPostgresInseguro,
    validar_destino_postgres_pruebas,
    verificar_identidad_base_pruebas,
)


PATRON_CODIGO = re.compile(r"^[A-Z0-9_-]{1,20}$")


def leer_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verifica el PostgreSQL efímero y, opcionalmente, crea el "
            "contenedor aislado de la demostración RFID."
        )
    )
    acciones = parser.add_mutually_exclusive_group()
    acciones.add_argument(
        "--crear-contenedor",
        metavar="CODIGO",
        help="Crea el fixture solo después de superar todas las barreras.",
    )
    acciones.add_argument(
        "--snapshot-contenedor",
        metavar="CODIGO",
        help="Devuelve el estado operacional para comparar antes y después.",
    )
    return parser.parse_args()


def main() -> None:
    argumentos = leer_argumentos()
    url_texto = os.getenv("PUERTOTRACK_TEST_DATABASE_URL", "")
    confirmacion = os.getenv("PUERTOTRACK_RUN_POSTGRES_TESTS", "")
    url_aplicacion = os.getenv("DATABASE_URL")
    url = validar_destino_postgres_pruebas(
        url_texto,
        confirmacion=confirmacion,
        url_aplicacion=url_aplicacion,
    )

    codigo_recibido = (
        argumentos.crear_contenedor or argumentos.snapshot_contenedor
    )
    codigo = None
    if codigo_recibido is not None:
        codigo = codigo_recibido.strip().upper()
        if not PATRON_CODIGO.fullmatch(codigo):
            raise ValueError(
                "El código de prueba debe tener entre 1 y 20 caracteres "
                "alfanuméricos, guion o guion bajo."
            )

    # Debe establecerse antes de importar models/database. load_dotenv no
    # reemplaza esta variable y, por tanto, no puede redirigir el proceso.
    os.environ["DATABASE_URL"] = url_texto
    from models import AuditLog, Contenedor, Movimiento, Ubicacion

    motor = create_engine(url, pool_pre_ping=True)
    try:
        with motor.begin() as conexion:
            verificar_identidad_base_pruebas(conexion, url)
            if codigo is None:
                print(
                    "Destino PostgreSQL aislado verificado; "
                    "no se realizaron escrituras."
                )
                return

            session = Session(bind=conexion, expire_on_commit=False)
            try:
                contenedor = session.scalar(
                    select(Contenedor).where(Contenedor.codigo == codigo)
                )
                if argumentos.snapshot_contenedor is not None:
                    if contenedor is None:
                        raise ValueError(
                            "El contenedor de prueba no existe en la base aislada."
                        )
                    snapshot = {
                        "contenedor": {
                            "id": contenedor.id,
                            "codigo": contenedor.codigo,
                            "estado": contenedor.estado,
                            "ubicacion_actual": contenedor._ubicacion_actual_texto,
                            "ubicacion_actual_id": contenedor.ubicacion_actual_id,
                        },
                        "totales": {
                            "movimientos": session.scalar(
                                select(func.count(Movimiento.id))
                            ),
                            "auditorias": session.scalar(
                                select(func.count(AuditLog.id))
                            ),
                            "ubicaciones": session.scalar(
                                select(func.count(Ubicacion.id))
                            ),
                        },
                    }
                    print(
                        json.dumps(
                            snapshot,
                            ensure_ascii=False,
                            sort_keys=True,
                        )
                    )
                    return

                creado = contenedor is None
                if contenedor is None:
                    contenedor = Contenedor(
                        codigo=codigo,
                        ubicacion_actual="Sin asignar",
                        ubicacion_actual_id=None,
                        estado="disponible",
                    )
                    session.add(contenedor)
                    session.flush()
                print(
                    f"Fixture RFID aislado: codigo={contenedor.codigo}; "
                    f"id={contenedor.id}; creado={str(creado).lower()}"
                )
            finally:
                session.close()
    except DestinoPostgresInseguro:
        raise
    finally:
        motor.dispose()


if __name__ == "__main__":
    main()
