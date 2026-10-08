"""Esquema 3: decisiones por metadatos, orden persistido y compatibilidad."""

from datetime import datetime

import pytest
from sqlalchemy import inspect, select
from test_consultas import CADENA_MEDICION, buscar, datos_medicion, preparar_peticion

from app import models as modelos
from datos import ocupaciones
from datos.demo import instrumentos as semilla_instrumentos
from datos.ocupaciones import OcupacionArchivo, RUTA_OCUPACIONES


FECHA = datetime(2026, 10, 1, 10)


def completar_items(cliente, actividad, prefijo, opciones):
    preparar_peticion(cliente, '/acciones/responder-items', {
        **datos_medicion(actividad), 'respuestas': [
            {'item': f'{prefijo}-{numero:02}', 'opcion': opcion}
            for numero, opcion in opciones
        ],
    })
    return preparar_peticion(cliente, '/acciones/completar-actividad', datos_medicion(actividad))


def test_metadatos_semilla_catalogo_y_columnas(sesion, cliente, aplicacion):
    catalogo = cliente.get('/instrumentos').json()
    assert {i['codigo']: i['tipo_resultado'] for i in catalogo} == {
        'TEST-RIASEC': 'COINCIDENCIAS', 'TEST-INT': 'DESTACADAS',
        'TEST-HAB': 'DESTACADAS', 'TEST-AUTO': 'COMPARACION',
    }
    assert {a['codigo']: a['momento'] for i in catalogo for a in i['aplicaciones']} == {
        'APL-RIASEC': 'UNICA', 'APL-INT': 'UNICA', 'APL-HAB': 'UNICA',
        'APL-AUTO-ENT': 'ENTRADA', 'APL-AUTO-SAL': 'SALIDA',
    }
    reglas = sesion.scalars(select(modelos.ReglaDesbloqueo)).all()
    assert {r.codigo: r.parametro_evaluador for r in reglas if r.parametro_evaluador is not None} == {
        'R-INS-EXPLORADOR': 3,
    }
    assert all('parametro_evaluador' not in regla for regla in cliente.get('/reglas').json())
    inspector = inspect(aplicacion.state.motor_bd)
    assert len(inspector.get_table_names()) == 45
    for tabla, columna in [('instrumento', 'tipo_resultado'), ('aplicacion', 'momento'),
                           ('regla_desbloqueo', 'parametro_evaluador')]:
        assert columna in {c['name'] for c in inspector.get_columns(tabla)}


@pytest.mark.parametrize('plano', [False, True])
@pytest.mark.skipif(not RUTA_OCUPACIONES.is_file(), reason='Requiere el catálogo O*NET real')
def test_coincidencias_y_codigo_siguen_tipo_y_orden_de_la_base(sesion, cliente, plano):
    instrumento = buscar(sesion, modelos.Instrumento, 'TEST-RIASEC')
    instrumento.codigo = 'INTERESES-RENOMBRADO'
    dimensiones = sesion.scalars(select(modelos.Dimension).where(
        modelos.Dimension.instrumento_id == instrumento.id,
    ).order_by(modelos.Dimension.orden)).all()
    for orden, dimension in enumerate(reversed(dimensiones), start=1):
        dimension.orden = orden
    sesion.commit()
    cadena = '3' * 60 if plano else CADENA_MEDICION
    for parte in range(4):
        respuesta = completar_items(cliente, f'LAB-RIA{parte + 1}', 'RIASEC',
                                    [(n, int(cadena[n - 1])) for n in range(parte * 15 + 1, parte * 15 + 16)])
    assert respuesta['resultados_generados'] == [{'instrumento': instrumento.codigo, 'aplicacion': 'APL-RIASEC'}]
    resultado = cliente.get(f'/cuentas/est-ana/instrumentos/{instrumento.codigo}/resultado').json()
    assert [d['codigo'] for d in resultado['dimensiones']] == list('CESAIR')
    assert resultado['codigo_interes'] == {'codigo': 'CES' if plano else 'RIE', 'hay_empate': plano}
    assert resultado['perfil_plano'] is plano
    assert len(resultado['coincidencias']) == (0 if plano else 10)
    if not plano:
        assert resultado['coincidencias'][0]['codigo_onet'] == '19-1031.02'
        assert resultado['coincidencias'][0]['correlacion'] == 0.897496


def test_destacadas_no_dependen_del_codigo(sesion, cliente):
    instrumento = buscar(sesion, modelos.Instrumento, 'TEST-HAB')
    instrumento.codigo = 'HABILIDADES-RENOMBRADO'
    sesion.commit()
    completar_items(cliente, 'LAB-HAB', 'HAB', [(n, 1 if n <= 12 else 2) for n in range(1, 25)])
    resultado = cliente.get(f'/cuentas/est-ana/instrumentos/{instrumento.codigo}/resultado').json()
    assert [d['codigo'] for d in resultado['dimensiones_destacadas']] == ['HAB-VAL']
    assert 'coincidencias' not in resultado


