import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.orm import sessionmaker

from app.api.router import crear_router
from app.config import cargar_configuracion, crear_evaluador_registro
from app.core.definiciones import CacheDefiniciones
from app.database import comprobar_tablas, crear_motor_bd
from app.services.registro.evaluacion import EvaluadorFalso


def crear_aplicacion(url_bd: str | None = None) -> FastAPI:
    variables = None if url_bd is None else {**os.environ, 'DATABASE_URL': url_bd}
    configuracion = cargar_configuracion(entorno=variables)
    motor_bd = crear_motor_bd(configuracion.url_bd)
    fabrica_sesiones = sessionmaker(bind=motor_bd)

    @asynccontextmanager
    async def ciclo_vida(aplicacion: FastAPI):
        evaluador = None
        try:
            evaluador = crear_evaluador_registro(configuracion)
            aplicacion.state.configuracion_registro = configuracion
            aplicacion.state.evaluador_respuestas = evaluador
            comprobar_tablas(motor_bd)
            motor_bd.cache_definiciones = CacheDefiniciones(motor_bd)
            yield
        finally:
            motor_bd.dispose()
            if evaluador is not None and hasattr(evaluador, 'cerrar'):
                evaluador.cerrar()

    aplicacion = FastAPI(title="Plataforma de orientación vocacional", lifespan=ciclo_vida)
    aplicacion.state.motor_bd = motor_bd
    aplicacion.state.configuracion = configuracion
    aplicacion.state.fabrica_sesiones = fabrica_sesiones
    aplicacion.state.evaluador_respuestas = EvaluadorFalso()
    aplicacion.include_router(crear_router(configuracion.entorno))
    return aplicacion


app = crear_aplicacion()
