"""B1: claves de contenido y visibilidad sin cambiar los escenarios existentes."""

import re

import pytest
from sqlalchemy import select

from app.database import crear_motor_bd
from app.models import Actividad, Visibilidad
from datos import cargar as carga


@pytest.mark.parametrize('conjunto', ['plataforma'])
def test_claves_y_visibilidad_de_los_conjuntos(tmp_path, conjunto):
    url = f'sqlite:///{(tmp_path / "contenidos.db").as_posix()}'
    carga.preparar_base(url, conjunto, crear_tablas=True)
    motor = crear_motor_bd(url)
    try:
        with motor.connect() as conexion:
            filas = conexion.execute(select(Actividad.codigo, Actividad.contenido, Actividad.visibilidad)).all()
        assert all(re.fullmatch(r'[a-z0-9_]+', contenido) for _, contenido, _ in filas)
        assert all(visibilidad == Visibilidad.SIEMPRE for _, _, visibilidad in filas)
        assert {codigo: contenido for codigo, contenido, _ in filas} == {
            'mission-welcome': 'mision_bienvenida',
            'enc-mitos': 'encuentro_mitos',
            'act-07': 'registro_mis_pregones',
            'mission-story': 'registro_huellas',
            'mission-future': 'registro_horizonte',
            'mission-compass': 'mision_brujula',
            'act-06': 'registro_linea_tiempo',
            'mission-expectations': 'registro_mochila',
            'mission-next-step': 'registro_siguiente_paso',
            **{f'act-tip-{n:02}': 'instrumento_mara' for n in range(1, 15)},
            'act-tip-final': 'encuentro_resultado_elena',
            'pad-01-rol': 'pad_01_acompanar',
            'pad-02-info': 'pad_02_informacion',
        }
    finally:
        motor.dispose()
