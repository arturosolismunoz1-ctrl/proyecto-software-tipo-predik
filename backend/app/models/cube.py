from sqlalchemy import Column, Float, Integer, JSON, SmallInteger, String, DateTime
from geoalchemy2 import Geometry
from app.db import Base


class CommercialDensityH3(Base):
    __tablename__ = "commercial_density_h3"
    __table_args__ = {"schema": "cube"}

    h3_index = Column(String(20), primary_key=True)
    h3_resolution = Column(SmallInteger)
    entidad = Column(String(100))
    municipio = Column(String(100))
    total_establecimientos = Column(Integer)
    por_categoria = Column(JSON)
    top_categoria = Column(String(255))
    geom_centroid = Column(Geometry(geometry_type="POINT", srid=4326))
    geom_hexagon = Column(Geometry(geometry_type="POLYGON", srid=4326))
    last_refreshed = Column(DateTime(timezone=True))


class PopulationDensityH3(Base):
    __tablename__ = "population_density_h3"
    __table_args__ = {"schema": "cube"}

    h3_index = Column(String(20), primary_key=True)
    h3_resolution = Column(SmallInteger)
    entidad = Column(String(100))
    municipio = Column(String(100))
    pobtot = Column(Integer)
    pobmas = Column(Integer)
    pobfem = Column(Integer)
    p_0a14 = Column(Integer)
    p_15a64 = Column(Integer)
    p_65ymas = Column(Integer)
    vivpar_hab = Column(Integer)
    densidad_hab_km2 = Column(Float)
    geom_centroid = Column(Geometry(geometry_type="POINT", srid=4326))
    geom_hexagon = Column(Geometry(geometry_type="POLYGON", srid=4326))
    last_refreshed = Column(DateTime(timezone=True))
