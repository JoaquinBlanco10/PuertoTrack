import hmac
import os
from dataclasses import dataclass


class ConfiguracionInvalida(RuntimeError):
    pass


def _entero(nombre: str, predeterminado: int, *, minimo: int, maximo: int) -> int:
    valor = os.getenv(nombre, str(predeterminado))
    try:
        numero = int(valor)
    except ValueError as error:
        raise ConfiguracionInvalida(f"{nombre} debe ser un número entero.") from error
    if not minimo <= numero <= maximo:
        raise ConfiguracionInvalida(
            f"{nombre} debe estar entre {minimo} y {maximo}."
        )
    return numero


def _flotante(
    nombre: str,
    predeterminado: float,
    *,
    minimo: float,
    maximo: float,
) -> float:
    valor = os.getenv(nombre, str(predeterminado))
    try:
        numero = float(valor)
    except ValueError as error:
        raise ConfiguracionInvalida(f"{nombre} debe ser numérico.") from error
    if not minimo <= numero <= maximo:
        raise ConfiguracionInvalida(
            f"{nombre} debe estar entre {minimo} y {maximo}."
        )
    return numero


@dataclass(frozen=True)
class Configuracion:
    mqtt_host: str
    mqtt_port: int
    mqtt_topic: str
    mqtt_client_id: str
    api_url: str
    clave_interna: str
    clave_dispositivo: str = ""
    mqtt_identifications_topic: str = "puertotrack/rfid/identificaciones.v1"
    max_payload_bytes: int = 4096
    dedup_ttl_seconds: int = 600
    max_processing_records: int = 500
    backend_timeout_seconds: float = 3.0

    @classmethod
    def desde_entorno(cls) -> "Configuracion":
        clave = os.getenv("RFID_INTERNAL_API_KEY", "")
        if clave != clave.strip() or len(clave.encode("utf-8")) < 32:
            raise ConfiguracionInvalida(
                "RFID_INTERNAL_API_KEY debe contener al menos 32 bytes."
            )
        clave_dispositivo = os.getenv("RFID_DEVICE_API_KEY", "")
        if clave_dispositivo and (
            clave_dispositivo != clave_dispositivo.strip()
            or len(clave_dispositivo.encode("utf-8")) < 32
        ):
            raise ConfiguracionInvalida(
                "RFID_DEVICE_API_KEY debe contener al menos 32 bytes."
            )
        if clave_dispositivo and hmac.compare_digest(
            clave_dispositivo,
            clave,
        ):
            raise ConfiguracionInvalida(
                "Las claves del dispositivo y del backend deben ser distintas."
            )
        host = os.getenv("RFID_MQTT_HOST", "localhost").strip()
        topic = os.getenv(
            "RFID_MQTT_TOPIC", "puertotrack/rfid/detecciones"
        ).strip()
        topic_identificaciones = os.getenv(
            "RFID_MQTT_IDENTIFICATIONS_TOPIC",
            "puertotrack/rfid/identificaciones.v1",
        ).strip()
        client_id = os.getenv(
            "RFID_MQTT_CLIENT_ID", "puertotrack-rfid-consumer"
        ).strip()
        api_url = os.getenv(
            "PUERTOTRACK_API_URL", "http://localhost:8000"
        ).strip().rstrip("/")
        if (
            not host
            or not topic
            or not topic_identificaciones
            or not client_id
            or not api_url
        ):
            raise ConfiguracionInvalida(
                "La configuración de red no puede contener valores vacíos."
            )
        if topic == topic_identificaciones:
            raise ConfiguracionInvalida(
                "Los topics de detección e identificación deben ser distintos."
            )
        return cls(
            mqtt_host=host,
            mqtt_port=_entero(
                "RFID_MQTT_PORT", 1883, minimo=1, maximo=65535
            ),
            mqtt_topic=topic,
            mqtt_client_id=client_id,
            api_url=api_url,
            clave_interna=clave,
            clave_dispositivo=clave_dispositivo,
            mqtt_identifications_topic=topic_identificaciones,
            max_payload_bytes=_entero(
                "RFID_MAX_PAYLOAD_BYTES", 4096, minimo=256, maximo=65536
            ),
            dedup_ttl_seconds=_entero(
                "RFID_DEDUP_TTL_SECONDS", 600, minimo=10, maximo=86400
            ),
            max_processing_records=_entero(
                "RFID_MAX_PROCESSING_RECORDS", 500, minimo=10, maximo=10000
            ),
            backend_timeout_seconds=_flotante(
                "RFID_BACKEND_TIMEOUT_SECONDS",
                3.0,
                minimo=0.2,
                maximo=30.0,
            ),
        )
