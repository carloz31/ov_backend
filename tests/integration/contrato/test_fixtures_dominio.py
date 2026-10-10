"""Fixtures por dominio y acciones de plataforma y piloto, reproducibles."""

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from pydantic import TypeAdapter
from scripts import exportar_fixtures_front as exportador

from app import main as principal
from app.schemas.actividades import BloqueActividades
from app.schemas.comun import ContenidoEstado
from app.schemas.cuentas import ResumenCuenta
from app.schemas.logros import LogrosCuenta


NUEVOS = {
    'resumen-inicial.json', 'actividades-inicial.json', 'actividades-ciudad.json',
    'fichas-inicial.json', 'fichas-ciudad.json', 'logros-inicial.json', 'logros-ciudad.json',
    'piloto-actividades-inicial.json', 'piloto-actividades-ciudad.json', 'piloto-actividades-final.json',
}


def test_exportacion_completa_reproducible_y_compatible(tmp_path, monkeypatch):
    monkeypatch.setenv('EVALUADOR', 'gemini')
    ajena = tmp_path / 'ajena.db'
    ajena.write_bytes(b'Conservar esta base')  # DATO DE PRUEBA: nunca se abre.
    monkeypatch.setenv('DATABASE_URL', f'sqlite:///{ajena.as_posix()}')
    crear_evaluador = principal.crear_evaluador_registro
    evaluadores = []

    def solo_falso(configuracion):
        evaluadores.append(configuracion.evaluador)
        assert configuracion.evaluador == 'falso'
        return crear_evaluador(configuracion)

    monkeypatch.setattr(principal, 'crear_evaluador_registro', solo_falso)
    originales = exportador.exportar_fixtures(tmp_path / 'originales')
    bytes_originales = {ruta.name: ruta.read_bytes() for ruta in originales}
    destino = tmp_path / 'completos'
    rutas = exportador.exportar_fixtures(destino, por_dominio=True)
    assert {ruta.name for ruta in rutas} == set(bytes_originales) | NUEVOS
    assert len(rutas) == 22
    assert {nombre: (destino / nombre).read_bytes() for nombre in bytes_originales} == bytes_originales
    datos = {ruta.name: json.loads(ruta.read_text(encoding='utf-8')) for ruta in rutas}
    datos_originales = {nombre: json.loads(contenido) for nombre, contenido in bytes_originales.items()}
    ResumenCuenta.model_validate(datos['resumen-inicial.json'])
    assert datos['resumen-inicial.json'] == datos_originales['resumen-inicial.json']
    for momento in ('inicial', 'ciudad'):
        bloques = TypeAdapter(list[BloqueActividades]).validate_python(datos[f'actividades-{momento}.json'])
        assert [len(b.actividades) for b in bloques] == [9, 15]
        TypeAdapter(list[ContenidoEstado]).validate_python(datos[f'fichas-{momento}.json'])
        LogrosCuenta.model_validate(datos[f'logros-{momento}.json'])
        assert datos[f'fichas-{momento}.json'] == datos_originales[f'fichas-{momento}.json']
        assert datos[f'logros-{momento}.json'] == datos_originales[f'logros-{momento}.json']
    for momento in ('inicial', 'ciudad', 'final'):
        bloques = TypeAdapter(list[BloqueActividades]).validate_python(datos[f'piloto-actividades-{momento}.json'])
        assert [len(b.actividades) for b in bloques] == [5, 16]
        ciudad = bloques[1]
        assert ciudad.estado == ('BLOQUEADA' if momento == 'inicial' else 'DISPONIBLE')
        elena = next(a for a in ciudad.actividades if a.codigo == 'act-tip-final')
        assert elena.visible is (momento == 'final')
        assert ciudad.actividades[-1].contenido == 'sin_contenido_prueba'
        assert ciudad.actividades[-1].visible is True
    assert [a['estado'] for a in datos['piloto-actividades-final.json'][0]['actividades']] == [
        'COMPLETADA', 'COMPLETADA', 'DISPONIBLE', 'BLOQUEADA', 'BLOQUEADA',
    ]
    contenido = {ruta.name: ruta.read_bytes() for ruta in rutas}
    conservar = destino / 'conservar.txt'
    conservar.write_text('Conservar', encoding='utf-8')
    exportador.exportar_fixtures(destino, por_dominio=True)
    assert {ruta.name: ruta.read_bytes() for ruta in rutas} == contenido
    assert conservar.read_text(encoding='utf-8') == 'Conservar'
    assert ajena.read_bytes() == b'Conservar esta base'
    assert evaluadores == ['falso'] * 5
    assert os.environ['EVALUADOR'] == 'gemini'


def test_fallo_del_piloto_no_escribe_nada_y_restaura_evaluador(tmp_path, monkeypatch):
    monkeypatch.delenv('EVALUADOR', raising=False)
    destino = tmp_path / 'sin-publicar'

    def fallar(cliente):
        raise RuntimeError('Fallo de prueba del piloto')

    monkeypatch.setattr(exportador, '_recorrer_piloto', fallar)
    with pytest.raises(RuntimeError, match='Fallo de prueba del piloto'):
        exportador.exportar_fixtures(destino, por_dominio=True)
    assert not destino.exists()
    assert 'EVALUADOR' not in os.environ


def test_cli_exporta_los_veintidos_fixtures(tmp_path):
    script = Path(exportador.__file__).resolve()
    destino = tmp_path / 'front' / 'tests' / 'fixtures' / 'servidor'
    resultado = subprocess.run([sys.executable, str(script), '--destino', str(destino)],
                               cwd=tmp_path, capture_output=True, text=True)
    assert resultado.returncode == 0, resultado.stderr
    assert 'Exportados 22 fixtures' in resultado.stdout
    assert len(list(destino.glob('*.json'))) == 22
    assert NUEVOS <= {ruta.name for ruta in destino.glob('*.json')}
