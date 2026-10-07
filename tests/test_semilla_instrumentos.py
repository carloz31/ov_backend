"""Fase 1: definiciones, importación de O*NET, restricciones y esquema versión 2."""

from collections import Counter
from datetime import datetime
from pathlib import Path
import sqlite3

from fastapi.testclient import TestClient
from openpyxl import Workbook
import pytest
from sqlalchemy import delete, func, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models as modelos
from app import semilla_instrumentos
from app.database import Base, MENSAJE_ESQUEMA_ANTERIOR, crear_motor_bd
from app.main import crear_aplicacion
from app.seed import cargar_semilla
from app.semilla_instrumentos import (
    OcupacionArchivo, cargar_catalogo_ocupaciones, leer_ocupaciones, relaciones_carreras,
    validar_distribucion_items,
)


FECHA = datetime(2026, 10, 1, 10)
RUTA_REAL = semilla_instrumentos.RUTA_OCUPACIONES
REQUIERE_EXCEL = pytest.mark.skipif(not RUTA_REAL.is_file(), reason=f"Falta el catálogo O*NET: {RUTA_REAL}")


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


def test_catalogos_y_estado_inicial_de_instrumentos(sesion, cliente):
    assert sesion.scalars(select(modelos.EsquemaVersion.version)).all() == [4]
    for modelo, cantidad in (
        (modelos.Instrumento, 4), (modelos.Dimension, 19), (modelos.EscalaRespuesta, 4),
        (modelos.OpcionEscala, 13), (modelos.ItemInstrumento, 137),
        (modelos.Aplicacion, 5), (modelos.AplicacionActividad, 9), (modelos.ActividadItem, 147),
        (modelos.Bloque, 11), (modelos.Actividad, 30), (modelos.Carrera, 8),
        (modelos.ReglaDesbloqueo, 47), (modelos.CondicionDesbloqueo, 58),
        (modelos.RespuestaItem, 0), (modelos.ResultadoInstrumento, 0),
        (modelos.ResultadoDimension, 0), (modelos.Coincidencia, 0),
    ):
        assert sesion.scalar(select(func.count()).select_from(modelo)) == cantidad
    assert sesion.scalar(select(func.count()).select_from(modelos.Actividad).join(modelos.Bloque).where(
        modelos.Bloque.audiencia == modelos.Audiencia.ESTUDIANTE,
    )) == 28
    for cuenta in ("est-ana", "est-luis"):
        bloques = cliente.get(f"/cuentas/{cuenta}/estado").json()["bloques"]
        lab = next(b for b in bloques if b["codigo"] == "LAB")
        assert lab["estado"] == "DISPONIBLE"
        assert {a["codigo"]: a["estado"] for a in lab["actividades"]} == {
            "LAB-AUT-E": "DISPONIBLE", "LAB-AUT-S": "BLOQUEADA", "LAB-HAB": "DISPONIBLE",
            "LAB-INT1": "DISPONIBLE", "LAB-INT2": "BLOQUEADA", "LAB-RIA1": "DISPONIBLE",
            "LAB-RIA2": "BLOQUEADA", "LAB-RIA3": "BLOQUEADA", "LAB-RIA4": "BLOQUEADA",
        }
    assert [b["codigo"] for b in cliente.get("/cuentas/apo-rosa/estado").json()["bloques"]] == ["P1"]
    assert sesion.scalar(select(func.count()).select_from(modelos.EventoUso)) == 0
    validar_distribucion_items(sesion)


def test_escalas_y_puntajes_exactos(sesion):
    esperadas = {
        "ESC-LIKERT5": [("Me disgusta mucho", 0), ("Me disgusta", 1), ("No estoy seguro", 2),
                        ("Me gusta", 3), ("Me gusta mucho", 4)],
        "ESC-SI-NO": [("Sí", 1), ("No", 0)],
        "ESC-FRECUENCIA": [("Casi siempre", 1), ("Casi nunca", 0)],
        "ESC-A-D": [("A (Bastante)", 4), ("B (Regular)", 3), ("C (Poco)", 2), ("D (Nada)", 1)],
    }
    for codigo, opciones in esperadas.items():
        escala = buscar(sesion, modelos.EscalaRespuesta, codigo)
        assert sesion.execute(select(modelos.OpcionEscala.orden, modelos.OpcionEscala.etiqueta,
                                     modelos.OpcionEscala.puntaje).where(
            modelos.OpcionEscala.escala_id == escala.id,
        ).order_by(modelos.OpcionEscala.orden)).all() == [
            (n, etiqueta, puntaje) for n, (etiqueta, puntaje) in enumerate(opciones, start=1)
        ]


