import re
from datetime import date, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, inspect, select, text
from sqlalchemy.exc import IntegrityError

from app import models as modelos
from app.main import crear_aplicacion
from app.models.base import Base
from datos.cargar import preparar_base


ESPECIFICACION = (Path(__file__).resolve().parents[1] / "docs" /
                 "spec-demo-motor-desbloqueos.md").read_text(encoding="utf-8")
ESPECIFICACION_INSTRUMENTOS = (Path(__file__).resolve().parents[1] / "docs" /
                             "spec-demo-instrumentos.md").read_text(encoding="utf-8")
FECHA = datetime(2026, 10, 1, 10)
TABLAS_ESTADO = {
    "progreso_actividad", "resultado_caso", "entrada_diario", "check_in",
    "entrevista", "entrevista_autor", "conversacion_vinculo", "evento_uso", "desbloqueo",
    "respuesta_item", "resultado_instrumento", "resultado_dimension", "coincidencia",
    "respuesta_registro", "turno_seguimiento", "evaluacion_respuesta",
}


def seccion(numero):
    coincidencia = re.search(rf"^### {re.escape(numero)} .*?(?=^### |^## |\Z)",
                            ESPECIFICACION, re.MULTILINE | re.DOTALL)
    assert coincidencia is not None
    return coincidencia.group()


def filas_tabla(documento):
    return [
        [columna.strip() for columna in linea.strip().strip("|").split("|")]
        for linea in documento.splitlines() if linea.startswith("|")
    ]


def por_codigo(sesion, modelo):
    return {fila.codigo: fila for fila in sesion.scalars(select(modelo))}


def test_tablas_indices_y_claves_foraneas(aplicacion, cliente):
    inspector = inspect(aplicacion.state.motor_bd)
    esperadas = {
        "cuenta", "vinculo_familiar", "bloque", "actividad", "ficha", "testimonio",
        "pregunta_diario", "conversacion", "insignia", "nivel", "familia_carrera",
        "carrera", "regla_desbloqueo", "condicion_desbloqueo",
    } | TABLAS_ESTADO
    esperadas |= {
        "instrumento", "dimension", "escala_respuesta", "opcion_escala", "item_instrumento",
        "actividad_item", "aplicacion", "aplicacion_actividad", "ocupacion", "puntaje_ocupacion",
        "carrera_ocupacion", "esquema_version",
        "item_registro", "criterio_completitud", "actividad_item_registro",
    }
    assert set(inspector.get_table_names()) == esperadas
    assert len(esperadas) == 45
    assert inspector.get_pk_constraint("entrevista_autor")["constrained_columns"] == [
        "entrevista_id", "cuenta_id",
    ]
    assert any(indice["column_names"] == ["cuenta_id", "tipo"]
               for indice in inspector.get_indexes("evento_uso"))
    with aplicacion.state.motor_bd.connect() as conexion:
        assert conexion.scalar(text("PRAGMA foreign_keys")) == 1
        assert conexion.execute(text("PRAGMA foreign_key_check")).all() == []
        assert conexion.scalar(text("SELECT rol FROM cuenta WHERE codigo='est-ana'")) == "ESTUDIANTE"


def test_cuentas_y_vinculo_segun_especificacion(sesion):
    cuentas = por_codigo(sesion, modelos.Cuenta)
    esperadas = {codigo: (nombre, rol) for codigo, nombre, rol in filas_tabla(seccion("7.1"))
                 if codigo.startswith(("est-", "apo-"))}
    assert {codigo: (cuenta.nombre, cuenta.rol.value) for codigo, cuenta in cuentas.items()} == esperadas
    vinculos = sesion.scalars(select(modelos.VinculoFamiliar)).all()
    assert len(vinculos) == 1
    vinculo = vinculos[0]
    assert vinculo.codigo == "VIN-ANA"
    assert vinculo.estudiante_id == cuentas["est-ana"].id
    assert vinculo.apoderado_id == cuentas["apo-rosa"].id
    assert vinculo.carta_estudiante is None and vinculo.carta_apoderado is None


