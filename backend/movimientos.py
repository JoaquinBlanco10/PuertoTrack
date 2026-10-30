from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from auth import requerir_roles
from database import obtener_sesion
from models import Usuario
from movimiento_service import (
    ContenedorMovimientoNoEncontrado,
    ErrorRegistroMovimiento,
    MovimientoService,
)
from movimiento_strategies import MovimientoInvalido
from schemas import (
    ContextoMovimientoContenedor,
    MovimientoCrear,
    MovimientoRespuesta,
)


router = APIRouter(prefix="/movimientos", tags=["Movimientos"])

Sesion = Annotated[Session, Depends(obtener_sesion)]
UsuarioAutorizado = Annotated[
    Usuario, Depends(requerir_roles("operador", "supervisor"))
]


@router.post(
    "",
    response_model=MovimientoRespuesta,
    status_code=status.HTTP_201_CREATED,
)
def registrar_movimiento(
    datos: MovimientoCrear,
    session: Sesion,
    usuario: UsuarioAutorizado,
) -> MovimientoRespuesta:
    try:
        return MovimientoService(session).registrar(datos, usuario)
    except MovimientoInvalido as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except ContenedorMovimientoNoEncontrado as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ErrorRegistroMovimiento as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@router.get("", response_model=list[MovimientoRespuesta])
def listar_movimientos(
    session: Sesion,
    _: UsuarioAutorizado,
    offset: Annotated[int, Query(ge=0)] = 0,
    limite: Annotated[int, Query(ge=1, le=100)] = 100,
    orden: Literal["asc", "desc"] = "asc",
) -> list[MovimientoRespuesta]:
    return MovimientoService(session).listar(
        offset=offset, limite=limite, orden=orden
    )


@router.get(
    "/contenedor/{contenedor_id}/contexto",
    response_model=ContextoMovimientoContenedor,
)
def obtener_contexto_movimientos_contenedor(
    contenedor_id: Annotated[int, Path(gt=0)],
    session: Sesion,
    _: UsuarioAutorizado,
) -> ContextoMovimientoContenedor:
    try:
        return MovimientoService(session).obtener_contexto_contenedor(
            contenedor_id
        )
    except ContenedorMovimientoNoEncontrado as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get(
    "/contenedor/{contenedor_id}",
    response_model=list[MovimientoRespuesta],
)
def listar_movimientos_por_contenedor(
    contenedor_id: Annotated[int, Path(gt=0)],
    session: Sesion,
    _: UsuarioAutorizado,
    offset: Annotated[int, Query(ge=0)] = 0,
    limite: Annotated[int, Query(ge=1, le=100)] = 100,
    orden: Literal["asc", "desc"] = "asc",
) -> list[MovimientoRespuesta]:
    try:
        return MovimientoService(session).listar_por_contenedor(
            contenedor_id,
            offset=offset,
            limite=limite,
            orden=orden,
        )
    except ContenedorMovimientoNoEncontrado as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
