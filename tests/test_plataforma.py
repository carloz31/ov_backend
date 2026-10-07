"""P1–P16 de §4.6; cada escenario usa una base independiente."""

from pathlib import Path

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import func, select

from app import models as modelos
from app.main import crear_aplicacion
from soporte_plataforma import (
    aplicacion, cliente, CAMINO, MARA, FECHA, pedir, completar, avanzar_camino,
    responder, estado, actividades, progreso, eventos, reglas, filas_base,
)


def test_p01_estado_inicial(cliente):
    inicial = estado(cliente)
    estados = actividades(cliente)
    assert estados['mission-welcome'] == 'DISPONIBLE'
    assert all(estados[c] == 'BLOQUEADA' for c in CAMINO[1:] + MARA + ('act-tip-final',))
    assert {b['codigo']: b['estado'] for b in inicial['bloques']} == {'CAMINO': 'DISPONIBLE', 'CIUDAD': 'BLOQUEADA'}
    assert len(inicial['fichas']) == 4 and all(f['estado'] == 'BLOQUEADA' for f in inicial['fichas'])
    visibles = {i['codigo']: i for i in inicial['insignias'] if i['codigo'] != '???'}
    assert set(visibles) == {f'I{n}' for n in range(1, 10)}
    assert all(i['estado'] == 'BLOQUEADA' and i['requisito'] for i in visibles.values())
    oculto, = [i for i in inicial['insignias'] if i['codigo'] == '???']
    assert oculto['estado'] == 'BLOQUEADA' and oculto['requisito'] is None
    assert inicial['conversaciones']['estado'] == 'BLOQUEADA'
    assert inicial['nivel_actual']['numero'] == 1
    assert inicial['testimonios'] == inicial['preguntas_diario'] == []


def test_p02_primer_paso(cliente):
    assert reglas(completar(cliente, 'mission-welcome')) == {'R-enc-mitos', 'R-first-steps', 'R-I1'}


def test_p03_saltarse_la_ruta(cliente, aplicacion):
    antes = filas_base(aplicacion)
    rechazo = completar(cliente, 'act-07', esperado=409)['detail']['progreso']
    regla, = rechazo['reglas']
    assert regla['regla'] == 'R-act-07'
    assert regla['condiciones'][0]['actual'] == 0 and regla['condiciones'][0]['requerido'] == 1
    assert filas_base(aplicacion) == antes
    assert eventos(cliente) == []


def test_p04_informativa_con_fichas(cliente):
    completar(cliente, 'mission-welcome')
    assert reglas(completar(cliente, 'enc-mitos')) == {
        'R-act-07', 'R-ficha-mitos', 'R-rec-ponteencarrera', 'R-rec-unesco-stem',
    }


def test_p05_repetir_no_suma(cliente):
    avanzar_camino(cliente, 'enc-mitos')
    antes = len(eventos(cliente))
    for _ in range(3):
        respuesta = completar(cliente, 'enc-mitos')
        assert respuesta['nuevos_desbloqueos'] == []
        assert [(e['tipo'], e['referencia']) for e in respuesta['eventos_registrados']] == [('COMPLETA_ACTIVIDAD', 'enc-mitos')]
    assert len(eventos(cliente)) == antes + 3
    assert progreso(cliente, 'INSIGNIA', 'I2')['reglas'][0]['evaluador_especial']['cumplido'] is False
    assert actividades(cliente)['enc-mitos'] == 'COMPLETADA'


def test_p06_un_evento_varios_desbloqueos(cliente):
    avanzar_camino(cliente, 'act-07')
    assert reglas(completar(cliente, 'mission-story')) == {'R-mission-future', 'R-I2', 'R-NIV-2'}
    assert estado(cliente)['nivel_actual']['numero'] == 2


