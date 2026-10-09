"""Semilla, evaluador, compatibilidad e invariantes complementarios de F2."""

import re
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from soporte_consultas import ContadorConsultas
from soporte_plataforma import (
    CAMINO, FECHA, MARA, actividades, aplicacion, avanzar_camino, cliente, completar, estado,
    eventos, filas_base, pedir, sesion,
)
from sqlalchemy import func, insert, select, text

from app import models as modelos
from app.core.contexto import ContextoConsultas
from app.main import crear_aplicacion
from app.models.base import Base
from app.services.motor.evaluadores import misiones_camino_sin_inicio
from app.services.motor.reglas import evaluar_regla, registrar_eventos
from datos import ocupaciones as datos_ocupaciones
from datos import plataforma as semilla_plataforma
from datos.cargar import preparar_base
from datos.ocupaciones import leer_ocupaciones, validar_distribucion_items


SPEC = (Path(__file__).resolve().parents[1] / 'docs/iteraciones/spec-iteracion-1.md').read_text(encoding='utf-8')


def test_catalogo_estructura_y_estado_vacio(sesion, aplicacion):
    esperados = {'cuenta': 3, 'vinculo_familiar': 1, 'bloque': 2, 'actividad': 24,
        'ficha': 4, 'insignia': 10, 'nivel': 5, 'regla_desbloqueo': 44, 'condicion_desbloqueo': 53,
        'instrumento': 1, 'escala_respuesta': 1, 'opcion_escala': 5, 'dimension': 6,
        'item_instrumento': 60, 'actividad_item': 60, 'aplicacion': 1, 'aplicacion_actividad': 14,
        'ocupacion': 36, 'puntaje_ocupacion': 216, 'familia_carrera': 6, 'carrera': 6,
        'carrera_ocupacion': 23}
    assert len(Base.metadata.tables) == 44
    for tabla in Base.metadata.sorted_tables:
        assert sesion.scalar(select(func.count()).select_from(tabla)) == esperados.get(tabla.name, 0), tabla.name
    assert set(sesion.scalars(select(modelos.Bloque.codigo))) == {'CAMINO', 'CIUDAD'}
    assert sesion.scalars(select(modelos.Instrumento.codigo)).all() == ['TEST-RIASEC']
    assert sesion.execute(text('PRAGMA foreign_key_check')).all() == []
    tabla_spec = SPEC.split('#### 4.3.8')[1].split('Familias y carreras')[0]
    ocupaciones = set(re.findall(r'^\| ([a-z][a-z-]+) \| (.+?) \| (\d{2}-\d{4}\.\d{2})', tabla_spec, re.M))
    ocupaciones = {(c, t.split(' (DATO DE PRUEBA:')[0], o) for c, t, o in ocupaciones}
    # El título de nurse no incluye la anotación documental entre paréntesis.
    assert set(sesion.execute(select(modelos.Ocupacion.codigo, modelos.Ocupacion.titulo, modelos.Ocupacion.codigo_onet))) == ocupaciones
    excel = {fila.codigo_onet: fila.valores for fila in leer_ocupaciones(datos_ocupaciones.RUTA_OCUPACIONES)}
    puntajes = list(sesion.execute(select(modelos.Ocupacion.codigo_onet, modelos.Dimension.codigo, modelos.PuntajeOcupacion.valor)
        .join(modelos.PuntajeOcupacion, modelos.PuntajeOcupacion.ocupacion_id == modelos.Ocupacion.id)
        .join(modelos.Dimension, modelos.Dimension.id == modelos.PuntajeOcupacion.dimension_id)))
    assert all(valor == excel[onet]['RIASEC'.index(d)] for onet, d, valor in puntajes)
    assert not any(c == 'drone-operator' for c, _, _ in ocupaciones)


