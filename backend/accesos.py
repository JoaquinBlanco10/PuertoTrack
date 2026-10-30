from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from access_client import (
    AccessServiceClient,
    ConfiguracionAccesosInvalida,
    ServicioAccesosNoDisponible,
)
from auth import requerir_roles
from models import Usuario
from schemas import DecisionAccesoRespuesta


router = APIRouter(prefix="/accesos", tags=["Accesos portuarios"])
EsSupervisor = Annotated[Usuario, Depends(requerir_roles("supervisor"))]
ResultadoAcceso = Literal[
    "habilitado", "denegado", "revision_manual", "no_determinado"
]


@router.get("", response_model=list[DecisionAccesoRespuesta])
def listar_decisiones_acceso(
    _: EsSupervisor,
    limite: Annotated[int, Query(ge=1, le=100)] = 50,
    resultado: ResultadoAcceso | None = None,
) -> list[DecisionAccesoRespuesta]:
    try:
        return AccessServiceClient().listar_decisiones(
            limite=limite,
            resultado=resultado,
        )
    except ConfiguracionAccesosInvalida as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error
    except ServicioAccesosNoDisponible as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error
