import argparse
import getpass

from sqlalchemy.exc import IntegrityError

from database import SessionLocal
from models import Usuario
from repositories import UsuarioRepository
from security import generar_password_hash


def leer_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Crea un usuario de PuertoTrack de forma controlada."
    )
    parser.add_argument("--nombre", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument(
        "--rol",
        choices=("operador", "supervisor"),
        default="operador",
    )
    return parser.parse_args()


def solicitar_password() -> str:
    password = getpass.getpass("Contraseña: ")
    confirmacion = getpass.getpass("Confirmar contraseña: ")

    if password != confirmacion:
        raise ValueError("Las contraseñas no coinciden.")
    if len(password) < 12:
        raise ValueError("La contraseña debe tener al menos 12 caracteres.")
    return password


def main() -> None:
    argumentos = leer_argumentos()
    email = argumentos.email.strip().lower()
    password = solicitar_password()

    with SessionLocal() as session:
        repository = UsuarioRepository(session)
        if repository.buscar_por_email(email) is not None:
            raise ValueError("Ya existe un usuario con ese email.")

        usuario = Usuario(
            nombre=argumentos.nombre.strip(),
            email=email,
            password_hash=generar_password_hash(password),
            rol=argumentos.rol,
        )
        try:
            repository.crear(usuario)
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise ValueError("No se pudo crear el usuario.") from error

    print(f"Usuario creado: {email} ({argumentos.rol})")


if __name__ == "__main__":
    main()
