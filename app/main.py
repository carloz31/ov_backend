from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import sessionmaker

from app.database import Base, crear_motor_bd, validar_version_esquema
from app.configuracion_base import cargar_configuracion_base
from app.routers import acciones, consultas, demo, instrumentos, registro
from app.seed import cargar_semilla_si_vacia, obtener_cargador_semilla
from app.definiciones import CacheDefiniciones
from app.contenido_registro import cargar_posiciones_registro
from app.evaluador_respuestas import EvaluadorFalso
from app.configuracion_registro import cargar_configuracion_registro, crear_evaluador_registro


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
    aplicacion.state.fabrica_sesiones = fabrica_sesiones
    aplicacion.state.evaluador_respuestas = EvaluadorFalso()
    aplicacion.include_router(consultas.router)
    aplicacion.include_router(acciones.router)
    aplicacion.include_router(instrumentos.router)
    aplicacion.include_router(registro.router)
    aplicacion.include_router(demo.router)
    aplicacion.mount("/demo/recursos", StaticFiles(directory=demo.RUTA_ESTATICOS), name="recursos_demo")
    return aplicacion


app = crear_aplicacion()
