from collections import Counter, deque
from threading import Lock
from time import monotonic
from typing import Callable

from .contracts import DecisionAcceso, ResultadoAcceso


class AlmacenDecisiones:
    def __init__(
        self,
        *,
        max_decisiones: int,
        ttl_deduplicacion: int,
        ttl_decisiones: int = 3600,
        reloj: Callable[[], float] = monotonic,
    ) -> None:
        self._decisiones: deque[tuple[float, DecisionAcceso]] = deque(
            maxlen=max_decisiones
        )
        self._eventos: dict[str, float] = {}
        self._ttl_deduplicacion = ttl_deduplicacion
        self._ttl_decisiones = ttl_decisiones
        self._reloj = reloj
        self._duplicados = 0
        self._invalidos = 0
        self._lock = Lock()

    def reservar_evento(self, evento_id: str) -> bool:
        ahora = self._reloj()
        with self._lock:
            limite = ahora - self._ttl_deduplicacion
            for vencido in [
                clave for clave, instante in self._eventos.items()
                if instante <= limite
            ]:
                self._eventos.pop(vencido, None)
            if evento_id in self._eventos:
                self._duplicados += 1
                return False
            self._eventos[evento_id] = ahora
            return True

    def registrar_invalido(self) -> None:
        with self._lock:
            self._invalidos += 1

    def registrar(self, decision: DecisionAcceso) -> None:
        with self._lock:
            ahora = self._reloj()
            self._purgar_decisiones(ahora)
            self._decisiones.append((ahora, decision))

    def listar(
        self, *, limite: int, resultado: ResultadoAcceso | None = None
    ) -> list[DecisionAcceso]:
        with self._lock:
            self._purgar_decisiones(self._reloj())
            decisiones = [
                decision for _, decision in reversed(self._decisiones)
            ]
        if resultado is not None:
            decisiones = [d for d in decisiones if d.resultado == resultado]
        return decisiones[:limite]

    def buscar_evento(self, evento_id: str) -> DecisionAcceso | None:
        with self._lock:
            self._purgar_decisiones(self._reloj())
            return next(
                (
                    decision
                    for _, decision in reversed(self._decisiones)
                    if str(decision.evento_id) == evento_id
                ),
                None,
            )

    def resumen(self) -> tuple[int, int, int, dict[ResultadoAcceso, int]]:
        with self._lock:
            self._purgar_decisiones(self._reloj())
            decisiones = [decision for _, decision in self._decisiones]
            duplicados = self._duplicados
            invalidos = self._invalidos
        conteo = Counter(item.resultado for item in decisiones)
        return (
            len(decisiones),
            duplicados,
            invalidos,
            {resultado: conteo.get(resultado, 0) for resultado in ResultadoAcceso},
        )

    def _purgar_decisiones(self, ahora: float) -> None:
        limite = ahora - self._ttl_decisiones
        while self._decisiones and self._decisiones[0][0] <= limite:
            self._decisiones.popleft()
