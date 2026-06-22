from fastapi import APIRouter
from .zona import router as zona_router
from .admin import router as admin_router
from .analisis import router as analisis_router

router = APIRouter()
router.include_router(zona_router, prefix="/zona", tags=["zona"])
router.include_router(admin_router, prefix="/admin", tags=["admin"])
router.include_router(analisis_router, prefix="/analisis", tags=["analisis"])
