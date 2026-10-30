from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from auditoria_service import AuditoriaService
from auth import requerir_roles
from database import obtener_sesion
from models import Usuario
from schemas import AuditLogRespuesta


router = APIRouter(prefix="/auditoria", tags=["Auditoría"])

Sesion = Annotated[Session, Depends(obtener_sesion)]
EsSupervisor = Annotated[
    Usuario, Depends(requerir_roles("supervisor"))
]


@router.get("", response_model=list[AuditLogRespuesta])
def listar_auditoria(
    session: Sesion,
    _: EsSupervisor,
    usuario_id: Annotated[int | None, Query(gt=0)] = None,
    entidad: Annotated[str | None, Query(min_length=1, max_length=50)] = None,
    entidad_id: Annotated[int | None, Query(gt=0)] = None,
    accion: Annotated[str | None, Query(min_length=1, max_length=50)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limite: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[AuditLogRespuesta]:
    return AuditoriaService(session).listar(
        usuario_id=usuario_id,
        entidad=entidad,
        entidad_id=entidad_id,
        accion=accion,
        offset=offset,
        limite=limite,
    )
