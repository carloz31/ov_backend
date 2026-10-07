from datetime import datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models as modelos
from app import motor
from app.database import Base, crear_motor_bd
from app.evaluadores import EVALUADORES, carreras_de_3_familias
from app.seed import cargar_semilla


FECHA = datetime(2026, 10, 1, 10)


@pytest.fixture
def sesion(tmp_path):
    """Pruebas del núcleo con SQLAlchemy, sin aplicación ni routers."""
    motor_bd = crear_motor_bd(f"sqlite:///{(tmp_path / 'motor.db').as_posix()}")
    Base.metadata.create_all(motor_bd)
    try:
        with Session(motor_bd) as sesion:
            with sesion.begin():
                cargar_semilla(sesion)
            yield sesion
    finally:
        motor_bd.dispose()


def buscar(sesion, modelo, codigo):
    entidad = sesion.scalar(select(modelo).where(modelo.codigo == codigo))
    assert entidad is not None
    return entidad


def registrar(sesion, cuenta, tipo, modelo=None, codigo=None, fecha=FECHA):
    referencia = buscar(sesion, modelo, codigo).id if modelo is not None else None
    return motor.registrar_eventos(sesion, cuenta, [(tipo, referencia)], fecha)


def agregar_eventos(sesion, cuenta, eventos):
    sesion.add_all([
        modelos.EventoUso(cuenta_id=cuenta.id, tipo=tipo, id_referencia=referencia, fecha_hora=fecha)
        for tipo, referencia, fecha in eventos
    ])
    sesion.flush()


def contar_filas(sesion, modelo):
    return sesion.scalar(select(func.count()).select_from(modelo))


@pytest.mark.parametrize("conteo,esperado_total,esperado_filtrado", [
    (modelos.TipoConteo.EVENTOS, 5, 2),
    (modelos.TipoConteo.REFERENCIAS_DISTINTAS, 3, 1),
    (modelos.TipoConteo.DIAS_DISTINTOS, 3, 1),
])
@pytest.mark.parametrize("filtrar", [False, True])
def test_conteos_filtran_cuenta_tipo_y_referencia(sesion, conteo, esperado_total, esperado_filtrado, filtrar):
    ana = buscar(sesion, modelos.Cuenta, "est-ana")
    luis = buscar(sesion, modelos.Cuenta, "est-luis")
    actividades = [buscar(sesion, modelos.Actividad, codigo).id for codigo in ("ACT-01", "ACT-02", "ACT-03")]
    completar = modelos.TipoEventoUso.COMPLETA_ACTIVIDAD
    agregar_eventos(sesion, ana, [
        (completar, actividades[0], FECHA),
        (completar, actividades[0], FECHA + timedelta(hours=1)),
        (completar, actividades[1], FECHA + timedelta(days=1)),
        (completar, actividades[1], FECHA + timedelta(days=1, hours=1)),
        (completar, actividades[2], FECHA + timedelta(days=2)),
        (modelos.TipoEventoUso.SUPERA_CASO, actividades[0], FECHA + timedelta(days=3)),
    ])
    agregar_eventos(sesion, luis, [(completar, actividades[0], FECHA + timedelta(days=4))])
    condicion = modelos.CondicionDesbloqueo(
        tipo_evento=completar, tipo_conteo=conteo, cantidad_minima=1,
        id_referencia=actividades[0] if filtrar else None,
    )
    assert motor.contar_eventos(sesion, ana, condicion) == (esperado_filtrado if filtrar else esperado_total)


@pytest.mark.parametrize("conteo", list(modelos.TipoConteo))
def test_conteo_inicial_es_cero(sesion, conteo):
    ana = buscar(sesion, modelos.Cuenta, "est-ana")
    condicion = modelos.CondicionDesbloqueo(
        tipo_evento=modelos.TipoEventoUso.INGRESO, tipo_conteo=conteo, cantidad_minima=1,
    )
    assert motor.contar_eventos(sesion, ana, condicion) == 0


