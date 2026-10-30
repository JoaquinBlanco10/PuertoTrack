"""crear tablas iniciales

Revision ID: 4083cc9c5727
Revises:
Create Date: 2026-10-18 15:06:32.813355

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4083cc9c5727"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "rol",
            sa.String(length=20),
            server_default="operador",
            nullable=False,
        ),
        sa.Column(
            "activo", sa.Boolean(), server_default="true", nullable=False
        ),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "rol IN ('operador', 'supervisor')",
            name="ck_usuarios_rol_valido",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "contenedores",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("codigo", sa.String(length=20), nullable=False),
        sa.Column("ubicacion_actual", sa.String(length=255), nullable=False),
        sa.Column("estado", sa.String(length=50), nullable=False),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "fecha_actualizacion",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("codigo"),
    )

    op.create_table(
        "movimientos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("contenedor_id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("ubicacion_origen", sa.String(length=255), nullable=False),
        sa.Column("ubicacion_destino", sa.String(length=255), nullable=False),
        sa.Column(
            "fecha_movimiento",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("observacion", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["contenedor_id"], ["contenedores.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"], ["usuarios.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_movimientos_contenedor_id"),
        "movimientos",
        ["contenedor_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_movimientos_usuario_id"),
        "movimientos",
        ["usuario_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_movimientos_usuario_id"), table_name="movimientos"
    )
    op.drop_index(
        op.f("ix_movimientos_contenedor_id"), table_name="movimientos"
    )
    op.drop_table("movimientos")
    op.drop_table("contenedores")
    op.drop_table("usuarios")
