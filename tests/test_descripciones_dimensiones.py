"""Anexo de cierre, perfil y resultados · F2: textos de catálogo y resultado."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.parametros import DESCRIPCIONES_RIASEC
from datos.demo.instrumentos import DESCRIPCIONES_INTELIGENCIAS
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


@pytest.mark.parametrize('fixture', ['aplicacion', 'aplicacion_plataforma'])
def test_resultado_riasec_incluye_las_seis_descripciones_reales(request, fixture):
    aplicacion = request.getfixturevalue(fixture)
    with TestClient(aplicacion) as cliente:
        if fixture == 'aplicacion_plataforma':
            avanzar_camino(cliente)
            actividades = MARA
        else:
            actividades = tuple(f'LAB-RIA{n}' for n in range(1, 5))
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


def test_inteligencias_expone_descripciones_tambien_en_destacadas_y_conserva_habilidades(cliente):
    completar_cuestionario(cliente, ('LAB-INT1', 'LAB-INT2'))
    respuesta = cliente.get('/cuentas/est-ana/instrumentos/TEST-INT/resultado')
    assert respuesta.status_code == 200, respuesta.text
    resultado = respuesta.json()
    assert {d['codigo']: d['descripcion'] for d in resultado['dimensiones']} == DESCRIPCIONES_INTELIGENCIAS
    assert resultado['dimensiones_destacadas'] == resultado['dimensiones']
    assert len(resultado['dimensiones_destacadas']) == 7
    catalogo = cliente.get('/instrumentos')
    assert catalogo.status_code == 200, catalogo.text
    habilidades = next(i for i in catalogo.json() if i['codigo'] == 'TEST-HAB')
    assert all(d['descripcion'] == f"Dimensión de demostración: {d['nombre']}."
               for d in habilidades['dimensiones'])


def test_descripciones_coinciden_con_los_textos_aprobados_del_anexo():
    anexo = (Path(__file__).resolve().parents[1] /
             'docs/iteraciones/spec-iteracion-1-cierre-perfil-resultados.md').read_text(encoding='utf-8')
    for codigo, texto in {**DESCRIPCIONES_RIASEC, **DESCRIPCIONES_INTELIGENCIAS}.items():
        filas = [linea.split('|') for linea in anexo.splitlines() if linea.startswith(f'| {codigo} |')]
        assert len(filas) == 2  # Descripción y ejemplos de presentación.
        assert filas[0][3].strip() == texto
