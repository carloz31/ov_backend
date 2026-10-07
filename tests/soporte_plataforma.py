"""Fixtures locales y recorridos de plataforma; no cambia las fixtures de demo."""

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select

from app.database import Base
from app.main import crear_aplicacion


FECHA = '2026-10-07T10:00:00'
CAMINO = ('mission-welcome', 'enc-mitos', 'act-07', 'mission-story', 'mission-future',
          'mission-compass', 'act-06', 'mission-expectations', 'mission-next-step')
MARA = tuple(f'act-tip-{n:02}' for n in range(1, 15))


@pytest.fixture
def aplicacion(tmp_path):
    return crear_aplicacion(f'sqlite:///{(tmp_path / "plataforma.db").as_posix()}', semilla='plataforma')


@pytest.fixture
def cliente(aplicacion):
    with TestClient(aplicacion) as abierto:
        yield abierto


@pytest.fixture
def sesion(cliente, aplicacion):
    with aplicacion.state.fabrica_sesiones() as abierta:
        yield abierta


def pedir(cliente, metodo, ruta, datos=None, esperado=200):
    respuesta = cliente.request(metodo, ruta, json=datos)
    assert respuesta.status_code == esperado, respuesta.text
    return respuesta.json()


def completar(cliente, codigo, cuenta='est-ana', esperado=200):
    return pedir(cliente, 'POST', '/acciones/completar-actividad',
                 {'cuenta': cuenta, 'actividad': codigo, 'fecha_hora': FECHA}, esperado)


def avanzar_camino(cliente, hasta=None, cuenta='est-ana'):
    ultimo = len(CAMINO) if hasta is None else CAMINO.index(hasta) + 1
    for codigo in CAMINO[:ultimo]:
        respuesta = completar(cliente, codigo, cuenta)
    return respuesta


def responder(cliente, actividad, cuenta='est-ana', opcion=None, inicio=0, fin=None):
    items = pedir(cliente, 'GET', f'/actividades/{actividad}/items')[inicio:fin]
    opciones = {'I': 5, 'R': 4, 'A': 3, 'S': 1, 'E': 1, 'C': 1}
    return pedir(cliente, 'POST', '/acciones/responder-items', {
        'cuenta': cuenta, 'actividad': actividad, 'fecha_hora': FECHA,
        'respuestas': [{'item': item['codigo'], 'opcion': opcion if opcion is not None else opciones[item['dimension']]}
                       for item in items],
    })


def estado(cliente, cuenta='est-ana'):
    return pedir(cliente, 'GET', f'/cuentas/{cuenta}/estado')


def actividades(cliente, cuenta='est-ana'):
    return {actividad['codigo']: actividad['estado'] for bloque in estado(cliente, cuenta)['bloques']
            for actividad in bloque['actividades']}


def progreso(cliente, tipo, codigo):
    return pedir(cliente, 'GET', f'/cuentas/est-ana/progreso/{tipo}/{codigo}')


def eventos(cliente, cuenta='est-ana'):
    return pedir(cliente, 'GET', f'/cuentas/{cuenta}/eventos')


def reglas(respuesta):
    return {nuevo['regla'] for nuevo in respuesta['nuevos_desbloqueos']}


def filas_base(aplicacion):
    with aplicacion.state.fabrica_sesiones() as sesion:
        return {tabla.name: sesion.execute(select(tabla).order_by(*tabla.primary_key.columns)).all()
                for tabla in Base.metadata.sorted_tables}
