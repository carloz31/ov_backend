"""Consultas de instrumentos: derivan vistas sin modificar respuestas ni resultados."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.contexto import contexto, usar_contexto
from app.core.definiciones import MODELOS_FIJOS
from app.core.parametros import DECIMALES_CORRELACION
from app.exceptions import ConsultaPendiente
from app.models import (
    Actividad, ActividadItem, Aplicacion, AplicacionActividad, Audiencia, Bloque, Carrera,
    CarreraOcupacion, Coincidencia, Cuenta, Dimension, EscalaRespuesta, EstadoProgreso,
    FamiliaCarrera, Instrumento, ItemInstrumento, MomentoAplicacion, Ocupacion, OpcionEscala,
    ProgresoActividad, RespuestaItem, ResultadoDimension, ResultadoInstrumento, Rol, TipoResultado,
)
from app.schemas.instrumentos import (
    ActividadPublica, AplicacionPublica, AvanceAplicacion, AvanceInstrumento, CarreraRecomendada,
    CodigoInteresPublico, CoincidenciaPublica, ComparacionAutopercepcion, ComparacionItem,
    ConteoAvance, ConteoItems, DimensionPublica, DimensionResultado, EscalaPublica,
    InstrumentoPublico, ItemPublico, OpcionPublica, RespuestaPublica, RespuestasActividad,
    ResultadoHistorico, ResultadoPublico,
)
from app.services.instrumentos.calculo import (
    DimensionCalculada, calcular_codigo_interes, calcular_dimensiones_destacadas,
)


@usar_contexto
def entidad_por_codigo(sesion: Session, modelo, codigo: str):
    entidad = (contexto(sesion).definiciones.por_codigo(modelo, codigo) if modelo in MODELOS_FIJOS
               else sesion.scalar(select(modelo).where(modelo.codigo == codigo)))
    if entidad is None:
        raise LookupError("Referencia no encontrada")
    return entidad


@usar_contexto
def cuenta_estudiante(sesion: Session, codigo: str) -> Cuenta:
    cuenta = entidad_por_codigo(sesion, Cuenta, codigo)
    if cuenta.rol != Rol.ESTUDIANTE:
        raise LookupError("Instrumentos no encontrados para esta cuenta")
    return cuenta


@usar_contexto
def actividad_estudiante(sesion: Session, codigo: str) -> Actividad:
    actividad = entidad_por_codigo(sesion, Actividad, codigo)
    if contexto(sesion).definiciones.obtener(Bloque, actividad.bloque_id).audiencia != Audiencia.ESTUDIANTE:
        raise LookupError("Actividad no encontrada para estudiantes")
    return actividad


@usar_contexto
def aplicaciones_de_instrumento(sesion: Session, instrumento: Instrumento) -> list[Aplicacion]:
    return sorted((aplicacion for aplicacion in contexto(sesion).definiciones.listar(Aplicacion)
                   if aplicacion.instrumento_id == instrumento.id), key=lambda aplicacion: aplicacion.codigo)


@usar_contexto
def actividades_de_aplicacion(sesion: Session, aplicacion: Aplicacion) -> list[Actividad]:
    definiciones = contexto(sesion).definiciones
    identificadores = {fila.actividad_id for fila in definiciones.listar(AplicacionActividad) if fila.aplicacion_id == aplicacion.id}
    return sorted((definiciones.obtener(Actividad, identificador) for identificador in identificadores),
                  key=lambda actividad: (actividad.orden, actividad.codigo))


def opcion_publica(opcion: OpcionEscala) -> OpcionPublica:
    return OpcionPublica(orden=opcion.orden, etiqueta=opcion.etiqueta, puntaje=opcion.puntaje)


@usar_contexto
def escala_publica(sesion: Session, escala: EscalaRespuesta) -> EscalaPublica:
    return EscalaPublica(codigo=escala.codigo, nombre=escala.nombre, opciones=[
        opcion_publica(opcion) for opcion in sorted((opcion for opcion in contexto(sesion).definiciones.listar(OpcionEscala)
                                      if opcion.escala_id == escala.id), key=lambda opcion: opcion.orden)
    ])


@usar_contexto
def catalogo_instrumentos(sesion: Session) -> list[InstrumentoPublico]:
    catalogo = []
    for instrumento in sorted(contexto(sesion).definiciones.listar(Instrumento), key=lambda instrumento: instrumento.codigo):
        dimensiones = sorted((dimension for dimension in contexto(sesion).definiciones.listar(Dimension)
                              if dimension.instrumento_id == instrumento.id), key=lambda dimension: (dimension.orden, dimension.codigo))
        escalas = sorted((escala for escala in contexto(sesion).definiciones.listar(EscalaRespuesta)
                          if escala.id in {item.escala_id for item in contexto(sesion).definiciones.listar(ItemInstrumento)
                                           if item.instrumento_id == instrumento.id}), key=lambda escala: escala.codigo)
        catalogo.append(InstrumentoPublico(
            codigo=instrumento.codigo, nombre=instrumento.nombre, descripcion=instrumento.descripcion,
            tipo_resultado=instrumento.tipo_resultado,
            dimensiones=[DimensionPublica(codigo=d.codigo, nombre=d.nombre, descripcion=d.descripcion,
                                         orden=d.orden) for d in dimensiones],
            escalas=[escala_publica(sesion, escala) for escala in escalas],
            aplicaciones=[AplicacionPublica(codigo=a.codigo, nombre=a.nombre, momento=a.momento, actividades=[
                ActividadPublica(codigo=t.codigo, titulo=t.titulo, orden=t.orden)
                for t in actividades_de_aplicacion(sesion, a)
            ]) for a in aplicaciones_de_instrumento(sesion, instrumento)],
        ))
    return catalogo


@usar_contexto
def items_presentados(sesion: Session, actividad: Actividad) -> list[ItemPublico]:
    definiciones = contexto(sesion).definiciones
    presentaciones = sorted((fila for fila in definiciones.listar(ActividadItem) if fila.actividad_id == actividad.id),
                            key=lambda fila: (fila.orden, definiciones.obtener(ItemInstrumento, fila.item_id).numero))
    filas = [(definiciones.obtener(ItemInstrumento, fila.item_id), fila.orden) for fila in presentaciones]
    return [ItemPublico(
        codigo=item.codigo, instrumento=definiciones.obtener(Instrumento, item.instrumento_id).codigo,
        numero=item.numero, orden=orden, enunciado=item.enunciado,
        dimension=None if item.dimension_id is None else definiciones.obtener(Dimension, item.dimension_id).codigo,
        inverso=item.inverso, escala=escala_publica(sesion, definiciones.obtener(EscalaRespuesta, item.escala_id)),
    ) for item, orden in filas]


@usar_contexto
def respuestas_actuales(sesion: Session, cuenta: Cuenta, actividad: Actividad) -> RespuestasActividad:
    filas = sesion.execute(select(RespuestaItem, ItemInstrumento.codigo, OpcionEscala).select_from(
        RespuestaItem,
    ).join(ProgresoActividad).join(ItemInstrumento, ItemInstrumento.id == RespuestaItem.item_id).join(
        ActividadItem, (ActividadItem.item_id == ItemInstrumento.id) & (ActividadItem.actividad_id == actividad.id),
    ).join(OpcionEscala, OpcionEscala.id == RespuestaItem.opcion_id).where(
        ProgresoActividad.cuenta_id == cuenta.id, ProgresoActividad.actividad_id == actividad.id,
    ).order_by(ActividadItem.orden, ItemInstrumento.numero))
    return RespuestasActividad(cuenta=cuenta.codigo, actividad=actividad.codigo, respuestas=[
        RespuestaPublica(item=codigo, opcion=opcion_publica(opcion), creada_en=respuesta.creada_en,
                        actualizada_en=respuesta.actualizada_en) for respuesta, codigo, opcion in filas
    ])


@usar_contexto
def avance_aplicacion(sesion: Session, cuenta: Cuenta, aplicacion: Aplicacion) -> AvanceAplicacion:
    actividades = actividades_de_aplicacion(sesion, aplicacion)
    datos = contexto(sesion)
    if not hasattr(datos, 'avances'):
        datos.avances = {}
    if cuenta.id not in datos.avances:
        respuestas = set(sesion.execute(select(ProgresoActividad.actividad_id, RespuestaItem.item_id).join(
            RespuestaItem, RespuestaItem.progreso_id == ProgresoActividad.id,
        ).where(ProgresoActividad.cuenta_id == cuenta.id)).all())
        vigentes = set(sesion.scalars(select(ResultadoInstrumento.aplicacion_id).where(
            ResultadoInstrumento.cuenta_id == cuenta.id, ResultadoInstrumento.anulado_en.is_(None),
        )))
        datos.avances[cuenta.id] = respuestas, vigentes
    respuestas, vigentes = datos.avances[cuenta.id]
    ids_actividades = {actividad.id for actividad in actividades}
    progresos = {identificador: progreso for identificador, progreso in datos.progresos_de(cuenta.id).items()
                 if identificador in ids_actividades}
    faltantes = [actividad.codigo for actividad in actividades if actividad.id not in progresos
                 or progresos[actividad.id].estado != EstadoProgreso.COMPLETADA]
    total_items = [fila for fila in datos.definiciones.listar(ActividadItem) if fila.actividad_id in ids_actividades
                   and datos.definiciones.obtener(ItemInstrumento, fila.item_id).instrumento_id == aplicacion.instrumento_id]
    respondidos = sum((fila.actividad_id, fila.item_id) in respuestas for fila in total_items)
    vigente = aplicacion.id in vigentes
    instrumento = datos.definiciones.obtener(Instrumento, aplicacion.instrumento_id)
    completo = not faltantes if instrumento.tipo_resultado == TipoResultado.COMPARACION else vigente
    estado = "COMPLETADO" if completo else "EN_PROGRESO" if progresos else "NO_INICIADO"
    return AvanceAplicacion(aplicacion=aplicacion.codigo, estado=estado,
        actividades=ConteoAvance(completadas=len(actividades) - len(faltantes), total=len(actividades), faltantes=faltantes),
        items=ConteoItems(respondidos=respondidos, total=len(total_items)), hay_resultado_vigente=vigente)


@usar_contexto
def avance_instrumentos(sesion: Session, cuenta: Cuenta) -> list[AvanceInstrumento]:
    return [AvanceInstrumento(instrumento=i.codigo, aplicaciones=[avance_aplicacion(sesion, cuenta, a)
        for a in aplicaciones_de_instrumento(sesion, i)])
        for i in sorted(contexto(sesion).definiciones.listar(Instrumento), key=lambda instrumento: instrumento.codigo)]


@usar_contexto
def seleccionar_aplicacion(sesion: Session, instrumento: Instrumento, codigo: str | None) -> Aplicacion:
    aplicaciones = aplicaciones_de_instrumento(sesion, instrumento)
    if codigo is None:
        if len(aplicaciones) != 1:
            raise ValueError("Debe indicar la aplicación de este instrumento")
        return aplicaciones[0]
    for aplicacion in aplicaciones:
        if aplicacion.codigo == codigo:
            return aplicacion
    raise LookupError("Aplicación no encontrada para este instrumento")


def cargar_representaciones(sesion, resultados):
    datos = contexto(sesion)
    if not hasattr(datos, 'representaciones'):
        datos.representaciones = {}
    faltantes = {resultado.id for resultado in resultados} - datos.representaciones.keys()
    if not faltantes:
        return
    por_dimension = {identificador: [] for identificador in faltantes}
    por_coincidencia = {identificador: [] for identificador in faltantes}
    por_carrera = {identificador: [] for identificador in faltantes}
    for dimension, resultado in sesion.execute(select(Dimension, ResultadoDimension).join(ResultadoDimension).where(
        ResultadoDimension.resultado_id.in_(faltantes),
    ).order_by(Dimension.orden, Dimension.codigo)):
        por_dimension[resultado.resultado_id].append((dimension, resultado))
    riasec = {resultado.id for resultado in resultados if resultado.id in faltantes
              and datos.definiciones.obtener(Instrumento, datos.definiciones.obtener(Aplicacion, resultado.aplicacion_id).instrumento_id).tipo_resultado == TipoResultado.COINCIDENCIAS}
    if riasec:
        for coincidencia, ocupacion in sesion.execute(select(Coincidencia, Ocupacion).join(Ocupacion).where(
            Coincidencia.resultado_id.in_(riasec),
        ).order_by(Coincidencia.posicion)):
            por_coincidencia[coincidencia.resultado_id].append((coincidencia, ocupacion))
        for resultado_id, carrera_id, ocupacion_id in sesion.execute(select(
            Coincidencia.resultado_id, CarreraOcupacion.carrera_id, CarreraOcupacion.ocupacion_id,
        ).join(CarreraOcupacion, CarreraOcupacion.ocupacion_id == Coincidencia.ocupacion_id).where(
            Coincidencia.resultado_id.in_(riasec),
        )):
            carrera = datos.definiciones.obtener(Carrera, carrera_id)
            familia = datos.definiciones.obtener(FamiliaCarrera, carrera.familia_id)
            por_carrera[resultado_id].append((carrera, familia, ocupacion_id))
    datos.representaciones.update({identificador: (por_dimension[identificador], por_coincidencia[identificador], por_carrera[identificador])
                                  for identificador in faltantes})


@usar_contexto
def representar_resultado(sesion: Session, resultado: ResultadoInstrumento, historico: bool = False) -> ResultadoPublico:
    definiciones = contexto(sesion).definiciones
    aplicacion = definiciones.obtener(Aplicacion, resultado.aplicacion_id)
    instrumento = definiciones.obtener(Instrumento, aplicacion.instrumento_id)
    cargar_representaciones(sesion, [resultado])
    filas, afines, relaciones_carreras = contexto(sesion).representaciones[resultado.id]
    datos = dict(instrumento=instrumento.codigo, aplicacion=aplicacion.codigo, calculado_en=resultado.calculado_en,
        perfil_plano=resultado.perfil_plano, dimensiones=[DimensionResultado(codigo=d.codigo, nombre=d.nombre,
            puntaje=r.puntaje, puntaje_maximo=r.puntaje_maximo, porcentaje=r.porcentaje) for d, r in filas])
    if instrumento.tipo_resultado == TipoResultado.DESTACADAS:
        destacadas = calcular_dimensiones_destacadas([
            DimensionCalculada(d.codigo, r.puntaje, r.puntaje_maximo, r.porcentaje) for d, r in filas
        ])
        datos["dimensiones_destacadas"] = [d for d in datos["dimensiones"] if d.codigo in destacadas]
    if instrumento.tipo_resultado == TipoResultado.COINCIDENCIAS:
        codigo = calcular_codigo_interes([r.puntaje for d, r in filas], [d.codigo for d, r in filas])
        datos["codigo_interes"] = CodigoInteresPublico(codigo=codigo.codigo, hay_empate=codigo.hay_empate)
        por_ocupacion = {o.id: CoincidenciaPublica(posicion=c.posicion, codigo=o.codigo, codigo_onet=o.codigo_onet,
            titulo=o.titulo, correlacion=round(c.correlacion, DECIMALES_CORRELACION), ajuste=c.ajuste) for c, o in afines}
        datos["coincidencias"] = list(por_ocupacion.values())
        carreras = {}
        for carrera, familia, ocupacion_id in relaciones_carreras:
            if carrera.id not in carreras:
                carreras[carrera.id] = CarreraRecomendada(codigo=carrera.codigo, nombre=carrera.nombre,
                                                         familia=familia.codigo, via=[])
            carreras[carrera.id].via.append(por_ocupacion[ocupacion_id])
        for carrera in carreras.values():
            carrera.via.sort(key=lambda via: via.posicion)
        datos["carreras_recomendadas"] = sorted(carreras.values(), key=lambda c: (c.via[0].posicion, c.codigo))
    if historico:
        return ResultadoHistorico(**datos, anulado_en=resultado.anulado_en)
    return ResultadoPublico(**datos)


@usar_contexto
def resultado_vigente(sesion: Session, cuenta: Cuenta, instrumento: Instrumento, codigo: str | None) -> ResultadoPublico:
    aplicacion = seleccionar_aplicacion(sesion, instrumento, codigo)
    resultado = sesion.scalar(select(ResultadoInstrumento).where(ResultadoInstrumento.cuenta_id == cuenta.id,
        ResultadoInstrumento.aplicacion_id == aplicacion.id, ResultadoInstrumento.anulado_en.is_(None)))
    if resultado is None:
        raise ConsultaPendiente("No hay resultado vigente", avance_aplicacion(sesion, cuenta, aplicacion))
    return representar_resultado(sesion, resultado)


@usar_contexto
def historial_resultados(sesion: Session, cuenta: Cuenta, instrumento: Instrumento) -> list[ResultadoHistorico]:
    resultados = list(sesion.scalars(select(ResultadoInstrumento).join(Aplicacion).where(
        ResultadoInstrumento.cuenta_id == cuenta.id, Aplicacion.instrumento_id == instrumento.id,
    ).order_by(ResultadoInstrumento.calculado_en.desc(), ResultadoInstrumento.id.desc())))
    cargar_representaciones(sesion, resultados)
    return [representar_resultado(sesion, resultado, historico=True) for resultado in resultados]


@usar_contexto
def comparacion_autopercepcion(sesion: Session, cuenta: Cuenta, instrumento: Instrumento) -> ComparacionAutopercepcion:
    if instrumento.tipo_resultado != TipoResultado.COMPARACION:
        raise LookupError("Este instrumento no admite comparación")
    aplicaciones = aplicaciones_de_instrumento(sesion, instrumento)
    entradas = [aplicacion for aplicacion in aplicaciones if aplicacion.momento == MomentoAplicacion.ENTRADA]
    salidas = [aplicacion for aplicacion in aplicaciones if aplicacion.momento == MomentoAplicacion.SALIDA]
    if len(entradas) != 1 or len(salidas) != 1:
        raise ValueError("La comparación requiere una aplicación de entrada y una de salida")
    entrada, salida = entradas[0], salidas[0]
    avances = [avance_aplicacion(sesion, cuenta, a) for a in (entrada, salida)]
    if any(avance.estado != "COMPLETADO" for avance in avances):
        raise ConsultaPendiente("Falta completar ambas aplicaciones de autopercepción", avances)
    aplicaciones = (entrada, salida)
    actividades = [{actividad.id for actividad in actividades_de_aplicacion(sesion, aplicacion)} for aplicacion in aplicaciones]
    respuestas_por_actividad = sesion.execute(select(ProgresoActividad.actividad_id, ItemInstrumento.codigo, OpcionEscala).select_from(
        RespuestaItem,
    ).join(ProgresoActividad).join(ItemInstrumento, ItemInstrumento.id == RespuestaItem.item_id).join(
        ActividadItem, (ActividadItem.item_id == ItemInstrumento.id) & (ActividadItem.actividad_id == ProgresoActividad.actividad_id),
    ).join(OpcionEscala, OpcionEscala.id == RespuestaItem.opcion_id).where(
        ProgresoActividad.cuenta_id == cuenta.id, ProgresoActividad.actividad_id.in_(set.union(*actividades)),
    )).all()
    respuestas = [{codigo: opcion_publica(opcion) for actividad_id, codigo, opcion in respuestas_por_actividad if actividad_id in ids}
                  for ids in actividades]
    items = sorted((item for item in contexto(sesion).definiciones.listar(ItemInstrumento)
                    if item.instrumento_id == instrumento.id), key=lambda item: item.numero)
    return ComparacionAutopercepcion(instrumento=instrumento.codigo, entrada=entrada.codigo, salida=salida.codigo,
        items=[ComparacionItem(item=i.codigo, enunciado=i.enunciado, entrada=respuestas[0][i.codigo],
            salida=respuestas[1][i.codigo],
            diferencia=respuestas[1][i.codigo].puntaje - respuestas[0][i.codigo].puntaje) for i in items])
