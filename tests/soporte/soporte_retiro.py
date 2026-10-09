"""Datos mínimos y mediciones para los ports R01–R40; DATO DE PRUEBA."""

from contextlib import contextmanager
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import select
from app import models as m
from app.main import crear_aplicacion
from datos.cargar import preparar_base
from soporte_consultas import ContadorConsultas
from soporte_plataforma import FECHA, MARA, avanzar_camino, completar, pedir, responder


FECHA_BD = datetime.fromisoformat(FECHA)


def buscar(sesion, modelo, codigo):
    resultado = sesion.scalar(select(modelo).where(modelo.codigo == codigo))
    assert resultado is not None, (modelo, codigo)
    return resultado


def regla(sesion, codigo, tipo, objetivo, condiciones, especial=None, parametro=None):
    nueva = m.ReglaDesbloqueo(codigo=codigo, nombre='DATO DE PRUEBA', tipo_objetivo=tipo,
        id_objetivo=objetivo, evaluador_especial=especial, parametro_evaluador=parametro,
        condiciones=[m.CondicionDesbloqueo(tipo_evento=evento, cantidad_minima=cantidad,
            id_referencia=referencia, tipo_conteo=conteo)
            for evento, cantidad, referencia, conteo in condiciones])
    sesion.add(nueva)
    sesion.flush()
    return nueva


def condicion(evento='INGRESO', cantidad=1, referencia=None, conteo='EVENTOS'):
    return evento, cantidad, referencia, conteo


def agregar_eventos(sesion, cuenta, eventos):
    sesion.add_all([m.EventoUso(cuenta_id=cuenta.id, tipo=tipo, id_referencia=referencia,
                              fecha_hora=fecha) for tipo, referencia, fecha in eventos])
    sesion.flush()


def medir(cliente, aplicacion, metodo, ruta, datos=None, esperado=200, limite=10):
    with ContadorConsultas(aplicacion.state.motor_bd) as contador:
        salida = pedir(cliente, metodo, ruta, datos, esperado)
    assert contador.cantidad <= limite, contador.diagnostico
    return salida, contador


@contextmanager
def base_aislada(tmp_path, nombre):
    url = f'sqlite:///{(tmp_path / (nombre + ".db")).as_posix()}'
    preparar_base(url, 'plataforma', crear_tablas=True)
    aplicacion = crear_aplicacion(url)
    with TestClient(aplicacion) as cliente:
        yield aplicacion, cliente


def datos_respuestas(cliente, actividad=MARA[0], opcion=3, cuenta='est-ana', cantidad=None):
    items = pedir(cliente, 'GET', f'/actividades/{actividad}/items')[:cantidad]
    return {'cuenta': cuenta, 'actividad': actividad, 'fecha_hora': FECHA,
            'respuestas': [{'item': i['codigo'], 'opcion': opcion} for i in items]}


def ciclo(cliente, cuenta='est-ana', opcion=None, hasta=None, abrir=True):
    if abrir:
        avanzar_camino(cliente, cuenta=cuenta)
    recorrido = MARA if hasta is None else MARA[:hasta]
    for actividad in recorrido:
        responder(cliente, actividad, cuenta=cuenta, opcion=opcion)
        salida = completar(cliente, actividad, cuenta=cuenta)
    return salida


def preparar_ultimo(cliente, cuenta='est-ana', opcion=None):
    ciclo(cliente, cuenta, opcion, hasta=13)
    responder(cliente, MARA[-1], cuenta=cuenta, opcion=opcion)


def resultado(cliente, instrumento='TEST-RIASEC', cuenta='est-ana', seleccion=''):
    return pedir(cliente, 'GET', f'/cuentas/{cuenta}/instrumentos/{instrumento}/resultado{seleccion}')


def reiniciar(cliente, instrumento='TEST-RIASEC', cuenta='est-ana', seleccion=None, esperado=200):
    datos = {'cuenta': cuenta, 'instrumento': instrumento, 'fecha_hora': '2026-10-08T10:00:00'}
    if seleccion is not None:
        datos['aplicacion'] = seleccion
    return pedir(cliente, 'POST', '/acciones/reiniciar-instrumento', datos, esperado)