def test_bloques_y_actividades_segun_especificacion(sesion):
    bloques = por_codigo(sesion, modelos.Bloque)
    actividades = por_codigo(sesion, modelos.Actividad)
    esperadas = {}
    filas = [fila for fila in filas_tabla(seccion("7.2")) if re.fullmatch(r"[BCP]\d+", fila[0])]
    assert set(bloques) == {fila[0] for fila in filas} | {"LAB", "REG"}
    for codigo, nombre, espacio, audiencia, contenido in filas:
        bloque = bloques[codigo]
        assert (bloque.nombre, bloque.espacio.value, bloque.audiencia.value) == (nombre, espacio, audiencia)
        assert bloque.numero == int(codigo[1:])
        patron = r"([\w-]+) ([^(]+) \((INFORMATIVA|REGISTRO|CUESTIONARIO|CASO)(?:, mínimo (\d+))?\)"
        for orden, (actividad, titulo, tipo, minimo) in enumerate(re.findall(patron, contenido), start=1):
            esperadas[actividad] = (titulo, tipo, orden, bloque.id, float(minimo) if minimo else None)
    assert len(esperadas) == 20
    lab = bloques["LAB"]
    assert (lab.nombre, lab.espacio.value, lab.audiencia.value, lab.numero) == (
        "Laboratorio de Helena (solo demo)", "CIUDAD", "ESTUDIANTE", 0,
    )
    for fila in filas_tabla(ESPECIFICACION_INSTRUMENTOS):
        coincidencia = re.fullmatch(r"(LAB-[\w-]+) \((\d+)\)", fila[0])
        if coincidencia:
            codigo_orden, titulo, tipo, _ = fila
            esperadas[coincidencia[1]] = (titulo, tipo, int(coincidencia[2]), lab.id, None)
    assert len(esperadas) == 29
    esperadas["REG-ACT08"] = ("Mi plan para fortalecer una habilidad", "REGISTRO", 1, bloques["REG"].id, None)
    assert len(esperadas) == 30
    assert {codigo: (fila.titulo, fila.tipo.value, fila.orden, fila.bloque_id, fila.puntaje_minimo)
            for codigo, fila in actividades.items()} == esperadas


def test_contenido_familias_y_carreras_segun_especificacion(sesion):
    filas = filas_tabla(seccion("7.3"))
    for tipo, modelo, atributo in (
        ("Ficha", modelos.Ficha, "titulo"), ("Testimonio", modelos.Testimonio, "titulo"),
        ("Pregunta de diario", modelos.PreguntaDiario, "pregunta"),
        ("Conversación", modelos.Conversacion, "titulo"),
    ):
        esperadas = {fila[1]: fila[2] for fila in filas if fila[0] == tipo}
        assert {codigo: getattr(fila, atributo) for codigo, fila in por_codigo(sesion, modelo).items()} == esperadas
    familias = por_codigo(sesion, modelos.FamiliaCarrera)
    esperadas = {}
    filas_familias = [fila for fila in filas if fila[0].startswith("FAM-")]
    assert set(familias) == {fila[0] for fila in filas_familias}
    for codigo_familia, carreras in filas_familias:
        for carrera in carreras.split(", "):
            codigo, nombre = carrera.split(" ", 1)
            esperadas[codigo] = (nombre, familias[codigo_familia].id)
    for codigo, nombre in (("CAR-AGR", "Ingeniería agrícola"), ("CAR-FOR", "Ingeniería forestal"),
                           ("CAR-AMB", "Ingeniería ambiental")):
        esperadas[codigo] = (nombre, familias["FAM-INGENIERIA"].id)
    assert len(esperadas) == 8
    assert {codigo: (fila.nombre, fila.familia_id) for codigo, fila in
            por_codigo(sesion, modelos.Carrera).items()} == esperadas


def test_insignias_y_niveles_segun_especificacion(sesion):
    esperadas = {
        codigo: (nombre, oculta == "sí", audiencia, requisito.removeprefix("(oculto) "))
        for codigo, nombre, oculta, audiencia, requisito in filas_tabla(seccion("7.4"))
        if codigo.startswith(("INS-", "LOG-"))
    }
    assert {codigo: (fila.nombre, fila.es_oculta, fila.audiencia.value, fila.requisito)
            for codigo, fila in por_codigo(sesion, modelos.Insignia).items()} == esperadas
    assert all(fila.descripcion for fila in por_codigo(sesion, modelos.Insignia).values())
    assert {fila.numero: fila.titulo for fila in sesion.scalars(select(modelos.Nivel))} == {
        int(numero): titulo for numero, titulo in filas_tabla(seccion("7.5")) if numero.isdigit()
    }


