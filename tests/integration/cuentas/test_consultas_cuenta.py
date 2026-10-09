"""R09–R10: consultas sin efectos, códigos y aislamiento."""

from soporte_datos_ports import preparar_preguntas_respondidas
from datetime import timedelta
from app import models as m
from soporte_dominios import RUTAS_DOMINIO
from soporte_plataforma import filas_base, pedir
from soporte_retiro import FECHA_BD, agregar_eventos, buscar, ciclo, sin_ids


def test_r09_pregunta_respondida_por_cuenta_sin_confundir_libres(cliente, aplicacion):
    with aplicacion.state.fabrica_sesiones.begin() as sesion:
        preparar_preguntas_respondidas(sesion)
    for cuenta, esperados in [('est-ana', [True, False]), ('est-luis', [False, True])]:
        preguntas = pedir(cliente, 'GET', f'/cuentas/{cuenta}/diario/preguntas')
        assert [p['respondida'] for p in preguntas] == esperados


def test_r10_gets_sin_efectos_ni_ids_e_historial_ordenado(cliente, aplicacion):
    ciclo(cliente)
    with aplicacion.state.fabrica_sesiones.begin() as sesion:
        ana, luis = [buscar(sesion, m.Cuenta, c) for c in ('est-ana', 'est-luis')]
        agregar_eventos(sesion, ana, [(tipo, None, FECHA_BD + timedelta(days=d)) for tipo, d in [('INGRESO', 3), ('RESPUESTA_REFLEXIVA', 2), ('FORMA_CREW', 3)]])
        agregar_eventos(sesion, luis, [('ESCRIBE_CARTA', None, FECHA_BD + timedelta(days=4))])
    antes = filas_base(aplicacion)
    rutas = ['/cuentas'] + [f'/cuentas/est-ana/{r}' for r in RUTAS_DOMINIO] + [
        '/cuentas/est-ana/eventos', '/instrumentos', '/actividades/act-tip-01/items',
        '/cuentas/est-ana/actividades/act-tip-01/respuestas', '/cuentas/est-ana/instrumentos',
        '/cuentas/est-ana/instrumentos/TEST-RIASEC/resultado', '/cuentas/est-ana/instrumentos/TEST-RIASEC/historial']
    for ruta in rutas:
        sin_ids(pedir(cliente, 'GET', ruta))
    eventos = pedir(cliente, 'GET', '/cuentas/est-ana/eventos')
    assert [e['fecha_hora'] for e in eventos] == sorted((e['fecha_hora'] for e in eventos), reverse=True)
    assert [e['tipo'] for e in eventos[:3]] == ['FORMA_CREW', 'INGRESO', 'RESPUESTA_REFLEXIVA']
    assert not any(e['tipo'] == 'ESCRIBE_CARTA' for e in eventos)
    assert filas_base(aplicacion) == antes
