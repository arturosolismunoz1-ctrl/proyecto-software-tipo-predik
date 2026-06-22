from fastapi import FastAPI
from app.api.v1 import router as api_router

app = FastAPI(
    title="GeoData Predik Clone",
    version="0.1.0",
    openapi_prefix="/api/v1"
)

app.include_router(api_router)


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok"}
