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


@app.get("/debug/db", tags=["health"])
def debug_db() -> dict:
    import os
    from sqlalchemy import text
    from app.db import SessionLocal, DATABASE_URL
    raw = os.getenv("DATABASE_URL", "NOT_SET")
    # Oculta password para mostrarlo seguro
    def hide_pass(url: str) -> str:
        try:
            at = url.rindex("@")
            scheme_end = url.index("://") + 3
            user_pass = url[scheme_end:at]
            user = user_pass.split(":")[0]
            return url[:scheme_end] + user + ":***@" + url[at+1:]
        except Exception:
            return url
    try:
        db = SessionLocal()
        result = db.execute(text("SELECT 1")).scalar()
        db.close()
        return {"status": "ok", "result": result, "url_used": hide_pass(DATABASE_URL)}
    except Exception as e:
        return {"status": "error", "error": str(e), "type": type(e).__name__,
                "env_url": hide_pass(raw), "url_used": hide_pass(DATABASE_URL)}
