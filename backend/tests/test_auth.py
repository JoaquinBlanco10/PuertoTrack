import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt
import auth as auth_module
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from models import Usuario
from repositories import UsuarioRepository
from login_protection import LimitadorLogin
from security import crear_access_token, generar_password_hash


PASSWORD_PRUEBA = secrets.token_urlsafe(24)


def crear_usuario(
    session: Session,
    *,
    email: str,
    rol: str = "operador",
    activo: bool = True,
) -> Usuario:
    return UsuarioRepository(session).crear(
        Usuario(
            nombre=f"Usuario {rol}",
            email=email,
            password_hash=generar_password_hash(PASSWORD_PRUEBA),
            rol=rol,
            activo=activo,
        )
    )


def iniciar_sesion(cliente: TestClient, email: str) -> str:
    respuesta = cliente.post(
        "/auth/login",
        data={"username": email, "password": PASSWORD_PRUEBA},
    )
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["token_type"] == "bearer"
    return cuerpo["access_token"]


def autorizacion(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_login_correcto_y_auth_me(
    cliente: TestClient, session_prueba: Session
) -> None:
    usuario = crear_usuario(
        session_prueba, email="operador@puertotrack.test"
    )

    token = iniciar_sesion(cliente, usuario.email)
    respuesta = cliente.get("/auth/me", headers=autorizacion(token))

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "id": usuario.id,
        "nombre": usuario.nombre,
        "email": usuario.email,
        "rol": "operador",
        "activo": True,
        "fecha_creacion": usuario.fecha_creacion.isoformat(),
    }
    assert "password_hash" not in respuesta.json()


def test_login_rechaza_password_incorrecta(
    cliente: TestClient, session_prueba: Session
) -> None:
    usuario = crear_usuario(
        session_prueba, email="password@puertotrack.test"
    )

    respuesta = cliente.post(
        "/auth/login",
        data={"username": usuario.email, "password": "password-incorrecta"},
    )

    assert respuesta.status_code == 401
    assert respuesta.headers["www-authenticate"] == "Bearer"


def test_login_limita_fuerza_bruta_por_email(
    cliente: TestClient, session_prueba: Session
) -> None:
    usuario = crear_usuario(
        session_prueba, email="limitado@puertotrack.test"
    )

    respuestas = [
        cliente.post(
            "/auth/login",
            data={"username": usuario.email, "password": "incorrecta"},
        )
        for _ in range(5)
    ]
    bloqueada = cliente.post(
        "/auth/login",
        data={"username": usuario.email, "password": PASSWORD_PRUEBA},
    )

    assert all(respuesta.status_code == 401 for respuesta in respuestas)
    assert bloqueada.status_code == 429
    assert int(bloqueada.headers["retry-after"]) > 0


def test_login_verifica_hash_ficticio_si_el_usuario_no_existe(
    cliente: TestClient, monkeypatch
) -> None:
    hashes_recibidos: list[str | None] = []

    def verificar(_: str, hash_almacenado: str | None) -> bool:
        hashes_recibidos.append(hash_almacenado)
        return False

    monkeypatch.setattr(
        auth_module, "verificar_password_con_hash_ficticio", verificar
    )
    respuesta = cliente.post(
        "/auth/login",
        data={
            "username": "inexistente@puertotrack.test",
            "password": "cualquier-password",
        },
    )

    assert respuesta.status_code == 401
    assert hashes_recibidos == [None]


def test_login_ignora_ip_reenviada_no_confiable_y_entrega_retry_after(
    cliente: TestClient, monkeypatch
) -> None:
    instante = [100.0]
    limitador = LimitadorLogin(
        ventana_segundos=60,
        max_fallos_email=10,
        max_fallos_ip=2,
        reloj=lambda: instante[0],
    )
    monkeypatch.setattr(auth_module, "limitador_login", limitador)

    for indice in range(2):
        respuesta = cliente.post(
            "/auth/login",
            headers={"X-Forwarded-For": f"203.0.113.{indice + 1}"},
            data={
                "username": f"inexistente-{indice}@puertotrack.test",
                "password": "incorrecta",
            },
        )
        assert respuesta.status_code == 401

    bloqueada = cliente.post(
        "/auth/login",
        headers={"X-Forwarded-For": "198.51.100.50"},
        data={
            "username": "otro@puertotrack.test",
            "password": "incorrecta",
        },
    )

    assert bloqueada.status_code == 429
    assert bloqueada.headers["retry-after"] == "60"


def test_token_invalido_es_rechazado(cliente: TestClient) -> None:
    respuesta = cliente.get(
        "/auth/me",
        headers=autorizacion("token.jwt.invalido"),
    )

    assert respuesta.status_code == 401
    assert respuesta.headers["www-authenticate"] == "Bearer"


def test_token_expirado_es_rechazado(
    cliente: TestClient, session_prueba: Session
) -> None:
    usuario = crear_usuario(
        session_prueba, email="token-expirado@puertotrack.test"
    )
    ahora = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": str(usuario.id),
            "iat": ahora - timedelta(minutes=2),
            "exp": ahora - timedelta(minutes=1),
        },
        os.environ["JWT_SECRET_KEY"],
        algorithm="HS256",
    )

    respuesta = cliente.get("/auth/me", headers=autorizacion(token))

    assert respuesta.status_code == 401


def test_usuario_inactivo_no_puede_ingresar_ni_reutilizar_token(
    cliente: TestClient, session_prueba: Session
) -> None:
    usuario = crear_usuario(
        session_prueba,
        email="inactivo@puertotrack.test",
        activo=False,
    )

    login = cliente.post(
        "/auth/login",
        data={"username": usuario.email, "password": PASSWORD_PRUEBA},
    )
    token = crear_access_token(usuario.id)
    acceso = cliente.get("/auth/me", headers=autorizacion(token))

    assert login.status_code == 403
    assert acceso.status_code == 403
    assert acceso.json()["detail"] == "El usuario está inactivo"


def test_operador_accede_a_ruta_compartida_pero_no_a_supervisor(
    cliente: TestClient, session_prueba: Session
) -> None:
    usuario = crear_usuario(
        session_prueba, email="rol-operador@puertotrack.test"
    )
    headers = autorizacion(iniciar_sesion(cliente, usuario.email))

    compartida = cliente.get("/auth/protegido", headers=headers)
    supervisor = cliente.get("/auth/supervisor", headers=headers)

    assert compartida.status_code == 200
    assert compartida.json()["rol"] == "operador"
    assert supervisor.status_code == 403


def test_supervisor_accede_a_ambas_rutas(
    cliente: TestClient, session_prueba: Session
) -> None:
    usuario = crear_usuario(
        session_prueba,
        email="rol-supervisor@puertotrack.test",
        rol="supervisor",
    )
    headers = autorizacion(iniciar_sesion(cliente, usuario.email))

    compartida = cliente.get("/auth/protegido", headers=headers)
    supervisor = cliente.get("/auth/supervisor", headers=headers)

    assert compartida.status_code == 200
    assert supervisor.status_code == 200
    assert supervisor.json()["rol"] == "supervisor"
