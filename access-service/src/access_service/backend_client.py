from urllib.parse import quote

import httpx

from .contracts import HechosOperacionales


class ContenedorDesconocido(Exception):
    pass


class BackendNoDisponible(Exception):
    pass


class ClienteBackend:
    def __init__(
        self,
        *,
        api_url: str,
        clave_interna: str,
        timeout: float,
        cliente: httpx.Client | None = None,
    ) -> None:
        self._propietario = cliente is None
        self._cliente = cliente or httpx.Client(
            base_url=api_url, timeout=timeout
        )
        self._clave = clave_interna

    def consultar_hechos(self, codigo: str) -> HechosOperacionales:
        try:
            respuesta = self._cliente.get(
                f"/internal/access/contenedores/{quote(codigo, safe='')}",
                headers={"X-PuertoTrack-Access-Key": self._clave},
            )
        except httpx.HTTPError as error:
            raise BackendNoDisponible("Backend no disponible.") from error
        if respuesta.status_code == 404:
            raise ContenedorDesconocido(codigo)
        if respuesta.status_code != 200:
            raise BackendNoDisponible(
                f"Backend respondió con estado {respuesta.status_code}."
            )
        try:
            return HechosOperacionales.model_validate(respuesta.json())
        except (ValueError, TypeError) as error:
            raise BackendNoDisponible("Contrato backend incompatible.") from error

    def cerrar(self) -> None:
        if self._propietario:
            self._cliente.close()
