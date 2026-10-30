import secrets
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import Contenedor, Movimiento, Ubicacion, Usuario
from movimiento_service import ErrorRegistroMovimiento, MovimientoService
from repositories import (
    ContenedorRepository,
    UbicacionRepository,
    UsuarioRepository,
)
from schemas import MovimientoCrear, TipoMovimiento
from security import generar_password_hash


PASSWORD_PRUEBA = secrets.token_urlsafe(24)


def crear_usuario(
    session: Session, *, email: str, rol: str = "operador"
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
    rol: str = "operador",
    email: str | None = None,
) -> tuple[dict[str, str], Usuario]:
    email_usuario = email or f"{rol}@movimientos.test"
    usuario = crear_usuario(session, email=email_usuario, rol=rol)
    respuesta = cliente.post(
        "/auth/login",
        data={"username": email_usuario, "password": PASSWORD_PRUEBA},
    )
    assert respuesta.status_code == 200
    session.commit()
    return (
        {"Authorization": f"Bearer {respuesta.json()['access_token']}"},
        usuario,
    )


def crear_ubicacion(
    session: Session,
    *,
    codigo: str,
    nombre: str,
    tipo: str,
    activo: bool = True,
) -> Ubicacion:
    return UbicacionRepository(session).crear(
        Ubicacion(
            codigo=codigo,
            nombre=nombre,
            tipo=tipo,
            activo=activo,
        )
    )


def crear_contenedor(
    session: Session,
    *,
    estado: str = "disponible",
    ubicacion: str = "Sin asignar",
    ubicacion_id: int | None = None,
    codigo: str = "MSCU1234567",
) -> Contenedor:
    return ContenedorRepository(session).crear(
        Contenedor(
            codigo=codigo,
            ubicacion_actual=ubicacion,
            ubicacion_actual_id=ubicacion_id,
            estado=estado,
        )
    )


def registrar(
    cliente: TestClient,
    headers: dict[str, str],
    *,
    contenedor_id: int,
    tipo: str,
    destino_id: int | None,
    observacion: str | None = None,
):
    cuerpo: dict[str, object] = {
        "contenedor_id": contenedor_id,
        "tipo": tipo,
    }
    if destino_id is not None:
        cuerpo["ubicacion_destino_id"] = destino_id
    if observacion is not None:
        cuerpo["observacion"] = observacion
    return cliente.post("/movimientos", headers=headers, json=cuerpo)


def test_ciclo_completo_registra_catalogo_historial_y_usuario_del_jwt(
    cliente: TestClient, session_prueba: Session
) -> None:
    patio_a = crear_ubicacion(
        session_prueba,
        codigo="PATIO_A",
        nombre="Patio A",
        tipo="interna",
    )
    patio_b = crear_ubicacion(
        session_prueba,
        codigo="PATIO_B",
        nombre="Patio B",
        tipo="interna",
    )
    fuera = crear_ubicacion(
        session_prueba,
        codigo="FUERA_PUERTO",
        nombre="Fuera del puerto",
        tipo="externa",
    )
    contenedor = crear_contenedor(session_prueba)
    headers, usuario = obtener_headers(cliente, session_prueba)

    entrada = registrar(
        cliente,
        headers,
        contenedor_id=contenedor.id,
        tipo="entrada",
        destino_id=patio_a.id,
    )
    traslado = registrar(
        cliente,
        headers,
        contenedor_id=contenedor.id,
        tipo="traslado",
        destino_id=patio_b.id,
    )
    salida = registrar(
        cliente,
        headers,
        contenedor_id=contenedor.id,
        tipo="salida",
        destino_id=fuera.id,
    )

    session_prueba.refresh(contenedor)
    historial = cliente.get(
        f"/movimientos/contenedor/{contenedor.id}", headers=headers
    )

    assert [entrada.status_code, traslado.status_code, salida.status_code] == [
        201,
        201,
        201,
    ]
    assert entrada.json()["ubicacion_origen"] == "Sin asignar"
    assert entrada.json()["ubicacion_destino_id"] == patio_a.id
    assert traslado.json()["ubicacion_origen_id"] == patio_a.id
    assert salida.json()["ubicacion_destino"] == "Fuera del puerto"
    assert salida.json()["usuario_id"] == usuario.id
    assert contenedor.estado == "en_transito"
    assert contenedor.ubicacion_actual == "Fuera del puerto"
    assert contenedor.ubicacion_actual_id == fuera.id
    assert [item["tipo"] for item in historial.json()] == [
        "entrada",
        "traslado",
        "salida",
    ]


