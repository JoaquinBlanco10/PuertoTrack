from collections import Counter, deque
from threading import Lock
from time import monotonic

from .contracts import EstadoProcesamiento, ProcesamientoRFID


class AlmacenProcesamientos:
    """Estado efímero, acotado y seguro para callbacks MQTT concurrentes."""

    def __init__(self, *, max_registros: int, ttl_deduplicacion: int) -> None:
        self._max_registros = max_registros
        self._ttl_deduplicacion = ttl_deduplicacion
        self._registros: deque[ProcesamientoRFID] = deque(maxlen=max_registros)
        self._eventos_vistos: dict[str, float] = {}
        self._lock = Lock()

    def reservar_evento(self, evento_id: str) -> bool:
        ahora = monotonic()
        with self._lock:
            self._depurar_eventos(ahora)
            if evento_id in self._eventos_vistos:
                return False
            self._eventos_vistos[evento_id] = ahora
            return True

    def liberar_evento(self, evento_id: str) -> None:
        """Permite reintentar únicamente errores transitorios de integración."""

        with self._lock:
            self._eventos_vistos.pop(evento_id, None)

    def registrar(self, registro: ProcesamientoRFID) -> None:
        with self._lock:
            self._registros.append(registro)

    def listar(
        self,
        *,
        limite: int,
        estado: EstadoProcesamiento | None = None,
    ) -> list[ProcesamientoRFID]:
        with self._lock:
            registros = list(reversed(self._registros))
        if estado is not None:
            registros = [item for item in registros if item.estado == estado]
        return registros[:limite]

    def buscar_evento(self, evento_id: str) -> ProcesamientoRFID | None:
        with self._lock:
            return next(
                (
                    item
                    for item in reversed(self._registros)
                    if item.evento_id is not None
                    and str(item.evento_id) == evento_id
                ),
                None,
            )

    def resumen(self) -> tuple[int, dict[EstadoProcesamiento, int]]:
        with self._lock:
            registros = list(self._registros)
        conteo = Counter(item.estado for item in registros)
        return len(registros), {
            estado: conteo.get(estado, 0) for estado in EstadoProcesamiento
        }

    def _depurar_eventos(self, ahora: float) -> None:
        limite = ahora - self._ttl_deduplicacion
        vencidos = [
            evento_id
            for evento_id, instante in self._eventos_vistos.items()
            if instante <= limite
        ]
        for evento_id in vencidos:
            self._eventos_vistos.pop(evento_id, None)
