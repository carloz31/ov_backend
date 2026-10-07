from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import acciones
from app.database import obtener_sesion
from app.schemas import (
    AccionCuenta, CheckInEntrada, CompletarActividadEntrada, CompletarConversacionEntrada,
    EscribirCartaEntrada, EscribirEntradaEntrada, EventoEntrada, PublicarEntrevistaEntrada,
    ResponderItemsEntrada, ResponderRegistroEntrada, ResolverCasoEntrada, RespuestaAccion,
    RespuestaAgrupada, RespuestaCompletarActividad, RespuestaItemsGuardados, VerCarreraEntrada,
    ReiniciarInstrumentoEntrada, RespuestaReiniciarInstrumento,
)


router = APIRouter(tags=["Acciones"])
SesionBD = Annotated[Session, Depends(obtener_sesion)]


def ejecutar_accion(sesion: Session, operacion: Callable):
    try:
        with sesion.begin():
            return operacion()
    except acciones.ErrorAccion as error:
        detalle = {"mensaje": str(error)}
        if error.progreso is not None:
            detalle["progreso"] = error.progreso.model_dump(mode="json", exclude_unset=True)
        if error.items_faltantes is not None:
            detalle["items_faltantes"] = error.items_faltantes
        raise HTTPException(status_code=error.estado_http, detail=detalle) from error
    except IntegrityError as error:
        raise HTTPException(status_code=409, detail={
            "mensaje": "La acción entra en conflicto con el estado actual de la cuenta",
        }) from error


@router.post("/acciones/ingresar", response_model=RespuestaAccion, response_model_exclude_unset=True)
def ingresar(entrada: AccionCuenta, sesion: SesionBD):
    return ejecutar_accion(sesion, lambda: acciones.ingresar(sesion, entrada))


@router.post("/acciones/completar-actividad", response_model=RespuestaCompletarActividad, response_model_exclude_unset=True)
def completar_actividad(entrada: CompletarActividadEntrada, sesion: SesionBD):
    return ejecutar_accion(sesion, lambda: acciones.completar_actividad(sesion, entrada))


@router.post("/acciones/responder-items", response_model=RespuestaItemsGuardados)
def responder_items(entrada: ResponderItemsEntrada, sesion: SesionBD):
    return ejecutar_accion(sesion, lambda: acciones.responder_items(sesion, entrada))


@router.post("/acciones/reiniciar-instrumento", response_model=RespuestaReiniciarInstrumento,
             response_model_exclude_unset=True)
def reiniciar_instrumento(entrada: ReiniciarInstrumentoEntrada, sesion: SesionBD):
    return ejecutar_accion(sesion, lambda: acciones.reiniciar_instrumento(sesion, entrada))


@router.post("/acciones/resolver-caso", response_model=RespuestaAccion, response_model_exclude_unset=True)
def resolver_caso(entrada: ResolverCasoEntrada, sesion: SesionBD):
    return ejecutar_accion(sesion, lambda: acciones.resolver_caso(sesion, entrada))


@router.post("/acciones/responder-registro", response_model=RespuestaAccion, response_model_exclude_unset=True)
def responder_registro(entrada: ResponderRegistroEntrada, sesion: SesionBD):
    return ejecutar_accion(sesion, lambda: acciones.responder_registro(sesion, entrada))


@router.post("/acciones/escribir-entrada", response_model=RespuestaAccion, response_model_exclude_unset=True)
def escribir_entrada(entrada: EscribirEntradaEntrada, sesion: SesionBD):
    return ejecutar_accion(sesion, lambda: acciones.escribir_entrada(sesion, entrada))


@router.post("/acciones/check-in", response_model=RespuestaAccion, response_model_exclude_unset=True)
def registrar_check_in(entrada: CheckInEntrada, sesion: SesionBD):
    return ejecutar_accion(sesion, lambda: acciones.registrar_check_in(sesion, entrada))


@router.post("/acciones/ver-carrera", response_model=RespuestaAccion, response_model_exclude_unset=True)
def ver_carrera(entrada: VerCarreraEntrada, sesion: SesionBD):
    return ejecutar_accion(sesion, lambda: acciones.ver_carrera(sesion, entrada))


@router.post("/acciones/publicar-entrevista", response_model=RespuestaAgrupada, response_model_exclude_unset=True)
def publicar_entrevista(entrada: PublicarEntrevistaEntrada, sesion: SesionBD):
    return ejecutar_accion(sesion, lambda: acciones.publicar_entrevista(sesion, entrada))


@router.post("/acciones/escribir-carta", response_model=RespuestaAccion, response_model_exclude_unset=True)
def escribir_carta(entrada: EscribirCartaEntrada, sesion: SesionBD):
    return ejecutar_accion(sesion, lambda: acciones.escribir_carta(sesion, entrada))


@router.post("/acciones/completar-conversacion", response_model=RespuestaAgrupada, response_model_exclude_unset=True)
def completar_conversacion(entrada: CompletarConversacionEntrada, sesion: SesionBD):
    return ejecutar_accion(sesion, lambda: acciones.completar_conversacion(sesion, entrada))


@router.post("/eventos", response_model=RespuestaAccion, response_model_exclude_unset=True, tags=["Depuración"])
def registrar_evento(entrada: EventoEntrada, sesion: SesionBD):
    return ejecutar_accion(sesion, lambda: acciones.registrar_evento_crudo(sesion, entrada))
