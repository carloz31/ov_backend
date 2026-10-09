from fastapi import APIRouter

from app.api import (
    acciones, actividades, comunidad, cuentas, desarrollo, diario, fichas, instrumentos, logros,
    registro, testimonios,
)


def crear_router(entorno: str) -> APIRouter:
    router = APIRouter()
    router.include_router(cuentas.router)
    router.include_router(actividades.router)
    router.include_router(fichas.router)
    router.include_router(testimonios.router)
    router.include_router(diario.router)
    router.include_router(logros.router)
    router.include_router(comunidad.router)
    router.include_router(acciones.router)
    router.include_router(instrumentos.router)
    router.include_router(registro.router)
    if entorno == 'desarrollo':
        router.include_router(desarrollo.router)
    return router
