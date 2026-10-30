"""catalogo de ubicaciones y referencias historicas

Revision ID: d9a6c4f2e810
Revises: cbaff025a858
Create Date: 2026-10-18 19:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d9a6c4f2e810"
down_revision: Union[str, Sequence[str], None] = "cbaff025a858"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Agrega el catálogo sin transformar textos históricos."""
    op.create_table(
        "ubicaciones",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("codigo", sa.String(length=30), nullable=False),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("tipo", sa.String(length=20), nullable=False),
        sa.Column(
            "activo", sa.Boolean(), server_default="true", nullable=False
        ),
        sa.CheckConstraint(
            "tipo IN ('interna', 'externa')",
            name="ck_ubicaciones_tipo_valido",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("codigo"),
    )
    op.create_index(
        op.f("ix_ubicaciones_activo"),
        "ubicaciones",
        ["activo"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ubicaciones_tipo"),
        "ubicaciones",
        ["tipo"],
        unique=False,
    )

    op.add_column(
        "contenedores",
        sa.Column("ubicacion_actual_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_contenedores_ubicacion_actual_id_ubicaciones",
        "contenedores",
        "ubicaciones",
        ["ubicacion_actual_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        op.f("ix_contenedores_ubicacion_actual_id"),
        "contenedores",
        ["ubicacion_actual_id"],
        unique=False,
    )

    op.add_column(
        "movimientos",
        sa.Column("ubicacion_origen_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "movimientos",
        sa.Column("ubicacion_destino_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_movimientos_ubicacion_origen_id_ubicaciones",
        "movimientos",
        "ubicaciones",
        ["ubicacion_origen_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_movimientos_ubicacion_destino_id_ubicaciones",
        "movimientos",
        "ubicaciones",
        ["ubicacion_destino_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        op.f("ix_movimientos_ubicacion_origen_id"),
        "movimientos",
        ["ubicacion_origen_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_movimientos_ubicacion_destino_id"),
        "movimientos",
        ["ubicacion_destino_id"],
        unique=False,
    )


def downgrade() -> None:
    """Revierte únicamente las estructuras añadidas."""
    op.drop_index(
        op.f("ix_movimientos_ubicacion_destino_id"),
        table_name="movimientos",
    )
    op.drop_index(
        op.f("ix_movimientos_ubicacion_origen_id"),
        table_name="movimientos",
    )
    op.drop_constraint(
        "fk_movimientos_ubicacion_destino_id_ubicaciones",
        "movimientos",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_movimientos_ubicacion_origen_id_ubicaciones",
        "movimientos",
        type_="foreignkey",
    )
    op.drop_column("movimientos", "ubicacion_destino_id")
    op.drop_column("movimientos", "ubicacion_origen_id")

    op.drop_index(
        op.f("ix_contenedores_ubicacion_actual_id"),
        table_name="contenedores",
    )
    op.drop_constraint(
        "fk_contenedores_ubicacion_actual_id_ubicaciones",
        "contenedores",
        type_="foreignkey",
    )
    op.drop_column("contenedores", "ubicacion_actual_id")

    op.drop_index(op.f("ix_ubicaciones_tipo"), table_name="ubicaciones")
    op.drop_index(op.f("ix_ubicaciones_activo"), table_name="ubicaciones")
    op.drop_table("ubicaciones")
