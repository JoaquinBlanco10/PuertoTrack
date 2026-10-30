import secrets
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session

from dashboard_service import DashboardService
from models import Contenedor, Movimiento, Ubicacion, Usuario
from repositories import UsuarioRepository
from security import generar_password_hash


PASSWORD_PRUEBA = secrets.token_urlsafe(24)


def crear_usuario(
    session: Session,
    *,
    email: str = "dashboard@puertotrack.test",
    rol: str = "operador",
) -> Usuario:
    return UsuarioRepository(session).crear(
        Usuario(
            nombre=f"Usuario {rol}",
            email=email,
            password_hash=generar_password_hash(PASSWORD_PRUEBA),
            rol=rol,
        )
    )


def headers_usuario(
    cliente: TestClient,
    session: Session,
    *,
    email: str,
    rol: str,
) -> dict[str, str]:
    crear_usuario(session, email=email, rol=rol)
    respuesta = cliente.post(
        "/auth/login",
        data={"username": email, "password": PASSWORD_PRUEBA},
    )
    assert respuesta.status_code == 200
    return {"Authorization": f"Bearer {respuesta.json()['access_token']}"}


def test_resumen_agrega_situaciones_coherencia_y_movimientos(
    session_prueba: Session,
) -> None:
    ahora = datetime(2026, 10, 18, 15, 30, tzinfo=timezone.utc)
    usuario = crear_usuario(session_prueba)
    interna = Ubicacion(
        codigo="PATIO_A", nombre="Patio A", tipo="interna", activo=True
    )
    externa = Ubicacion(
        codigo="FUERA", nombre="Fuera del puerto", tipo="externa", activo=True
    )
    session_prueba.add_all([interna, externa])
    session_prueba.flush()

    dentro = Contenedor(
        codigo="CONT-DENTRO",
        ubicacion_actual=interna.nombre,
        ubicacion_actual_id=interna.id,
        estado="en_patio",
    )
    fuera = Contenedor(
        codigo="CONT-FUERA",
        ubicacion_actual=externa.nombre,
        ubicacion_actual_id=externa.id,
        estado="en_transito",
    )
    sin_confirmar = Contenedor(
        codigo="CONT-SIN-FK",
        ubicacion_actual="Texto histórico",
        ubicacion_actual_id=None,
        estado="disponible",
    )
    inconsistente = Contenedor(
        codigo="CONT-ERROR",
        ubicacion_actual=interna.nombre,
        ubicacion_actual_id=interna.id,
        estado="en_transito",
    )
    session_prueba.add_all([dentro, fuera, sin_confirmar, inconsistente])
    session_prueba.flush()

    movimientos = [
        Movimiento(
            contenedor_id=dentro.id,
            usuario_id=usuario.id,
            tipo="entrada",
            ubicacion_origen="Sin asignar",
            ubicacion_destino=interna.nombre,
            fecha_movimiento=ahora - timedelta(hours=1),
        ),
        Movimiento(
            contenedor_id=dentro.id,
            usuario_id=usuario.id,
            tipo="traslado",
            ubicacion_origen="Patio B",
            ubicacion_destino=interna.nombre,
            fecha_movimiento=ahora - timedelta(days=2),
        ),
        Movimiento(
            contenedor_id=fuera.id,
            usuario_id=usuario.id,
            tipo="salida",
            ubicacion_origen=interna.nombre,
            ubicacion_destino=externa.nombre,
            fecha_movimiento=ahora - timedelta(days=2, hours=1),
        ),
        Movimiento(
            contenedor_id=fuera.id,
            usuario_id=usuario.id,
            tipo="salida",
            ubicacion_origen=interna.nombre,
            ubicacion_destino=externa.nombre,
            fecha_movimiento=ahora - timedelta(days=8),
        ),
        Movimiento(
            contenedor_id=dentro.id,
            usuario_id=usuario.id,
            tipo="entrada",
            ubicacion_origen="Origen del límite",
            ubicacion_destino=interna.nombre,
            fecha_movimiento=datetime(
                2026, 10, 12, 0, 0, tzinfo=timezone.utc
            ),
        ),
        Movimiento(
            contenedor_id=dentro.id,
            usuario_id=usuario.id,
            tipo="traslado",
            ubicacion_origen="Fuera del período",
            ubicacion_destino=interna.nombre,
            fecha_movimiento=datetime(
                2026, 10, 19, 0, 0, tzinfo=timezone.utc
            ),
        ),
    ]
    session_prueba.add_all(movimientos)
    session_prueba.flush()

    resumen = DashboardService(session_prueba).obtener_resumen(ahora)

    assert resumen.zona_horaria == "UTC"
    assert resumen.periodo.desde.isoformat() == "2026-10-12"
    assert resumen.periodo.hasta.isoformat() == "2026-10-18"
    assert resumen.contenedores.model_dump() == {
        "dentro_puerto": 2,
        "fuera_puerto": 1,
        "presencia_sin_confirmar": 1,
        "inconsistentes": 1,
    }
    assert len(resumen.movimientos_ultimos_7_dias) == 7
    por_fecha = {
        item.fecha.isoformat(): item
        for item in resumen.movimientos_ultimos_7_dias
    }
    assert por_fecha["2026-10-18"].entrada == 1
    assert por_fecha["2026-10-16"].traslado == 1
    assert por_fecha["2026-10-16"].salida == 1
    assert por_fecha["2026-10-12"].entrada == 1
    assert por_fecha["2026-10-13"].total == 0
    assert len(resumen.ultimos_movimientos) == 6
    assert resumen.ultimos_movimientos[0].contenedor_codigo == "CONT-DENTRO"
    assert resumen.ultimos_movimientos[0].usuario_nombre == "Usuario operador"


