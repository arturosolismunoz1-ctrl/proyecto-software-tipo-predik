from fastapi import APIRouter
from .auth import router as auth_router
from .zona import router as zona_router
from .admin import router as admin_router
from .analisis import router as analisis_router
from .etl import router as etl_router
from .reporte import router as reporte_router
from .catalogo import router as catalogo_router
from .bie import router as bie_router

router = APIRouter(prefix="/api/v1")
router.include_router(auth_router,     prefix="/auth",     tags=["auth"])
router.include_router(zona_router,     prefix="/zona",     tags=["zona"])
router.include_router(admin_router,    prefix="/admin",    tags=["admin"])
router.include_router(analisis_router, prefix="/analisis", tags=["analisis"])
router.include_router(etl_router,      prefix="/admin",    tags=["etl"])
router.include_router(reporte_router,  prefix="/reporte",  tags=["reporte"])
router.include_router(catalogo_router, prefix="/catalogo", tags=["catalogo"])
router.include_router(bie_router,      prefix="/bie",      tags=["bie"])
