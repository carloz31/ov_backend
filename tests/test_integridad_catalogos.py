"""R38: restricciones de catálogo/relaciones, defaults y códigos opcionales."""

import pytest
from sqlalchemy import insert, inspect, select
from sqlalchemy.exc import IntegrityError
from app import models as m
from soporte_catalogos import completar_catalogos_vacios
from soporte_estado_desarrollo import llenar_estado
from soporte_retiro import FECHA_BD, buscar


def test_r38_integridad_catalogos_relaciones_respuestas_y_defaults(cliente, aplicacion):
    llenar_estado(aplicacion)
    with aplicacion.state.fabrica_sesiones.begin() as sesion:
        completar_catalogos_vacios(sesion)
    with aplicacion.state.fabrica_sesiones() as sesion:
        modelos = (m.Cuenta, m.VinculoFamiliar, m.Bloque, m.Actividad, m.Ficha, m.Testimonio,
            m.PreguntaDiario, m.Conversacion, m.Insignia, m.FamiliaCarrera, m.Carrera,
            m.ReglaDesbloqueo, m.Nivel, m.Entrevista, m.EntrevistaAutor, m.Instrumento,
            m.Dimension, m.EscalaRespuesta, m.OpcionEscala, m.ItemInstrumento, m.Aplicacion,
            m.Ocupacion, m.ActividadItem, m.AplicacionActividad, m.PuntajeOcupacion,
            m.CarreraOcupacion, m.RespuestaItem, m.ConversacionVinculo)
        for modelo in modelos:
            tabla = modelo.__table__
            original = sesion.execute(select(tabla)).mappings().first()
            assert original is not None, modelo
            datos = {k: v for k, v in original.items() if k != 'id'}
            with pytest.raises(IntegrityError):
                with sesion.begin_nested():
                    sesion.execute(insert(tabla), datos)
        guiada = sesion.scalar(select(m.EntradaDiario).where(m.EntradaDiario.origen == 'GUIADA'))
        with pytest.raises(IntegrityError):
            with sesion.begin_nested():
                sesion.add(m.EntradaDiario(cuenta_id=guiada.cuenta_id, pregunta_id=guiada.pregunta_id,
                    origen='GUIADA', texto='DATO DE PRUEBA', fecha_hora=FECHA_BD))
                sesion.flush()
        item = sesion.scalar(select(m.ItemInstrumento))
        with pytest.raises(IntegrityError):
            with sesion.begin_nested():
                sesion.add(m.ItemInstrumento(instrumento_id=item.instrumento_id, numero=item.numero,
                    codigo='item-numero-repetido', enunciado='DATO DE PRUEBA', escala_id=item.escala_id))
                sesion.flush()
        ocupacion = sesion.scalar(select(m.Ocupacion).where(m.Ocupacion.codigo.is_not(None)))
        with pytest.raises(IntegrityError):
            with sesion.begin_nested():
                sesion.add(m.Ocupacion(codigo=ocupacion.codigo, codigo_onet='PRUEBA-UNICO', titulo='DATO DE PRUEBA'))
                sesion.flush()
        assert len(list(sesion.scalars(select(m.Ocupacion).where(m.Ocupacion.codigo.is_(None))))) == 2
        conversacion = m.Conversacion(codigo='conv-default', titulo='DATO DE PRUEBA', tema='DATO DE PRUEBA')
        sesion.add(conversacion)
        sesion.flush()
        vinculo = sesion.scalar(select(m.VinculoFamiliar))
        registro = m.ConversacionVinculo(vinculo_id=vinculo.id, conversacion_id=conversacion.id)
        desbloqueo = m.Desbloqueo(cuenta_id=buscar(sesion, m.Cuenta, 'est-luis').id,
            regla_id=sesion.scalar(select(m.ReglaDesbloqueo.id)), fecha_hora=FECHA_BD)
        sesion.add_all([registro, desbloqueo])
        sesion.flush()
        assert registro.conversado is False and registro.conversado_en is None
        assert desbloqueo.visto is False and item.inverso is False
        assert sesion.scalar(select(m.Actividad)).visibilidad == 'SIEMPRE'
    inspector = inspect(aplicacion.state.motor_bd)
    assert len(inspector.get_table_names()) == 44
    columnas = {c['name']: c for c in inspector.get_columns('ocupacion')}
    assert set(columnas) == {'id', 'codigo', 'codigo_onet', 'titulo'} and columnas['codigo']['nullable'] is True
    assert any(r['column_names'] == ['codigo'] for r in inspector.get_unique_constraints('ocupacion'))
