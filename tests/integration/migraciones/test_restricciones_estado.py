from datetime import date, datetime

import pytest
from sqlalchemy import func, inspect, select, text
from sqlalchemy.exc import IntegrityError

from app import models as modelos


FECHA = datetime(2026, 10, 1, 10)
TABLAS_ESTADO = {
    "progreso_actividad", "resultado_caso", "entrada_diario", "check_in",
    "entrevista", "entrevista_autor", "conversacion_vinculo", "evento_uso", "desbloqueo",
    "respuesta_item", "resultado_instrumento", "resultado_dimension", "coincidencia",
    "respuesta_registro", "turno_seguimiento", "evaluacion_respuesta",
}


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
        "carrera_ocupacion",
        "item_registro", "criterio_completitud", "actividad_item_registro",
    }
    assert set(inspector.get_table_names()) == esperadas
    assert len(esperadas) == 44
    assert inspector.get_pk_constraint("entrevista_autor")["constrained_columns"] == [
        "entrevista_id", "cuenta_id",
    ]
    assert any(indice["column_names"] == ["cuenta_id", "tipo"]
               for indice in inspector.get_indexes("evento_uso"))
    with aplicacion.state.motor_bd.connect() as conexion:
        assert conexion.scalar(text("PRAGMA foreign_keys")) == 1
        assert conexion.execute(text("PRAGMA foreign_key_check")).all() == []
        assert conexion.scalar(text("SELECT rol FROM cuenta WHERE codigo='est-ana'")) == "ESTUDIANTE"


@pytest.mark.parametrize("modelo,datos", [
    (modelos.ProgresoActividad, {"cuenta_id": 1, "actividad_id": 1, "estado": modelos.EstadoProgreso.COMPLETADA}),
    (modelos.CheckIn, {"cuenta_id": 1, "fecha": date(2026, 10, 1), "nivel_seguridad": 3}),
    (modelos.Desbloqueo, {"cuenta_id": 1, "regla_id": 1, "fecha_hora": FECHA}),
])
def test_estado_no_admite_duplicados(sesion, modelo, datos):
    sesion.add(modelo(**datos))
    sesion.flush()
    with pytest.raises(IntegrityError):
        with sesion.begin_nested():
            sesion.add(modelo(**datos))
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
