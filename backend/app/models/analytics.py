from sqlalchemy import Column, DateTime, ForeignKey, JSON, String
from geoalchemy2 import Geometry
from app.db import Base


class ZonaAnalysisResult(Base):
    __tablename__ = "zona_analysis_results"
    __table_args__ = {"schema": "analytics"}

    id = Column(String, primary_key=True)
    organization_id = Column(String, ForeignKey("core.organizations.id"), nullable=False)
    user_id = Column(String, ForeignKey("core.users.id"), nullable=True)
    polygon = Column(Geometry(geometry_type="POLYGON", srid=4326))
    analysis_type = Column(String(50))
    result_json = Column(JSON)
    created_at = Column(DateTime(timezone=True))
