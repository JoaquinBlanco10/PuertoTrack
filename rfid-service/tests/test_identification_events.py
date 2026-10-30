from datetime import datetime, timezone
from uuid import uuid4

from rfid_service.config import Configuracion
from rfid_service.contracts import (
    EstadoProcesamiento,
    ProcesamientoRFID,
    crear_identificacion,
)
from rfid_service.mqtt_consumer import ConsumidorMQTT


def _procesamiento(estado: EstadoProcesamiento) -> ProcesamientoRFID:
    return ProcesamientoRFID(
        procesamiento_id=uuid4(),
        evento_id=uuid4(),
        codigo_contenedor="CONT123",
        lector="PORTICO_NORTE",
        fecha_evento=datetime.now(timezone.utc),
        recibido_en=datetime.now(timezone.utc),
        estado=estado,
        detalle="prueba",
        contenedor_id=7 if estado == EstadoProcesamiento.VALIDO else None,
    )


def test_solo_crea_identificaciones_pertinentes() -> None:
    valido = crear_identificacion(_procesamiento(EstadoProcesamiento.VALIDO))
    desconocido = crear_identificacion(
        _procesamiento(EstadoProcesamiento.DESCONOCIDO)
    )

    assert valido is not None
    assert valido.version == 1
    assert valido.contenedor_id == 7
    assert desconocido is not None
    assert desconocido.resultado_identificacion == "codigo_desconocido"
    for estado in (
        EstadoProcesamiento.DUPLICADO,
        EstadoProcesamiento.INVALIDO,
        EstadoProcesamiento.ERROR,
    ):
        assert crear_identificacion(_procesamiento(estado)) is None


def test_consumidor_publica_una_sola_vez_y_no_republica_duplicado() -> None:
    resultados = iter(
        [
            _procesamiento(EstadoProcesamiento.VALIDO),
            _procesamiento(EstadoProcesamiento.DUPLICADO),
        ]
    )

    class ProcesadorFalso:
        def procesar(self, payload: bytes) -> ProcesamientoRFID:
            return next(resultados)

    class Publicacion:
        rc = 0

    class ClienteFalso:
        def __init__(self) -> None:
            self.publicaciones: list[tuple[str, str, int]] = []

        def publish(self, topic: str, payload: str, qos: int) -> Publicacion:
            self.publicaciones.append((topic, payload, qos))
            return Publicacion()

    config = Configuracion(
        mqtt_host="localhost",
        mqtt_port=1883,
        mqtt_topic="puertotrack/rfid/detecciones",
        mqtt_client_id="rfid-test",
        api_url="http://backend.test",
        clave_interna="k" * 32,
    )
    consumidor = ConsumidorMQTT(config, ProcesadorFalso())  # type: ignore[arg-type]
    cliente = ClienteFalso()

    consumidor._al_recibir(cliente, None, type("M", (), {"payload": b"x"})())
    consumidor._al_recibir(cliente, None, type("M", (), {"payload": b"x"})())

    assert len(cliente.publicaciones) == 1
    assert cliente.publicaciones[0][0] == "puertotrack/rfid/identificaciones.v1"
    assert cliente.publicaciones[0][2] == 1
