from fastapi import APIRouter

from app.api import acciones, cuentas, demo, instrumentos, registro


def crear_router(entorno: str) -> APIRouter:
    router = APIRouter()
    router.include_router(cuentas.router)
    router.include_router(acciones.router)
    router.include_router(instrumentos.router)
    router.include_router(registro.router)
    if entorno == 'desarrollo':
        router.include_router(registro.router_demo)
        router.include_router(demo.router)
    return router
