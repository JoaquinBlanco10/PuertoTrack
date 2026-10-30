import secrets

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from auditoria_service import DatosAuditoriaInvalidos
from models import AuditLog, Contenedor, Movimiento, Ubicacion, Usuario
from repositories import (
    AuditLogRepository,
    ContenedorRepository,
    UbicacionRepository,
    UsuarioRepository,
)
from security import generar_password_hash


PASSWORD_PRUEBA = secrets.token_urlsafe(24)


def crear_usuario(
    session: Session,
    *,
    email: str,
    rol: str,
) -> Usuario:
    return UsuarioRepository(session).crear(
        Usuario(
            nombre=f"Usuario {rol}",
            email=email,
            password_hash=generar_password_hash(PASSWORD_PRUEBA),
            rol=rol,
        )
    )


def obtener_headers(
    cliente: TestClient,
    session: Session,
    *,
    email: str,
    rol: str,
    confirmar: bool = False,
) -> tuple[dict[str, str], Usuario]:
    usuario = crear_usuario(session, email=email, rol=rol)
    respuesta = cliente.post(
        "/auth/login",
        data={"username": email, "password": PASSWORD_PRUEBA},
    )
    assert respuesta.status_code == 200
    if confirmar:
        session.commit()
    return (
        {"Authorization": f"Bearer {respuesta.json()['access_token']}"},
        usuario,
    )


def crear_contenedor_api(
    cliente: TestClient,
    headers: dict[str, str],
    *,
    codigo: str = "MSCU1234567",
) -> dict:
    respuesta = cliente.post(
        "/contenedores",
        headers=headers,
        json={"codigo": codigo},
    )
    assert respuesta.status_code == 201
    return respuesta.json()


def crear_ubicacion_interna(session: Session) -> Ubicacion:
    return UbicacionRepository(session).crear(
        Ubicacion(
            codigo="PATIO_A",
            nombre="Patio A",
            tipo="interna",
            activo=True,
        )
    )


def test_audita_creacion_actualizacion_y_movimiento_sin_datos_sensibles(
    cliente: TestClient, session_prueba: Session
) -> None:
    headers, usuario = obtener_headers(
        cliente,
        session_prueba,
        email="supervisor-auditoria@puertotrack.test",
        rol="supervisor",
    )
    contenedor = crear_contenedor_api(cliente, headers)
    patio = crear_ubicacion_interna(session_prueba)

    actualizacion = cliente.patch(
        f"/contenedores/{contenedor['id']}",
        headers=headers,
        json={"codigo": "TGHU7654321"},
    )
    movimiento = cliente.post(
        "/movimientos",
        headers=headers,
        json={
            "contenedor_id": contenedor["id"],
            "tipo": "entrada",
            "ubicacion_destino_id": patio.id,
            "observacion": "Dato operativo no replicado en auditoría",
        },
    )

    assert actualizacion.status_code == 200
    assert movimiento.status_code == 201

    registros = session_prueba.scalars(
        select(AuditLog).order_by(AuditLog.id)
    ).all()
    assert [registro.accion for registro in registros] == [
        "crear",
        "actualizar",
        "registrar_movimiento",
    ]
    assert all(registro.usuario_id == usuario.id for registro in registros)

    creacion, cambio, registro_movimiento = registros
    assert creacion.entidad == "contenedor"
    assert creacion.entidad_id == contenedor["id"]
    assert creacion.datos_anteriores is None
    assert creacion.datos_nuevos == {
        "codigo": "MSCU1234567",
        "ubicacion_actual": "Sin asignar",
        "estado": "disponible",
    }
    assert cambio.datos_anteriores == {"codigo": "MSCU1234567"}
    assert cambio.datos_nuevos == {"codigo": "TGHU7654321"}
    assert registro_movimiento.entidad == "movimiento"
    assert registro_movimiento.entidad_id == movimiento.json()["id"]
    assert registro_movimiento.datos_anteriores == {
        "estado": "disponible",
        "ubicacion_actual": "Sin asignar",
        "ubicacion_actual_id": None,
    }
    assert registro_movimiento.datos_nuevos["tipo"] == "entrada"

    texto_auditoria = " ".join(
        str(registro.datos_anteriores) + str(registro.datos_nuevos)
        for registro in registros
    ).casefold()
    for termino in ("password", "hash", "jwt", "secret", "token"):
        assert termino not in texto_auditoria


def test_endpoint_auditoria_es_exclusivo_de_supervisor_y_solo_lectura(
    cliente: TestClient, session_prueba: Session
) -> None:
    operador_headers, _ = obtener_headers(
        cliente,
        session_prueba,
        email="operador-auditoria@puertotrack.test",
        rol="operador",
    )
    supervisor_headers, _ = obtener_headers(
        cliente,
        session_prueba,
        email="supervisor-lectura@puertotrack.test",
        rol="supervisor",
    )

    assert cliente.get("/auditoria").status_code == 401
    assert cliente.get(
        "/auditoria", headers=operador_headers
    ).status_code == 403
    assert cliente.get(
        "/auditoria", headers=supervisor_headers
    ).status_code == 200
    assert cliente.post(
        "/auditoria", headers=supervisor_headers, json={}
    ).status_code == 405
    assert cliente.patch(
        "/auditoria", headers=supervisor_headers, json={}
    ).status_code == 405
    assert cliente.delete(
        "/auditoria", headers=supervisor_headers
    ).status_code == 405


