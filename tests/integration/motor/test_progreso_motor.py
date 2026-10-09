"""R08: explicaciones públicas de reglas genéricas."""

from soporte_datos_ports import preparar_explicaciones
from soporte_plataforma import pedir, progreso


def test_r08_explicaciones_compuestas_alternativas_y_sin_reglas(cliente, aplicacion):
    with aplicacion.state.fabrica_sesiones.begin() as sesion:
        preparar_explicaciones(sesion)
    pedir(cliente, 'POST', '/acciones/ingresar', {'cuenta': 'est-ana'})
    explicacion = progreso(cliente, 'FICHA', 'ficha-prueba')['reglas'][0]
    assert [(c['actual'], c['requerido'], c['cumplida']) for c in explicacion['condiciones']] == [(1, 2, False), (0, 1, False)]
    assert explicacion['evaluador_especial'] == {'nombre': 'misiones_camino_sin_inicio', 'cumplido': False}
    assert explicacion['cumplida'] is False
    libre = progreso(cliente, 'FICHA', 'ficha-libre')
    assert libre['reglas'] == [] and libre['disponible'] is True
    for cuenta, actual in (('est-ana', 1), ('apo-rosa', 0)):
        alternativas = pedir(cliente, 'GET', f'/cuentas/{cuenta}/progreso/CONVERSACIONES/-')['reglas']
        por_codigo = {r['regla']: r for r in alternativas}
        assert por_codigo['R-PRUEBA-OR-A']['condiciones'][0]['actual'] == actual
        assert por_codigo['R-PRUEBA-OR-B']['condiciones'][0]['actual'] == 0