def test_referencias_nulas_no_son_objetos_distintos(sesion):
    ana = buscar(sesion, modelos.Cuenta, "est-ana")
    agregar_eventos(sesion, ana, [(modelos.TipoEventoUso.INGRESO, None, FECHA)] * 3)
    condicion = modelos.CondicionDesbloqueo(
        tipo_evento=modelos.TipoEventoUso.INGRESO,
        tipo_conteo=modelos.TipoConteo.REFERENCIAS_DISTINTAS, cantidad_minima=1,
    )
    assert motor.contar_eventos(sesion, ana, condicion) == 0


def test_progreso_umbral_y_avance_sin_limitar(sesion):
    ana = buscar(sesion, modelos.Cuenta, "est-ana")
    regla = buscar(sesion, modelos.ReglaDesbloqueo, "R-LOG-PENSADOR")
    for cantidad in range(5):
        resultado = motor.evaluar_regla(sesion, ana, regla)
        assert resultado.cumple is (cantidad >= 3)
        assert resultado.condiciones[0].actual == cantidad
        assert resultado.condiciones[0].requerido == 3
        assert resultado.condiciones[0].cumplida is (cantidad >= 3)
        assert resultado.evaluador_especial is None
        agregar_eventos(sesion, ana, [(modelos.TipoEventoUso.RESPUESTA_REFLEXIVA, None, FECHA)])


def test_regla_compuesta_exige_todas_las_condiciones(sesion):
    ana = buscar(sesion, modelos.Cuenta, "est-ana")
    regla = buscar(sesion, modelos.ReglaDesbloqueo, "R-ACT-17")
    assert not motor.evaluar_regla(sesion, ana, regla).cumple
    registrar(sesion, ana, modelos.TipoEventoUso.COMPLETA_ACTIVIDAD, modelos.Actividad, "ACT-13")
    resultado = motor.evaluar_regla(sesion, ana, regla)
    assert resultado.cumple is False
    assert [condicion.cumplida for condicion in resultado.condiciones] == [True, False]
    assert [condicion.referencia for condicion in resultado.condiciones] == ["ACT-13", "C1"]
    assert not motor.objetivo_disponible(sesion, ana, modelos.TipoObjetivo.ACTIVIDAD, regla.id_objetivo)
    nuevos = registrar(sesion, ana, modelos.TipoEventoUso.COMPLETA_BLOQUE, modelos.Bloque, "C1")
    assert "R-ACT-17" in {nuevo.regla for nuevo in nuevos}
    assert motor.evaluar_regla(sesion, ana, regla).cumple
    assert motor.objetivo_disponible(sesion, ana, modelos.TipoObjetivo.ACTIVIDAD, regla.id_objetivo)


def test_eventos_de_otras_cuentas_no_completan_regla_compuesta(sesion):
    ana = buscar(sesion, modelos.Cuenta, "est-ana")
    luis = buscar(sesion, modelos.Cuenta, "est-luis")
    regla = buscar(sesion, modelos.ReglaDesbloqueo, "R-ACT-17")
    registrar(sesion, ana, modelos.TipoEventoUso.COMPLETA_ACTIVIDAD, modelos.Actividad, "ACT-13")
    registrar(sesion, luis, modelos.TipoEventoUso.COMPLETA_BLOQUE, modelos.Bloque, "C1")
    assert motor.evaluar_regla(sesion, ana, regla).cumple is False
    assert motor.evaluar_regla(sesion, luis, regla).cumple is False