def test_resumen_limita_los_movimientos_recientes_a_diez(
    session_prueba: Session,
) -> None:
    ahora = datetime(2026, 10, 18, 12, tzinfo=timezone.utc)
    usuario = crear_usuario(session_prueba)
    contenedor = Contenedor(
        codigo="CONT-001",
        ubicacion_actual="Sin asignar",
        ubicacion_actual_id=None,
        estado="disponible",
    )
    session_prueba.add(contenedor)
    session_prueba.flush()
    session_prueba.add_all(
        Movimiento(
            contenedor_id=contenedor.id,
            usuario_id=usuario.id,
            tipo="entrada",
            ubicacion_origen="Origen",
            ubicacion_destino="Destino",
            fecha_movimiento=ahora - timedelta(days=20, minutes=indice),
        )
        for indice in range(12)
    )
    session_prueba.flush()

    resumen = DashboardService(session_prueba).obtener_resumen(ahora)

    assert len(resumen.ultimos_movimientos) == 10
    fechas = [item.fecha_movimiento for item in resumen.ultimos_movimientos]
    assert fechas == sorted(fechas, reverse=True)


def test_periodo_se_interpreta_siempre_como_dias_utc(
    session_prueba: Session,
) -> None:
    # En Santiago todavía es 17 de octubre, pero el instante ya pertenece al
    # 18 de octubre en la convención UTC publicada por el endpoint.
    instante_santiago = datetime(
        2026,
        10,
        17,
        21,
        30,
        tzinfo=ZoneInfo("America/Santiago"),
    )

    resumen = DashboardService(session_prueba).obtener_resumen(
        instante_santiago
    )

    assert resumen.generado_en == datetime(
        2026, 10, 18, 0, 30, tzinfo=timezone.utc
    )
    assert resumen.periodo.desde.isoformat() == "2026-10-12"
    assert resumen.periodo.hasta.isoformat() == "2026-10-18"
    assert resumen.movimientos_ultimos_7_dias[-1].fecha.isoformat() == (
        "2026-10-18"
    )


def test_movimiento_historico_se_devuelve_sin_reinterpretar_sus_textos(
    session_prueba: Session,
) -> None:
    ahora = datetime(2026, 10, 18, 12, tzinfo=timezone.utc)
    usuario = crear_usuario(session_prueba)
    contenedor = Contenedor(
        codigo="LEGACY-001",
        ubicacion_actual="casa de Jose",
        ubicacion_actual_id=None,
        estado="disponible",
    )
    session_prueba.add(contenedor)
    session_prueba.flush()
    session_prueba.add(
        Movimiento(
            contenedor_id=contenedor.id,
            usuario_id=usuario.id,
            tipo=None,
            ubicacion_origen="patio viejo",
            ubicacion_destino="casa de Jose",
            fecha_movimiento=ahora - timedelta(days=1),
        )
    )
    session_prueba.flush()

    resumen = DashboardService(session_prueba).obtener_resumen(ahora)

    historico = resumen.ultimos_movimientos[0]
    assert historico.tipo is None
    assert historico.ubicacion_origen == "patio viejo"
    assert historico.ubicacion_destino == "casa de Jose"
    assert all(
        item.total == 0 for item in resumen.movimientos_ultimos_7_dias
    )


def test_resumen_vacio_incluye_los_siete_dias_en_cero(
    session_prueba: Session,
) -> None:
    ahora = datetime(2026, 10, 18, 12, tzinfo=timezone.utc)
    consultas: list[str] = []
    motor = session_prueba.get_bind()

    def registrar_consulta(
        connection, cursor, statement, parameters, context, executemany
    ) -> None:
        if statement.lstrip().upper().startswith("SELECT"):
            consultas.append(statement)

    event.listen(motor, "before_cursor_execute", registrar_consulta)
    try:
        resumen = DashboardService(session_prueba).obtener_resumen(ahora)
    finally:
        event.remove(motor, "before_cursor_execute", registrar_consulta)

    assert resumen.contenedores.model_dump() == {
        "dentro_puerto": 0,
        "fuera_puerto": 0,
        "presencia_sin_confirmar": 0,
        "inconsistentes": 0,
    }
    assert len(resumen.movimientos_ultimos_7_dias) == 7
    assert all(item.total == 0 for item in resumen.movimientos_ultimos_7_dias)
    assert resumen.ultimos_movimientos == []
    assert len(consultas) == 3


def test_endpoint_dashboard_requiere_jwt_y_acepta_ambos_roles(
    cliente: TestClient,
    session_prueba: Session,
) -> None:
    operador = headers_usuario(
        cliente,
        session_prueba,
        email="operador-dashboard@puertotrack.test",
        rol="operador",
    )
    supervisor = headers_usuario(
        cliente,
        session_prueba,
        email="supervisor-dashboard@puertotrack.test",
        rol="supervisor",
    )

    assert cliente.get("/dashboard/resumen").status_code == 401
    respuesta_operador = cliente.get(
        "/dashboard/resumen", headers=operador
    )
    respuesta_supervisor = cliente.get(
        "/dashboard/resumen", headers=supervisor
    )

    assert respuesta_operador.status_code == 200
    assert respuesta_supervisor.status_code == 200
    cuerpo = respuesta_operador.json()
    assert cuerpo["zona_horaria"] == "UTC"
    assert cuerpo["periodo"]["dias"] == 7
    assert len(cuerpo["movimientos_ultimos_7_dias"]) == 7
