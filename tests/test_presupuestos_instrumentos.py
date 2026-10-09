"""R12, R30–R31: SQL agrupado de respuestas, cálculo y consultas."""

from soporte_datos_ports import agregar_ocupaciones
from sqlalchemy import select
from app import models as m
from soporte_plataforma import MARA, avanzar_camino, pedir
from soporte_retiro import base_aislada, ciclo, datos_respuestas, medir, preparar_ultimo


def test_r12_uno_o_todos_insertar_y_reemplazar_con_identidad(tmp_path):
    conteos = []
    for cantidad in (1, 5):
        with base_aislada(tmp_path, f'lote-{cantidad}') as (aplicacion, cliente):
            avanzar_camino(cliente)
            datos = datos_respuestas(cliente, cantidad=cantidad)
            _, nuevas = medir(cliente, aplicacion, 'POST', '/acciones/responder-items', datos)
            with aplicacion.state.fabrica_sesiones() as sesion:
                antes = {r.item_id: (r.id, r.creada_en, r.actualizada_en) for r in sesion.scalars(select(m.RespuestaItem))}
            datos['fecha_hora'] = '2026-10-08T10:00:00'
            for respuesta in datos['respuestas']:
                respuesta['opcion'] = 5
            _, existentes = medir(cliente, aplicacion, 'POST', '/acciones/responder-items', datos)
            with aplicacion.state.fabrica_sesiones() as sesion:
                despues = {r.item_id: (r.id, r.creada_en, r.actualizada_en) for r in sesion.scalars(select(m.RespuestaItem))}
            assert len(antes) == len(despues) == cantidad
            assert all(despues[i][:2] == valor[:2] and despues[i][2] > valor[2] for i, valor in antes.items())
            assert all(r['opcion']['orden'] == 5 for r in pedir(cliente, 'GET', '/cuentas/est-ana/actividades/act-tip-01/respuestas')['respuestas'])
            conteos.append((nuevas.cantidad, existentes.cantidad))
    assert conteos[0] == conteos[1]


def test_r30_calculo_constante_con_cien_ocupaciones(tmp_path):
    conteos = []
    for extra in (0, 100):
        with base_aislada(tmp_path, f'ocupaciones-{extra}') as (aplicacion, cliente):
            if extra:
                with aplicacion.state.fabrica_sesiones.begin() as sesion:
                    agregar_ocupaciones(sesion, extra)
            preparar_ultimo(cliente)
            _, contador = medir(cliente, aplicacion, 'POST', '/acciones/completar-actividad',
                {'cuenta': 'est-ana', 'actividad': MARA[-1]}, limite=20)
            lecturas = [e.sentencia for e in contador.ejecuciones if e.sentencia.startswith('SELECT') and 'JOIN puntaje_ocupacion' in e.sentencia]
            assert len(lecturas) == 1
            conteos.append(contador.cantidad)
    assert conteos[0] == conteos[1]


def test_r31_presupuestos_de_consultas_y_reinicio(cliente, aplicacion):
    rutas = ['/instrumentos', '/actividades/act-tip-01/items', '/cuentas/est-ana/instrumentos',
             '/cuentas/est-ana/actividades/act-tip-01/respuestas']
    for ruta in rutas:
        medir(cliente, aplicacion, 'GET', ruta)
    medir(cliente, aplicacion, 'GET', '/cuentas/est-ana/instrumentos/TEST-RIASEC/resultado', esperado=409)
    ciclo(cliente)
    for ruta in rutas + ['/cuentas/est-ana/instrumentos/TEST-RIASEC/resultado',
                         '/cuentas/est-ana/instrumentos/TEST-RIASEC/historial']:
        medir(cliente, aplicacion, 'GET', ruta)
    medir(cliente, aplicacion, 'POST', '/acciones/reiniciar-instrumento',
        {'cuenta': 'est-ana', 'instrumento': 'TEST-RIASEC'}, limite=12)
