from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies import SesionBD
from app.exceptions import consultar
from app.models import Cuenta, Instrumento
from app.schemas.instrumentos import (
    AvanceInstrumento, ComparacionAutopercepcion, InstrumentoPublico, ItemPublico,
    RespuestasActividad, ResultadoHistorico, ResultadoPublico,
)
from app.services.instrumentos import consultas as consultas


router = APIRouter(tags=["Instrumentos"])


def obtener_estudiante(cuenta: str, sesion: SesionBD) -> Cuenta:
    return consultar(lambda: consultas.cuenta_estudiante(sesion, cuenta))


Estudiante = Annotated[Cuenta, Depends(obtener_estudiante)]


@router.get("/instrumentos", response_model=list[InstrumentoPublico])
def catalogo(sesion: SesionBD):
    return consultas.catalogo_instrumentos(sesion)


@router.get("/actividades/{actividad}/items", response_model=list[ItemPublico])
def items(actividad: str, sesion: SesionBD):
    return consultar(lambda: consultas.items_presentados(sesion, consultas.actividad_estudiante(sesion, actividad)))


@router.get("/cuentas/{cuenta}/actividades/{actividad}/respuestas", response_model=RespuestasActividad)
def respuestas(estudiante: Estudiante, actividad: str, sesion: SesionBD):
    return consultar(lambda: consultas.respuestas_actuales(sesion, estudiante,
                                                         consultas.actividad_estudiante(sesion, actividad)))


@router.get("/cuentas/{cuenta}/instrumentos", response_model=list[AvanceInstrumento])
def avance(estudiante: Estudiante, sesion: SesionBD):
    return consultas.avance_instrumentos(sesion, estudiante)


@router.get("/cuentas/{cuenta}/instrumentos/{instrumento}/comparacion", response_model=ComparacionAutopercepcion)
def comparacion(estudiante: Estudiante, instrumento: str, sesion: SesionBD):
    return consultar(lambda: consultas.comparacion_autopercepcion(sesion, estudiante,
        consultas.entidad_por_codigo(sesion, Instrumento, instrumento)))


@router.get("/cuentas/{cuenta}/instrumentos/{instrumento}/resultado", response_model=ResultadoPublico,
            response_model_exclude_unset=True)
def resultado(estudiante: Estudiante, instrumento: str, sesion: SesionBD, aplicacion: str | None = None):
    return consultar(lambda: consultas.resultado_vigente(sesion, estudiante,
        consultas.entidad_por_codigo(sesion, Instrumento, instrumento), aplicacion))


@router.get("/cuentas/{cuenta}/instrumentos/{instrumento}/historial", response_model=list[ResultadoHistorico],
            response_model_exclude_unset=True)
def historial(estudiante: Estudiante, instrumento: str, sesion: SesionBD):
    return consultar(lambda: consultas.historial_resultados(sesion, estudiante,
        consultas.entidad_por_codigo(sesion, Instrumento, instrumento)))
