from sqlalchemy.orm import Session

from app.core.contexto import usar_contexto
from app.models import Carrera, Cuenta, TipoEventoUso
from app.schemas.acciones import RespuestaAccion, VerCarreraEntrada
from app.services.comun import buscar_por_codigo, fecha_accion, responder_con_eventos


@usar_contexto
def ver_carrera(sesion: Session, entrada: VerCarreraEntrada) -> RespuestaAccion:
    cuenta = buscar_por_codigo(sesion, Cuenta, entrada.cuenta)
    carrera = buscar_por_codigo(sesion, Carrera, entrada.carrera)
    return responder_con_eventos(sesion, cuenta, [(TipoEventoUso.VISTA_CARRERA, carrera.id)], fecha_accion(entrada))
