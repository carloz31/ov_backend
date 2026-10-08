"""Conversaciones de registro; lectura y escritura separadas de la evaluación."""

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, insert, select, update

from app.core.contexto import contexto, usar_contexto
from app.core.parametros import MAXIMO_SEGUIMIENTOS_POR_ITEM
from app.exceptions import ErrorAccion
from app.models import (
    Actividad, Bloque, Cuenta, EstadoProgreso, EvaluacionRespuesta, ProgresoActividad,
    RespuestaRegistro, Rol, TipoEventoUso, TipoObjetivo, TurnoSeguimiento,
)
from app.models.enums import ClasificacionRespuesta, EstadoRespuestaRegistro, OrigenEvaluacion
from app.schemas.registro import (
    EstadoItemRegistro, MensajePreguntaRegistro, MensajeRespuestaRegistro, PosicionGuardada,
    RespuestaEnvioRegistro,
)
from app.services.comun import (
    buscar_por_codigo, exigir_disponible, fecha_accion, responder_con_eventos,
)
from app.services.registro.evaluacion import (
    ContextoEvaluacion, ConversacionEvaluacion, CriterioEvaluacion, RespuestaAnterior,
    TurnoEvaluacion, evaluar_respuesta,
)


def validar_registro(sesion, codigo_actividad, codigo_cuenta=None, disponible=False):
    actividad = buscar_por_codigo(sesion, Actividad, codigo_actividad)
    definiciones = contexto(sesion).definiciones
    bloque = definiciones.obtener(Bloque, actividad.bloque_id)
    if bloque.audiencia.value != Rol.ESTUDIANTE.value:
        raise ErrorAccion("Actividad de estudiante no encontrada", estado_http=404)
    cuenta = None
    if codigo_cuenta is not None:
        cuenta = buscar_por_codigo(sesion, Cuenta, codigo_cuenta)
        if cuenta.rol != Rol.ESTUDIANTE:
            raise ErrorAccion("Registro no encontrado para esta cuenta", estado_http=404)
        if disponible:
            exigir_disponible(sesion, cuenta, TipoObjetivo.ACTIVIDAD, actividad)
    return cuenta, actividad, definiciones.items_registro_por_actividad.get(actividad.id, ())


def validar_item(items, codigo):
    item = next((item for item in items if item.codigo == codigo), None)
    if item is None:
        raise ErrorAccion("El ítem no pertenece a esta actividad")
    return item


@dataclass(frozen=True, slots=True)
class TurnoLeido:
    id: int
    orden: int
    pregunta: str
    criterios_objetivo: tuple[str, ...]
    respuesta: str | None
    respondido_en: datetime | None


@dataclass(frozen=True, slots=True)
class RegistroLeido:
    progreso: ProgresoActividad | None
    respuestas: dict[int, RespuestaRegistro]
    turnos: dict[int, tuple[TurnoLeido, ...]]
    origenes_iniciales: dict[int, OrigenEvaluacion]


def leer_registro(sesion, cuenta, actividad):
    # Una lectura para progreso, respuestas, turnos y el origen de su primer envío.
    filas = sesion.execute(select(ProgresoActividad, RespuestaRegistro, TurnoSeguimiento,
        EvaluacionRespuesta.origen).outerjoin(RespuestaRegistro,
            RespuestaRegistro.progreso_id == ProgresoActividad.id).outerjoin(TurnoSeguimiento,
            TurnoSeguimiento.respuesta_id == RespuestaRegistro.id).outerjoin(EvaluacionRespuesta, and_(
            EvaluacionRespuesta.respuesta_id == RespuestaRegistro.id, EvaluacionRespuesta.numero == 1,
        )).where(ProgresoActividad.cuenta_id == cuenta.id,
                 ProgresoActividad.actividad_id == actividad.id).order_by(TurnoSeguimiento.orden)).all()
    respuestas, turnos, origenes = {}, {}, {}
    for _, respuesta, turno, origen in filas:
        if respuesta is None:
            continue
        respuestas[respuesta.item_registro_id] = respuesta
        if origen is not None:
            origenes[respuesta.id] = origen
        if turno is not None:
            turnos.setdefault(respuesta.id, {})[turno.id] = TurnoLeido(
                turno.id, turno.orden, turno.pregunta, tuple(turno.criterios_objetivo), turno.respuesta, turno.respondido_en)
    return RegistroLeido(filas[0][0] if filas else None, respuestas,
                        {identificador: tuple(filas.values()) for identificador, filas in turnos.items()}, origenes)


