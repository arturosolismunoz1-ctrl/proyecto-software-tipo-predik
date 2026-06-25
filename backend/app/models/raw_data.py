from sqlalchemy import BigInteger, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry

from app.db import Base


class DenueEstablishment(Base):
    __tablename__ = "denue_establishments"
    __table_args__ = {"schema": "raw_data"}

    id = Column(BigInteger, primary_key=True)
    clee = Column(String(50), unique=True)
    nombre = Column(String(255))
    razon_social = Column(String(255))
    clase_actividad = Column(String(255))
    codigo_scian = Column(String(10))
    estrato_personal = Column(String(50))
    entidad = Column(String(100))
    municipio = Column(String(100))
    localidad = Column(String(100))
    colonia = Column(String(150))
    cp = Column(String(10))
    geom = Column(Geometry(geometry_type="POINT", srid=4326))
    fuente_actualizacion = Column(Date)
    fetched_at = Column(DateTime(timezone=True))
    raw_response = Column(JSON)


class AgebGeometry(Base):
    """Polígonos de AGEBs del Marco Geoestadístico Nacional (MGN)."""

    __tablename__ = "ageb_geometries"
    __table_args__ = {"schema": "raw_data"}

    cvegeo = Column(String(16), primary_key=True)
    clave_ent = Column(String(2), nullable=False)
    clave_mun = Column(String(3))
    cve_loc = Column(String(4))
    cve_ageb = Column(String(4))
    cvegeo_9 = Column(String(9))
    nom_ent = Column(String(100))
    nom_mun = Column(String(150))
    nom_loc = Column(String(250))
    ambito = Column(String(10))
    geom = Column(Geometry(geometry_type="MULTIPOLYGON", srid=4326))
    loaded_at = Column(DateTime(timezone=True))


class AgebDemographics(Base):
    """Indicadores del Censo de Población y Vivienda 2020 a nivel AGEB."""

    __tablename__ = "ageb_demographics"
    __table_args__ = {"schema": "raw_data"}

    cvegeo = Column(String(16), primary_key=True)
    fuente = Column(String(50))
    pobtot = Column(Integer())
    pobmas = Column(Integer())
    pobfem = Column(Integer())
    p_0a14 = Column(Integer())
    p_15a64 = Column(Integer())
    p_65ymas = Column(Integer())
    vivpar_hab = Column(Integer())
    prom_ocup = Column(Float())
    graproes = Column(Float())
    pcon_disc = Column(Integer())
    psinder = Column(Integer())
    pder_ss = Column(Integer())
    indicadores = Column(JSON)
    score_nse = Column(Float(), nullable=True)
    nse_nivel = Column(String(10), nullable=True)
    loaded_at = Column(DateTime(timezone=True))


class BieIndicador(Base):
    """Serie de tiempo de un indicador macroeconómico del BIE (INEGI)."""

    __tablename__ = "bie_indicadores"
    __table_args__ = {"schema": "raw_data"}

    id = Column(Integer, primary_key=True, autoincrement=True)
    indicador_id = Column(String(20), nullable=False)
    nombre = Column(String(200))
    descripcion = Column(Text())
    unidad = Column(String(100))
    frecuencia = Column(String(20))
    area_clave = Column(String(10), nullable=False)
    estado_clave = Column(String(2))
    periodo = Column(String(10), nullable=False)
    periodo_fecha = Column(Date())
    valor = Column(Float())
    fuente = Column(String(50), default="BIE_INEGI")
    loaded_at = Column(DateTime(timezone=True))


class ManzanaVivienda(Base):
    """Inventario Nacional de Vivienda a nivel manzana."""

    __tablename__ = "manzana_vivienda"
    __table_args__ = {"schema": "raw_data"}

    cvegeo = Column(String(16), primary_key=True)
    clave_ent = Column(String(2))
    clave_mun = Column(String(3))
    cve_loc = Column(String(4))
    cve_ageb = Column(String(4))
    cve_mza = Column(String(3))
    cvegeo_ageb = Column(String(16))
    vivtot = Column(Integer())
    vivpar = Column(Integer())
    vivpar_hab = Column(Integer())
    con_agua = Column(Integer())
    con_dren = Column(Integer())
    con_luz = Column(Integer())
    geom = Column(Geometry(geometry_type="MULTIPOLYGON", srid=4326))
    indicadores = Column(JSON)
    fuente = Column(String(50))
    loaded_at = Column(DateTime(timezone=True))
