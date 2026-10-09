"""Fase 1: definiciones, importación de O*NET, restricciones y esquema versión 2."""

from datetime import datetime

import pytest
from openpyxl import Workbook
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app import models as modelos
from datos.ocupaciones import OcupacionArchivo, leer_ocupaciones


FECHA = datetime(2026, 10, 1, 10)


def buscar(sesion, modelo, codigo):
    return sesion.scalar(select(modelo).where(modelo.codigo == codigo))


def crear_excel(tmp_path, filas, encabezado=("code", "title", "R", "I", "A", "S", "E", "C")):
    ruta = tmp_path / "ocupaciones.xlsx"
    libro = Workbook()
    libro.active.append(encabezado)
    for fila in filas:
        libro.active.append(fila)
    libro.save(ruta)
    libro.close()
    return ruta


def test_excel_valido_conserva_orden_y_valores(tmp_path):
    ruta = crear_excel(tmp_path, [("19-1031.02", "Range Managers", 1, 2, 3, 4, 5, 6),
                                  (None,) * 8, ("17-2021.00", "Agricultural Engineers", 4.2, 1.8, 3.4, 4, 5.6, 3)])
    assert leer_ocupaciones(ruta) == [OcupacionArchivo("19-1031.02", "Range Managers", (1, 2, 3, 4, 5, 6)),
                                    OcupacionArchivo("17-2021.00", "Agricultural Engineers", (4.2, 1.8, 3.4, 4, 5.6, 3))]


@pytest.mark.parametrize("caso, mensaje", [
    ("columnas", "Columnas"), ("repetido", "Código O\\*NET repetido"),
    ("texto", "Valor no numérico"), ("vacio", "Valor no numérico"), ("booleano", "Valor no numérico"),
    ("codigo", "Código O\\*NET inválido"), ("titulo", "Título de ocupación inválido"),
    ("sin_filas", "no contiene datos"),
])
def test_excel_rechaza_datos_invalidos(tmp_path, caso, mensaje):
    fila = ["19-1031.02", "Range Managers", 1, 2, 3, 4, 5, 6]
    filas = [fila]
    encabezado = ("code", "title", "R", "I", "A", "S", "E", "C")
    if caso == "columnas":
        encabezado = ("codigo", *encabezado[1:])
    elif caso == "repetido":
        filas = [fila, fila.copy()]
    elif caso in {"texto", "vacio", "booleano"}:
        fila[2] = {"texto": "no numérico", "vacio": None, "booleano": True}[caso]
    elif caso == "codigo":
        fila[0] = None
    elif caso == "titulo":
        fila[1] = " "
    elif caso == "sin_filas":
        filas = []
    with pytest.raises(ValueError, match=mensaje):
        leer_ocupaciones(crear_excel(tmp_path, filas, encabezado))


def test_excel_ausente_o_ilegible(tmp_path):
    with pytest.raises(ValueError, match="Falta el archivo"):
        leer_ocupaciones(tmp_path / "ausente.xlsx")
    ruta = tmp_path / "ilegible.xlsx"
    ruta.write_text("No es un Excel", encoding="utf-8")
    with pytest.raises(ValueError, match="No se puede leer"):
        leer_ocupaciones(ruta)


def test_dos_resultados_vigentes_prohibidos(sesion):
    ana = buscar(sesion, modelos.Cuenta, "est-ana")
    aplicacion = buscar(sesion, modelos.Aplicacion, "APL-RIASEC")
    resultado = modelos.ResultadoInstrumento(cuenta_id=ana.id, aplicacion_id=aplicacion.id, calculado_en=FECHA)
    sesion.add(resultado)
    sesion.flush()
    with pytest.raises(IntegrityError):
        with sesion.begin_nested():
            sesion.add(modelos.ResultadoInstrumento(cuenta_id=ana.id, aplicacion_id=aplicacion.id, calculado_en=FECHA))
            sesion.flush()
    resultado.anulado_en = FECHA
    sesion.flush()
    sesion.add(modelos.ResultadoInstrumento(cuenta_id=ana.id, aplicacion_id=aplicacion.id, calculado_en=FECHA))
    sesion.flush()
    assert sesion.scalar(select(func.count()).select_from(modelos.ResultadoInstrumento)) == 2


@pytest.mark.parametrize("correlacion, ajuste, posicion", [
    (-0.1, "GOOD_FIT", 1), (0.7, "BEST_FIT", 1), (0.729, "GREAT_FIT", 1),
    (0.607, "GREAT_FIT", 1), (0.608, "GOOD_FIT", 1), (0.9, "BEST_FIT", 0), (0.9, "BEST_FIT", 11),
])
def test_coincidencias_rechazan_ajustes_y_posiciones_invalidas(sesion, correlacion, ajuste, posicion):
    # Ocupación independiente del Excel, únicamente para probar restricciones SQL.
    ocupacion = modelos.Ocupacion(codigo_onet="PRUEBA", titulo="Prueba SQL")
    sesion.add(ocupacion)
    resultado = modelos.ResultadoInstrumento(cuenta_id=buscar(sesion, modelos.Cuenta, "est-ana").id,
                                             aplicacion_id=buscar(sesion, modelos.Aplicacion, "APL-RIASEC").id,
                                             calculado_en=FECHA)
    sesion.add(resultado)
    sesion.flush()
    with pytest.raises(IntegrityError):
        with sesion.begin_nested():
            sesion.add(modelos.Coincidencia(resultado_id=resultado.id, ocupacion_id=ocupacion.id,
                                          posicion=posicion, correlacion=correlacion, ajuste=ajuste))
            sesion.flush()