def test_evaluador_de_carreras_cuenta_familias_no_visitas_ni_carreras(sesion):
    ana = buscar(sesion, modelos.Cuenta, "est-ana")
    luis = buscar(sesion, modelos.Cuenta, "est-luis")
    regla = buscar(sesion, modelos.ReglaDesbloqueo, "R-INS-EXPLORADOR")
    inicial = motor.evaluar_regla(sesion, ana, regla)
    assert inicial.condiciones[0].actual == 0
    assert inicial.evaluador_especial.cumplido is False
    for carrera in ("CAR-ENF", "CAR-ENF", "CAR-MED", "CAR-CIV"):
        nuevos = registrar(sesion, ana, modelos.TipoEventoUso.VISTA_CARRERA, modelos.Carrera, carrera)
        assert "R-INS-EXPLORADOR" not in {nuevo.regla for nuevo in nuevos}
    registrar(sesion, luis, modelos.TipoEventoUso.VISTA_CARRERA, modelos.Carrera, "CAR-DIS")
    diseno = buscar(sesion, modelos.Carrera, "CAR-DIS")
    agregar_eventos(sesion, ana, [(modelos.TipoEventoUso.COMPLETA_ACTIVIDAD, diseno.id, FECHA),
                                 (modelos.TipoEventoUso.VISTA_CARRERA, None, FECHA),
                                 (modelos.TipoEventoUso.VISTA_CARRERA, 99999, FECHA)])
    assert carreras_de_3_familias(sesion, ana) is False
    resultado = motor.evaluar_regla(sesion, ana, regla)
    assert resultado.condiciones[0].cumplida is True
    assert resultado.evaluador_especial.nombre == "carreras_de_3_familias"
    assert resultado.evaluador_especial.cumplido is False
    assert resultado.cumple is False
    nuevos = registrar(sesion, ana, modelos.TipoEventoUso.VISTA_CARRERA, modelos.Carrera, "CAR-DIS")
    assert [nuevo.regla for nuevo in nuevos] == ["R-INS-EXPLORADOR"]
    assert nuevos[0].evaluador_especial.cumplido is True
    assert carreras_de_3_familias(sesion, ana) is True
    assert motor.evaluar_regla(sesion, ana, regla).cumple is True


def test_evaluador_verdadero_no_reemplaza_condiciones(sesion, monkeypatch):
    ana = buscar(sesion, modelos.Cuenta, "est-ana")
    monkeypatch.setitem(EVALUADORES, "siempre_verdadero", lambda sesion, cuenta: True)
    regla = modelos.ReglaDesbloqueo(
        codigo="PRUEBA", evaluador_especial="siempre_verdadero",
        condiciones=[modelos.CondicionDesbloqueo(tipo_evento=modelos.TipoEventoUso.INGRESO,
                     tipo_conteo=modelos.TipoConteo.EVENTOS, cantidad_minima=1)],
    )
    resultado = motor.evaluar_regla(sesion, ana, regla)
    assert resultado.cumple is False
    assert resultado.condiciones[0].cumplida is False
    assert resultado.evaluador_especial.cumplido is True


def test_primer_desbloqueo_explicado_sin_ids_internos(sesion):
    ana = buscar(sesion, modelos.Cuenta, "est-ana")
    nuevos = registrar(sesion, ana, modelos.TipoEventoUso.COMPLETA_ACTIVIDAD, modelos.Actividad, "ACT-01")
    assert len(nuevos) == 1
    datos = nuevos[0].model_dump(mode="json", exclude={"evaluador_especial"})
    assert datos == {
        "regla": "R-ACT-02", "tipo_objetivo": "ACTIVIDAD",
        "objetivo": {"codigo": "ACT-02", "nombre": "Mis expectativas"},
        "condiciones": [{"tipo_evento": "COMPLETA_ACTIVIDAD", "referencia": "ACT-01",
                         "tipo_conteo": "EVENTOS", "actual": 1, "requerido": 1, "cumplida": True}],
    }
    desbloqueo = sesion.scalar(select(modelos.Desbloqueo))
    assert desbloqueo.cuenta_id == ana.id
    assert desbloqueo.fecha_hora == FECHA and desbloqueo.visto is False
    assert contar_filas(sesion, modelos.EventoUso) == 1


