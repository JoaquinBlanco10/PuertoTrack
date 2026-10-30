from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from access_service.app import crear_app
from access_service.config import Configuracion
from access_service.contracts import DecisionAcceso, ResultadoAcceso


CLAVE = "a" * 40
CONFIG = Configuracion(
    mqtt_host="localhost",
    mqtt_port=1883,
    input_topic="puertotrack/rfid/identificaciones.v1",
    output_topic="puertotrack/accesos/resultados.v1",
    mqtt_client_id="access-test",
    api_url="http://backend.test",
    clave_interna=CLAVE,
)


def test_api_interna_protegida_y_health_observable() -> None:
    app = crear_app(configuracion=CONFIG, iniciar_mqtt=False)
    decision = DecisionAcceso(
        decision_id=uuid4(),
        evento_id=uuid4(),
        codigo_contenedor="CONT123",
        contenedor_id=7,
        lector="PORTICO_NORTE",
        fecha_evento=datetime.now(timezone.utc),
        resultado=ResultadoAcceso.HABILITADO,
        motivo="PRIMERA_ENTRADA_HABILITADA",
        fecha_decision=datetime.now(timezone.utc),
    )
    app.state.almacen.registrar(decision)

    with TestClient(app) as cliente:
        salud = cliente.get("/health")
        sin_clave = cliente.get("/internal/decisiones")
        listado = cliente.get(
            "/internal/decisiones?resultado=habilitado",
            headers={"X-PuertoTrack-Access-Key": CLAVE},
        )
        detalle = cliente.get(
            f"/internal/decisiones/{decision.evento_id}",
            headers={"X-PuertoTrack-Access-Key": CLAVE},
        )

    assert salud.status_code == 200
    assert salud.json()["mqtt_conectado"] is False
    assert sin_clave.status_code == 401
    assert len(listado.json()) == 1
    assert detalle.json()["motivo"] == "PRIMERA_ENTRADA_HABILITADA"
