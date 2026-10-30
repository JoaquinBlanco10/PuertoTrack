from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EstadoProcesamiento(str, Enum):
    VALIDO = "valido"
    DESCONOCIDO = "codigo_desconocido"
    DUPLICADO = "duplicado"
    INVALIDO = "mensaje_invalido"
    ERROR = "error_integracion"


class DeteccionRFID(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    evento_id: UUID
    codigo_contenedor: str = Field(min_length=1, max_length=20)
    lector: str = Field(min_length=1, max_length=64)
    fecha_utc: datetime

    @field_validator("codigo_contenedor")
    @classmethod
    def normalizar_codigo(cls, valor: str) -> str:
        return valor.upper()

    @field_validator("fecha_utc")
    @classmethod
    def exigir_utc(cls, valor: datetime) -> datetime:
        if valor.tzinfo is None or valor.utcoffset() is None:
            raise ValueError("fecha_utc debe incluir zona horaria UTC")
        if valor.utcoffset() != timedelta(0):
            raise ValueError("fecha_utc debe expresarse en UTC")
        return valor.astimezone(timezone.utc)


class DeteccionAceptada(BaseModel):
    evento_id: UUID
    estado: Literal["aceptado"] = "aceptado"


class ContenedorIdentificado(BaseModel):
    model_config = ConfigDict(extra="forbid")

    existe: Literal[True]
    id: int = Field(gt=0)
    codigo: str


class ProcesamientoRFID(BaseModel):
    procesamiento_id: UUID
    evento_id: UUID | None
    codigo_contenedor: str | None
    lector: str | None
    fecha_evento: datetime | None
    recibido_en: datetime
    estado: EstadoProcesamiento
    detalle: str
    contenedor_id: int | None = None


class ResumenEstado(BaseModel):
    servicio: str = "puertotrack-rfid"
    mqtt_conectado: bool
    procesamientos_conservados: int
    por_estado: dict[EstadoProcesamiento, int]


class ResultadoIdentificacion(str, Enum):
    VALIDO = "valido"
    DESCONOCIDO = "codigo_desconocido"


class IdentificacionRFID(BaseModel):
    """Evento derivado y versionado consumido por el servicio de accesos."""

    model_config = ConfigDict(extra="forbid")

    version: Literal[1] = 1
    evento_id: UUID
    codigo_contenedor: str
    contenedor_id: int | None
    lector: str
    fecha_utc: datetime
    identificado_en: datetime
    resultado_identificacion: ResultadoIdentificacion


def crear_identificacion(
    procesamiento: ProcesamientoRFID,
) -> IdentificacionRFID | None:
    """Solo produce eventos pertinentes; inválidos, errores y duplicados paran."""

    if procesamiento.estado not in {
        EstadoProcesamiento.VALIDO,
        EstadoProcesamiento.DESCONOCIDO,
    }:
        return None
    if (
        procesamiento.evento_id is None
        or procesamiento.codigo_contenedor is None
        or procesamiento.lector is None
        or procesamiento.fecha_evento is None
    ):
        return None
    return IdentificacionRFID(
        evento_id=procesamiento.evento_id,
        codigo_contenedor=procesamiento.codigo_contenedor,
        contenedor_id=procesamiento.contenedor_id,
        lector=procesamiento.lector,
        fecha_utc=procesamiento.fecha_evento,
        identificado_en=procesamiento.recibido_en,
        resultado_identificacion=ResultadoIdentificacion(
            procesamiento.estado.value
        ),
    )
