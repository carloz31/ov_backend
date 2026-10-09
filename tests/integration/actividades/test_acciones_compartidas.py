"""R33–R34: acciones compartidas y SQL agrupado; DATO DE PRUEBA."""

from soporte_datos_ports import agregar_autores
from soporte_datos_ports import preparar_conversacion
import pytest
from app.services import comun
from soporte_plataforma import avanzar_camino, filas_base, pedir
from soporte_retiro import medir


def test_r33_conversacion_actor_disponible_repeticion_y_rollback(cliente, aplicacion, monkeypatch):
    with aplicacion.state.fabrica_sesiones.begin() as sesion:
        preparar_conversacion(sesion)
    avanzar_camino(cliente)
    assert pedir(cliente, 'GET', '/cuentas/apo-rosa/conversaciones')['estado'] == 'BLOQUEADA'
    datos = {'cuenta': 'est-ana', 'conversacion': 'conv-prueba'}
    antes = filas_base(aplicacion)
    original = comun.registrar_eventos
    def fallar(sesion, cuenta, eventos, fecha):
        salida = original(sesion, cuenta, eventos, fecha)
        if cuenta.codigo == 'apo-rosa':
            raise RuntimeError('DATO DE PRUEBA: segunda cuenta')
        return salida
    with monkeypatch.context() as parche:
        parche.setattr(comun, 'registrar_eventos', fallar)
        with pytest.raises(RuntimeError, match='segunda cuenta'):
            pedir(cliente, 'POST', '/acciones/completar-conversacion', datos)
    assert filas_base(aplicacion) == antes
    respuesta, contador = medir(cliente, aplicacion, 'POST', '/acciones/completar-conversacion', datos, limite=12)
    assert set(respuesta['por_cuenta']) == {'est-ana', 'apo-rosa'}
    assert all([e['tipo'] for e in r['eventos_registrados']] == ['COMPLETA_CONVERSACION'] for r in respuesta['por_cuenta'].values())
    assert 'R-I6' in {d['regla'] for d in respuesta['por_cuenta']['est-ana']['nuevos_desbloqueos']}
    assert respuesta['por_cuenta']['apo-rosa']['nuevos_desbloqueos'] == []
    primera = filas_base(aplicacion)
    repetida = pedir(cliente, 'POST', '/acciones/completar-conversacion', datos)
    assert all(r['eventos_registrados'] == r['nuevos_desbloqueos'] == [] for r in repetida['por_cuenta'].values())
    assert filas_base(aplicacion) == primera
    pedir(cliente, 'POST', '/acciones/completar-conversacion', {**datos, 'cuenta': 'apo-rosa'}, 409)
    assert filas_base(aplicacion) == primera


def test_r34_coautoria_independiente_y_sql_de_dos_a_veinte(tmp_path, base_aislada):
    cantidades = []
    for cantidad in (2, 20):
        with base_aislada(tmp_path, f'autores-{cantidad}') as (aplicacion, cliente):
            autores = ['est-ana', 'est-luis']
            with aplicacion.state.fabrica_sesiones.begin() as sesion:
                agregar_autores(sesion, cantidad, autores)
            # Ana ya tiene la insignia; la nueva publicación se evalúa individualmente.
            pedir(cliente, 'POST', '/acciones/publicar-entrevista', {'autores': ['est-ana'], 'resumen': 'DATO DE PRUEBA'})
            respuesta, contador = medir(cliente, aplicacion, 'POST', '/acciones/publicar-entrevista',
                {'autores': autores, 'resumen': 'DATO DE PRUEBA'})
            assert set(respuesta['por_cuenta']) == set(autores)
            for codigo, salida in respuesta['por_cuenta'].items():
                assert [e['tipo'] for e in salida['eventos_registrados']] == ['PUBLICA_ENTREVISTA']
                assert ('R-I8' in {d['regla'] for d in salida['nuevos_desbloqueos']}) == (codigo != 'est-ana')
            cantidades.append(contador.cantidad)
    assert cantidades[0] == cantidades[1]
