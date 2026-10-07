"""Exporta §4.5 desde la API, con datos de prueba y sin servicios externos."""

import argparse
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# DATO DE PRUEBA: fecha y respuestas explícitas para reproducir P1/P2/P7/P10/P12.
FECHA = '2026-10-07T10:00:00'
OPCIONES = {'I': 5, 'R': 4, 'A': 3, 'S': 1, 'E': 1, 'C': 1}
CAMINO = ('mission-welcome', 'enc-mitos', 'act-07', 'mission-story', 'mission-future',
          'mission-compass', 'act-06', 'mission-expectations', 'mission-next-step')


def _pedir(cliente, metodo, ruta, datos=None):
    respuesta = cliente.request(metodo, ruta, json=datos)
    if respuesta.status_code != 200:
        raise RuntimeError(f'{metodo} {ruta} respondió {respuesta.status_code}: {respuesta.text}')
    return respuesta.json()


def _completar(cliente, actividad):
    return _pedir(cliente, 'POST', '/acciones/completar-actividad', {
        'cuenta': 'est-ana', 'actividad': actividad, 'fecha_hora': FECHA,
    })


def _recorrer(cliente):
    fixtures = {'estado-inicial.json': _pedir(cliente, 'GET', '/cuentas/est-ana/estado')}
    for actividad in CAMINO:
        respuesta = _completar(cliente, actividad)
        if actividad in ('mission-welcome', 'mission-next-step'):
            fixtures[f'completar-{actividad}.json'] = respuesta
    fixtures['estado-ciudad.json'] = _pedir(cliente, 'GET', '/cuentas/est-ana/estado')
    ruta_avisos = '/cuentas/est-ana/desbloqueos?solo_no_vistos=true'
    avisos = _pedir(cliente, 'GET', ruta_avisos)
    fixtures['desbloqueos-no-vistos.json'] = avisos
    marcados = _pedir(cliente, 'POST', '/cuentas/est-ana/desbloqueos/marcar-vistos')
    if marcados['marcados'] != len(avisos) or _pedir(cliente, 'GET', ruta_avisos) != []:
        raise RuntimeError('P12: el marcado no vació los desbloqueos no vistos')
    for numero in range(1, 15):
        actividad = f'act-tip-{numero:02}'
        items = _pedir(cliente, 'GET', f'/actividades/{actividad}/items')
        if numero == 1:
            fixtures['items-act-tip-01.json'] = items
        _pedir(cliente, 'POST', '/acciones/responder-items', {
            'cuenta': 'est-ana', 'actividad': actividad, 'fecha_hora': FECHA,
            'respuestas': [{'item': item['codigo'], 'opcion': OPCIONES[item['dimension']]}
                           for item in items],
        })
        respuesta = _completar(cliente, actividad)
        if numero == 14:
            fixtures['completar-act-tip-14.json'] = respuesta
    fixtures['resultado-riasec.json'] = _pedir(
        cliente, 'GET', '/cuentas/est-ana/instrumentos/TEST-RIASEC/resultado',
    )
    return fixtures


def exportar_fixtures(destino: Path) -> list[Path]:
    """Genera respuestas en una base desechable y escribe solo los ocho fixtures."""
    evaluador_anterior = os.environ.get('EVALUADOR')
    os.environ['EVALUADOR'] = 'falso'
    try:
        from fastapi.testclient import TestClient
        from app.main import crear_aplicacion

        with TemporaryDirectory(prefix='ov-fixtures-front-') as temporal:
            ruta_bd = Path(temporal) / 'plataforma.db'
            aplicacion = crear_aplicacion(f'sqlite:///{ruta_bd.as_posix()}', semilla='plataforma')
            with TestClient(aplicacion) as cliente:
                fixtures = _recorrer(cliente)
    finally:
        if evaluador_anterior is None:
            os.environ.pop('EVALUADOR', None)
        else:
            os.environ['EVALUADOR'] = evaluador_anterior
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    archivos = []
    for nombre, respuesta in fixtures.items():
        ruta = destino / nombre
        ruta.write_text(json.dumps(respuesta, ensure_ascii=False, indent=2, sort_keys=True) + '\n',
                        encoding='utf-8', newline='\n')
        archivos.append(ruta)
    return archivos


def main() -> None:
    argumentos = argparse.ArgumentParser(
        description='Genera los ocho fixtures de contrato en tests/fixtures/servidor de ov_frontend.',
    )
    argumentos.add_argument('--destino', type=Path,
                           help='Carpeta tests/fixtures/servidor de ov_frontend; se crea si no existe.')
    opciones = argumentos.parse_args()
    if opciones.destino is None:
        argumentos.error('Falta --destino: indica la carpeta tests/fixtures/servidor de ov_frontend.')
    try:
        archivos = exportar_fixtures(opciones.destino)
    except (OSError, ValueError, RuntimeError) as error:
        argumentos.exit(1, f'No se pudieron exportar los fixtures: {error}\n')
    print(f'Exportados {len(archivos)} fixtures en {opciones.destino.resolve()}')


if __name__ == '__main__':
    main()
