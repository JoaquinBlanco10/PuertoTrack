from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from auth import requerir_roles
from contenedor_service import (
    CodigoContenedorDuplicado,
    ContenedorNoEncontrado,
    ContenedorYaRegularizado,
    ContenedorService,
    DatosContenedorInvalidos,
    ErrorPersistenciaContenedor,
    RegularizacionSinEvidencia,
    UbicacionRegularizacionNoEncontrada,
)
from database import obtener_sesion
from models import Usuario
from schemas import (
    ContenedorActualizar,
    ContenedorCrear,
    ContenedorRegularizarUbicacion,
    ContenedorRespuesta,
)


router = APIRouter(prefix="/contenedores", tags=["Contenedores"])

Sesion = Annotated[Session, Depends(obtener_sesion)]
PuedeConsultar = Annotated[
    Usuario, Depends(requerir_roles("operador", "supervisor"))
]
EsSupervisor = Annotated[
    Usuario, Depends(requerir_roles("supervisor"))
]


def _traducir_error(error: Exception) -> HTTPException:
    if isinstance(error, DatosContenedorInvalidos):
        return HTTPException(status_code=400, detail=str(error))
    if isinstance(error, ContenedorNoEncontrado):
        return HTTPException(status_code=404, detail=str(error))
    if isinstance(error, CodigoContenedorDuplicado):
        return HTTPException(status_code=409, detail=str(error))
    if isinstance(error, ContenedorYaRegularizado):
        return HTTPException(status_code=409, detail=str(error))
    if isinstance(error, RegularizacionSinEvidencia):
        return HTTPException(status_code=409, detail=str(error))
    if isinstance(error, UbicacionRegularizacionNoEncontrada):
        return HTTPException(status_code=404, detail=str(error))
    if isinstance(error, ErrorPersistenciaContenedor):
        return HTTPException(status_code=500, detail=str(error))
    return HTTPException(status_code=500, detail="Error interno")


@router.post(
    "",
    response_model=ContenedorRespuesta,
    status_code=status.HTTP_201_CREATED,
)
def crear_contenedor(
    datos: ContenedorCrear,
    session: Sesion,
    usuario: EsSupervisor,
) -> ContenedorRespuesta:
    try:
        return ContenedorService(session).crear(datos, usuario)
    except (
        DatosContenedorInvalidos,
        CodigoContenedorDuplicado,
        ErrorPersistenciaContenedor,
    ) as error:
        raise _traducir_error(error) from error


@router.get("", response_model=list[ContenedorRespuesta])
def listar_contenedores(
    session: Sesion,
    _: PuedeConsultar,
    offset: Annotated[int, Query(ge=0)] = 0,
    limite: Annotated[int, Query(ge=1, le=100)] = 100,
    situacion: Annotated[
        str | None,
        Query(pattern="^(dentro_puerto|fuera_puerto|presencia_sin_confirmar)$"),
    ] = None,
    coherencia: Annotated[
        str | None,
        Query(pattern="^(coherente|sin_confirmar|inconsistente)$"),
    ] = None,
    codigo: Annotated[
        str | None,
        Query(min_length=1, max_length=20),
    ] = None,
) -> list[ContenedorRespuesta]:
    try:
        return ContenedorService(session).listar(
            offset=offset,
            limite=limite,
            situacion=situacion,
            coherencia=coherencia,
            codigo=codigo,
        )
    except DatosContenedorInvalidos as error:
        raise _traducir_error(error) from error


@router.get("/codigo/{codigo}", response_model=ContenedorRespuesta)
def buscar_contenedor_por_codigo(
    codigo: str,
    session: Sesion,
    _: PuedeConsultar,
) -> ContenedorRespuesta:
    try:
        return ContenedorService(session).buscar_por_codigo(codigo)
    except (DatosContenedorInvalidos, ContenedorNoEncontrado) as error:
        raise _traducir_error(error) from error


@router.get("/{contenedor_id}", response_model=ContenedorRespuesta)
def buscar_contenedor_por_id(
    contenedor_id: Annotated[int, Path(gt=0)],
    session: Sesion,
    _: PuedeConsultar,
) -> ContenedorRespuesta:
    try:
        return ContenedorService(session).buscar_por_id(contenedor_id)
    except ContenedorNoEncontrado as error:
        raise _traducir_error(error) from error


@router.patch("/{contenedor_id}", response_model=ContenedorRespuesta)
def actualizar_contenedor(
    contenedor_id: Annotated[int, Path(gt=0)],
    datos: ContenedorActualizar,
    session: Sesion,
    usuario: EsSupervisor,
) -> ContenedorRespuesta:
    try:
        return ContenedorService(session).actualizar(
            contenedor_id, datos, usuario
        )
    except (
        DatosContenedorInvalidos,
        ContenedorNoEncontrado,
        CodigoContenedorDuplicado,
        ErrorPersistenciaContenedor,
    ) as error:
        raise _traducir_error(error) from error


@router.post(
    "/{contenedor_id}/regularizar-ubicacion",
    response_model=ContenedorRespuesta,
)
def regularizar_ubicacion_contenedor(
    contenedor_id: Annotated[int, Path(gt=0)],
    datos: ContenedorRegularizarUbicacion,
    session: Sesion,
    usuario: EsSupervisor,
) -> ContenedorRespuesta:
    try:
        return ContenedorService(session).regularizar_ubicacion(
            contenedor_id,
            datos.ubicacion_id,
            datos.estado,
            datos.justificacion,
            usuario,
        )
    except (
        ContenedorNoEncontrado,
        ContenedorYaRegularizado,
        RegularizacionSinEvidencia,
        DatosContenedorInvalidos,
        UbicacionRegularizacionNoEncontrada,
        ErrorPersistenciaContenedor,
    ) as error:
        raise _traducir_error(error) from error
