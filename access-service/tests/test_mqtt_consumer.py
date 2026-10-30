from datetime import datetime, timezone
from uuid import uuid4

from access_service.config import Configuracion
from access_service.contracts import DecisionAcceso, ResultadoAcceso
from access_service.mqtt_consumer import ConsumidorMQTT


def test_publica_solo_si_hay_decision_nueva() -> None:
    decision = DecisionAcceso(
        decision_id=uuid4(),
        evento_id=uuid4(),
        codigo_contenedor="CONT123",
        contenedor_id=7,
        lector="PORTICO",
        fecha_evento=datetime.now(timezone.utc),
        resultado=ResultadoAcceso.HABILITADO,
        motivo="PRIMERA_ENTRADA_HABILITADA",
        fecha_decision=datetime.now(timezone.utc),
    )

    class Procesador:
        def __init__(self) -> None:
            self.resultados = iter([decision, None])

        def procesar(self, payload: bytes):
            return next(self.resultados)

    class Publicacion:
        rc = 0

    class Cliente:
        def __init__(self) -> None:
            self.publicaciones = []

        def publish(self, topic, payload, qos):
            self.publicaciones.append((topic, payload, qos))
            return Publicacion()

    config = Configuracion(
        mqtt_host="localhost",
        mqtt_port=1883,
        input_topic="puertotrack/rfid/identificaciones.v1",
        output_topic="puertotrack/accesos/resultados.v1",
        mqtt_client_id="access-test",
        api_url="http://backend.test",
        clave_interna="k" * 32,
    )
    consumidor = ConsumidorMQTT(config, Procesador())  # type: ignore[arg-type]
    cliente = Cliente()
    mensaje = type("M", (), {"payload": b"x"})()

    consumidor._al_recibir(cliente, None, mensaje)
    consumidor._al_recibir(cliente, None, mensaje)

    assert len(cliente.publicaciones) == 1
    assert cliente.publicaciones[0][0] == "puertotrack/accesos/resultados.v1"
