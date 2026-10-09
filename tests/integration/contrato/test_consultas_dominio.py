"""Contrato de las siete consultas por dominio."""

import pytest
from sqlalchemy import select

from app.models import Actividad, Bloque, Cuenta, EstadoProgreso, ProgresoActividad, Visibilidad
from datos.plataforma import (
    ACTIVIDADES_CAMINO, ACTIVIDADES_CIUDAD, CONTENIDOS_ACTIVIDADES, FICHAS, INSIGNIAS, NIVELES,
)
from soporte_plataforma import CAMINO, avanzar_camino, completar, pedir, responder


RUTAS = ('resumen', 'actividades', 'fichas', 'logros', 'testimonios', 'diario/preguntas', 'conversaciones')


def consultar(cliente, ruta, cuenta='est-ana'):
    return pedir(cliente, 'GET', f'/cuentas/{cuenta}/{ruta}')


def esperado(ruta, completo):
    if ruta == 'resumen':
        numero = 3 if completo else 1
        return {'cuenta': {'codigo': 'est-ana', 'nombre': 'Ana', 'rol': 'ESTUDIANTE'},
                'nivel_actual': {'numero': numero, 'titulo': NIVELES[numero - 1][1]}}
    if ruta == 'actividades':
        bloques = []
        for codigo, nombre, numero, espacio, catalogo in (
            ('CAMINO', 'El camino', 1, 'MISIONES_CAMPO', ACTIVIDADES_CAMINO),
            ('CIUDAD', 'La ciudad', 2, 'CIUDAD', ACTIVIDADES_CIUDAD),
        ):
            estados = (['COMPLETADA'] * 9 if completo else ['DISPONIBLE'] + ['BLOQUEADA'] * 8) if codigo == 'CAMINO' else (
                ['DISPONIBLE'] + ['BLOQUEADA'] * 14 if completo else ['BLOQUEADA'] * 15
            )
            bloques.append({
                'codigo': codigo, 'nombre': nombre, 'numero': numero, 'espacio': espacio,
                'estado': 'DISPONIBLE' if codigo == 'CAMINO' or completo else 'BLOQUEADA',
                'actividades': [
                    {'codigo': actividad, 'titulo': titulo, 'tipo': tipo, 'orden': orden,
                     'contenido': CONTENIDOS_ACTIVIDADES[actividad], 'visibilidad': 'SIEMPRE',
                     'visible': True, 'estado': estado}
                    for orden, ((actividad, titulo, tipo), estado) in enumerate(zip(catalogo, estados, strict=True), 1)
                ],
            })
        return bloques
    if ruta == 'fichas':
        return [{'codigo': codigo, 'titulo': titulo, 'estado': 'DISPONIBLE' if completo else 'BLOQUEADA'}
                for codigo, titulo, _ in sorted(FICHAS)]
    if ruta == 'logros':
        insignias = []
        for codigo, nombre, descripcion, requisito, oculta in sorted(INSIGNIAS):
            insignias.append(
                {'codigo': '???', 'nombre': 'Logro oculto', 'descripcion': None, 'requisito': None, 'estado': 'BLOQUEADA'}
                if oculta else {'codigo': codigo, 'nombre': nombre, 'descripcion': descripcion,
                                'requisito': requisito, 'estado': 'OBTENIDA' if completo and codigo in ('I1', 'I2', 'I3') else 'BLOQUEADA'}
            )
        return {'insignias': insignias, 'niveles': [
            {'numero': numero, 'titulo': titulo, 'estado': 'OBTENIDO' if numero <= (3 if completo else 1) else 'BLOQUEADO'}
            for numero, titulo in NIVELES
        ]}
    if ruta == 'conversaciones':
        return {'estado': 'DISPONIBLE' if completo else 'BLOQUEADA'}
    return []


@pytest.mark.parametrize('ruta', RUTAS)
@pytest.mark.parametrize('completo', [False, True], ids=['inicio', 'camino_completo'])
def test_contrato_y_valores_plataforma(cliente, ruta, completo):
    if completo:
        avanzar_camino(cliente)
    assert consultar(cliente, ruta) == esperado(ruta, completo)


@pytest.mark.parametrize('ruta', RUTAS)
def test_cuenta_inexistente(cliente, ruta):
    respuesta = cliente.get(f'/cuentas/no-existe/{ruta}')
    assert respuesta.status_code == 404
    assert respuesta.json() == {'detail': 'Cuenta no encontrada'}


@pytest.mark.parametrize('ruta', RUTAS)
def test_apoderado_sin_listas_estudiantiles(cliente, ruta):
    respuesta = consultar(cliente, ruta, 'apo-rosa')
    if ruta == 'resumen':
        assert respuesta == {'cuenta': {'codigo': 'apo-rosa', 'nombre': 'Rosa', 'rol': 'APODERADO'}, 'nivel_actual': None}
    elif ruta == 'logros':
        assert respuesta == {'insignias': [], 'niveles': []}
    elif ruta == 'conversaciones':
        assert respuesta == {'estado': 'BLOQUEADA'}
    else:
        assert respuesta == []