def test_rejillas_dimensiones_y_enunciados(sesion):
    esperadas = {
        "R": [1, 2, 13, 14, 25, 26, 37, 38, 49, 50],
        "I": [3, 4, 15, 16, 27, 28, 39, 40, 51, 52],
        "A": [5, 6, 17, 18, 29, 30, 41, 42, 53, 54],
        "S": [7, 8, 19, 20, 31, 32, 43, 44, 55, 56],
        "E": [9, 10, 21, 22, 33, 34, 45, 46, 57, 58],
        "C": [11, 12, 23, 24, 35, 36, 47, 48, 59, 60],
        "INT-LIN": [1, 8, 11, 17, 21, 24, 27, 36, 41, 43],
        "INT-LOG": [3, 6, 13, 20, 25, 28, 37], "INT-ESP": [7, 18, 26, 29],
        "INT-CIN": [2, 14, 19, 30, 38], "INT-MUS": [5, 10, 31, 39],
        "INT-INTER": [4, 9, 16, 22, 32, 34, 40, 42], "INT-INTRA": [12, 15, 23, 33, 35],
        "HAB-ASE": [1, 10, 15, 19, 21], "HAB-EMP": [4, 7, 16, 22], "HAB-LID": [5, 14, 20],
        "HAB-RES": [6, 13, 17, 24], "HAB-EXP": [3, 8, 23], "HAB-VAL": [2, 9, 11, 12, 18],
    }
    dimensiones = sesion.scalars(select(modelos.Dimension)).all()
    assert {d.codigo for d in dimensiones} == set(esperadas)
    for dimension in dimensiones:
        assert sesion.scalars(select(modelos.ItemInstrumento.numero).where(
            modelos.ItemInstrumento.dimension_id == dimension.id,
        ).order_by(modelos.ItemInstrumento.numero)).all() == esperadas[dimension.codigo]
    riasec = buscar(sesion, modelos.Instrumento, "TEST-RIASEC")
    assert sesion.scalars(select(modelos.Dimension.codigo).where(
        modelos.Dimension.instrumento_id == riasec.id,
    ).order_by(modelos.Dimension.orden)).all() == list("RIASEC")
    assert set(sesion.scalars(select(modelos.ItemInstrumento.codigo).where(
        modelos.ItemInstrumento.inverso.is_(True),
    ))) == {"HAB-03", "HAB-05", "HAB-08", "HAB-20"}
    auto = buscar(sesion, modelos.Instrumento, "TEST-AUTO")
    assert sesion.scalars(select(modelos.Dimension.id).where(modelos.Dimension.instrumento_id == auto.id)).all() == []
    items_auto = sesion.scalars(select(modelos.ItemInstrumento).where(
        modelos.ItemInstrumento.instrumento_id == auto.id,
    ).order_by(modelos.ItemInstrumento.numero)).all()
    for item in items_auto:
        assert item.dimension_id is None
        assert sesion.scalar(select(func.count()).select_from(modelos.ActividadItem).where(
            modelos.ActividadItem.item_id == item.id,
        )) == 2
    especificacion = (Path(__file__).resolve().parents[1] / "docs/spec-demo-instrumentos.md").read_text(encoding="utf-8")
    for item in sesion.scalars(select(modelos.ItemInstrumento)):
        instrumento = sesion.get(modelos.Instrumento, item.instrumento_id)
        if instrumento.codigo == "TEST-AUTO":
            assert f"  {item.numero}. {item.enunciado}" in especificacion
        else:
            assert item.enunciado == f"Ítem {item.numero} de {instrumento.nombre}"


