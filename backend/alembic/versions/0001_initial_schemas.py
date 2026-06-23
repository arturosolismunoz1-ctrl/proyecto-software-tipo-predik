"""Initial schemas

Revision ID: 0001_initial_schemas
Revises: None
Create Date: 2026-06-20 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry

revision = "0001_initial_schemas"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis CASCADE")
    op.execute("CREATE EXTENSION IF NOT EXISTS h3 CASCADE")
    op.execute("CREATE EXTENSION IF NOT EXISTS h3_postgis CASCADE")

    op.execute("CREATE SCHEMA IF NOT EXISTS core")
    op.execute("CREATE SCHEMA IF NOT EXISTS raw_data")
    op.execute("CREATE SCHEMA IF NOT EXISTS cube")
    op.execute("CREATE SCHEMA IF NOT EXISTS analytics")

    op.create_table(
        "organizations",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("plan", sa.String(length=50), nullable=False, server_default="starter"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        schema="core",
    )

    op.create_table(
        "users",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("core.organizations.id"), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False, server_default="analyst"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        schema="core",
    )

    op.create_table(
        "api_credentials",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("core.organizations.id"), nullable=False),
        sa.Column("connector_name", sa.String(length=100), nullable=False),
        sa.Column("encrypted_value", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        schema="core",
    )

    op.create_table(
        "query_log",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("core.organizations.id"), nullable=False),
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("core.users.id"), nullable=True),
        sa.Column("endpoint", sa.String(length=255)),
        sa.Column("request_summary", sa.JSON()),
        sa.Column("duration_ms", sa.Integer()),
        sa.Column("status_code", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        schema="core",
    )

    op.create_table(
        "denue_establishments",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("clee", sa.String(length=50), nullable=True, unique=True),
        sa.Column("nombre", sa.String(length=255)),
        sa.Column("razon_social", sa.String(length=255)),
        sa.Column("clase_actividad", sa.String(length=255)),
        sa.Column("codigo_scian", sa.String(length=10)),
        sa.Column("estrato_personal", sa.String(length=50)),
        sa.Column("entidad", sa.String(length=100)),
        sa.Column("municipio", sa.String(length=100)),
        sa.Column("localidad", sa.String(length=100)),
        sa.Column("colonia", sa.String(length=150)),
        sa.Column("cp", sa.String(length=10)),
        sa.Column("geom", Geometry(geometry_type="POINT", srid=4326), nullable=True),
        sa.Column("fuente_actualizacion", sa.Date()),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("raw_response", sa.JSON()),
        schema="raw_data",
    )
    op.create_index("idx_denue_geom", "denue_establishments", ["geom"], unique=False, schema="raw_data", postgresql_using="gist")
    op.create_index("idx_denue_scian", "denue_establishments", ["codigo_scian"], unique=False, schema="raw_data")

    op.create_table(
        "commercial_density_h3",
        sa.Column("h3_index", sa.String(length=20), primary_key=True),
        sa.Column("h3_resolution", sa.SmallInteger()),
        sa.Column("entidad", sa.String(length=100)),
        sa.Column("municipio", sa.String(length=100)),
        sa.Column("total_establecimientos", sa.Integer()),
        sa.Column("por_categoria", sa.JSON()),
        sa.Column("top_categoria", sa.String(length=255)),
        sa.Column("geom_centroid", Geometry(geometry_type="POINT", srid=4326), nullable=True),
        sa.Column("geom_hexagon", Geometry(geometry_type="POLYGON", srid=4326), nullable=True),
        sa.Column("last_refreshed", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        schema="cube",
    )
    op.create_index("idx_cube_comercial_geom", "commercial_density_h3", ["geom_hexagon"], unique=False, schema="cube", postgresql_using="gist")

    op.create_table(
        "zona_analysis_results",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("core.organizations.id"), nullable=False),
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("core.users.id"), nullable=True),
        sa.Column("polygon", Geometry(geometry_type="POLYGON", srid=4326), nullable=True),
        sa.Column("analysis_type", sa.String(length=50)),
        sa.Column("result_json", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        schema="analytics",
    )
    op.create_index("idx_zona_results_polygon", "zona_analysis_results", ["polygon"], unique=False, schema="analytics", postgresql_using="gist")


def downgrade() -> None:
    op.drop_index("idx_zona_results_polygon", table_name="zona_analysis_results", schema="analytics")
    op.drop_table("zona_analysis_results", schema="analytics")

    op.drop_index("idx_cube_comercial_geom", table_name="commercial_density_h3", schema="cube")
    op.drop_table("commercial_density_h3", schema="cube")

    op.drop_index("idx_denue_scian", table_name="denue_establishments", schema="raw_data")
    op.drop_index("idx_denue_geom", table_name="denue_establishments", schema="raw_data")
    op.drop_table("denue_establishments", schema="raw_data")

    op.drop_table("query_log", schema="core")
    op.drop_table("api_credentials", schema="core")
    op.drop_table("users", schema="core")
    op.drop_table("organizations", schema="core")