@pytest.mark.parametrize('visibilidad', list(Visibilidad))
@pytest.mark.parametrize('estado', ['BLOQUEADA', 'DISPONIBLE', 'EN_CURSO', 'COMPLETADA'])
def test_visibilidad_no_oculta_filas_ni_titulos(sesion, cliente, visibilidad, estado):
    codigo = 'enc-mitos' if estado == 'BLOQUEADA' else 'mission-welcome'
    actividad = sesion.scalar(select(Actividad).where(Actividad.codigo == codigo))
    actividad.visibilidad = visibilidad  # DATO DE PRUEBA: variante temporal, sin cambiar plataforma.
    if estado in ('EN_CURSO', 'COMPLETADA'):
        ana = sesion.scalar(select(Cuenta).where(Cuenta.codigo == 'est-ana'))
        sesion.add(ProgresoActividad(cuenta_id=ana.id, actividad_id=actividad.id, estado=EstadoProgreso(estado)))
    sesion.commit()
    actividades = consultar(cliente, 'actividades')[0]['actividades']
    assert len(actividades) == 9
    recibida = next(fila for fila in actividades if fila['codigo'] == codigo)
    assert recibida['titulo'] == actividad.titulo
    assert recibida['estado'] == estado
    assert recibida['visibilidad'] == visibilidad.value
    assert recibida['visible'] is (visibilidad == Visibilidad.SIEMPRE or estado != 'BLOQUEADA')


def test_actividad_al_desbloquear_cambia_de_visible_con_la_accion(sesion, cliente):
    actividad = sesion.scalar(select(Actividad).where(Actividad.codigo == 'enc-mitos'))
    actividad.visibilidad = Visibilidad.AL_DESBLOQUEAR  # DATO DE PRUEBA.
    sesion.commit()
    assert consultar(cliente, 'actividades')[0]['actividades'][1]['visible'] is False
    completar(cliente, 'mission-welcome')
    recibida = consultar(cliente, 'actividades')[0]['actividades'][1]
    assert recibida['estado'] == 'DISPONIBLE' and recibida['visible'] is True


@pytest.mark.parametrize('codigo', ['enc-mitos', 'act-tip-01'], ids=['actividad_bloqueada', 'bloque_bloqueado'])
def test_bloqueo_prevalece_sobre_progreso(sesion, cliente, codigo):
    ana = sesion.scalar(select(Cuenta).where(Cuenta.codigo == 'est-ana'))
    actividad = sesion.scalar(select(Actividad).where(Actividad.codigo == codigo))
    sesion.add(ProgresoActividad(cuenta_id=ana.id, actividad_id=actividad.id, estado=EstadoProgreso.COMPLETADA))
    sesion.commit()
    recibida = next(a for b in consultar(cliente, 'actividades') for a in b['actividades'] if a['codigo'] == codigo)
    assert recibida['estado'] == 'BLOQUEADA'


def test_cuestionario_en_curso_y_lecturas_aisladas_por_cuenta(cliente):
    avanzar_camino(cliente)
    responder(cliente, 'act-tip-01', fin=3)
    assert consultar(cliente, 'actividades')[1]['actividades'][0]['estado'] == 'EN_CURSO'
    for ruta in RUTAS:
        luis = consultar(cliente, ruta, 'est-luis')
        if ruta == 'resumen':
            inicial = esperado(ruta, False)
            inicial['cuenta'] = {'codigo': 'est-luis', 'nombre': 'Luis', 'rol': 'ESTUDIANTE'}
        else:
            inicial = esperado(ruta, False)
        assert luis == inicial


def test_orden_por_numero_y_codigo_y_por_orden_y_codigo(sesion, cliente):
    # DATO DE PRUEBA: el empate y el orden inverso distinguen ambas claves de ordenación.
    ciudad = sesion.scalar(select(Bloque).where(Bloque.codigo == 'CIUDAD'))
    ciudad.numero = 0
    welcome = sesion.scalar(select(Actividad).where(Actividad.codigo == 'mission-welcome'))
    welcome.orden = 2
    sesion.commit()
    bloques = consultar(cliente, 'actividades')
    assert [b['codigo'] for b in bloques] == ['CIUDAD', 'CAMINO']
    assert [a['codigo'] for a in bloques[1]['actividades'][:2]] == ['enc-mitos', 'mission-welcome']
    ciudad.numero = 1
    sesion.commit()
    assert [b['codigo'] for b in consultar(cliente, 'actividades')] == ['CAMINO', 'CIUDAD']


def test_insignia_oculta_solo_se_revela_al_obtenerse(cliente):
    ocultas = [i for i in consultar(cliente, 'logros')['insignias'] if i['codigo'] == '???']
    assert ocultas == [{'codigo': '???', 'nombre': 'Logro oculto', 'descripcion': None, 'requisito': None, 'estado': 'BLOQUEADA'}]
    pedir(cliente, 'POST', '/eventos', {'cuenta': 'est-ana', 'tipo': 'VENCE_DESAFIO_INTACTO'})
    insignias = consultar(cliente, 'logros')['insignias']
    assert not any(i['codigo'] == '???' for i in insignias)
    revelada = next(i for i in insignias if i['codigo'] == 'I10')
    assert revelada['estado'] == 'OBTENIDA' and revelada['descripcion'] and revelada['requisito']
