"""Agrega tablas raw_data para AGEBs, Censo 2020 e Inventario Nacional de Vivienda

Revision ID: 0002_ageb_tables
Revises: 0001_initial_schemas
Create Date: 2026-06-23 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry

revision = "0002_ageb_tables"
down_revision = "0001_initial_schemas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── AGEBs: geometrías del Marco Geoestadístico Nacional (MGN) ─────────────
    op.create_table(
        "ageb_geometries",
        sa.Column("cvegeo", sa.String(length=16), primary_key=True),
        sa.Column("clave_ent", sa.String(length=2), nullable=False),
        sa.Column("clave_mun", sa.String(length=3)),
        sa.Column("cve_loc", sa.String(length=4)),
        sa.Column("cve_ageb", sa.String(length=4)),
        sa.Column("nom_ent", sa.String(length=100)),
        sa.Column("nom_mun", sa.String(length=150)),
        sa.Column("nom_loc", sa.String(length=250)),
        sa.Column("ambito", sa.String(length=10)),   # Urbana | Rural
        sa.Column("geom", Geometry(geometry_type="MULTIPOLYGON", srid=4326)),
        sa.Column("loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        schema="raw_data",
    )
    op.create_index(
        "idx_ageb_geom", "ageb_geometries", ["geom"],
        unique=False, schema="raw_data", postgresql_using="gist",
    )
    op.create_index("idx_ageb_ent", "ageb_geometries", ["clave_ent"], schema="raw_data")

    # ── AGEBs: indicadores demográficos del Censo 2020 ────────────────────────
    op.create_table(
        "ageb_demographics",
        sa.Column("cvegeo", sa.String(length=16), primary_key=True),
        sa.Column("fuente", sa.String(length=50)),         # 'Censo 2020'
        # Población
        sa.Column("pobtot", sa.Integer()),
        sa.Column("pobmas", sa.Integer()),
        sa.Column("pobfem", sa.Integer()),
        # Grupos de edad (derivados de columnas crudas)
        sa.Column("p_0a14", sa.Integer()),
        sa.Column("p_15a64", sa.Integer()),
        sa.Column("p_65ymas", sa.Integer()),
        # Vivienda
        sa.Column("vivpar_hab", sa.Integer()),
        sa.Column("prom_ocup", sa.Float()),
        # Educación
        sa.Column("graproes", sa.Float()),
        # Salud / derechohabiencia
        sa.Column("pcon_disc", sa.Integer()),
        sa.Column("psinder", sa.Integer()),
        sa.Column("pder_ss", sa.Integer()),
        # Todos los indicadores crudos del CSV
        sa.Column("indicadores", sa.JSON()),
        sa.Column("loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        schema="raw_data",
    )
    op.create_index("idx_ageb_dem_ent", "ageb_demographics", ["cvegeo"], schema="raw_data")

    # ── Manzanas: Inventario Nacional de Vivienda ──────────────────────────────
    # cvegeo = ENTIDAD(2) + MUN(3) + LOC(4) + AGEB(4) + MZA(3) = 16 chars
    op.create_table(
        "manzana_vivienda",
        sa.Column("cvegeo", sa.String(length=16), primary_key=True),
        sa.Column("clave_ent", sa.String(length=2)),
        sa.Column("clave_mun", sa.String(length=3)),
        sa.Column("cve_loc", sa.String(length=4)),
        sa.Column("cve_ageb", sa.String(length=4)),
        sa.Column("cve_mza", sa.String(length=3)),
        sa.Column("cvegeo_ageb", sa.String(length=16)),    # FK lógica → ageb_geometries
        # Vivienda
        sa.Column("vivtot", sa.Integer()),
        sa.Column("vivpar", sa.Integer()),
        sa.Column("vivpar_hab", sa.Integer()),
        # Infraestructura / servicios (0-100 o conteo)
        sa.Column("con_agua", sa.Integer()),               # c/agua entubada
        sa.Column("con_dren", sa.Integer()),               # c/drenaje
        sa.Column("con_luz", sa.Integer()),                # c/electricidad
        # Geometría (shapefile del INV o manzanas del MGN)
        sa.Column("geom", Geometry(geometry_type="MULTIPOLYGON", srid=4326)),
        # Todos los indicadores crudos
        sa.Column("indicadores", sa.JSON()),
        sa.Column("fuente", sa.String(length=50)),         # 'INV2020' | 'Censo2020'
        sa.Column("loaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        schema="raw_data",
    )
    op.create_index(
        "idx_mza_geom", "manzana_vivienda", ["geom"],
        unique=False, schema="raw_data", postgresql_using="gist",
    )
    op.create_index("idx_mza_ageb", "manzana_vivienda", ["cvegeo_ageb"], schema="raw_data")


def downgrade() -> None:
    op.drop_index("idx_mza_ageb", table_name="manzana_vivienda", schema="raw_data")
    op.drop_index("idx_mza_geom", table_name="manzana_vivienda", schema="raw_data")
    op.drop_table("manzana_vivienda", schema="raw_data")

    op.drop_index("idx_ageb_dem_ent", table_name="ageb_demographics", schema="raw_data")
    op.drop_table("ageb_demographics", schema="raw_data")

    op.drop_index("idx_ageb_ent", table_name="ageb_geometries", schema="raw_data")
    op.drop_index("idx_ageb_geom", table_name="ageb_geometries", schema="raw_data")
    op.drop_table("ageb_geometries", schema="raw_data")
