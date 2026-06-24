"""Elimina cube.commercial_density_h3 y cube.population_density_h3

Revision ID: 0006_drop_cube_h3
Revises: 0005_add_cvegeo9_index
Create Date: 2026-06-24

Por qué:
  Los cubos H3 fueron reemplazados por consultas directas a raw_data.ageb_geometries,
  raw_data.ageb_demographics y raw_data.manzana_vivienda. La extensión h3 ya no
  es necesaria. Los reportes y análisis ahora usan unidades estadísticas reales
  del INEGI (AGEBs y manzanas) en lugar de celdas hexagonales arbitrarias.
"""
from alembic import op

revision = "0006_drop_cube_h3"
down_revision = "0005_add_cvegeo9_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("commercial_density_h3", schema="cube")
    op.drop_table("population_density_h3", schema="cube")


def downgrade() -> None:
    # Las tablas no se recrean en downgrade — requeriría la extensión h3 que fue eliminada.
    pass
