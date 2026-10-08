from sqlalchemy import bindparam, delete, insert, select, update
from sqlalchemy.orm import Session

from app.core.contexto import contexto, usar_contexto
from app.exceptions import ErrorAccion
from app.models import (
    Actividad, ActividadItem, AplicacionActividad, Audiencia, Bloque, Cuenta, EstadoProgreso,
    EstadoRespuestaRegistro, Instrumento, ItemInstrumento, OpcionEscala, ProgresoActividad, RespuestaItem,
    RespuestaRegistro, ResultadoCaso, ResultadoInstrumento, Rol, TipoActividad, TipoEventoUso,
    TipoObjetivo, TipoResultado, Visibilidad,
)
from app.schemas.acciones import (
    CompletarActividadEntrada, ProgresoRespuestas, ReiniciarInstrumentoEntrada,
    ResolverCasoEntrada, ResponderItemsEntrada, RespuestaAccion, RespuestaCompletarActividad,
    RespuestaItemGuardada, RespuestaItemsGuardados, RespuestaReiniciarInstrumento,
    ResultadoAnulado,
)
from app.schemas.actividades import ActividadCuenta, BloqueActividades
from app.services.comun import (
    buscar_por_codigo, exigir_disponible, existe_evento, fecha_accion, responder_con_eventos,
)
from app.services.instrumentos.consultas import actividades_de_aplicacion, seleccionar_aplicacion
from app.services.instrumentos.resultados import generar_resultados_al_completar
from app.services.motor.reglas import objetivo_disponible


@usar_contexto
def completar_progreso(sesion: Session, cuenta: Cuenta, actividad: Actividad):
    datos = contexto(sesion)
    progresos = datos.progresos_de(cuenta.id)
    progreso = progresos.get(actividad.id)
    if progreso is None:
        progreso = ProgresoActividad(cuenta_id=cuenta.id, actividad_id=actividad.id,
                                     estado=EstadoProgreso.COMPLETADA)
        sesion.add(progreso)
        progresos[actividad.id] = progreso
    else:
        progreso.estado = EstadoProgreso.COMPLETADA
    sesion.flush()
    eventos = [(TipoEventoUso.COMPLETA_ACTIVIDAD, actividad.id)]
    actividades = [otra for otra in datos.definiciones.listar(Actividad) if otra.bloque_id == actividad.bloque_id]
    completo = all(otra.id in progresos and progresos[otra.id].estado == EstadoProgreso.COMPLETADA for otra in actividades)
    if completo and not existe_evento(sesion, cuenta, TipoEventoUso.COMPLETA_BLOQUE, actividad.bloque_id):
        eventos.append((TipoEventoUso.COMPLETA_BLOQUE, actividad.bloque_id))
    return progreso, eventos


@usar_contexto
def items_de_actividad(sesion: Session, actividad: Actividad) -> list[ItemInstrumento]:
    definiciones = contexto(sesion).definiciones
    presentaciones = sorted((fila for fila in definiciones.listar(ActividadItem) if fila.actividad_id == actividad.id),
                            key=lambda fila: (fila.orden, definiciones.obtener(ItemInstrumento, fila.item_id).numero))
    return [definiciones.obtener(ItemInstrumento, fila.item_id) for fila in presentaciones]


@usar_contexto
def progreso_de_actividad(sesion: Session, cuenta: Cuenta, actividad: Actividad) -> ProgresoActividad | None:
    return contexto(sesion).progresos_de(cuenta.id).get(actividad.id)


