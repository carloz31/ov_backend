"""Exporta los fixtures de plataforma y piloto (§5.4), sin servicios externos."""

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


def _recorrer(cliente, *, por_dominio=False):
    fixtures = {'estado-inicial.json': _pedir(cliente, 'GET', '/cuentas/est-ana/estado')}
    if por_dominio:
        fixtures.update(_consultas_dominio(cliente, 'inicial'))
    for actividad in CAMINO:
        respuesta = _completar(cliente, actividad)
        if actividad in ('mission-welcome', 'mission-next-step'):
            fixtures[f'completar-{actividad}.json'] = respuesta
    fixtures['estado-ciudad.json'] = _pedir(cliente, 'GET', '/cuentas/est-ana/estado')
    if por_dominio:
        fixtures.update(_consultas_dominio(cliente, 'ciudad'))
    ruta_avisos = '/cuentas/est-ana/desbloqueos?solo_no_vistos=true'
    avisos = _pedir(cliente, 'GET', ruta_avisos)
    fixtures['desbloqueos-no-vistos.json'] = avisos
    marcados = _pedir(cliente, 'POST', '/cuentas/est-ana/desbloqueos/marcar-vistos')
    if marcados['marcados'] != len(avisos) or _pedir(cliente, 'GET', ruta_avisos) != []:
        raise RuntimeError('P12: el marcado no vació los desbloqueos no vistos')
    fixtures.update(_recorrer_mara(cliente))
    return fixtures


def _consultas_dominio(cliente, momento):
    rutas = ('resumen', 'actividades', 'fichas', 'logros') if momento == 'inicial' else ('actividades', 'fichas', 'logros')
    return {f'{ruta}-{momento}.json': _pedir(cliente, 'GET', f'/cuentas/est-ana/{ruta}') for ruta in rutas}


def _recorrer_mara(cliente):
    fixtures = {}
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


def _recorrer_piloto(cliente):
    ruta = '/cuentas/est-ana/actividades'
    fixtures = {'piloto-actividades-inicial.json': _pedir(cliente, 'GET', ruta)}
    for actividad in ('mission-welcome', 'enc-mitos'):
        _completar(cliente, actividad)
    fixtures['piloto-actividades-ciudad.json'] = _pedir(cliente, 'GET', ruta)
    _recorrer_mara(cliente)
    fixtures['piloto-actividades-final.json'] = _pedir(cliente, 'GET', ruta)
    return fixtures


def exportar_fixtures(destino: Path, *, por_dominio: bool = False) -> list[Path]:
    """Conserva los ocho originales; el CLI activa los diez nuevos con por_dominio.

    Cada conjunto usa su base temporal. Se termina todo el recorrido antes de
    escribir archivos, y nunca se abre DATABASE_URL ni se usa el evaluador real.
    """
    evaluador_anterior = os.environ.get('EVALUADOR')
    os.environ['EVALUADOR'] = 'falso'
    try:
        from fastapi.testclient import TestClient
        from app.main import crear_aplicacion
        from datos.cargar import preparar_base

        with TemporaryDirectory(prefix='ov-fixtures-front-') as temporal:
            fixtures = {}
            for conjunto in ('plataforma', 'piloto') if por_dominio else ('plataforma',):
                ruta_bd = Path(temporal) / f'{conjunto}.db'
                url = f'sqlite:///{ruta_bd.as_posix()}'
                preparar_base(url, conjunto, crear_tablas=True)
                aplicacion = crear_aplicacion(url)
                with TestClient(aplicacion) as cliente:
                    if conjunto == 'piloto':
                        fixtures.update(_recorrer_piloto(cliente))
                    elif por_dominio:
                        fixtures.update(_recorrer(cliente, por_dominio=True))
                    else:
                        fixtures.update(_recorrer(cliente))
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
        description='Genera los 18 fixtures de contrato en tests/fixtures/servidor de ov_frontend.',
    )
    argumentos.add_argument('--destino', type=Path,
                           help='Carpeta tests/fixtures/servidor de ov_frontend; se crea si no existe.')
    opciones = argumentos.parse_args()
    if opciones.destino is None:
        argumentos.error('Falta --destino: indica la carpeta tests/fixtures/servidor de ov_frontend.')
    try:
        archivos = exportar_fixtures(opciones.destino, por_dominio=True)
    except (OSError, ValueError, RuntimeError) as error:
        argumentos.exit(1, f'No se pudieron exportar los fixtures: {error}\n')
    print(f'Exportados {len(archivos)} fixtures en {opciones.destino.resolve()}')


if __name__ == '__main__':
    main()
