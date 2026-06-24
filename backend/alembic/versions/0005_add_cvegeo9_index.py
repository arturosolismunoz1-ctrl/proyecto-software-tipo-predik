"""Agrega columna cvegeo_9 a ageb_geometries y la puebla desde clave_ent+clave_mun+cve_ageb

Revision ID: 0005_add_cvegeo9_index
Revises: 0004_bie_indicadores
Create Date: 2026-06-23 00:00:00.000000

Por qué:
  El shapefile MGN 2025 almacena CVEGEO en dos formatos:
    - 9 chars  (ent+mun+ageb)        — 17k registros
    - 13 chars (ent+mun+loc+ageb)    — 65k registros
  El Censo 2020 usa siempre 9 chars (ent+mun+ageb).
  La columna cvegeo_9 normaliza ambos formatos al de 9 chars para que el JOIN funcione.
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_add_cvegeo9_index"
down_revision = "0004_bie_indicadores"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ageb_geometries",
        sa.Column("cvegeo_9", sa.String(length=9), nullable=True),
        schema="raw_data",
    )

    op.execute("""
        UPDATE raw_data.ageb_geometries
        SET cvegeo_9 =
            LPAD(clave_ent, 2, '0')
            || LPAD(clave_mun, 3, '0')
            || LPAD(cve_ageb,  4, '0')
        WHERE clave_ent IS NOT NULL
          AND clave_mun IS NOT NULL
          AND cve_ageb  IS NOT NULL
          AND cve_ageb  != ''
    """)

    op.create_index(
        "idx_ageb_cvegeo9",
        "ageb_geometries",
        ["cvegeo_9"],
        schema="raw_data",
    )


def downgrade() -> None:
    op.drop_index("idx_ageb_cvegeo9", table_name="ageb_geometries", schema="raw_data")
    op.drop_column("ageb_geometries", "cvegeo_9", schema="raw_data")
