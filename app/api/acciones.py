from fastapi import APIRouter

from app.dependencies import SesionBD, ejecutar_accion
from app.schemas.acciones import (
    AccionCuenta, CheckInEntrada, CompletarActividadEntrada, CompletarConversacionEntrada,
    EscribirCartaEntrada, EscribirEntradaEntrada, EventoEntrada, PublicarEntrevistaEntrada,
    ReiniciarInstrumentoEntrada, ResolverCasoEntrada, ResponderItemsEntrada,
    ResponderRegistroEntrada, RespuestaAccion, RespuestaAgrupada, RespuestaCompletarActividad,
    RespuestaItemsGuardados, RespuestaReiniciarInstrumento, VerCarreraEntrada,
)
from app.services import (
    actividades as servicio_actividades, carreras as servicio_carreras,
    comunidad as servicio_comunidad, diario as servicio_diario, eventos as servicio_eventos,
)


router = APIRouter(tags=["Acciones"])


@router.post("/acciones/ingresar", response_model=RespuestaAccion, response_model_exclude_unset=True)
def ingresar(entrada: AccionCuenta, sesion: SesionBD):
    return ejecutar_accion(sesion, lambda: servicio_eventos.ingresar(sesion, entrada))


@router.post("/acciones/completar-actividad", response_model=RespuestaCompletarActividad, response_model_exclude_unset=True)
def completar_actividad(entrada: CompletarActividadEntrada, sesion: SesionBD):
    return ejecutar_accion(sesion, lambda: servicio_actividades.completar_actividad(sesion, entrada))


@router.post("/acciones/responder-items", response_model=RespuestaItemsGuardados)
def responder_items(entrada: ResponderItemsEntrada, sesion: SesionBD):
    return ejecutar_accion(sesion, lambda: servicio_actividades.responder_items(sesion, entrada))


@router.post("/acciones/reiniciar-instrumento", response_model=RespuestaReiniciarInstrumento,
             response_model_exclude_unset=True)
def reiniciar_instrumento(entrada: ReiniciarInstrumentoEntrada, sesion: SesionBD):
    return ejecutar_accion(sesion, lambda: servicio_actividades.reiniciar_instrumento(sesion, entrada))


@router.post("/acciones/resolver-caso", response_model=RespuestaAccion, response_model_exclude_unset=True)
def resolver_caso(entrada: ResolverCasoEntrada, sesion: SesionBD):
    return ejecutar_accion(sesion, lambda: servicio_actividades.resolver_caso(sesion, entrada))


@router.post("/acciones/responder-registro", response_model=RespuestaAccion, response_model_exclude_unset=True)
def responder_registro(entrada: ResponderRegistroEntrada, sesion: SesionBD):
    return ejecutar_accion(sesion, lambda: servicio_diario.responder_registro(sesion, entrada))


@router.post("/acciones/escribir-entrada", response_model=RespuestaAccion, response_model_exclude_unset=True)
def escribir_entrada(entrada: EscribirEntradaEntrada, sesion: SesionBD):
    return ejecutar_accion(sesion, lambda: servicio_diario.escribir_entrada(sesion, entrada))


@router.post("/acciones/check-in", response_model=RespuestaAccion, response_model_exclude_unset=True)
def registrar_check_in(entrada: CheckInEntrada, sesion: SesionBD):
    return ejecutar_accion(sesion, lambda: servicio_diario.registrar_check_in(sesion, entrada))


@router.post("/acciones/ver-carrera", response_model=RespuestaAccion, response_model_exclude_unset=True)
def ver_carrera(entrada: VerCarreraEntrada, sesion: SesionBD):
    return ejecutar_accion(sesion, lambda: servicio_carreras.ver_carrera(sesion, entrada))


@router.post("/acciones/publicar-entrevista", response_model=RespuestaAgrupada, response_model_exclude_unset=True)
def publicar_entrevista(entrada: PublicarEntrevistaEntrada, sesion: SesionBD):
    return ejecutar_accion(sesion, lambda: servicio_comunidad.publicar_entrevista(sesion, entrada))


@router.post("/acciones/escribir-carta", response_model=RespuestaAccion, response_model_exclude_unset=True)
def escribir_carta(entrada: EscribirCartaEntrada, sesion: SesionBD):
    return ejecutar_accion(sesion, lambda: servicio_comunidad.escribir_carta(sesion, entrada))


@router.post("/acciones/completar-conversacion", response_model=RespuestaAgrupada, response_model_exclude_unset=True)
def completar_conversacion(entrada: CompletarConversacionEntrada, sesion: SesionBD):
    return ejecutar_accion(sesion, lambda: servicio_comunidad.completar_conversacion(sesion, entrada))


@router.post("/eventos", response_model=RespuestaAccion, response_model_exclude_unset=True, tags=["Depuración"])
def registrar_evento(entrada: EventoEntrada, sesion: SesionBD):
    return ejecutar_accion(sesion, lambda: servicio_eventos.registrar_evento_crudo(sesion, entrada))
