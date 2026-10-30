from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    JSON,
    String,
    Text,
    and_,
    case,
    func,
    or_,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = (
        CheckConstraint(
            "rol IN ('operador', 'supervisor')",
            name="ck_usuarios_rol_valido",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    rol: Mapped[str] = mapped_column(
        String(20), nullable=False, default="operador", server_default="operador"
    )
    activo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    movimientos: Mapped[list["Movimiento"]] = relationship(
        back_populates="usuario"
    )


class Ubicacion(Base):
    __tablename__ = "ubicaciones"
    __table_args__ = (
        CheckConstraint(
            "tipo IN ('interna', 'externa')",
            name="ck_ubicaciones_tipo_valido",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(
        String(30), nullable=False, unique=True
    )
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    activo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true", index=True
    )

    contenedores_actuales: Mapped[list["Contenedor"]] = relationship(
        back_populates="ubicacion_actual_catalogo",
        foreign_keys="Contenedor.ubicacion_actual_id",
    )
    movimientos_origen: Mapped[list["Movimiento"]] = relationship(
        back_populates="ubicacion_origen_catalogo",
        foreign_keys="Movimiento.ubicacion_origen_id",
    )
    movimientos_destino: Mapped[list["Movimiento"]] = relationship(
        back_populates="ubicacion_destino_catalogo",
        foreign_keys="Movimiento.ubicacion_destino_id",
    )


class Contenedor(Base):
    __tablename__ = "contenedores"

    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    # Conserva el texto persistido por compatibilidad histórica. Cuando existe
    # una FK, el nombre vigente del catálogo es la fuente canónica expuesta por
    # ``ubicacion_actual`` (ver la propiedad más abajo).
    _ubicacion_actual_texto: Mapped[str] = mapped_column(
        "ubicacion_actual", String(255), nullable=False
    )
    ubicacion_actual_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("ubicaciones.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    estado: Mapped[str] = mapped_column(String(50), nullable=False)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    fecha_actualizacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    movimientos: Mapped[list["Movimiento"]] = relationship(
        back_populates="contenedor"
    )
    ubicacion_actual_catalogo: Mapped[Optional["Ubicacion"]] = relationship(
        back_populates="contenedores_actuales",
        foreign_keys=[ubicacion_actual_id],
        lazy="selectin",
    )

    @property
    def ubicacion_actual(self) -> str:
        if (
            self.ubicacion_actual_id is not None
            and self.ubicacion_actual_catalogo is not None
        ):
            return self.ubicacion_actual_catalogo.nombre
        return self._ubicacion_actual_texto

    @ubicacion_actual.setter
    def ubicacion_actual(self, valor: str) -> None:
        self._ubicacion_actual_texto = valor

    @hybrid_property
    def situacion(self) -> str:
        if self.ubicacion_actual_id is None:
            return "presencia_sin_confirmar"
        if (
            self.ubicacion_actual_catalogo is not None
            and self.ubicacion_actual_catalogo.tipo == "interna"
        ):
            return "dentro_puerto"
        return "fuera_puerto"

    @situacion.inplace.expression
    @classmethod
    def _situacion_expression(cls):
        return case(
            (
                cls.ubicacion_actual_id.is_(None),
                "presencia_sin_confirmar",
            ),
            (Ubicacion.tipo == "interna", "dentro_puerto"),
            else_="fuera_puerto",
        )

    @hybrid_property
    def coherencia_operacional(self) -> str:
        if self.ubicacion_actual_id is None:
            return "sin_confirmar"
        if self.ubicacion_actual_catalogo is None:
            return "inconsistente"
        if (
            self.ubicacion_actual_catalogo.tipo == "interna"
            and self.estado == "en_patio"
        ) or (
            self.ubicacion_actual_catalogo.tipo == "externa"
            and self.estado == "en_transito"
        ):
            return "coherente"
        return "inconsistente"

    @coherencia_operacional.inplace.expression
    @classmethod
    def _coherencia_operacional_expression(cls):
        return case(
            (cls.ubicacion_actual_id.is_(None), "sin_confirmar"),
            (
                or_(
                    and_(
                        Ubicacion.tipo == "interna",
                        cls.estado == "en_patio",
                    ),
                    and_(
                        Ubicacion.tipo == "externa",
                        cls.estado == "en_transito",
                    ),
                ),
                "coherente",
            ),
            else_="inconsistente",
        )

    @property
    def tiene_evidencia_historica(self) -> bool:
        return bool(getattr(self, "_tiene_evidencia_historica", False))

    @property
    def regularizacion_permitida(self) -> bool:
        return self.tiene_evidencia_historica and (
            self.ubicacion_actual_id is None
            or self.coherencia_operacional == "inconsistente"
        )


class Movimiento(Base):
    __tablename__ = "movimientos"
    __table_args__ = (
        CheckConstraint(
            "tipo IS NULL OR tipo IN ('entrada', 'traslado', 'salida')",
            name="ck_movimientos_tipo_valido",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    contenedor_id: Mapped[int] = mapped_column(
        ForeignKey("contenedores.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    tipo: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )
    ubicacion_origen: Mapped[str] = mapped_column(String(255), nullable=False)
    ubicacion_destino: Mapped[str] = mapped_column(String(255), nullable=False)
    ubicacion_origen_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("ubicaciones.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    ubicacion_destino_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("ubicaciones.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    fecha_movimiento: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    observacion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    contenedor: Mapped["Contenedor"] = relationship(back_populates="movimientos")
    usuario: Mapped["Usuario"] = relationship(back_populates="movimientos")
    ubicacion_origen_catalogo: Mapped[Optional["Ubicacion"]] = relationship(
        back_populates="movimientos_origen",
        foreign_keys=[ubicacion_origen_id],
    )
    ubicacion_destino_catalogo: Mapped[Optional["Ubicacion"]] = relationship(
        back_populates="movimientos_destino",
        foreign_keys=[ubicacion_destino_id],
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    accion: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entidad: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entidad_id: Mapped[int] = mapped_column(nullable=False, index=True)
    datos_anteriores: Mapped[Optional[dict[str, object]]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=True
    )
    datos_nuevos: Mapped[Optional[dict[str, object]]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=True
    )
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
