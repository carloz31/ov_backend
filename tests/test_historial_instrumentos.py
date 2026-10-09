"""R21: detalle de historia, desempate por id y SQL constante."""

from soporte_datos_ports import agregar_veinte_resultados
from soporte_retiro import ciclo, medir, reiniciar, resultado


def test_r21_historial_detallado_ordenado_y_coste_constante(cliente, aplicacion):
    ciclo(cliente)
    original = resultado(cliente)
    reiniciar(cliente)
    ruta = '/cuentas/est-ana/instrumentos/TEST-RIASEC/historial'
    inicial, antes = medir(cliente, aplicacion, 'GET', ruta)
    assert inicial[0]['dimensiones'] == original['dimensiones']
    assert inicial[0]['coincidencias'] == original['coincidencias'] and inicial[0]['anulado_en'] is not None
    with aplicacion.state.fabrica_sesiones.begin() as sesion:
        agregar_veinte_resultados(sesion)
    historial, despues = medir(cliente, aplicacion, 'GET', ruta)
    assert despues.cantidad == antes.cantidad <= 10 and len(historial) == 21
    assert [h['dimensiones'][0]['porcentaje'] for h in historial[:20]] == list(reversed(range(20)))
    assert historial[-1] == inicial[0]
    assert all(h['coincidencias'] == original['coincidencias'] for h in historial)
