import re

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.contexto import contexto, usar_contexto
from app.models import (
    Cuenta, Desbloqueo, EventoUso, Insignia, Nivel, ReglaDesbloqueo, TipoEventoUso, TipoObjetivo,
)
from app.schemas.cuentas import (
    CuentaResumen, DesbloqueoLegible, EventoLegible,
    NivelActual, ObjetivoProgreso, ProgresoObjetivo, ProgresoRegla, ResumenCuenta,
)
from app.schemas.motor import CondicionLegible, ReglaLegible
from app.services.motor.referencias import (
    MODELOS_OBJETIVO, objetivo_legible, precargar_referencias, referencia_legible,
)
from app.services.motor.reglas import (
    evaluar_regla, nivel_actual, objetivo_corresponde_a_cuenta, objetivo_disponible,
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
def resumen_cuenta(sesion: Session, cuenta: Cuenta) -> ResumenCuenta:
    actual = nivel_actual(sesion, cuenta)
    return ResumenCuenta(
        cuenta=CuentaResumen.model_validate(cuenta),
        nivel_actual=None if actual is None else NivelActual(numero=actual.numero, titulo=actual.titulo),
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


def obtener_cuenta_demo(sesion: Session, cuenta: str) -> Cuenta | None:
    return sesion.scalar(select(Cuenta).where(Cuenta.codigo == cuenta))