@usar_contexto
def responder_items(sesion: Session, entrada: ResponderItemsEntrada) -> RespuestaItemsGuardados:
    cuenta = buscar_por_codigo(sesion, Cuenta, entrada.cuenta)
    if cuenta.rol != Rol.ESTUDIANTE:
        raise ErrorAccion("Instrumentos no encontrados para esta cuenta", estado_http=404)
    actividad = buscar_por_codigo(sesion, Actividad, entrada.actividad)
    exigir_disponible(sesion, cuenta, TipoObjetivo.ACTIVIDAD, actividad)
    items = {item.codigo: item for item in items_de_actividad(sesion, actividad)}
    if not items:
        raise ErrorAccion("La actividad no presenta ítems de instrumento")
    if sesion.scalar(select(ResultadoInstrumento.id).join(
        AplicacionActividad, AplicacionActividad.aplicacion_id == ResultadoInstrumento.aplicacion_id,
    ).where(ResultadoInstrumento.cuenta_id == cuenta.id, ResultadoInstrumento.anulado_en.is_(None),
            AplicacionActividad.actividad_id == actividad.id).limit(1)) is not None:
        raise ErrorAccion("Las respuestas están fijas: la aplicación tiene un resultado vigente")
    progreso = progreso_de_actividad(sesion, cuenta, actividad)
    definiciones = contexto(sesion).definiciones
    instrumentos_comparacion = {instrumento.id for instrumento in definiciones.listar(Instrumento)
                               if instrumento.tipo_resultado == TipoResultado.COMPARACION}
    opciones = {(opcion.escala_id, opcion.orden): opcion for opcion in definiciones.listar(OpcionEscala)}
    validadas = []
    for respuesta in entrada.respuestas:
        item = items.get(respuesta.item)
        if item is None:
            raise ErrorAccion(f"El ítem {respuesta.item} no se presenta en {actividad.codigo}")
        if progreso is not None and progreso.estado == EstadoProgreso.COMPLETADA and (
            item.instrumento_id in instrumentos_comparacion
        ):
            raise ErrorAccion("Las respuestas están fijas: la actividad sin dimensiones está completada")
        opcion = opciones.get((item.escala_id, respuesta.opcion))
        if opcion is None:
            raise ErrorAccion(f"La opción {respuesta.opcion} no pertenece a la escala de {item.codigo}", estado_http=422)
        validadas.append((item, opcion))
    # Todo el lote se valida antes de crear progreso o modificar respuestas.
    fecha = fecha_accion(entrada)
    if progreso is None:
        progreso = ProgresoActividad(cuenta_id=cuenta.id, actividad_id=actividad.id, estado=EstadoProgreso.EN_CURSO)
        sesion.add(progreso)
        sesion.flush()
    contexto(sesion).progresos_de(cuenta.id)[actividad.id] = progreso
    existentes = {respuesta.item_id: respuesta for respuesta in sesion.scalars(select(RespuestaItem).where(
        RespuestaItem.progreso_id == progreso.id,
    ))}
    nuevas, actualizadas = [], []
    for item, opcion in validadas:
        respuesta = existentes.get(item.id)
        if respuesta is None:
            nuevas.append(dict(progreso_id=progreso.id, item_id=item.id, opcion_id=opcion.id,
                               creada_en=fecha, actualizada_en=fecha))
        else:
            actualizadas.append(dict(respuesta_id=respuesta.id, nueva_opcion=opcion.id, nueva_fecha=fecha))
    if nuevas:
        sesion.execute(insert(RespuestaItem.__table__), nuevas)
    if actualizadas:
        sesion.execute(update(RespuestaItem.__table__).where(RespuestaItem.id == bindparam('respuesta_id')).values(
            opcion_id=bindparam('nueva_opcion'), actualizada_en=bindparam('nueva_fecha'),
        ), actualizadas)
    respondidos = len((set(existentes) | {item.id for item, _ in validadas}) & {item.id for item in items.values()})
    return RespuestaItemsGuardados(
        cuenta=cuenta.codigo, actividad=actividad.codigo,
        respuestas_guardadas=[RespuestaItemGuardada(item=item.codigo, opcion=opcion.orden) for item, opcion in validadas],
        progreso=ProgresoRespuestas(estado=progreso.estado, respondidos=respondidos, total=len(items)),
    )


