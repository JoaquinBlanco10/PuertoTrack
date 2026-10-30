from sqlalchemy.orm import Session

from auditoria_service import AuditoriaService
from models import Movimiento, Usuario
from movimiento_strategies import MovimientoInvalido, obtener_estrategia
from repositories import (
    ContenedorRepository,
    MovimientoRepository,
    UbicacionRepository,
)
from schemas import ContextoMovimientoContenedor, MovimientoCrear


class ContenedorMovimientoNoEncontrado(Exception):
    pass


class ErrorRegistroMovimiento(Exception):
    pass


class MovimientoService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.contenedores = ContenedorRepository(session)
        self.movimientos = MovimientoRepository(session)
        self.ubicaciones = UbicacionRepository(session)
        self.auditoria = AuditoriaService(session)

    def registrar(
        self, datos: MovimientoCrear, usuario: Usuario
    ) -> Movimiento:
        try:
            contenedor = self.contenedores.buscar_por_id_para_actualizar(
                datos.contenedor_id
            )
            if contenedor is None:
                raise ContenedorMovimientoNoEncontrado(
                    "Contenedor no encontrado."
                )

            estrategia = obtener_estrategia(datos.tipo)
            destino = self.ubicaciones.buscar_por_id_para_actualizar(
                datos.ubicacion_destino_id
            )
            if destino is None:
                raise MovimientoInvalido(
                    "La ubicación de destino no existe."
                )
            datos_anteriores = {
                "estado": contenedor.estado,
                "ubicacion_actual": contenedor.ubicacion_actual,
                "ubicacion_actual_id": contenedor.ubicacion_actual_id,
            }
            resultado = estrategia.procesar(contenedor, destino)
            observacion = self._normalizar_observacion(datos.observacion)

            movimiento = Movimiento(
                contenedor_id=contenedor.id,
                usuario_id=usuario.id,
                tipo=datos.tipo.value,
                ubicacion_origen=resultado.origen,
                ubicacion_destino=resultado.destino,
                ubicacion_origen_id=resultado.origen_id,
                ubicacion_destino_id=resultado.destino_id,
                observacion=observacion,
            )
            contenedor.estado = resultado.nuevo_estado
            contenedor.ubicacion_actual = resultado.nueva_ubicacion
            contenedor.ubicacion_actual_id = resultado.nueva_ubicacion_id
            # Mantiene coherente la respuesta ORM en esta misma transaccion.
            contenedor.ubicacion_actual_catalogo = destino

            self.movimientos.crear(movimiento)
            self.auditoria.registrar(
                usuario_id=usuario.id,
                accion="registrar_movimiento",
                entidad="movimiento",
                entidad_id=movimiento.id,
                datos_anteriores=datos_anteriores,
                datos_nuevos={
                    "contenedor_id": contenedor.id,
                    "tipo": datos.tipo.value,
                    "ubicacion_origen": resultado.origen,
                    "ubicacion_destino": resultado.destino,
                    "ubicacion_origen_id": resultado.origen_id,
                    "ubicacion_destino_id": resultado.destino_id,
                    "estado": resultado.nuevo_estado,
                    "ubicacion_actual": resultado.nueva_ubicacion,
                    "ubicacion_actual_id": resultado.nueva_ubicacion_id,
                },
            )
            self.session.commit()
            return movimiento
        except (MovimientoInvalido, ContenedorMovimientoNoEncontrado):
            self.session.rollback()
            raise
        except Exception as error:
            self.session.rollback()
            raise ErrorRegistroMovimiento(
                "No se pudo registrar el movimiento."
            ) from error

    def listar(
        self,
        offset: int = 0,
        limite: int = 100,
        orden: str = "asc",
    ) -> list[Movimiento]:
        return self.movimientos.listar(
            offset=offset, limite=limite, orden=orden
        )

    def listar_por_contenedor(
        self,
        contenedor_id: int,
        offset: int = 0,
        limite: int = 100,
        orden: str = "asc",
    ) -> list[Movimiento]:
        if self.contenedores.buscar_por_id(contenedor_id) is None:
            raise ContenedorMovimientoNoEncontrado(
                "Contenedor no encontrado."
            )
        return self.movimientos.buscar_por_contenedor(
            contenedor_id,
            offset=offset,
            limite=limite,
            orden=orden,
        )

    def obtener_contexto_contenedor(
        self, contenedor_id: int
    ) -> ContextoMovimientoContenedor:
        if self.contenedores.buscar_por_id(contenedor_id) is None:
            raise ContenedorMovimientoNoEncontrado(
                "Contenedor no encontrado."
            )
        tiene_movimientos = self.movimientos.tiene_movimientos(contenedor_id)
        tiene_salida = self.movimientos.tiene_tipo(contenedor_id, "salida")
        if tiene_salida:
            etiqueta = "reingreso"
        elif not tiene_movimientos:
            etiqueta = "primera_entrada"
        else:
            etiqueta = "entrada"
        return ContextoMovimientoContenedor(
            contenedor_id=contenedor_id,
            tiene_movimientos=tiene_movimientos,
            tiene_salida_previa=tiene_salida,
            etiqueta_entrada=etiqueta,
        )

    @staticmethod
    def _normalizar_observacion(observacion: str | None) -> str | None:
        if observacion is None:
            return None
        observacion_limpia = observacion.strip()
        return observacion_limpia or None
