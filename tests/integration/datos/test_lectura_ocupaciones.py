"""Lectura ocupaciones."""

import pytest
from openpyxl import Workbook
from datos.ocupaciones import OcupacionArchivo, leer_ocupaciones


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