@usar_contexto
def completar_actividad(sesion: Session, entrada: CompletarActividadEntrada) -> RespuestaCompletarActividad:
    cuenta = buscar_por_codigo(sesion, Cuenta, entrada.cuenta)
    actividad = buscar_por_codigo(sesion, Actividad, entrada.actividad)
    items = items_de_actividad(sesion, actividad)
    items_registro = contexto(sesion).definiciones.items_registro_por_actividad.get(actividad.id, ())
    if (items or items_registro) and cuenta.rol != Rol.ESTUDIANTE:
        mensaje = "Instrumentos no encontrados para esta cuenta" if items else "Registro no encontrado para esta cuenta"
        raise ErrorAccion(mensaje, estado_http=404)
    exigir_disponible(sesion, cuenta, TipoObjetivo.ACTIVIDAD, actividad)
    if actividad.tipo == TipoActividad.CASO:
        raise ErrorAccion("Los casos deben completarse mediante resolver-caso")
    if items:
        progreso = progreso_de_actividad(sesion, cuenta, actividad)
        respondidos = set() if progreso is None else set(sesion.scalars(select(RespuestaItem.item_id).where(
            RespuestaItem.progreso_id == progreso.id,
        )))
        faltantes = [item.codigo for item in items if item.id not in respondidos]
        if faltantes:
            raise ErrorAccion("Faltan ítems por responder", items_faltantes=faltantes)
    obligatorios = [item for item in items_registro if item.obligatorio]
    if obligatorios:
        progreso = progreso_de_actividad(sesion, cuenta, actividad)
        finalizados = set() if progreso is None else set(sesion.scalars(select(RespuestaRegistro.item_registro_id).where(
            RespuestaRegistro.progreso_id == progreso.id,
            RespuestaRegistro.estado == EstadoRespuestaRegistro.FINAL,
        )))
        faltantes = [item.codigo for item in obligatorios if item.id not in finalizados]
        if faltantes:
            raise ErrorAccion("Faltan ítems de registro por finalizar", items_faltantes=faltantes)
    fecha = fecha_accion(entrada)
    _, eventos = completar_progreso(sesion, cuenta, actividad)
    respuesta = responder_con_eventos(sesion, cuenta, eventos, fecha)
    generados = generar_resultados_al_completar(sesion, cuenta, actividad, fecha)
    return RespuestaCompletarActividad(eventos_registrados=respuesta.eventos_registrados,
                                      nuevos_desbloqueos=respuesta.nuevos_desbloqueos,
                                      resultados_generados=generados)


@usar_contexto
def reiniciar_instrumento(sesion: Session, entrada: ReiniciarInstrumentoEntrada) -> RespuestaReiniciarInstrumento:
    cuenta = buscar_por_codigo(sesion, Cuenta, entrada.cuenta)
    if cuenta.rol != Rol.ESTUDIANTE:
        raise ErrorAccion("Instrumentos no encontrados para esta cuenta", estado_http=404)
    instrumento = buscar_por_codigo(sesion, Instrumento, entrada.instrumento)
    try:
        aplicacion = seleccionar_aplicacion(sesion, instrumento, entrada.aplicacion)
    except LookupError as error:
        raise ErrorAccion(str(error), estado_http=404) from error
    except ValueError as error:
        raise ErrorAccion(str(error), estado_http=422) from error
    actividades = actividades_de_aplicacion(sesion, aplicacion)
    progresos = list(sesion.scalars(select(ProgresoActividad).where(
        ProgresoActividad.cuenta_id == cuenta.id,
        ProgresoActividad.actividad_id.in_([actividad.id for actividad in actividades]),
    )))
    filtro_respuestas = (
        RespuestaItem.progreso_id.in_([progreso.id for progreso in progresos]),
        RespuestaItem.item_id.in_(select(ItemInstrumento.id).where(ItemInstrumento.instrumento_id == instrumento.id)),
    )
    resultado = sesion.scalar(select(ResultadoInstrumento).where(
        ResultadoInstrumento.cuenta_id == cuenta.id, ResultadoInstrumento.aplicacion_id == aplicacion.id,
        ResultadoInstrumento.anulado_en.is_(None),
    ))
    tiene_respuestas = sesion.scalar(select(RespuestaItem.id).where(*filtro_respuestas).limit(1)) is not None
    if resultado is None and not tiene_respuestas:
        raise ErrorAccion("Nada que reiniciar")
    fecha = fecha_accion(entrada)
    anulado = None
    if resultado is not None:
        resultado.anulado_en = fecha
        anulado = ResultadoAnulado(instrumento=instrumento.codigo, aplicacion=aplicacion.codigo,
                                  calculado_en=resultado.calculado_en, anulado_en=fecha)
    sesion.execute(delete(RespuestaItem).where(*filtro_respuestas))
    for progreso in progresos:
        progreso.estado = EstadoProgreso.EN_CURSO
    sesion.flush()
    respuesta = responder_con_eventos(sesion, cuenta, [(TipoEventoUso.REINICIA_INSTRUMENTO, instrumento.id)], fecha)
    ids_reiniciados = {progreso.actividad_id for progreso in progresos}
    return RespuestaReiniciarInstrumento(
        cuenta=cuenta.codigo, instrumento=instrumento.codigo, aplicacion=aplicacion.codigo, resultado_anulado=anulado,
        actividades_reiniciadas=[actividad.codigo for actividad in actividades if actividad.id in ids_reiniciados],
        eventos_registrados=respuesta.eventos_registrados, nuevos_desbloqueos=respuesta.nuevos_desbloqueos,
    )


