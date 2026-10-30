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
from schemas import ContenedorRFIDRespuesta


VARIABLE_CLAVE_RFID = "RFID_INTERNAL_API_KEY"
CABECERA_CLAVE_RFID = "X-PuertoTrack-Internal-Key"
MIN_BYTES_CLAVE_RFID = 32

router = APIRouter(prefix="/internal/rfid", tags=["Integración RFID"])
Sesion = Annotated[Session, Depends(obtener_sesion)]


def autenticar_servicio_rfid(
    clave_recibida: Annotated[
        str | None,
        Header(alias=CABECERA_CLAVE_RFID),
    ] = None,
) -> None:
    clave_configurada = os.getenv(VARIABLE_CLAVE_RFID, "")
    if (
        clave_configurada != clave_configurada.strip()
        or len(clave_configurada.encode("utf-8")) < MIN_BYTES_CLAVE_RFID
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La integración RFID no está configurada.",
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
    response_model=ContenedorRFIDRespuesta,
    dependencies=[Depends(autenticar_servicio_rfid)],
)
def identificar_contenedor_rfid(
    codigo: Annotated[str, Path(min_length=1, max_length=20)],
    session: Sesion,
) -> ContenedorRFIDRespuesta:
    """Confirma identidad sin exponer ni modificar datos operacionales."""

    try:
        contenedor = ContenedorService(session).buscar_por_codigo(codigo)
    except (DatosContenedorInvalidos, ContenedorNoEncontrado) as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contenedor no encontrado.",
        ) from error
    return ContenedorRFIDRespuesta(
        existe=True,
        id=contenedor.id,
        codigo=contenedor.codigo,
    )
