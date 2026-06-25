"""Agrega score_nse y nse_nivel a ageb_demographics

Revision ID: 0007_nse_score
Revises: 0006_drop_cube_h3
Create Date: 2026-06-25

Por qué:
  El sistema original clasificaba NSE con un umbral absoluto de graproes
  (escolaridad promedio del AGEB), lo que sobreestimaba los niveles altos
  en ciudades educadas. El nuevo campo score_nse es un score 0-100 que
  combina educación, internet, automóvil, computadora y seguridad social
  con pesos inspirados en la metodología AMAI. nse_nivel asigna el nivel
  según umbrales calibrados con la distribución nacional AMAI 2020.
"""
from alembic import op
import sqlalchemy as sa

revision = "0007_nse_score"
down_revision = "0006_drop_cube_h3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ageb_demographics",
        sa.Column("score_nse", sa.Float(), nullable=True),
        schema="raw_data",
    )
    op.add_column(
        "ageb_demographics",
        sa.Column("nse_nivel", sa.String(10), nullable=True),
        schema="raw_data",
    )
    op.create_index(
        "ix_ageb_demographics_nse_nivel",
        "ageb_demographics",
        ["nse_nivel"],
        schema="raw_data",
    )


def downgrade() -> None:
    op.drop_index("ix_ageb_demographics_nse_nivel", table_name="ageb_demographics", schema="raw_data")
    op.drop_column("ageb_demographics", "nse_nivel", schema="raw_data")
    op.drop_column("ageb_demographics", "score_nse", schema="raw_data")