def test_filtros_y_paginacion_de_auditoria(
    cliente: TestClient, session_prueba: Session
) -> None:
    headers, usuario = obtener_headers(
        cliente,
        session_prueba,
        email="supervisor-filtros@puertotrack.test",
        rol="supervisor",
    )
    contenedor = crear_contenedor_api(cliente, headers)
    patio = crear_ubicacion_interna(session_prueba)
    cliente.patch(
        f"/contenedores/{contenedor['id']}",
        headers=headers,
        json={"codigo": "TGHU7654321"},
    )
    movimiento = cliente.post(
        "/movimientos",
        headers=headers,
        json={
            "contenedor_id": contenedor["id"],
            "tipo": "entrada",
            "ubicacion_destino_id": patio.id,
        },
    ).json()

    por_usuario = cliente.get(
        f"/auditoria?usuario_id={usuario.id}", headers=headers
    )
    por_entidad = cliente.get(
        f"/auditoria?entidad=contenedor&entidad_id={contenedor['id']}",
        headers=headers,
    )
    por_accion = cliente.get(
        "/auditoria?accion=registrar_movimiento", headers=headers
    )
    por_movimiento = cliente.get(
        f"/auditoria?entidad=movimiento&entidad_id={movimiento['id']}",
        headers=headers,
    )
    paginado = cliente.get(
        "/auditoria?offset=1&limite=1", headers=headers
    )

    assert por_usuario.status_code == 200
    assert len(por_usuario.json()) == 3
    assert len(por_entidad.json()) == 2
    assert [item["accion"] for item in por_accion.json()] == [
        "registrar_movimiento"
    ]
    assert len(por_movimiento.json()) == 1
    assert por_movimiento.json()[0]["entidad_id"] == movimiento["id"]
    assert len(paginado.json()) == 1


def test_fallo_de_auditoria_revierte_creacion_de_contenedor(
    cliente: TestClient,
    session_prueba: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers, _ = obtener_headers(
        cliente,
        session_prueba,
        email="rollback-contenedor@puertotrack.test",
        rol="supervisor",
        confirmar=True,
    )

    def fallar(*args, **kwargs):
        raise RuntimeError("fallo de auditoría simulado")

    monkeypatch.setattr(AuditLogRepository, "crear", fallar)
    respuesta = cliente.post(
        "/contenedores",
        headers=headers,
        json={"codigo": "MSCU1234567"},
    )

    assert respuesta.status_code == 500
    assert session_prueba.scalar(select(func.count(Contenedor.id))) == 0
    assert session_prueba.scalar(select(func.count(AuditLog.id))) == 0


def test_fallo_de_auditoria_revierte_movimiento_y_contenedor(
    cliente: TestClient,
    session_prueba: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers, _ = obtener_headers(
        cliente,
        session_prueba,
        email="rollback-movimiento@puertotrack.test",
        rol="operador",
        confirmar=True,
    )
    contenedor = ContenedorRepository(session_prueba).crear(
        Contenedor(
            codigo="MSCU1234567",
            ubicacion_actual="Zona externa",
            estado="disponible",
        )
    )
    patio = crear_ubicacion_interna(session_prueba)
    session_prueba.commit()

    def fallar(*args, **kwargs):
        raise RuntimeError("fallo de auditoría simulado")

    monkeypatch.setattr(AuditLogRepository, "crear", fallar)
    respuesta = cliente.post(
        "/movimientos",
        headers=headers,
        json={
            "contenedor_id": contenedor.id,
            "tipo": "entrada",
            "ubicacion_destino_id": patio.id,
        },
    )

    session_prueba.expire_all()
    contenedor_guardado = session_prueba.get(Contenedor, contenedor.id)
    assert respuesta.status_code == 500
    assert contenedor_guardado.estado == "disponible"
    assert contenedor_guardado.ubicacion_actual == "Zona externa"
    assert session_prueba.scalar(select(func.count(Movimiento.id))) == 0
    assert session_prueba.scalar(select(func.count(AuditLog.id))) == 0


def test_servicio_rechaza_campos_sensibles_en_snapshots(
    session_prueba: Session,
) -> None:
    repository = AuditLogRepository(session_prueba)

    from auditoria_service import AuditoriaService

    with pytest.raises(DatosAuditoriaInvalidos):
        AuditoriaService(session_prueba).registrar(
            usuario_id=None,
            accion="prueba",
            entidad="prueba",
            entidad_id=1,
            datos_anteriores=None,
            datos_nuevos={"password_hash": "valor-no-permitido"},
        )

    assert repository.listar_con_filtros() == []
