import os
from dataclasses import dataclass


class ConfiguracionInvalida(RuntimeError):
    pass


def _entero(nombre: str, predeterminado: int, minimo: int, maximo: int) -> int:
    try:
        valor = int(os.getenv(nombre, str(predeterminado)))
    except ValueError as error:
        raise ConfiguracionInvalida(f"{nombre} debe ser entero.") from error
    if not minimo <= valor <= maximo:
        raise ConfiguracionInvalida(
            f"{nombre} debe estar entre {minimo} y {maximo}."
        )
    return valor


def _flotante(nombre: str, predeterminado: float) -> float:
    try:
        valor = float(os.getenv(nombre, str(predeterminado)))
    except ValueError as error:
        raise ConfiguracionInvalida(f"{nombre} debe ser numérico.") from error
    if not 0.2 <= valor <= 30:
        raise ConfiguracionInvalida(f"{nombre} debe estar entre 0.2 y 30.")
    return valor


@dataclass(frozen=True)
class Configuracion:
    mqtt_host: str
    mqtt_port: int
    input_topic: str
    output_topic: str
    mqtt_client_id: str
    api_url: str
    clave_interna: str
    max_payload_bytes: int = 4096
    dedup_ttl_seconds: int = 600
    decision_ttl_seconds: int = 3600
    max_decisions: int = 500
    backend_timeout_seconds: float = 3.0

    @classmethod
    def desde_entorno(cls) -> "Configuracion":
        clave = os.getenv("ACCESS_INTERNAL_API_KEY", "")
        if clave != clave.strip() or len(clave.encode("utf-8")) < 32:
            raise ConfiguracionInvalida(
                "ACCESS_INTERNAL_API_KEY debe contener al menos 32 bytes."
            )
        host = os.getenv("ACCESS_MQTT_HOST", "localhost").strip()
        entrada = os.getenv(
            "ACCESS_MQTT_INPUT_TOPIC",
            "puertotrack/rfid/identificaciones.v1",
        ).strip()
        salida = os.getenv(
            "ACCESS_MQTT_OUTPUT_TOPIC",
            "puertotrack/accesos/resultados.v1",
        ).strip()
        client_id = os.getenv(
            "ACCESS_MQTT_CLIENT_ID", "puertotrack-access-consumer"
        ).strip()
        api_url = os.getenv(
            "PUERTOTRACK_API_URL", "http://127.0.0.1:8000"
        ).strip().rstrip("/")
        if not all((host, entrada, salida, client_id, api_url)):
            raise ConfiguracionInvalida(
                "La configuración de red no puede contener valores vacíos."
            )
        if entrada == salida:
            raise ConfiguracionInvalida(
                "Los topics de entrada y salida deben ser distintos."
            )
        return cls(
            mqtt_host=host,
            mqtt_port=_entero("ACCESS_MQTT_PORT", 1883, 1, 65535),
            input_topic=entrada,
            output_topic=salida,
            mqtt_client_id=client_id,
            api_url=api_url,
            clave_interna=clave,
            max_payload_bytes=_entero(
                "ACCESS_MAX_PAYLOAD_BYTES", 4096, 256, 65536
            ),
            dedup_ttl_seconds=_entero(
                "ACCESS_DEDUP_TTL_SECONDS", 600, 10, 86400
            ),
            decision_ttl_seconds=_entero(
                "ACCESS_DECISION_TTL_SECONDS", 3600, 60, 604800
            ),
            max_decisions=_entero(
                "ACCESS_MAX_DECISIONS", 500, 10, 10000
            ),
            backend_timeout_seconds=_flotante(
                "ACCESS_BACKEND_TIMEOUT_SECONDS", 3.0
            ),
        )
