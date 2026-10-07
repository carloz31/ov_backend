from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app import acciones_registro, consultas_registro
from app.acciones import ErrorAccion
from app.database import obtener_sesion
from app.routers.acciones import ejecutar_accion
from app.schemas_registro import (
    AccionItemRegistroEntrada, EstadoItemRegistro, EvaluacionRegistroDemo, GuardarPosicionEntrada,
    ItemRegistroPublico, PosicionGuardada, RegistroConsultado, RespuestaEnvioRegistro, TextoRegistroEntrada,
    ResponderSeguimientoEntrada,
)


router = APIRouter(tags=['Registro'])
SesionBD = Annotated[Session, Depends(obtener_sesion)]


@router.post('/acciones/guardar-posicion', response_model=PosicionGuardada)
def guardar_posicion(entrada: GuardarPosicionEntrada, sesion: SesionBD, peticion: Request):
    return ejecutar_accion(sesion, lambda: acciones_registro.guardar_posicion(
        sesion, entrada, peticion.app.state.posiciones_registro))


@router.post('/acciones/registro/guardar-borrador', response_model=EstadoItemRegistro)
def guardar_borrador(entrada: TextoRegistroEntrada, sesion: SesionBD):
    return ejecutar_accion(sesion, lambda: acciones_registro.guardar_borrador(sesion, entrada))


@router.post('/acciones/registro/enviar', response_model=RespuestaEnvioRegistro, response_model_exclude_unset=True)
def enviar(entrada: TextoRegistroEntrada, peticion: Request):
    return ejecutar_envio(entrada, peticion)


@router.post('/acciones/registro/responder-seguimiento', response_model=RespuestaEnvioRegistro,
             response_model_exclude_unset=True)
def responder_seguimiento(entrada: ResponderSeguimientoEntrada, peticion: Request):
    return ejecutar_envio(entrada, peticion, seguimiento=True)


def ejecutar_envio(entrada, peticion, seguimiento=False):
    # No usa la dependencia de sesión: el núcleo abre y cierra cada fase por separado.
    try:
        configuracion = peticion.app.state.configuracion_registro
        return acciones_registro.enviar(peticion.app.state.fabrica_sesiones, entrada,
            peticion.app.state.evaluador_respuestas,
            seguimiento=seguimiento,
            modelo=configuracion.modelo if configuracion.evaluador == 'gemini' else None,
            tiempo_maximo_segundos=configuracion.timeout_segundos)
    except ErrorAccion as error:
        detalle = {'mensaje': str(error)}
        if error.progreso is not None:
            detalle['progreso'] = error.progreso.model_dump(mode='json', exclude_unset=True)
        raise HTTPException(status_code=error.estado_http, detail=detalle) from error
    except IntegrityError as error:
        raise HTTPException(status_code=409, detail={
            'mensaje': 'El envío entra en conflicto con el estado actual de la cuenta',
        }) from error
    except OperationalError as error:
        # SQLite puede rechazar un escritor simultáneo antes de comprobar la condición.
        if getattr(error.orig, 'sqlite_errorname', '') in ('SQLITE_BUSY', 'SQLITE_BUSY_SNAPSHOT', 'SQLITE_LOCKED'):
            raise HTTPException(status_code=409, detail={
                'mensaje': 'El registro está siendo actualizado; vuelve a intentarlo',
            }) from error
        raise


@router.post('/acciones/registro/continuar-sin-responder', response_model=RespuestaEnvioRegistro,
             response_model_exclude_unset=True)
def continuar_sin_responder(entrada: AccionItemRegistroEntrada, sesion: SesionBD):
    return ejecutar_accion(sesion, lambda: acciones_registro.continuar_sin_responder(sesion, entrada))


@router.get('/actividades/{actividad}/items-registro', response_model=list[ItemRegistroPublico])
def consultar_items(actividad: str, sesion: SesionBD):
    return ejecutar_accion(sesion, lambda: consultas_registro.consultar_items(sesion, actividad))


@router.get('/cuentas/{cuenta}/actividades/{actividad}/registro', response_model=RegistroConsultado,
            response_model_exclude_unset=True)
def consultar_registro(cuenta: str, actividad: str, sesion: SesionBD):
    return ejecutar_accion(sesion, lambda: consultas_registro.consultar_registro(sesion, cuenta, actividad))


@router.get('/demo/registro/{cuenta}/{actividad}/evaluaciones', response_model=list[EvaluacionRegistroDemo])
def consultar_evaluaciones(cuenta: str, actividad: str, sesion: SesionBD):
    return ejecutar_accion(sesion, lambda: consultas_registro.consultar_evaluaciones(sesion, cuenta, actividad))
