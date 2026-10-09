"""R01: conteos generales sobre plataforma."""

from datetime import timedelta
from app import models as m
from app.services.motor import reglas as motor
from soporte_retiro import FECHA_BD, agregar_eventos, buscar


def test_r01_conteos_filtran_cuenta_tipo_referencia_y_fecha(sesion):
    ana, luis = [buscar(sesion, m.Cuenta, c) for c in ('est-ana', 'est-luis')]
    ids = [buscar(sesion, m.Actividad, c).id for c in ('mission-welcome', 'enc-mitos', 'act-07')]
    agregar_eventos(sesion, ana, [('COMPLETA_ACTIVIDAD', ids[n], FECHA_BD + timedelta(days=n, hours=h))
        for n, h in ((0, 0), (0, 1), (1, 0), (1, 1), (2, 0))]
        + [('SUPERA_CASO', ids[0], FECHA_BD + timedelta(days=3))])
    agregar_eventos(sesion, luis, [('COMPLETA_ACTIVIDAD', ids[0], FECHA_BD + timedelta(days=4))])
    for conteo, total, filtrado in [('EVENTOS', 5, 2), ('REFERENCIAS_DISTINTAS', 3, 1), ('DIAS_DISTINTOS', 3, 1)]:
        for referencia, esperado in ((None, total), (ids[0], filtrado)):
            condicion = m.CondicionDesbloqueo(tipo_evento='COMPLETA_ACTIVIDAD',
                tipo_conteo=conteo, cantidad_minima=1, id_referencia=referencia)
            assert motor.contar_eventos(sesion, ana, condicion) == esperado