def conversacion_publica(texto_inicial, turnos):
    mensajes = [MensajeRespuestaRegistro(tipo='respuesta', texto=texto_inicial)]
    for turno in turnos:
        mensajes.append(MensajePreguntaRegistro(tipo='pregunta', orden=turno.orden, texto=turno.pregunta))
        if turno.respuesta is not None:
            mensajes.append(MensajeRespuestaRegistro(tipo='respuesta', orden=turno.orden, texto=turno.respuesta,
                                                     borrador=turno.respondido_en is None))
    return mensajes


def conversacion_evaluable(texto_inicial, turnos):
    return ConversacionEvaluacion(texto_inicial, tuple(TurnoEvaluacion(t.pregunta,
        t.respuesta if t.respondido_en is not None else None) for t in turnos))


def crear_progreso(sesion, cuenta, actividad):
    progreso = ProgresoActividad(cuenta_id=cuenta.id, actividad_id=actividad.id, estado=EstadoProgreso.EN_CURSO)
    sesion.add(progreso)
    sesion.flush()
    return progreso


def marca_actualizacion(anterior=None):
    """Avanza aunque la fecha simulada o el reloj retrocedan."""
    ahora = datetime.now(timezone.utc).replace(tzinfo=None)
    return max(ahora, anterior + timedelta(microseconds=1)) if anterior is not None else ahora


def comprobar_cambio(sesion, respuesta, valores):
    resultado = sesion.execute(update(RespuestaRegistro.__table__).where(
        RespuestaRegistro.id == respuesta.id, RespuestaRegistro.estado == respuesta.estado,
        RespuestaRegistro.actualizada_en == respuesta.actualizada_en).values(**valores))
    if resultado.rowcount != 1:
        raise ErrorAccion("La respuesta cambió durante el envío; vuelve a intentarlo")


def turno_pendiente(turnos):
    if not turnos or turnos[-1].respondido_en is not None:
        raise ErrorAccion("No hay una pregunta de seguimiento pendiente")
    return turnos[-1]


@usar_contexto
def guardar_posicion(sesion, entrada, posiciones):
    cuenta, actividad, _ = validar_registro(sesion, entrada.actividad, entrada.cuenta, disponible=True)
    if entrada.posicion not in posiciones.get(actividad.codigo, ()):
        raise ErrorAccion("La posición no pertenece a los momentos de la actividad", estado_http=422)
    progreso = contexto(sesion).progresos_de(cuenta.id).get(actividad.id)
    if progreso is None:
        progreso = crear_progreso(sesion, cuenta, actividad)
    progreso.posicion = entrada.posicion
    return PosicionGuardada(posicion=entrada.posicion, estado=progreso.estado)


