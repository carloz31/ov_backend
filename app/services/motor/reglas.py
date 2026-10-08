"""Motor de la sección 4. No confirma transacciones ni depende de routers."""

from datetime import datetime

from sqlalchemy import insert
from sqlalchemy.orm import Session

from app.core.contexto import contexto, usar_contexto
from app.models import (
    Actividad, Bloque, CondicionDesbloqueo, Cuenta, Desbloqueo, EventoUso, Nivel, ReglaDesbloqueo,
    Rol, TipoConteo, TipoEventoUso, TipoObjetivo,
)
from app.schemas.motor import DesbloqueoNuevo, ProgresoCondicion, ResultadoEvaluador, ResultadoRegla
from app.services.motor.evaluadores import EVALUADORES
from app.services.motor.referencias import (
    MODELOS_OBJETIVO, objetivo_legible, precargar_referencias, referencia_legible,
)


@usar_contexto
def contar_eventos(sesion: Session, cuenta: Cuenta, condicion: CondicionDesbloqueo) -> int:
    if condicion.tipo_conteo not in tuple(TipoConteo):
        raise ValueError(f"Tipo de conteo desconocido: {condicion.tipo_conteo}")
    return contexto(sesion).contar(cuenta.id, condicion.tipo_evento, condicion.id_referencia, condicion.tipo_conteo)


@usar_contexto
def evaluar_regla(sesion: Session, cuenta: Cuenta, regla: ReglaDesbloqueo) -> ResultadoRegla:
    if not regla.condiciones:
        raise ValueError(f"Regla sin condiciones: {regla.codigo}")
    condiciones = []
    for condicion in regla.condiciones:
        actual = contar_eventos(sesion, cuenta, condicion)
        condiciones.append(ProgresoCondicion(
            tipo_evento=condicion.tipo_evento,
            referencia=referencia_legible(sesion, condicion.tipo_evento, condicion.id_referencia),
            tipo_conteo=condicion.tipo_conteo, actual=actual,
            requerido=condicion.cantidad_minima, cumplida=actual >= condicion.cantidad_minima,
        ))
    especial = None
    if regla.evaluador_especial is not None:
        evaluador = EVALUADORES.get(regla.evaluador_especial)
        if evaluador is None:
            raise ValueError(f"Evaluador especial desconocido: {regla.evaluador_especial}")
        resultados = contexto(sesion).especiales.setdefault(cuenta.id, {})
        clave = (regla.evaluador_especial, regla.parametro_evaluador)
        if clave not in resultados:
            datos = contexto(sesion)
            anterior = getattr(datos, 'regla_en_evaluacion', None)
            datos.regla_en_evaluacion = regla
            try:
                resultados[clave] = evaluador(sesion, cuenta)
            finally:
                datos.regla_en_evaluacion = anterior
        especial = ResultadoEvaluador(nombre=regla.evaluador_especial, cumplido=resultados[clave])
    return ResultadoRegla(
        cumple=all(condicion.cumplida for condicion in condiciones)
        and (especial is None or especial.cumplido),
        condiciones=condiciones, evaluador_especial=especial,
    )


@usar_contexto
def objetivo_corresponde_a_cuenta(
    sesion: Session, cuenta: Cuenta, tipo_objetivo: TipoObjetivo, id_objetivo: int | None,
) -> bool:
    if tipo_objetivo == TipoObjetivo.CONVERSACIONES:
        return id_objetivo is None
    definiciones = contexto(sesion).definiciones
    objetivo = definiciones.obtener(MODELOS_OBJETIVO[tipo_objetivo], id_objetivo)
    if objetivo is None:
        return False
    if tipo_objetivo == TipoObjetivo.ACTIVIDAD:
        bloque = definiciones.obtener(Bloque, objetivo.bloque_id)
        return bloque.audiencia.value == cuenta.rol.value
    if tipo_objetivo in (TipoObjetivo.BLOQUE, TipoObjetivo.INSIGNIA):
        return objetivo.audiencia.value == cuenta.rol.value
    return cuenta.rol == Rol.ESTUDIANTE