def test_items_por_actividad_y_aplicacion(sesion):
    esperadas = {
        "LAB-AUT-E": ("APL-AUTO-ENT", "AUT", 1, 10), "LAB-AUT-S": ("APL-AUTO-SAL", "AUT", 1, 10),
        "LAB-HAB": ("APL-HAB", "HAB", 1, 24), "LAB-INT1": ("APL-INT", "INT", 1, 22),
        "LAB-INT2": ("APL-INT", "INT", 23, 43), "LAB-RIA1": ("APL-RIASEC", "RIASEC", 1, 15),
        "LAB-RIA2": ("APL-RIASEC", "RIASEC", 16, 30), "LAB-RIA3": ("APL-RIASEC", "RIASEC", 31, 45),
        "LAB-RIA4": ("APL-RIASEC", "RIASEC", 46, 60),
    }
    for codigo, (aplicacion, prefijo, inicio, fin) in esperadas.items():
        actividad = buscar(sesion, modelos.Actividad, codigo)
        assert sesion.execute(select(modelos.ItemInstrumento.codigo, modelos.ActividadItem.orden).join(
            modelos.ActividadItem, modelos.ActividadItem.item_id == modelos.ItemInstrumento.id,
        ).where(modelos.ActividadItem.actividad_id == actividad.id).order_by(modelos.ActividadItem.orden)).all() == [
            (f"{prefijo}-{numero:02}", orden) for orden, numero in enumerate(range(inicio, fin + 1), start=1)
        ]
        assert sesion.scalars(select(modelos.Aplicacion.codigo).join(modelos.AplicacionActividad).where(
            modelos.AplicacionActividad.actividad_id == actividad.id,
        )).all() == [aplicacion]


@pytest.mark.parametrize("caso", ["faltante", "repetido", "ajeno"])
def test_distribucion_rechaza_items_faltantes_repetidos_y_ajenos(sesion, caso):
    primera = buscar(sesion, modelos.Actividad, "LAB-RIA1")
    segunda = buscar(sesion, modelos.Actividad, "LAB-RIA2")
    item = buscar(sesion, modelos.ItemInstrumento, "RIASEC-01")
    if caso == "faltante":
        sesion.execute(delete(modelos.ActividadItem).where(modelos.ActividadItem.actividad_id == primera.id,
                                                         modelos.ActividadItem.item_id == item.id))
    else:
        if caso == "ajeno":
            item = buscar(sesion, modelos.ItemInstrumento, "INT-01")
        sesion.add(modelos.ActividadItem(actividad_id=segunda.id, item_id=item.id, orden=16))
    sesion.flush()
    with pytest.raises(ValueError, match="Distribución inválida en APL-RIASEC") as error:
        validar_distribucion_items(sesion)
    assert item.codigo in str(error.value)


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


def ocupaciones_para_relaciones():
    # Datos sintéticos exclusivos de validación; nunca se cargan en la demo real.
    return [OcupacionArchivo(codigo, "Prueba", (1, 2, 3, 4, 5, 6)) for codigo in (
        "29-1141.00", "29-1216.00", "17-2051.00", "27-1024.00", "11-1021.00", "17-2021.00",
        "19-1031.02", "19-1032.00", "17-2199.11", "19-2041.02",
    )]


@pytest.mark.parametrize("codigo", [o.codigo_onet for o in ocupaciones_para_relaciones()])
def test_relaciones_exigen_todas_las_ocupaciones(codigo):
    filas = [o for o in ocupaciones_para_relaciones() if o.codigo_onet != codigo]
    with pytest.raises(ValueError, match=codigo):
        relaciones_carreras(filas)


def test_medicina_utiliza_el_primero_del_archivo_si_falta_codigo(caplog):
    filas = [o for o in ocupaciones_para_relaciones() if o.codigo_onet != "29-1216.00"]
    filas.extend([OcupacionArchivo("29-1299.00", "Primera", (1,) * 6),
                  OcupacionArchivo("29-1211.00", "Segunda", (2,) * 6)])
    assert relaciones_carreras(filas)["CAR-MED"] == ("29-1299.00",)
    assert "29-1299.00" in caplog.text


