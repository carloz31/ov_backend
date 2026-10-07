from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import consultas_instrumentos as consultas
from app.database import obtener_sesion
from app.esquemas_instrumentos import (
    AvanceInstrumento, ComparacionAutopercepcion, InstrumentoPublico, ItemPublico,
    RespuestasActividad, ResultadoHistorico, ResultadoPublico,
)
from app.models import Cuenta, Instrumento


router = APIRouter(tags=["Instrumentos"])
SesionBD = Annotated[Session, Depends(obtener_sesion)]


def consultar(operacion: Callable):
    try:
        return operacion()
    except consultas.ConsultaPendiente as error:
        avance = error.avance
        detalle = [a.model_dump(mode="json") for a in avance] if isinstance(avance, list) else avance.model_dump(mode="json")
        raise HTTPException(status_code=409, detail={"mensaje": str(error), "avance": detalle}) from error
    except LookupError as error:
        raise HTTPException(status_code=404, detail={"mensaje": str(error)}) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail={"mensaje": str(error)}) from error


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
