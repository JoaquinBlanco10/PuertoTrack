from datetime import date, datetime
from enum import Enum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


RolUsuario = Literal["operador", "supervisor"]
SituacionContenedor = Literal[
    "dentro_puerto", "fuera_puerto", "presencia_sin_confirmar"
]
CoherenciaOperacional = Literal[
    "coherente", "sin_confirmar", "inconsistente"
]
MAX_LONGITUD_OBSERVACION = 1000


class EstadoContenedor(str, Enum):
    DISPONIBLE = "disponible"
    EN_PATIO = "en_patio"
    EN_TRANSITO = "en_transito"
    CARGADO = "cargado"
    DESCARGADO = "descargado"
    MANTENIMIENTO = "mantenimiento"


class TipoMovimiento(str, Enum):
    ENTRADA = "entrada"
    TRASLADO = "traslado"
    SALIDA = "salida"


class TipoUbicacion(str, Enum):
    INTERNA = "interna"
    EXTERNA = "externa"


class TokenRespuesta(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UsuarioRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    email: str
    rol: RolUsuario
    activo: bool
    fecha_creacion: datetime


class AccesoRespuesta(BaseModel):
    mensaje: str
    rol: RolUsuario


class ContenedorCrear(BaseModel):
    model_config = ConfigDict(extra="forbid")

    codigo: str = Field(description="Código único del contenedor")


class ContenedorActualizar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    codigo: str | None = None


class ContenedorRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    ubicacion_actual: str
    ubicacion_actual_id: int | None
    situacion: SituacionContenedor
    coherencia_operacional: CoherenciaOperacional
    tiene_evidencia_historica: bool
    regularizacion_permitida: bool
    estado: str
    fecha_creacion: datetime
    fecha_actualizacion: datetime


class ContenedorRFIDRespuesta(BaseModel):
    """Contrato mínimo expuesto exclusivamente a la integración RFID."""

    existe: Literal[True] = True
    id: int
    codigo: str


class HechosAccesoContenedorRespuesta(BaseModel):
    """Hechos mínimos para una política externa de habilitación operacional."""

    existe: Literal[True] = True
    id: int
    codigo: str
    estado: str
    situacion: SituacionContenedor
    coherencia_operacional: CoherenciaOperacional
    ubicacion_actual_id: int | None
    tiene_movimientos: bool
    tiene_salida_previa: bool
    etiqueta_entrada: Literal["primera_entrada", "reingreso", "entrada"]


class DecisionAccesoRespuesta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: Literal[1] = 1
    decision_id: UUID
    evento_id: UUID
    codigo_contenedor: str
    contenedor_id: int | None
    lector: str
    fecha_evento: datetime
    resultado: Literal[
        "habilitado", "denegado", "revision_manual", "no_determinado"
    ]
    motivo: str
    fecha_decision: datetime


class MovimientoCrear(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contenedor_id: int = Field(gt=0)
    tipo: TipoMovimiento
    ubicacion_destino_id: int = Field(gt=0)
    observacion: str | None = Field(
        default=None, max_length=MAX_LONGITUD_OBSERVACION
    )


class MovimientoRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    contenedor_id: int
    usuario_id: int
    tipo: TipoMovimiento | None
    ubicacion_origen: str
    ubicacion_destino: str
    ubicacion_origen_id: int | None
    ubicacion_destino_id: int | None
    fecha_movimiento: datetime
    observacion: str | None


class ContextoMovimientoContenedor(BaseModel):
    contenedor_id: int
    tiene_movimientos: bool
    tiene_salida_previa: bool
    etiqueta_entrada: Literal["primera_entrada", "reingreso", "entrada"]


class UbicacionCrear(BaseModel):
    model_config = ConfigDict(extra="forbid")

    codigo: str
    nombre: str
    tipo: TipoUbicacion


class UbicacionActualizar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str | None = None
    tipo: TipoUbicacion | None = None
    activo: bool | None = None


class UbicacionRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    codigo: str
    nombre: str
    tipo: TipoUbicacion
    activo: bool


class ContenedorRegularizarUbicacion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ubicacion_id: int = Field(gt=0)
    estado: Literal["en_patio", "en_transito"]
    justificacion: str = Field(min_length=10, max_length=500)


class AuditLogRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    usuario_id: int | None
    accion: str
    entidad: str
    entidad_id: int
    datos_anteriores: dict[str, Any] | None
    datos_nuevos: dict[str, Any] | None
    fecha: datetime


class TotalesContenedoresDashboard(BaseModel):
    dentro_puerto: int = Field(ge=0)
    fuera_puerto: int = Field(ge=0)
    presencia_sin_confirmar: int = Field(ge=0)
    inconsistentes: int = Field(ge=0)


class MovimientoDiarioDashboard(BaseModel):
    fecha: date
    entrada: int = Field(ge=0)
    traslado: int = Field(ge=0)
    salida: int = Field(ge=0)

    @property
    def total(self) -> int:
        return self.entrada + self.traslado + self.salida


class MovimientoRecienteDashboard(BaseModel):
    id: int
    contenedor_id: int
    contenedor_codigo: str
    usuario_id: int
    usuario_nombre: str
    tipo: TipoMovimiento | None
    ubicacion_origen: str
    ubicacion_destino: str
    fecha_movimiento: datetime


class PeriodoDashboard(BaseModel):
    desde: date
    hasta: date
    dias: Literal[7]


class DashboardResumenRespuesta(BaseModel):
    generado_en: datetime
    zona_horaria: Literal["UTC"]
    periodo: PeriodoDashboard
    contenedores: TotalesContenedoresDashboard
    movimientos_ultimos_7_dias: list[MovimientoDiarioDashboard]
    ultimos_movimientos: list[MovimientoRecienteDashboard]
