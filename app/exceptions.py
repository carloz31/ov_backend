from collections.abc import Callable

from fastapi import HTTPException

from app.schemas.cuentas import ProgresoObjetivo
from app.schemas.instrumentos import AvanceAplicacion


class ErrorAccion(Exception):
    def __init__(self, mensaje: str, estado_http: int = 409, progreso: ProgresoObjetivo | None = None,
                 items_faltantes: list[str] | None = None):
        super().__init__(mensaje)
        self.estado_http = estado_http
        self.progreso = progreso
        self.items_faltantes = items_faltantes


class ConsultaPendiente(Exception):
    def __init__(self, mensaje: str, avance: AvanceAplicacion | list[AvanceAplicacion]):
        super().__init__(mensaje)
        self.avance = avance


def traducir_error_accion(error: ErrorAccion, *, incluir_items_faltantes: bool = True) -> HTTPException:
    detalle = {"mensaje": str(error)}
    if error.progreso is not None:
        detalle["progreso"] = error.progreso.model_dump(mode="json", exclude_unset=True)
    if incluir_items_faltantes and error.items_faltantes is not None:
        detalle["items_faltantes"] = error.items_faltantes
    return HTTPException(status_code=error.estado_http, detail=detalle)


def consultar(operacion: Callable):
    try:
        return operacion()
    except ConsultaPendiente as error:
        avance = error.avance
        detalle = [a.model_dump(mode="json") for a in avance] if isinstance(avance, list) else avance.model_dump(mode="json")
        raise HTTPException(status_code=409, detail={"mensaje": str(error), "avance": detalle}) from error
    except LookupError as error:
        raise HTTPException(status_code=404, detail={"mensaje": str(error)}) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail={"mensaje": str(error)}) from error
