import json

from sqlalchemy.orm import Session

from models import AuditLog
from repositories import AuditLogRepository


FRAGMENTOS_SENSIBLES = frozenset(
    {
        "password",
        "hash",
        "contraseña",
        "contrasena",
        "clave",
        "token",
        "jwt",
        "secret",
        "secreto",
    }
)


class DatosAuditoriaInvalidos(Exception):
    pass


class AuditoriaService:
    """Registra auditorías sin controlar el commit de la transacción."""

    def __init__(self, session: Session) -> None:
        self.repository = AuditLogRepository(session)

    def registrar(
        self,
        *,
        usuario_id: int | None,
        accion: str,
        entidad: str,
        entidad_id: int,
        datos_anteriores: dict[str, object] | None,
        datos_nuevos: dict[str, object] | None,
    ) -> AuditLog:
        self._validar_snapshot(datos_anteriores)
        self._validar_snapshot(datos_nuevos)
        registro = AuditLog(
            usuario_id=usuario_id,
            accion=accion,
            entidad=entidad,
            entidad_id=entidad_id,
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos,
        )
        return self.repository.crear(registro)

    def listar(
        self,
        *,
        usuario_id: int | None = None,
        entidad: str | None = None,
        entidad_id: int | None = None,
        accion: str | None = None,
        offset: int = 0,
        limite: int = 100,
    ) -> list[AuditLog]:
        return self.repository.listar_con_filtros(
            usuario_id=usuario_id,
            entidad=self._normalizar_filtro(entidad),
            entidad_id=entidad_id,
            accion=self._normalizar_filtro(accion),
            offset=offset,
            limite=limite,
        )

    @classmethod
    def _validar_snapshot(
        cls, datos: dict[str, object] | None
    ) -> None:
        if datos is None:
            return
        cls._validar_contenido(datos)
        try:
            json.dumps(datos)
        except (TypeError, ValueError) as error:
            raise DatosAuditoriaInvalidos(
                "Los datos de auditoría deben ser serializables como JSON."
            ) from error

    @classmethod
    def _validar_contenido(cls, valor: object) -> None:
        if isinstance(valor, dict):
            for clave, contenido in valor.items():
                clave_normalizada = str(clave).casefold()
                if any(
                    fragmento in clave_normalizada
                    for fragmento in FRAGMENTOS_SENSIBLES
                ):
                    raise DatosAuditoriaInvalidos(
                        f"El campo sensible {clave} no puede auditarse."
                    )
                cls._validar_contenido(contenido)
        elif isinstance(valor, (list, tuple)):
            for elemento in valor:
                cls._validar_contenido(elemento)

    @staticmethod
    def _normalizar_filtro(valor: str | None) -> str | None:
        if valor is None:
            return None
        valor_limpio = valor.strip().lower()
        return valor_limpio or None
