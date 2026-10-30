from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import Engine, func, select, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from contenedor_service import ContenedorService
from models import AuditLog, Contenedor, Movimiento, Ubicacion, Usuario
from movimiento_service import ErrorRegistroMovimiento, MovimientoService
from movimiento_strategies import MovimientoInvalido
from repositories import ContenedorRepository
from schemas import MovimientoCrear, TipoMovimiento, UbicacionActualizar
from ubicacion_service import UbicacionService


pytestmark = pytest.mark.postgres_integration


def _sufijo() -> str:
    return uuid4().hex[:10].upper()


def _usuario(session: Session, sufijo: str) -> Usuario:
    usuario = Usuario(
        nombre=f"Supervisor {sufijo}",
        email=f"supervisor-{sufijo.casefold()}@postgres.test",
        password_hash="hash-exclusivo-de-pruebas",
        rol="supervisor",
        activo=True,
    )
    session.add(usuario)
    session.flush()
    return usuario


def _ubicacion(
    session: Session,
    sufijo: str,
    *,
    nombre: str,
    tipo: str = "interna",
) -> Ubicacion:
    ubicacion = Ubicacion(
        codigo=f"{tipo[:3].upper()}_{sufijo}"[:30],
        nombre=nombre,
        tipo=tipo,
        activo=True,
    )
    session.add(ubicacion)
    session.flush()
    return ubicacion


def _contenedor(
    session: Session,
    sufijo: str,
    *,
    estado: str = "disponible",
    ubicacion: Ubicacion | None = None,
    texto: str = "Sin asignar",
) -> Contenedor:
    contenedor = Contenedor(
        codigo=f"PG{sufijo}"[:20],
        ubicacion_actual=ubicacion.nombre if ubicacion is not None else texto,
        ubicacion_actual_id=ubicacion.id if ubicacion is not None else None,
        estado=estado,
    )
    if ubicacion is not None:
        contenedor.ubicacion_actual_catalogo = ubicacion
    session.add(contenedor)
    session.flush()
    return contenedor


def test_registro_movimiento_actualiza_y_audita_atomicamente(
    session_postgres: Session,
) -> None:
    sufijo = _sufijo()
    usuario = _usuario(session_postgres, sufijo)
    destino = _ubicacion(
        session_postgres, sufijo, nombre=f"Patio integración {sufijo}"
    )
    contenedor = _contenedor(session_postgres, sufijo)

    movimiento = MovimientoService(session_postgres).registrar(
        MovimientoCrear(
            contenedor_id=contenedor.id,
            tipo=TipoMovimiento.ENTRADA,
            ubicacion_destino_id=destino.id,
            observacion="Ingreso verificado en PostgreSQL",
        ),
        usuario,
    )

    session_postgres.refresh(contenedor)
    auditoria = session_postgres.scalar(
        select(AuditLog).where(
            AuditLog.entidad == "movimiento",
            AuditLog.entidad_id == movimiento.id,
        )
    )
    assert movimiento.tipo == "entrada"
    assert movimiento.ubicacion_destino_id == destino.id
    assert contenedor.estado == "en_patio"
    assert contenedor.ubicacion_actual_id == destino.id
    assert auditoria is not None
    assert auditoria.usuario_id == usuario.id


def test_select_for_update_bloquea_una_segunda_transaccion(
    motor_postgres: Engine,
) -> None:
    sufijo = _sufijo()
    with Session(motor_postgres) as preparacion:
        contenedor = _contenedor(preparacion, sufijo)
        preparacion.commit()
        contenedor_id = contenedor.id

    primera = Session(motor_postgres)
    try:
        bloqueado = ContenedorRepository(
            primera
        ).buscar_por_id_para_actualizar(contenedor_id)
        assert bloqueado is not None

        def intentar_segundo_bloqueo() -> str | None:
            with Session(motor_postgres) as segunda:
                try:
                    segunda.execute(text("SET LOCAL lock_timeout = '250ms'"))
                    ContenedorRepository(
                        segunda
                    ).buscar_por_id_para_actualizar(contenedor_id)
                except OperationalError as error:
                    segunda.rollback()
                    return getattr(error.orig, "sqlstate", None)
                segunda.rollback()
                return None

        with ThreadPoolExecutor(max_workers=1) as ejecutor:
            codigo_sqlstate = ejecutor.submit(
                intentar_segundo_bloqueo
            ).result(timeout=5)

        assert codigo_sqlstate == "55P03"
    finally:
        primera.rollback()
        primera.close()


