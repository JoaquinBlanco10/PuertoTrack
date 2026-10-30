import secrets
from datetime import datetime, timezone
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from access_client import AccessServiceClient, ServicioAccesosNoDisponible
from models import AuditLog, Contenedor, Movimiento, Usuario
from repositories import UsuarioRepository
from security import generar_password_hash


CLAVE_ACCESOS = "clave-accesos-pruebas-aisladas-0123456789"
PASSWORD = secrets.token_urlsafe(24)


def _headers_usuario(
    cliente: TestClient,
    session: Session,
    *,
    rol: str,
    email: str,
) -> dict[str, str]:
    UsuarioRepository(session).crear(
        Usuario(
            nombre=f"Usuario {rol}",
            email=email,
            password_hash=generar_password_hash(PASSWORD),
            rol=rol,
        )
    )
    respuesta = cliente.post(
        "/auth/login",
        data={"username": email, "password": PASSWORD},
    )
    assert respuesta.status_code == 200
    return {"Authorization": f"Bearer {respuesta.json()['access_token']}"}


def test_hechos_acceso_son_minimos_y_no_escriben(
    cliente: TestClient,
    session_prueba: Session,
    monkeypatch,
) -> None:
    monkeypatch.setenv("ACCESS_INTERNAL_API_KEY", CLAVE_ACCESOS)
    contenedor = Contenedor(
        codigo="ACCESO123",
        ubicacion_actual="Sin asignar",
        ubicacion_actual_id=None,
        estado="disponible",
    )
    session_prueba.add(contenedor)
    session_prueba.commit()

    respuesta = cliente.get(
        "/internal/access/contenedores/acceso123",
        headers={"X-PuertoTrack-Access-Key": CLAVE_ACCESOS},
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "existe": True,
        "id": contenedor.id,
        "codigo": "ACCESO123",
        "estado": "disponible",
        "situacion": "presencia_sin_confirmar",
        "coherencia_operacional": "sin_confirmar",
        "ubicacion_actual_id": None,
        "tiene_movimientos": False,
        "tiene_salida_previa": False,
        "etiqueta_entrada": "primera_entrada",
    }
    assert session_prueba.scalar(select(func.count(Movimiento.id))) == 0
    assert session_prueba.scalar(select(func.count(AuditLog.id))) == 0


def test_hechos_acceso_rechazan_clave_y_codigo_desconocido(
    cliente: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setenv("ACCESS_INTERNAL_API_KEY", CLAVE_ACCESOS)

    assert cliente.get(
        "/internal/access/contenedores/NOEXISTE"
    ).status_code == 401
    assert cliente.get(
        "/internal/access/contenedores/NOEXISTE",
        headers={"X-PuertoTrack-Access-Key": "incorrecta"},
    ).status_code == 401
    assert cliente.get(
        "/internal/access/contenedores/NOEXISTE",
        headers={"X-PuertoTrack-Access-Key": CLAVE_ACCESOS},
    ).status_code == 404


def test_proxy_accesos_es_exclusivo_de_supervisor(
    cliente: TestClient,
    session_prueba: Session,
    monkeypatch,
) -> None:
    operador = _headers_usuario(
        cliente,
        session_prueba,
        rol="operador",
        email="operador-accesos@puertotrack.test",
    )
    supervisor = _headers_usuario(
        cliente,
        session_prueba,
        rol="supervisor",
        email="supervisor-accesos@puertotrack.test",
    )
    decision = {
        "version": 1,
        "decision_id": str(uuid4()),
        "evento_id": str(uuid4()),
        "codigo_contenedor": "ACCESO123",
        "contenedor_id": 7,
        "lector": "PORTICO_NORTE",
        "fecha_evento": datetime.now(timezone.utc).isoformat(),
        "resultado": "habilitado",
        "motivo": "PRIMERA_ENTRADA_HABILITADA",
        "fecha_decision": datetime.now(timezone.utc).isoformat(),
    }
    monkeypatch.setattr(
        AccessServiceClient,
        "__init__",
        lambda self: None,
    )
    monkeypatch.setattr(
        AccessServiceClient,
        "listar_decisiones",
        lambda self, **kwargs: [decision],
    )

    assert cliente.get("/accesos").status_code == 401
    assert cliente.get("/accesos", headers=operador).status_code == 403
    respuesta = cliente.get(
        "/accesos?limite=10&resultado=habilitado",
        headers=supervisor,
    )

    assert respuesta.status_code == 200
    assert respuesta.json()[0]["version"] == 1
    assert respuesta.json()[0]["motivo"] == "PRIMERA_ENTRADA_HABILITADA"


def test_proxy_traduce_servicio_no_disponible(
    cliente: TestClient,
    session_prueba: Session,
    monkeypatch,
) -> None:
    supervisor = _headers_usuario(
        cliente,
        session_prueba,
        rol="supervisor",
        email="supervisor-error-accesos@puertotrack.test",
    )
    monkeypatch.setattr(AccessServiceClient, "__init__", lambda self: None)

    def fallar(self, **kwargs):
        raise ServicioAccesosNoDisponible("servicio no disponible")

    monkeypatch.setattr(AccessServiceClient, "listar_decisiones", fallar)

    respuesta = cliente.get("/accesos", headers=supervisor)

    assert respuesta.status_code == 503
