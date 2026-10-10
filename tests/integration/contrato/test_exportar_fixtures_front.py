"""Contrato, reproducibilidad y aislamiento del exportador de §4.5."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import TypeAdapter
from scripts import exportar_fixtures_front as exportador
from soporte_plataforma import BLOQUE_FAMILIA

from app import main as principal
from app.schemas.acciones import RespuestaCompletarActividad
from app.schemas.cuentas import CuentaResumen, DesbloqueoLegible, ResumenCuenta
from app.schemas.actividades import BloqueActividades
from app.schemas.comun import ContenidoEstado
from app.schemas.logros import LogrosCuenta
from app.schemas.instrumentos import ItemPublico, ResultadoPublico


SCRIPT = Path(exportador.__file__).resolve()
NOMBRES = {
    'resumen-inicial.json', 'actividades-inicial.json', 'actividades-ciudad.json',
    'fichas-inicial.json', 'fichas-ciudad.json', 'logros-inicial.json', 'logros-ciudad.json',
    'completar-mission-welcome.json', 'completar-mission-next-step.json',
    'items-act-tip-01.json', 'completar-act-tip-14.json',
    'resultado-riasec.json', 'desbloqueos-no-vistos.json',
    'cuentas.json', 'apoderado-actividades-inicial.json',
    'apoderado-completar-pad-01-rol.json', 'apoderado-actividades-pad-01.json',
    'apoderado-completar-pad-02-info.json', 'apoderado-actividades-final.json',
}


def test_exportador_exige_destino_incluso_desde_otro_directorio(tmp_path):
    resultado = subprocess.run([sys.executable, str(SCRIPT)], cwd=tmp_path,
                               capture_output=True, text=True)
    assert resultado.returncode == 2
    assert 'Falta --destino' in resultado.stderr
    assert 'tests/fixtures/servidor de ov_frontend' in resultado.stderr
    assert list(tmp_path.iterdir()) == []


def test_fixtures_reproducen_el_contrato_y_se_regeneran_identicos(tmp_path, monkeypatch):
    monkeypatch.setenv('EVALUADOR', 'gemini')
    ruta_ajena = tmp_path / 'base-del-usuario.db'
    # DATO DE PRUEBA: un archivo que jamás debe abrir ni reiniciar el exportador.
    ruta_ajena.write_bytes(b'Base del usuario: conservar estos bytes')
    monkeypatch.setenv('DATABASE_URL', f'sqlite:///{ruta_ajena.as_posix()}')
    bases = []
    crear = principal.crear_aplicacion
    crear_evaluador = principal.crear_evaluador_registro

    def crear_temporal(url_bd):
        ruta = Path(url_bd.removeprefix('sqlite:///'))
        assert ruta.name == 'plataforma.db' and ruta.parent.is_dir()
        assert ruta != ruta_ajena
        bases.append(ruta)
        return crear(url_bd)

    def solo_falso(configuracion):
        assert configuracion.evaluador == 'falso'
        return crear_evaluador(configuracion)

    monkeypatch.setattr(principal, 'crear_aplicacion', crear_temporal)
    monkeypatch.setattr(principal, 'crear_evaluador_registro', solo_falso)
    destino = tmp_path / 'front' / 'tests' / 'fixtures' / 'servidor'
    archivos = exportador.exportar_fixtures(destino)
    assert {ruta.name for ruta in archivos} == NOMBRES
    assert {ruta.name for ruta in destino.iterdir()} == NOMBRES
    bytes_antes = {ruta.name: ruta.read_bytes() for ruta in archivos}
    datos = {nombre: json.loads(contenido) for nombre, contenido in bytes_antes.items()}
    ResumenCuenta.model_validate(datos['resumen-inicial.json'])
    for momento in ('inicial', 'ciudad'):
        TypeAdapter(list[BloqueActividades]).validate_python(datos[f'actividades-{momento}.json'])
        TypeAdapter(list[ContenidoEstado]).validate_python(datos[f'fichas-{momento}.json'])
        LogrosCuenta.model_validate(datos[f'logros-{momento}.json'])
    for nombre in ('completar-mission-welcome.json', 'completar-mission-next-step.json',
                   'completar-act-tip-14.json'):
        RespuestaCompletarActividad.model_validate(datos[nombre])
    TypeAdapter(list[ItemPublico]).validate_python(datos['items-act-tip-01.json'])
    TypeAdapter(list[DesbloqueoLegible]).validate_python(datos['desbloqueos-no-vistos.json'])
    ResultadoPublico.model_validate(datos['resultado-riasec.json'])
    inicial = {**datos['resumen-inicial.json'], **datos['logros-inicial.json'],
               'bloques': datos['actividades-inicial.json']}
    estados = {a['codigo']: a['estado'] for b in inicial['bloques'] for a in b['actividades']}
    assert estados['mission-welcome'] == 'DISPONIBLE'
    assert all(e == 'BLOQUEADA' for c, e in estados.items() if c != 'mission-welcome')
    assert inicial['nivel_actual']['numero'] == 1
    assert any(i['codigo'] == '???' for i in inicial['insignias'])
    assert {d['regla'] for d in datos['completar-mission-welcome.json']['nuevos_desbloqueos']} == {
        'R-enc-mitos', 'R-first-steps', 'R-I1',
    }
    llegada = datos['completar-mission-next-step.json']
    assert {d['regla'] for d in llegada['nuevos_desbloqueos']} == {
        'R-ciudad', 'R-I3', 'R-NIV-3', 'R-FAM-ESTUDIANTE',
    }
    assert llegada['eventos_registrados'][-1]['referencia'] == 'CAMINO'
    niveles = datos['logros-ciudad.json']['niveles']
    ciudad = {'nivel_actual': max((n for n in niveles if n['estado'] == 'OBTENIDO'), key=lambda n: n['numero']),
              'bloques': datos['actividades-ciudad.json']}
    assert ciudad['nivel_actual']['numero'] == 3
    bloque = next(b for b in ciudad['bloques'] if b['codigo'] == 'CIUDAD')
    assert bloque['estado'] == 'DISPONIBLE'
    assert bloque['actividades'][0]['estado'] == 'DISPONIBLE'
    assert all(a['estado'] == 'BLOQUEADA' for a in bloque['actividades'][1:])
    items = datos['items-act-tip-01.json']
    assert [i['codigo'] for i in items] == [f'RIASEC-{n:02}' for n in range(1, 6)]
    assert len(items[0]['escala']['opciones']) == 5
    cierre = datos['completar-act-tip-14.json']
    assert cierre['resultados_generados'] == [{'instrumento': 'TEST-RIASEC', 'aplicacion': 'APL-RIASEC'}]
    assert {d['regla'] for d in cierre['nuevos_desbloqueos']} == {'R-act-tip-final'}
    resultado = datos['resultado-riasec.json']
    assert resultado['calculado_en'] == exportador.FECHA
    assert resultado['codigo_interes'] == {'codigo': 'IRA', 'hay_empate': False}
    assert {d['codigo']: d['porcentaje'] for d in resultado['dimensiones']} == {
        'I': 100, 'R': 75, 'A': 50, 'S': 0, 'E': 0, 'C': 0,
    }
    assert len(resultado['coincidencias']) == 10
    assert resultado['coincidencias'][0]['codigo'] == 'geologist'
    assert all(c['codigo'] for c in resultado['coincidencias'])
    assert {c['codigo'] for c in resultado['carreras_recomendadas']} == {
        'environmental-engineering', 'civil-engineering', 'veterinary-medicine',
    }
    avisos = datos['desbloqueos-no-vistos.json']
    assert len(avisos) == 19 and all(d['visto'] is False for d in avisos)
    assert 'R-ciudad' in {d['regla'] for d in avisos}
    assert not any(d['regla'].startswith('R-act-tip-') for d in avisos)
    assert all(d['fecha_hora'] == exportador.FECHA for d in avisos)
    # Regenera sobre archivos existentes sin tocar otros archivos del destino.
    conservar = destino / 'conservar.txt'
    conservar.write_text('Conservar', encoding='utf-8')
    exportador.exportar_fixtures(destino)
    assert {ruta.name: ruta.read_bytes() for ruta in archivos} == bytes_antes
    assert conservar.read_text(encoding='utf-8') == 'Conservar'
    assert len(bases) == 2 and all(not ruta.parent.exists() for ruta in bases)
    assert ruta_ajena.read_bytes() == b'Base del usuario: conservar estos bytes'
    assert exportador.os.environ['EVALUADOR'] == 'gemini'


def test_fallo_del_recorrido_no_escribe_fixtures_y_restaura_evaluador(tmp_path, monkeypatch):
    monkeypatch.delenv('EVALUADOR', raising=False)
    destino = tmp_path / 'no-publicado'

    def fallar(cliente):
        raise RuntimeError('Fallo de prueba del recorrido')

    monkeypatch.setattr(exportador, '_recorrer', fallar)
    with pytest.raises(RuntimeError, match='Fallo de prueba del recorrido'):
        exportador.exportar_fixtures(destino)
    assert not destino.exists()
    assert 'EVALUADOR' not in exportador.os.environ


def test_fixtures_apoderado_reflejan_cuentas_desbloqueo_y_completitud(tmp_path):
    archivos = exportador.exportar_fixtures(tmp_path / 'servidor')
    datos = {ruta.name: json.loads(ruta.read_bytes()) for ruta in archivos}
    cuentas = TypeAdapter(list[CuentaResumen]).validate_python(datos['cuentas.json'])
    assert [(c.codigo, c.nombre, c.rol) for c in cuentas] == [
        ('apo-rosa', 'Rosa', 'APODERADO'), ('est-ana', 'Ana', 'ESTUDIANTE'), ('est-luis', 'Luis', 'ESTUDIANTE'),
    ]
    for momento in ('inicial', 'pad-01', 'final'):
        TypeAdapter(list[BloqueActividades]).validate_python(datos[f'apoderado-actividades-{momento}.json'])
    assert datos['apoderado-actividades-inicial.json'] == [BLOQUE_FAMILIA]
    for momento, estados in (
        ('pad-01', ['COMPLETADA', 'DISPONIBLE']), ('final', ['COMPLETADA', 'COMPLETADA']),
    ):
        bloque, = datos[f'apoderado-actividades-{momento}.json']
        assert {clave: valor for clave, valor in bloque.items() if clave != 'actividades'} == {
            clave: valor for clave, valor in BLOQUE_FAMILIA.items() if clave != 'actividades'
        }
        assert bloque['actividades'] == [
            {**actividad, 'estado': estado}
            for actividad, estado in zip(BLOQUE_FAMILIA['actividades'], estados, strict=True)
        ]
    for actividad in ('pad-01-rol', 'pad-02-info'):
        RespuestaCompletarActividad.model_validate(datos[f'apoderado-completar-{actividad}.json'])
    primera = datos['apoderado-completar-pad-01-rol.json']
    assert primera['eventos_registrados'] == [
        {'tipo': 'COMPLETA_ACTIVIDAD', 'referencia': 'pad-01-rol', 'fecha_hora': exportador.FECHA},
    ]
    assert [(d['regla'], d['tipo_objetivo'], d['objetivo']['codigo']) for d in primera['nuevos_desbloqueos']] == [
        ('R-pad-02-info', 'ACTIVIDAD', 'pad-02-info'),
    ]
    segunda = datos['apoderado-completar-pad-02-info.json']
    assert segunda['eventos_registrados'] == [
        {'tipo': 'COMPLETA_ACTIVIDAD', 'referencia': 'pad-02-info', 'fecha_hora': exportador.FECHA},
        {'tipo': 'COMPLETA_BLOQUE', 'referencia': 'FAMILIA', 'fecha_hora': exportador.FECHA},
    ]
    assert segunda['nuevos_desbloqueos'] == []
    assert primera['resultados_generados'] == segunda['resultados_generados'] == []


@pytest.mark.parametrize('evaluador_previo', [None, 'gemini'])
def test_fallo_del_apoderado_no_escribe_fixtures_y_restaura_evaluador(tmp_path, monkeypatch, evaluador_previo):
    if evaluador_previo is None:
        monkeypatch.delenv('EVALUADOR', raising=False)
    else:
        monkeypatch.setenv('EVALUADOR', evaluador_previo)
    destino = tmp_path / 'sin-publicar'

    def fallar(cliente):
        assert os.environ['EVALUADOR'] == 'falso'
        raise RuntimeError('Fallo de prueba del apoderado')

    monkeypatch.setattr(exportador, '_recorrer_apoderado', fallar)
    with pytest.raises(RuntimeError, match='Fallo de prueba del apoderado'):
        exportador.exportar_fixtures(destino)
    assert not destino.exists()
    assert os.environ.get('EVALUADOR') == evaluador_previo
