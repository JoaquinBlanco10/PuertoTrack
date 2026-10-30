from typing import Generic, TypeVar

from datetime import datetime

from sqlalchemy import Date, case, cast, exists, func, or_, select
from sqlalchemy.orm import Session

from models import AuditLog, Contenedor, Movimiento, Ubicacion, Usuario


ModeloT = TypeVar(
    "ModeloT", Usuario, Contenedor, Movimiento, Ubicacion, AuditLog
)


class RepositorioBase(Generic[ModeloT]):
    """Operaciones de persistencia compartidas por todos los repositorios."""

    modelo: type[ModeloT]

    def __init__(self, session: Session) -> None:
        self.session = session

    def crear(self, entidad: ModeloT) -> ModeloT:
        self.session.add(entidad)
        self.session.flush()
        self.session.refresh(entidad)
        return entidad

    def buscar_por_id(self, entidad_id: int) -> ModeloT | None:
        return self.session.get(self.modelo, entidad_id)

    def actualizar(self, entidad: ModeloT) -> ModeloT:
        self.session.flush()
        self.session.refresh(entidad)
        return entidad

    def listar(self, offset: int = 0, limite: int = 100) -> list[ModeloT]:
        consulta = (
            select(self.modelo)
            .order_by(self.modelo.id)
            .offset(offset)
            .limit(limite)
        )
        return list(self.session.scalars(consulta).all())


class UsuarioRepository(RepositorioBase[Usuario]):
    modelo = Usuario

    def buscar_por_email(self, email: str) -> Usuario | None:
        consulta = select(Usuario).where(Usuario.email == email)
        return self.session.scalar(consulta)


class ContenedorRepository(RepositorioBase[Contenedor]):
    modelo = Contenedor

    def _marcar_evidencia(
        self, contenedores: list[Contenedor]
    ) -> list[Contenedor]:
        if not contenedores:
            return contenedores
        ids = [contenedor.id for contenedor in contenedores]
        con_movimientos = set(
            self.session.scalars(
                select(Movimiento.contenedor_id)
                .where(Movimiento.contenedor_id.in_(ids))
                .distinct()
            ).all()
        )
        con_regularizacion_previa = set(
            self.session.scalars(
                select(AuditLog.entidad_id)
                .where(
                    AuditLog.entidad == "contenedor",
                    AuditLog.accion == "regularizar_ubicacion",
                    AuditLog.entidad_id.in_(ids),
                )
                .distinct()
            ).all()
        )
        for contenedor in contenedores:
            contenedor._tiene_evidencia_historica = (
                contenedor.id in con_movimientos
                or contenedor.id in con_regularizacion_previa
            )
        return contenedores

    def buscar_por_id(self, entidad_id: int) -> Contenedor | None:
        contenedor = self.session.get(Contenedor, entidad_id)
        if contenedor is not None:
            self._marcar_evidencia([contenedor])
        return contenedor

    def buscar_por_codigo(self, codigo: str) -> Contenedor | None:
        consulta = select(Contenedor).where(Contenedor.codigo == codigo)
        contenedor = self.session.scalar(consulta)
        if contenedor is not None:
            self._marcar_evidencia([contenedor])
        return contenedor

    def buscar_por_id_para_actualizar(
        self, contenedor_id: int
    ) -> Contenedor | None:
        consulta = (
            select(Contenedor)
            .where(Contenedor.id == contenedor_id)
            .with_for_update()
        )
        contenedor = self.session.scalar(consulta)
        if contenedor is not None:
            self._marcar_evidencia([contenedor])
        return contenedor

    def listar(
        self,
        offset: int = 0,
        limite: int = 100,
        situacion: str | None = None,
        coherencia: str | None = None,
        codigo: str | None = None,
    ) -> list[Contenedor]:
        consulta = select(Contenedor)
        if situacion is not None or coherencia is not None:
            consulta = consulta.outerjoin(
                Ubicacion,
                Contenedor.ubicacion_actual_id == Ubicacion.id,
            )
        if situacion is not None:
            consulta = consulta.where(Contenedor.situacion == situacion)
        if coherencia is not None:
            consulta = consulta.where(
                Contenedor.coherencia_operacional == coherencia
            )
        if codigo is not None:
            consulta = consulta.where(
                Contenedor.codigo.startswith(codigo, autoescape=True)
            )
        consulta = (
            consulta.order_by(Contenedor.id).offset(offset).limit(limite)
        )
        return self._marcar_evidencia(
            list(self.session.scalars(consulta).all())
        )