def test_varios_eventos_se_evaluan_juntos_y_sin_cascadas(sesion):
    ana = buscar(sesion, modelos.Cuenta, "est-ana")
    actividad = buscar(sesion, modelos.Actividad, "ACT-03")
    bloque = buscar(sesion, modelos.Bloque, "B0")
    nuevos = motor.registrar_eventos(sesion, ana, [
        (modelos.TipoEventoUso.COMPLETA_ACTIVIDAD, actividad.id),
        (modelos.TipoEventoUso.COMPLETA_BLOQUE, bloque.id),
    ], FECHA)
    assert {nuevo.regla for nuevo in nuevos} == {"R-ACT-04", "R-INS-PRIMER-PASO", "R-NIV-2"}
    assert contar_filas(sesion, modelos.EventoUso) == 2
    assert contar_filas(sesion, modelos.Desbloqueo) == 3
    assert motor.nivel_actual(sesion, ana).numero == 2
    assert {nuevo.objetivo.codigo for nuevo in nuevos} == {"ACT-04", "INS-PRIMER-PASO", "N2"}


def test_regla_relacionada_con_dos_eventos_se_evaluan_una_sola_vez(sesion, monkeypatch):
    ana = buscar(sesion, modelos.Cuenta, "est-ana")
    actividad = buscar(sesion, modelos.Actividad, "ACT-13")
    bloque = buscar(sesion, modelos.Bloque, "C1")
    original = motor.evaluar_regla
    evaluadas = []

    def registrar_evaluacion(sesion, cuenta, regla):
        evaluadas.append(regla.codigo)
        return original(sesion, cuenta, regla)

    monkeypatch.setattr(motor, "evaluar_regla", registrar_evaluacion)
    nuevos = motor.registrar_eventos(sesion, ana, [
        (modelos.TipoEventoUso.COMPLETA_ACTIVIDAD, actividad.id),
        (modelos.TipoEventoUso.COMPLETA_BLOQUE, bloque.id),
    ], FECHA)
    assert evaluadas.count("R-ACT-17") == 1
    assert [nuevo.regla for nuevo in nuevos].count("R-ACT-17") == 1
    assert all(condicion.actual == 1 for nuevo in nuevos if nuevo.regla == "R-ACT-17"
               for condicion in nuevo.condiciones)


def test_repeticiones_no_duplican_ni_revocan_desbloqueos(sesion, monkeypatch):
    ana = buscar(sesion, modelos.Cuenta, "est-ana")
    registrar(sesion, ana, modelos.TipoEventoUso.COMPLETA_ACTIVIDAD, modelos.Actividad, "ACT-01")
    desbloqueo = sesion.scalar(select(modelos.Desbloqueo))
    desbloqueo.visto = True
    original = motor.evaluar_regla
    evaluadas = []

    def registrar_evaluacion(sesion, cuenta, regla):
        evaluadas.append(regla.codigo)
        return original(sesion, cuenta, regla)

    monkeypatch.setattr(motor, "evaluar_regla", registrar_evaluacion)
    for _ in range(5):
        assert registrar(sesion, ana, modelos.TipoEventoUso.COMPLETA_ACTIVIDAD,
                         modelos.Actividad, "ACT-01", fecha=FECHA - timedelta(days=1)) == []
    assert "R-ACT-02" not in evaluadas
    assert contar_filas(sesion, modelos.Desbloqueo) == 1
    assert contar_filas(sesion, modelos.EventoUso) == 6
    assert desbloqueo.visto is True and desbloqueo.fecha_hora == FECHA
    regla = buscar(sesion, modelos.ReglaDesbloqueo, "R-LOG-INCANSABLE")
    assert motor.evaluar_regla(sesion, ana, regla).condiciones[0].actual == 1


