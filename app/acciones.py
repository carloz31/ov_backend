"""Acciones de la sección 5. El llamador controla una sola transacción."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import bindparam, delete, insert, select, update
from sqlalchemy.orm import Session

from app.consultas import progreso_objetivo
from app.contexto_consultas import contexto, usar_contexto
from app.definiciones import MODELOS_FIJOS
from app.consultas_instrumentos import actividades_de_aplicacion, seleccionar_aplicacion
from app.models import (
    Actividad, ActividadItem, AplicacionActividad, Carrera, CheckIn, Conversacion, ConversacionVinculo, Cuenta,
    EntradaDiario, Entrevista, EntrevistaAutor, EstadoProgreso, EventoUso,
    Desbloqueo, Dimension, Instrumento, ItemInstrumento, OpcionEscala, OrigenEntrada, PreguntaDiario, ProgresoActividad,
    RespuestaItem, RespuestaRegistro, EstadoRespuestaRegistro, ResultadoCaso, ResultadoInstrumento, Rol,
    TipoActividad, TipoEventoUso, TipoObjetivo, TipoResultado, VinculoFamiliar,
)
from app.motor import objetivo_disponible, registrar_eventos
from app.referencias import MODELOS_REFERENCIA, referencia_legible
from app.resultados_instrumentos import generar_resultados_al_completar
from app.schemas import (
    AccionCuenta, CheckInEntrada, CompletarActividadEntrada, CompletarConversacionEntrada,
    DesbloqueoNuevo, EscribirCartaEntrada, EscribirEntradaEntrada, EventoEntrada,
    EventoLegible, FechaAccion, ProgresoObjetivo, PublicarEntrevistaEntrada,
    ProgresoRespuestas, ResponderItemsEntrada, ResponderRegistroEntrada, ResolverCasoEntrada,
    RespuestaAccion, RespuestaAgrupada, RespuestaCompletarActividad, RespuestaItemGuardada,
    RespuestaItemsGuardados, VerCarreraEntrada, ReiniciarInstrumentoEntrada,
    RespuestaReiniciarInstrumento, ResultadoAnulado,
)


class ErrorAccion(Exception):
    def __init__(self, mensaje: str, estado_http: int = 409, progreso: ProgresoObjetivo | None = None,
                 items_faltantes: list[str] | None = None):
        super().__init__(mensaje)
        self.estado_http = estado_http
        self.progreso = progreso
        self.items_faltantes = items_faltantes


def fecha_accion(entrada: FechaAccion) -> datetime:
    fecha = entrada.fecha_hora or datetime.now(timezone(timedelta(hours=-5)))
    # Se conserva el calendario simulado, como en los conteos de la fase 2.
    return fecha.replace(tzinfo=None)


@usar_contexto
def buscar_por_codigo(sesion: Session, modelo, codigo: str):
    entidad = (contexto(sesion).definiciones.por_codigo(modelo, codigo) if modelo in MODELOS_FIJOS
               else sesion.scalar(select(modelo).where(modelo.codigo == codigo)))
    if entidad is None:
        raise ErrorAccion("Cuenta o referencia no encontrada", estado_http=404)
    return entidad


def exigir_estudiante(cuenta: Cuenta) -> None:
    if cuenta.rol != Rol.ESTUDIANTE:
        raise ErrorAccion("Esta acción solo está permitida para estudiantes")


def exigir_disponible(sesion: Session, cuenta: Cuenta, tipo: TipoObjetivo, entidad=None) -> None:
    identificador = None if entidad is None else entidad.id
    if objetivo_disponible(sesion, cuenta, tipo, identificador):
        return
    codigo = "-" if entidad is None else entidad.codigo
    try:
        progreso = progreso_objetivo(sesion, cuenta, tipo, codigo)
    except (LookupError, PermissionError):
        progreso = None
    raise ErrorAccion("El objetivo no está disponible para esta cuenta", progreso=progreso)


@usar_contexto
def existe_evento(sesion: Session, cuenta: Cuenta, tipo: TipoEventoUso, referencia: int) -> bool:
    from app.models import TipoConteo
    return contexto(sesion).contar(cuenta.id, tipo, referencia, TipoConteo.EVENTOS) > 0


@usar_contexto
def responder_con_eventos(
    sesion: Session, cuenta: Cuenta, eventos: list[tuple[TipoEventoUso, int | None]], fecha: datetime,
) -> RespuestaAccion:
    nuevos = registrar_eventos(sesion, cuenta, eventos, fecha)
    # Permite omitir solo el evaluador ausente, conservando referencias null en la API.
    nuevos = [nuevo if nuevo.evaluador_especial is not None else DesbloqueoNuevo.model_validate(
        nuevo.model_dump(exclude={"evaluador_especial"}),
    ) for nuevo in nuevos]
    return RespuestaAccion(
        eventos_registrados=[EventoLegible(
            tipo=tipo, referencia=referencia_legible(sesion, tipo, referencia), fecha_hora=fecha,
        ) for tipo, referencia in eventos],
        nuevos_desbloqueos=nuevos,
    )


@usar_contexto
def responder_varias_cuentas(sesion, cuentas, eventos_por_cuenta, fecha):
    filas = [dict(cuenta_id=cuenta.id, tipo=tipo, id_referencia=referencia, fecha_hora=fecha)
             for cuenta in cuentas for tipo, referencia in eventos_por_cuenta[cuenta.id]]
    if not filas:
        return RespuestaAgrupada(por_cuenta={cuenta.codigo: responder_con_eventos(sesion, cuenta, [], fecha) for cuenta in cuentas})
    sesion.flush()
    sesion.execute(insert(EventoUso.__table__), filas)
    datos = contexto(sesion)
    ids_cuentas = [cuenta.id for cuenta in cuentas]
    for cuenta_id in ids_cuentas:
        datos.invalidar_eventos(cuenta_id)
    datos.cargar_conteos(ids_cuentas)
    datos.cargar_desbloqueos(ids_cuentas)
    sesion.info['lote_eventos'] = set(ids_cuentas)
    sesion.info['lote_desbloqueos'] = []
    try:
        respuestas = {cuenta.codigo: responder_con_eventos(sesion, cuenta, eventos_por_cuenta[cuenta.id], fecha)
                      for cuenta in cuentas}
        pendientes = sesion.info['lote_desbloqueos']
        if pendientes:
            sesion.execute(insert(Desbloqueo.__table__), pendientes)
        return RespuestaAgrupada(por_cuenta=respuestas)
    finally:
        sesion.info.pop('lote_eventos', None)
        sesion.info.pop('lote_desbloqueos', None)


@usar_contexto
def ingresar(sesion: Session, entrada: AccionCuenta) -> RespuestaAccion:
    cuenta = buscar_por_codigo(sesion, Cuenta, entrada.cuenta)
    return responder_con_eventos(sesion, cuenta, [(TipoEventoUso.INGRESO, None)], fecha_accion(entrada))


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


@usar_contexto
def ver_carrera(sesion: Session, entrada: VerCarreraEntrada) -> RespuestaAccion:
    cuenta = buscar_por_codigo(sesion, Cuenta, entrada.cuenta)
    carrera = buscar_por_codigo(sesion, Carrera, entrada.carrera)
    return responder_con_eventos(sesion, cuenta, [(TipoEventoUso.VISTA_CARRERA, carrera.id)], fecha_accion(entrada))


@usar_contexto
def publicar_entrevista(sesion: Session, entrada: PublicarEntrevistaEntrada) -> RespuestaAgrupada:
    por_codigo = {cuenta.codigo: cuenta for cuenta in sesion.scalars(select(Cuenta).where(Cuenta.codigo.in_(entrada.autores)))}
    if any(codigo not in por_codigo for codigo in entrada.autores):
        raise ErrorAccion("Cuenta o referencia no encontrada", estado_http=404)
    cuentas = [por_codigo[codigo] for codigo in entrada.autores]
    for cuenta in cuentas:
        exigir_estudiante(cuenta)
    fecha = fecha_accion(entrada)
    entrevista = Entrevista(codigo=f"ENT-{uuid4().hex}", resumen=entrada.resumen, fecha_hora=fecha)
    sesion.add(entrevista)
    sesion.flush()
    sesion.execute(insert(EntrevistaAutor.__table__), [dict(entrevista_id=entrevista.id, cuenta_id=cuenta.id) for cuenta in cuentas])
    return responder_varias_cuentas(sesion, cuentas, {
        cuenta.id: [(TipoEventoUso.PUBLICA_ENTREVISTA, entrevista.id)] for cuenta in cuentas
    }, fecha)


def vinculo_de_cuenta(sesion: Session, cuenta: Cuenta) -> VinculoFamiliar:
    filtro = VinculoFamiliar.estudiante_id == cuenta.id if cuenta.rol == Rol.ESTUDIANTE else (
        VinculoFamiliar.apoderado_id == cuenta.id
    )
    vinculo = sesion.scalar(select(VinculoFamiliar).where(filtro).order_by(VinculoFamiliar.codigo).limit(1))
    if vinculo is None:
        raise ErrorAccion("La cuenta no pertenece a un vínculo familiar")
    return vinculo


@usar_contexto
def escribir_carta(sesion: Session, entrada: EscribirCartaEntrada) -> RespuestaAccion:
    cuenta = buscar_por_codigo(sesion, Cuenta, entrada.cuenta)
    vinculo = vinculo_de_cuenta(sesion, cuenta)
    columna = "carta_estudiante" if cuenta.rol == Rol.ESTUDIANTE else "carta_apoderado"
    primera = getattr(vinculo, columna) is None and not existe_evento(
        sesion, cuenta, TipoEventoUso.ESCRIBE_CARTA, vinculo.id,
    )
    setattr(vinculo, columna, entrada.texto)
    eventos = [(TipoEventoUso.ESCRIBE_CARTA, vinculo.id)] if primera else []
    return responder_con_eventos(sesion, cuenta, eventos, fecha_accion(entrada))


@usar_contexto
def completar_conversacion(sesion: Session, entrada: CompletarConversacionEntrada) -> RespuestaAgrupada:
    cuenta = buscar_por_codigo(sesion, Cuenta, entrada.cuenta)
    conversacion = buscar_por_codigo(sesion, Conversacion, entrada.conversacion)
    vinculo = vinculo_de_cuenta(sesion, cuenta)
    contexto(sesion).cargar_desbloqueos([vinculo.estudiante_id, vinculo.apoderado_id])
    exigir_disponible(sesion, cuenta, TipoObjetivo.CONVERSACIONES)
    ids_cuentas = (vinculo.estudiante_id, vinculo.apoderado_id)
    por_id = {otra.id: otra for otra in sesion.scalars(select(Cuenta).where(Cuenta.id.in_(ids_cuentas)))}
    cuentas = [por_id[identificador] for identificador in ids_cuentas]
    contexto(sesion).cargar_desbloqueos(ids_cuentas)
    registro = sesion.scalar(select(ConversacionVinculo).where(
        ConversacionVinculo.vinculo_id == vinculo.id, ConversacionVinculo.conversacion_id == conversacion.id,
    ))
    primera = registro is None or not registro.conversado
    fecha = fecha_accion(entrada)
    if primera:
        if registro is None:
            registro = ConversacionVinculo(vinculo_id=vinculo.id, conversacion_id=conversacion.id)
            sesion.add(registro)
        registro.conversado = True
        registro.conversado_en = fecha
    if primera:
        contexto(sesion).cargar_conteos(ids_cuentas)
    eventos_por_cuenta = {
        otra.id: [(TipoEventoUso.COMPLETA_CONVERSACION, conversacion.id)] if primera and not existe_evento(
            sesion, otra, TipoEventoUso.COMPLETA_CONVERSACION, conversacion.id,
        ) else [] for otra in cuentas
    }
    return responder_varias_cuentas(sesion, cuentas, eventos_por_cuenta, fecha)


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
