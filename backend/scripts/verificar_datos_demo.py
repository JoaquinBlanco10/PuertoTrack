"""Comprueba, sin escribir, la base efímera usada por la DEMO interactiva."""

import argparse
import json
import os

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from postgres_test_safety import (
    validar_destino_postgres_pruebas,
    verificar_identidad_base_pruebas,
)


UBICACIONES_DEMO = {
    "MUELLE_1": ("Muelle 1", "interna", True),
    "PATIO_A": ("Patio A", "interna", True),
    "PATIO_B": ("Patio B", "interna", True),
    "FUERA_PUERTO": ("Fuera del puerto", "externa", True),
    "DEPOSITO_EXT": ("Depósito externo", "externa", True),
    "ZONA_INACTIVA": ("Zona externa inactiva", "externa", False),
}
CONTENEDORES_DEMO = {
    "DEMOENTRADA",
    "DEMOTRASLADO",
    "DEMOSALIDA",
    "DEMOREINGRESO",
    "DEMOHISTORIAL",
}
USUARIOS_DEMO = {
    "supervisor.demo@puertotrack.test",
    "operador.demo@puertotrack.test",
}


def _argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--estado", choices=("vacia", "preparada"), required=True)
    return parser.parse_args()


def _exigir_vacia(resumen: dict[str, object]) -> None:
    conteos = resumen["conteos"]
    if not isinstance(conteos, dict) or any(conteos.values()):
        raise RuntimeError(
            "La base nueva de la DEMO contiene datos antes de preparar fixtures."
        )


def _exigir_preparada(resumen: dict[str, object]) -> None:
    if resumen["usuarios"] != USUARIOS_DEMO:
        raise RuntimeError("Los usuarios no corresponden exclusivamente a la DEMO.")
    if resumen["contenedores"] != CONTENEDORES_DEMO:
        raise RuntimeError(
            "Los contenedores no corresponden exclusivamente a la DEMO."
        )
    if resumen["ubicaciones"] != UBICACIONES_DEMO:
        raise RuntimeError(
            "Las ubicaciones no corresponden exclusivamente a la DEMO."
        )
    conteos_esperados = {
        "usuarios": 2,
        "ubicaciones": 6,
        "contenedores": 5,
        "movimientos": 6,
        "audit_logs": 18,
    }
    if resumen["conteos"] != conteos_esperados:
        raise RuntimeError("Los conteos preparados de la DEMO son inesperados.")


def main() -> None:
    estado = _argumentos().estado
    url_texto = os.getenv("PUERTOTRACK_TEST_DATABASE_URL", "")
    url = validar_destino_postgres_pruebas(
        url_texto,
        confirmacion=os.getenv("PUERTOTRACK_RUN_POSTGRES_TESTS", ""),
        url_aplicacion=os.getenv("DATABASE_URL"),
    )

    os.environ["DATABASE_URL"] = url_texto
    from models import AuditLog, Contenedor, Movimiento, Ubicacion, Usuario

    motor = create_engine(url, pool_pre_ping=True)
    try:
        with motor.connect() as conexion:
            verificar_identidad_base_pruebas(conexion, url)
            session = Session(bind=conexion)
            try:
                ubicaciones = {
                    item.codigo: (item.nombre, item.tipo, item.activo)
                    for item in session.scalars(select(Ubicacion)).all()
                }
                contenedores = set(
                    session.scalars(select(Contenedor.codigo)).all()
                )
                usuarios = set(session.scalars(select(Usuario.email)).all())
                resumen: dict[str, object] = {
                    "conteos": {
                        "usuarios": session.scalar(select(func.count(Usuario.id))),
                        "ubicaciones": session.scalar(
                            select(func.count(Ubicacion.id))
                        ),
                        "contenedores": session.scalar(
                            select(func.count(Contenedor.id))
                        ),
                        "movimientos": session.scalar(
                            select(func.count(Movimiento.id))
                        ),
                        "audit_logs": session.scalar(
                            select(func.count(AuditLog.id))
                        ),
                    },
                    "usuarios": usuarios,
                    "ubicaciones": ubicaciones,
                    "contenedores": contenedores,
                }
                if estado == "vacia":
                    _exigir_vacia(resumen)
                else:
                    _exigir_preparada(resumen)
                print(
                    json.dumps(
                        {
                            "estado_demo": estado,
                            "conteos": resumen["conteos"],
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                )
            finally:
                session.close()
    finally:
        motor.dispose()


if __name__ == "__main__":
    main()
