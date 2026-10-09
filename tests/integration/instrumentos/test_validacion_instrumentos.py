"""R13 y R23: lotes y reinicios inválidos sin escrituras."""

from soporte_plataforma import avanzar_camino, filas_base, pedir, responder
from soporte_retiro import aplicaciones_extra, datos_respuestas, medir


def test_r13_lote_mixto_se_valida_antes_de_escribir(tmp_path, base_aislada):
    for existente in (False, True):
        for fallo in ('item', 'opcion'):
            with base_aislada(tmp_path, f'mixto-{existente}-{fallo}') as (aplicacion, cliente):
                avanzar_camino(cliente)
                if existente:
                    responder(cliente, 'act-tip-01')
                datos = datos_respuestas(cliente, opcion=5)
                if fallo == 'item':
                    datos['respuestas'][-1]['item'] = 'RIASEC-06'
                else:
                    datos['respuestas'][-1]['opcion'] = 999
                antes = filas_base(aplicacion)
                medir(cliente, aplicacion, 'POST', '/acciones/responder-items', datos,
                      esperado=409 if fallo == 'item' else 422)
                assert filas_base(aplicacion) == antes


def test_r23_reinicios_invalidos_y_vacios_sin_efectos(cliente, aplicacion):
    datos = {'cuenta': 'est-ana', 'instrumento': 'TEST-RIASEC'}
    variantes = [({}, 409), ({'cuenta': 'no-existe'}, 404), ({'cuenta': 'apo-rosa'}, 404),
        ({'instrumento': 'no-existe'}, 404), ({'aplicacion': 'no-existe'}, 404),
        ({'fecha_hora': 'invalida'}, 422)]
    for cambios, esperado in variantes:
        antes = filas_base(aplicacion)
        pedir(cliente, 'POST', '/acciones/reiniciar-instrumento', {**datos, **cambios}, esperado)
        assert filas_base(aplicacion) == antes
    with aplicacion.state.fabrica_sesiones.begin() as sesion:
        aplicaciones_extra(sesion, 1)
    for cambios, esperado in [({}, 422), ({'aplicacion': 'APL-RIASEC'}, 409), ({'aplicacion': 'APL-PRUEBA-0'}, 409)]:
        antes = filas_base(aplicacion)
        pedir(cliente, 'POST', '/acciones/reiniciar-instrumento', {**datos, **cambios}, esperado)
        assert filas_base(aplicacion) == antes