def test_solo_se_evaluan_tipos_relacionados_y_lista_vacia_no_hace_nada(sesion, monkeypatch):
    ana = buscar(sesion, modelos.Cuenta, "est-ana")
    actividad = buscar(sesion, modelos.Actividad, "ACT-01")
    agregar_eventos(sesion, ana, [(modelos.TipoEventoUso.COMPLETA_ACTIVIDAD, actividad.id, FECHA)])

    def evaluacion_inesperada(*args):
        pytest.fail("Un tipo sin reglas o una lista vacía no debe evaluar reglas")

    monkeypatch.setattr(motor, "evaluar_regla", evaluacion_inesperada)
    assert motor.registrar_eventos(sesion, ana, [], FECHA) == []
    assert contar_filas(sesion, modelos.EventoUso) == 1
    assert registrar(sesion, ana, modelos.TipoEventoUso.INGRESO) == []
    assert contar_filas(sesion, modelos.EventoUso) == 2
    assert contar_filas(sesion, modelos.Desbloqueo) == 0


@pytest.mark.parametrize("cuenta,codigo,regla", [
    ("est-ana", "ACT-13", "R-FAM-ESTUDIANTE"),
    ("apo-rosa", "ACT-P02", "R-FAM-APODERADO"),
])
def test_reglas_alternativas_mismo_objetivo_no_exigen_ambas(sesion, cuenta, codigo, regla):
    cuenta = buscar(sesion, modelos.Cuenta, cuenta)
    registrar(sesion, cuenta, modelos.TipoEventoUso.COMPLETA_ACTIVIDAD, modelos.Actividad, codigo)
    assert not motor.objetivo_disponible(sesion, cuenta, modelos.TipoObjetivo.CONVERSACIONES, None)
    nuevos = registrar(sesion, cuenta, modelos.TipoEventoUso.ESCRIBE_CARTA, modelos.VinculoFamiliar, "VIN-ANA")
    assert [nuevo.regla for nuevo in nuevos] == [regla]
    assert nuevos[0].objetivo.codigo == "-"
    assert motor.objetivo_disponible(sesion, cuenta, modelos.TipoObjetivo.CONVERSACIONES, None)


def test_evento_compartido_filtro_audiencia_y_aislamiento(sesion):
    ana = buscar(sesion, modelos.Cuenta, "est-ana")
    rosa = buscar(sesion, modelos.Cuenta, "apo-rosa")
    nuevos_rosa = registrar(sesion, rosa, modelos.TipoEventoUso.COMPLETA_CONVERSACION,
                            modelos.Conversacion, "CONV-01")
    assert nuevos_rosa == []
    pregunta = buscar(sesion, modelos.PreguntaDiario, "PD-CONV-01")
    assert not motor.objetivo_disponible(sesion, ana, modelos.TipoObjetivo.PREGUNTA_DIARIO, pregunta.id)
    nuevos_ana = registrar(sesion, ana, modelos.TipoEventoUso.COMPLETA_CONVERSACION,
                           modelos.Conversacion, "CONV-01")
    assert [nuevo.regla for nuevo in nuevos_ana] == ["R-PD-CONV-01"]
    assert motor.objetivo_disponible(sesion, ana, modelos.TipoObjetivo.PREGUNTA_DIARIO, pregunta.id)
    assert not motor.objetivo_disponible(sesion, rosa, modelos.TipoObjetivo.PREGUNTA_DIARIO, pregunta.id)
    eventos = sesion.scalars(select(modelos.EventoUso)).all()
    assert {evento.cuenta_id for evento in eventos} == {ana.id, rosa.id}
    assert len(eventos) == 2


