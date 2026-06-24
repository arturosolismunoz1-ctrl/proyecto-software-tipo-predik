import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://admin:dev_password_local@localhost:5432/geodata_predik_clone",
)

if "sslmode" not in DATABASE_URL and os.getenv("ENVIRONMENT", "development") == "production":
    DATABASE_URL += "?sslmode=require"

engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
Base = declarative_base()
