"""Iteración 1 · F1: configuración, esquema y compatibilidad de la demo."""

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError
from test_instrumentos import CADENA_B, REQUIERE_OCUPACIONES, aplicar_cadena

from app import models as modelos


def test_columnas_y_restricciones_nuevas_con_demo_intacta(sesion, aplicacion):
    inspector = inspect(aplicacion.state.motor_bd)
    assert len(inspector.get_table_names()) == 44
    ocupacion = {columna['name']: columna for columna in inspector.get_columns('ocupacion')}
    assert set(ocupacion) == {'id', 'codigo', 'codigo_onet', 'titulo'}
    assert ocupacion['codigo']['nullable'] is True
    assert any(restriccion['column_names'] == ['codigo']
               for restriccion in inspector.get_unique_constraints('ocupacion'))
    assert all(codigo is None for codigo in sesion.scalars(select(modelos.Ocupacion.codigo)))
    # DATO DE PRUEBA: ocupaciones sintéticas para unicidad y nulos múltiples.
    sesion.add_all([
        modelos.Ocupacion(codigo_onet='PRUEBA-NULO-1', titulo='Prueba'),
        modelos.Ocupacion(codigo_onet='PRUEBA-NULO-2', titulo='Prueba'),
        modelos.Ocupacion(codigo='ocupacion-prueba', codigo_onet='PRUEBA-CODIGO-1', titulo='Prueba'),
    ])
    sesion.flush()
    with pytest.raises(IntegrityError):
        with sesion.begin_nested():
            sesion.add(modelos.Ocupacion(codigo='ocupacion-prueba', codigo_onet='PRUEBA-CODIGO-2', titulo='Prueba'))
            sesion.flush()


@REQUIERE_OCUPACIONES
@pytest.mark.parametrize('codigo', [None, 'range-manager-prueba'])
def test_codigo_ocupacion_en_resultado_historial_y_via(cliente, aplicacion, codigo):
    list(aplicar_cadena(cliente, CADENA_B))
    if codigo is not None:
        # DATO DE PRUEBA: código sintético, solo en esta base temporal.
        with aplicacion.state.fabrica_sesiones.begin() as sesion:
            ocupacion = sesion.scalar(select(modelos.Ocupacion).where(modelos.Ocupacion.codigo_onet == '19-1031.02'))
            ocupacion.codigo = codigo
    ruta = '/cuentas/est-ana/instrumentos/TEST-RIASEC'
    vigente = cliente.get(f'{ruta}/resultado').json()
    assert vigente['coincidencias'][0]['codigo'] == codigo
    assert vigente['coincidencias'][0]['codigo_onet'] == '19-1031.02'
    assert vigente['carreras_recomendadas'][0]['via'][0] == vigente['coincidencias'][0]
    assert all(afin['codigo'] is None for afin in vigente['coincidencias'][1:])
    assert cliente.get(f'{ruta}/historial').json() == [{**vigente, 'anulado_en': None}]
    respuesta = cliente.post('/acciones/reiniciar-instrumento', json={
        'cuenta': 'est-ana', 'instrumento': 'TEST-RIASEC', 'fecha_hora': '2026-10-02T10:00:00',
    })
    assert respuesta.status_code == 200
    assert cliente.get(f'{ruta}/historial').json() == [{**vigente, 'anulado_en': '2026-10-02T10:00:00'}]
