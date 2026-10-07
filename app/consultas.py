import re

from app.contexto_consultas import contexto, usar_contexto

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import (
    Actividad, Audiencia, Bloque, Cuenta, Desbloqueo, EntradaDiario,
    EventoUso, Ficha, Insignia, Nivel, OrigenEntrada,
    PreguntaDiario, ReglaDesbloqueo, Rol, Testimonio, TipoEventoUso, TipoObjetivo,
)
from app.motor import evaluar_regla, nivel_actual, objetivo_corresponde_a_cuenta, objetivo_disponible
from app.referencias import MODELOS_OBJETIVO, objetivo_legible, precargar_referencias, referencia_legible
from app.schemas import (
    ActividadEstado, BloqueEstado, CondicionLegible, ContenidoEstado, ConversacionesEstado,
    CuentaResumen, DesbloqueoLegible, EstadoCuenta, EventoLegible, InsigniaEstado,
    NivelActual, NivelEstado, ObjetivoProgreso, PreguntaDiarioEstado, ProgresoObjetivo,
    ProgresoRegla, ReglaLegible,
)


@usar_contexto
def listar_reglas(sesion: Session) -> list[ReglaLegible]:
    resultado = []
    precargar_referencias(sesion, [(condicion.tipo_evento, condicion.id_referencia)
                                  for regla in contexto(sesion).definiciones.listar(ReglaDesbloqueo)
                                  for condicion in regla.condiciones])
    for regla in sorted(contexto(sesion).definiciones.listar(ReglaDesbloqueo), key=lambda regla: regla.codigo):
        condiciones = []
        for condicion in regla.condiciones:
            condiciones.append(CondicionLegible(
                tipo_evento=condicion.tipo_evento,
                referencia=referencia_legible(sesion, condicion.tipo_evento, condicion.id_referencia),
                tipo_conteo=condicion.tipo_conteo, cantidad_minima=condicion.cantidad_minima,
            ))
        resultado.append(ReglaLegible(
            regla=regla.codigo, nombre=regla.nombre, tipo_objetivo=regla.tipo_objetivo,
            objetivo=objetivo_legible(sesion, regla), condiciones=condiciones,
            evaluador_especial=regla.evaluador_especial,
        ))
    return resultado


def listar_cuentas(sesion: Session) -> list[CuentaResumen]:
    return [CuentaResumen.model_validate(cuenta)
            for cuenta in sesion.scalars(select(Cuenta).order_by(Cuenta.codigo))]


@usar_contexto
def estado_contenido(sesion: Session, cuenta: Cuenta, modelo, tipo: TipoObjetivo) -> list[ContenidoEstado]:
    return [ContenidoEstado(
        codigo=contenido.codigo, titulo=contenido.titulo,
        estado="DISPONIBLE" if objetivo_disponible(sesion, cuenta, tipo, contenido.id) else "BLOQUEADA",
    ) for contenido in sorted(contexto(sesion).definiciones.listar(modelo), key=lambda contenido: contenido.codigo)]


