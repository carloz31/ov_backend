from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import sessionmaker

from app.api import demo
from app.api.router import router
from app.config import (
    cargar_configuracion_base, cargar_configuracion_registro, crear_evaluador_registro,
)
from app.core.definiciones import CacheDefiniciones
from app.database import crear_motor_bd, validar_version_esquema
from app.models.base import Base
from app.services.registro.contenido import cargar_posiciones_registro
from app.services.registro.evaluacion import EvaluadorFalso


def obtener_cargador_semilla(semilla: str):
    """Puente temporal de R2; desaparece al separar el arranque en R3."""
    from datos.cargar import obtener_cargador_semilla as obtener_cargador

    return obtener_cargador(semilla)


def cargar_semilla_si_vacia(sesion, semilla: str):
    """Puente temporal de R2, con la misma política de carga existente."""
    from datos.cargar import cargar_semilla_si_vacia as cargar

    return cargar(sesion, semilla)


def crear_aplicacion(url_bd: str | None = None, semilla: str | None = None) -> FastAPI:
    configuracion_base = cargar_configuracion_base(url_bd, semilla)
    motor_bd = crear_motor_bd(configuracion_base.url_bd)
    fabrica_sesiones = sessionmaker(bind=motor_bd)

    @asynccontextmanager
    async def ciclo_vida(aplicacion: FastAPI):
        evaluador = None
        try:
            configuracion = cargar_configuracion_registro()
            evaluador = crear_evaluador_registro(configuracion)
            aplicacion.state.configuracion_registro = configuracion
            aplicacion.state.evaluador_respuestas = evaluador
            validar_version_esquema(motor_bd, configuracion_base.semilla)
            obtener_cargador_semilla(configuracion_base.semilla)
            Base.metadata.create_all(motor_bd)
            with fabrica_sesiones.begin() as sesion:
                cargar_semilla_si_vacia(sesion, configuracion_base.semilla)
                posiciones = (cargar_posiciones_registro(sesion)
                              if configuracion_base.semilla == 'demo' else {})
            aplicacion.state.posiciones_registro = posiciones
            motor_bd.cache_definiciones = CacheDefiniciones(motor_bd)
            yield
        finally:
            motor_bd.dispose()
            if evaluador is not None and hasattr(evaluador, 'cerrar'):
                evaluador.cerrar()

    aplicacion = FastAPI(title="Demo del motor de desbloqueos", lifespan=ciclo_vida)
    aplicacion.state.motor_bd = motor_bd
    aplicacion.state.semilla = configuracion_base.semilla
    aplicacion.state.obtener_cargador_semilla = obtener_cargador_semilla
    aplicacion.state.fabrica_sesiones = fabrica_sesiones
    aplicacion.state.evaluador_respuestas = EvaluadorFalso()
    aplicacion.include_router(router)
    aplicacion.mount("/demo/recursos", StaticFiles(directory=demo.RUTA_ESTATICOS), name="recursos_demo")
    return aplicacion


app = crear_aplicacion()