def reglas_esperadas():
    """Lee las condiciones del documento, sin importar constantes de la semilla."""
    resultado = {}
    filas = filas_tabla(seccion("7.6")) + [fila for fila in filas_tabla(ESPECIFICACION_INSTRUMENTOS)
                                          if fila[0].startswith("R-LAB-")]
    for fila in filas:
        if not fila[0].startswith("R-"):
            continue
        codigo, objetivo, descripcion, *especial = fila
        condiciones = []
        anterior = re.search(r"lo de (R-NIV-\d+)", descripcion)
        if anterior:
            condiciones.extend(resultado[anterior[1]]["condiciones"])
        patron = r"([A-Z_]+)(?:\(([^)]+)\))?(?: (EVENTOS|REFERENCIAS_DISTINTAS|DIAS_DISTINTOS))? ≥ (\d+)"
        for evento, referencia, conteo, cantidad in re.findall(patron, descripcion):
            condiciones.append({
                "tipo_evento": evento, "referencia": referencia or None,
                "tipo_conteo": conteo or "EVENTOS", "cantidad_minima": int(cantidad),
            })
        if objetivo.startswith("nivel "):
            tipo, objetivo = "NIVEL", f"N{objetivo.split()[-1]}"
        elif objetivo == "CONVERSACIONES":
            tipo, objetivo = "CONVERSACIONES", "-"
        else:
            prefijo = objetivo.split("-")[0]
            tipo = {"FIC": "FICHA", "TES": "TESTIMONIO", "PD": "PREGUNTA_DIARIO",
                    "INS": "INSIGNIA", "LOG": "INSIGNIA"}.get(prefijo, "ACTIVIDAD")
            if re.fullmatch(r"C\d+", objetivo):
                tipo = "BLOQUE"
        resultado[codigo] = {
            "tipo_objetivo": tipo, "objetivo": objetivo, "condiciones": condiciones,
            "evaluador_especial": especial[0] if especial and especial[0] else None,
        }
    return resultado


def test_reglas_completas_segun_especificacion(cliente, sesion):
    respuesta = cliente.get("/reglas")
    assert respuesta.status_code == 200
    reglas = respuesta.json()
    esperadas = reglas_esperadas()
    assert len(reglas) == len(esperadas) == 47
    assert sum(len(regla["condiciones"]) for regla in reglas) == 58
    assert {regla["regla"]: {
        "tipo_objetivo": regla["tipo_objetivo"], "objetivo": regla["objetivo"]["codigo"],
        "condiciones": regla["condiciones"], "evaluador_especial": regla["evaluador_especial"],
    } for regla in reglas} == esperadas
    assert [regla["regla"] for regla in reglas] == sorted(esperadas)
    assert sesion.scalar(select(func.count()).select_from(modelos.CondicionDesbloqueo)) == 58
    for regla in reglas:
        assert regla["nombre"] and regla["objetivo"]["nombre"]
        assert set(regla) == {"regla", "nombre", "tipo_objetivo", "objetivo", "condiciones", "evaluador_especial"}
        assert set(regla["objetivo"]) == {"codigo", "nombre"}
        assert isinstance(regla["objetivo"]["codigo"], str)
        for condicion in regla["condiciones"]:
            assert set(condicion) == {"tipo_evento", "referencia", "tipo_conteo", "cantidad_minima"}
            assert condicion["referencia"] is None or isinstance(condicion["referencia"], str)


def test_arranque_no_repite_semilla_y_conserva_estado(tmp_path):
    url = f"sqlite:///{(tmp_path / 'persistencia.db').as_posix()}"
    preparar_base(url, 'demo', crear_tablas=True)
    primera = crear_aplicacion(url)
    with TestClient(primera) as cliente:
        reglas_iniciales = cliente.get("/reglas").json()
        with primera.state.fabrica_sesiones.begin() as sesion:
            cuenta = sesion.scalar(select(modelos.Cuenta).where(modelos.Cuenta.codigo == "est-ana"))
            cuenta.nombre = "Ana con datos conservados"
            sesion.add(modelos.EventoUso(cuenta_id=cuenta.id, tipo=modelos.TipoEventoUso.INGRESO,
                                         fecha_hora=FECHA))
    segunda = crear_aplicacion(url)
    with TestClient(segunda) as cliente:
        assert cliente.get("/reglas").json() == reglas_iniciales
        with segunda.state.fabrica_sesiones() as sesion:
            assert sesion.scalar(select(func.count()).select_from(modelos.Cuenta)) == 3
            assert sesion.scalar(select(func.count()).select_from(modelos.EventoUso)) == 1
            assert sesion.scalar(select(modelos.Cuenta.nombre).where(
                modelos.Cuenta.codigo == "est-ana")) == "Ana con datos conservados"


