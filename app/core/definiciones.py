"""Catálogo fijo por Engine: registros inmutables, sin entidades ORM compartidas."""

from collections.abc import Mapping
from dataclasses import dataclass
from threading import RLock
from types import MappingProxyType

from sqlalchemy import event, select
from sqlalchemy.orm import Session

from app import models as modelos


MODELOS_FIJOS = (
    modelos.Bloque, modelos.Actividad, modelos.Ficha, modelos.Testimonio,
    modelos.PreguntaDiario, modelos.Conversacion, modelos.Insignia, modelos.Nivel,
    modelos.FamiliaCarrera, modelos.Carrera, modelos.ReglaDesbloqueo,
    modelos.CondicionDesbloqueo, modelos.Instrumento, modelos.Dimension,
    modelos.EscalaRespuesta, modelos.OpcionEscala, modelos.ItemInstrumento,
    modelos.ActividadItem, modelos.Aplicacion, modelos.AplicacionActividad,
    modelos.ItemRegistro, modelos.CriterioCompletitud, modelos.ActividadItemRegistro,
)


@dataclass(frozen=True)
class Registro:
    valores: Mapping[str, object]

    def __getattr__(self, nombre):
        try:
            return self.valores[nombre]
        except KeyError:
            raise AttributeError(nombre) from None


class Definiciones:
    def __init__(self, conexion):
        filas = {
            modelo: [dict(fila) for fila in conexion.execute(select(modelo.__table__)).mappings()]
            for modelo in MODELOS_FIJOS
        }
        condiciones = {}
        for fila in sorted(filas[modelos.CondicionDesbloqueo], key=lambda fila: fila['id']):
            condiciones.setdefault(fila['regla_id'], []).append(Registro(MappingProxyType(fila)))
        for fila in filas[modelos.ReglaDesbloqueo]:
            fila['condiciones'] = tuple(condiciones.get(fila['id'], ()))
        self.tablas = MappingProxyType({
            modelo: tuple(Registro(MappingProxyType(fila)) for fila in registros)
            for modelo, registros in filas.items()
        })
        self.ids = MappingProxyType({modelo: MappingProxyType({fila.id: fila for fila in registros if hasattr(fila, 'id')})
                                     for modelo, registros in self.tablas.items()})
        self.codigos = MappingProxyType({modelo: MappingProxyType({
            (fila.item_registro_id, fila.codigo) if modelo is modelos.CriterioCompletitud else fila.codigo: fila
            for fila in registros if hasattr(fila, 'codigo')})
                                         for modelo, registros in self.tablas.items()})
        criterios, items_registro = {}, {}
        for criterio in sorted(self.listar(modelos.CriterioCompletitud), key=lambda fila: (fila.orden, fila.codigo)):
            criterios.setdefault(criterio.item_registro_id, []).append(criterio)
        for relacion in sorted(self.listar(modelos.ActividadItemRegistro), key=lambda fila: (fila.orden, fila.item_registro_id)):
            items_registro.setdefault(relacion.actividad_id, []).append(self.obtener(modelos.ItemRegistro, relacion.item_registro_id))
        self.criterios_por_item_registro = MappingProxyType({clave: tuple(valor) for clave, valor in criterios.items()})
        self.items_registro_por_actividad = MappingProxyType({clave: tuple(valor) for clave, valor in items_registro.items()})
        objetivos, eventos = {}, {}
        for regla in sorted(self.listar(modelos.ReglaDesbloqueo), key=lambda regla: regla.codigo):
            objetivos.setdefault((regla.tipo_objetivo, regla.id_objetivo), []).append(regla)
            for tipo in {condicion.tipo_evento for condicion in regla.condiciones}:
                eventos.setdefault(tipo, []).append(regla)
        self.reglas_objetivo = MappingProxyType({clave: tuple(valor) for clave, valor in objetivos.items()})
        self.reglas_evento = MappingProxyType({clave: tuple(valor) for clave, valor in eventos.items()})

    def listar(self, modelo):
        return self.tablas[modelo]

    def obtener(self, modelo, identificador):
        return self.ids[modelo].get(identificador)

    def por_codigo(self, modelo, codigo):
        return self.codigos[modelo].get(codigo)


class CacheDefiniciones:
    def __init__(self, motor_bd):
        self.motor_bd = motor_bd
        self._cerrojo = RLock()
        self.actual = None
        self.recargar()

    def recargar(self):
        with self._cerrojo:
            with self.motor_bd.connect() as conexion:
                nueva = Definiciones(conexion)
            self.actual = nueva


def cache_del_motor(sesion):
    enlace = sesion.get_bind()
    motor_bd = getattr(enlace, 'engine', enlace)
    return getattr(motor_bd, 'cache_definiciones', None)


def obtener_definiciones(sesion):
    cache = cache_del_motor(sesion)
    cambios = sesion.info.get('definiciones_modificadas') or any(
        isinstance(objeto, MODELOS_FIJOS) for objeto in (*sesion.new, *sesion.dirty, *sesion.deleted)
    )
    if cache is not None and not cambios:
        return cache.actual
    sesion.flush()
    return Definiciones(sesion.connection())


@event.listens_for(Session, 'do_orm_execute')
def detectar_escritura_agrupada_definiciones(operacion):
    if operacion.is_insert or operacion.is_update or operacion.is_delete:
        tabla = getattr(operacion.statement, 'table', None)
        if tabla is not None and tabla.name in {modelo.__tablename__ for modelo in MODELOS_FIJOS}:
            if cache_del_motor(operacion.session) is not None:
                operacion.session.info['definiciones_modificadas'] = True


@event.listens_for(Session, 'after_flush')
def detectar_cambios_definiciones(sesion, contexto):
    if cache_del_motor(sesion) is not None and any(
        isinstance(objeto, MODELOS_FIJOS) for objeto in (*sesion.new, *sesion.dirty, *sesion.deleted)
    ):
        sesion.info['definiciones_modificadas'] = True


@event.listens_for(Session, 'after_commit')
def actualizar_definiciones_confirmadas(sesion):
    if sesion.info.pop('definiciones_modificadas', False):
        cache = cache_del_motor(sesion)
        if cache is not None:
            cache.recargar()


@event.listens_for(Session, 'after_rollback')
def descartar_definiciones_revertidas(sesion):
    sesion.info.pop('definiciones_modificadas', None)
