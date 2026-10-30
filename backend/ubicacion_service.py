from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from auditoria_service import AuditoriaService
from models import Ubicacion, Usuario
from repositories import UbicacionRepository
from schemas import TipoUbicacion, UbicacionActualizar, UbicacionCrear


class ErrorUbicacion(Exception):
    """Error de negocio base del catálogo de ubicaciones."""


class DatosUbicacionInvalidos(ErrorUbicacion):
    pass


class UbicacionNoEncontrada(ErrorUbicacion):
    pass


class CodigoUbicacionDuplicado(ErrorUbicacion):
    pass


class TipoUbicacionBloqueado(ErrorUbicacion):
    pass


class ErrorPersistenciaUbicacion(ErrorUbicacion):
    pass


class UbicacionService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = UbicacionRepository(session)
        self.auditoria = AuditoriaService(session)

    def crear(self, datos: UbicacionCrear, usuario: Usuario) -> Ubicacion:
        codigo = self._validar_texto(datos.codigo, "codigo", 30).upper()
        nombre = self._validar_texto(datos.nombre, "nombre", 120)
        tipo = self._normalizar_tipo(datos.tipo)
        if self.repository.buscar_por_codigo(codigo) is not None:
            raise CodigoUbicacionDuplicado(
                f"Ya existe una ubicación con el código {codigo}."
            )

        ubicacion = Ubicacion(
            codigo=codigo,
            nombre=nombre,
            tipo=tipo,
            activo=True,
        )
        try:
            self.repository.crear(ubicacion)
            self.auditoria.registrar(
                usuario_id=usuario.id,
                accion="crear",
                entidad="ubicacion",
                entidad_id=ubicacion.id,
                datos_anteriores=None,
                datos_nuevos=self._snapshot(ubicacion),
            )
            self.session.commit()
            return ubicacion
        except IntegrityError as error:
            self.session.rollback()
            raise CodigoUbicacionDuplicado(
                f"Ya existe una ubicación con el código {codigo}."
            ) from error
        except Exception as error:
            self.session.rollback()
            raise ErrorPersistenciaUbicacion(
                "No se pudo crear la ubicación."
            ) from error

    def listar(
        self,
        *,
        incluir_inactivas: bool = False,
        tipo: TipoUbicacion | None = None,
        offset: int = 0,
        limite: int = 100,
    ) -> list[Ubicacion]:
        return self.repository.listar_filtradas(
            solo_activas=not incluir_inactivas,
            tipo=tipo.value if tipo is not None else None,
            offset=offset,
            limite=limite,
        )

    def buscar_por_id(
        self, ubicacion_id: int, *, permitir_inactiva: bool = False
    ) -> Ubicacion:
        ubicacion = self.repository.buscar_por_id(ubicacion_id)
        if ubicacion is None or (not permitir_inactiva and not ubicacion.activo):
            raise UbicacionNoEncontrada("Ubicación no encontrada.")
        return ubicacion

    def actualizar(
        self,
        ubicacion_id: int,
        datos: UbicacionActualizar,
        usuario: Usuario,
    ) -> Ubicacion:
        ubicacion = self.repository.buscar_por_id_para_actualizar(ubicacion_id)
        if ubicacion is None:
            raise UbicacionNoEncontrada("Ubicación no encontrada.")
        cambios = datos.model_dump(exclude_unset=True)
        if not cambios:
            raise DatosUbicacionInvalidos(
                "Debes proporcionar al menos un campo para actualizar."
            )

        anteriores = self._snapshot(ubicacion)
        nuevo_nombre = ubicacion.nombre
        nuevo_tipo = ubicacion.tipo
        nuevo_activo = ubicacion.activo
        if "nombre" in cambios:
            if cambios["nombre"] is None:
                raise DatosUbicacionInvalidos("nombre no puede ser nulo.")
            nuevo_nombre = self._validar_texto(
                cambios["nombre"], "nombre", 120
            )
        if "tipo" in cambios:
            if cambios["tipo"] is None:
                raise DatosUbicacionInvalidos("tipo no puede ser nulo.")
            nuevo_tipo = self._normalizar_tipo(cambios["tipo"])
            if (
                nuevo_tipo != ubicacion.tipo
                and self.repository.esta_utilizada(ubicacion.id)
            ):
                raise TipoUbicacionBloqueado(
                    "No se puede cambiar el tipo de una ubicación utilizada."
                )
        if "activo" in cambios:
            if cambios["activo"] is None:
                raise DatosUbicacionInvalidos("activo no puede ser nulo.")
            nuevo_activo = cambios["activo"]

        try:
            ubicacion.nombre = nuevo_nombre
            ubicacion.tipo = nuevo_tipo
            ubicacion.activo = nuevo_activo
            self.repository.actualizar(ubicacion)
            self.auditoria.registrar(
                usuario_id=usuario.id,
                accion="actualizar",
                entidad="ubicacion",
                entidad_id=ubicacion.id,
                datos_anteriores=anteriores,
                datos_nuevos=self._snapshot(ubicacion),
            )
            self.session.commit()
            return ubicacion
        except Exception as error:
            self.session.rollback()
            raise ErrorPersistenciaUbicacion(
                "No se pudo actualizar la ubicación."
            ) from error

    @staticmethod
    def _validar_texto(valor: str, campo: str, limite: int) -> str:
        limpio = valor.strip()
        if not limpio:
            raise DatosUbicacionInvalidos(f"{campo} es obligatorio.")
        if len(limpio) > limite:
            raise DatosUbicacionInvalidos(
                f"{campo} no puede superar {limite} caracteres."
            )
        return limpio

    @staticmethod
    def _normalizar_tipo(tipo: str | TipoUbicacion) -> str:
        valor = tipo.value if isinstance(tipo, TipoUbicacion) else tipo
        if valor not in {"interna", "externa"}:
            raise DatosUbicacionInvalidos("Tipo de ubicación no permitido.")
        return valor

    @staticmethod
    def _snapshot(ubicacion: Ubicacion) -> dict[str, object]:
        return {
            "codigo": ubicacion.codigo,
            "nombre": ubicacion.nombre,
            "tipo": ubicacion.tipo,
            "activo": ubicacion.activo,
        }