@REQUIERE_EXCEL
def test_catalogo_real_y_relaciones_exactas(sesion):
    archivo = leer_ocupaciones(RUTA_REAL)
    assert len(archivo) == 923
    ocupaciones = sesion.scalars(select(modelos.Ocupacion)).all()
    assert {o.codigo_onet: o.titulo for o in ocupaciones} == {o.codigo_onet: o.titulo for o in archivo}
    assert sesion.scalar(select(func.count()).select_from(modelos.PuntajeOcupacion)) == 5538
    dimensiones = {d.id: d.codigo for d in sesion.scalars(select(modelos.Dimension))}
    codigos = {o.id: o.codigo_onet for o in ocupaciones}
    puntajes = {(codigos[p.ocupacion_id], dimensiones[p.dimension_id]): p.valor
                for p in sesion.scalars(select(modelos.PuntajeOcupacion))}
    assert puntajes == {(o.codigo_onet, d): v for o in archivo for d, v in zip("RIASEC", o.valores, strict=True)}
    relaciones = sesion.execute(select(modelos.Carrera.codigo, modelos.Ocupacion.codigo_onet).join(
        modelos.CarreraOcupacion, modelos.CarreraOcupacion.carrera_id == modelos.Carrera.id,
    ).join(modelos.Ocupacion, modelos.Ocupacion.id == modelos.CarreraOcupacion.ocupacion_id)).all()
    assert set(relaciones) == {
        ("CAR-ENF", "29-1141.00"), ("CAR-MED", "29-1216.00"), ("CAR-CIV", "17-2051.00"),
        ("CAR-DIS", "27-1024.00"), ("CAR-ADM", "11-1021.00"), ("CAR-AGR", "17-2021.00"),
        ("CAR-FOR", "19-1031.02"), ("CAR-FOR", "19-1032.00"),
        ("CAR-AMB", "17-2199.11"), ("CAR-AMB", "19-2041.02"),
    }
    assert Counter(c for c, _ in relaciones) == {
        "CAR-ENF": 1, "CAR-MED": 1, "CAR-CIV": 1, "CAR-DIS": 1, "CAR-ADM": 1,
        "CAR-AGR": 1, "CAR-FOR": 2, "CAR-AMB": 2,
    }


def test_version_unica_y_dos_resultados_vigentes_prohibidos(sesion):
    with pytest.raises(IntegrityError):
        with sesion.begin_nested():
            sesion.add(modelos.EsquemaVersion(id=2, version=2))
            sesion.flush()
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


def test_respuestas_opciones_e_items_unicos(sesion):
    item = buscar(sesion, modelos.ItemInstrumento, "RIASEC-01")
    ana = buscar(sesion, modelos.Cuenta, "est-ana")
    actividad = buscar(sesion, modelos.Actividad, "LAB-RIA1")
    progreso = modelos.ProgresoActividad(cuenta_id=ana.id, actividad_id=actividad.id, estado=modelos.EstadoProgreso.EN_CURSO)
    sesion.add(progreso)
    sesion.flush()
    opcion = sesion.scalar(select(modelos.OpcionEscala).where(modelos.OpcionEscala.escala_id == item.escala_id,
                                                           modelos.OpcionEscala.orden == 1))
    sesion.add(modelos.RespuestaItem(progreso_id=progreso.id, item_id=item.id, opcion_id=opcion.id,
                                    creada_en=FECHA, actualizada_en=FECHA))
    sesion.flush()
    duplicados = [
        modelos.RespuestaItem(progreso_id=progreso.id, item_id=item.id, opcion_id=opcion.id,
                             creada_en=FECHA, actualizada_en=FECHA),
        modelos.OpcionEscala(escala_id=item.escala_id, orden=1, etiqueta="Duplicada", puntaje=0),
        modelos.ItemInstrumento(instrumento_id=item.instrumento_id, codigo="DUP-01", numero=1,
                                enunciado="Duplicado", escala_id=item.escala_id),
        modelos.ActividadItem(actividad_id=actividad.id, item_id=item.id, orden=2),
    ]
    for duplicado in duplicados:
        with pytest.raises(IntegrityError):
            with sesion.begin_nested():
                sesion.add(duplicado)
                sesion.flush()


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


@pytest.mark.parametrize("version", [None, 1, 3, 5, "sin_fila"])
def test_arranque_rechaza_esquema_anterior_sin_modificar_base(tmp_path, version):
    ruta = tmp_path / "prueba.db"
    motor = crear_motor_bd(f"sqlite:///{ruta.as_posix()}")
    if version is None:
        with motor.begin() as conexion:
            conexion.execute(text("CREATE TABLE cuenta (id INTEGER PRIMARY KEY, codigo TEXT)"))
            conexion.execute(text("INSERT INTO cuenta VALUES (1, 'dato-anterior')"))
    else:
        Base.metadata.create_all(motor)
        if version != "sin_fila":
            with motor.begin() as conexion:
                conexion.execute(text("INSERT INTO esquema_version (id, version) VALUES (1, :version)"), {"version": version})
    motor.dispose()
    antes = ruta.read_bytes()
    aplicacion = crear_aplicacion(f"sqlite:///{ruta.as_posix()}")
    with pytest.raises(RuntimeError) as error:
        with TestClient(aplicacion):
            pass
    assert str(error.value) == MENSAJE_ESQUEMA_ANTERIOR
    assert ruta.read_bytes() == antes
    with sqlite3.connect(ruta) as conexion:
        if version is None:
            assert conexion.execute("SELECT codigo FROM cuenta").fetchall() == [("dato-anterior",)]
            assert conexion.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall() == [("cuenta",)]