@pytest.mark.parametrize("cuenta,tipo,modelo,codigo,esperado", [
    ("est-ana", "BLOQUE", modelos.Bloque, "B0", True),
    ("est-ana", "BLOQUE", modelos.Bloque, "P1", False),
    ("est-ana", "BLOQUE", modelos.Bloque, "C1", False),
    ("est-ana", "ACTIVIDAD", modelos.Actividad, "ACT-01", True),
    ("est-ana", "ACTIVIDAD", modelos.Actividad, "ACT-02", False),
    ("est-ana", "ACTIVIDAD", modelos.Actividad, "ACT-P01", False),
    ("est-ana", "ACTIVIDAD", modelos.Actividad, "HEL-01", False),
    ("est-ana", "FICHA", modelos.Ficha, "FIC-PROFESIONES", False),
    ("est-ana", "TESTIMONIO", modelos.Testimonio, "TES-HOSPITAL", False),
    ("est-ana", "PREGUNTA_DIARIO", modelos.PreguntaDiario, "PD-HISTORIA", False),
    ("est-ana", "INSIGNIA", modelos.Insignia, "INS-CONOZCO-MI-ROL", False),
    ("apo-rosa", "BLOQUE", modelos.Bloque, "P1", True),
    ("apo-rosa", "BLOQUE", modelos.Bloque, "B0", False),
    ("apo-rosa", "ACTIVIDAD", modelos.Actividad, "ACT-P01", True),
    ("apo-rosa", "ACTIVIDAD", modelos.Actividad, "ACT-P02", False),
    ("apo-rosa", "ACTIVIDAD", modelos.Actividad, "ACT-01", False),
])
def test_disponibilidad_inicial(sesion, cuenta, tipo, modelo, codigo, esperado):
    cuenta = buscar(sesion, modelos.Cuenta, cuenta)
    objetivo = buscar(sesion, modelo, codigo)
    assert motor.objetivo_disponible(sesion, cuenta, modelos.TipoObjetivo(tipo), objetivo.id) is esperado


@pytest.mark.parametrize("tipo,modelo,codigo,regla", [
    ("BLOQUE", modelos.Bloque, "C1", "R-CIUDAD-C1"),
    ("ACTIVIDAD", modelos.Actividad, "ACT-02", "R-ACT-02"),
    ("FICHA", modelos.Ficha, "FIC-PROFESIONES", "R-FIC-PROFESIONES"),
    ("TESTIMONIO", modelos.Testimonio, "TES-HOSPITAL", "R-TES-HOSPITAL"),
    ("PREGUNTA_DIARIO", modelos.PreguntaDiario, "PD-HISTORIA", "R-PD-HISTORIA"),
    ("INSIGNIA", modelos.Insignia, "INS-PRIMER-PASO", "R-INS-PRIMER-PASO"),
])
def test_desbloqueo_no_elimina_filtro_de_audiencia(sesion, tipo, modelo, codigo, regla):
    rosa = buscar(sesion, modelos.Cuenta, "apo-rosa")
    objetivo = buscar(sesion, modelo, codigo)
    regla = buscar(sesion, modelos.ReglaDesbloqueo, regla)
    sesion.add(modelos.Desbloqueo(cuenta_id=rosa.id, regla_id=regla.id, fecha_hora=FECHA))
    sesion.flush()
    assert not motor.objetivo_disponible(sesion, rosa, modelos.TipoObjetivo(tipo), objetivo.id)


def test_ciudad_hereda_bloque_y_conserva_reglas_propias(sesion):
    ana = buscar(sesion, modelos.Cuenta, "est-ana")
    registrar(sesion, ana, modelos.TipoEventoUso.COMPLETA_ACTIVIDAD, modelos.Actividad, "ACT-13")
    for codigo in ("HEL-01", "HEL-03", "CASO-01", "COMP-13"):
        actividad = buscar(sesion, modelos.Actividad, codigo)
        assert motor.objetivo_disponible(sesion, ana, modelos.TipoObjetivo.ACTIVIDAD, actividad.id)
    for codigo in ("HEL-02", "CASO-02", "INV-01"):
        actividad = buscar(sesion, modelos.Actividad, codigo)
        assert not motor.objetivo_disponible(sesion, ana, modelos.TipoObjetivo.ACTIVIDAD, actividad.id)


