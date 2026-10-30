"""Carga datos ficticios exclusivamente en PostgreSQL efímero de integración.

El script no usa ``SessionLocal`` y no importa modelos ni servicios hasta que
la URL, el marcador explícito y la identidad real de PostgreSQL fueron
validados. Las contraseñas llegan solo mediante variables del proceso.
"""

import json
import os

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from postgres_test_safety import (
    validar_destino_postgres_pruebas,
    verificar_identidad_base_pruebas,
)


CODIGOS_CONTENEDORES_DEMO = (
    "DEMOENTRADA",
    "DEMOTRASLADO",
    "DEMOSALIDA",
    "DEMOREINGRESO",
    "DEMOHISTORIAL",
)
NOMBRE_SUPERVISOR_DEMO = "Supervisor Demo"


def _leer_password(nombre: str) -> str:
    valor = os.getenv(nombre, "")
    if len(valor) < 16:
        raise ValueError(f"{nombre} debe contener al menos 16 caracteres.")
    return valor


def main() -> None:
    url_texto = os.getenv("PUERTOTRACK_TEST_DATABASE_URL", "")
    url = validar_destino_postgres_pruebas(
        url_texto,
        confirmacion=os.getenv("PUERTOTRACK_RUN_POSTGRES_TESTS", ""),
        url_aplicacion=os.getenv("DATABASE_URL"),
    )
    password_supervisor = _leer_password(
        "PUERTOTRACK_DEMO_SUPERVISOR_PASSWORD"
    )
    password_operador = _leer_password("PUERTOTRACK_DEMO_OPERADOR_PASSWORD")

    # load_dotenv no puede reemplazar esta URL explícita al importar database.
    os.environ["DATABASE_URL"] = url_texto
    from contenedor_service import ContenedorService
    from models import Usuario
    from movimiento_service import MovimientoService
    from schemas import (
        ContenedorCrear,
        MovimientoCrear,
        TipoMovimiento,
        TipoUbicacion,
        UbicacionActualizar,
        UbicacionCrear,
    )
    from security import generar_password_hash, verificar_password
    from ubicacion_service import UbicacionService

    motor = create_engine(url, pool_pre_ping=True)
    conexion = motor.connect()
    try:
        verificar_identidad_base_pruebas(conexion, url)
        session = Session(bind=conexion, expire_on_commit=False)
        try:
            supervisor = Usuario(
                nombre=NOMBRE_SUPERVISOR_DEMO,
                email="supervisor.demo@puertotrack.test",
                password_hash=generar_password_hash(password_supervisor),
                rol="supervisor",
                activo=True,
            )
            operador = Usuario(
                nombre="Operador Demo",
                email="operador.demo@puertotrack.test",
                password_hash=generar_password_hash(password_operador),
                rol="operador",
                activo=True,
            )
            session.add_all([supervisor, operador])
            session.commit()
            if not verificar_password(
                password_supervisor, supervisor.password_hash
            ) or not verificar_password(
                password_operador, operador.password_hash
            ):
                raise RuntimeError(
                    "No fue posible verificar las credenciales recién creadas."
                )

            ubicaciones = UbicacionService(session)
            muelle = ubicaciones.crear(
                UbicacionCrear(
                    codigo="MUELLE_1",
                    nombre="Muelle 1",
                    tipo=TipoUbicacion.INTERNA,
                ),
                supervisor,
            )
            patio_a = ubicaciones.crear(
                UbicacionCrear(
                    codigo="PATIO_A",
                    nombre="Patio A",
                    tipo=TipoUbicacion.INTERNA,
                ),
                supervisor,
            )
            patio_b = ubicaciones.crear(
                UbicacionCrear(
                    codigo="PATIO_B",
                    nombre="Patio B",
                    tipo=TipoUbicacion.INTERNA,
                ),
                supervisor,
            )
            fuera = ubicaciones.crear(
                UbicacionCrear(
                    codigo="FUERA_PUERTO",
                    nombre="Fuera del puerto",
                    tipo=TipoUbicacion.EXTERNA,
                ),
                supervisor,
            )
            ubicaciones.crear(
                UbicacionCrear(
                    codigo="DEPOSITO_EXT",
                    nombre="Depósito externo",
                    tipo=TipoUbicacion.EXTERNA,
                ),
                supervisor,
            )
            inactiva = ubicaciones.crear(
                UbicacionCrear(
                    codigo="ZONA_INACTIVA",
                    nombre="Zona externa inactiva",
                    tipo=TipoUbicacion.EXTERNA,
                ),
                supervisor,
            )
            ubicaciones.actualizar(
                inactiva.id,
                UbicacionActualizar(activo=False),
                supervisor,
            )

            contenedores = ContenedorService(session)
            creados = {
                codigo: contenedores.crear(
                    ContenedorCrear(codigo=codigo), supervisor
                )
                for codigo in CODIGOS_CONTENEDORES_DEMO
            }

            movimientos = MovimientoService(session)
            movimientos.registrar(
                MovimientoCrear(
                    contenedor_id=creados["DEMOTRASLADO"].id,
                    tipo=TipoMovimiento.ENTRADA,
                    ubicacion_destino_id=patio_a.id,
                    observacion="Entrada ficticia para demostrar traslados.",
                ),
                operador,
            )
            movimientos.registrar(
                MovimientoCrear(
                    contenedor_id=creados["DEMOSALIDA"].id,
                    tipo=TipoMovimiento.ENTRADA,
                    ubicacion_destino_id=muelle.id,
                    observacion="Entrada ficticia para demostrar una salida.",
                ),
                operador,
            )
            movimientos.registrar(
                MovimientoCrear(
                    contenedor_id=creados["DEMOREINGRESO"].id,
                    tipo=TipoMovimiento.ENTRADA,
                    ubicacion_destino_id=patio_a.id,
                ),
                operador,
            )
            movimientos.registrar(
                MovimientoCrear(
                    contenedor_id=creados["DEMOREINGRESO"].id,
                    tipo=TipoMovimiento.SALIDA,
                    ubicacion_destino_id=fuera.id,
                    observacion="Salida ficticia para demostrar un reingreso.",
                ),
                operador,
            )
            movimientos.registrar(
                MovimientoCrear(
                    contenedor_id=creados["DEMOHISTORIAL"].id,
                    tipo=TipoMovimiento.ENTRADA,
                    ubicacion_destino_id=muelle.id,
                ),
                operador,
            )
            movimientos.registrar(
                MovimientoCrear(
                    contenedor_id=creados["DEMOHISTORIAL"].id,
                    tipo=TipoMovimiento.TRASLADO,
                    ubicacion_destino_id=patio_b.id,
                    observacion="Traslado ficticio para poblar el historial.",
                ),
                operador,
            )

            # Relee desde PostgreSQL después de todos los commits de servicios.
            session.expire_all()
            supervisor_persistido = session.scalar(
                select(Usuario).where(
                    Usuario.email == "supervisor.demo@puertotrack.test"
                )
            )
            operador_persistido = session.scalar(
                select(Usuario).where(
                    Usuario.email == "operador.demo@puertotrack.test"
                )
            )
            if (
                supervisor_persistido is None
                or operador_persistido is None
                or not verificar_password(
                    password_supervisor,
                    supervisor_persistido.password_hash,
                )
                or not verificar_password(
                    password_operador,
                    operador_persistido.password_hash,
                )
            ):
                raise RuntimeError(
                    "Las credenciales persistidas no superaron la verificación."
                )

            # La verificación de identidad abrió una transacción en
            # ``conexion`` antes de construir la Session. Los commits de los
            # servicios participan en esa transacción externa; se confirma
            # aquí únicamente después de preparar y releer todo el fixture.
            session.commit()
            conexion.commit()
            print(
                json.dumps(
                    {
                        "demo_preparada": True,
                        "usuarios": 2,
                        "ubicaciones": 6,
                        "contenedores": list(CODIGOS_CONTENEDORES_DEMO),
                        "movimientos": 6,
                    },
                    ensure_ascii=False,
                )
            )
        finally:
            session.close()
    finally:
        conexion.close()
        motor.dispose()


if __name__ == "__main__":
    main()