def test_arranque_no_repara_base_version_dos_con_tablas_faltantes(tmp_path):
    ruta = tmp_path / "parcial.db"
    with sqlite3.connect(ruta) as conexion:
        conexion.execute("CREATE TABLE esquema_version (id INTEGER PRIMARY KEY, version INTEGER)")
        conexion.execute("INSERT INTO esquema_version VALUES (1, 2)")
    antes = ruta.read_bytes()
    with pytest.raises(RuntimeError, match="esquema anterior"):
        with TestClient(crear_aplicacion(f"sqlite:///{ruta.as_posix()}")):
            pass
    assert ruta.read_bytes() == antes


def test_reinicio_escribe_version_dos_y_catalogo_completo(cliente, aplicacion):
    for _ in range(2):
        assert cliente.post("/demo/reiniciar").json() == {"mensaje": "Demo reiniciada"}
        with aplicacion.state.fabrica_sesiones() as sesion:
            assert sesion.scalars(select(modelos.EsquemaVersion.version)).all() == [4]
            assert sesion.scalar(select(func.count()).select_from(modelos.ItemInstrumento)) == 137
            assert sesion.scalar(select(func.count()).select_from(modelos.ReglaDesbloqueo)) == 47
            validar_distribucion_items(sesion)
    assert len(inspect(aplicacion.state.motor_bd).get_table_names()) == 45


@pytest.mark.parametrize("fallo", ["ausente", "columnas", "codigo_requerido"])
def test_error_de_catalogo_revierte_toda_la_semilla(tmp_path, monkeypatch, fallo):
    if fallo == "ausente":
        ruta = tmp_path / "ausente.xlsx"
        mensaje = "Falta el archivo"
    elif fallo == "columnas":
        ruta = crear_excel(tmp_path, [], ("invalido",))
        mensaje = "Columnas"
    else:
        ruta = crear_excel(tmp_path, [("19-1031.02", "Range Managers", 1, 2, 3, 4, 5, 6)])
        mensaje = "29-1141.00"
    monkeypatch.setattr(semilla_instrumentos, "RUTA_OCUPACIONES", ruta)
    monkeypatch.setattr(semilla_instrumentos, "cargar_catalogo_ocupaciones", cargar_catalogo_ocupaciones)
    motor = crear_motor_bd(f"sqlite:///{(tmp_path / 'semilla.db').as_posix()}")
    try:
        Base.metadata.create_all(motor)
        with Session(motor) as sesion:
            with pytest.raises(ValueError, match=mensaje):
                with sesion.begin():
                    cargar_semilla(sesion)
        with Session(motor) as sesion:
            for tabla in Base.metadata.sorted_tables:
                assert sesion.scalar(select(func.count()).select_from(tabla)) == 0
    finally:
        motor.dispose()


def test_reinicio_con_excel_invalido_conserva_estado_y_muestra_error(cliente, aplicacion, tmp_path, monkeypatch):
    assert cliente.post("/acciones/completar-actividad", json={
        "cuenta": "est-ana", "actividad": "ACT-01",
    }).status_code == 200
    estado = cliente.get("/cuentas/est-ana/estado").json()
    eventos = cliente.get("/cuentas/est-ana/eventos").json()
    desbloqueos = cliente.get("/cuentas/est-ana/desbloqueos").json()
    monkeypatch.setattr(semilla_instrumentos, "RUTA_OCUPACIONES", tmp_path / "ausente.xlsx")
    monkeypatch.setattr(semilla_instrumentos, "cargar_catalogo_ocupaciones", cargar_catalogo_ocupaciones)
    respuesta = cliente.post("/demo/reiniciar")
    assert respuesta.status_code == 422
    assert "Falta el archivo" in respuesta.json()["detail"]["mensaje"]
    assert cliente.get("/cuentas/est-ana/estado").json() == estado
    assert cliente.get("/cuentas/est-ana/eventos").json() == eventos
    assert cliente.get("/cuentas/est-ana/desbloqueos").json() == desbloqueos
    with aplicacion.state.fabrica_sesiones() as sesion:
        assert sesion.scalars(select(modelos.EsquemaVersion.version)).all() == [4]
