from abc import ABC, abstractmethod
from dataclasses import dataclass

from models import Contenedor, Ubicacion
from schemas import TipoMovimiento


class MovimientoInvalido(Exception):
    """La operación solicitada no respeta las reglas portuarias."""


@dataclass(frozen=True)
class ResultadoMovimiento:
    origen: str
    destino: str
    origen_id: int | None
    destino_id: int
    nuevo_estado: str
    nueva_ubicacion: str
    nueva_ubicacion_id: int


class MovimientoStrategy(ABC):
    tipo: TipoMovimiento

    @abstractmethod
    def procesar(
        self, contenedor: Contenedor, destino: Ubicacion
    ) -> ResultadoMovimiento:
        """Valida y calcula el cambio sin escribir en la base de datos."""

    @staticmethod
    def _obtener_origen(contenedor: Contenedor) -> str:
        origen = contenedor.ubicacion_actual.strip()
        if not origen:
            raise MovimientoInvalido(
                "El contenedor no tiene una ubicación actual válida."
            )
        return origen

    @staticmethod
    def _validar_coherencia_actual(contenedor: Contenedor) -> None:
        if contenedor.ubicacion_actual_id is None:
            if contenedor.estado == "en_patio":
                raise MovimientoInvalido(
                    "El contenedor figura en patio sin una ubicación confirmada. "
                    "Un supervisor debe regularizar sus datos históricos."
                )
            return
        if contenedor.coherencia_operacional != "coherente":
            raise MovimientoInvalido(
                "La ubicación catalogada y el estado del contenedor son "
                "incoherentes. Un supervisor debe regularizarlos antes de "
                "registrar otro movimiento."
            )

    @staticmethod
    def _validar_destino(
        destino: Ubicacion, tipo_esperado: str
    ) -> str:
        if not destino.activo:
            raise MovimientoInvalido(
                "La ubicación de destino está inactiva."
            )
        if destino.tipo != tipo_esperado:
            raise MovimientoInvalido(
                f"La ubicación de destino debe ser {tipo_esperado}."
            )
        if not destino.nombre.strip():
            raise MovimientoInvalido(
                "La ubicación de destino es obligatoria."
            )
        destino_limpio = destino.nombre.strip()
        if len(destino_limpio) > 255:
            raise MovimientoInvalido(
                "La ubicación de destino no puede superar 255 caracteres."
            )
        return destino_limpio

    @staticmethod
    def _validar_cambio_ubicacion(
        contenedor: Contenedor, destino: Ubicacion
    ) -> None:
        if contenedor.ubicacion_actual_id is not None:
            mismo_destino = contenedor.ubicacion_actual_id == destino.id
        else:
            mismo_destino = (
                contenedor.ubicacion_actual.strip().casefold()
                == destino.nombre.strip().casefold()
            )
        if mismo_destino:
            raise MovimientoInvalido(
                "La ubicación de destino debe ser distinta de la actual."
            )


class EntradaStrategy(MovimientoStrategy):
    tipo = TipoMovimiento.ENTRADA

    def procesar(
        self, contenedor: Contenedor, destino: Ubicacion
    ) -> ResultadoMovimiento:
        self._validar_coherencia_actual(contenedor)
        if contenedor.estado not in {"disponible", "en_transito"}:
            raise MovimientoInvalido(
                "La entrada solo está permitida desde disponible o en_transito."
            )
        origen = self._obtener_origen(contenedor)
        destino_valido = self._validar_destino(destino, "interna")
        self._validar_cambio_ubicacion(contenedor, destino)
        return ResultadoMovimiento(
            origen=origen,
            destino=destino_valido,
            origen_id=contenedor.ubicacion_actual_id,
            destino_id=destino.id,
            nuevo_estado="en_patio",
            nueva_ubicacion=destino_valido,
            nueva_ubicacion_id=destino.id,
        )


class TrasladoStrategy(MovimientoStrategy):
    tipo = TipoMovimiento.TRASLADO

    def procesar(
        self, contenedor: Contenedor, destino: Ubicacion
    ) -> ResultadoMovimiento:
        self._validar_coherencia_actual(contenedor)
        if contenedor.estado != "en_patio":
            raise MovimientoInvalido(
                "El traslado solo está permitido desde en_patio."
            )
        origen = self._obtener_origen(contenedor)
        destino_valido = self._validar_destino(destino, "interna")
        self._validar_cambio_ubicacion(contenedor, destino)
        return ResultadoMovimiento(
            origen=origen,
            destino=destino_valido,
            origen_id=contenedor.ubicacion_actual_id,
            destino_id=destino.id,
            nuevo_estado="en_patio",
            nueva_ubicacion=destino_valido,
            nueva_ubicacion_id=destino.id,
        )


class SalidaStrategy(MovimientoStrategy):
    tipo = TipoMovimiento.SALIDA

    def procesar(
        self, contenedor: Contenedor, destino: Ubicacion
    ) -> ResultadoMovimiento:
        self._validar_coherencia_actual(contenedor)
        if contenedor.estado != "en_patio":
            raise MovimientoInvalido(
                "La salida solo está permitida desde en_patio."
            )
        origen = self._obtener_origen(contenedor)
        destino_valido = self._validar_destino(destino, "externa")
        self._validar_cambio_ubicacion(contenedor, destino)
        return ResultadoMovimiento(
            origen=origen,
            destino=destino_valido,
            origen_id=contenedor.ubicacion_actual_id,
            destino_id=destino.id,
            nuevo_estado="en_transito",
            nueva_ubicacion=destino_valido,
            nueva_ubicacion_id=destino.id,
        )


ESTRATEGIAS: dict[TipoMovimiento, MovimientoStrategy] = {
    TipoMovimiento.ENTRADA: EntradaStrategy(),
    TipoMovimiento.TRASLADO: TrasladoStrategy(),
    TipoMovimiento.SALIDA: SalidaStrategy(),
}


def obtener_estrategia(tipo: TipoMovimiento) -> MovimientoStrategy:
    return ESTRATEGIAS[tipo]