@usar_contexto
def guardar_borrador(sesion, entrada):
    cuenta, actividad, items = validar_registro(sesion, entrada.actividad, entrada.cuenta, disponible=True)
    item = validar_item(items, entrada.item)
    registro = leer_registro(sesion, cuenta, actividad)
    respuesta = registro.respuestas.get(item.id)
    if respuesta is not None and respuesta.estado == EstadoRespuestaRegistro.FINAL:
        raise ErrorAccion("La respuesta está finalizada; usa enviar o responder seguimiento para editarla")
    marca = marca_actualizacion(respuesta.actualizada_en if respuesta is not None else None)
    if respuesta is None:
        progreso = registro.progreso or crear_progreso(sesion, cuenta, actividad)
        sesion.execute(insert(RespuestaRegistro.__table__), dict(progreso_id=progreso.id, item_registro_id=item.id,
            texto_inicial=entrada.texto, estado=EstadoRespuestaRegistro.BORRADOR, creada_en=fecha_accion(entrada),
            actualizada_en=marca, ampliada=False))
        estado = EstadoRespuestaRegistro.BORRADOR
    else:
        estado = respuesta.estado
        valores = dict(actualizada_en=marca)
        if estado == EstadoRespuestaRegistro.BORRADOR:
            valores['texto_inicial'] = entrada.texto
        comprobar_cambio(sesion, respuesta, valores)
        if estado == EstadoRespuestaRegistro.PENDIENTE_SEGUIMIENTO:
            turno = turno_pendiente(registro.turnos.get(respuesta.id, ()))
            sesion.execute(update(TurnoSeguimiento.__table__).where(TurnoSeguimiento.id == turno.id)
                           .values(respuesta=entrada.texto))
    return EstadoItemRegistro(item=item.codigo, estado=estado)


@dataclass(frozen=True, slots=True)
class LecturaEnvio:
    respuesta_id: int | None
    estado: EstadoRespuestaRegistro | None
    actualizada_en: datetime | None
    contexto: ContextoEvaluacion
    min_caracteres: int
    repregunta_generica: str
    seguimiento: bool
    orden: int | None
    requiere_evaluacion: bool


@usar_contexto
def preparar_envio(sesion, entrada, seguimiento=False):
    if not entrada.texto.strip():
        raise ErrorAccion("La respuesta no puede estar vacía", estado_http=422)
    cuenta, actividad, items = validar_registro(sesion, entrada.actividad, entrada.cuenta, disponible=True)
    item = validar_item(items, entrada.item)
    registro = leer_registro(sesion, cuenta, actividad)
    respuesta = registro.respuestas.get(item.id)
    estado = respuesta.estado if respuesta is not None else None
    turnos = registro.turnos.get(respuesta.id, ()) if respuesta is not None else ()
    orden = None
    requiere_evaluacion = estado != EstadoRespuestaRegistro.FINAL
    criterios = contexto(sesion).definiciones.criterios_por_item_registro.get(item.id, ())
    faltantes = tuple(c.codigo for c in criterios)
    if seguimiento:
        if estado == EstadoRespuestaRegistro.FINAL:
            if entrada.orden is None:
                raise ErrorAccion("Indica el orden del turno que quieres editar", estado_http=422)
            turno = next((t for t in turnos if t.orden == entrada.orden and t.respondido_en is not None), None)
            if turno is None:
                raise ErrorAccion("Solo se puede editar un turno ya respondido")
        elif estado == EstadoRespuestaRegistro.PENDIENTE_SEGUIMIENTO:
            if entrada.orden is not None:
                raise ErrorAccion("El orden solo se indica al editar una respuesta finalizada", estado_http=422)
            turno = turno_pendiente(turnos)
            requiere_evaluacion = registro.origenes_iniciales.get(respuesta.id) != OrigenEvaluacion.RESPALDO_LONGITUD
        else:
            raise ErrorAccion("Solo se puede responder un seguimiento pendiente o editar un turno finalizado")
        orden, faltantes = turno.orden, turno.criterios_objetivo
        conversacion = conversacion_evaluable(respuesta.texto_inicial,
            tuple(replace(t, respuesta=entrada.texto, respondido_en=fecha_accion(entrada)) if t.orden == orden else t
                  for t in turnos))
    else:
        if estado == EstadoRespuestaRegistro.PENDIENTE_SEGUIMIENTO:
            raise ErrorAccion("Responde la pregunta pendiente con responder seguimiento")
        conversacion = conversacion_evaluable(entrada.texto, turnos)
    anteriores = tuple(RespuestaAnterior(otro.consigna,
        conversacion_evaluable(registro.respuestas[otro.id].texto_inicial,
            registro.turnos.get(registro.respuestas[otro.id].id, ()))) for otro in items
        if otro.id != item.id and otro.id in registro.respuestas
        and registro.respuestas[otro.id].estado == EstadoRespuestaRegistro.FINAL)
    return LecturaEnvio(respuesta.id if respuesta is not None else None, estado,
        respuesta.actualizada_en if respuesta is not None else None,
        ContextoEvaluacion(actividad.titulo, item.consigna,
            tuple(CriterioEvaluacion(c.codigo, c.descripcion) for c in criterios), anteriores, conversacion, faltantes),
        item.min_caracteres, item.repregunta_generica, seguimiento, orden, requiere_evaluacion)


