from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from rfid_service.app import crear_app
from rfid_service.config import Configuracion
from rfid_service.contracts import EstadoProcesamiento, ProcesamientoRFID


CONFIGURACION = Configuracion(
    mqtt_host="localhost",
    mqtt_port=1883,
    mqtt_topic="puertotrack/rfid/detecciones",
    mqtt_client_id="rfid-test",
    api_url="http://backend.test",
    clave_interna="k" * 32,
)


def test_estado_y_consulta_de_procesamientos_son_observables() -> None:
    app = crear_app(configuracion=CONFIGURACION, iniciar_mqtt=False)
    evento_id = uuid4()
    app.state.almacen.registrar(
        ProcesamientoRFID(
            procesamiento_id=uuid4(),
            evento_id=evento_id,
            codigo_contenedor="CONT123",
            lector="LECTOR_TEST",
            fecha_evento=datetime.now(timezone.utc),
            recibido_en=datetime.now(timezone.utc),
            estado=EstadoProcesamiento.VALIDO,
            detalle="Contenedor identificado.",
            contenedor_id=8,
        )
    )

    with TestClient(app) as cliente:
        estado = cliente.get("/health")
        listado = cliente.get("/procesamientos?estado=valido")
        detalle = cliente.get(f"/procesamientos/{evento_id}")
        inexistente = cliente.get(f"/procesamientos/{uuid4()}")

    assert estado.status_code == 200
    assert estado.json()["mqtt_conectado"] is False
    assert estado.json()["por_estado"]["valido"] == 1
    assert len(listado.json()) == 1
    assert detalle.json()["contenedor_id"] == 8
    assert inexistente.status_code == 404
