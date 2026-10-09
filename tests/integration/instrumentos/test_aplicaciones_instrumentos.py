"""R19: varias aplicaciones por actividad, selección y coste constante."""

from soporte_plataforma import MARA, pedir
from soporte_retiro import aplicaciones_extra, medir, preparar_ultimo, resultado


def test_r19_resultados_por_aplicacion_y_sql_constante(tmp_path, base_aislada):
    cantidades = []
    for extra in (1, 10):
        with base_aislada(tmp_path, f'aplicaciones-{extra}') as (aplicacion, cliente):
            with aplicacion.state.fabrica_sesiones.begin() as sesion:
                aplicaciones_extra(sesion, extra)
            preparar_ultimo(cliente)
            salida, contador = medir(cliente, aplicacion, 'POST', '/acciones/completar-actividad',
                {'cuenta': 'est-ana', 'actividad': MARA[-1]}, limite=20)
            assert {r['aplicacion'] for r in salida['resultados_generados']} == {'APL-RIASEC'} | {f'APL-PRUEBA-{n}' for n in range(extra)}
            pedir(cliente, 'GET', '/cuentas/est-ana/instrumentos/TEST-RIASEC/resultado', esperado=422)
            for codigo in ('APL-RIASEC', *(f'APL-PRUEBA-{n}' for n in range(extra))):
                assert resultado(cliente, seleccion=f'?aplicacion={codigo}')['aplicacion'] == codigo
            cantidades.append(contador.cantidad)
    assert cantidades[0] == cantidades[1]