@usar_contexto
def persistir_envio(sesion, entrada, lectura, evaluacion):
    # Nuevos contexto de consultas y entidades: no reutilizar lecturas de fase 1.
    cuenta, actividad, items = validar_registro(sesion, entrada.actividad, entrada.cuenta, disponible=True)
    item = validar_item(items, entrada.item)
    registro = leer_registro(sesion, cuenta, actividad)
    respuesta = registro.respuestas.get(item.id)
    actual = (respuesta.id, respuesta.estado, respuesta.actualizada_en) if respuesta is not None else (None, None, None)
    if actual != (lectura.respuesta_id, lectura.estado, lectura.actualizada_en):
        raise ErrorAccion("La respuesta cambió durante la evaluación; vuelve a intentarlo")
    fecha = fecha_accion(entrada)
    turnos = registro.turnos.get(respuesta.id, ()) if respuesta is not None else ()
    edicion = lectura.estado == EstadoRespuestaRegistro.FINAL
    pendiente = (not edicion and evaluacion is not None and evaluacion.clasificacion == ClasificacionRespuesta.VAGA
                 and not evaluacion.requiere_atencion and len(turnos) < MAXIMO_SEGUIMIENTOS_POR_ITEM)
    estado = EstadoRespuestaRegistro.PENDIENTE_SEGUIMIENTO if pendiente else EstadoRespuestaRegistro.FINAL
    valores = dict(estado=estado, actualizada_en=marca_actualizacion(lectura.actualizada_en))
    if not lectura.seguimiento:
        valores['texto_inicial'] = entrada.texto
        if not edicion:
            valores['clasificacion_inicial'] = evaluacion.clasificacion
    elif not edicion:
        valores['ampliada'] = True
    if respuesta is None:
        progreso = registro.progreso or crear_progreso(sesion, cuenta, actividad)
        respuesta_id = sesion.execute(insert(RespuestaRegistro.__table__).values(progreso_id=progreso.id,
            item_registro_id=item.id, creada_en=fecha, ampliada=False, **valores)
            .returning(RespuestaRegistro.id)).scalar_one()
    else:
        comprobar_cambio(sesion, respuesta, valores)
        respuesta_id = respuesta.id
    if lectura.seguimiento:
        turno = next(t for t in turnos if t.orden == lectura.orden)
        cambios = dict(respuesta=entrada.texto)
        if not edicion:
            cambios['respondido_en'] = fecha
        sesion.execute(update(TurnoSeguimiento.__table__).where(TurnoSeguimiento.id == turno.id).values(**cambios))
        turnos = tuple(replace(t, respuesta=entrada.texto, respondido_en=t.respondido_en if edicion else fecha)
                       if t.id == turno.id else t for t in turnos)
    if pendiente:
        orden = len(turnos) + 1
        turno_id = sesion.execute(insert(TurnoSeguimiento.__table__).values(respuesta_id=respuesta_id, orden=orden,
            pregunta=evaluacion.pregunta, criterios_objetivo=list(evaluacion.criterios_faltantes), creado_en=fecha)
            .returning(TurnoSeguimiento.id)).scalar_one()
        turnos += (TurnoLeido(turno_id, orden, evaluacion.pregunta, evaluacion.criterios_faltantes, None, None),)
    if evaluacion is not None:
        sesion.execute(insert(EvaluacionRespuesta.__table__), dict(respuesta_id=respuesta_id,
            numero=lectura.orden + 1 if lectura.seguimiento else 1, origen=evaluacion.origen,
            clasificacion=evaluacion.clasificacion, criterios_faltantes=list(evaluacion.criterios_faltantes),
            pregunta_generada=evaluacion.pregunta, requiere_atencion=evaluacion.requiere_atencion,
            modelo=evaluacion.modelo, version_prompt=evaluacion.version_prompt, latencia_ms=evaluacion.latencia_ms,
            error=evaluacion.error, texto_evaluado=evaluacion.texto_evaluado, fecha_hora=fecha))
    clasificacion_inicial = valores.get('clasificacion_inicial', respuesta.clasificacion_inicial if respuesta else None)
    ampliada = valores.get('ampliada', respuesta.ampliada if respuesta else False)
    reflexiva = not edicion and estado == EstadoRespuestaRegistro.FINAL and (
        clasificacion_inicial == ClasificacionRespuesta.ADECUADA or ampliada)
    eventos = responder_con_eventos(sesion, cuenta, [(TipoEventoUso.RESPUESTA_REFLEXIVA, None)] if reflexiva else [], fecha)
    texto_inicial = entrada.texto if not lectura.seguimiento else respuesta.texto_inicial
    return RespuestaEnvioRegistro(item=item.codigo, estado=estado, conversacion=conversacion_publica(texto_inicial, turnos),
                                 **eventos.model_dump(exclude_unset=True))


