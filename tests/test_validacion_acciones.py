"""R40: tipo, audiencia, vínculo y referencias, sin efectos."""

from soporte_datos_ports import preparar_validacion
from soporte_plataforma import avanzar_camino, filas_base, pedir


def test_r40_rechazos_de_acciones_y_consultas_sin_efectos(cliente, aplicacion):
    with aplicacion.state.fabrica_sesiones.begin() as sesion:
        preparar_validacion(sesion)
    avanzar_camino(cliente)
    entradas = [
        ('/acciones/resolver-caso', {'cuenta': 'est-ana', 'actividad': 'mission-welcome', 'puntaje': 70}, 409),
        ('/acciones/responder-items', {'cuenta': 'est-ana', 'actividad': 'mission-welcome', 'respuestas': [{'item': 'RIASEC-01', 'opcion': 3}]}, 409),
        ('/acciones/responder-items', {'cuenta': 'apo-rosa', 'actividad': 'act-tip-01', 'respuestas': [{'item': 'RIASEC-01', 'opcion': 3}]}, 404),
        ('/acciones/completar-actividad', {'cuenta': 'apo-rosa', 'actividad': 'act-tip-01'}, 404),
        ('/acciones/escribir-carta', {'cuenta': 'est-luis', 'texto': 'DATO DE PRUEBA'}, 409),
        ('/acciones/escribir-entrada', {'cuenta': 'apo-rosa', 'origen': 'LIBRE', 'texto': 'DATO DE PRUEBA'}, 409),
        ('/acciones/completar-conversacion', {'cuenta': 'est-luis', 'conversacion': 'conv-prueba'}, 409),
        ('/acciones/completar-actividad', {'cuenta': 'apo-rosa', 'actividad': 'mission-welcome'}, 409),
        ('/acciones/publicar-entrevista', {'autores': ['apo-rosa'], 'resumen': 'DATO DE PRUEBA'}, 409),
        ('/acciones/check-in', {'cuenta': 'apo-rosa', 'nivel_seguridad': 3}, 409),
    ]
    consultas = [('/actividades/no-existe/items', 404), ('/cuentas/est-ana/actividades/no-existe/respuestas', 404),
        ('/cuentas/est-ana/instrumentos/no-existe/resultado', 404),
        ('/cuentas/est-ana/instrumentos/TEST-RIASEC/resultado?aplicacion=APL-PRUEBA-UNICA', 404),
        ('/cuentas/est-ana/instrumentos/TEST-RIASEC/comparacion', 404)]
    for cuenta in ('no-existe', 'apo-rosa'):
        consultas += [(f'/cuentas/{cuenta}/{ruta}', 404) for ruta in ('instrumentos',
            'actividades/act-tip-01/respuestas', 'instrumentos/TEST-RIASEC/resultado',
            'instrumentos/TEST-RIASEC/historial', 'instrumentos/TEST-RIASEC/comparacion')]
    for ruta, datos, esperado in entradas:
        antes = filas_base(aplicacion)
        pedir(cliente, 'POST', ruta, datos, esperado)
        assert filas_base(aplicacion) == antes
    for ruta, esperado in consultas:
        antes = filas_base(aplicacion)
        pedir(cliente, 'GET', ruta, esperado=esperado)
        assert filas_base(aplicacion) == antes
