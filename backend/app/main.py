import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load .env from repo root (two levels up from backend/app/)
load_dotenv(Path(__file__).resolve().parents[2] / ".env")
from app.api.v1 import router as api_router
from app.middleware import QueryLogMiddleware

try:
    from app.scheduler import start_scheduler, stop_scheduler
except ImportError:
    start_scheduler = stop_scheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    if start_scheduler:
        start_scheduler()
    yield
    if stop_scheduler:
        stop_scheduler()


app = FastAPI(
    title="GeoData Predik Clone",
    version="0.1.0",
    lifespan=lifespan,
)

origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(QueryLogMiddleware)
app.include_router(api_router)


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok"}
