"""B1: claves de contenido y visibilidad sin cambiar los escenarios existentes."""

import re

import pytest
from sqlalchemy import select, update

from app.database import crear_motor_bd
from app.models import Actividad, Base, Visibilidad
from datos import cargar as carga


@pytest.mark.parametrize('conjunto', ['demo', 'plataforma'])
def test_claves_y_visibilidad_de_los_conjuntos(tmp_path, conjunto):
    url = f'sqlite:///{(tmp_path / "contenidos.db").as_posix()}'
    carga.preparar_base(url, conjunto, crear_tablas=True)
    motor = crear_motor_bd(url)
    try:
        with motor.connect() as conexion:
            filas = conexion.execute(select(Actividad.codigo, Actividad.contenido, Actividad.visibilidad)).all()
        assert all(re.fullmatch(r'[a-z0-9_]+', contenido) for _, contenido, _ in filas)
        assert all(visibilidad == Visibilidad.SIEMPRE for _, _, visibilidad in filas)
        if conjunto == 'demo':
            assert len(filas) == 30
            assert all(contenido == codigo.lower().replace('-', '_') for codigo, contenido, _ in filas)
            assert any(codigo == 'REG-ACT08' and contenido == 'reg_act08' for codigo, contenido, _ in filas)
        else:
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
            }
    finally:
        motor.dispose()


@pytest.mark.parametrize('clave', ['', 'Contenido', 'con-guion', 'con espacio', 'niño', 'contenido\n'])
def test_clave_invalida_revierte_toda_la_carga(tmp_path, monkeypatch, clave):
    url = f'sqlite:///{(tmp_path / "invalida.db").as_posix()}'
    original = carga.CONJUNTOS['demo']

    def cargar_invalida(sesion):
        original(sesion)
        sesion.execute(update(Actividad).where(Actividad.codigo == 'ACT-01').values(contenido=clave))

    monkeypatch.setitem(carga.CONJUNTOS, 'demo', cargar_invalida)
    with pytest.raises(ValueError, match='Contenido inválido en la actividad ACT-01'):
        carga.preparar_base(url, 'demo', crear_tablas=True)
    motor = crear_motor_bd(url)
    try:
        with motor.connect() as conexion:
            assert all(conexion.execute(select(tabla)).first() is None for tabla in Base.metadata.sorted_tables)
    finally:
        motor.dispose()