def test_riasec_enunciados_y_distribucion_exactos(sesion, cliente):
    validar_distribucion_items(sesion)
    enunciados = {d: [] for d in 'RIASEC'}
    for inicio, fin, dimensiones in (('| k | R Realista', '| k | S Social', 'RIA'),
                                   ('| k | S Social', 'No se siembran TEST-INT', 'SEC')):
        for linea in SPEC[SPEC.index(inicio):SPEC.index(fin)].splitlines():
            if re.match(r'^\| \d+ \|', linea):
                valores = [v.strip() for v in linea.strip().strip('|').split('|')][1:]
                for d, valor in zip(dimensiones, valores, strict=True):
                    enunciados[d].append(valor)
    todos = []
    for n, actividad in enumerate(MARA, start=1):
        items = pedir(cliente, 'GET', f'/actividades/{actividad}/items')
        assert len(items) == (5 if n <= 4 else 4)
        assert [i['orden'] for i in items] == list(range(1, len(items) + 1))
        todos.extend(items)
    assert [i['numero'] for i in todos] == list(range(1, 61))
    assert [i['codigo'] for i in todos] == [f'RIASEC-{n:02}' for n in range(1, 61)]
    assert [i['dimension'] for i in todos] == list('RRIIAASSEECC' * 5)
    assert all(i['enunciado'] == enunciados[i['dimension']][2 * ((i['numero'] - 1) // 12) + (i['numero'] - 1) % 2]
               for i in todos)
    assert all(i['inverso'] is False for i in todos)
    assert [(o['orden'], o['puntaje']) for o in todos[0]['escala']['opciones']] == [(1, 0), (2, 1), (3, 2), (4, 3), (5, 4)]
    assert pedir(cliente, 'GET', '/actividades/mission-compass/items') == []


@pytest.mark.parametrize('fallo', ['ausente', 'invalido', 'referencia_ausente'])
def test_excel_erroneo_revierte_carga_explicita(cliente, aplicacion, tmp_path, monkeypatch, fallo):
    avanzar_camino(cliente, 'enc-mitos')
    antes = filas_base(aplicacion)
    cache = aplicacion.state.motor_bd.cache_definiciones.actual
    if fallo == 'referencia_ausente':
        filas = leer_ocupaciones(datos_ocupaciones.RUTA_OCUPACIONES)
        monkeypatch.setattr(semilla_plataforma, 'leer_ocupaciones', lambda ruta: [f for f in filas if f.codigo_onet != '19-2042.00'])
        mensaje = 'Falta la ocupación O*NET 19-2042.00, requerida por geologist'
    else:
        ruta_excel = tmp_path / 'fallo.xlsx'
        if fallo == 'invalido':
            ruta_excel.write_text('archivo inválido', encoding='utf-8')
        monkeypatch.setattr(semilla_plataforma, 'RUTA_OCUPACIONES', ruta_excel)
        mensaje = f'{"Falta" if fallo == "ausente" else "No se puede leer"} el archivo de ocupaciones: {ruta_excel}'
    with pytest.raises(ValueError) as error:
        preparar_base(str(aplicacion.state.motor_bd.url), 'plataforma', vaciar=True)
    assert str(error.value) == mensaje
    assert filas_base(aplicacion) == antes
    assert aplicacion.state.motor_bd.cache_definiciones.actual is cache
    url = f'sqlite:///{(tmp_path / "carga_fallida.db").as_posix()}'
    with pytest.raises(ValueError) as error:
        preparar_base(url, 'plataforma', crear_tablas=True)
    assert str(error.value) == mensaje
    nueva = crear_aplicacion(url)
    assert all(filas == [] for filas in filas_base(nueva).values())
    nueva.state.motor_bd.dispose()


def test_fallo_tardio_revierte_carga_y_conserva_cache(cliente, aplicacion, monkeypatch, tmp_path):
    avanzar_camino(cliente, 'mission-story')
    antes = filas_base(aplicacion)
    cache = aplicacion.state.motor_bd.cache_definiciones.actual
    def fallar(sesion):
        raise ValueError('Fallo después de cargar los datos')
    monkeypatch.setattr(semilla_plataforma, 'validar_distribucion_items', fallar)
    with pytest.raises(ValueError, match='Fallo después'):
        preparar_base(str(aplicacion.state.motor_bd.url), 'plataforma', vaciar=True)
    assert filas_base(aplicacion) == antes
    assert aplicacion.state.motor_bd.cache_definiciones.actual is cache
    url = f'sqlite:///{(tmp_path / "fallo_tardio.db").as_posix()}'
    with pytest.raises(ValueError, match='Fallo después'):
        preparar_base(url, 'plataforma', crear_tablas=True)
    nueva = crear_aplicacion(url)
    assert all(f == [] for f in filas_base(nueva).values())
    nueva.state.motor_bd.dispose()


@pytest.mark.parametrize('minimo', [None, 0, -1, True, 1.5])
def test_evaluador_rechaza_parametros_invalidos(sesion, minimo):
    datos = ContextoConsultas(sesion)
    sesion.info['contexto_consultas'] = datos
    datos.regla_en_evaluacion = SimpleNamespace(parametro_evaluador=minimo)
    cuenta = sesion.scalar(select(modelos.Cuenta).where(modelos.Cuenta.codigo == 'est-ana'))
    with pytest.raises(ValueError, match='parámetro entero positivo'):
        misiones_camino_sin_inicio(sesion, cuenta)


def test_evaluador_exige_regla_y_sin_camino_es_falso(sesion):
    cuenta = sesion.scalar(select(modelos.Cuenta).where(modelos.Cuenta.codigo == 'est-ana'))
    with pytest.raises(ValueError, match='Debe indicar la regla'):
        misiones_camino_sin_inicio(sesion, cuenta)
    datos = ContextoConsultas(sesion)
    sesion.info['contexto_consultas'] = datos
    datos.regla_en_evaluacion = SimpleNamespace(parametro_evaluador=3)
    datos.definiciones = SimpleNamespace(por_codigo=lambda *args: None)
    assert misiones_camino_sin_inicio(sesion, cuenta) is False


def test_evaluador_filtra_repeticiones_cuentas_ciudad_y_memoiza_por_umbral(sesion, aplicacion):
    cuentas = {c.codigo: c for c in sesion.scalars(select(modelos.Cuenta))}
    actividades_por_codigo = {a.codigo: a for a in sesion.scalars(select(modelos.Actividad))}
    ana, luis = cuentas['est-ana'], cuentas['est-luis']
    # DATO DE PRUEBA: eventos crudos para aislar el predicado del evaluador.
    referencias = ['mission-welcome', 'enc-mitos', 'enc-mitos', 'enc-mitos', 'act-07', 'act-tip-01']
    filas = [{'cuenta_id': ana.id, 'tipo': modelos.TipoEventoUso.COMPLETA_ACTIVIDAD,
              'id_referencia': actividades_por_codigo[c].id, 'fecha_hora': datetime.fromisoformat(FECHA)} for c in referencias]
    filas += [{'cuenta_id': luis.id, 'tipo': modelos.TipoEventoUso.COMPLETA_ACTIVIDAD,
               'id_referencia': actividades_por_codigo['mission-story'].id, 'fecha_hora': datetime.fromisoformat(FECHA)},
              {'cuenta_id': ana.id, 'tipo': modelos.TipoEventoUso.COMPLETA_ACTIVIDAD,
               'id_referencia': None, 'fecha_hora': datetime.fromisoformat(FECHA)},
              {'cuenta_id': ana.id, 'tipo': modelos.TipoEventoUso.INGRESO,
               'id_referencia': actividades_por_codigo['mission-future'].id, 'fecha_hora': datetime.fromisoformat(FECHA)}]
    sesion.execute(insert(modelos.EventoUso), filas)
    datos = ContextoConsultas(sesion)
    sesion.info['contexto_consultas'] = datos
    with ContadorConsultas(aplicacion.state.motor_bd) as contador:
        datos.cargar_conteos([ana.id])
    assert contador.cantidad == 1
    def regla(minimo):
        return modelos.ReglaDesbloqueo(codigo=f'PRUEBA-{minimo}', nombre='DATO DE PRUEBA',
            tipo_objetivo=modelos.TipoObjetivo.INSIGNIA, id_objetivo=1,
            evaluador_especial='misiones_camino_sin_inicio', parametro_evaluador=minimo,
            condiciones=[modelos.CondicionDesbloqueo(tipo_evento=modelos.TipoEventoUso.COMPLETA_ACTIVIDAD,
                          tipo_conteo=modelos.TipoConteo.EVENTOS, cantidad_minima=1)])
    with ContadorConsultas(aplicacion.state.motor_bd) as contador:
        assert evaluar_regla(sesion, ana, regla(2)).cumple is True
        assert evaluar_regla(sesion, ana, regla(3)).cumple is False
        assert evaluar_regla(sesion, ana, regla(2)).cumple is True
    assert contador.cantidad == 0
    assert datos.especiales[ana.id] == {('misiones_camino_sin_inicio', 2): True, ('misiones_camino_sin_inicio', 3): False}
    registrar_eventos(sesion, ana, [(modelos.TipoEventoUso.COMPLETA_ACTIVIDAD, actividades_por_codigo['mission-story'].id)],
                      datetime.fromisoformat(FECHA))
    assert evaluar_regla(sesion, ana, regla(3)).cumple is True


def test_invariantes_desbloqueos_nivel_audiencia_y_eventos(cliente, aplicacion):
    anteriores, nivel = {}, 1
    for codigo in CAMINO + ('enc-mitos', 'mission-next-step'):
        completar(cliente, codigo)
        with aplicacion.state.fabrica_sesiones() as sesion:
            actuales = {(d.cuenta_id, d.regla_id): (d.id, d.fecha_hora, d.visto) for d in sesion.scalars(select(modelos.Desbloqueo))}
        assert anteriores.items() <= actuales.items()
        assert len(actuales) == len(filas_base(aplicacion)['desbloqueo'])
        actual = estado(cliente)['nivel_actual']['numero']
        assert actual >= nivel
        anteriores, nivel = actuales, actual
    historial = eventos(cliente)
    assert sum(e['tipo'] == 'COMPLETA_BLOQUE' and e['referencia'] == 'CAMINO' for e in historial) == 1
    assert sum(e['tipo'] == 'COMPLETA_ACTIVIDAD' and e['referencia'] == 'mission-next-step' for e in historial) == 2
    assert actividades(cliente)['mission-next-step'] == 'COMPLETADA'
    assert eventos(cliente, 'est-luis') == [] and estado(cliente, 'est-luis')['nivel_actual']['numero'] == 1
    assert estado(cliente, 'apo-rosa')['bloques'] == []


def test_check_in_y_diario_aislados_por_cuenta(cliente, sesion):
    # DATO DE PRUEBA: la semilla no define preguntas; esta permite probar el invariante GUIADA.
    sesion.add(modelos.PreguntaDiario(codigo='pregunta-prueba', pregunta='DATO DE PRUEBA'))
    sesion.commit()
    for cuenta in ('est-ana', 'est-luis'):
        cuerpo = {'cuenta': cuenta, 'nivel_seguridad': 3, 'fecha_hora': FECHA}
        pedir(cliente, 'POST', '/acciones/check-in', cuerpo)
        pedir(cliente, 'POST', '/acciones/check-in', cuerpo, esperado=409)
        guiada = {'cuenta': cuenta, 'origen': 'GUIADA', 'pregunta': 'pregunta-prueba',
                  'texto': 'DATO DE PRUEBA', 'fecha_hora': FECHA}
        pedir(cliente, 'POST', '/acciones/escribir-entrada', guiada)
        pedir(cliente, 'POST', '/acciones/escribir-entrada', guiada, esperado=409)
        for _ in range(2):
            pedir(cliente, 'POST', '/acciones/escribir-entrada', {'cuenta': cuenta, 'origen': 'LIBRE', 'texto': 'DATO DE PRUEBA', 'fecha_hora': FECHA})
        historial = eventos(cliente, cuenta)
        assert sum(e['tipo'] == 'REGISTRA_CHECK_IN' for e in historial) == 1
        assert sum(e['tipo'] == 'ESCRIBE_ENTRADA_LIBRE' for e in historial) == 2
        # §5: toda entrada emite DIARIO; las libres emiten además LIBRE.
        assert sum(e['tipo'] == 'ESCRIBE_ENTRADA_DIARIO' for e in historial) == 3
        cuenta_id = sesion.scalar(select(modelos.Cuenta.id).where(modelos.Cuenta.codigo == cuenta))
        assert sesion.scalar(select(func.count()).select_from(modelos.EntradaDiario).where(
            modelos.EntradaDiario.cuenta_id == cuenta_id,
            modelos.EntradaDiario.origen == modelos.OrigenEntrada.GUIADA,
        )) == 1


def test_carta_se_registra_solo_la_primera_vez_por_cuenta(cliente):
    for cuenta in ('est-ana', 'apo-rosa'):
        for texto in ('Primera carta', 'Carta editada'):
            pedir(cliente, 'POST', '/acciones/escribir-carta',
                  {'cuenta': cuenta, 'vinculo': 'VIN-ANA', 'texto': texto, 'fecha_hora': FECHA})
        assert sum(e['tipo'] == 'ESCRIBE_CARTA' and e['referencia'] == 'VIN-ANA' for e in eventos(cliente, cuenta)) == 1
