"""Conjunto de prueba B3: cinco pasos y Ciudad disponible desde el segundo."""

import os
import subprocess
import sys

import pytest
from sqlalchemy import select

from app.main import crear_aplicacion
from app.models import Base, EventoUso, ProgresoActividad
from datos.cargar import preparar_base
from soporte_plataforma import completar, pedir, responder


CAMINO = ('mission-welcome', 'enc-mitos', 'act-07', 'mission-story', 'mission-compass')


@pytest.fixture
def aplicacion(tmp_path):
    url = f"sqlite:///{(tmp_path / 'piloto.db').as_posix()}"
    preparar_base(url, 'piloto', crear_tablas=True)
    return crear_aplicacion(url)


def actividades(cliente):
    return pedir(cliente, 'GET', '/cuentas/est-ana/actividades')


def test_inicio_cinco_actividades_y_ciudad_bloqueada(cliente):
    camino, ciudad = actividades(cliente)
    assert camino['codigo'] == 'CAMINO' and camino['estado'] == 'DISPONIBLE'
    assert [a['codigo'] for a in camino['actividades']] == list(CAMINO)
    assert [a['orden'] for a in camino['actividades']] == [1, 2, 3, 4, 5]
    assert [a['estado'] for a in camino['actividades']] == ['DISPONIBLE'] + ['BLOQUEADA'] * 4
    assert all(a['visibilidad'] == 'SIEMPRE' and a['visible'] for a in camino['actividades'])
    assert ciudad['codigo'] == 'CIUDAD' and ciudad['estado'] == 'BLOQUEADA'
    assert len(ciudad['actividades']) == 16
    assert all(a['estado'] == 'BLOQUEADA' for a in ciudad['actividades'])
    assert [a['codigo'] for a in ciudad['actividades'][:14]] == [f'act-tip-{n:02}' for n in range(1, 15)]


def test_segundo_paso_abre_ciudad_sin_completar_camino(cliente):
    completar(cliente, 'mission-welcome')
    assert actividades(cliente)[1]['estado'] == 'BLOQUEADA'
    respuesta = completar(cliente, 'enc-mitos')
    ciudad = actividades(cliente)[1]
    assert ciudad['estado'] == 'DISPONIBLE'
    assert ciudad['actividades'][0]['estado'] == 'DISPONIBLE'
    assert 'R-ciudad' in {d['regla'] for d in respuesta['nuevos_desbloqueos']}
    assert not any(e['tipo'] == 'COMPLETA_BLOQUE' for e in respuesta['eventos_registrados'])
    assert [a['estado'] for a in actividades(cliente)[0]['actividades']] == [
        'COMPLETADA', 'COMPLETADA', 'DISPONIBLE', 'BLOQUEADA', 'BLOQUEADA',
    ]


def test_camino_reducido_conserva_insignias_y_niveles(cliente):
    respuestas = {}
    for codigo in CAMINO:
        respuestas[codigo] = completar(cliente, codigo)
    cuarta = {d['regla'] for d in respuestas['mission-story']['nuevos_desbloqueos']}
    assert {'R-I2', 'R-NIV-2', 'R-mission-compass'} <= cuarta
    ultima = respuestas['mission-compass']
    assert ultima['eventos_registrados'][-1]['tipo'] == 'COMPLETA_BLOQUE'
    assert ultima['eventos_registrados'][-1]['referencia'] == 'CAMINO'
    assert {'R-I3', 'R-NIV-3', 'R-FAM-ESTUDIANTE'} <= {d['regla'] for d in ultima['nuevos_desbloqueos']}
    assert 'R-ciudad' not in {d['regla'] for d in ultima['nuevos_desbloqueos']}
    logros = pedir(cliente, 'GET', '/cuentas/est-ana/logros')
    assert {i['codigo'] for i in logros['insignias'] if i['estado'] == 'OBTENIDA'} == {'I1', 'I2', 'I3'}
    assert [n['estado'] for n in logros['niveles']] == ['OBTENIDO'] * 3 + ['BLOQUEADO'] * 2
    assert pedir(cliente, 'GET', '/cuentas/est-ana/resumen')['nivel_actual']['numero'] == 3


