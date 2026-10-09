"""R18 y R24: rollback después de persistir cálculo o reinicio."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app import models as m
from app.services import actividades as servicio_actividades
from app.services.instrumentos import resultados as servicio_resultados
from soporte_plataforma import MARA, avanzar_camino, completar, filas_base, pedir, responder
from soporte_retiro import base_aislada, ciclo, preparar_ultimo


def test_r18_fallo_despues_de_guardar_resultado_revierte_toda_accion(cliente, aplicacion, monkeypatch):
    preparar_ultimo(cliente)
    antes = filas_base(aplicacion)
    original = servicio_resultados.guardar_resultados
    def fallar(sesion, calculos):
        original(sesion, calculos)
        assert sesion.scalar(select(m.ResultadoInstrumento.id)) is not None
        assert sesion.scalar(select(m.ResultadoDimension.resultado_id)) is not None
        assert sesion.scalar(select(m.Coincidencia.resultado_id)) is not None
        raise IntegrityError('DATO DE PRUEBA', {}, RuntimeError('fallo después de guardar'))
    monkeypatch.setattr(servicio_resultados, 'guardar_resultados', fallar)
    completar(cliente, MARA[-1], esperado=409)
    assert filas_base(aplicacion) == antes


def test_r24_reinicio_parcial_y_completo_revierte_despues_del_evento(tmp_path, monkeypatch):
    original = servicio_actividades.responder_con_eventos
    def fallar(sesion, cuenta, eventos, fecha):
        salida = original(sesion, cuenta, eventos, fecha)
        assert salida.eventos_registrados[0].tipo == 'REINICIA_INSTRUMENTO'
        raise IntegrityError('DATO DE PRUEBA', {}, RuntimeError('fallo después del evento'))
    for completo in (False, True):
        with base_aislada(tmp_path, f'reinicio-{completo}') as (aplicacion, cliente):
            if completo:
                ciclo(cliente)
            else:
                avanzar_camino(cliente)
                responder(cliente, MARA[0])
            antes = filas_base(aplicacion)
            with monkeypatch.context() as parche:
                parche.setattr(servicio_actividades, 'responder_con_eventos', fallar)
                pedir(cliente, 'POST', '/acciones/reiniciar-instrumento',
                    {'cuenta': 'est-ana', 'instrumento': 'TEST-RIASEC'}, 409)
            assert filas_base(aplicacion) == antes
