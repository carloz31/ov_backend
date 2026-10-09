"""R02–R04 y R06: reglas, concesiones y aislamiento."""

from collections import Counter
import pytest
from sqlalchemy import select
from app import models as m
from app.services.motor import reglas as motor
from app.services.motor.evaluadores import EVALUADORES
from soporte_plataforma import actividades, filas_base, pedir
from soporte_retiro import FECHA_BD, agregar_eventos, buscar, condicion, regla


def test_r02_and_umbral_evaluador_y_evaluacion_unica(sesion, monkeypatch):
    ana, luis = [buscar(sesion, m.Cuenta, c) for c in ('est-ana', 'est-luis')]
    ficha = sesion.scalar(select(m.Ficha))
    nueva = regla(sesion, 'R-PRUEBA-AND', 'FICHA', ficha.id,
        [condicion('INGRESO', 2), condicion('PUBLICA_ENTREVISTA')], 'prueba_especial')
    monkeypatch.setitem(EVALUADORES, 'prueba_especial', lambda s, c: c.codigo == 'est-ana')
    agregar_eventos(sesion, luis, [('INGRESO', None, FECHA_BD)] * 5 + [('PUBLICA_ENTREVISTA', None, FECHA_BD)])
    assert motor.evaluar_regla(sesion, ana, nueva).cumple is False
    agregar_eventos(sesion, ana, [('INGRESO', None, FECHA_BD)] * 3)
    evaluacion = motor.evaluar_regla(sesion, ana, nueva)
    assert evaluacion.condiciones[0].actual == 3 and evaluacion.condiciones[0].requerido == 2
    assert evaluacion.cumple is False and evaluacion.evaluador_especial.cumplido is True
    assert motor.evaluar_regla(sesion, luis, nueva).cumple is False
    llamadas = Counter()
    original = motor.evaluar_regla
    def observar(s, c, r):
        llamadas[r.codigo] += 1
        return original(s, c, r)
    monkeypatch.setattr(motor, 'evaluar_regla', observar)
    nuevos = motor.registrar_eventos(sesion, ana, [('INGRESO', None), ('PUBLICA_ENTREVISTA', None)], FECHA_BD)
    assert 'R-PRUEBA-AND' in {n.regla for n in nuevos}
    assert llamadas['R-PRUEBA-AND'] == 1
    assert motor.registrar_eventos(sesion, ana, [('PUBLICA_ENTREVISTA', None)], FECHA_BD) == []


def test_r03_despacho_vacio_y_rollback_por_evaluador_desconocido(cliente, aplicacion, monkeypatch):
    with aplicacion.state.fabrica_sesiones.begin() as sesion:
        ficha = sesion.scalar(select(m.Ficha))
        regla(sesion, 'R-PRUEBA-OK', 'FICHA', ficha.id, [condicion('INGRESO')])
        regla(sesion, 'R-PRUEBA-Z-ERROR', 'FICHA', ficha.id, [condicion('INGRESO')], 'desconocido')
    antes = filas_base(aplicacion)
    llamadas = []
    original = motor.evaluar_regla
    def observar(s, c, r):
        llamadas.append(r.codigo)
        return original(s, c, r)
    monkeypatch.setattr(motor, 'evaluar_regla', observar)
    with aplicacion.state.fabrica_sesiones() as sesion:
        ana = buscar(sesion, m.Cuenta, 'est-ana')
        assert motor.registrar_eventos(sesion, ana, [], FECHA_BD) == []
        assert llamadas == []
        motor.registrar_eventos(sesion, ana, [('ESCRIBE_ENTRADA_LIBRE', None)], FECHA_BD)
        assert llamadas == []
        sesion.rollback()
    with pytest.raises(ValueError, match='Evaluador especial desconocido'):
        with aplicacion.state.fabrica_sesiones.begin() as sesion:
            motor.registrar_eventos(sesion, buscar(sesion, m.Cuenta, 'est-ana'), [('INGRESO', None)], FECHA_BD)
    assert llamadas == ['R-PRUEBA-OK', 'R-PRUEBA-Z-ERROR']
    assert filas_base(aplicacion) == antes