def aplicaciones_extra(sesion, cantidad):
    instrumento = buscar(sesion, m.Instrumento, 'TEST-RIASEC')
    actividades = [buscar(sesion, m.Actividad, codigo).id for codigo in MARA]
    for n in range(cantidad):
        nueva = m.Aplicacion(codigo=f'APL-PRUEBA-{n}', nombre='DATO DE PRUEBA',
                            instrumento_id=instrumento.id)
        sesion.add(nueva)
        sesion.flush()
        sesion.add_all([m.AplicacionActividad(aplicacion_id=nueva.id, actividad_id=a) for a in actividades])


def instrumento_minimo(sesion, tipo='DESTACADAS', descripciones=None):
    """Solo tres ítems; dos momentos comparten los mismos ítems en COMPARACION."""
    instrumento = m.Instrumento(codigo='TEST-PRUEBA', nombre='DATO DE PRUEBA',
        descripcion='DATO DE PRUEBA', tipo_resultado=tipo)
    sesion.add(instrumento)
    sesion.flush()
    escala = buscar(sesion, m.EscalaRespuesta, 'ESC-LIKERT5')
    dimensiones = []
    for n, (codigo, descripcion) in enumerate((descripciones or {
            'DIM-A': 'DATO DE PRUEBA A', 'DIM-B': 'DATO DE PRUEBA B',
            'DIM-C': 'DATO DE PRUEBA C'}).items(), 1):
        if tipo == 'COMPARACION':
            break
        dimension = m.Dimension(instrumento_id=instrumento.id, codigo=codigo,
            nombre=codigo, descripcion=descripcion, orden=n)
        sesion.add(dimension)
        sesion.flush()
        dimensiones.append(dimension)
    items = []
    for n in range(1, len(dimensiones) + 1 if dimensiones else 4):
        item = m.ItemInstrumento(instrumento_id=instrumento.id, codigo=f'ITEM-PRUEBA-{n}',
            numero=n, enunciado='DATO DE PRUEBA', escala_id=escala.id,
            dimension_id=dimensiones[n-1].id if dimensiones else None, inverso=n == 2)
        sesion.add(item)
        sesion.flush()
        items.append(item)
    bloque = buscar(sesion, m.Bloque, 'CAMINO')
    momentos = ('ENTRADA', 'SALIDA') if tipo == 'COMPARACION' else ('UNICA',)
    codigos = []
    for n, momento in enumerate(momentos):
        actividad = m.Actividad(codigo=f'act-prueba-{n}', titulo='DATO DE PRUEBA',
            tipo='CUESTIONARIO', contenido='prueba', orden=100+n, bloque_id=bloque.id)
        aplicacion = m.Aplicacion(codigo=f'APL-PRUEBA-{momento}', nombre='DATO DE PRUEBA',
            instrumento_id=instrumento.id, momento=momento)
        sesion.add_all([actividad, aplicacion])
        sesion.flush()
        sesion.add(m.AplicacionActividad(aplicacion_id=aplicacion.id, actividad_id=actividad.id))
        sesion.add_all([m.ActividadItem(actividad_id=actividad.id, item_id=item.id, orden=i)
                       for i, item in enumerate(items, 1)])
        codigos.append(actividad.codigo)
    return codigos


def contestar_minimo(cliente, actividad, opciones=None):
    datos = datos_respuestas(cliente, actividad)
    for respuesta, opcion in zip(datos['respuestas'], opciones or [5, 1, 3]):
        respuesta['opcion'] = opcion
    pedir(cliente, 'POST', '/acciones/responder-items', datos)
    return completar(cliente, actividad)


def sin_ids(datos):
    if isinstance(datos, dict):
        assert all(k != 'id' and not k.endswith('_id') and k != 'id_referencia' for k in datos)
        for valor in datos.values():
            sin_ids(valor)
    elif isinstance(datos, list):
        for valor in datos:
            sin_ids(valor)
