from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from database import obtener_sesion
from login_protection import limitador_login
from models import Usuario
from repositories import UsuarioRepository
from schemas import AccesoRespuesta, TokenRespuesta, UsuarioRespuesta
from security import (
    InvalidTokenError,
    crear_access_token,
    decodificar_access_token,
    verificar_password_con_hash_ficticio,
)


router = APIRouter(prefix="/auth", tags=["Autenticación"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

Sesion = Annotated[Session, Depends(obtener_sesion)]
Token = Annotated[str, Depends(oauth2_scheme)]


def _error_credenciales() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )


def obtener_usuario_actual(token: Token, session: Sesion) -> Usuario:
    try:
        payload = decodificar_access_token(token)
        usuario_id = int(payload["sub"])
    except (InvalidTokenError, KeyError, TypeError, ValueError):
        raise _error_credenciales()

    usuario = UsuarioRepository(session).buscar_por_id(usuario_id)
    if usuario is None:
        raise _error_credenciales()
    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario está inactivo",
        )
    return usuario


def requerir_roles(*roles_permitidos: str) -> Callable[..., Usuario]:
    def verificar_rol(
        usuario: Annotated[Usuario, Depends(obtener_usuario_actual)],
    ) -> Usuario:
        if usuario.rol not in roles_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para acceder a este recurso",
            )
        return usuario

    return verificar_rol


@router.post("/login", response_model=TokenRespuesta)
def login(
    request: Request,
    formulario: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Sesion,
) -> TokenRespuesta:
    email = formulario.username.strip().lower()
    ip = request.client.host if request.client is not None else "desconocida"
    espera = limitador_login.iniciar_intento(email=email, ip=ip)
    if espera:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados intentos de inicio de sesión. Intenta más tarde.",
            headers={"Retry-After": str(espera)},
        )

    intento_finalizado = False
    try:
        usuario = UsuarioRepository(session).buscar_por_email(email)
        password_valida = verificar_password_con_hash_ficticio(
            formulario.password,
            usuario.password_hash if usuario is not None else None,
        )
        if usuario is None or not password_valida:
            limitador_login.registrar_fallo(email=email, ip=ip)
            intento_finalizado = True
            raise _error_credenciales()

        limitador_login.registrar_exito(email=email, ip=ip)
        intento_finalizado = True
    finally:
        if not intento_finalizado:
            limitador_login.cancelar_intento(email=email, ip=ip)

    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario está inactivo",
        )

    return TokenRespuesta(access_token=crear_access_token(usuario.id))


@router.get("/me", response_model=UsuarioRespuesta)
def obtener_mi_usuario(
    usuario: Annotated[Usuario, Depends(obtener_usuario_actual)],
) -> Usuario:
    return usuario


@router.get("/protegido", response_model=AccesoRespuesta)
def acceso_ambos_roles(
    usuario: Annotated[
        Usuario, Depends(requerir_roles("operador", "supervisor"))
    ],
) -> AccesoRespuesta:
    return AccesoRespuesta(
        mensaje="Acceso autorizado para usuario autenticado",
        rol=usuario.rol,
    )


@router.get("/supervisor", response_model=AccesoRespuesta)
def acceso_solo_supervisor(
    usuario: Annotated[Usuario, Depends(requerir_roles("supervisor"))],
) -> AccesoRespuesta:
    return AccesoRespuesta(
        mensaje="Acceso autorizado para supervisor",
        rol=usuario.rol,
    )