@usar_contexto
def estado_cuenta(sesion: Session, cuenta: Cuenta) -> EstadoCuenta:
    datos = contexto(sesion)
    progresos = {identificador: progreso.estado for identificador, progreso in datos.progresos_de(cuenta.id).items()}
    bloques = []
    for bloque in sorted((bloque for bloque in datos.definiciones.listar(Bloque)
                         if bloque.audiencia == Audiencia(cuenta.rol.value)), key=lambda bloque: bloque.codigo):
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
            actividades.append(ActividadEstado(codigo=actividad.codigo, titulo=actividad.titulo, estado=estado))
        bloques.append(BloqueEstado(
            codigo=bloque.codigo, nombre=bloque.nombre, espacio=bloque.espacio,
            estado="DISPONIBLE" if bloque_disponible else "BLOQUEADA", actividades=actividades,
        ))

    insignias = []
    for insignia in sorted((insignia for insignia in datos.definiciones.listar(Insignia)
                           if insignia.audiencia == Audiencia(cuenta.rol.value)), key=lambda insignia: insignia.codigo):
        obtenida = objetivo_disponible(sesion, cuenta, TipoObjetivo.INSIGNIA, insignia.id)
        oculta = insignia.es_oculta and not obtenida
        insignias.append(InsigniaEstado(
            codigo="???" if oculta else insignia.codigo,
            nombre="Logro oculto" if oculta else insignia.nombre,
            descripcion=None if oculta else insignia.descripcion,
            requisito=None if oculta else insignia.requisito,
            estado="OBTENIDA" if obtenida else "BLOQUEADA",
        ))

    fichas, testimonios, preguntas, niveles = [], [], [], []
    if cuenta.rol == Rol.ESTUDIANTE:
        fichas = estado_contenido(sesion, cuenta, Ficha, TipoObjetivo.FICHA)
        testimonios = estado_contenido(sesion, cuenta, Testimonio, TipoObjetivo.TESTIMONIO)
        respondidas = set(sesion.scalars(select(EntradaDiario.pregunta_id).where(
            EntradaDiario.cuenta_id == cuenta.id, EntradaDiario.origen == OrigenEntrada.GUIADA,
        )))
        preguntas = [PreguntaDiarioEstado(
            codigo=pregunta.codigo, pregunta=pregunta.pregunta,
            estado="DISPONIBLE" if objetivo_disponible(sesion, cuenta, TipoObjetivo.PREGUNTA_DIARIO,
                                                       pregunta.id) else "BLOQUEADA",
            respondida=pregunta.id in respondidas,
        ) for pregunta in sorted(datos.definiciones.listar(PreguntaDiario), key=lambda pregunta: pregunta.codigo)]
        niveles = [NivelEstado(
            numero=nivel.numero, titulo=nivel.titulo,
            estado="OBTENIDO" if objetivo_disponible(sesion, cuenta, TipoObjetivo.NIVEL, nivel.id) else "BLOQUEADO",
        ) for nivel in sorted(datos.definiciones.listar(Nivel), key=lambda nivel: nivel.numero)]
    actual = nivel_actual(sesion, cuenta)
    return EstadoCuenta(
        cuenta=CuentaResumen.model_validate(cuenta),
        nivel_actual=None if actual is None else NivelActual(numero=actual.numero, titulo=actual.titulo),
        bloques=bloques, fichas=fichas, testimonios=testimonios, preguntas_diario=preguntas,
        conversaciones=ConversacionesEstado(
            estado="DISPONIBLE" if objetivo_disponible(sesion, cuenta, TipoObjetivo.CONVERSACIONES, None)
            else "BLOQUEADA",
        ),
        insignias=insignias, niveles=niveles,
    )


@usar_contexto
def id_objetivo_por_codigo(sesion: Session, tipo: TipoObjetivo, codigo: str) -> int | None:
    if tipo == TipoObjetivo.CONVERSACIONES:
        if codigo == "-":
            return None
        raise LookupError("Objetivo no encontrado")
    definiciones = contexto(sesion).definiciones
    modelo = MODELOS_OBJETIVO[tipo]
    if tipo == TipoObjetivo.NIVEL:
        coincidencia = re.fullmatch(r"N([1-9]\d*)", codigo)
        if coincidencia is None:
            raise LookupError("Objetivo no encontrado")
        objetivo = next((nivel for nivel in definiciones.listar(Nivel) if nivel.numero == int(coincidencia[1])), None)
    else:
        objetivo = definiciones.por_codigo(modelo, codigo)
    if objetivo is None:
        raise LookupError("Objetivo no encontrado")
    return objetivo.id


