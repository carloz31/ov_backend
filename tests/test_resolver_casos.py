"""R35: intentos y umbral inclusivo; DATO DE PRUEBA."""

from soporte_datos_ports import preparar_casos
from sqlalchemy import select
from app import models as m
from soporte_plataforma import filas_base, pedir


def test_r35_intentos_extremos_umbral_y_superacion_unica(cliente, aplicacion):
    with aplicacion.state.fabrica_sesiones.begin() as sesion:
        preparar_casos(sesion)
    for minimo in (0, 70, 100):
        datos = {'cuenta': 'est-ana', 'actividad': f'caso-prueba-{minimo}'}
        antes = filas_base(aplicacion)
        pedir(cliente, 'POST', '/acciones/completar-actividad', datos, 409)
        assert filas_base(aplicacion) == antes
        if minimo:
            fallido = pedir(cliente, 'POST', '/acciones/resolver-caso', {**datos, 'puntaje': minimo-1})
            assert 'SUPERA_CASO' not in [e['tipo'] for e in fallido['eventos_registrados']]
        aprobado = pedir(cliente, 'POST', '/acciones/resolver-caso', {**datos, 'puntaje': minimo})
        assert [e['tipo'] for e in aprobado['eventos_registrados']].count('SUPERA_CASO') == 1
        for puntaje in (0, 100):
            repetido = pedir(cliente, 'POST', '/acciones/resolver-caso', {**datos, 'puntaje': puntaje})
            assert 'SUPERA_CASO' not in [e['tipo'] for e in repetido['eventos_registrados']]
    with aplicacion.state.fabrica_sesiones() as sesion:
        assert len(list(sesion.scalars(select(m.ResultadoCaso)))) == 11