def test_p07_llegada_a_la_ciudad(cliente):
    respuesta = avanzar_camino(cliente)
    assert [(e['tipo'], e['referencia']) for e in respuesta['eventos_registrados']] == [
        ('COMPLETA_ACTIVIDAD', 'mission-next-step'), ('COMPLETA_BLOQUE', 'CAMINO'),
    ]
    assert reglas(respuesta) == {'R-ciudad', 'R-I3', 'R-NIV-3', 'R-FAM-ESTUDIANTE'}
    estados = actividades(cliente)
    assert estados['act-tip-01'] == 'DISPONIBLE'
    assert all(estados[c] == 'BLOQUEADA' for c in MARA[1:] + ('act-tip-final',))
    assert estado(cliente)['nivel_actual']['numero'] == 3


def test_p08_cuestionario_incompleto(cliente, aplicacion):
    avanzar_camino(cliente)
    respuesta = responder(cliente, 'act-tip-01', fin=3)
    assert respuesta['progreso'] == {'estado': 'EN_CURSO', 'respondidos': 3, 'total': 5}
    antes = filas_base(aplicacion)
    assert completar(cliente, 'act-tip-01', esperado=409)['detail']['items_faltantes'] == ['RIASEC-04', 'RIASEC-05']
    assert filas_base(aplicacion) == antes
    assert actividades(cliente)['act-tip-01'] == 'EN_CURSO'


def test_p09_retomar(cliente):
    avanzar_camino(cliente)
    responder(cliente, 'act-tip-01', fin=3)
    guardadas = pedir(cliente, 'GET', '/cuentas/est-ana/actividades/act-tip-01/respuestas')['respuestas']
    assert [(r['item'], r['opcion']['orden']) for r in guardadas] == [('RIASEC-01', 4), ('RIASEC-02', 4), ('RIASEC-03', 5)]
    responder(cliente, 'act-tip-01', inicio=3)
    respuesta = completar(cliente, 'act-tip-01')
    assert reglas(respuesta) == {'R-act-tip-02'} and respuesta['resultados_generados'] == []


def test_p10_resultado(cliente):
    avanzar_camino(cliente)
    for actividad in MARA:
        responder(cliente, actividad)
        respuesta = completar(cliente, actividad)
        if actividad != 'act-tip-14':
            assert respuesta['resultados_generados'] == []
    assert respuesta['resultados_generados'] == [{'instrumento': 'TEST-RIASEC', 'aplicacion': 'APL-RIASEC'}]
    assert reglas(respuesta) == {'R-act-tip-final'}
    resultado = pedir(cliente, 'GET', '/cuentas/est-ana/instrumentos/TEST-RIASEC/resultado')
    assert {d['codigo']: d['porcentaje'] for d in resultado['dimensiones']} == {'I': 100, 'R': 75, 'A': 50, 'S': 0, 'E': 0, 'C': 0}
    assert resultado['codigo_interes'] == {'codigo': 'IRA', 'hay_empate': False}
    coincidencias = resultado['coincidencias']
    assert len(coincidencias) == 10 and all(c['codigo'] for c in coincidencias)
    assert [c['posicion'] for c in coincidencias] == list(range(1, 11))
    assert [c['correlacion'] for c in coincidencias] == sorted((c['correlacion'] for c in coincidencias), reverse=True)
    assert coincidencias[0]['codigo'] == 'geologist' and coincidencias[0]['ajuste'] == 'BEST_FIT'
    carreras = resultado['carreras_recomendadas']
    assert {c['codigo'] for c in carreras} == {'environmental-engineering', 'civil-engineering', 'veterinary-medicine'}
    assert all(c['via'] and all(v in coincidencias for v in c['via']) for c in carreras)


def test_p11_perfil_plano(cliente):
    avanzar_camino(cliente, cuenta='est-luis')
    for actividad in MARA:
        responder(cliente, actividad, cuenta='est-luis', opcion=3)
        completar(cliente, actividad, cuenta='est-luis')
    resultado = pedir(cliente, 'GET', '/cuentas/est-luis/instrumentos/TEST-RIASEC/resultado')
    assert resultado['perfil_plano'] is True
    assert resultado['coincidencias'] == resultado['carreras_recomendadas'] == []


def test_p12_avisos(cliente):
    avanzar_camino(cliente)
    ruta = '/cuentas/est-ana/desbloqueos?solo_no_vistos=true'
    no_vistos = pedir(cliente, 'GET', ruta)
    assert no_vistos and all(d['visto'] is False for d in no_vistos)
    assert pedir(cliente, 'POST', '/cuentas/est-ana/desbloqueos/marcar-vistos')['marcados'] == len(no_vistos)
    assert pedir(cliente, 'GET', ruta) == []


