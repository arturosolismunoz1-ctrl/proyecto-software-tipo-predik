"""Agrega cube.population_density_h3 para densidad poblacional por celda H3

Revision ID: 0003_cube_population
Revises: 0002_ageb_tables
Create Date: 2026-06-23 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry

revision = "0003_cube_population"
down_revision = "0002_ageb_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "population_density_h3",
        sa.Column("h3_index", sa.String(length=20), primary_key=True),
        sa.Column("h3_resolution", sa.SmallInteger()),
        sa.Column("entidad", sa.String(length=100)),
        sa.Column("municipio", sa.String(length=100)),
        sa.Column("pobtot", sa.Integer()),
        sa.Column("pobmas", sa.Integer()),
        sa.Column("pobfem", sa.Integer()),
        sa.Column("p_0a14", sa.Integer()),
        sa.Column("p_15a64", sa.Integer()),
        sa.Column("p_65ymas", sa.Integer()),
        sa.Column("vivpar_hab", sa.Integer()),
        sa.Column("densidad_hab_km2", sa.Float()),
        sa.Column("geom_centroid", Geometry(geometry_type="POINT", srid=4326)),
        sa.Column("geom_hexagon", Geometry(geometry_type="POLYGON", srid=4326)),
        sa.Column("last_refreshed", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        schema="cube",
    )
    op.create_index(
        "idx_pop_h3_geom", "population_density_h3", ["geom_hexagon"],
        unique=False, schema="cube", postgresql_using="gist",
    )
    op.create_index(
        "idx_pop_h3_resolution", "population_density_h3", ["h3_resolution"],
        schema="cube",
    )


def downgrade() -> None:
    op.drop_index("idx_pop_h3_resolution", table_name="population_density_h3", schema="cube")
    op.drop_index("idx_pop_h3_geom", table_name="population_density_h3", schema="cube")
    op.drop_table("population_density_h3", schema="cube")
