from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from auditoria_service import AuditoriaService
from models import Contenedor, Usuario
from repositories import ContenedorRepository, UbicacionRepository
from schemas import ContenedorActualizar, ContenedorCrear


class ErrorContenedor(Exception):
    """Error de negocio base para la gestión de contenedores."""


class DatosContenedorInvalidos(ErrorContenedor):
    pass


class ContenedorNoEncontrado(ErrorContenedor):
    pass


class CodigoContenedorDuplicado(ErrorContenedor):
    pass


class ErrorPersistenciaContenedor(ErrorContenedor):
    pass


class UbicacionRegularizacionNoEncontrada(ErrorContenedor):
    pass


class ContenedorYaRegularizado(ErrorContenedor):
    pass


class RegularizacionSinEvidencia(ErrorContenedor):
    pass


class ContenedorService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = ContenedorRepository(session)
        self.ubicaciones = UbicacionRepository(session)
        self.auditoria = AuditoriaService(session)

    def crear(self, datos: ContenedorCrear, usuario: Usuario) -> Contenedor:
        codigo = self._validar_texto(datos.codigo, "codigo", 20).upper()

        if self.repository.buscar_por_codigo(codigo) is not None:
            raise CodigoContenedorDuplicado(
                f"Ya existe un contenedor con el código {codigo}."
            )

        contenedor = Contenedor(
            codigo=codigo,
            ubicacion_actual="Sin asignar",
            ubicacion_actual_id=None,
            estado="disponible",
        )
        try:
            self.repository.crear(contenedor)
            self.auditoria.registrar(
                usuario_id=usuario.id,
                accion="crear",
                entidad="contenedor",
                entidad_id=contenedor.id,
                datos_anteriores=None,
                datos_nuevos={
                    "codigo": contenedor.codigo,
                    "ubicacion_actual": contenedor.ubicacion_actual,
                    "estado": contenedor.estado,
                },
            )
            self.session.commit()
        except IntegrityError as error:
            self.session.rollback()
            raise CodigoContenedorDuplicado(
                f"Ya existe un contenedor con el código {codigo}."
            ) from error
        except Exception as error:
            self.session.rollback()
            raise ErrorPersistenciaContenedor(
                "No se pudo crear el contenedor."
            ) from error
        return contenedor

    def listar(
        self,
        offset: int = 0,
        limite: int = 100,
        situacion: str | None = None,
        coherencia: str | None = None,
        codigo: str | None = None,
    ) -> list[Contenedor]:
        codigo_normalizado = None
        if codigo is not None:
            codigo_normalizado = self._validar_texto(
                codigo, "codigo", 20
            ).upper()
        return self.repository.listar(
            offset=offset,
            limite=limite,
            situacion=situacion,
            coherencia=coherencia,
            codigo=codigo_normalizado,
        )

    def buscar_por_id(self, contenedor_id: int) -> Contenedor:
        contenedor = self.repository.buscar_por_id(contenedor_id)
        if contenedor is None:
            raise ContenedorNoEncontrado("Contenedor no encontrado.")
        return contenedor

    def regularizar_ubicacion(
        self,
        contenedor_id: int,
        ubicacion_id: int,
        estado: str,
        justificacion: str,
        usuario: Usuario,
    ) -> Contenedor:
        try:
            contenedor = self.repository.buscar_por_id_para_actualizar(
                contenedor_id
            )
            if contenedor is None:
                raise ContenedorNoEncontrado("Contenedor no encontrado.")
            if not contenedor.tiene_evidencia_historica:
                raise RegularizacionSinEvidencia(
                    "La regularización requiere un movimiento histórico o una "
                    "regularización previa auditada. Para un contenedor nuevo "
                    "registra su primera entrada en Movimientos."
                )
            if not contenedor.regularizacion_permitida:
                raise ContenedorYaRegularizado(
                    "El contenedor ya tiene ubicación y estado operacional coherentes."
                )

            ubicacion = self.ubicaciones.buscar_por_id_para_actualizar(
                ubicacion_id
            )
            if ubicacion is None or not ubicacion.activo:
                raise UbicacionRegularizacionNoEncontrada(
                    "La ubicación no existe o está inactiva."
                )

            estado_esperado = (
                "en_patio" if ubicacion.tipo == "interna" else "en_transito"
            )
            if estado != estado_esperado:
                raise DatosContenedorInvalidos(
                    f"Una ubicación {ubicacion.tipo} requiere estado "
                    f"{estado_esperado}."
                )
            justificacion_limpia = self._validar_texto(
                justificacion, "justificacion", 500
            )
            if len(justificacion_limpia) < 10:
                raise DatosContenedorInvalidos(
                    "justificacion debe tener al menos 10 caracteres."
                )

            anteriores = {
                "ubicacion_actual": contenedor.ubicacion_actual,
                "ubicacion_actual_id": contenedor.ubicacion_actual_id,
                "estado": contenedor.estado,
            }
            contenedor.ubicacion_actual = ubicacion.nombre
            contenedor.ubicacion_actual_id = ubicacion.id
            contenedor.ubicacion_actual_catalogo = ubicacion
            contenedor.estado = estado_esperado
            self.repository.actualizar(contenedor)
            self.auditoria.registrar(
                usuario_id=usuario.id,
                accion="regularizar_ubicacion",
                entidad="contenedor",
                entidad_id=contenedor.id,
                datos_anteriores=anteriores,
                datos_nuevos={
                    "ubicacion_actual": contenedor.ubicacion_actual,
                    "ubicacion_actual_id": contenedor.ubicacion_actual_id,
                    "ubicacion_codigo": ubicacion.codigo,
                    "estado": contenedor.estado,
                    "justificacion": justificacion_limpia,
                },
            )
            self.session.commit()
            return contenedor
        except (
            ContenedorNoEncontrado,
            ContenedorYaRegularizado,
            RegularizacionSinEvidencia,
            UbicacionRegularizacionNoEncontrada,
            DatosContenedorInvalidos,
        ):
            self.session.rollback()
            raise
        except Exception as error:
            self.session.rollback()
            raise ErrorPersistenciaContenedor(
                "No se pudo regularizar la ubicación del contenedor."
            ) from error

    def buscar_por_codigo(self, codigo: str) -> Contenedor:
        codigo_normalizado = self._validar_texto(
            codigo, "codigo", 20
        ).upper()
        contenedor = self.repository.buscar_por_codigo(codigo_normalizado)
        if contenedor is None:
            raise ContenedorNoEncontrado("Contenedor no encontrado.")
        return contenedor

    def actualizar(
        self,
        contenedor_id: int,
        datos: ContenedorActualizar,
        usuario: Usuario,
    ) -> Contenedor:
        try:
            contenedor = self.repository.buscar_por_id_para_actualizar(
                contenedor_id
            )
            if contenedor is None:
                raise ContenedorNoEncontrado("Contenedor no encontrado.")

            datos_anteriores = {"codigo": contenedor.codigo}
            cambios = datos.model_dump(exclude_unset=True)
            if not cambios:
                raise DatosContenedorInvalidos(
                    "Debes proporcionar al menos un campo para actualizar."
                )
            if cambios.get("codigo") is None:
                raise DatosContenedorInvalidos("codigo no puede ser nulo.")

            codigo = self._validar_texto(
                cambios["codigo"], "codigo", 20
            ).upper()
            existente = self.repository.buscar_por_codigo(codigo)
            if existente is not None and existente.id != contenedor.id:
                raise CodigoContenedorDuplicado(
                    f"Ya existe un contenedor con el código {codigo}."
                )
            contenedor.codigo = codigo

            self.repository.actualizar(contenedor)
            self.auditoria.registrar(
                usuario_id=usuario.id,
                accion="actualizar",
                entidad="contenedor",
                entidad_id=contenedor.id,
                datos_anteriores=datos_anteriores,
                datos_nuevos={"codigo": contenedor.codigo},
            )
            self.session.commit()
        except (
            DatosContenedorInvalidos,
            ContenedorNoEncontrado,
            CodigoContenedorDuplicado,
        ):
            self.session.rollback()
            raise
        except IntegrityError as error:
            self.session.rollback()
            raise CodigoContenedorDuplicado(
                f"Ya existe un contenedor con el código {contenedor.codigo}."
            ) from error
        except Exception as error:
            self.session.rollback()
            raise ErrorPersistenciaContenedor(
                "No se pudo actualizar el contenedor."
            ) from error
        return contenedor

    @staticmethod
    def _validar_texto(valor: str, campo: str, longitud_maxima: int) -> str:
        valor_limpio = valor.strip()
        if not valor_limpio:
            raise DatosContenedorInvalidos(f"{campo} es obligatorio.")
        if len(valor_limpio) > longitud_maxima:
            raise DatosContenedorInvalidos(
                f"{campo} no puede superar {longitud_maxima} caracteres."
            )
        return valor_limpio