@usar_contexto
def objetivo_disponible(
    sesion: Session, cuenta: Cuenta, tipo_objetivo: TipoObjetivo, id_objetivo: int | None,
) -> bool:
    if not objetivo_corresponde_a_cuenta(sesion, cuenta, tipo_objetivo, id_objetivo):
        return False
    datos = contexto(sesion)
    if tipo_objetivo == TipoObjetivo.ACTIVIDAD:
        actividad = datos.definiciones.obtener(Actividad, id_objetivo)
        if not objetivo_disponible(sesion, cuenta, TipoObjetivo.BLOQUE, actividad.bloque_id):
            return False
    reglas = datos.definiciones.reglas_objetivo.get((tipo_objetivo, id_objetivo), ())
    return not reglas or any(regla.id in datos.obtenidas(cuenta.id) for regla in reglas)


@usar_contexto
def registrar_eventos(
    sesion: Session, cuenta: Cuenta,
    eventos: list[tuple[TipoEventoUso, int | None]], fecha_hora: datetime,
) -> list[DesbloqueoNuevo]:
    """Registra y evalúa en la transacción del llamador, sin commits."""
    if not eventos:
        return []
    eventos = [(TipoEventoUso(tipo), referencia) for tipo, referencia in eventos]
    sesion.flush()
    datos = contexto(sesion)
    lote = sesion.info.get('lote_eventos')
    if lote is None:
        sesion.execute(insert(EventoUso.__table__), [dict(
            cuenta_id=cuenta.id, tipo=tipo, id_referencia=referencia, fecha_hora=fecha_hora,
        ) for tipo, referencia in eventos])
        datos.invalidar_eventos(cuenta.id)
    else:
        # La acción de varias cuentas ya insertó todo el lote en esta transacción.
        lote.discard(cuenta.id)
    tipos_nuevos = {tipo for tipo, _ in eventos}
    candidatas = {regla.id: regla for tipo in tipos_nuevos
                 for regla in datos.definiciones.reglas_evento.get(tipo, ())}
    obtenidas = datos.obtenidas(cuenta.id)
    precargar_referencias(sesion, [(condicion.tipo_evento, condicion.id_referencia)
                                  for regla in candidatas.values() if regla.id not in obtenidas
                                  for condicion in regla.condiciones])
    nuevas_filas, nuevos = [], []
    for regla in sorted(candidatas.values(), key=lambda regla: regla.codigo):
        if regla.id in obtenidas or not objetivo_corresponde_a_cuenta(sesion, cuenta, regla.tipo_objetivo, regla.id_objetivo):
            continue
        resultado = evaluar_regla(sesion, cuenta, regla)
        if resultado.cumple:
            nuevas_filas.append(dict(cuenta_id=cuenta.id, regla_id=regla.id, fecha_hora=fecha_hora, visto=False))
            obtenidas.add(regla.id)
            nuevos.append(DesbloqueoNuevo(
                regla=regla.codigo, tipo_objetivo=regla.tipo_objetivo,
                objetivo=objetivo_legible(sesion, regla), condiciones=resultado.condiciones,
                evaluador_especial=resultado.evaluador_especial,
            ))
    if nuevas_filas:
        pendientes = sesion.info.get('lote_desbloqueos')
        if pendientes is None:
            sesion.execute(insert(Desbloqueo.__table__), nuevas_filas)
        else:
            pendientes.extend(nuevas_filas)
    sesion.flush()
    return nuevos


@usar_contexto
def nivel_actual(sesion: Session, cuenta: Cuenta) -> Nivel | None:
    for nivel in sorted(contexto(sesion).definiciones.listar(Nivel), key=lambda nivel: nivel.numero, reverse=True):
        if objetivo_disponible(sesion, cuenta, TipoObjetivo.NIVEL, nivel.id):
            return nivel
    return None