@usar_contexto
def progreso_objetivo(
    sesion: Session, cuenta: Cuenta, tipo: TipoObjetivo, codigo: str,
) -> ProgresoObjetivo:
    identificador = id_objetivo_por_codigo(sesion, tipo, codigo)
    if not objetivo_corresponde_a_cuenta(sesion, cuenta, tipo, identificador):
        raise LookupError("Objetivo no encontrado para esta cuenta")
    disponible = objetivo_disponible(sesion, cuenta, tipo, identificador)
    if tipo == TipoObjetivo.INSIGNIA:
        insignia = contexto(sesion).definiciones.obtener(Insignia, identificador)
        if insignia.es_oculta and not disponible:
            raise PermissionError("El progreso de este logro permanece oculto hasta obtenerlo")
    reglas = []
    precargar_referencias(sesion, [(condicion.tipo_evento, condicion.id_referencia)
                                  for regla in contexto(sesion).definiciones.reglas_objetivo.get((tipo, identificador), ())
                                  for condicion in regla.condiciones])
    for regla in contexto(sesion).definiciones.reglas_objetivo.get((tipo, identificador), ()):
        resultado = evaluar_regla(sesion, cuenta, regla)
        campos = {"regla": regla.codigo, "cumplida": resultado.cumple, "condiciones": resultado.condiciones}
        if resultado.evaluador_especial is not None:
            campos["evaluador_especial"] = resultado.evaluador_especial
        reglas.append(ProgresoRegla(**campos))
    return ProgresoObjetivo(
        objetivo=ObjetivoProgreso(tipo=tipo, codigo=codigo), disponible=disponible, reglas=reglas,
    )


@usar_contexto
def listar_eventos(sesion: Session, cuenta: Cuenta) -> list[EventoLegible]:
    resultado = []
    eventos = list(sesion.scalars(select(EventoUso).where(EventoUso.cuenta_id == cuenta.id).order_by(
        EventoUso.fecha_hora.desc(), EventoUso.id.desc(),
    )))
    precargar_referencias(sesion, [(evento.tipo, evento.id_referencia) for evento in eventos])
    for evento in eventos:
        # El modelo de diario/check-in no define un código público para estas referencias.
        referencia = None if evento.tipo in (
            TipoEventoUso.ESCRIBE_ENTRADA_DIARIO, TipoEventoUso.ESCRIBE_ENTRADA_LIBRE,
            TipoEventoUso.REGISTRA_CHECK_IN,
        ) else referencia_legible(sesion, evento.tipo, evento.id_referencia)
        resultado.append(EventoLegible(tipo=evento.tipo, referencia=referencia, fecha_hora=evento.fecha_hora))
    return resultado


@usar_contexto
def listar_desbloqueos(sesion: Session, cuenta: Cuenta, solo_no_vistos: bool = False) -> list[DesbloqueoLegible]:
    consulta = select(Desbloqueo).where(Desbloqueo.cuenta_id == cuenta.id)
    if solo_no_vistos:
        consulta = consulta.where(Desbloqueo.visto.is_(False))
    consulta = consulta.order_by(Desbloqueo.fecha_hora.desc(), Desbloqueo.id.desc())
    resultado = []
    for desbloqueo in sesion.scalars(consulta):
        regla = contexto(sesion).definiciones.obtener(ReglaDesbloqueo, desbloqueo.regla_id)
        if objetivo_corresponde_a_cuenta(sesion, cuenta, regla.tipo_objetivo, regla.id_objetivo):
            resultado.append(DesbloqueoLegible(
                regla=regla.codigo, tipo_objetivo=regla.tipo_objetivo,
                objetivo=objetivo_legible(sesion, regla), fecha_hora=desbloqueo.fecha_hora, visto=desbloqueo.visto,
            ))
    return resultado


def marcar_desbloqueos_vistos(sesion: Session, cuenta: Cuenta) -> int:
    resultado = sesion.execute(update(Desbloqueo).where(
        Desbloqueo.cuenta_id == cuenta.id, Desbloqueo.visto.is_(False),
    ).values(visto=True))
    return resultado.rowcount