@usar_contexto
def resolver_caso(sesion: Session, entrada: ResolverCasoEntrada) -> RespuestaAccion:
    cuenta = buscar_por_codigo(sesion, Cuenta, entrada.cuenta)
    actividad = buscar_por_codigo(sesion, Actividad, entrada.actividad)
    exigir_disponible(sesion, cuenta, TipoObjetivo.ACTIVIDAD, actividad)
    if actividad.tipo != TipoActividad.CASO:
        raise ErrorAccion("La actividad debe ser de tipo CASO")
    fecha = fecha_accion(entrada)
    progreso, eventos = completar_progreso(sesion, cuenta, actividad)
    sesion.add(ResultadoCaso(progreso_id=progreso.id, puntaje=entrada.puntaje, fecha_hora=fecha))
    if entrada.puntaje >= actividad.puntaje_minimo and not existe_evento(
        sesion, cuenta, TipoEventoUso.SUPERA_CASO, actividad.id,
    ):
        eventos.append((TipoEventoUso.SUPERA_CASO, actividad.id))
    return responder_con_eventos(sesion, cuenta, eventos, fecha)


@usar_contexto
def listar_bloques_cuenta(sesion: Session, cuenta: Cuenta) -> list[BloqueActividades]:
    datos = contexto(sesion)
    progresos = {identificador: progreso.estado for identificador, progreso in datos.progresos_de(cuenta.id).items()}
    bloques = []
    for bloque in sorted((bloque for bloque in datos.definiciones.listar(Bloque)
                         if bloque.audiencia == Audiencia(cuenta.rol.value)), key=lambda bloque: (bloque.numero, bloque.codigo)):
        bloque_disponible = objetivo_disponible(sesion, cuenta, TipoObjetivo.BLOQUE, bloque.id)
        actividades = []
        for actividad in sorted((actividad for actividad in datos.definiciones.listar(Actividad)
                                 if actividad.bloque_id == bloque.id), key=lambda actividad: (actividad.orden, actividad.codigo)):
            disponible = bloque_disponible and objetivo_disponible(
                sesion, cuenta, TipoObjetivo.ACTIVIDAD, actividad.id,
            )
            estado = "BLOQUEADA" if not disponible else (
                progresos[actividad.id].value if actividad.id in progresos else "DISPONIBLE"
            )
            actividades.append(ActividadCuenta(
                codigo=actividad.codigo, titulo=actividad.titulo, tipo=actividad.tipo, orden=actividad.orden,
                contenido=actividad.contenido, visibilidad=actividad.visibilidad,
                visible=actividad.visibilidad == Visibilidad.SIEMPRE or estado != "BLOQUEADA", estado=estado,
            ))
        bloques.append(BloqueActividades(
            codigo=bloque.codigo, nombre=bloque.nombre, numero=bloque.numero, espacio=bloque.espacio,
            estado="DISPONIBLE" if bloque_disponible else "BLOQUEADA", actividades=actividades,
        ))
    return bloques