def test_dos_movimientos_concurrentes_solo_confirman_uno(
    motor_postgres: Engine,
) -> None:
    sufijo = _sufijo()
    with Session(motor_postgres) as preparacion:
        usuario = _usuario(preparacion, sufijo)
        destino_a = _ubicacion(
            preparacion, f"A{sufijo}", nombre=f"Patio A {sufijo}"
        )
        destino_b = _ubicacion(
            preparacion, f"B{sufijo}", nombre=f"Patio B {sufijo}"
        )
        contenedor = _contenedor(preparacion, sufijo)
        preparacion.commit()
        usuario_id = usuario.id
        contenedor_id = contenedor.id
        destinos = (destino_a.id, destino_b.id)

    barrera = Barrier(2)

    def registrar_entrada(destino_id: int) -> str:
        with Session(motor_postgres) as session:
            usuario_local = session.get(Usuario, usuario_id)
            assert usuario_local is not None
            barrera.wait(timeout=5)
            try:
                MovimientoService(session).registrar(
                    MovimientoCrear(
                        contenedor_id=contenedor_id,
                        tipo=TipoMovimiento.ENTRADA,
                        ubicacion_destino_id=destino_id,
                    ),
                    usuario_local,
                )
                return "confirmado"
            except MovimientoInvalido:
                return "rechazado"

    with ThreadPoolExecutor(max_workers=2) as ejecutor:
        resultados = list(ejecutor.map(registrar_entrada, destinos))

    assert sorted(resultados) == ["confirmado", "rechazado"]
    with Session(motor_postgres) as verificacion:
        actual = verificacion.get(Contenedor, contenedor_id)
        movimientos = verificacion.scalars(
            select(Movimiento).where(
                Movimiento.contenedor_id == contenedor_id
            )
        ).all()
        assert actual is not None
        assert actual.estado == "en_patio"
        assert len(movimientos) == 1
        auditorias = verificacion.scalar(
            select(func.count(AuditLog.id)).where(
                AuditLog.entidad == "movimiento",
                AuditLog.entidad_id == movimientos[0].id,
            )
        )
        assert auditorias == 1


