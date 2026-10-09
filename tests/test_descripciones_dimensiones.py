"""Anexo de cierre, perfil y resultados · F2: textos de catálogo y resultado."""


import pytest
from fastapi.testclient import TestClient

from app.core.parametros import DESCRIPCIONES_RIASEC
from soporte_plataforma import MARA, avanzar_camino


def completar_cuestionario(cliente, actividades):
    # DATO DE PRUEBA: primera opción de cada escala, con fecha fija.
    for actividad in actividades:
        items = cliente.get(f'/actividades/{actividad}/items')
        assert items.status_code == 200, items.text
        respuesta = cliente.post('/acciones/responder-items', json={
            'cuenta': 'est-ana', 'actividad': actividad, 'fecha_hora': '2026-10-09T10:00:00',
            'respuestas': [{'item': item['codigo'], 'opcion': 1} for item in items.json()],
        })
        assert respuesta.status_code == 200, respuesta.text
        respuesta = cliente.post('/acciones/completar-actividad', json={
            'cuenta': 'est-ana', 'actividad': actividad, 'fecha_hora': '2026-10-09T10:00:00',
        })
        assert respuesta.status_code == 200, respuesta.text


@pytest.mark.parametrize('fixture', ['aplicacion_plataforma'])
def test_resultado_riasec_incluye_las_seis_descripciones_reales(request, fixture):
    aplicacion = request.getfixturevalue(fixture)
    with TestClient(aplicacion) as cliente:
        avanzar_camino(cliente)
        actividades = MARA
        completar_cuestionario(cliente, actividades)
        respuesta = cliente.get('/cuentas/est-ana/instrumentos/TEST-RIASEC/resultado')
        assert respuesta.status_code == 200, respuesta.text
        dimensiones = respuesta.json()['dimensiones']
        assert len(dimensiones) == 6
        assert {d['codigo']: d['descripcion'] for d in dimensiones} == DESCRIPCIONES_RIASEC
        assert all(d['descripcion'] and not d['descripcion'].startswith('Dimensión de demostración:')
                   for d in dimensiones)
        historial = cliente.get('/cuentas/est-ana/instrumentos/TEST-RIASEC/historial')
        assert historial.status_code == 200, historial.text
        assert historial.json()[0]['dimensiones'] == dimensiones
