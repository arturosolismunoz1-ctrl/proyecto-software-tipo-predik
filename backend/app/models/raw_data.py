from sqlalchemy import BigInteger, Column, Date, DateTime, ForeignKey, Integer, String, JSON
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
