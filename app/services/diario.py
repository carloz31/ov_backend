from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.contexto import usar_contexto
from app.exceptions import ErrorAccion
from app.models import (
    CheckIn, Cuenta, EntradaDiario, OrigenEntrada, PreguntaDiario, TipoEventoUso, TipoObjetivo,
)
from app.schemas.acciones import (
    CheckInEntrada, EscribirEntradaEntrada, ResponderRegistroEntrada, RespuestaAccion,
)
from app.services.comun import (
    buscar_por_codigo, exigir_disponible, exigir_estudiante, fecha_accion, responder_con_eventos,
)


@usar_contexto
def responder_registro(sesion: Session, entrada: ResponderRegistroEntrada) -> RespuestaAccion:
    cuenta = buscar_por_codigo(sesion, Cuenta, entrada.cuenta)
    eventos = [(TipoEventoUso.RESPUESTA_REFLEXIVA, None)] if (
        entrada.clasificacion == "ADECUADA" or entrada.ampliada
    ) else []
    return responder_con_eventos(sesion, cuenta, eventos, fecha_accion(entrada))


@usar_contexto
def escribir_entrada(sesion: Session, entrada: EscribirEntradaEntrada) -> RespuestaAccion:
    cuenta = buscar_por_codigo(sesion, Cuenta, entrada.cuenta)
    exigir_estudiante(cuenta)
    pregunta = None
    if entrada.origen == OrigenEntrada.GUIADA:
        pregunta = buscar_por_codigo(sesion, PreguntaDiario, entrada.pregunta)
        exigir_disponible(sesion, cuenta, TipoObjetivo.PREGUNTA_DIARIO, pregunta)
        if sesion.scalar(select(EntradaDiario.id).where(
            EntradaDiario.cuenta_id == cuenta.id, EntradaDiario.origen == OrigenEntrada.GUIADA,
            EntradaDiario.pregunta_id == pregunta.id,
        ).limit(1)) is not None:
            raise ErrorAccion("La pregunta ya tiene una entrada GUIADA de esta cuenta")
    fecha = fecha_accion(entrada)
    registro = EntradaDiario(cuenta_id=cuenta.id, origen=entrada.origen,
                            pregunta_id=None if pregunta is None else pregunta.id,
                            texto=entrada.texto, fecha_hora=fecha)
    sesion.add(registro)
    sesion.flush()
    eventos = [(TipoEventoUso.ESCRIBE_ENTRADA_DIARIO, registro.id)]
    if entrada.origen == OrigenEntrada.LIBRE:
        eventos.append((TipoEventoUso.ESCRIBE_ENTRADA_LIBRE, registro.id))
    return responder_con_eventos(sesion, cuenta, eventos, fecha)


@usar_contexto
def registrar_check_in(sesion: Session, entrada: CheckInEntrada) -> RespuestaAccion:
    cuenta = buscar_por_codigo(sesion, Cuenta, entrada.cuenta)
    exigir_estudiante(cuenta)
    fecha = fecha_accion(entrada)
    if sesion.scalar(select(CheckIn.id).where(
        CheckIn.cuenta_id == cuenta.id, CheckIn.fecha == fecha.date(),
    ).limit(1)) is not None:
        raise ErrorAccion("La cuenta ya tiene un check-in en esta fecha")
    registro = CheckIn(cuenta_id=cuenta.id, fecha=fecha.date(), nivel_seguridad=entrada.nivel_seguridad)
    sesion.add(registro)
    sesion.flush()
    return responder_con_eventos(sesion, cuenta, [(TipoEventoUso.REGISTRA_CHECK_IN, registro.id)], fecha)
