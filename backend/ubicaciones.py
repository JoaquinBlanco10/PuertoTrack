from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from auth import requerir_roles
from database import obtener_sesion
from models import Usuario
from schemas import (
    TipoUbicacion,
    UbicacionActualizar,
    UbicacionCrear,
    UbicacionRespuesta,
)
from ubicacion_service import (
    CodigoUbicacionDuplicado,
    DatosUbicacionInvalidos,
    ErrorPersistenciaUbicacion,
    TipoUbicacionBloqueado,
    UbicacionNoEncontrada,
    UbicacionService,
)


router = APIRouter(prefix="/ubicaciones", tags=["Ubicaciones"])
Sesion = Annotated[Session, Depends(obtener_sesion)]
PuedeConsultar = Annotated[
    Usuario, Depends(requerir_roles("operador", "supervisor"))
]
EsSupervisor = Annotated[Usuario, Depends(requerir_roles("supervisor"))]


def _traducir_error(error: Exception) -> HTTPException:
    if isinstance(error, DatosUbicacionInvalidos):
        return HTTPException(status_code=400, detail=str(error))
    if isinstance(error, UbicacionNoEncontrada):
        return HTTPException(status_code=404, detail=str(error))
    if isinstance(
        error, (CodigoUbicacionDuplicado, TipoUbicacionBloqueado)
    ):
        return HTTPException(status_code=409, detail=str(error))
    if isinstance(error, ErrorPersistenciaUbicacion):
        return HTTPException(status_code=500, detail=str(error))
    return HTTPException(status_code=500, detail="Error interno")


@router.get("", response_model=list[UbicacionRespuesta])
def listar_ubicaciones(
    session: Sesion,
    usuario: PuedeConsultar,
    tipo: TipoUbicacion | None = None,
    incluir_inactivas: bool = False,
    offset: Annotated[int, Query(ge=0)] = 0,
    limite: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[UbicacionRespuesta]:
    if incluir_inactivas and usuario.rol != "supervisor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un supervisor puede consultar ubicaciones inactivas",
        )
    return UbicacionService(session).listar(
        incluir_inactivas=incluir_inactivas,
        tipo=tipo,
        offset=offset,
        limite=limite,
    )


@router.get("/{ubicacion_id}", response_model=UbicacionRespuesta)
def buscar_ubicacion(
    ubicacion_id: Annotated[int, Path(gt=0)],
    session: Sesion,
    usuario: PuedeConsultar,
) -> UbicacionRespuesta:
    try:
        return UbicacionService(session).buscar_por_id(
            ubicacion_id,
            permitir_inactiva=usuario.rol == "supervisor",
        )
    except UbicacionNoEncontrada as error:
        raise _traducir_error(error) from error


@router.post(
    "",
    response_model=UbicacionRespuesta,
    status_code=status.HTTP_201_CREATED,
)
def crear_ubicacion(
    datos: UbicacionCrear,
    session: Sesion,
    usuario: EsSupervisor,
) -> UbicacionRespuesta:
    try:
        return UbicacionService(session).crear(datos, usuario)
    except (
        DatosUbicacionInvalidos,
        CodigoUbicacionDuplicado,
        ErrorPersistenciaUbicacion,
    ) as error:
        raise _traducir_error(error) from error


@router.patch("/{ubicacion_id}", response_model=UbicacionRespuesta)
def actualizar_ubicacion(
    ubicacion_id: Annotated[int, Path(gt=0)],
    datos: UbicacionActualizar,
    session: Sesion,
    usuario: EsSupervisor,
) -> UbicacionRespuesta:
    try:
        return UbicacionService(session).actualizar(
            ubicacion_id, datos, usuario
        )
    except (
        DatosUbicacionInvalidos,
        UbicacionNoEncontrada,
        TipoUbicacionBloqueado,
        ErrorPersistenciaUbicacion,
    ) as error:
        raise _traducir_error(error) from error
