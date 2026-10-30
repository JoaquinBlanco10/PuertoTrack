import os

import httpx
from pydantic import TypeAdapter, ValidationError

from schemas import DecisionAccesoRespuesta


class ConfiguracionAccesosInvalida(RuntimeError):
    pass


class ServicioAccesosNoDisponible(RuntimeError):
    pass


class AccessServiceClient:
    def __init__(self) -> None:
        self.url = os.getenv(
            "ACCESS_SERVICE_URL", "http://127.0.0.1:8200"
        ).strip().rstrip("/")
        self.clave = os.getenv("ACCESS_INTERNAL_API_KEY", "")
        if not self.url or len(self.clave.encode("utf-8")) < 32:
            raise ConfiguracionAccesosInvalida(
                "La consulta del servicio de accesos no está configurada."
            )

    def listar_decisiones(
        self,
        *,
        limite: int,
        resultado: str | None,
    ) -> list[DecisionAccesoRespuesta]:
        parametros: dict[str, str | int] = {"limite": limite}
        if resultado is not None:
            parametros["resultado"] = resultado
        try:
            respuesta = httpx.get(
                f"{self.url}/internal/decisiones",
                params=parametros,
                headers={"X-PuertoTrack-Access-Key": self.clave},
                timeout=3.0,
            )
            respuesta.raise_for_status()
            return TypeAdapter(list[DecisionAccesoRespuesta]).validate_python(
                respuesta.json()
            )
        except (httpx.HTTPError, ValueError, ValidationError) as error:
            raise ServicioAccesosNoDisponible(
                "No fue posible consultar el servicio de accesos."
            ) from error
