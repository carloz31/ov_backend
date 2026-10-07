"""Datos de una petición o llamada al núcleo; nunca sobreviven a la operación."""

from functools import wraps

from sqlalchemy import distinct, func, literal, select, union_all

from app.definiciones import obtener_definiciones
from app.models import Desbloqueo, EventoUso, ProgresoActividad, TipoConteo


class ContextoConsultas:
    def __init__(self, sesion):
        self.sesion = sesion
        self.definiciones = obtener_definiciones(sesion)
        self.conteos = {}
        self.desbloqueos = {}
        self.progresos = {}
        self.especiales = {}

    def cargar_conteos(self, cuentas):
        faltantes = set(cuentas) - self.conteos.keys()
        if not faltantes:
            return
        fuente = select(EventoUso.cuenta_id, EventoUso.tipo, EventoUso.id_referencia,
                        EventoUso.fecha_hora).where(EventoUso.cuenta_id.in_(faltantes)).cte('eventos_cuenta')
        columnas = (fuente.c.cuenta_id, fuente.c.tipo)
        conteos = (func.count(), func.count(distinct(fuente.c.id_referencia)),
                   func.count(distinct(func.date(fuente.c.fecha_hora))))
        totales = select(*columnas, literal(None).label('referencia'), *conteos).group_by(*columnas)
        referencias = select(*columnas, fuente.c.id_referencia, *conteos).where(
            fuente.c.id_referencia.is_not(None),
        ).group_by(*columnas, fuente.c.id_referencia)
        for cuenta_id in faltantes:
            self.conteos[cuenta_id] = {}
        for cuenta_id, tipo, referencia, eventos, distintas, dias in self.sesion.execute(union_all(totales, referencias)):
            self.conteos[cuenta_id][tipo, referencia] = {
                TipoConteo.EVENTOS: eventos, TipoConteo.REFERENCIAS_DISTINTAS: distintas,
                TipoConteo.DIAS_DISTINTOS: dias,
            }

    def contar(self, cuenta_id, tipo, referencia, conteo):
        self.cargar_conteos([cuenta_id])
        return self.conteos[cuenta_id].get((tipo, referencia), {}).get(conteo, 0)

    def cargar_desbloqueos(self, cuentas):
        faltantes = set(cuentas) - self.desbloqueos.keys()
        if not faltantes:
            return
        for cuenta_id in faltantes:
            self.desbloqueos[cuenta_id] = set()
        for cuenta_id, regla_id in self.sesion.execute(select(Desbloqueo.cuenta_id, Desbloqueo.regla_id).where(
            Desbloqueo.cuenta_id.in_(faltantes),
        )):
            self.desbloqueos[cuenta_id].add(regla_id)

    def obtenidas(self, cuenta_id):
        self.cargar_desbloqueos([cuenta_id])
        return self.desbloqueos[cuenta_id]

    def progresos_de(self, cuenta_id):
        if cuenta_id not in self.progresos:
            self.progresos[cuenta_id] = {progreso.actividad_id: progreso for progreso in self.sesion.scalars(
                select(ProgresoActividad).where(ProgresoActividad.cuenta_id == cuenta_id),
            )}
        return self.progresos[cuenta_id]

    def invalidar_eventos(self, cuenta_id):
        self.conteos.pop(cuenta_id, None)
        self.especiales.pop(cuenta_id, None)


def contexto(sesion):
    return sesion.info['contexto_consultas']


def usar_contexto(funcion):
    @wraps(funcion)
    def ejecutar(sesion, *argumentos, **opciones):
        propio = 'contexto_consultas' not in sesion.info
        if propio:
            sesion.info['contexto_consultas'] = ContextoConsultas(sesion)
        try:
            return funcion(sesion, *argumentos, **opciones)
        finally:
            if propio:
                del sesion.info['contexto_consultas']
    return ejecutar
