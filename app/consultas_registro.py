"""Lecturas agrupadas del registro y su historial técnico."""

from sqlalchemy import select

from app.acciones_registro import conversacion_publica, leer_registro, validar_registro
from app.contexto_consultas import usar_contexto
from app.models import EvaluacionRespuesta, ProgresoActividad, RespuestaRegistro
from app.schemas_registro import (
    EvaluacionRegistroDemo, ItemRegistroPublico, RegistroConsultado, RespuestaRegistroPublica,
)


@usar_contexto
def consultar_items(sesion, actividad):
    _, _, items = validar_registro(sesion, actividad)
    return [ItemRegistroPublico(**{campo: getattr(item, campo) for campo in ItemRegistroPublico.model_fields})
            for item in items]


@usar_contexto
def consultar_registro(sesion, cuenta, actividad):
    cuenta, actividad, items = validar_registro(sesion, actividad, cuenta)
    registro = leer_registro(sesion, cuenta, actividad)
    progreso, respuestas = registro.progreso, registro.respuestas
    return RegistroConsultado(posicion=progreso.posicion if progreso is not None else None,
        estado=progreso.estado if progreso is not None else None,
        respuestas=[RespuestaRegistroPublica(item=item.codigo, estado=respuestas[item.id].estado,
            conversacion=conversacion_publica(respuestas[item.id].texto_inicial,
                registro.turnos.get(respuestas[item.id].id, ())))
            for item in items if item.id in respuestas])


@usar_contexto
def consultar_evaluaciones(sesion, cuenta, actividad):
    cuenta, actividad, items = validar_registro(sesion, actividad, cuenta)
    codigos = {item.id: item.codigo for item in items}
    filas = sesion.execute(select(EvaluacionRespuesta, RespuestaRegistro.item_registro_id).join(
        RespuestaRegistro, RespuestaRegistro.id == EvaluacionRespuesta.respuesta_id).join(
        ProgresoActividad, ProgresoActividad.id == RespuestaRegistro.progreso_id).where(
        ProgresoActividad.cuenta_id == cuenta.id, ProgresoActividad.actividad_id == actividad.id
    ).order_by(EvaluacionRespuesta.id))
    return [EvaluacionRegistroDemo(item=codigos[item_id], **{
        campo: getattr(evaluacion, campo)
        for campo in EvaluacionRegistroDemo.model_fields if campo != 'item'
    }) for evaluacion, item_id in filas]