class UbicacionRepository(RepositorioBase[Ubicacion]):
    modelo = Ubicacion

    def buscar_por_codigo(self, codigo: str) -> Ubicacion | None:
        return self.session.scalar(
            select(Ubicacion).where(Ubicacion.codigo == codigo)
        )

    def buscar_por_id_para_actualizar(
        self, ubicacion_id: int
    ) -> Ubicacion | None:
        return self.session.scalar(
            select(Ubicacion)
            .where(Ubicacion.id == ubicacion_id)
            .with_for_update()
        )

    def listar_filtradas(
        self,
        *,
        solo_activas: bool = True,
        tipo: str | None = None,
        offset: int = 0,
        limite: int = 100,
    ) -> list[Ubicacion]:
        consulta = select(Ubicacion)
        if solo_activas:
            consulta = consulta.where(Ubicacion.activo.is_(True))
        if tipo is not None:
            consulta = consulta.where(Ubicacion.tipo == tipo)
        consulta = (
            consulta.order_by(Ubicacion.codigo).offset(offset).limit(limite)
        )
        return list(self.session.scalars(consulta).all())

    def esta_utilizada(self, ubicacion_id: int) -> bool:
        en_contenedores = exists().where(
            Contenedor.ubicacion_actual_id == ubicacion_id
        )
        en_movimientos = exists().where(
            or_(
                Movimiento.ubicacion_origen_id == ubicacion_id,
                Movimiento.ubicacion_destino_id == ubicacion_id,
            )
        )
        return bool(
            self.session.scalar(select(en_contenedores))
            or self.session.scalar(select(en_movimientos))
        )


class MovimientoRepository(RepositorioBase[Movimiento]):
    modelo = Movimiento

    @staticmethod
    def _orden(orden: str):
        if orden == "desc":
            return (
                Movimiento.fecha_movimiento.desc(),
                Movimiento.id.desc(),
            )
        return (
            Movimiento.fecha_movimiento.asc(),
            Movimiento.id.asc(),
        )

    def listar(
        self,
        offset: int = 0,
        limite: int = 100,
        orden: str = "asc",
    ) -> list[Movimiento]:
        consulta = (
            select(Movimiento)
            .order_by(*self._orden(orden))
            .offset(offset)
            .limit(limite)
        )
        return list(self.session.scalars(consulta).all())

    def buscar_por_contenedor(
        self,
        contenedor_id: int,
        offset: int = 0,
        limite: int = 100,
        orden: str = "asc",
    ) -> list[Movimiento]:
        consulta = (
            select(Movimiento)
            .where(Movimiento.contenedor_id == contenedor_id)
            .order_by(*self._orden(orden))
            .offset(offset)
            .limit(limite)
        )
        return list(self.session.scalars(consulta).all())

    def buscar_por_usuario(
        self,
        usuario_id: int,
        offset: int = 0,
        limite: int = 100,
    ) -> list[Movimiento]:
        consulta = (
            select(Movimiento)
            .where(Movimiento.usuario_id == usuario_id)
            .order_by(Movimiento.id)
            .offset(offset)
            .limit(limite)
        )
        return list(self.session.scalars(consulta).all())

    def tiene_movimientos(self, contenedor_id: int) -> bool:
        consulta = select(
            exists().where(Movimiento.contenedor_id == contenedor_id)
        )
        return bool(self.session.scalar(consulta))

    def tiene_tipo(self, contenedor_id: int, tipo: str) -> bool:
        consulta = select(
            exists().where(
                Movimiento.contenedor_id == contenedor_id,
                Movimiento.tipo == tipo,
            )
        )
        return bool(self.session.scalar(consulta))


