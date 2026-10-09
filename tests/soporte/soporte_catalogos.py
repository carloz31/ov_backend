"""Corrupciones controladas y filas mínimas de catálogo; DATO DE PRUEBA."""

from sqlalchemy import delete, update
from app import models as m
from datos import plataforma
from datos.ocupaciones import validar_distribucion_items
from soporte_retiro import FECHA_BD, buscar, instrumento_minimo


def cargar_catalogo_corrupto(sesion, variante):
    plataforma.cargar(sesion)
    item = buscar(sesion, m.ItemInstrumento, 'RIASEC-01')
    if variante == 'faltante':
        sesion.execute(delete(m.ActividadItem).where(m.ActividadItem.item_id == item.id))
    elif variante == 'repetido':
        sesion.add(m.ActividadItem(actividad_id=buscar(sesion, m.Actividad, 'act-tip-02').id,
                                  item_id=item.id, orden=99))
    elif variante == 'ajeno':
        instrumento_minimo(sesion)
        ajeno = buscar(sesion, m.ItemInstrumento, 'ITEM-PRUEBA-1')
        sesion.add(m.ActividadItem(actividad_id=buscar(sesion, m.Actividad, 'act-tip-01').id,
                                  item_id=ajeno.id, orden=99))
    else:
        sesion.execute(update(m.Actividad).where(m.Actividad.codigo == 'mission-welcome').values(contenido=variante))
    sesion.flush()
    validar_distribucion_items(sesion)


def completar_catalogos_vacios(sesion):
    sesion.add_all([
        m.Testimonio(codigo='testimonio-prueba', titulo='DATO DE PRUEBA', descripcion='DATO DE PRUEBA', enlace='https://example.invalid'),
        m.PreguntaDiario(codigo='pregunta-prueba', pregunta='DATO DE PRUEBA'),
    ])
    sesion.flush()
    sesion.add(m.EntradaDiario(cuenta_id=buscar(sesion, m.Cuenta, 'est-ana').id, origen='GUIADA',
        pregunta_id=buscar(sesion, m.PreguntaDiario, 'pregunta-prueba').id, texto='DATO DE PRUEBA', fecha_hora=FECHA_BD))
    sesion.add_all([m.Ocupacion(codigo_onet=f'PRUEBA-NULO-{n}', titulo='DATO DE PRUEBA') for n in (1, 2)])