def test_comparacion_generica_conserva_test_auto_y_usa_momentos(sesion, cliente):
    for actividad, opcion in [('LAB-AUT-E', 2), ('LAB-AUT-S', 1)]:
        completada = completar_items(cliente, actividad, 'AUT', [(n, opcion) for n in range(1, 11)])
        assert completada['resultados_generados'] == []
    antes = cliente.get('/cuentas/est-ana/instrumentos/TEST-AUTO/comparacion').json()
    assert [item['diferencia'] for item in antes['items']] == [1] * 10
    instrumento = buscar(sesion, modelos.Instrumento, 'TEST-AUTO')
    instrumento.codigo = 'COMPARACION-RENOMBRADA'
    entrada = buscar(sesion, modelos.Aplicacion, 'APL-AUTO-ENT')
    salida = buscar(sesion, modelos.Aplicacion, 'APL-AUTO-SAL')
    entrada.codigo, salida.codigo = 'Z-ENTRADA', 'A-SALIDA'
    sesion.commit()
    despues = cliente.get(f'/cuentas/est-ana/instrumentos/{instrumento.codigo}/comparacion')
    assert despues.status_code == 200
    assert despues.json() == {**antes, 'instrumento': instrumento.codigo, 'entrada': 'Z-ENTRADA', 'salida': 'A-SALIDA'}
    entrada.momento, salida.momento = modelos.MomentoAplicacion.SALIDA, modelos.MomentoAplicacion.ENTRADA
    sesion.commit()
    invertida = cliente.get(f'/cuentas/est-ana/instrumentos/{instrumento.codigo}/comparacion').json()
    assert (invertida['entrada'], invertida['salida']) == ('A-SALIDA', 'Z-ENTRADA')
    assert [item['diferencia'] for item in invertida['items']] == [-1] * 10


def test_comparacion_requiere_tipo_y_ambos_momentos(sesion, cliente):
    ruta = '/cuentas/est-ana/instrumentos/{}/comparacion'
    assert cliente.get(ruta.format('TEST-RIASEC')).status_code == 404
    assert cliente.get(ruta.format('inexistente')).status_code == 404
    assert cliente.get(ruta.format('TEST-AUTO')).status_code == 409
    salida = buscar(sesion, modelos.Aplicacion, 'APL-AUTO-SAL')
    salida.momento = modelos.MomentoAplicacion.UNICA
    sesion.commit()
    assert cliente.get(ruta.format('TEST-AUTO')).status_code == 422


def test_evaluador_lee_parametro_de_cada_regla_sin_compartir_resultados(sesion, cliente):
    regla = buscar(sesion, modelos.ReglaDesbloqueo, 'R-INS-EXPLORADOR')
    regla.parametro_evaluador = 2
    otra = modelos.ReglaDesbloqueo(
        codigo='R-DIVERSIDAD-CUATRO', nombre='Cuatro familias', tipo_objetivo=regla.tipo_objetivo,
        id_objetivo=regla.id_objetivo, evaluador_especial=regla.evaluador_especial, parametro_evaluador=4,
        condiciones=[modelos.CondicionDesbloqueo(tipo_evento=modelos.TipoEventoUso.VISTA_CARRERA,
                     tipo_conteo=modelos.TipoConteo.EVENTOS, cantidad_minima=1)],
    )
    sesion.add(otra)
    sesion.commit()
    for codigo in ('CAR-ENF', 'CAR-CIV'):
        respuesta = preparar_peticion(cliente, '/acciones/ver-carrera', {'cuenta': 'est-ana', 'carrera': codigo})
    assert [d['regla'] for d in respuesta['nuevos_desbloqueos']] == ['R-INS-EXPLORADOR']
    progreso = cliente.get('/cuentas/est-ana/progreso/INSIGNIA/INS-EXPLORADOR').json()
    assert {r['regla']: r['evaluador_especial']['cumplido'] for r in progreso['reglas']} == {
        'R-INS-EXPLORADOR': True, 'R-DIVERSIDAD-CUATRO': False,
    }


def test_excel_asocia_dimension_por_codigo_aunque_cambie_orden(sesion, monkeypatch):
    from sqlalchemy import delete
    instrumento = buscar(sesion, modelos.Instrumento, 'TEST-RIASEC')
    instrumento.codigo = 'CATALOGO-RENOMBRADO'
    dimensiones = sesion.scalars(select(modelos.Dimension).where(
        modelos.Dimension.instrumento_id == instrumento.id,
    ).order_by(modelos.Dimension.orden)).all()
    for orden, dimension in enumerate(reversed(dimensiones), start=1):
        dimension.orden = orden
    sesion.execute(delete(modelos.CarreraOcupacion))
    sesion.execute(delete(modelos.PuntajeOcupacion))
    sesion.execute(delete(modelos.Ocupacion))
    fila = OcupacionArchivo('DEMO-01', 'Perfil', (1, 2, 3, 4, 5, 6))
    monkeypatch.setattr(ocupaciones, 'leer_ocupaciones', lambda ruta: [fila])
    monkeypatch.setattr(semilla_instrumentos, 'relaciones_carreras', lambda filas: {'CAR-ENF': ('DEMO-01',)})
    semilla_instrumentos.cargar_catalogo_ocupaciones(sesion)
    assert dict(sesion.execute(select(modelos.Dimension.codigo, modelos.PuntajeOcupacion.valor).join(
        modelos.PuntajeOcupacion, modelos.PuntajeOcupacion.dimension_id == modelos.Dimension.id,
    )).all()) == {'R': 1, 'I': 2, 'A': 3, 'S': 4, 'E': 5, 'C': 6}