def test_r04_condiciones_concesion_y_bloque_son_independientes(cliente, aplicacion):
    with aplicacion.state.fabrica_sesiones.begin() as sesion:
        bloque = buscar(sesion, m.Bloque, 'CIUDAD')
        actividad = m.Actividad(codigo='act-prueba-bloque', titulo='DATO DE PRUEBA', tipo='INFORMATIVA',
            contenido='prueba', orden=100, bloque_id=bloque.id)
        sesion.add(actividad)
        sesion.flush()
        nueva = regla(sesion, 'R-PRUEBA-BLOQUE', 'ACTIVIDAD', actividad.id, [condicion('INGRESO')])
        ana = buscar(sesion, m.Cuenta, 'est-ana')
        agregar_eventos(sesion, ana, [('INGRESO', None, FECHA_BD)])
        assert motor.evaluar_regla(sesion, ana, nueva).cumple is True
        assert motor.objetivo_disponible(sesion, ana, m.TipoObjetivo.ACTIVIDAD, actividad.id) is False
    antes = filas_base(aplicacion)
    explicacion = pedir(cliente, 'GET', '/cuentas/est-ana/progreso/ACTIVIDAD/act-prueba-bloque')
    assert explicacion['reglas'][0]['cumplida'] is True
    assert actividades(cliente)['act-prueba-bloque'] == 'BLOQUEADA'
    assert filas_base(aplicacion) == antes
    pedir(cliente, 'POST', '/acciones/ingresar', {'cuenta': 'est-ana'})
    assert actividades(cliente)['act-prueba-bloque'] == 'BLOQUEADA'
    with aplicacion.state.fabrica_sesiones.begin() as sesion:
        ana = buscar(sesion, m.Cuenta, 'est-ana')
        assert sesion.scalar(select(m.Desbloqueo).join(m.ReglaDesbloqueo).where(
            m.Desbloqueo.cuenta_id == ana.id, m.ReglaDesbloqueo.codigo == 'R-PRUEBA-BLOQUE')) is not None
        motor.registrar_eventos(sesion, ana, [('COMPLETA_BLOQUE', buscar(sesion, m.Bloque, 'CAMINO').id)], FECHA_BD)
    assert actividades(cliente)['act-prueba-bloque'] == 'DISPONIBLE'


def test_r06_alternativas_audiencias_y_cuentas(sesion):
    estudiante = buscar(sesion, m.Cuenta, 'est-ana')
    apoderado = buscar(sesion, m.Cuenta, 'apo-rosa')
    luis = buscar(sesion, m.Cuenta, 'est-luis')
    regla(sesion, 'R-PRUEBA-ALT-A', 'CONVERSACIONES', None, [condicion('INGRESO')])
    regla(sesion, 'R-PRUEBA-ALT-B', 'CONVERSACIONES', None, [condicion('PUBLICA_ENTREVISTA')])
    actividad = buscar(sesion, m.Actividad, 'enc-mitos')
    regla(sesion, 'R-PRUEBA-AUDIENCIA', 'ACTIVIDAD', actividad.id, [condicion('INGRESO')])
    for cuenta in (estudiante, apoderado):
        assert not motor.objetivo_disponible(sesion, cuenta, m.TipoObjetivo.CONVERSACIONES, None)
        nuevos = motor.registrar_eventos(sesion, cuenta, [('INGRESO', None)], FECHA_BD)
        codigos = {n.regla for n in nuevos}
        assert 'R-PRUEBA-ALT-A' in codigos and 'R-PRUEBA-ALT-B' not in codigos
        assert ('R-PRUEBA-AUDIENCIA' in codigos) == (cuenta == estudiante)
        assert motor.objetivo_disponible(sesion, cuenta, m.TipoObjetivo.CONVERSACIONES, None)
    assert not motor.objetivo_disponible(sesion, luis, m.TipoObjetivo.CONVERSACIONES, None)
    assert 'R-PRUEBA-ALT-B' in {n.regla for n in motor.registrar_eventos(sesion, luis, [('PUBLICA_ENTREVISTA', None)], FECHA_BD)}
