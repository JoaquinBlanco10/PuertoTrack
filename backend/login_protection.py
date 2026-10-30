from collections import deque
from collections.abc import Callable
from math import ceil
from threading import Lock
from time import monotonic


VENTANA_INTENTOS_SEGUNDOS = 5 * 60
MAX_FALLOS_POR_EMAIL = 5
MAX_FALLOS_POR_IP = 20


class LimitadorLogin:
    """Limitador local de intentos fallidos para una instancia del backend."""

    def __init__(
        self,
        *,
        ventana_segundos: int = VENTANA_INTENTOS_SEGUNDOS,
        max_fallos_email: int = MAX_FALLOS_POR_EMAIL,
        max_fallos_ip: int = MAX_FALLOS_POR_IP,
        reloj: Callable[[], float] = monotonic,
    ) -> None:
        self.ventana_segundos = ventana_segundos
        self.max_fallos_email = max_fallos_email
        self.max_fallos_ip = max_fallos_ip
        self._reloj = reloj
        self._fallos_email: dict[str, deque[float]] = {}
        self._fallos_ip: dict[str, deque[float]] = {}
        self._en_curso_email: dict[str, int] = {}
        self._en_curso_ip: dict[str, int] = {}
        self._lock = Lock()

    def segundos_para_reintentar(self, *, email: str, ip: str) -> int:
        ahora = self._reloj()
        with self._lock:
            return self._segundos_bloqueo(email=email, ip=ip, ahora=ahora)

    def iniciar_intento(self, *, email: str, ip: str) -> int:
        """Reserva atómicamente capacidad para evitar ráfagas concurrentes."""

        ahora = self._reloj()
        with self._lock:
            espera = self._segundos_bloqueo(
                email=email, ip=ip, ahora=ahora
            )
            if espera:
                return espera
            self._en_curso_email[email] = (
                self._en_curso_email.get(email, 0) + 1
            )
            self._en_curso_ip[ip] = self._en_curso_ip.get(ip, 0) + 1
            return 0

    def registrar_fallo(self, *, email: str, ip: str) -> None:
        ahora = self._reloj()
        with self._lock:
            self._liberar_reserva(email=email, ip=ip)
            self._vigentes(self._fallos_email, email, ahora).append(ahora)
            self._vigentes(self._fallos_ip, ip, ahora).append(ahora)

    def registrar_exito(self, *, email: str, ip: str) -> None:
        with self._lock:
            self._liberar_reserva(email=email, ip=ip)
            self._fallos_email.pop(email, None)

    def cancelar_intento(self, *, email: str, ip: str) -> None:
        with self._lock:
            self._liberar_reserva(email=email, ip=ip)

    def reiniciar(self) -> None:
        """Limpia el estado; se utiliza también para aislar las pruebas."""

        with self._lock:
            self._fallos_email.clear()
            self._fallos_ip.clear()
            self._en_curso_email.clear()
            self._en_curso_ip.clear()

    def _segundos_bloqueo(
        self, *, email: str, ip: str, ahora: float
    ) -> int:
        fallos_email = self._vigentes(self._fallos_email, email, ahora)
        fallos_ip = self._vigentes(self._fallos_ip, ip, ahora)
        esperas: list[float] = []
        if (
            len(fallos_email) + self._en_curso_email.get(email, 0)
            >= self.max_fallos_email
        ):
            esperas.append(
                self.ventana_segundos - (ahora - fallos_email[0])
                if fallos_email
                else 1
            )
        if (
            len(fallos_ip) + self._en_curso_ip.get(ip, 0)
            >= self.max_fallos_ip
        ):
            esperas.append(
                self.ventana_segundos - (ahora - fallos_ip[0])
                if fallos_ip
                else 1
            )
        return max(1, ceil(max(esperas))) if esperas else 0

    def _liberar_reserva(self, *, email: str, ip: str) -> None:
        for registros, clave in (
            (self._en_curso_email, email),
            (self._en_curso_ip, ip),
        ):
            cantidad = registros.get(clave, 0)
            if cantidad <= 1:
                registros.pop(clave, None)
            else:
                registros[clave] = cantidad - 1

    def _vigentes(
        self,
        registros: dict[str, deque[float]],
        clave: str,
        ahora: float,
    ) -> deque[float]:
        intentos = registros.setdefault(clave, deque())
        limite_inferior = ahora - self.ventana_segundos
        while intentos and intentos[0] <= limite_inferior:
            intentos.popleft()
        if not intentos:
            registros.pop(clave, None)
            intentos = registros.setdefault(clave, deque())
        return intentos


limitador_login = LimitadorLogin()