def test_historial_y_contexto_distinguen_primera_entrada_y_reingreso(
    cliente: TestClient, session_prueba: Session
) -> None:
    patio = crear_ubicacion(
        session_prueba,
        codigo="PATIO_A",
        nombre="Patio A",
        tipo="interna",
    )
    fuera = crear_ubicacion(
        session_prueba,
        codigo="FUERA_PUERTO",
        nombre="Fuera del puerto",
        tipo="externa",
    )
    contenedor = crear_contenedor(session_prueba)
    headers, _ = obtener_headers(cliente, session_prueba)

    inicial = cliente.get(
        f"/movimientos/contenedor/{contenedor.id}/contexto",
        headers=headers,
    )
    registrar(
        cliente,
        headers,
        contenedor_id=contenedor.id,
        tipo="entrada",
        destino_id=patio.id,
    )
    despues_entrada = cliente.get(
        f"/movimientos/contenedor/{contenedor.id}/contexto",
        headers=headers,
    )
    registrar(
        cliente,
        headers,
        contenedor_id=contenedor.id,
        tipo="salida",
        destino_id=fuera.id,
    )
    despues_salida = cliente.get(
        f"/movimientos/contenedor/{contenedor.id}/contexto",
        headers=headers,
    )

    assert inicial.json()["etiqueta_entrada"] == "primera_entrada"
    assert despues_entrada.json()["etiqueta_entrada"] == "entrada"
    assert despues_salida.json()["etiqueta_entrada"] == "reingreso"


def test_historial_global_y_por_contenedor_admiten_paginacion(
    cliente: TestClient, session_prueba: Session
) -> None:
    patio_a = crear_ubicacion(
        session_prueba, codigo="PATIO_A", nombre="Patio A", tipo="interna"
    )
    patio_b = crear_ubicacion(
        session_prueba, codigo="PATIO_B", nombre="Patio B", tipo="interna"
    )
    contenedor = crear_contenedor(session_prueba)
    headers, _ = obtener_headers(cliente, session_prueba)
    registrar(
        cliente,
        headers,
        contenedor_id=contenedor.id,
        tipo="entrada",
        destino_id=patio_a.id,
    )
    registrar(
        cliente,
        headers,
        contenedor_id=contenedor.id,
        tipo="traslado",
        destino_id=patio_b.id,
    )

    global_paginado = cliente.get(
        "/movimientos?offset=1&limite=1", headers=headers
    )
    por_contenedor = cliente.get(
        f"/movimientos/contenedor/{contenedor.id}?offset=0&limite=1",
        headers=headers,
    )

    assert [item["tipo"] for item in global_paginado.json()] == ["traslado"]
    assert [item["tipo"] for item in por_contenedor.json()] == ["entrada"]


def test_historial_admite_orden_descendente_determinista_y_conserva_ascendente(
    cliente: TestClient, session_prueba: Session
) -> None:
    contenedor = crear_contenedor(session_prueba)
    headers, usuario = obtener_headers(cliente, session_prueba)
    misma_fecha = datetime(2026, 10, 18, 12, 0, tzinfo=timezone.utc)
    movimientos = [
        Movimiento(
            contenedor_id=contenedor.id,
            usuario_id=usuario.id,
            tipo="entrada",
            ubicacion_origen="Origen 1",
            ubicacion_destino="Destino 1",
            fecha_movimiento=misma_fecha,
        ),
        Movimiento(
            contenedor_id=contenedor.id,
            usuario_id=usuario.id,
            tipo="traslado",
            ubicacion_origen="Origen 2",
            ubicacion_destino="Destino 2",
            fecha_movimiento=misma_fecha,
        ),
        Movimiento(
            contenedor_id=contenedor.id,
            usuario_id=usuario.id,
            tipo="salida",
            ubicacion_origen="Origen 3",
            ubicacion_destino="Destino 3",
            fecha_movimiento=misma_fecha + timedelta(minutes=1),
        ),
    ]
    session_prueba.add_all(movimientos)
    session_prueba.commit()

    compatible = cliente.get("/movimientos", headers=headers)
    descendente = cliente.get(
        "/movimientos?orden=desc", headers=headers
    )
    pagina_descendente = cliente.get(
        f"/movimientos/contenedor/{contenedor.id}"
        "?orden=desc&offset=1&limite=1",
        headers=headers,
    )

    assert [item["id"] for item in compatible.json()] == [
        movimientos[0].id,
        movimientos[1].id,
        movimientos[2].id,
    ]
    assert [item["id"] for item in descendente.json()] == [
        movimientos[2].id,
        movimientos[1].id,
        movimientos[0].id,
    ]
    assert [item["id"] for item in pagina_descendente.json()] == [
        movimientos[1].id
    ]
    assert cliente.get(
        "/movimientos?orden=otro", headers=headers
    ).status_code == 400