def test_p13_progreso_de_lo_bloqueado(cliente):
    completar(cliente, 'mission-welcome')
    ciudad = progreso(cliente, 'BLOQUE', 'CIUDAD')['reglas'][0]['condiciones'][0]
    assert (ciudad['tipo_evento'], ciudad['referencia'], ciudad['actual'], ciudad['requerido']) == ('COMPLETA_BLOQUE', 'CAMINO', 0, 1)
    insignia = progreso(cliente, 'INSIGNIA', 'I2')['reglas'][0]
    assert insignia['condiciones'][0]['cumplida'] is True
    assert insignia['evaluador_especial'] == {'nombre': 'misiones_camino_sin_inicio', 'cumplido': False}
    cierre = progreso(cliente, 'ACTIVIDAD', 'act-tip-final')['reglas'][0]['condiciones'][0]
    assert (cierre['referencia'], cierre['actual'], cierre['requerido']) == ('act-tip-14', 0, 1)


def test_p14_audiencia(cliente):
    rosa = estado(cliente, 'apo-rosa')
    assert rosa['bloques'] == rosa['fichas'] == rosa['insignias'] == []
    assert rosa['nivel_actual'] is None


def test_p15_semillas_separadas(cliente, aplicacion, tmp_path):
    ruta = tmp_path / 'demo.db'
    with TestClient(crear_aplicacion(f'sqlite:///{ruta.as_posix()}', semilla='demo')):
        pass
    antes = ruta.read_bytes()
    with pytest.raises(RuntimeError) as error:
        with TestClient(crear_aplicacion(f'sqlite:///{ruta.as_posix()}', semilla='plataforma')):
            pass
    assert str(error.value) == ('La base demo.db fue creada con la semilla demo; la aplicación está configurada '
                                'con plataforma. Usa otra RUTA_BD o borra el archivo.')
    assert ruta.read_bytes() == antes
    inicial = filas_base(aplicacion)
    cache = aplicacion.state.motor_bd.cache_definiciones.actual
    avanzar_camino(cliente)
    pedir(cliente, 'POST', '/demo/reiniciar')
    assert filas_base(aplicacion) == inicial
    assert aplicacion.state.motor_bd.cache_definiciones.actual is not cache
    assert aplicacion.state.posiciones_registro == {}
    assert actividades(cliente)['mission-welcome'] == 'DISPONIBLE'
    assert eventos(cliente) == []
    with aplicacion.state.fabrica_sesiones() as sesion:
        assert sesion.scalar(select(modelos.EsquemaVersion.semilla)) == 'plataforma'
        assert sesion.scalar(select(func.count()).select_from(modelos.Ocupacion)) == 36
    # Otro arranque conserva la semilla y valida sus CHECK vigentes.
    with TestClient(crear_aplicacion(f'sqlite:///{Path(aplicacion.state.motor_bd.url.database).as_posix()}', semilla='plataforma')) as nuevo:
        assert estado(nuevo) == estado(cliente)


def test_p16_eventos_nuevos(cliente):
    for evento, insignia in (('INVITA_A_CREW', 'I4'), ('FORMA_CREW', 'I5'), ('VENCE_DESAFIO_INTACTO', 'I10')):
        respuesta = pedir(cliente, 'POST', '/eventos', {'cuenta': 'est-ana', 'tipo': evento, 'fecha_hora': FECHA})
        assert reglas(respuesta) == {f'R-{insignia}'}
        assert respuesta['eventos_registrados'] == [{'tipo': evento, 'referencia': None, 'fecha_hora': FECHA}]
    oculto, = [i for i in estado(cliente)['insignias'] if i['codigo'] == 'I10']
    assert oculto['estado'] == 'OBTENIDA' and oculto['nombre'] == 'Luz sin fisuras'
    assert oculto['requisito'] == 'Vence al enemigo sin perder destellos en tu primera victoria.'