def test_fallo_de_auditoria_revierte_movimiento_y_contenedor(
    motor_postgres: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    sufijo = _sufijo()
    with Session(motor_postgres) as preparacion:
        usuario = _usuario(preparacion, sufijo)
        destino = _ubicacion(
            preparacion, sufijo, nombre=f"Patio rollback {sufijo}"
        )
        contenedor = _contenedor(preparacion, sufijo)
        auditorias_antes = preparacion.scalar(
            select(func.count(AuditLog.id))
        )
        preparacion.commit()
        usuario_id = usuario.id
        destino_id = destino.id
        contenedor_id = contenedor.id

    with Session(motor_postgres) as session:
        usuario_local = session.get(Usuario, usuario_id)
        assert usuario_local is not None
        servicio = MovimientoService(session)

        def fallar_auditoria(**kwargs: object) -> None:
            raise RuntimeError("fallo controlado de auditoría")

        monkeypatch.setattr(servicio.auditoria, "registrar", fallar_auditoria)
        with pytest.raises(ErrorRegistroMovimiento):
            servicio.registrar(
                MovimientoCrear(
                    contenedor_id=contenedor_id,
                    tipo=TipoMovimiento.ENTRADA,
                    ubicacion_destino_id=destino_id,
                ),
                usuario_local,
            )

    with Session(motor_postgres) as verificacion:
        actual = verificacion.get(Contenedor, contenedor_id)
        assert actual is not None
        assert actual.estado == "disponible"
        assert actual.ubicacion_actual_id is None
        assert verificacion.scalar(
            select(func.count(Movimiento.id)).where(
                Movimiento.contenedor_id == contenedor_id
            )
        ) == 0
        assert verificacion.scalar(select(func.count(AuditLog.id))) == (
            auditorias_antes
        )


@pytest.mark.parametrize("entidad", ["contenedor", "ubicacion"])
def test_restricciones_unicas_se_aplican_en_postgres(
    session_postgres: Session, entidad: str
) -> None:
    sufijo = _sufijo()
    if entidad == "contenedor":
        primero = Contenedor(
            codigo=f"UNQ{sufijo}"[:20],
            ubicacion_actual="Sin asignar",
            estado="disponible",
        )
        duplicado = Contenedor(
            codigo=primero.codigo,
            ubicacion_actual="Sin asignar",
            estado="disponible",
        )
    else:
        primero = Ubicacion(
            codigo=f"UNQ_{sufijo}"[:30],
            nombre="Única uno",
            tipo="interna",
            activo=True,
        )
        duplicado = Ubicacion(
            codigo=primero.codigo,
            nombre="Única dos",
            tipo="externa",
            activo=True,
        )

    session_postgres.add(primero)
    session_postgres.flush()
    session_postgres.add(duplicado)
    with pytest.raises(IntegrityError):
        session_postgres.flush()
    session_postgres.rollback()


def test_regularizacion_historica_es_atomica_y_no_inventa_movimientos(
    session_postgres: Session,
) -> None:
    sufijo = _sufijo()
    usuario = _usuario(session_postgres, sufijo)
    ubicacion = _ubicacion(
        session_postgres, sufijo, nombre=f"Patio regularizado {sufijo}"
    )
    contenedor = _contenedor(
        session_postgres,
        sufijo,
        estado="en_patio",
        texto="Texto histórico ambiguo",
    )
    historico = Movimiento(
        contenedor_id=contenedor.id,
        usuario_id=usuario.id,
        tipo=None,
        ubicacion_origen="Origen histórico",
        ubicacion_destino="Destino histórico",
        ubicacion_origen_id=None,
        ubicacion_destino_id=None,
        observacion="Evidencia histórica",
    )
    session_postgres.add(historico)
    session_postgres.flush()
    movimientos_antes = session_postgres.scalar(
        select(func.count(Movimiento.id)).where(
            Movimiento.contenedor_id == contenedor.id
        )
    )

    actualizado = ContenedorService(session_postgres).regularizar_ubicacion(
        contenedor.id,
        ubicacion.id,
        "en_patio",
        "Documento histórico portuario verificado",
        usuario,
    )

    auditoria = session_postgres.scalar(
        select(AuditLog).where(
            AuditLog.entidad == "contenedor",
            AuditLog.entidad_id == contenedor.id,
            AuditLog.accion == "regularizar_ubicacion",
        )
    )
    assert actualizado.ubicacion_actual_id == ubicacion.id
    assert actualizado.estado == "en_patio"
    assert session_postgres.scalar(
        select(func.count(Movimiento.id)).where(
            Movimiento.contenedor_id == contenedor.id
        )
    ) == movimientos_antes
    assert auditoria is not None
    assert auditoria.datos_nuevos is not None
    assert auditoria.datos_nuevos["justificacion"] == (
        "Documento histórico portuario verificado"
    )


def test_renombrado_actualiza_nombre_canonico_y_conserva_snapshots(
    session_postgres: Session,
) -> None:
    sufijo = _sufijo()
    usuario = _usuario(session_postgres, sufijo)
    nombre_anterior = f"Patio antiguo {sufijo}"
    ubicacion = _ubicacion(
        session_postgres, sufijo, nombre=nombre_anterior
    )
    contenedor = _contenedor(
        session_postgres,
        sufijo,
        estado="en_patio",
        ubicacion=ubicacion,
    )
    historico = Movimiento(
        contenedor_id=contenedor.id,
        usuario_id=usuario.id,
        tipo="traslado",
        ubicacion_origen="Otro patio histórico",
        ubicacion_destino=nombre_anterior,
        ubicacion_origen_id=None,
        ubicacion_destino_id=ubicacion.id,
    )
    session_postgres.add(historico)
    session_postgres.flush()

    nombre_nuevo = f"Patio vigente {sufijo}"
    UbicacionService(session_postgres).actualizar(
        ubicacion.id,
        UbicacionActualizar(nombre=nombre_nuevo),
        usuario,
    )

    session_postgres.refresh(contenedor)
    session_postgres.refresh(historico)
    texto_persistido = session_postgres.scalar(
        select(Contenedor._ubicacion_actual_texto).where(
            Contenedor.id == contenedor.id
        )
    )
    auditoria = session_postgres.scalar(
        select(AuditLog).where(
            AuditLog.entidad == "ubicacion",
            AuditLog.entidad_id == ubicacion.id,
            AuditLog.accion == "actualizar",
        )
    )
    assert contenedor.ubicacion_actual == nombre_nuevo
    assert texto_persistido == nombre_anterior
    assert historico.ubicacion_destino == nombre_anterior
    assert auditoria is not None
    assert auditoria.datos_anteriores is not None
    assert auditoria.datos_anteriores["nombre"] == nombre_anterior
