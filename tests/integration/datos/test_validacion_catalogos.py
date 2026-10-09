"""R37: carga atómica y correspondencia de las dimensiones del Excel."""

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from app import models as m
from app.database import crear_motor_bd
from datos import cargar, plataforma
from soporte_catalogos import cargar_catalogo_corrupto


def test_r37_catalogos_invalidos_atomicos_y_excel_por_codigo(tmp_path, monkeypatch):
    variantes = ['faltante', 'repetido', 'ajeno', '', 'Contenido', 'con-guion', 'con espacio', 'niño', 'contenido\n']
    for n, variante in enumerate(variantes):
        url = f'sqlite:///{(tmp_path / f"catalogo-{n}.db").as_posix()}'
        with monkeypatch.context() as parche:
            parche.setitem(cargar.CONJUNTOS, 'plataforma', lambda sesion: cargar_catalogo_corrupto(sesion, variante))
            mensaje = 'Distribución inválida en APL-RIASEC' if n < 3 else 'Contenido inválido en la actividad mission-welcome'
            with pytest.raises(ValueError, match=mensaje):
                cargar.preparar_base(url, 'plataforma', crear_tablas=True)
        motor = crear_motor_bd(url)
        try:
            with motor.connect() as conexion:
                assert all(conexion.execute(select(tabla)).first() is None for tabla in m.Base.metadata.sorted_tables)
        finally:
            motor.dispose()
    url = f'sqlite:///{(tmp_path / "orden.db").as_posix()}'
    original = plataforma._cargar_riasec
    def invertir(sesion, actividades):
        dimensiones = original(sesion, actividades)
        for n, dimension in enumerate(reversed(list(dimensiones.values())), 1):
            dimension.orden = n
        return dimensiones
    with monkeypatch.context() as parche:
        parche.setattr(plataforma, '_cargar_riasec', invertir)
        cargar.preparar_base(url, 'plataforma', crear_tablas=True)
    archivo = plataforma._leer_catalogo_seleccionado()
    motor = crear_motor_bd(url)
    try:
        with Session(motor) as sesion:
            filas = sesion.execute(select(m.Ocupacion.codigo, m.Dimension.codigo, m.PuntajeOcupacion.valor)
                .select_from(m.PuntajeOcupacion).join(m.Ocupacion).join(m.Dimension)).all()
            esperados = {(codigo, dimension): fila.valores[n] for codigo, fila in archivo.items()
                         for n, (dimension, _) in enumerate(plataforma.DIMENSIONES_RIASEC)}
            assert {(codigo, dimension): valor for codigo, dimension, valor in filas} == esperados
    finally:
        motor.dispose()