def test_elena_se_revela_despues_de_interaccion_catorce(cliente):
    for codigo in CAMINO[:2]:
        completar(cliente, codigo)
    for numero in range(1, 15):
        elena = next(a for a in actividades(cliente)[1]['actividades'] if a['codigo'] == 'act-tip-final')
        assert elena['contenido'] == 'encuentro_resultado_elena'
        assert elena['visibilidad'] == 'AL_DESBLOQUEAR'
        assert elena['estado'] == 'BLOQUEADA' and elena['visible'] is False
        codigo = f'act-tip-{numero:02}'
        responder(cliente, codigo)
        completar(cliente, codigo)
    elena = next(a for a in actividades(cliente)[1]['actividades'] if a['codigo'] == 'act-tip-final')
    assert elena['estado'] == 'DISPONIBLE' and elena['visible'] is True
    assert any(a['estado'] != 'COMPLETADA' for a in actividades(cliente)[0]['actividades'])
    resultado = pedir(cliente, 'GET', '/cuentas/est-ana/instrumentos/TEST-RIASEC/resultado')
    assert resultado['codigo_interes'] == {'codigo': 'IRA', 'hay_empate': False}
    assert len(resultado['coincidencias']) == 10
    assert resultado['coincidencias'][0]['codigo'] == 'geologist'


def test_actividad_sin_contenido_se_envia_visible_y_hereda_ciudad(cliente):
    extra = actividades(cliente)[1]['actividades'][-1]
    assert extra == {
        'codigo': 'cdd-sin-contenido', 'titulo': 'Actividad de prueba sin contenido', 'tipo': 'INFORMATIVA',
        'orden': 16, 'contenido': 'sin_contenido_prueba', 'visibilidad': 'SIEMPRE', 'visible': True, 'estado': 'BLOQUEADA',
    }
    for codigo in CAMINO[:2]:
        completar(cliente, codigo)
    extra = actividades(cliente)[1]['actividades'][-1]
    assert extra['estado'] == 'DISPONIBLE' and extra['visible'] is True
    completar(cliente, 'cdd-sin-contenido')
    assert actividades(cliente)[1]['actividades'][-1]['estado'] == 'COMPLETADA'


def test_rechaza_salto_en_el_camino_sin_registrar_estado(cliente, sesion):
    completar(cliente, 'mission-compass', esperado=409)
    assert list(sesion.scalars(select(EventoUso))) == []
    assert list(sesion.scalars(select(ProgresoActividad))) == []


def test_reinicio_conserva_catalogo_piloto(cliente, sesion):
    inicial = actividades(cliente)
    for codigo in CAMINO:
        completar(cliente, codigo)
    pedir(cliente, 'POST', '/demo/reiniciar')
    assert actividades(cliente) == inicial
    assert list(sesion.scalars(select(EventoUso))) == []
    assert list(sesion.scalars(select(ProgresoActividad))) == []


def test_catalogos_ajenos_camino_son_identicos_a_plataforma(aplicacion, tmp_path):
    url = f"sqlite:///{(tmp_path / 'referencia-plataforma.db').as_posix()}"
    preparar_base(url, 'plataforma', crear_tablas=True)
    referencia = crear_aplicacion(url)
    variables = {'actividad', 'regla_desbloqueo', 'condicion_desbloqueo', 'aplicacion_actividad', 'actividad_item'}
    try:
        with aplicacion.state.fabrica_sesiones() as piloto, referencia.state.fabrica_sesiones() as plataforma:
            for tabla in Base.metadata.sorted_tables:
                if tabla.name not in variables:
                    consulta = select(tabla).order_by(*tabla.primary_key.columns)
                    assert piloto.execute(consulta).all() == plataforma.execute(consulta).all(), tabla.name
    finally:
        referencia.state.motor_bd.dispose()


def test_cargador_cli_admite_piloto_y_vaciado(tmp_path):
    url = f"sqlite:///{(tmp_path / 'cli-piloto.db').as_posix()}"
    preparar_base(url, 'demo', crear_tablas=True)
    codigo = "from datos.cargar import main; raise SystemExit(main(['piloto', '--vaciar']))"
    entorno = {**os.environ, 'DATABASE_URL': url, 'EVALUADOR': 'falso'}
    resultado = subprocess.run([sys.executable, '-c', codigo], env=entorno, capture_output=True, text=True)
    assert resultado.returncode == 0, resultado.stderr
    assert 'actividad: 21' in resultado.stdout
    app = crear_aplicacion(url)
    try:
        with app.state.fabrica_sesiones() as sesion:
            assert len(sesion.execute(select(Base.metadata.tables['actividad'])).all()) == 21
    finally:
        app.state.motor_bd.dispose()
