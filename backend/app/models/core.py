from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db import Base


class Organization(Base):
    __tablename__ = "organizations"
    __table_args__ = {"schema": "core"}

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    name = Column(String(255), nullable=False)
    plan = Column(String(50), nullable=False, server_default="starter")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, nullable=False, server_default="true")

    users = relationship("User", back_populates="organization")
    api_credentials = relationship("APICredential", back_populates="organization")
    query_log = relationship("QueryLog", back_populates="organization")


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "core"}

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    organization_id = Column(UUID(as_uuid=True), ForeignKey("core.organizations.id"), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, server_default="analyst")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    organization = relationship("Organization", back_populates="users")
    query_log = relationship("QueryLog", back_populates="user")


class APICredential(Base):
    __tablename__ = "api_credentials"
    __table_args__ = {"schema": "core"}

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    organization_id = Column(UUID(as_uuid=True), ForeignKey("core.organizations.id"), nullable=False)
    connector_name = Column(String(100), nullable=False)
    encrypted_value = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    organization = relationship("Organization", back_populates="api_credentials")


class QueryLog(Base):
    __tablename__ = "query_log"
    __table_args__ = {"schema": "core"}

    id = Column(String, primary_key=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("core.organizations.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("core.users.id"), nullable=True)
    endpoint = Column(String(255))
    request_summary = Column(String)
    duration_ms = Column(String)
    status_code = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    organization = relationship("Organization", back_populates="query_log")
    user = relationship("User", back_populates="query_log")