def enviar(fabrica_sesiones, entrada, evaluador, *, seguimiento=False, **opciones_evaluacion):
    with fabrica_sesiones.begin() as sesion:
        lectura = preparar_envio(sesion, entrada, seguimiento)
    evaluacion = evaluar_respuesta(lectura.contexto, lectura.min_caracteres, lectura.repregunta_generica,
        evaluador, **opciones_evaluacion) if lectura.requiere_evaluacion else None
    with fabrica_sesiones.begin() as sesion:
        return persistir_envio(sesion, entrada, lectura, evaluacion)


@usar_contexto
def continuar_sin_responder(sesion, entrada):
    cuenta, actividad, items = validar_registro(sesion, entrada.actividad, entrada.cuenta, disponible=True)
    item = validar_item(items, entrada.item)
    registro = leer_registro(sesion, cuenta, actividad)
    respuesta = registro.respuestas.get(item.id)
    if respuesta is None or respuesta.estado != EstadoRespuestaRegistro.PENDIENTE_SEGUIMIENTO:
        raise ErrorAccion("Solo se puede continuar una respuesta con un seguimiento pendiente")
    turnos = registro.turnos.get(respuesta.id, ())
    turno = turno_pendiente(turnos)
    comprobar_cambio(sesion, respuesta, dict(estado=EstadoRespuestaRegistro.FINAL,
                                            actualizada_en=marca_actualizacion(respuesta.actualizada_en)))
    if turno.respuesta is not None:
        sesion.execute(update(TurnoSeguimiento.__table__).where(TurnoSeguimiento.id == turno.id).values(respuesta=None))
        turnos = tuple(replace(t, respuesta=None) if t.id == turno.id else t for t in turnos)
    reflexiva = respuesta.clasificacion_inicial == ClasificacionRespuesta.ADECUADA or respuesta.ampliada
    eventos = responder_con_eventos(sesion, cuenta, [(TipoEventoUso.RESPUESTA_REFLEXIVA, None)] if reflexiva else [],
                                   fecha_accion(entrada))
    return RespuestaEnvioRegistro(item=item.codigo, estado=EstadoRespuestaRegistro.FINAL,
        conversacion=conversacion_publica(respuesta.texto_inicial, turnos), **eventos.model_dump(exclude_unset=True))
