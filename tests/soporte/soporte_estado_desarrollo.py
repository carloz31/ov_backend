"""Filas sintéticas para comprobar el reinicio de las 16 tablas; DATO DE PRUEBA."""

from datetime import datetime
from sqlalchemy import select
from app import models as modelos
from app.models import Base


def llenar_estado(aplicacion):
    # DATO DE PRUEBA: una fila válida en cada tabla de estado, con sus dependencias.
    fecha = datetime(2026, 10, 8, 10)
    with aplicacion.state.fabrica_sesiones.begin() as sesion:
        cuenta = sesion.scalar(select(modelos.Cuenta).where(modelos.Cuenta.codigo == 'est-ana'))
        actividad = sesion.scalar(select(modelos.Actividad).where(modelos.Actividad.codigo == 'mission-welcome'))
        vinculo = sesion.scalar(select(modelos.VinculoFamiliar))
        conversacion = modelos.Conversacion(codigo='conv-prueba', titulo='DATO DE PRUEBA', tema='DATO DE PRUEBA')
        sesion.add(conversacion)
        sesion.flush()
        regla = sesion.scalar(select(modelos.ReglaDesbloqueo))
        aplicacion_instrumento = sesion.scalar(select(modelos.Aplicacion))
        dimension = sesion.scalar(select(modelos.Dimension).where(
            modelos.Dimension.instrumento_id == aplicacion_instrumento.instrumento_id))
        item = sesion.scalar(select(modelos.ItemInstrumento))
        opcion = sesion.scalar(select(modelos.OpcionEscala).where(modelos.OpcionEscala.escala_id == item.escala_id))
        item_registro = modelos.ItemRegistro(codigo='registro-prueba', nombre='DATO DE PRUEBA', consigna='DATO DE PRUEBA', min_caracteres=1, obligatorio=True, repregunta_generica='DATO DE PRUEBA')
        sesion.add(item_registro)
        sesion.flush()
        ocupacion = sesion.scalar(select(modelos.Ocupacion))
        if ocupacion is None:
            ocupacion = modelos.Ocupacion(codigo_onet='PRUEBA-REINICIO', titulo='DATO DE PRUEBA')
            sesion.add(ocupacion)
        progreso = modelos.ProgresoActividad(cuenta_id=cuenta.id, actividad_id=actividad.id, estado='EN_CURSO')
        entrevista = modelos.Entrevista(codigo='ENT-REINICIO', resumen='DATO DE PRUEBA', fecha_hora=fecha)
        resultado = modelos.ResultadoInstrumento(cuenta_id=cuenta.id, aplicacion_id=aplicacion_instrumento.id, calculado_en=fecha)
        sesion.add_all([progreso, entrevista, resultado])
        sesion.flush()
        respuesta = modelos.RespuestaRegistro(progreso_id=progreso.id, item_registro_id=item_registro.id,
            texto_inicial='DATO DE PRUEBA', estado='PENDIENTE_SEGUIMIENTO', creada_en=fecha, actualizada_en=fecha)
        sesion.add(respuesta)
        sesion.flush()
        sesion.add_all([
            modelos.ResultadoCaso(progreso_id=progreso.id, puntaje=85, fecha_hora=fecha),
            modelos.EntradaDiario(cuenta_id=cuenta.id, origen='LIBRE', texto='DATO DE PRUEBA', fecha_hora=fecha),
            modelos.CheckIn(cuenta_id=cuenta.id, fecha=fecha.date(), nivel_seguridad=3),
            modelos.EntrevistaAutor(entrevista_id=entrevista.id, cuenta_id=cuenta.id),
            modelos.ConversacionVinculo(vinculo_id=vinculo.id, conversacion_id=conversacion.id, conversado=True),
            modelos.EventoUso(cuenta_id=cuenta.id, tipo='INGRESO', fecha_hora=fecha),
            modelos.Desbloqueo(cuenta_id=cuenta.id, regla_id=regla.id, fecha_hora=fecha),
            modelos.RespuestaItem(progreso_id=progreso.id, item_id=item.id, opcion_id=opcion.id, creada_en=fecha, actualizada_en=fecha),
            modelos.ResultadoDimension(resultado_id=resultado.id, dimension_id=dimension.id, puntaje=1, puntaje_maximo=5, porcentaje=20),
            modelos.Coincidencia(resultado_id=resultado.id, ocupacion_id=ocupacion.id, posicion=1, correlacion=0.9, ajuste='BEST_FIT'),
            modelos.TurnoSeguimiento(respuesta_id=respuesta.id, orden=1, pregunta='DATO DE PRUEBA', criterios_objetivo=['C1'], creado_en=fecha),
            modelos.EvaluacionRespuesta(respuesta_id=respuesta.id, numero=1, origen='RESPALDO_LONGITUD', clasificacion='VAGA',
                criterios_faltantes=['C1'], texto_evaluado='DATO DE PRUEBA', fecha_hora=fecha),
        ])


def filas(motor):
    with motor.connect() as conexion:
        return {tabla.name: conexion.execute(select(tabla).order_by(*tabla.primary_key.columns)).all()
                for tabla in Base.metadata.sorted_tables}
