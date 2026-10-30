from sqlalchemy import func, select
from sqlalchemy.orm import Session

from fastapi.testclient import TestClient

from models import AuditLog, Contenedor, Movimiento


CLAVE_INTERNA_PRUEBA = "clave-rfid-pruebas-aisladas-0123456789"


def test_contrato_rfid_identifica_solo_datos_minimos_sin_escribir(
    cliente: TestClient,
    session_prueba: Session,
    monkeypatch,
) -> None:
    monkeypatch.setenv("RFID_INTERNAL_API_KEY", CLAVE_INTERNA_PRUEBA)
    contenedor = Contenedor(
        codigo="RFID1234567",
        ubicacion_actual="Información no expuesta",
        estado="en_patio",
    )
    session_prueba.add(contenedor)
    session_prueba.commit()

    respuesta = cliente.get(
        "/internal/rfid/contenedores/rfid1234567",
        headers={"X-PuertoTrack-Internal-Key": CLAVE_INTERNA_PRUEBA},
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "existe": True,
        "id": contenedor.id,
        "codigo": "RFID1234567",
    }
    assert session_prueba.scalar(select(func.count(Movimiento.id))) == 0
    assert session_prueba.scalar(select(func.count(AuditLog.id))) == 0


def test_contrato_rfid_rechaza_clave_ausente_incorrecta_o_no_configurada(
    cliente: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setenv("RFID_INTERNAL_API_KEY", CLAVE_INTERNA_PRUEBA)
    sin_clave = cliente.get("/internal/rfid/contenedores/ABC123")
    incorrecta = cliente.get(
        "/internal/rfid/contenedores/ABC123",
        headers={"X-PuertoTrack-Internal-Key": "incorrecta"},
    )
    monkeypatch.delenv("RFID_INTERNAL_API_KEY")
    no_configurada = cliente.get(
        "/internal/rfid/contenedores/ABC123",
        headers={"X-PuertoTrack-Internal-Key": CLAVE_INTERNA_PRUEBA},
    )

    assert sin_clave.status_code == 401
    assert incorrecta.status_code == 401
    assert no_configurada.status_code == 503


def test_contrato_rfid_distingue_codigo_desconocido(
    cliente: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setenv("RFID_INTERNAL_API_KEY", CLAVE_INTERNA_PRUEBA)

    respuesta = cliente.get(
        "/internal/rfid/contenedores/NOEXISTE",
        headers={"X-PuertoTrack-Internal-Key": CLAVE_INTERNA_PRUEBA},
    )

    assert respuesta.status_code == 404
    assert respuesta.json() == {"detail": "Contenedor no encontrado."}
