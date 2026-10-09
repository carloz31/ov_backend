"""Preparaciones mínimas para ports sobre plataforma; DATO DE PRUEBA."""

from datetime import timedelta
from sqlalchemy import select
from app import models as m
from soporte_plataforma import MARA
from soporte_retiro import FECHA_BD, buscar, condicion, instrumento_minimo, regla


def preparar_explicaciones(sesion):
    ficha = m.Ficha(codigo='ficha-prueba', titulo='DATO DE PRUEBA', contenido='DATO DE PRUEBA')
    libre = m.Ficha(codigo='ficha-libre', titulo='DATO DE PRUEBA', contenido='DATO DE PRUEBA')
    sesion.add_all([ficha, libre])
    sesion.flush()
    regla(sesion, 'R-PRUEBA-EXPLICAR', 'FICHA', ficha.id,
        [condicion('INGRESO', 2), condicion('COMPLETA_ACTIVIDAD')], 'misiones_camino_sin_inicio', 2)
    regla(sesion, 'R-PRUEBA-OR-A', 'CONVERSACIONES', None, [condicion('INGRESO', 2)])
    regla(sesion, 'R-PRUEBA-OR-B', 'CONVERSACIONES', None, [condicion('ESCRIBE_CARTA')])


def preparar_preguntas_respondidas(sesion):
    preguntas = [m.PreguntaDiario(codigo=f'pregunta-prueba-{n}', pregunta='DATO DE PRUEBA') for n in range(2)]
    sesion.add_all(preguntas)
    sesion.flush()
    for cuenta, pregunta in [('est-ana', preguntas[0]), ('est-luis', preguntas[1])]:
        sesion.add(m.EntradaDiario(cuenta_id=buscar(sesion, m.Cuenta, cuenta).id,
            origen='GUIADA', pregunta_id=pregunta.id, texto='DATO DE PRUEBA', fecha_hora=FECHA_BD))
    sesion.add(m.EntradaDiario(cuenta_id=buscar(sesion, m.Cuenta, 'est-ana').id,
        origen='LIBRE', texto='DATO DE PRUEBA', fecha_hora=FECHA_BD))


def preparar_respuesta_ajena(sesion):
    instrumento_minimo(sesion)
    ana = buscar(sesion, m.Cuenta, 'est-ana')
    progreso = sesion.scalar(select(m.ProgresoActividad).where(
        m.ProgresoActividad.cuenta_id == ana.id,
        m.ProgresoActividad.actividad_id == buscar(sesion, m.Actividad, MARA[0]).id))
    item = buscar(sesion, m.ItemInstrumento, 'ITEM-PRUEBA-1')
    opcion = sesion.scalar(select(m.OpcionEscala).where(m.OpcionEscala.escala_id == item.escala_id, m.OpcionEscala.orden == 1))
    sesion.add(m.RespuestaItem(progreso_id=progreso.id, item_id=item.id, opcion_id=opcion.id,
                              creada_en=FECHA_BD, actualizada_en=FECHA_BD))


def agregar_veinte_resultados(sesion):
    original_bd = sesion.scalar(select(m.ResultadoInstrumento))
    dimensiones = list(sesion.scalars(select(m.ResultadoDimension)))
    coincidencias = list(sesion.scalars(select(m.Coincidencia)))
    for n in range(20):
        fecha = FECHA_BD + timedelta(days=1+n//10)
        nuevo = m.ResultadoInstrumento(cuenta_id=original_bd.cuenta_id, aplicacion_id=original_bd.aplicacion_id,
            calculado_en=fecha, anulado_en=fecha, perfil_plano=False)
        sesion.add(nuevo)
        sesion.flush()
        sesion.add_all([m.ResultadoDimension(resultado_id=nuevo.id, dimension_id=d.dimension_id,
            puntaje=d.puntaje, puntaje_maximo=d.puntaje_maximo, porcentaje=n) for d in dimensiones])
        sesion.add_all([m.Coincidencia(resultado_id=nuevo.id, ocupacion_id=c.ocupacion_id,
            posicion=c.posicion, correlacion=c.correlacion, ajuste=c.ajuste) for c in coincidencias])


def renombrar_e_invertir_dimensiones(sesion):
    instrumento = buscar(sesion, m.Instrumento, 'TEST-RIASEC')
    instrumento.codigo = 'TEST-RENOMBRADO'
    dimensiones = list(sesion.scalars(select(m.Dimension).order_by(m.Dimension.orden)))
    for n, dimension in enumerate(reversed(dimensiones), 1):
        dimension.orden = n


def agregar_ocupaciones(sesion, extra):
    dimensiones = list(sesion.scalars(select(m.Dimension).order_by(m.Dimension.orden)))
    for n in range(extra):
        ocupacion = m.Ocupacion(codigo_onet=f'PRUEBA-{n}', titulo='DATO DE PRUEBA')
        sesion.add(ocupacion)
        sesion.flush()
        sesion.add_all([m.PuntajeOcupacion(ocupacion_id=ocupacion.id, dimension_id=d.id, valor=i+1)
                       for i, d in enumerate(dimensiones)])


def preparar_conversacion(sesion):
    sesion.add(m.Conversacion(codigo='conv-prueba', titulo='DATO DE PRUEBA', tema='DATO DE PRUEBA'))


def agregar_autores(sesion, cantidad, autores):
    for n in range(cantidad-2):
        codigo = f'est-prueba-{n}'
        sesion.add(m.Cuenta(codigo=codigo, nombre='DATO DE PRUEBA', rol='ESTUDIANTE'))
        autores.append(codigo)


def preparar_casos(sesion):
    bloque = buscar(sesion, m.Bloque, 'CAMINO')
    for minimo in (0, 70, 100):
        sesion.add(m.Actividad(codigo=f'caso-prueba-{minimo}', titulo='DATO DE PRUEBA',
            contenido='prueba', tipo='CASO', puntaje_minimo=minimo, orden=100+minimo, bloque_id=bloque.id))


def preparar_validacion(sesion):
    instrumento_minimo(sesion)
    sesion.add(m.Conversacion(codigo='conv-prueba', titulo='DATO DE PRUEBA', tema='DATO DE PRUEBA'))