def test_reinicio_conserva_catalogo_y_vacia_todo_el_estado(cliente, sesion, aplicacion):
    reglas_iniciales = cliente.get("/reglas").json()
    cuentas = por_codigo(sesion, modelos.Cuenta)
    actividades = por_codigo(sesion, modelos.Actividad)
    ana = cuentas["est-ana"]
    ana.nombre = "Modificado"
    vinculo = sesion.scalar(select(modelos.VinculoFamiliar))
    vinculo.carta_estudiante = "Una carta"
    vinculo.carta_apoderado = "Otra carta"
    progreso = modelos.ProgresoActividad(cuenta_id=ana.id, actividad_id=actividades["CASO-01"].id,
                                         estado=modelos.EstadoProgreso.COMPLETADA)
    entrevista = modelos.Entrevista(codigo="ENT-01", resumen="Resumen", fecha_hora=FECHA)
    sesion.add_all([progreso, entrevista])
    sesion.flush()
    pregunta = sesion.scalar(select(modelos.PreguntaDiario))
    conversacion = sesion.scalar(select(modelos.Conversacion))
    regla = sesion.scalar(select(modelos.ReglaDesbloqueo))
    sesion.add_all([
        modelos.ResultadoCaso(progreso_id=progreso.id, puntaje=85, fecha_hora=FECHA),
        modelos.EntradaDiario(cuenta_id=ana.id, origen=modelos.OrigenEntrada.GUIADA,
                             pregunta_id=pregunta.id, texto="Entrada", fecha_hora=FECHA),
        modelos.CheckIn(cuenta_id=ana.id, fecha=FECHA.date(), nivel_seguridad=3),
        modelos.EntrevistaAutor(entrevista_id=entrevista.id, cuenta_id=ana.id),
        modelos.ConversacionVinculo(vinculo_id=vinculo.id, conversacion_id=conversacion.id,
                                    conversado=True, conversado_en=FECHA),
        modelos.EventoUso(cuenta_id=ana.id, tipo=modelos.TipoEventoUso.INGRESO, fecha_hora=FECHA),
        modelos.Desbloqueo(cuenta_id=ana.id, regla_id=regla.id, fecha_hora=FECHA, visto=True),
    ])
    sesion.commit()
    sesion.close()
    for _ in range(2):
        respuesta = cliente.post("/demo/reiniciar")
        assert respuesta.status_code == 200
        assert respuesta.json() == {"mensaje": "Demo reiniciada"}
        assert cliente.get("/reglas").json() == reglas_iniciales
    with aplicacion.state.fabrica_sesiones() as nueva:
        for nombre in TABLAS_ESTADO:
            assert nueva.scalar(select(func.count()).select_from(Base.metadata.tables[nombre])) == 0
        assert nueva.scalar(select(modelos.Cuenta.nombre).where(modelos.Cuenta.codigo == "est-ana")) == "Modificado"
        vinculo = nueva.scalar(select(modelos.VinculoFamiliar))
        assert vinculo.carta_estudiante == "Una carta" and vinculo.carta_apoderado == "Otra carta"


@pytest.mark.parametrize("modelo,datos", [
    (modelos.ProgresoActividad, {"cuenta_id": 1, "actividad_id": 1, "estado": modelos.EstadoProgreso.COMPLETADA}),
    (modelos.CheckIn, {"cuenta_id": 1, "fecha": date(2026, 10, 1), "nivel_seguridad": 3}),
    (modelos.EntradaDiario, {"cuenta_id": 1, "origen": modelos.OrigenEntrada.GUIADA,
                           "pregunta_id": 1, "texto": "Entrada", "fecha_hora": FECHA}),
    (modelos.Desbloqueo, {"cuenta_id": 1, "regla_id": 1, "fecha_hora": FECHA}),
    (modelos.ConversacionVinculo, {"vinculo_id": 1, "conversacion_id": 1}),
])
def test_estado_no_admite_duplicados(sesion, modelo, datos):
    sesion.add(modelo(**datos))
    sesion.flush()
    with pytest.raises(IntegrityError):
        with sesion.begin_nested():
            sesion.add(modelo(**datos))
            sesion.flush()


def test_codigos_y_numeros_unicos_en_catalogos(sesion):
    catalogos = (modelos.Cuenta, modelos.VinculoFamiliar, modelos.Bloque, modelos.Actividad,
                modelos.Ficha, modelos.Testimonio, modelos.PreguntaDiario, modelos.Conversacion,
                modelos.Insignia, modelos.FamiliaCarrera, modelos.Carrera, modelos.ReglaDesbloqueo,
                modelos.Nivel)
    for modelo in catalogos:
        original = sesion.scalar(select(modelo))
        datos = {columna.name: getattr(original, columna.name) for columna in modelo.__table__.columns
                 if columna.name != "id"}
        with pytest.raises(IntegrityError):
            with sesion.begin_nested():
                sesion.add(modelo(**datos))
                sesion.flush()
    entrevista = modelos.Entrevista(codigo="ENT-01", resumen="Uno", fecha_hora=FECHA)
    sesion.add(entrevista)
    sesion.flush()
    with pytest.raises(IntegrityError):
        with sesion.begin_nested():
            sesion.add(modelos.Entrevista(codigo="ENT-01", resumen="Dos", fecha_hora=FECHA))
            sesion.flush()
    sesion.add(modelos.EntrevistaAutor(entrevista_id=entrevista.id, cuenta_id=1))
    sesion.flush()
    with pytest.raises(IntegrityError):
        with sesion.begin_nested():
            sesion.add(modelos.EntrevistaAutor(entrevista_id=entrevista.id, cuenta_id=1))
            sesion.flush()