def test_regla_de_actividad_puede_cumplirse_antes_que_bloque_contenedor(sesion):
    ana = buscar(sesion, modelos.Cuenta, "est-ana")
    helena = buscar(sesion, modelos.Actividad, "HEL-02")
    nuevos = registrar(sesion, ana, modelos.TipoEventoUso.COMPLETA_ACTIVIDAD, modelos.Actividad, "HEL-01")
    assert "R-HEL-02" in {nuevo.regla for nuevo in nuevos}
    assert not motor.objetivo_disponible(sesion, ana, modelos.TipoObjetivo.ACTIVIDAD, helena.id)
    registrar(sesion, ana, modelos.TipoEventoUso.COMPLETA_ACTIVIDAD, modelos.Actividad, "ACT-13")
    assert motor.objetivo_disponible(sesion, ana, modelos.TipoObjetivo.ACTIVIDAD, helena.id)


def test_condiciones_cumplidas_sin_desbloqueo_no_dan_disponibilidad(sesion):
    ana = buscar(sesion, modelos.Cuenta, "est-ana")
    primera = buscar(sesion, modelos.Actividad, "ACT-01")
    segunda = buscar(sesion, modelos.Actividad, "ACT-02")
    agregar_eventos(sesion, ana, [(modelos.TipoEventoUso.COMPLETA_ACTIVIDAD, primera.id, FECHA)])
    regla = buscar(sesion, modelos.ReglaDesbloqueo, "R-ACT-02")
    assert motor.evaluar_regla(sesion, ana, regla).cumple
    assert not motor.objetivo_disponible(sesion, ana, modelos.TipoObjetivo.ACTIVIDAD, segunda.id)


@pytest.mark.parametrize("tipo", list(modelos.TipoObjetivo))
def test_objetivos_inexistentes_no_estan_disponibles(sesion, tipo):
    ana = buscar(sesion, modelos.Cuenta, "est-ana")
    assert not motor.objetivo_disponible(sesion, ana, tipo, 99999)
    if tipo != modelos.TipoObjetivo.CONVERSACIONES:
        assert not motor.objetivo_disponible(sesion, ana, tipo, None)


def test_niveles_requieren_condiciones_previas_y_nunca_bajan(sesion):
    ana = buscar(sesion, modelos.Cuenta, "est-ana")
    rosa = buscar(sesion, modelos.Cuenta, "apo-rosa")
    assert motor.nivel_actual(sesion, ana).numero == 1
    assert motor.nivel_actual(sesion, rosa) is None
    registrar(sesion, ana, modelos.TipoEventoUso.COMPLETA_ACTIVIDAD, modelos.Actividad, "ACT-13")
    assert motor.nivel_actual(sesion, ana).numero == 1
    registrar(sesion, ana, modelos.TipoEventoUso.COMPLETA_BLOQUE, modelos.Bloque, "B0")
    assert motor.nivel_actual(sesion, ana).numero == 3
    registrar(sesion, ana, modelos.TipoEventoUso.SUPERA_CASO, modelos.Actividad, "CASO-01")
    assert motor.nivel_actual(sesion, ana).numero == 3
    registrar(sesion, ana, modelos.TipoEventoUso.COMPLETA_BLOQUE, modelos.Bloque, "C1")
    assert motor.nivel_actual(sesion, ana).numero == 4
    registrar(sesion, ana, modelos.TipoEventoUso.COMPLETA_ACTIVIDAD, modelos.Actividad, "ACT-18")
    assert motor.nivel_actual(sesion, ana).numero == 5
    registrar(sesion, ana, modelos.TipoEventoUso.INGRESO, fecha=FECHA - timedelta(days=1))
    assert motor.nivel_actual(sesion, ana).numero == 5
    niveles = sesion.scalars(select(modelos.Nivel)).all()
    assert all(motor.objetivo_disponible(sesion, ana, modelos.TipoObjetivo.NIVEL, nivel.id) for nivel in niveles)
    assert all(not motor.objetivo_disponible(sesion, rosa, modelos.TipoObjetivo.NIVEL, nivel.id) for nivel in niveles)