class DashboardRepository:
    """Consultas de lectura agregadas para el panel operativo."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def contar_contenedores(self) -> dict[str, int]:
        consulta = (
            select(
                func.sum(
                    case((Contenedor.situacion == "dentro_puerto", 1), else_=0)
                ).label("dentro_puerto"),
                func.sum(
                    case((Contenedor.situacion == "fuera_puerto", 1), else_=0)
                ).label("fuera_puerto"),
                func.sum(
                    case(
                        (
                            Contenedor.situacion
                            == "presencia_sin_confirmar",
                            1,
                        ),
                        else_=0,
                    )
                ).label("presencia_sin_confirmar"),
                func.sum(
                    case(
                        (
                            Contenedor.coherencia_operacional
                            == "inconsistente",
                            1,
                        ),
                        else_=0,
                    )
                ).label("inconsistentes"),
            )
            .select_from(Contenedor)
            .outerjoin(Ubicacion, Contenedor.ubicacion_actual_id == Ubicacion.id)
        )
        fila = self.session.execute(consulta).one()
        return {
            "dentro_puerto": int(fila.dentro_puerto or 0),
            "fuera_puerto": int(fila.fuera_puerto or 0),
            "presencia_sin_confirmar": int(
                fila.presencia_sin_confirmar or 0
            ),
            "inconsistentes": int(fila.inconsistentes or 0),
        }

    def agrupar_movimientos_por_dia(
        self,
        *,
        desde: datetime,
        hasta_exclusivo: datetime,
    ) -> list[tuple[object, str, int]]:
        dialecto = self.session.get_bind().dialect.name
        if dialecto == "postgresql":
            dia = cast(
                func.timezone("UTC", Movimiento.fecha_movimiento), Date
            )
        else:
            # SQLite se utiliza únicamente en la suite aislada de pruebas.
            dia = func.date(Movimiento.fecha_movimiento)

        consulta = (
            select(
                dia.label("dia"),
                Movimiento.tipo,
                func.count(Movimiento.id).label("cantidad"),
            )
            .where(
                Movimiento.fecha_movimiento >= desde,
                Movimiento.fecha_movimiento < hasta_exclusivo,
                Movimiento.tipo.in_(("entrada", "traslado", "salida")),
            )
            .group_by(dia, Movimiento.tipo)
            .order_by(dia, Movimiento.tipo)
        )
        return [
            (fila.dia, fila.tipo, int(fila.cantidad))
            for fila in self.session.execute(consulta)
        ]

    def ultimos_movimientos(self, limite: int = 10) -> list[dict[str, object]]:
        consulta = (
            select(
                Movimiento.id,
                Movimiento.contenedor_id,
                Contenedor.codigo.label("contenedor_codigo"),
                Movimiento.usuario_id,
                Usuario.nombre.label("usuario_nombre"),
                Movimiento.tipo,
                Movimiento.ubicacion_origen,
                Movimiento.ubicacion_destino,
                Movimiento.fecha_movimiento,
            )
            .join(Contenedor, Contenedor.id == Movimiento.contenedor_id)
            .join(Usuario, Usuario.id == Movimiento.usuario_id)
            .order_by(
                Movimiento.fecha_movimiento.desc(), Movimiento.id.desc()
            )
            .limit(limite)
        )
        return [dict(fila._mapping) for fila in self.session.execute(consulta)]

class AuditLogRepository(RepositorioBase[AuditLog]):
    modelo = AuditLog

    def listar_con_filtros(
        self,
        *,
        usuario_id: int | None = None,
        entidad: str | None = None,
        entidad_id: int | None = None,
        accion: str | None = None,
        offset: int = 0,
        limite: int = 100,
    ) -> list[AuditLog]:
        consulta = select(AuditLog)
        if usuario_id is not None:
            consulta = consulta.where(AuditLog.usuario_id == usuario_id)
        if entidad is not None:
            consulta = consulta.where(AuditLog.entidad == entidad)
        if entidad_id is not None:
            consulta = consulta.where(AuditLog.entidad_id == entidad_id)
        if accion is not None:
            consulta = consulta.where(AuditLog.accion == accion)

        consulta = (
            consulta.order_by(AuditLog.id.desc())
            .offset(offset)
            .limit(limite)
        )
        return list(self.session.scalars(consulta).all())

