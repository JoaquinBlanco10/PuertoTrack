import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError


ALGORITMO_JWT = "HS256"
MINUTOS_EXPIRACION_POR_DEFECTO = 30
MIN_BYTES_SECRETO_JWT = 32
MIN_CARACTERES_DISTINTOS_SECRETO_JWT = 8

_SECRETOS_JWT_CONOCIDOS = frozenset(
    {
        "secret",
        "jwtsecret",
        "jwtsecretkey",
        "changeme",
        "cambiame",
        "yoursecretkey",
        "supersecret",
        "password",
        "puertotrack",
        "development",
        "abcdefghijklmnopqrstuvwxyz123456",
        "01234567890123456789012345678901",
    }
)

password_hash = PasswordHash.recommended()
_HASH_PASSWORD_FICTICIO = password_hash.hash(secrets.token_urlsafe(32))


def generar_password_hash(password: str) -> str:
    return password_hash.hash(password)


def verificar_password(password: str, hash_almacenado: str) -> bool:
    try:
        return password_hash.verify(password, hash_almacenado)
    except (UnknownHashError, ValueError):
        return False


def verificar_password_con_hash_ficticio(
    password: str, hash_almacenado: str | None
) -> bool:
    """Ejecuta siempre Argon2, incluso cuando el usuario no existe."""

    hash_para_verificar = hash_almacenado or _HASH_PASSWORD_FICTICIO
    coincide = verificar_password(password, hash_para_verificar)
    return hash_almacenado is not None and coincide


def _es_valor_repetitivo(valor: str) -> bool:
    for longitud in range(1, (len(valor) // 2) + 1):
        if len(valor) % longitud == 0:
            fragmento = valor[:longitud]
            if fragmento * (len(valor) // longitud) == valor:
                return True
    return False


def _obtener_secreto_jwt() -> str:
    secreto = os.getenv("JWT_SECRET_KEY")
    if secreto is None or not secreto.strip():
        raise RuntimeError(
            "JWT_SECRET_KEY no está configurada. Revisa .env.example."
        )
    secreto_limpio = secreto.strip()
    normalizado = "".join(
        caracter for caracter in secreto_limpio.casefold() if caracter.isalnum()
    )
    if (
        secreto != secreto_limpio
        or len(secreto_limpio.encode("utf-8")) < MIN_BYTES_SECRETO_JWT
        or len(set(secreto_limpio))
        < MIN_CARACTERES_DISTINTOS_SECRETO_JWT
        or normalizado in _SECRETOS_JWT_CONOCIDOS
        or _es_valor_repetitivo(secreto_limpio)
    ):
        raise RuntimeError(
            "JWT_SECRET_KEY no cumple los requisitos mínimos de seguridad. "
            "Configura un valor aleatorio de al menos 32 bytes."
        )
    return secreto_limpio


def _obtener_minutos_expiracion() -> int:
    valor = os.getenv(
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        str(MINUTOS_EXPIRACION_POR_DEFECTO),
    )
    try:
        minutos = int(valor)
    except ValueError as error:
        raise RuntimeError(
            "ACCESS_TOKEN_EXPIRE_MINUTES debe ser un número entero."
        ) from error

    if minutos <= 0:
        raise RuntimeError(
            "ACCESS_TOKEN_EXPIRE_MINUTES debe ser mayor que cero."
        )
    return minutos


def crear_access_token(usuario_id: int) -> str:
    ahora = datetime.now(timezone.utc)
    datos = {
        "sub": str(usuario_id),
        "iat": ahora,
        "exp": ahora + timedelta(minutes=_obtener_minutos_expiracion()),
    }
    return jwt.encode(datos, _obtener_secreto_jwt(), algorithm=ALGORITMO_JWT)


def decodificar_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(
        token,
        _obtener_secreto_jwt(),
        algorithms=[ALGORITMO_JWT],
        options={"require": ["sub", "iat", "exp"]},
    )


def validar_configuracion_seguridad() -> None:
    """Valida la configuración sensible sin devolver ni registrar secretos."""

    _obtener_secreto_jwt()
    _obtener_minutos_expiracion()


__all__ = [
    "InvalidTokenError",
    "crear_access_token",
    "decodificar_access_token",
    "generar_password_hash",
    "verificar_password",
    "verificar_password_con_hash_ficticio",
    "validar_configuracion_seguridad",
]
