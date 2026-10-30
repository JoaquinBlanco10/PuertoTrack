import hmac
import os
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Path, status
from sqlalchemy.orm import Session

from contenedor_service import (
    ContenedorNoEncontrado,
    ContenedorService,
    DatosContenedorInvalidos,
)
from database import obtener_sesion
from movimiento_service import MovimientoService
from schemas import HechosAccesoContenedorRespuesta


VARIABLE_CLAVE_ACCESOS = "ACCESS_INTERNAL_API_KEY"
CABECERA_CLAVE_ACCESOS = "X-PuertoTrack-Access-Key"
MIN_BYTES_CLAVE_ACCESOS = 32

router = APIRouter(prefix="/internal/access", tags=["Integración de accesos"])
Sesion = Annotated[Session, Depends(obtener_sesion)]


def autenticar_servicio_accesos(
    clave_recibida: Annotated[
        str | None,
        Header(alias=CABECERA_CLAVE_ACCESOS),
    ] = None,
) -> None:
    clave_configurada = os.getenv(VARIABLE_CLAVE_ACCESOS, "")
    if (
        clave_configurada != clave_configurada.strip()
        or len(clave_configurada.encode("utf-8")) < MIN_BYTES_CLAVE_ACCESOS
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La integración de accesos no está configurada.",
        )
    if clave_recibida is None or not hmac.compare_digest(
        clave_recibida,
        clave_configurada,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credencial interna inválida.",
        )


@router.get(
    "/contenedores/{codigo}",
    response_model=HechosAccesoContenedorRespuesta,
    dependencies=[Depends(autenticar_servicio_accesos)],
)
def consultar_hechos_acceso(
    codigo: Annotated[str, Path(min_length=1, max_length=20)],
    session: Sesion,
) -> HechosAccesoContenedorRespuesta:
    """Expone hechos de solo lectura, nunca una autorización comercial."""

    try:
        contenedor = ContenedorService(session).buscar_por_codigo(codigo)
    except (DatosContenedorInvalidos, ContenedorNoEncontrado) as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contenedor no encontrado.",
        ) from error
    contexto = MovimientoService(session).obtener_contexto_contenedor(
        contenedor.id
    )
    return HechosAccesoContenedorRespuesta(
        existe=True,
        id=contenedor.id,
        codigo=contenedor.codigo,
        estado=contenedor.estado,
        situacion=contenedor.situacion,
        coherencia_operacional=contenedor.coherencia_operacional,
        ubicacion_actual_id=contenedor.ubicacion_actual_id,
        tiene_movimientos=contexto.tiene_movimientos,
        tiene_salida_previa=contexto.tiene_salida_previa,
        etiqueta_entrada=contexto.etiqueta_entrada,
    )