def test_rechaza_destinos_inexistentes_inactivos_incompatibles_y_repetidos(
    cliente: TestClient, session_prueba: Session
) -> None:
    patio_a = crear_ubicacion(
        session_prueba, codigo="PATIO_A", nombre="Patio A", tipo="interna"
    )
    inactiva = crear_ubicacion(
        session_prueba,
        codigo="PATIO_CERRADO",
        nombre="Patio cerrado",
        tipo="interna",
        activo=False,
    )
    externa = crear_ubicacion(
        session_prueba,
        codigo="DEPOSITO",
        nombre="Depósito externo",
        tipo="externa",
    )
    headers, _ = obtener_headers(cliente, session_prueba)
    session_prueba.commit()

    contenedor_disponible = crear_contenedor(session_prueba)
    session_prueba.commit()
    inexistente = registrar(
        cliente,
        headers,
        contenedor_id=contenedor_disponible.id,
        tipo="entrada",
        destino_id=9999,
    )
    inactivo = registrar(
        cliente,
        headers,
        contenedor_id=contenedor_disponible.id,
        tipo="entrada",
        destino_id=inactiva.id,
    )
    tipo_incompatible = registrar(
        cliente,
        headers,
        contenedor_id=contenedor_disponible.id,
        tipo="entrada",
        destino_id=externa.id,
    )
    faltante = registrar(
        cliente,
        headers,
        contenedor_id=contenedor_disponible.id,
        tipo="entrada",
        destino_id=None,
    )

    contenedor_patio = crear_contenedor(
        session_prueba,
        estado="en_patio",
        ubicacion="Patio A",
        ubicacion_id=patio_a.id,
        codigo="TGHU7654321",
    )
    repetido = registrar(
        cliente,
        headers,
        contenedor_id=contenedor_patio.id,
        tipo="traslado",
        destino_id=patio_a.id,
    )

    assert [
        inexistente.status_code,
        inactivo.status_code,
        tipo_incompatible.status_code,
        faltante.status_code,
        repetido.status_code,
    ] == [400, 400, 400, 400, 400]
    assert session_prueba.scalar(select(func.count(Movimiento.id))) == 0


def test_texto_libre_y_usuario_del_body_son_rechazados(
    cliente: TestClient, session_prueba: Session
) -> None:
    contenedor = crear_contenedor(session_prueba)
    headers, _ = obtener_headers(cliente, session_prueba)

    respuesta = cliente.post(
        "/movimientos",
        headers=headers,
        json={
            "contenedor_id": contenedor.id,
            "usuario_id": 9999,
            "tipo": "entrada",
            "ubicacion_destino": "casa de Jose",
        },
    )

    assert respuesta.status_code == 400
    assert session_prueba.scalar(select(func.count(Movimiento.id))) == 0


def test_observacion_limita_nuevos_movimientos_sin_afectar_historicos(
    cliente: TestClient, session_prueba: Session
) -> None:
    patio = crear_ubicacion(
        session_prueba, codigo="PATIO_A", nombre="Patio A", tipo="interna"
    )
    headers, usuario = obtener_headers(cliente, session_prueba)
    valido = crear_contenedor(session_prueba, codigo="OBSERVACION1")
    excedido = crear_contenedor(session_prueba, codigo="OBSERVACION2")
    session_prueba.commit()

    aceptado = registrar(
        cliente,
        headers,
        contenedor_id=valido.id,
        tipo="entrada",
        destino_id=patio.id,
        observacion="x" * 1000,
    )
    rechazado = registrar(
        cliente,
        headers,
        contenedor_id=excedido.id,
        tipo="entrada",
        destino_id=patio.id,
        observacion="x" * 1001,
    )

    historico = Movimiento(
        contenedor_id=excedido.id,
        usuario_id=usuario.id,
        tipo=None,
        ubicacion_origen="Texto histórico",
        ubicacion_destino="Destino histórico",
        observacion="h" * 1200,
    )
    session_prueba.add(historico)
    session_prueba.commit()
    listado = cliente.get("/movimientos", headers=headers)

    assert aceptado.status_code == 201
    assert len(aceptado.json()["observacion"]) == 1000
    assert rechazado.status_code == 400
    assert excedido.estado == "disponible"
    assert any(
        item["id"] == historico.id and len(item["observacion"]) == 1200
        for item in listado.json()
    )


def test_rechaza_movimientos_si_estado_y_ubicacion_actual_no_coinciden(
    cliente: TestClient, session_prueba: Session
) -> None:
    patio = crear_ubicacion(
        session_prueba, codigo="PATIO_A", nombre="Patio A", tipo="interna"
    )
    otro_patio = crear_ubicacion(
        session_prueba, codigo="PATIO_B", nombre="Patio B", tipo="interna"
    )
    incoherente = crear_contenedor(
        session_prueba,
        codigo="INCOHERENTE1",
        estado="disponible",
        ubicacion="Patio A",
        ubicacion_id=patio.id,
    )
    headers, _ = obtener_headers(cliente, session_prueba)

    respuesta = registrar(
        cliente,
        headers,
        contenedor_id=incoherente.id,
        tipo="entrada",
        destino_id=otro_patio.id,
    )

    assert respuesta.status_code == 400
    assert "incoherentes" in respuesta.json()["detail"]
    assert session_prueba.scalar(select(func.count(Movimiento.id))) == 0


