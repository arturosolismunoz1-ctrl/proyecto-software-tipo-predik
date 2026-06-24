"""Agrega raw_data.bie_indicadores para series de tiempo BIE (INEGI)

Revision ID: 0004_bie_indicadores
Revises: 0003_cube_population
Create Date: 2026-06-23 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_bie_indicadores"
down_revision = "0003_cube_population"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bie_indicadores",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("indicador_id", sa.String(20), nullable=False),
        sa.Column("nombre", sa.String(200)),
        sa.Column("descripcion", sa.Text()),
        sa.Column("unidad", sa.String(100)),
        sa.Column("frecuencia", sa.String(20)),
        sa.Column("area_clave", sa.String(10), nullable=False),
        sa.Column("estado_clave", sa.String(2)),
        sa.Column("periodo", sa.String(10), nullable=False),
        sa.Column("periodo_fecha", sa.Date()),
        sa.Column("valor", sa.Float()),
        sa.Column("fuente", sa.String(50), server_default="BIE_INEGI"),
        sa.Column("loaded_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("indicador_id", "area_clave", "periodo", name="uq_bie_ind_area_periodo"),
        schema="raw_data",
    )
    op.create_index(
        "idx_bie_estado_clave",
        "bie_indicadores",
        ["estado_clave"],
        schema="raw_data",
    )
    op.create_index(
        "idx_bie_indicador_id",
        "bie_indicadores",
        ["indicador_id"],
        schema="raw_data",
    )
    op.create_index(
        "idx_bie_periodo_fecha",
        "bie_indicadores",
        ["periodo_fecha"],
        schema="raw_data",
    )


def downgrade() -> None:
    op.drop_table("bie_indicadores", schema="raw_data")
