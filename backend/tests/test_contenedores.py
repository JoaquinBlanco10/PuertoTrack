import secrets

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import AuditLog, Contenedor, Movimiento, Ubicacion, Usuario
from repositories import (
    AuditLogRepository,
    ContenedorRepository,
    UbicacionRepository,
    UsuarioRepository,
)
from security import generar_password_hash


PASSWORD_PRUEBA = secrets.token_urlsafe(24)


def crear_usuario(session: Session, *, email: str, rol: str) -> Usuario:
    return UsuarioRepository(session).crear(
        Usuario(
            nombre=f"Usuario {rol}",
            email=email,
            password_hash=generar_password_hash(PASSWORD_PRUEBA),
            rol=rol,
        )
    )


def obtener_headers(
    cliente: TestClient, session: Session, *, rol: str
) -> dict[str, str]:
    email = f"{rol}@contenedores.test"
    crear_usuario(session, email=email, rol=rol)
    login = cliente.post(
        "/auth/login",
        data={"username": email, "password": PASSWORD_PRUEBA},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def crear_contenedor_directo(
    session: Session,
    *,
    codigo: str = "MSCU1234567",
    ubicacion: str = "Patio historico",
    estado: str = "en_patio",
    ubicacion_id: int | None = None,
) -> Contenedor:
    return ContenedorRepository(session).crear(
        Contenedor(
            codigo=codigo,
            ubicacion_actual=ubicacion,
            ubicacion_actual_id=ubicacion_id,
            estado=estado,
        )
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
        Ubicacion(codigo=codigo, nombre=nombre, tipo=tipo, activo=activo)
    )


def test_supervisor_crea_contenedor_con_inicio_controlado(
    cliente: TestClient, session_prueba: Session
) -> None:
    headers = obtener_headers(cliente, session_prueba, rol="supervisor")
    respuesta = cliente.post(
        "/contenedores", headers=headers, json={"codigo": "mscu1234567"}
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["codigo"] == "MSCU1234567"
    assert respuesta.json()["ubicacion_actual"] == "Sin asignar"
    assert respuesta.json()["ubicacion_actual_id"] is None
    assert respuesta.json()["situacion"] == "presencia_sin_confirmar"
    assert respuesta.json()["coherencia_operacional"] == "sin_confirmar"
    assert respuesta.json()["tiene_evidencia_historica"] is False
    assert respuesta.json()["regularizacion_permitida"] is False
    assert respuesta.json()["estado"] == "disponible"


def test_operador_lista_busca_y_filtra_por_situacion(
    cliente: TestClient, session_prueba: Session
) -> None:
    interna = crear_ubicacion(
        session_prueba, codigo="PATIO_A", nombre="Patio A", tipo="interna"
    )
    externa = crear_ubicacion(
        session_prueba,
        codigo="FUERA_PUERTO",
        nombre="Fuera del puerto",
        tipo="externa",
    )
    dentro = crear_contenedor_directo(
        session_prueba,
        codigo="DENTRO1",
        ubicacion="Patio A",
        ubicacion_id=interna.id,
    )
    fuera = crear_contenedor_directo(
        session_prueba,
        codigo="FUERA1",
        ubicacion="Fuera del puerto",
        ubicacion_id=externa.id,
        estado="en_transito",
    )
    incierto = crear_contenedor_directo(
        session_prueba, codigo="LEGACY1", ubicacion="casa de Jose"
    )
    inconsistente = crear_contenedor_directo(
        session_prueba,
        codigo="REVISAR1",
        ubicacion="Patio A",
        ubicacion_id=interna.id,
        estado="en_transito",
    )
    headers = obtener_headers(cliente, session_prueba, rol="operador")

    listado = cliente.get("/contenedores", headers=headers)
    por_id = cliente.get(f"/contenedores/{dentro.id}", headers=headers)
    por_codigo = cliente.get("/contenedores/codigo/dentro1", headers=headers)
    filtrados = {
        situacion: cliente.get(
            f"/contenedores?situacion={situacion}", headers=headers
        ).json()
        for situacion in (
            "dentro_puerto",
            "fuera_puerto",
            "presencia_sin_confirmar",
        )
    }
    por_coherencia = cliente.get(
        "/contenedores?coherencia=inconsistente", headers=headers
    )

    assert listado.status_code == 200
    assert por_id.json()["situacion"] == "dentro_puerto"
    assert por_codigo.json()["id"] == dentro.id
    assert [item["id"] for item in filtrados["dentro_puerto"]] == [
        dentro.id,
        inconsistente.id,
    ]
    assert [item["id"] for item in filtrados["fuera_puerto"]] == [fuera.id]
    assert [item["id"] for item in filtrados["presencia_sin_confirmar"]] == [
        incierto.id
    ]
    assert [item["id"] for item in por_coherencia.json()] == [
        inconsistente.id
    ]


def test_busqueda_paginada_encuentra_contenedores_fuera_de_los_primeros_cien(
    cliente: TestClient, session_prueba: Session
) -> None:
    session_prueba.add_all(
        [
            Contenedor(
                codigo=f"LOTE{indice:04d}",
                ubicacion_actual="Sin asignar",
                ubicacion_actual_id=None,
                estado="disponible",
            )
            for indice in range(105)
        ]
    )
    session_prueba.flush()
    patio = crear_ubicacion(
        session_prueba,
        codigo="PATIO_BUSQUEDA",
        nombre="Patio de búsqueda",
        tipo="interna",
    )
    objetivos = [
        crear_contenedor_directo(
            session_prueba,
            codigo=f"OBJETIVO{indice}",
            ubicacion="Patio de búsqueda",
            ubicacion_id=patio.id,
        )
        for indice in range(3)
    ]
    headers = obtener_headers(cliente, session_prueba, rol="operador")

    primera_pagina = cliente.get(
        "/contenedores?offset=0&limite=100", headers=headers
    )
    busqueda = cliente.get(
        "/contenedores?codigo=objetivo&situacion=dentro_puerto"
        "&offset=1&limite=1",
        headers=headers,
    )

    assert primera_pagina.status_code == 200
    assert all(
        item["id"] != objetivos[1].id for item in primera_pagina.json()
    )
    assert busqueda.status_code == 200
    assert [item["id"] for item in busqueda.json()] == [objetivos[1].id]


def test_supervisor_corrige_solo_codigo_y_duplicados_conflictivos(
    cliente: TestClient, session_prueba: Session
) -> None:
    primero = crear_contenedor_directo(session_prueba)
    segundo = crear_contenedor_directo(session_prueba, codigo="TGHU7654321")
    headers = obtener_headers(cliente, session_prueba, rol="supervisor")

    actualizacion = cliente.patch(
        f"/contenedores/{primero.id}",
        headers=headers,
        json={"codigo": "abcd7654321"},
    )
    duplicado_crear = cliente.post(
        "/contenedores", headers=headers, json={"codigo": segundo.codigo}
    )
    duplicado_actualizar = cliente.patch(
        f"/contenedores/{primero.id}",
        headers=headers,
        json={"codigo": segundo.codigo},
    )

    assert actualizacion.status_code == 200
    assert actualizacion.json()["codigo"] == "ABCD7654321"
    assert actualizacion.json()["ubicacion_actual"] == "Patio historico"
    assert duplicado_crear.status_code == 409
    assert duplicado_actualizar.status_code == 409


def test_correccion_codigo_bloquea_la_fila_del_contenedor(
    cliente: TestClient,
    session_prueba: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    contenedor = crear_contenedor_directo(session_prueba)
    headers = obtener_headers(cliente, session_prueba, rol="supervisor")
    sentencias = []
    scalar_original = session_prueba.scalar

    def registrar_sentencia(statement, *args, **kwargs):
        sentencias.append(statement)
        return scalar_original(statement, *args, **kwargs)

    monkeypatch.setattr(session_prueba, "scalar", registrar_sentencia)
    respuesta = cliente.patch(
        f"/contenedores/{contenedor.id}",
        headers=headers,
        json={"codigo": "NUEV1234567"},
    )

    assert respuesta.status_code == 200
    assert any(
        getattr(sentencia, "_for_update_arg", None) is not None
        for sentencia in sentencias
    )


def test_creacion_y_patch_rechazan_campos_operacionales(
    cliente: TestClient, session_prueba: Session
) -> None:
    contenedor = crear_contenedor_directo(session_prueba)
    headers = obtener_headers(cliente, session_prueba, rol="supervisor")
    session_prueba.commit()
    creacion = cliente.post(
        "/contenedores",
        headers=headers,
        json={
            "codigo": "ABCD1234567",
            "ubicacion_actual": "Patio A",
            "estado": "en_patio",
        },
    )
    patch = cliente.patch(
        f"/contenedores/{contenedor.id}",
        headers=headers,
        json={"ubicacion_actual": "Patio B", "estado": "en_transito"},
    )
    faltante = cliente.post("/contenedores", headers=headers, json={})
    vacio = cliente.patch(
        f"/contenedores/{contenedor.id}", headers=headers, json={}
    )

    session_prueba.refresh(contenedor)
    assert [r.status_code for r in (creacion, patch, faltante, vacio)] == [
        400,
        400,
        400,
        400,
    ]
    assert contenedor.ubicacion_actual == "Patio historico"
    assert contenedor.estado == "en_patio"


def test_regularizacion_supervisor_es_auditada_y_no_reescribe_historial(
    cliente: TestClient, session_prueba: Session
) -> None:
    usuario = crear_usuario(
        session_prueba, email="autor-historico@test.local", rol="operador"
    )
    contenedor = crear_contenedor_directo(
        session_prueba, ubicacion="casa de Jose", estado="en_patio"
    )
    historico = Movimiento(
        contenedor_id=contenedor.id,
        usuario_id=usuario.id,
        tipo=None,
        ubicacion_origen="muelle antiguo",
        ubicacion_destino="casa de Jose",
        ubicacion_origen_id=None,
        ubicacion_destino_id=None,
    )
    session_prueba.add(historico)
    session_prueba.flush()
    patio = crear_ubicacion(
        session_prueba, codigo="PATIO_A", nombre="Patio A", tipo="interna"
    )
    headers = obtener_headers(cliente, session_prueba, rol="supervisor")

    respuesta = cliente.post(
        f"/contenedores/{contenedor.id}/regularizar-ubicacion",
        headers=headers,
        json={
            "ubicacion_id": patio.id,
            "estado": "en_patio",
            "justificacion": "Manifiesto histórico verificado por supervisión.",
        },
    )

    session_prueba.refresh(historico)
    auditoria = session_prueba.scalar(
        select(AuditLog).where(AuditLog.accion == "regularizar_ubicacion")
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["ubicacion_actual"] == "Patio A"
    assert respuesta.json()["ubicacion_actual_id"] == patio.id
    assert respuesta.json()["situacion"] == "dentro_puerto"
    assert respuesta.json()["estado"] == "en_patio"
    assert historico.ubicacion_destino == "casa de Jose"
    assert historico.ubicacion_destino_id is None
    assert session_prueba.scalar(select(func.count(Movimiento.id))) == 1
    assert auditoria is not None
    assert auditoria.datos_anteriores["ubicacion_actual"] == "casa de Jose"
    assert auditoria.datos_nuevos["ubicacion_codigo"] == "PATIO_A"
    assert auditoria.datos_nuevos["justificacion"].startswith("Manifiesto")


def test_regularizacion_valida_permisos_estado_y_rollback(
    cliente: TestClient,
    session_prueba: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    contenedor = crear_contenedor_directo(
        session_prueba, estado="disponible"
    )
    activa = crear_ubicacion(
        session_prueba, codigo="PATIO_A", nombre="Patio A", tipo="interna"
    )
    inactiva = crear_ubicacion(
        session_prueba,
        codigo="PATIO_X",
        nombre="Patio cerrado",
        tipo="interna",
        activo=False,
    )
    operador = obtener_headers(cliente, session_prueba, rol="operador")
    autor = session_prueba.scalar(
        select(Usuario).where(Usuario.email == "operador@contenedores.test")
    )
    session_prueba.add(
        Movimiento(
            contenedor_id=contenedor.id,
            usuario_id=autor.id,
            tipo=None,
            ubicacion_origen="archivo",
            ubicacion_destino="Patio historico",
        )
    )
    session_prueba.commit()
    assert cliente.post(
        f"/contenedores/{contenedor.id}/regularizar-ubicacion",
        headers=operador,
        json={
            "ubicacion_id": activa.id,
            "estado": "en_patio",
            "justificacion": "Documento histórico confirmado.",
        },
    ).status_code == 403

    supervisor = obtener_headers(cliente, session_prueba, rol="supervisor")
    session_prueba.commit()
    assert cliente.post(
        f"/contenedores/{contenedor.id}/regularizar-ubicacion",
        headers=supervisor,
        json={
            "ubicacion_id": inactiva.id,
            "estado": "en_patio",
            "justificacion": "Documento histórico confirmado.",
        },
    ).status_code == 404
    session_prueba.commit()

    def fallar(*args, **kwargs):
        raise RuntimeError("fallo de auditoria simulado")

    monkeypatch.setattr(AuditLogRepository, "crear", fallar)
    fallida = cliente.post(
        f"/contenedores/{contenedor.id}/regularizar-ubicacion",
        headers=supervisor,
        json={
            "ubicacion_id": activa.id,
            "estado": "en_patio",
            "justificacion": "Documento histórico confirmado.",
        },
    )
    session_prueba.expire_all()
    guardado = session_prueba.get(Contenedor, contenedor.id)
    assert fallida.status_code == 500
    assert guardado is not None and guardado.ubicacion_actual_id is None
    assert guardado.estado == "disponible"
    assert session_prueba.scalar(select(func.count(AuditLog.id))) == 0


def test_regularizacion_repetida_es_conflicto(
    cliente: TestClient, session_prueba: Session
) -> None:
    patio = crear_ubicacion(
        session_prueba, codigo="PATIO_A", nombre="Patio A", tipo="interna"
    )
    contenedor = crear_contenedor_directo(
        session_prueba, ubicacion="Patio A", ubicacion_id=patio.id
    )
    headers = obtener_headers(cliente, session_prueba, rol="supervisor")
    respuesta = cliente.post(
        f"/contenedores/{contenedor.id}/regularizar-ubicacion",
        headers=headers,
        json={
            "ubicacion_id": patio.id,
            "estado": "en_patio",
            "justificacion": "Documento histórico confirmado.",
        },
    )
    assert respuesta.status_code == 409


def test_no_regulariza_un_alta_nueva_sin_evidencia(
    cliente: TestClient, session_prueba: Session
) -> None:
    headers = obtener_headers(cliente, session_prueba, rol="supervisor")
    creado = cliente.post(
        "/contenedores", headers=headers, json={"codigo": "NUEVO1234567"}
    ).json()
    patio = crear_ubicacion(
        session_prueba, codigo="MUELLE_1", nombre="Muelle 1", tipo="interna"
    )

    respuesta = cliente.post(
        f"/contenedores/{creado['id']}/regularizar-ubicacion",
        headers=headers,
        json={
            "ubicacion_id": patio.id,
            "estado": "en_patio",
            "justificacion": "Supuesto antecedente no verificable.",
        },
    )

    guardado = session_prueba.get(Contenedor, creado["id"])
    assert respuesta.status_code == 409
    assert guardado.ubicacion_actual == "Sin asignar"
    assert guardado.ubicacion_actual_id is None
    assert guardado.estado == "disponible"


def test_regularizacion_exige_estado_coherente_y_justificacion(
    cliente: TestClient, session_prueba: Session
) -> None:
    autor = crear_usuario(
        session_prueba, email="autor-evidencia@test.local", rol="operador"
    )
    contenedor = crear_contenedor_directo(session_prueba)
    session_prueba.add(
        Movimiento(
            contenedor_id=contenedor.id,
            usuario_id=autor.id,
            tipo=None,
            ubicacion_origen="archivo",
            ubicacion_destino="Patio historico",
        )
    )
    externa = crear_ubicacion(
        session_prueba,
        codigo="DEPOSITO_EXT",
        nombre="Depósito externo",
        tipo="externa",
    )
    headers = obtener_headers(cliente, session_prueba, rol="supervisor")
    session_prueba.commit()

    incoherente = cliente.post(
        f"/contenedores/{contenedor.id}/regularizar-ubicacion",
        headers=headers,
        json={
            "ubicacion_id": externa.id,
            "estado": "en_patio",
            "justificacion": "Documento histórico confirmado.",
        },
    )
    sin_justificacion = cliente.post(
        f"/contenedores/{contenedor.id}/regularizar-ubicacion",
        headers=headers,
        json={"ubicacion_id": externa.id, "estado": "en_transito"},
    )
    correcta = cliente.post(
        f"/contenedores/{contenedor.id}/regularizar-ubicacion",
        headers=headers,
        json={
            "ubicacion_id": externa.id,
            "estado": "en_transito",
            "justificacion": "Manifiesto de salida histórico verificado.",
        },
    )

    assert incoherente.status_code == 400
    assert sin_justificacion.status_code == 400
    assert correcta.status_code == 200
    assert correcta.json()["estado"] == "en_transito"
    assert correcta.json()["coherencia_operacional"] == "coherente"


def test_corrige_inconsistencia_previa_si_existe_auditoria_de_regularizacion(
    cliente: TestClient, session_prueba: Session
) -> None:
    patio = crear_ubicacion(
        session_prueba, codigo="MUELLE_1", nombre="Muelle 1", tipo="interna"
    )
    contenedor = crear_contenedor_directo(
        session_prueba,
        ubicacion="Muelle 1",
        ubicacion_id=patio.id,
        estado="disponible",
    )
    headers = obtener_headers(cliente, session_prueba, rol="supervisor")
    supervisor = session_prueba.scalar(
        select(Usuario).where(Usuario.email == "supervisor@contenedores.test")
    )
    session_prueba.add(
        AuditLog(
            usuario_id=supervisor.id,
            accion="regularizar_ubicacion",
            entidad="contenedor",
            entidad_id=contenedor.id,
            datos_anteriores={"ubicacion_actual": "Sin asignar"},
            datos_nuevos={"ubicacion_actual": "Muelle 1"},
        )
    )
    session_prueba.commit()

    detalle = cliente.get(f"/contenedores/{contenedor.id}", headers=headers)
    corregida = cliente.post(
        f"/contenedores/{contenedor.id}/regularizar-ubicacion",
        headers=headers,
        json={
            "ubicacion_id": patio.id,
            "estado": "en_patio",
            "justificacion": "Corrección del estado omitido en regularización previa.",
        },
    )

    assert detalle.json()["coherencia_operacional"] == "inconsistente"
    assert detalle.json()["tiene_evidencia_historica"] is True
    assert detalle.json()["regularizacion_permitida"] is True
    assert corregida.status_code == 200
    assert corregida.json()["estado"] == "en_patio"
    assert corregida.json()["coherencia_operacional"] == "coherente"


def test_errores_basicos_permisos_y_sin_delete(
    cliente: TestClient, session_prueba: Session
) -> None:
    contenedor = crear_contenedor_directo(session_prueba)
    operador = obtener_headers(cliente, session_prueba, rol="operador")

    assert cliente.get("/contenedores").status_code == 401
    assert cliente.get("/contenedores/9999", headers=operador).status_code == 404
    assert cliente.get(
        "/contenedores/codigo/INEXISTENTE", headers=operador
    ).status_code == 404
    assert cliente.post(
        "/contenedores", headers=operador, json={"codigo": "ABCD1234567"}
    ).status_code == 403
    assert cliente.patch(
        f"/contenedores/{contenedor.id}",
        headers=operador,
        json={"codigo": "NUEVO1234567"},
    ).status_code == 403
    assert cliente.delete(
        f"/contenedores/{contenedor.id}", headers=operador
    ).status_code == 405
