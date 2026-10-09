"""Lecturas agrupadas del registro."""


from app.core.contexto import usar_contexto
from app.schemas.registro import (
    ItemRegistroPublico, RegistroConsultado, RespuestaRegistroPublica,
)
from app.services.registro.acciones import conversacion_publica, leer_registro, validar_registro


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
