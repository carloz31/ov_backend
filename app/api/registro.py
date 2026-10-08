from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.exc import IntegrityError, OperationalError

from app.database import es_bloqueo_temporal
from app.dependencies import SesionBD, ejecutar_accion
from app.exceptions import ErrorAccion, traducir_error_accion
from app.schemas.registro import (
    AccionItemRegistroEntrada, EstadoItemRegistro, EvaluacionRegistroDemo, GuardarPosicionEntrada,
    ItemRegistroPublico, PosicionGuardada, RegistroConsultado, ResponderSeguimientoEntrada,
    RespuestaEnvioRegistro, TextoRegistroEntrada,
)
from app.services.registro import acciones as acciones_registro, consultas as consultas_registro


router = APIRouter(tags=['Registro'])


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
        raise traducir_error_accion(error, incluir_items_faltantes=False) from error
    except IntegrityError as error:
        raise HTTPException(status_code=409, detail={
            'mensaje': 'El envío entra en conflicto con el estado actual de la cuenta',
        }) from error
    except OperationalError as error:
        # SQLite puede rechazar un escritor simultáneo antes de comprobar la condición.
        if es_bloqueo_temporal(error):
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
