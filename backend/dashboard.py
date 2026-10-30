from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from auth import requerir_roles
from dashboard_service import DashboardService
from database import obtener_sesion
from models import Usuario
from schemas import DashboardResumenRespuesta


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

Sesion = Annotated[Session, Depends(obtener_sesion)]
UsuarioAutorizado = Annotated[
    Usuario, Depends(requerir_roles("operador", "supervisor"))
]


@router.get("/resumen", response_model=DashboardResumenRespuesta)
def obtener_resumen_dashboard(
    session: Sesion,
    _: UsuarioAutorizado,
) -> DashboardResumenRespuesta:
    return DashboardService(session).obtener_resumen()
