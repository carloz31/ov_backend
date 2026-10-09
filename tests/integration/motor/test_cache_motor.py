"""R14: cachés independientes y recarga exclusivamente tras commit."""

from app import models as m
from soporte_plataforma import pedir
from soporte_retiro import condicion, regla


def test_r14_cache_por_motor_commit_y_rollback(cliente, aplicacion, tmp_path, base_aislada):
    with base_aislada(tmp_path, 'otra') as (otra, otro_cliente):
        cache = aplicacion.state.motor_bd.cache_definiciones
        otra_cache = otra.state.motor_bd.cache_definiciones
        anterior, ajena = cache.actual, otra_cache.actual
        with aplicacion.state.fabrica_sesiones.begin() as sesion:
            ficha = m.Ficha(codigo='ficha-cache', titulo='DATO DE PRUEBA', contenido='DATO DE PRUEBA')
            sesion.add(ficha)
            sesion.flush()
            regla(sesion, 'R-PRUEBA-CACHE', 'FICHA', ficha.id, [condicion()])
        assert cache.actual is not anterior and otra_cache.actual is ajena
        assert any(f['codigo'] == 'ficha-cache' for f in pedir(cliente, 'GET', '/cuentas/est-ana/fichas'))
        assert not any(f['codigo'] == 'ficha-cache' for f in pedir(otro_cliente, 'GET', '/cuentas/est-ana/fichas'))
        progreso = pedir(cliente, 'GET', '/cuentas/est-ana/progreso/FICHA/ficha-cache')
        assert progreso['disponible'] is False and progreso['reglas'][0]['regla'] == 'R-PRUEBA-CACHE'
        pedir(cliente, 'POST', '/acciones/ingresar', {'cuenta': 'est-ana'})
        assert pedir(cliente, 'GET', '/cuentas/est-ana/progreso/FICHA/ficha-cache')['disponible'] is True
        confirmada = cache.actual
        with aplicacion.state.fabrica_sesiones() as sesion:
            sesion.add(m.Ficha(codigo='ficha-revertida', titulo='DATO DE PRUEBA', contenido='DATO DE PRUEBA'))
            sesion.flush()
            sesion.rollback()
        assert cache.actual is confirmada and otra_cache.actual is ajena
        assert not any(f['codigo'] == 'ficha-revertida' for f in pedir(cliente, 'GET', '/cuentas/est-ana/fichas'))
