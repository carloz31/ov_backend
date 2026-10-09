"""R39: descripciones aprobadas en catálogo, destacadas e historial."""

from pathlib import Path
from soporte_descripciones import DESCRIPCIONES_INTELIGENCIAS
from soporte_plataforma import pedir
from soporte_retiro import contestar_minimo, instrumento_minimo, resultado


def test_r39_textos_aprobados_se_propagan_a_resultados(cliente, aplicacion):
    anexo = (Path(__file__).resolve().parents[3] / 'docs/iteraciones/spec-iteracion-1-cierre-perfil-resultados.md').read_text(encoding='utf-8')
    for codigo, descripcion in DESCRIPCIONES_INTELIGENCIAS.items():
        assert f'| {codigo} |' in anexo and descripcion in anexo
    with aplicacion.state.fabrica_sesiones.begin() as sesion:
        actividad, = instrumento_minimo(sesion, descripciones=DESCRIPCIONES_INTELIGENCIAS)
    catalogo = next(i for i in pedir(cliente, 'GET', '/instrumentos') if i['codigo'] == 'TEST-PRUEBA')
    assert {d['codigo']: d['descripcion'] for d in catalogo['dimensiones']} == DESCRIPCIONES_INTELIGENCIAS
    contestar_minimo(cliente, actividad, [5, 1, 5, 5, 5, 5, 5])
    obtenido = resultado(cliente, instrumento='TEST-PRUEBA')
    assert {d['codigo']: d['descripcion'] for d in obtenido['dimensiones']} == DESCRIPCIONES_INTELIGENCIAS
    assert obtenido['dimensiones_destacadas'] == obtenido['dimensiones']
    historial, = pedir(cliente, 'GET', '/cuentas/est-ana/instrumentos/TEST-PRUEBA/historial')
    assert historial['dimensiones'] == obtenido['dimensiones']
    assert historial['dimensiones_destacadas'] == obtenido['dimensiones_destacadas']
