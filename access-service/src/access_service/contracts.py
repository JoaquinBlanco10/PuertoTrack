from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ResultadoIdentificacion(str, Enum):
    VALIDO = "valido"
    DESCONOCIDO = "codigo_desconocido"


class ResultadoAcceso(str, Enum):
    HABILITADO = "habilitado"
    DENEGADO = "denegado"
    REVISION_MANUAL = "revision_manual"
    NO_DETERMINADO = "no_determinado"


class IdentificacionRFID(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    version: Literal[1]
    evento_id: UUID
    codigo_contenedor: str = Field(min_length=1, max_length=20)
    contenedor_id: int | None
    lector: str = Field(min_length=1, max_length=64)
    fecha_utc: datetime
    identificado_en: datetime
    resultado_identificacion: ResultadoIdentificacion

    @field_validator("codigo_contenedor")
    @classmethod
    def normalizar_codigo(cls, valor: str) -> str:
        return valor.upper()

    @field_validator("fecha_utc", "identificado_en")
    @classmethod
    def exigir_utc(cls, valor: datetime) -> datetime:
        if valor.tzinfo is None or valor.utcoffset() != timedelta(0):
            raise ValueError("Las fechas deben expresarse en UTC.")
        return valor.astimezone(timezone.utc)


class HechosOperacionales(BaseModel):
    model_config = ConfigDict(extra="forbid")

    existe: Literal[True]
    id: int = Field(gt=0)
    codigo: str
    estado: str
    situacion: Literal[
        "dentro_puerto", "fuera_puerto", "presencia_sin_confirmar"
    ]
    coherencia_operacional: Literal[
        "coherente", "sin_confirmar", "inconsistente"
    ]
    ubicacion_actual_id: int | None
    tiene_movimientos: bool
    tiene_salida_previa: bool
    etiqueta_entrada: Literal["primera_entrada", "reingreso", "entrada"]


class DecisionAcceso(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: Literal[1] = 1
    decision_id: UUID
    evento_id: UUID
    codigo_contenedor: str
    contenedor_id: int | None
    lector: str
    fecha_evento: datetime
    resultado: ResultadoAcceso
    motivo: str
    fecha_decision: datetime


class ResumenSalud(BaseModel):
    servicio: str = "puertotrack-access-service"
    mqtt_conectado: bool
    decisiones_conservadas: int
    duplicados_ignorados: int
    mensajes_invalidos: int
    por_resultado: dict[ResultadoAcceso, int]
