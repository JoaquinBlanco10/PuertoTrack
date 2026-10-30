import secrets

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import AuditLog, Contenedor, Movimiento, Ubicacion, Usuario
from repositories import AuditLogRepository, UbicacionRepository, UsuarioRepository
from security import generar_password_hash


PASSWORD_PRUEBA = secrets.token_urlsafe(24)


def headers_para(
    cliente: TestClient, session: Session, *, rol: str, sufijo: str
) -> dict[str, str]:
    email = f"{rol}-{sufijo}@ubicaciones.test"
    UsuarioRepository(session).crear(
        Usuario(
            nombre=f"Usuario {rol}",
            email=email,
            password_hash=generar_password_hash(PASSWORD_PRUEBA),
            rol=rol,
        )
    )
    login = cliente.post(
        "/auth/login",
        data={"username": email, "password": PASSWORD_PRUEBA},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def ubicacion_directa(
    session: Session,
    *,
    codigo: str,
    tipo: str = "interna",
    activo: bool = True,
) -> Ubicacion:
    return UbicacionRepository(session).crear(
        Ubicacion(
            codigo=codigo,
            nombre=codigo.replace("_", " ").title(),
            tipo=tipo,
            activo=activo,
        )
    )


def test_supervisor_administra_catalogo_y_genera_auditoria(
    cliente: TestClient, session_prueba: Session
) -> None:
    headers = headers_para(
        cliente, session_prueba, rol="supervisor", sufijo="admin"
    )
    creada = cliente.post(
        "/ubicaciones",
        headers=headers,
        json={"codigo": "patio_norte", "nombre": "Patio Norte", "tipo": "interna"},
    )
    assert creada.status_code == 201
    ubicacion_id = creada.json()["id"]
    actualizada = cliente.patch(
        f"/ubicaciones/{ubicacion_id}",
        headers=headers,
        json={"nombre": "Patio Norte 1", "activo": False},
    )
    listado = cliente.get(
        "/ubicaciones?incluir_inactivas=true", headers=headers
    )

    assert actualizada.status_code == 200
    assert actualizada.json()["codigo"] == "PATIO_NORTE"
    assert actualizada.json()["activo"] is False
    assert [item["id"] for item in listado.json()] == [ubicacion_id]
    auditorias = session_prueba.scalars(
        select(AuditLog)
        .where(AuditLog.entidad == "ubicacion")
        .order_by(AuditLog.id)
    ).all()
    assert [item.accion for item in auditorias] == ["crear", "actualizar"]


def test_operador_solo_consulta_habilitadas(
    cliente: TestClient, session_prueba: Session
) -> None:
    activa = ubicacion_directa(session_prueba, codigo="PATIO_A")
    inactiva = ubicacion_directa(
        session_prueba, codigo="PATIO_X", activo=False
    )
    headers = headers_para(
        cliente, session_prueba, rol="operador", sufijo="consulta"
    )

    listado = cliente.get("/ubicaciones", headers=headers)
    por_id_activa = cliente.get(f"/ubicaciones/{activa.id}", headers=headers)
    por_id_inactiva = cliente.get(
        f"/ubicaciones/{inactiva.id}", headers=headers
    )

    assert [item["id"] for item in listado.json()] == [activa.id]
    assert por_id_activa.status_code == 200
    assert por_id_inactiva.status_code == 404
    assert cliente.get(
        "/ubicaciones?incluir_inactivas=true", headers=headers
    ).status_code == 403
    assert cliente.post(
        "/ubicaciones",
        headers=headers,
        json={"codigo": "NUEVA", "nombre": "Nueva", "tipo": "externa"},
    ).status_code == 403
    assert cliente.patch(
        f"/ubicaciones/{activa.id}", headers=headers, json={"activo": False}
    ).status_code == 403


def test_codigos_estables_unicos_y_sin_eliminacion(
    cliente: TestClient, session_prueba: Session
) -> None:
    existente = ubicacion_directa(session_prueba, codigo="PATIO_A")
    headers = headers_para(
        cliente, session_prueba, rol="supervisor", sufijo="codigo"
    )
    duplicada = cliente.post(
        "/ubicaciones",
        headers=headers,
        json={"codigo": "PATIO_A", "nombre": "Otro", "tipo": "interna"},
    )
    cambiar_codigo = cliente.patch(
        f"/ubicaciones/{existente.id}",
        headers=headers,
        json={"codigo": "CODIGO_NUEVO"},
    )
    eliminar = cliente.delete(f"/ubicaciones/{existente.id}", headers=headers)

    assert duplicada.status_code == 409
    assert cambiar_codigo.status_code == 400
    assert eliminar.status_code == 405


def test_tipo_puede_cambiar_solo_si_ubicacion_no_fue_utilizada(
    cliente: TestClient, session_prueba: Session
) -> None:
    libre = ubicacion_directa(session_prueba, codigo="LIBRE")
    usada = ubicacion_directa(session_prueba, codigo="USADA")
    session_prueba.add(
        Contenedor(
            codigo="MSCU1234567",
            ubicacion_actual=usada.nombre,
            ubicacion_actual_id=usada.id,
            estado="en_patio",
        )
    )
    session_prueba.flush()
    headers = headers_para(
        cliente, session_prueba, rol="supervisor", sufijo="tipo"
    )

    permitido = cliente.patch(
        f"/ubicaciones/{libre.id}", headers=headers, json={"tipo": "externa"}
    )
    bloqueado = cliente.patch(
        f"/ubicaciones/{usada.id}", headers=headers, json={"tipo": "externa"}
    )

    assert permitido.status_code == 200
    assert permitido.json()["tipo"] == "externa"
    assert bloqueado.status_code == 409
    session_prueba.refresh(usada)
    assert usada.tipo == "interna"


def test_validaciones_filtros_y_autenticacion(
    cliente: TestClient, session_prueba: Session
) -> None:
    ubicacion_directa(session_prueba, codigo="PATIO_A")
    externa = ubicacion_directa(
        session_prueba, codigo="FUERA_PUERTO", tipo="externa"
    )
    headers = headers_para(
        cliente, session_prueba, rol="supervisor", sufijo="filtros"
    )

    filtradas = cliente.get("/ubicaciones?tipo=externa", headers=headers)
    invalida = cliente.post(
        "/ubicaciones",
        headers=headers,
        json={"codigo": "X", "nombre": "X", "tipo": "desconocida"},
    )
    assert [item["id"] for item in filtradas.json()] == [externa.id]
    assert invalida.status_code == 400
    assert cliente.get("/ubicaciones").status_code == 401


def test_fallo_de_auditoria_revierte_catalogo(
    cliente: TestClient,
    session_prueba: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    headers = headers_para(
        cliente, session_prueba, rol="supervisor", sufijo="rollback"
    )
    session_prueba.commit()

    def fallar(*args, **kwargs):
        raise RuntimeError("fallo de auditoria simulado")

    monkeypatch.setattr(AuditLogRepository, "crear", fallar)
    respuesta = cliente.post(
        "/ubicaciones",
        headers=headers,
        json={"codigo": "PATIO_A", "nombre": "Patio A", "tipo": "interna"},
    )

    assert respuesta.status_code == 500
    assert session_prueba.scalar(select(func.count(Ubicacion.id))) == 0
    assert session_prueba.scalar(select(func.count(AuditLog.id))) == 0


def test_nombre_catalogado_es_canonico_sin_alterar_snapshots_historicos(
    cliente: TestClient, session_prueba: Session
) -> None:
    origen = ubicacion_directa(session_prueba, codigo="PATIO_ANTIGUO")
    destino = ubicacion_directa(session_prueba, codigo="PATIO_DESTINO")
    headers = headers_para(
        cliente, session_prueba, rol="supervisor", sufijo="nombre-canonico"
    )
    usuario = UsuarioRepository(session_prueba).buscar_por_email(
        "supervisor-nombre-canonico@ubicaciones.test"
    )
    assert usuario is not None
    contenedor = Contenedor(
        codigo="MSCU7654321",
        ubicacion_actual="Texto persistido anterior",
        ubicacion_actual_id=origen.id,
        estado="en_patio",
    )
    session_prueba.add(contenedor)
    session_prueba.flush()
    historico = Movimiento(
        contenedor_id=contenedor.id,
        usuario_id=usuario.id,
        tipo="traslado",
        ubicacion_origen="Snapshot origen histórico",
        ubicacion_destino="Snapshot destino histórico",
        ubicacion_origen_id=origen.id,
        ubicacion_destino_id=origen.id,
    )
    session_prueba.add(historico)
    session_prueba.commit()

    renombrada = cliente.patch(
        f"/ubicaciones/{origen.id}",
        headers=headers,
        json={"nombre": "Patio Vigente"},
    )
    consultado = cliente.get(
        f"/contenedores/{contenedor.id}", headers=headers
    )
    historial_antes = cliente.get(
        f"/movimientos/contenedor/{contenedor.id}", headers=headers
    )
    texto_persistido_tras_renombrar = session_prueba.scalar(
        select(Contenedor._ubicacion_actual_texto).where(
            Contenedor.id == contenedor.id
        )
    )
    nuevo_movimiento = cliente.post(
        "/movimientos",
        headers=headers,
        json={
            "contenedor_id": contenedor.id,
            "tipo": "traslado",
            "ubicacion_destino_id": destino.id,
        },
    )
    dashboard = cliente.get("/dashboard/resumen", headers=headers)

    assert renombrada.status_code == 200
    assert consultado.status_code == 200
    assert consultado.json()["ubicacion_actual"] == "Patio Vigente"
    assert texto_persistido_tras_renombrar == "Texto persistido anterior"
    assert historial_antes.status_code == 200
    assert historial_antes.json()[0]["ubicacion_origen"] == (
        "Snapshot origen histórico"
    )
    assert historial_antes.json()[0]["ubicacion_destino"] == (
        "Snapshot destino histórico"
    )
    assert nuevo_movimiento.status_code == 201
    assert nuevo_movimiento.json()["ubicacion_origen"] == "Patio Vigente"
    assert nuevo_movimiento.json()["ubicacion_destino"] == destino.nombre
    assert dashboard.status_code == 200
    movimientos_dashboard = {
        item["id"]: item for item in dashboard.json()["ultimos_movimientos"]
    }
    assert movimientos_dashboard[historico.id]["ubicacion_origen"] == (
        "Snapshot origen histórico"
    )
    assert movimientos_dashboard[historico.id]["ubicacion_destino"] == (
        "Snapshot destino histórico"
    )
    assert movimientos_dashboard[nuevo_movimiento.json()["id"]][
        "ubicacion_origen"
    ] == "Patio Vigente"
    assert historico.ubicacion_origen == "Snapshot origen histórico"
    assert historico.ubicacion_destino == "Snapshot destino histórico"

    auditorias_renombrado = session_prueba.scalars(
        select(AuditLog).where(
            AuditLog.entidad == "ubicacion",
            AuditLog.entidad_id == origen.id,
            AuditLog.accion == "actualizar",
        )
    ).all()
    assert len(auditorias_renombrado) == 1
    assert auditorias_renombrado[0].datos_anteriores["nombre"] == (
        "Patio Antiguo"
    )
    assert auditorias_renombrado[0].datos_nuevos["nombre"] == "Patio Vigente"


def test_contenedor_sin_fk_conserva_texto_historico_como_fallback(
    cliente: TestClient, session_prueba: Session
) -> None:
    headers = headers_para(
        cliente, session_prueba, rol="operador", sufijo="fallback"
    )
    contenedor = Contenedor(
        codigo="TGHU7654321",
        ubicacion_actual="casa de Jose",
        ubicacion_actual_id=None,
        estado="disponible",
    )
    session_prueba.add(contenedor)
    session_prueba.commit()

    respuesta = cliente.get(
        f"/contenedores/{contenedor.id}", headers=headers
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["ubicacion_actual"] == "casa de Jose"
    assert respuesta.json()["ubicacion_actual_id"] is None
