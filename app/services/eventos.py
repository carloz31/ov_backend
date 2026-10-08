from sqlalchemy.orm import Session

from app.core.contexto import usar_contexto
from app.exceptions import ErrorAccion
from app.models import Cuenta, TipoEventoUso
from app.schemas.acciones import AccionCuenta, EventoEntrada, RespuestaAccion
from app.services.comun import buscar_por_codigo, fecha_accion, responder_con_eventos
from app.services.motor.referencias import MODELOS_REFERENCIA


@usar_contexto
def ingresar(sesion: Session, entrada: AccionCuenta) -> RespuestaAccion:
    cuenta = buscar_por_codigo(sesion, Cuenta, entrada.cuenta)
    return responder_con_eventos(sesion, cuenta, [(TipoEventoUso.INGRESO, None)], fecha_accion(entrada))


@usar_contexto
def registrar_evento_crudo(sesion: Session, entrada: EventoEntrada) -> RespuestaAccion:
    cuenta = buscar_por_codigo(sesion, Cuenta, entrada.cuenta)
    referencia = None
    if entrada.referencia is not None:
        modelo = MODELOS_REFERENCIA.get(entrada.tipo)
        if modelo is None:
            raise ErrorAccion("Este tipo de evento no admite una referencia con código público", estado_http=422)
        referencia = buscar_por_codigo(sesion, modelo, entrada.referencia).id
    return responder_con_eventos(sesion, cuenta, [(entrada.tipo, referencia)], fecha_accion(entrada))
