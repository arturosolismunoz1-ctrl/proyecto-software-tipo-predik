from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI

# Load .env from repo root (two levels up from backend/app/)
load_dotenv(Path(__file__).resolve().parents[2] / ".env")
from app.api.v1 import router as api_router
from app.middleware import QueryLogMiddleware
from app.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="GeoData Predik Clone",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(QueryLogMiddleware)
app.include_router(api_router)


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok"}
