from fastapi import APIRouter

from app.api import acciones, cuentas, demo, instrumentos, registro


router = APIRouter()
router.include_router(cuentas.router)
router.include_router(acciones.router)
router.include_router(instrumentos.router)
router.include_router(registro.router)
router.include_router(demo.router)