def test_entradas_libres_intentos_y_eventos_pueden_repetirse(sesion):
    for _ in range(2):
        sesion.add(modelos.EntradaDiario(cuenta_id=1, origen=modelos.OrigenEntrada.LIBRE,
                                       texto="Libre", fecha_hora=FECHA))
        sesion.add(modelos.EventoUso(cuenta_id=1, tipo=modelos.TipoEventoUso.COMPLETA_ACTIVIDAD,
                                     id_referencia=1, fecha_hora=FECHA))
    progreso = modelos.ProgresoActividad(cuenta_id=1, actividad_id=15, estado=modelos.EstadoProgreso.COMPLETADA)
    sesion.add(progreso)
    sesion.flush()
    for puntaje in (50, 85, 95):
        sesion.add(modelos.ResultadoCaso(progreso_id=progreso.id, puntaje=puntaje, fecha_hora=FECHA))
    sesion.flush()
    assert sesion.scalar(select(func.count()).select_from(modelos.EntradaDiario)) == 2
    assert sesion.scalar(select(func.count()).select_from(modelos.EventoUso)) == 2
    assert sesion.scalar(select(func.count()).select_from(modelos.ResultadoCaso)) == 3


@pytest.mark.parametrize("modelo,datos", [
    (modelos.CheckIn, {"cuenta_id": 999, "fecha": date(2026, 10, 1), "nivel_seguridad": 3}),
    (modelos.CheckIn, {"cuenta_id": 1, "fecha": date(2026, 10, 1), "nivel_seguridad": 0}),
    (modelos.CheckIn, {"cuenta_id": 1, "fecha": date(2026, 10, 1), "nivel_seguridad": 6}),
    (modelos.EntradaDiario, {"cuenta_id": 1, "origen": modelos.OrigenEntrada.GUIADA,
                           "texto": "Sin pregunta", "fecha_hora": FECHA}),
    (modelos.ReglaDesbloqueo, {"codigo": "R-INVALIDA", "nombre": "Inválida",
                             "tipo_objetivo": modelos.TipoObjetivo.ACTIVIDAD}),
    (modelos.ReglaDesbloqueo, {"codigo": "R-INVALIDA", "nombre": "Inválida",
                             "tipo_objetivo": modelos.TipoObjetivo.CONVERSACIONES, "id_objetivo": 1}),
])
def test_restricciones_rechazan_datos_invalidos(sesion, modelo, datos):
    with pytest.raises(IntegrityError):
        with sesion.begin_nested():
            sesion.add(modelo(**datos))
            sesion.flush()


def test_defaults_falsos(sesion):
    desbloqueo = modelos.Desbloqueo(cuenta_id=1, regla_id=1, fecha_hora=FECHA)
    conversacion = modelos.ConversacionVinculo(vinculo_id=1, conversacion_id=1)
    sesion.add_all([desbloqueo, conversacion])
    sesion.flush()
    assert desbloqueo.visto is False
    assert conversacion.conversado is False
    assert conversacion.conversado_en is None


def test_preparar_base_se_revierte_completa_si_falla(tmp_path, monkeypatch):
    from sqlalchemy.orm import Session
    from app.database import crear_motor_bd

    url = f'sqlite:///{(tmp_path / "carga_atomica.db").as_posix()}'
    original = Session.flush
    llamadas = 0

    def fallar_al_final(sesion, *args, **kwargs):
        nonlocal llamadas
        llamadas += 1
        original(sesion, *args, **kwargs)
        if llamadas == 4:
            raise RuntimeError("Fallo simulado durante la carga")

    monkeypatch.setattr(Session, 'flush', fallar_al_final)
    with pytest.raises(RuntimeError, match="Fallo simulado"):
        preparar_base(url, 'demo', crear_tablas=True)
    motor = crear_motor_bd(url)
    try:
        with Session(motor) as sesion:
            for tabla in Base.metadata.sorted_tables:
                assert sesion.scalar(select(func.count()).select_from(tabla)) == 0
    finally:
        motor.dispose()
