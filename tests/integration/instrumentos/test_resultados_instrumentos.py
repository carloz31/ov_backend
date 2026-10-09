"""R29: el código opcional de ocupación se conserva en todas las consultas."""

from soporte_plataforma import pedir
from soporte_retiro import buscar, ciclo, reiniciar, resultado
from app import models as m


def test_r29_codigo_nullable_en_coincidencia_via_e_historial(cliente, aplicacion):
    ciclo(cliente)
    obtenido = resultado(cliente)
    codigo = obtenido['carreras_recomendadas'][0]['via'][0]['codigo']
    with aplicacion.state.fabrica_sesiones.begin() as sesion:
        buscar(sesion, m.Ocupacion, codigo).codigo = None
    obtenido = resultado(cliente)
    coincidencia = next(c for c in obtenido['coincidencias'] if c['codigo'] is None)
    vias = [v for c in obtenido['carreras_recomendadas'] for v in c['via']]
    assert coincidencia in vias
    reiniciar(cliente)
    historico, = pedir(cliente, 'GET', '/cuentas/est-ana/instrumentos/TEST-RIASEC/historial')
    assert historico['coincidencias'] == obtenido['coincidencias']
    assert historico['carreras_recomendadas'] == obtenido['carreras_recomendadas']
    assert historico['anulado_en'] is not None