def test_operador_y_supervisor_pueden_registrar_y_consultar(
    cliente: TestClient, session_prueba: Session
) -> None:
    patio_a = crear_ubicacion(
        session_prueba, codigo="PATIO_A", nombre="Patio A", tipo="interna"
    )
    patio_b = crear_ubicacion(
        session_prueba, codigo="PATIO_B", nombre="Patio B", tipo="interna"
    )
    operador_headers, _ = obtener_headers(
        cliente,
        session_prueba,
        rol="operador",
        email="operador-permisos@movimientos.test",
    )
    operador = registrar(
        cliente,
        operador_headers,
        contenedor_id=crear_contenedor(session_prueba).id,
        tipo="entrada",
        destino_id=patio_a.id,
    )

    supervisor_headers, _ = obtener_headers(
        cliente,
        session_prueba,
        rol="supervisor",
        email="supervisor-permisos@movimientos.test",
    )
    supervisor = registrar(
        cliente,
        supervisor_headers,
        contenedor_id=crear_contenedor(
            session_prueba, codigo="TGHU7654321"
        ).id,
        tipo="entrada",
        destino_id=patio_b.id,
    )

    assert operador.status_code == 201
    assert supervisor.status_code == 201
    assert cliente.get(
        "/movimientos", headers=operador_headers
    ).status_code == 200
    assert cliente.get(
        "/movimientos", headers=supervisor_headers
    ).status_code == 200


def test_sin_token_y_contenedor_inexistente(
    cliente: TestClient, session_prueba: Session
) -> None:
    patio = crear_ubicacion(
        session_prueba, codigo="PATIO_A", nombre="Patio A", tipo="interna"
    )
    headers, _ = obtener_headers(cliente, session_prueba)

    assert cliente.get("/movimientos").status_code == 401
    assert registrar(
        cliente,
        headers,
        contenedor_id=9999,
        tipo="entrada",
        destino_id=patio.id,
    ).status_code == 404
    assert cliente.get(
        "/movimientos/contenedor/9999", headers=headers
    ).status_code == 404


def test_error_de_persistencia_hace_rollback(
    session_prueba: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    usuario = crear_usuario(
        session_prueba, email="rollback@movimientos.test"
    )
    patio = crear_ubicacion(
        session_prueba, codigo="PATIO_A", nombre="Patio A", tipo="interna"
    )
    contenedor = crear_contenedor(session_prueba)
    session_prueba.commit()
    service = MovimientoService(session_prueba)

    def fallar(_: Movimiento) -> Movimiento:
        raise RuntimeError("fallo simulado")

    monkeypatch.setattr(service.movimientos, "crear", fallar)

    with pytest.raises(ErrorRegistroMovimiento):
        service.registrar(
            MovimientoCrear(
                contenedor_id=contenedor.id,
                tipo=TipoMovimiento.ENTRADA,
                ubicacion_destino_id=patio.id,
            ),
            usuario,
        )

    session_prueba.expire_all()
    guardado = session_prueba.get(Contenedor, contenedor.id)
    assert guardado.estado == "disponible"
    assert guardado.ubicacion_actual == "Sin asignar"
    assert guardado.ubicacion_actual_id is None
    assert session_prueba.scalar(select(func.count(Movimiento.id))) == 0


def test_registro_bloquea_contenedor_y_destino(
    session_prueba: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    usuario = crear_usuario(
        session_prueba, email="bloqueo@movimientos.test"
    )
    patio = crear_ubicacion(
        session_prueba, codigo="PATIO_A", nombre="Patio A", tipo="interna"
    )
    contenedor = crear_contenedor(session_prueba)
    sentencias = []
    scalar_original = session_prueba.scalar

    def registrar_sentencia(statement, *args, **kwargs):
        sentencias.append(statement)
        return scalar_original(statement, *args, **kwargs)

    monkeypatch.setattr(session_prueba, "scalar", registrar_sentencia)
    MovimientoService(session_prueba).registrar(
        MovimientoCrear(
            contenedor_id=contenedor.id,
            tipo=TipoMovimiento.ENTRADA,
            ubicacion_destino_id=patio.id,
        ),
        usuario,
    )

    bloqueos = [
        sentencia
        for sentencia in sentencias
        if getattr(sentencia, "_for_update_arg", None) is not None
    ]
    assert len(bloqueos) >= 2