def test_coautores_se_evaluan_independientemente(sesion):
    ana = buscar(sesion, modelos.Cuenta, "est-ana")
    luis = buscar(sesion, modelos.Cuenta, "est-luis")
    entrevista = modelos.Entrevista(codigo="ENT-PRUEBA", resumen="Una entrevista", fecha_hora=FECHA)
    sesion.add(entrevista)
    sesion.flush()
    eventos = [(modelos.TipoEventoUso.PUBLICA_ENTREVISTA, entrevista.id)]
    assert [nuevo.regla for nuevo in motor.registrar_eventos(sesion, ana, eventos, FECHA)] == ["R-INS-INVESTIGADOR"]
    assert [nuevo.regla for nuevo in motor.registrar_eventos(sesion, luis, eventos, FECHA)] == ["R-INS-INVESTIGADOR"]
    assert contar_filas(sesion, modelos.Desbloqueo) == 2
    assert contar_filas(sesion, modelos.EventoUso) == 2


def test_reversion_de_accion_incluye_estado_eventos_y_desbloqueos(sesion):
    with pytest.raises(RuntimeError, match="Fallo de acción"):
        with sesion.begin():
            ana = buscar(sesion, modelos.Cuenta, "est-ana")
            actividad = buscar(sesion, modelos.Actividad, "ACT-01")
            sesion.add(modelos.ProgresoActividad(cuenta_id=ana.id, actividad_id=actividad.id,
                                                 estado=modelos.EstadoProgreso.COMPLETADA))
            nuevos = motor.registrar_eventos(sesion, ana, [
                (modelos.TipoEventoUso.COMPLETA_ACTIVIDAD, actividad.id),
            ], FECHA)
            assert [nuevo.regla for nuevo in nuevos] == ["R-ACT-02"]
            assert contar_filas(sesion, modelos.Desbloqueo) == 1
            raise RuntimeError("Fallo de acción")
    assert contar_filas(sesion, modelos.ProgresoActividad) == 0
    assert contar_filas(sesion, modelos.EventoUso) == 0
    assert contar_filas(sesion, modelos.Desbloqueo) == 0
    assert contar_filas(sesion, modelos.ReglaDesbloqueo) == 47


def test_evaluador_desconocido_revierte_lote_completo(sesion):
    ficha = buscar(sesion, modelos.Ficha, "FIC-PROFESIONES")
    sesion.add(modelos.ReglaDesbloqueo(
        codigo="Z-EVALUADOR-INVALIDO", nombre="Solo para probar el fallo",
        tipo_objetivo=modelos.TipoObjetivo.FICHA, id_objetivo=ficha.id,
        evaluador_especial="desconocido",
        condiciones=[modelos.CondicionDesbloqueo(tipo_evento=modelos.TipoEventoUso.COMPLETA_ACTIVIDAD,
                     tipo_conteo=modelos.TipoConteo.EVENTOS, cantidad_minima=1)],
    ))
    sesion.commit()
    with pytest.raises(ValueError, match="Evaluador especial desconocido: desconocido"):
        with sesion.begin():
            ana = buscar(sesion, modelos.Cuenta, "est-ana")
            registrar(sesion, ana, modelos.TipoEventoUso.COMPLETA_ACTIVIDAD, modelos.Actividad, "ACT-01")
    assert contar_filas(sesion, modelos.EventoUso) == 0
    assert contar_filas(sesion, modelos.Desbloqueo) == 0


def test_regla_sin_condiciones_es_configuracion_invalida(sesion):
    ana = buscar(sesion, modelos.Cuenta, "est-ana")
    regla = modelos.ReglaDesbloqueo(codigo="VACIA", condiciones=[])
    with pytest.raises(ValueError, match="Regla sin condiciones: VACIA"):
        motor.evaluar_regla(sesion, ana, regla)
