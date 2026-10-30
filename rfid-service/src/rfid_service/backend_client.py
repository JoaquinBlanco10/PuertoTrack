from urllib.parse import quote

import httpx

from .contracts import ContenedorIdentificado


class CodigoContenedorDesconocido(Exception):
    pass


class ErrorBackendOperacional(Exception):
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
        self._clave_interna = clave_interna
        self._propietario_cliente = cliente is None
        self._cliente = cliente or httpx.Client(
            base_url=api_url,
            timeout=timeout,
        )

    def identificar(self, codigo: str) -> ContenedorIdentificado:
        try:
            respuesta = self._cliente.get(
                f"/internal/rfid/contenedores/{quote(codigo, safe='')}",
                headers={
                    "Accept": "application/json",
                    "X-PuertoTrack-Internal-Key": self._clave_interna,
                },
            )
        except httpx.HTTPError as error:
            raise ErrorBackendOperacional(
                "No fue posible consultar el backend operacional."
            ) from error
        if respuesta.status_code == 404:
            raise CodigoContenedorDesconocido(codigo)
        if respuesta.status_code != 200:
            raise ErrorBackendOperacional(
                f"El backend respondió con estado {respuesta.status_code}."
            )
        try:
            return ContenedorIdentificado.model_validate(respuesta.json())
        except (ValueError, TypeError) as error:
            raise ErrorBackendOperacional(
                "El backend devolvió una respuesta incompatible."
            ) from error

    def cerrar(self) -> None:
        if self._propietario_cliente:
            self._cliente.close()
