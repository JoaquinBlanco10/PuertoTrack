import json
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from rfid_service.app import crear_app
from rfid_service.config import Configuracion, ConfiguracionInvalida
from rfid_service.contracts import DeteccionRFID
from rfid_service.mqtt_consumer import (
    ConsumidorMQTT,
    MQTTNoDisponible,
    PublicacionMQTTFallida,
)


CLAVE_DISPOSITIVO = "d" * 32
HEADERS = {"X-PuertoTrack-Device-Key": CLAVE_DISPOSITIVO}


def configuracion(*, clave_dispositivo: str = CLAVE_DISPOSITIVO) -> Configuracion:
    return Configuracion(
        mqtt_host="localhost",
        mqtt_port=1883,
        mqtt_topic="puertotrack/rfid/detecciones",
        mqtt_client_id="rfid-ingestion-test",
        api_url="http://backend.test",
        clave_interna="i" * 32,
        clave_dispositivo=clave_dispositivo,
    )


def payload() -> dict[str, str]:
    return {
        "evento_id": str(uuid4()),
        "codigo_contenedor": " cont123 ",
        "lector": " LECTOR_MOVIL_01 ",
        "fecha_utc": "2026-10-30T12:00:00Z",
    }


def test_configuracion_exige_clave_de_dispositivo_fuerte_e_independiente(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RFID_INTERNAL_API_KEY", "i" * 32)
    monkeypatch.setenv("RFID_DEVICE_API_KEY", "corta")
    with pytest.raises(ConfiguracionInvalida):
        Configuracion.desde_entorno()

    monkeypatch.setenv("RFID_DEVICE_API_KEY", "i" * 32)
    with pytest.raises(ConfiguracionInvalida):
        Configuracion.desde_entorno()

    monkeypatch.setenv("RFID_DEVICE_API_KEY", "d" * 32)
    assert Configuracion.desde_entorno().clave_dispositivo == "d" * 32


class PublicadorFalso:
    def __init__(self) -> None:
        self.detecciones: list[DeteccionRFID] = []
        self.error: Exception | None = None

    def publicar_deteccion(self, deteccion: DeteccionRFID) -> None:
        if self.error is not None:
            raise self.error
        self.detecciones.append(deteccion)


def test_endpoint_exige_clave_independiente_y_configurada() -> None:
    app = crear_app(configuracion=configuracion(), iniciar_mqtt=False)
    with TestClient(app) as cliente:
        app.state.consumidor = PublicadorFalso()
        sin_clave = cliente.post("/detecciones", json=payload())
        incorrecta = cliente.post(
            "/detecciones",
            json=payload(),
            headers={"X-PuertoTrack-Device-Key": "x" * 32},
        )

    app_sin_clave = crear_app(
        configuracion=configuracion(clave_dispositivo=""),
        iniciar_mqtt=False,
    )
    with TestClient(app_sin_clave) as cliente:
        no_configurado = cliente.post("/detecciones", json=payload())

    assert sin_clave.status_code == 401
    assert incorrecta.status_code == 401
    assert no_configurado.status_code == 503


def test_endpoint_valida_y_publica_el_contrato_existente() -> None:
    app = crear_app(configuracion=configuracion(), iniciar_mqtt=False)
    publicador = PublicadorFalso()

    with TestClient(app) as cliente:
        app.state.consumidor = publicador
        respuesta = cliente.post("/detecciones", json=payload(), headers=HEADERS)

    assert respuesta.status_code == 202
    assert respuesta.json()["estado"] == "aceptado"
    UUID(respuesta.json()["evento_id"])
    assert len(publicador.detecciones) == 1
    assert publicador.detecciones[0].codigo_contenedor == "CONT123"
    assert publicador.detecciones[0].lector == "LECTOR_MOVIL_01"


@pytest.mark.parametrize(
    "datos",
    [
        {**payload(), "campo_extra": "no permitido"},
        {**payload(), "evento_id": "no-es-uuid"},
        {**payload(), "fecha_utc": "2026-10-30T09:00:00-03:00"},
    ],
)
def test_endpoint_rechaza_json_que_no_cumple_el_contrato(
    datos: dict[str, str],
) -> None:
    app = crear_app(configuracion=configuracion(), iniciar_mqtt=False)
    publicador = PublicadorFalso()

    with TestClient(app) as cliente:
        app.state.consumidor = publicador
        respuesta = cliente.post("/detecciones", json=datos, headers=HEADERS)

    assert respuesta.status_code == 422
    assert publicador.detecciones == []


def test_endpoint_rechaza_json_mal_formado() -> None:
    app = crear_app(configuracion=configuracion(), iniciar_mqtt=False)
    publicador = PublicadorFalso()

    with TestClient(app) as cliente:
        app.state.consumidor = publicador
        respuesta = cliente.post(
            "/detecciones",
            content="{json-invalido",
            headers={**HEADERS, "Content-Type": "application/json"},
        )

    assert respuesta.status_code == 422
    assert publicador.detecciones == []


@pytest.mark.parametrize(
    "error",
    [
        MQTTNoDisponible("sin conexión"),
        PublicacionMQTTFallida("sin confirmación"),
    ],
)
def test_endpoint_no_devuelve_202_si_mqtt_falla(error: Exception) -> None:
    app = crear_app(configuracion=configuracion(), iniciar_mqtt=False)
    publicador = PublicadorFalso()
    publicador.error = error

    with TestClient(app) as cliente:
        app.state.consumidor = publicador
        respuesta = cliente.post("/detecciones", json=payload(), headers=HEADERS)

    assert respuesta.status_code == 503


class ConfirmacionFalsa:
    def __init__(self, *, rc: int = 0, confirmada: bool = True) -> None:
        self.rc = rc
        self.confirmada = confirmada
        self.timeout: int | None = None

    def wait_for_publish(self, timeout: int) -> None:
        self.timeout = timeout

    def is_published(self) -> bool:
        return self.confirmada


class ClienteMQTTFalso:
    def __init__(self, confirmacion: ConfirmacionFalsa) -> None:
        self.confirmacion = confirmacion
        self.publicaciones: list[tuple[str, str, int, bool]] = []

    def publish(
        self,
        topic: str,
        contenido: str,
        *,
        qos: int,
        retain: bool,
    ) -> ConfirmacionFalsa:
        self.publicaciones.append((topic, contenido, qos, retain))
        return self.confirmacion


def test_publicador_usa_qos_uno_sin_retencion_y_espera_confirmacion() -> None:
    consumidor = ConsumidorMQTT(configuracion(), object())  # type: ignore[arg-type]
    confirmacion = ConfirmacionFalsa()
    cliente = ClienteMQTTFalso(confirmacion)
    consumidor._cliente = cliente
    consumidor._conectado.set()
    deteccion = DeteccionRFID.model_validate(payload())

    consumidor.publicar_deteccion(deteccion)

    assert len(cliente.publicaciones) == 1
    topic, contenido, qos, retain = cliente.publicaciones[0]
    assert topic == "puertotrack/rfid/detecciones"
    assert json.loads(contenido)["evento_id"] == str(deteccion.evento_id)
    assert qos == 1
    assert retain is False
    assert confirmacion.timeout == 5


def test_publicador_detecta_falta_de_conexion_y_puback() -> None:
    deteccion = DeteccionRFID(
        evento_id=uuid4(),
        codigo_contenedor="CONT123",
        lector="LECTOR_MOVIL_01",
        fecha_utc=datetime.now(timezone.utc),
    )
    consumidor = ConsumidorMQTT(configuracion(), object())  # type: ignore[arg-type]
    with pytest.raises(MQTTNoDisponible):
        consumidor.publicar_deteccion(deteccion)

    confirmacion = ConfirmacionFalsa(confirmada=False)
    consumidor._cliente = ClienteMQTTFalso(confirmacion)
    consumidor._conectado.set()
    with pytest.raises(PublicacionMQTTFallida):
        consumidor.publicar_deteccion(deteccion)
