"""I1–I14 mediante acciones y consultas públicas; invariantes y atomicidad."""

from collections import Counter
from datetime import datetime

import pytest
from sqlalchemy import func, select

from app import models as modelos
from app import acciones
from app import resultados_instrumentos
from app.calculo_instrumentos import calcular_codigo_interes, clasificar_ajuste
from app.semilla_instrumentos import RUTA_OCUPACIONES


FECHA = "2026-10-01T10:00:00"
CADENA_A = "511222115515411122551525542552114321231141335215514152553521"
CADENA_B = "333322223322343333233333443333333333444433333433444433334433"
REQUIERE_OCUPACIONES = pytest.mark.skipif(not RUTA_OCUPACIONES.is_file(), reason=f"Falta el catálogo O*NET: {RUTA_OCUPACIONES}")


@pytest.fixture(autouse=True)
def reiniciar_instrumentos(cliente):
    assert cliente.post("/demo/reiniciar").status_code == 200


def guardar(cliente, actividad, respuestas, cuenta="est-ana", fecha=FECHA):
    respuesta = cliente.post("/acciones/responder-items", json={
        "cuenta": cuenta, "actividad": actividad, "respuestas": respuestas, "fecha_hora": fecha,
    })
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def completar(cliente, actividad, cuenta="est-ana", fecha=FECHA):
    respuesta = cliente.post("/acciones/completar-actividad", json={
        "cuenta": cuenta, "actividad": actividad, "fecha_hora": fecha,
    })
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def reiniciar(cliente, instrumento="TEST-RIASEC", cuenta="est-ana", codigo=None, fecha="2026-10-02T10:00:00-05:00"):
    entrada = {"cuenta": cuenta, "instrumento": instrumento, "fecha_hora": fecha}
    if codigo is not None:
        entrada["aplicacion"] = codigo
    respuesta = cliente.post("/acciones/reiniciar-instrumento", json=entrada)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def verificar_invariantes_persistidos(aplicacion):
    """Los anulados conservan historia; solo los vigentes exigen progresos completos."""
    with aplicacion.state.fabrica_sesiones() as sesion:
        vigentes = sesion.scalars(select(modelos.ResultadoInstrumento).where(modelos.ResultadoInstrumento.anulado_en.is_(None))).all()
        assert all(cantidad == 1 for cantidad in Counter((r.cuenta_id, r.aplicacion_id) for r in vigentes).values())
        for resultado in vigentes:
            actividades = set(sesion.scalars(select(modelos.AplicacionActividad.actividad_id).where(
                modelos.AplicacionActividad.aplicacion_id == resultado.aplicacion_id)))
            completadas = set(sesion.scalars(select(modelos.ProgresoActividad.actividad_id).where(
                modelos.ProgresoActividad.cuenta_id == resultado.cuenta_id,
                modelos.ProgresoActividad.estado == modelos.EstadoProgreso.COMPLETADA,
                modelos.ProgresoActividad.actividad_id.in_(actividades))))
            assert actividades == completadas
        for aplicacion_instrumento in sesion.scalars(select(modelos.Aplicacion)):
            esperados = set(sesion.scalars(select(modelos.ItemInstrumento.id).where(
                modelos.ItemInstrumento.instrumento_id == aplicacion_instrumento.instrumento_id)))
            presentados = list(sesion.scalars(select(modelos.ActividadItem.item_id).join(
                modelos.AplicacionActividad, modelos.AplicacionActividad.actividad_id == modelos.ActividadItem.actividad_id,
            ).where(modelos.AplicacionActividad.aplicacion_id == aplicacion_instrumento.id)))
            assert Counter(presentados) == Counter({item: 1 for item in esperados})
        for coincidencia in sesion.scalars(select(modelos.Coincidencia)):
            assert coincidencia.correlacion >= 0
            assert coincidencia.ajuste == clasificar_ajuste(coincidencia.correlacion)


def estado_actividades(cliente, cuenta="est-ana"):
    return {a["codigo"]: a["estado"] for b in cliente.get(f"/cuentas/{cuenta}/estado").json()["bloques"]
            for a in b["actividades"]}


def avance_publico(cliente, instrumento="TEST-RIASEC", cuenta="est-ana"):
    respuesta = cliente.get(f"/cuentas/{cuenta}/instrumentos")
    assert respuesta.status_code == 200, respuesta.text
    return next(i["aplicaciones"] for i in respuesta.json() if i["instrumento"] == instrumento)


def resultado_publico(cliente, instrumento="TEST-RIASEC", cuenta="est-ana"):
    respuesta = cliente.get(f"/cuentas/{cuenta}/instrumentos/{instrumento}/resultado")
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def contar(aplicacion, modelo):
    with aplicacion.state.fabrica_sesiones() as sesion:
        return sesion.scalar(select(func.count()).select_from(modelo))


def resultados(aplicacion, codigo="APL-RIASEC", cuenta="est-ana"):
    with aplicacion.state.fabrica_sesiones() as sesion:
        return sesion.scalars(select(modelos.ResultadoInstrumento).join(modelos.Cuenta).join(modelos.Aplicacion).where(
            modelos.Cuenta.codigo == cuenta, modelos.Aplicacion.codigo == codigo,
        ).order_by(modelos.ResultadoInstrumento.id)).all()


def dimensiones(aplicacion, resultado):
    with aplicacion.state.fabrica_sesiones() as sesion:
        return sesion.execute(select(modelos.Dimension.codigo, modelos.ResultadoDimension.puntaje,
                                     modelos.ResultadoDimension.puntaje_maximo, modelos.ResultadoDimension.porcentaje).join(
            modelos.ResultadoDimension, modelos.ResultadoDimension.dimension_id == modelos.Dimension.id,
        ).where(modelos.ResultadoDimension.resultado_id == resultado.id).order_by(modelos.Dimension.orden)).all()


def coincidencias(aplicacion, resultado):
    with aplicacion.state.fabrica_sesiones() as sesion:
        return sesion.execute(select(modelos.Coincidencia.posicion, modelos.Ocupacion.codigo_onet,
                                     modelos.Ocupacion.titulo, modelos.Coincidencia.correlacion, modelos.Coincidencia.ajuste).join(
            modelos.Ocupacion, modelos.Ocupacion.id == modelos.Coincidencia.ocupacion_id,
        ).where(modelos.Coincidencia.resultado_id == resultado.id).order_by(modelos.Coincidencia.posicion)).all()


def respuestas_persistidas(aplicacion, actividad="LAB-RIA1", cuenta="est-ana"):
    with aplicacion.state.fabrica_sesiones() as sesion:
        return sesion.execute(select(modelos.RespuestaItem.id, modelos.ItemInstrumento.codigo,
                                     modelos.OpcionEscala.orden, modelos.OpcionEscala.puntaje,
                                     modelos.RespuestaItem.creada_en, modelos.RespuestaItem.actualizada_en).select_from(
            modelos.RespuestaItem,
        ).join(modelos.ProgresoActividad).join(modelos.Cuenta).join(modelos.Actividad).join(
            modelos.ItemInstrumento, modelos.ItemInstrumento.id == modelos.RespuestaItem.item_id,
        ).join(modelos.OpcionEscala, modelos.OpcionEscala.id == modelos.RespuestaItem.opcion_id).where(
            modelos.Cuenta.codigo == cuenta, modelos.Actividad.codigo == actividad,
        ).order_by(modelos.ItemInstrumento.numero)).all()


def aplicar_cadena(cliente, cadena, cuenta="est-ana", hasta=4, fecha=FECHA):
    """Reparte los 60 dígitos entre las cuatro actividades y usa solo acciones HTTP."""
    assert len(cadena) == 60
    for bloque in range(hasta):
        actividad = f"LAB-RIA{bloque + 1}"
        guardado = guardar(cliente, actividad, [
            {"item": f"RIASEC-{numero:02}", "opcion": int(cadena[numero - 1])}
            for numero in range(bloque * 15 + 1, bloque * 15 + 16)
        ], cuenta, fecha)
        assert guardado["progreso"] == {"estado": "EN_CURSO", "respondidos": 15, "total": 15}
        yield completar(cliente, actividad, cuenta, fecha)


def test_i1_estado_inicial_del_laboratorio(cliente, aplicacion):
    instrumentos = cliente.get("/cuentas/est-ana/instrumentos").json()
    assert [i["instrumento"] for i in instrumentos] == ["TEST-AUTO", "TEST-HAB", "TEST-INT", "TEST-RIASEC"]
    assert [(a["aplicacion"], a["actividades"]["total"], a["items"]["total"])
            for i in instrumentos for a in i["aplicaciones"]] == [
        ("APL-AUTO-ENT", 1, 10), ("APL-AUTO-SAL", 1, 10), ("APL-HAB", 1, 24), ("APL-INT", 2, 43), ("APL-RIASEC", 4, 60),
    ]
    assert all(a["estado"] == "NO_INICIADO" and a["actividades"]["completadas"] == 0
               and a["items"]["respondidos"] == 0 and not a["hay_resultado_vigente"]
               for i in instrumentos for a in i["aplicaciones"])
    assert {codigo: estado for codigo, estado in estado_actividades(cliente).items() if codigo.startswith("LAB-")} == {
        "LAB-AUT-E": "DISPONIBLE", "LAB-AUT-S": "BLOQUEADA", "LAB-HAB": "DISPONIBLE",
        "LAB-INT1": "DISPONIBLE", "LAB-INT2": "BLOQUEADA", "LAB-RIA1": "DISPONIBLE",
        "LAB-RIA2": "BLOQUEADA", "LAB-RIA3": "BLOQUEADA", "LAB-RIA4": "BLOQUEADA",
    }
    assert not any(codigo.startswith("LAB-") for codigo in estado_actividades(cliente, "apo-rosa"))
    for modelo in (modelos.ProgresoActividad, modelos.RespuestaItem, modelos.ResultadoInstrumento, modelos.EventoUso):
        assert contar(aplicacion, modelo) == 0


def test_i2_respuestas_parciales_impiden_completar_sin_eventos(cliente, aplicacion):
    guardado = guardar(cliente, "LAB-RIA1", [{"item": f"RIASEC-{n:02}", "opcion": 3} for n in range(1, 11)])
    assert guardado["cuenta"] == "est-ana"
    assert guardado["actividad"] == "LAB-RIA1"
    assert guardado["progreso"] == {"estado": "EN_CURSO", "respondidos": 10, "total": 15}
    respuesta = cliente.post("/acciones/completar-actividad", json={"cuenta": "est-ana", "actividad": "LAB-RIA1"})
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"]["items_faltantes"] == [f"RIASEC-{n:02}" for n in range(11, 16)]
    assert estado_actividades(cliente)["LAB-RIA1"] == "EN_CURSO"
    assert contar(aplicacion, modelos.RespuestaItem) == 10
    assert contar(aplicacion, modelos.ResultadoInstrumento) == 0
    assert contar(aplicacion, modelos.EventoUso) == 0
    assert contar(aplicacion, modelos.Desbloqueo) == 0
    avance, = avance_publico(cliente)
    assert avance == {"aplicacion": "APL-RIASEC", "estado": "EN_PROGRESO",
        "actividades": {"completadas": 0, "total": 4, "faltantes": [f"LAB-RIA{n}" for n in range(1, 5)]},
        "items": {"respondidos": 10, "total": 60}, "hay_resultado_vigente": False}
    respuesta = cliente.get("/cuentas/est-ana/instrumentos/TEST-RIASEC/resultado")
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"]["avance"] == avance
    actuales = cliente.get("/cuentas/est-ana/actividades/LAB-RIA1/respuestas").json()
    assert [r["item"] for r in actuales["respuestas"]] == [f"RIASEC-{n:02}" for n in range(1, 11)]


def test_i3_validacion_de_item_opcion_y_disponibilidad_y_reemplazo(cliente, aplicacion):
    base = {"cuenta": "est-ana", "actividad": "LAB-RIA1", "respuestas": [{"item": "RIASEC-20", "opcion": 1}]}
    assert cliente.post("/acciones/responder-items", json=base).status_code == 409
    assert cliente.post("/acciones/responder-items", json={**base, "respuestas": [{"item": "RIASEC-01", "opcion": 6}]}).status_code == 422
    bloqueada = cliente.post("/acciones/responder-items", json={**base, "actividad": "LAB-RIA2"})
    assert bloqueada.status_code == 409
    assert bloqueada.json()["detail"]["progreso"]["reglas"][0]["regla"] == "R-LAB-RIA2"
    assert bloqueada.json()["detail"]["progreso"]["reglas"][0]["condiciones"][0]["actual"] == 0
    assert contar(aplicacion, modelos.ProgresoActividad) == 0
    guardar(cliente, "LAB-RIA1", [{"item": "RIASEC-01", "opcion": 1}])
    anterior = respuestas_persistidas(aplicacion)[0]
    cambio = guardar(cliente, "LAB-RIA1", [{"item": "RIASEC-01", "opcion": 5}], fecha="2026-10-02T12:00:00-05:00")
    actual = respuestas_persistidas(aplicacion)[0]
    assert cambio["respuestas_guardadas"] == [{"item": "RIASEC-01", "opcion": 5}]
    assert actual.id == anterior.id
    assert actual.orden == 5 and actual.puntaje == 4
    assert actual.creada_en == anterior.creada_en == datetime(2026, 10, 1, 10)
    assert actual.actualizada_en == datetime(2026, 10, 2, 12)
    assert contar(aplicacion, modelos.RespuestaItem) == 1
    assert contar(aplicacion, modelos.EventoUso) == 0

    actual_publica, = cliente.get("/cuentas/est-ana/actividades/LAB-RIA1/respuestas").json()["respuestas"]
    assert actual_publica == {"item": "RIASEC-01", "opcion": {"orden": 5, "etiqueta": "Me gusta mucho", "puntaje": 4},
                            "creada_en": FECHA, "actualizada_en": "2026-10-02T12:00:00"}


@REQUIERE_OCUPACIONES
def test_i4_riasec_genera_resultado_solo_en_la_cuarta_actividad(cliente, aplicacion):
    for numero, respuesta in enumerate(aplicar_cadena(cliente, CADENA_A), start=1):
        if numero < 4:
            assert respuesta["resultados_generados"] == []
            assert resultados(aplicacion) == []
            assert estado_actividades(cliente)[f"LAB-RIA{numero + 1}"] == "DISPONIBLE"
            assert f"R-LAB-RIA{numero + 1}" in [nuevo["regla"] for nuevo in respuesta["nuevos_desbloqueos"]]
            pendiente = cliente.get("/cuentas/est-ana/instrumentos/TEST-RIASEC/resultado")
            assert pendiente.status_code == 409
            assert pendiente.json()["detail"]["avance"]["actividades"]["faltantes"] == [f"LAB-RIA{n}" for n in range(numero + 1, 5)]
        else:
            assert respuesta["resultados_generados"] == [{"instrumento": "TEST-RIASEC", "aplicacion": "APL-RIASEC"}]
    resultado, = resultados(aplicacion)
    assert resultado.calculado_en == datetime(2026, 10, 1, 10)
    assert resultado.anulado_en is None and resultado.perfil_plano is False
    assert dimensiones(aplicacion, resultado) == [
        ("R", 21, 40, 52.5), ("I", 9, 40, 22.5), ("A", 17, 40, 42.5),
        ("S", 20, 40, 50), ("E", 28, 40, 70), ("C", 15, 40, 37.5),
    ]
    codigo = calcular_codigo_interes([fila.puntaje for fila in dimensiones(aplicacion, resultado)])
    assert (codigo.codigo, codigo.hay_empate) == ("ERS", False)
    filas = coincidencias(aplicacion, resultado)
    assert len(filas) == 10
    assert [fila.posicion for fila in filas] == list(range(1, 11))
    assert [fila.correlacion for fila in filas] == sorted((fila.correlacion for fila in filas), reverse=True)
    assert all(fila.correlacion >= 0 and fila.ajuste == clasificar_ajuste(fila.correlacion) for fila in filas)
    publico = resultado_publico(cliente)
    assert [(d["codigo"], d["puntaje"], d["puntaje_maximo"], d["porcentaje"]) for d in publico["dimensiones"]] == dimensiones(aplicacion, resultado)
    assert publico["codigo_interes"] == {"codigo": "ERS", "hay_empate": False}
    assert [(c["posicion"], c["codigo_onet"], c["correlacion"], c["ajuste"]) for c in publico["coincidencias"]] == [
        (f.posicion, f.codigo_onet, round(f.correlacion, 6), f.ajuste) for f in filas]
    avance, = avance_publico(cliente)
    assert avance["estado"] == "COMPLETADO" and avance["hay_resultado_vigente"]
    assert avance["actividades"] == {"completadas": 4, "total": 4, "faltantes": []}
    assert avance["items"] == {"respondidos": 60, "total": 60}


@REQUIERE_OCUPACIONES
def test_i5_coincidencias_de_luis_contra_el_notebook(cliente, aplicacion):
    list(aplicar_cadena(cliente, CADENA_B, cuenta="est-luis"))
    resultado, = resultados(aplicacion, cuenta="est-luis")
    assert [fila.puntaje for fila in dimensiones(aplicacion, resultado)] == [27, 24, 18, 17, 23, 18]
    esperadas = [
        (1, "19-1031.02", "Range Managers", 0.897496),
        (2, "17-2199.11", "Solar Energy Systems Engineers", 0.833365),
        (3, "17-2199.10", "Wind Energy Engineers", 0.813152),
        (4, "17-2021.00", "Agricultural Engineers", 0.789390),
        (5, "17-2121.00", "Marine Engineers and Naval Architects", 0.786206),
        (6, "19-2041.02", "Environmental Restoration Planners", 0.786097),
        (7, "49-9092.00", "Commercial Divers", 0.785974),
        (8, "53-7031.00", "Dredge Operators", 0.765276),
        (9, "11-9041.01", "Biofuels/Biodiesel Technology and Product Development Managers", 0.761303),
        (10, "17-2141.01", "Fuel Cell Engineers", 0.754871),
    ]
    filas = coincidencias(aplicacion, resultado)
    assert [(f.posicion, f.codigo_onet, f.titulo, round(f.correlacion, 6)) for f in filas] == esperadas
    assert all(f.ajuste == "BEST_FIT" and f.correlacion != round(f.correlacion, 6) for f in filas)
    assert resultados(aplicacion, cuenta="est-ana") == []
    publico = resultado_publico(cliente, cuenta="est-luis")
    assert publico["codigo_interes"] == {"codigo": "RIE", "hay_empate": False}
    assert [(c["posicion"], c["codigo_onet"], c["titulo"], c["correlacion"]) for c in publico["coincidencias"]] == esperadas
    assert all(c["ajuste"] == "BEST_FIT" for c in publico["coincidencias"])
    assert [(c["codigo"], c["nombre"], c["familia"], [(v["posicion"], v["codigo_onet"]) for v in c["via"]])
            for c in publico["carreras_recomendadas"]] == [
        ("CAR-FOR", "Ingeniería forestal", "FAM-INGENIERIA", [(1, "19-1031.02")]),
        ("CAR-AMB", "Ingeniería ambiental", "FAM-INGENIERIA", [(2, "17-2199.11"), (6, "19-2041.02")]),
        ("CAR-AGR", "Ingeniería agrícola", "FAM-INGENIERIA", [(4, "17-2021.00")]),
    ]
    por_posicion = {c["posicion"]: c for c in publico["coincidencias"]}
    assert all(v == por_posicion[v["posicion"]] for c in publico["carreras_recomendadas"] for v in c["via"])
    assert cliente.get("/cuentas/est-ana/instrumentos/TEST-RIASEC/resultado").status_code == 409


def test_i6_perfil_plano_conserva_resultado_sin_coincidencias(cliente, aplicacion):
    list(aplicar_cadena(cliente, "3" * 60))
    resultado, = resultados(aplicacion)
    assert resultado.perfil_plano is True
    assert dimensiones(aplicacion, resultado) == [(codigo, 20, 40, 50) for codigo in "RIASEC"]
    assert coincidencias(aplicacion, resultado) == []
    codigo = calcular_codigo_interes([20] * 6)
    assert (codigo.codigo, codigo.hay_empate) == ("RIA", True)
    publico = resultado_publico(cliente)
    assert publico["perfil_plano"] is True
    assert publico["codigo_interes"] == {"codigo": "RIA", "hay_empate": True}
    assert publico["coincidencias"] == publico["carreras_recomendadas"] == []


@REQUIERE_OCUPACIONES
def test_i7_respuestas_fijas_y_rehacer_sin_recalcular(cliente, aplicacion):
    list(aplicar_cadena(cliente, CADENA_A))
    anterior, = resultados(aplicacion)
    publico_anterior = resultado_publico(cliente)
    valores = dimensiones(aplicacion, anterior)
    afines = coincidencias(aplicacion, anterior)
    respuestas = respuestas_persistidas(aplicacion, "LAB-RIA2")
    eventos = contar(aplicacion, modelos.EventoUso)
    cambio = cliente.post("/acciones/responder-items", json={
        "cuenta": "est-ana", "actividad": "LAB-RIA2", "respuestas": [{"item": "RIASEC-16", "opcion": 5}],
    })
    assert cambio.status_code == 409
    assert respuestas_persistidas(aplicacion, "LAB-RIA2") == respuestas
    repeticion = completar(cliente, "LAB-RIA2", fecha="2026-10-02T10:00:00")
    assert repeticion["resultados_generados"] == []
    assert [evento["tipo"] for evento in repeticion["eventos_registrados"]] == ["COMPLETA_ACTIVIDAD"]
    assert contar(aplicacion, modelos.EventoUso) == eventos + 1
    actual, = resultados(aplicacion)
    assert (actual.id, actual.calculado_en) == (anterior.id, anterior.calculado_en)
    assert dimensiones(aplicacion, actual) == valores
    assert coincidencias(aplicacion, actual) == afines
    assert resultado_publico(cliente) == publico_anterior
    historico, = cliente.get("/cuentas/est-ana/instrumentos/TEST-RIASEC/historial").json()
    assert historico == {**publico_anterior, "anulado_en": None}


def test_i8_inteligencias_genera_resultado_al_completar_la_segunda_actividad(cliente, aplicacion):
    for actividad, inicio, fin in (("LAB-INT1", 1, 22), ("LAB-INT2", 23, 43)):
        guardar(cliente, actividad, [{"item": f"INT-{n:02}", "opcion": 1 if n % 2 else 2} for n in range(inicio, fin + 1)])
        respuesta = completar(cliente, actividad)
        if actividad == "LAB-INT1":
            assert respuesta["resultados_generados"] == []
            assert resultados(aplicacion, "APL-INT") == []
        else:
            assert respuesta["resultados_generados"] == [{"instrumento": "TEST-INT", "aplicacion": "APL-INT"}]
    resultado, = resultados(aplicacion, "APL-INT")
    assert dimensiones(aplicacion, resultado) == [
        ("INT-LIN", 7, 10, 70), ("INT-LOG", 4, 7, 57.14), ("INT-ESP", 2, 4, 50),
        ("INT-CIN", 1, 5, 20), ("INT-MUS", 3, 4, 75), ("INT-INTER", 1, 8, 12.5), ("INT-INTRA", 4, 5, 80),
    ]
    assert coincidencias(aplicacion, resultado) == []
    publico = resultado_publico(cliente, "TEST-INT")
    assert [(d["codigo"], d["puntaje"], d["puntaje_maximo"], d["porcentaje"]) for d in publico["dimensiones"]] == dimensiones(aplicacion, resultado)
    assert set(publico) == {"instrumento", "aplicacion", "calculado_en", "perfil_plano", "dimensiones", "dimensiones_destacadas"}
    assert publico["dimensiones_destacadas"] == [publico["dimensiones"][6]]


def test_i8b_inteligencias_destaca_espacial_y_musical_en_orden_y_conserva_historial(cliente):
    afirmativos = {7, 18, 26, 29, 5, 10, 31, 39}
    for actividad, inicio, fin in (("LAB-INT1", 1, 22), ("LAB-INT2", 23, 43)):
        guardar(cliente, actividad, [{"item": f"INT-{n:02}", "opcion": 1 if n in afirmativos else 2}
                                    for n in range(inicio, fin + 1)])
        completar(cliente, actividad)
    publico = resultado_publico(cliente, "TEST-INT")
    assert [d["porcentaje"] for d in publico["dimensiones"]] == [0, 0, 100, 0, 100, 0, 0]
    assert publico["dimensiones_destacadas"] == [publico["dimensiones"][2], publico["dimensiones"][4]]
    reiniciar(cliente, "TEST-INT")
    historial = cliente.get("/cuentas/est-ana/instrumentos/TEST-INT/historial")
    assert historial.status_code == 200
    historico, = historial.json()
    assert historico["anulado_en"] is not None
    assert {k: v for k, v in historico.items() if k != "anulado_en"} == publico


def test_inteligencias_en_cero_destaca_todas_las_dimensiones(cliente):
    for actividad, inicio, fin in (("LAB-INT1", 1, 22), ("LAB-INT2", 23, 43)):
        guardar(cliente, actividad, [{"item": f"INT-{n:02}", "opcion": 2} for n in range(inicio, fin + 1)])
        completar(cliente, actividad)
    publico = resultado_publico(cliente, "TEST-INT")
    assert all(d["puntaje"] == d["porcentaje"] == 0 for d in publico["dimensiones"])
    assert publico["dimensiones_destacadas"] == publico["dimensiones"]


def test_i9_habilidades_sociales_aplica_la_inversion(cliente, aplicacion):
    guardar(cliente, "LAB-HAB", [{"item": f"HAB-{n:02}", "opcion": 1 if n <= 12 else 2} for n in range(1, 25)])
    respuesta = completar(cliente, "LAB-HAB")
    assert respuesta["resultados_generados"] == [{"instrumento": "TEST-HAB", "aplicacion": "APL-HAB"}]
    resultado, = resultados(aplicacion, "APL-HAB")
    assert dimensiones(aplicacion, resultado) == [
        ("HAB-ASE", 2, 5, 40), ("HAB-EMP", 2, 4, 50), ("HAB-LID", 1, 3, 33.33),
        ("HAB-RES", 1, 4, 25), ("HAB-EXP", 0, 3, 0), ("HAB-VAL", 4, 5, 80),
    ]
    assert coincidencias(aplicacion, resultado) == []
    publico = resultado_publico(cliente, "TEST-HAB")
    assert [(d["codigo"], d["puntaje"], d["puntaje_maximo"], d["porcentaje"]) for d in publico["dimensiones"]] == dimensiones(aplicacion, resultado)
    assert set(publico) == {"instrumento", "aplicacion", "calculado_en", "perfil_plano", "dimensiones", "dimensiones_destacadas"}
    assert publico["dimensiones_destacadas"] == [publico["dimensiones"][5]]


def test_i10_autopercepcion_guarda_los_mismos_items_en_dos_progresos(cliente, aplicacion):
    entrada = "BCCDBCACDB"
    salida = "AABCAACBBA"
    for actividad, letras in (("LAB-AUT-E", entrada), ("LAB-AUT-S", salida)):
        guardar(cliente, actividad, [{"item": f"AUT-{n:02}", "opcion": ord(letra) - ord("A") + 1}
                                    for n, letra in enumerate(letras, start=1)])
        assert completar(cliente, actividad)["resultados_generados"] == []
        if actividad == "LAB-AUT-E":
            comparacion = cliente.get("/cuentas/est-ana/instrumentos/TEST-AUTO/comparacion")
            assert comparacion.status_code == 409
            assert [a["estado"] for a in comparacion.json()["detail"]["avance"]] == ["COMPLETADO", "NO_INICIADO"]
        assert cliente.post("/acciones/responder-items", json={
            "cuenta": "est-ana", "actividad": actividad, "respuestas": [{"item": "AUT-01", "opcion": 1}],
        }).status_code == 409
    assert contar(aplicacion, modelos.ResultadoInstrumento) == 0
    entradas = respuestas_persistidas(aplicacion, "LAB-AUT-E")
    salidas = respuestas_persistidas(aplicacion, "LAB-AUT-S")
    assert len(entradas) == len(salidas) == 10
    assert [r.puntaje for r in entradas] == [3, 2, 2, 1, 3, 2, 4, 2, 1, 3]
    assert [r.puntaje for r in salidas] == [4, 4, 3, 2, 4, 4, 2, 3, 3, 4]
    assert [s.puntaje - e.puntaje for e, s in zip(entradas, salidas, strict=True)] == [1, 2, 1, 1, 1, 2, -2, 1, 2, 1]
    assert set(r.id for r in entradas).isdisjoint(r.id for r in salidas)
    assert contar(aplicacion, modelos.RespuestaItem) == 20
    comparacion = cliente.get("/cuentas/est-ana/instrumentos/TEST-AUTO/comparacion")
    assert comparacion.status_code == 200, comparacion.text
    filas = comparacion.json()["items"]
    assert [r["item"] for r in filas] == [f"AUT-{n:02}" for n in range(1, 11)]
    assert [r["entrada"]["puntaje"] for r in filas] == [r.puntaje for r in entradas]
    assert [r["salida"]["puntaje"] for r in filas] == [r.puntaje for r in salidas]
    assert [r["entrada"]["etiqueta"][0] for r in filas] == list(entrada)
    assert [r["salida"]["etiqueta"][0] for r in filas] == list(salida)
    assert [r["diferencia"] for r in filas] == [1, 2, 1, 1, 1, 2, -2, 1, 2, 1]
    assert [a["estado"] for a in avance_publico(cliente, "TEST-AUTO")] == ["COMPLETADO", "COMPLETADO"]
    assert cliente.get("/cuentas/est-ana/instrumentos/TEST-AUTO/historial").json() == []


@pytest.mark.parametrize("respuestas", [
    [], [{"item": "RIASEC-01", "opcion": 1}] * 2,
    [{"item": "RIASEC-01", "opcion": True}], [{"item": "RIASEC-01", "opcion": 1.5}],
    [{"item": "RIASEC-01", "opcion": "2"}], [{"item": "RIASEC-01", "opcion": 0}],
])
def test_entrada_invalida_no_crea_progreso_ni_respuestas(cliente, aplicacion, respuestas):
    assert cliente.post("/acciones/responder-items", json={
        "cuenta": "est-ana", "actividad": "LAB-RIA1", "respuestas": respuestas,
    }).status_code == 422
    assert contar(aplicacion, modelos.ProgresoActividad) == contar(aplicacion, modelos.RespuestaItem) == 0
    assert contar(aplicacion, modelos.EventoUso) == 0


@pytest.mark.parametrize("preexistente", [False, True])
@pytest.mark.parametrize("invalida, estado", [({"item": "RIASEC-20", "opcion": 1}, 409),
                                            ({"item": "RIASEC-02", "opcion": 6}, 422)])
def test_lote_se_valida_completo_antes_de_crear_o_reemplazar(cliente, aplicacion, preexistente, invalida, estado):
    if preexistente:
        guardar(cliente, "LAB-RIA1", [{"item": "RIASEC-01", "opcion": 5}])
    antes = respuestas_persistidas(aplicacion)
    progresos = contar(aplicacion, modelos.ProgresoActividad)
    respuesta = cliente.post("/acciones/responder-items", json={
        "cuenta": "est-ana", "actividad": "LAB-RIA1",
        "respuestas": [{"item": "RIASEC-01", "opcion": 1}, invalida],
    })
    assert respuesta.status_code == estado
    assert respuestas_persistidas(aplicacion) == antes
    assert contar(aplicacion, modelos.ProgresoActividad) == progresos
    assert contar(aplicacion, modelos.EventoUso) == 0


@pytest.mark.parametrize("cuenta, actividad, estado", [
    ("no-existe", "LAB-RIA1", 404), ("est-ana", "no-existe", 404), ("apo-rosa", "LAB-RIA1", 404),
    ("est-ana", "ACT-01", 409),
])
def test_cuentas_actividades_y_audiencia_se_validan(cliente, aplicacion, cuenta, actividad, estado):
    assert cliente.post("/acciones/responder-items", json={
        "cuenta": cuenta, "actividad": actividad, "respuestas": [{"item": "RIASEC-01", "opcion": 1}],
    }).status_code == estado
    assert contar(aplicacion, modelos.RespuestaItem) == 0
    assert contar(aplicacion, modelos.EventoUso) == 0


def test_apoderado_no_puede_completar_actividades_de_instrumentos(cliente):
    assert cliente.post("/acciones/completar-actividad", json={
        "cuenta": "apo-rosa", "actividad": "LAB-RIA1",
    }).status_code == 404


def test_completar_sin_respuestas_devuelve_todos_los_faltantes(cliente, aplicacion):
    respuesta = cliente.post("/acciones/completar-actividad", json={"cuenta": "est-ana", "actividad": "LAB-HAB"})
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"]["items_faltantes"] == [f"HAB-{n:02}" for n in range(1, 25)]
    assert contar(aplicacion, modelos.ProgresoActividad) == contar(aplicacion, modelos.EventoUso) == 0


def test_actividad_sin_items_conserva_eventos_y_anuncia_lista_vacia(cliente):
    respuesta = completar(cliente, "ACT-01")
    assert respuesta["resultados_generados"] == []
    assert [e["tipo"] for e in respuesta["eventos_registrados"]] == ["COMPLETA_ACTIVIDAD"]
    assert [d["regla"] for d in respuesta["nuevos_desbloqueos"]] == ["R-ACT-02"]


def test_se_puede_editar_una_actividad_completada_si_la_aplicacion_sigue_incompleta(cliente, aplicacion):
    list(aplicar_cadena(cliente, "3" * 60, hasta=1))
    assert resultados(aplicacion) == []
    guardado = guardar(cliente, "LAB-RIA1", [{"item": "RIASEC-01", "opcion": 5}])
    assert guardado["progreso"] == {"estado": "COMPLETADA", "respondidos": 15, "total": 15}
    assert estado_actividades(cliente)["LAB-RIA1"] == "COMPLETADA"
    assert respuestas_persistidas(aplicacion)[0].orden == 5


def test_respuestas_de_otra_cuenta_no_completan_la_actividad(cliente, aplicacion):
    guardar(cliente, "LAB-RIA1", [{"item": f"RIASEC-{n:02}", "opcion": 3} for n in range(1, 16)])
    respuesta = cliente.post("/acciones/completar-actividad", json={"cuenta": "est-luis", "actividad": "LAB-RIA1"})
    assert respuesta.status_code == 409
    assert len(respuesta.json()["detail"]["items_faltantes"]) == 15
    assert respuestas_persistidas(aplicacion, cuenta="est-luis") == []
    assert estado_actividades(cliente, "est-luis")["LAB-RIA1"] == "DISPONIBLE"


def test_actividad_con_progreso_en_curso_sigue_bloqueada_si_su_bloque_lo_esta(cliente, aplicacion):
    with aplicacion.state.fabrica_sesiones.begin() as sesion:
        cuenta = sesion.scalar(select(modelos.Cuenta).where(modelos.Cuenta.codigo == "est-ana"))
        actividad = sesion.scalar(select(modelos.Actividad).where(modelos.Actividad.codigo == "HEL-01"))
        sesion.add(modelos.ProgresoActividad(cuenta_id=cuenta.id, actividad_id=actividad.id, estado=modelos.EstadoProgreso.EN_CURSO))
    assert estado_actividades(cliente)["HEL-01"] == "BLOQUEADA"


def test_una_actividad_genera_resultados_para_cada_aplicacion(cliente, aplicacion):
    with aplicacion.state.fabrica_sesiones.begin() as sesion:
        instrumento = sesion.scalar(select(modelos.Instrumento).where(modelos.Instrumento.codigo == "TEST-HAB"))
        actividad = sesion.scalar(select(modelos.Actividad).where(modelos.Actividad.codigo == "LAB-HAB"))
        segunda = modelos.Aplicacion(codigo="APL-HAB-OTRA", nombre="Prueba de dos aplicaciones", instrumento_id=instrumento.id)
        sesion.add(segunda)
        sesion.flush()
        sesion.add(modelos.AplicacionActividad(aplicacion_id=segunda.id, actividad_id=actividad.id))
    guardar(cliente, "LAB-HAB", [{"item": f"HAB-{n:02}", "opcion": 1} for n in range(1, 25)])
    assert completar(cliente, "LAB-HAB")["resultados_generados"] == [
        {"instrumento": "TEST-HAB", "aplicacion": "APL-HAB"},
        {"instrumento": "TEST-HAB", "aplicacion": "APL-HAB-OTRA"},
    ]
    assert contar(aplicacion, modelos.ResultadoInstrumento) == 2
    assert cliente.get("/cuentas/est-ana/instrumentos/TEST-HAB/resultado").status_code == 422
    for codigo in ("APL-HAB", "APL-HAB-OTRA"):
        respuesta = cliente.get("/cuentas/est-ana/instrumentos/TEST-HAB/resultado", params={"aplicacion": codigo})
        assert respuesta.status_code == 200
        assert respuesta.json()["aplicacion"] == codigo
    assert [r["aplicacion"] for r in cliente.get("/cuentas/est-ana/instrumentos/TEST-HAB/historial").json()] == [
        "APL-HAB-OTRA", "APL-HAB",
    ]


def test_fallo_del_calculo_revierte_resultados_progreso_eventos_y_desbloqueos(cliente, aplicacion, monkeypatch):
    for actividad in ("ACT-01", "ACT-02", "ACT-03", "ACT-04", "ACT-05", "ACT-06", "ACT-12"):
        completar(cliente, actividad)
    guardar(cliente, "LAB-HAB", [{"item": f"HAB-{n:02}", "opcion": 1} for n in range(1, 25)])
    eventos = cliente.get("/cuentas/est-ana/eventos").json()
    desbloqueos = cliente.get("/cuentas/est-ana/desbloqueos").json()
    respuestas = respuestas_persistidas(aplicacion, "LAB-HAB")
    original = resultados_instrumentos.generar_resultado

    def fallar_despues_de_guardar(sesion, cuenta, aplicacion_instrumento, fecha):
        original(sesion, cuenta, aplicacion_instrumento, fecha)
        assert sesion.scalar(select(func.count()).select_from(modelos.ResultadoInstrumento)) == 1
        assert sesion.scalar(select(func.count()).select_from(modelos.ResultadoDimension)) == 6
        assert sesion.scalar(select(modelos.Desbloqueo.id).join(modelos.ReglaDesbloqueo).where(
            modelos.ReglaDesbloqueo.codigo == "R-LOG-INCANSABLE",
        )) is not None
        raise RuntimeError("Fallo forzado después de guardar el resultado")

    monkeypatch.setattr(resultados_instrumentos, "generar_resultado", fallar_despues_de_guardar)
    with pytest.raises(RuntimeError, match="Fallo forzado"):
        completar(cliente, "LAB-HAB")
    assert estado_actividades(cliente)["LAB-HAB"] == "EN_CURSO"
    assert cliente.get("/cuentas/est-ana/eventos").json() == eventos
    assert cliente.get("/cuentas/est-ana/desbloqueos").json() == desbloqueos
    assert respuestas_persistidas(aplicacion, "LAB-HAB") == respuestas
    for modelo in (modelos.ResultadoInstrumento, modelos.ResultadoDimension, modelos.Coincidencia):
        assert contar(aplicacion, modelo) == 0


def test_catalogo_e_items_publicos_conservan_definiciones_orden_y_opciones(cliente):
    respuesta = cliente.get("/instrumentos")
    assert respuesta.status_code == 200
    catalogo = respuesta.json()
    assert [i["codigo"] for i in catalogo] == ["TEST-AUTO", "TEST-HAB", "TEST-INT", "TEST-RIASEC"]
    assert [len(i["dimensiones"]) for i in catalogo] == [0, 6, 7, 6]
    assert [[e["codigo"] for e in i["escalas"]] for i in catalogo] == [
        ["ESC-A-D"], ["ESC-FRECUENCIA"], ["ESC-SI-NO"], ["ESC-LIKERT5"],
    ]
    riasec = catalogo[-1]
    assert [d["codigo"] for d in riasec["dimensiones"]] == list("RIASEC")
    assert [d["orden"] for d in riasec["dimensiones"]] == list(range(1, 7))
    assert [a["codigo"] for a in riasec["aplicaciones"][0]["actividades"]] == [f"LAB-RIA{n}" for n in range(1, 5)]
    assert [a["codigo"] for a in catalogo[0]["aplicaciones"]] == ["APL-AUTO-ENT", "APL-AUTO-SAL"]
    for instrumento in catalogo:
        for aplicacion in instrumento["aplicaciones"]:
            todos = []
            for actividad in aplicacion["actividades"]:
                respuesta = cliente.get(f"/actividades/{actividad['codigo']}/items")
                assert respuesta.status_code == 200
                items = respuesta.json()
                assert [i["orden"] for i in items] == list(range(1, len(items) + 1))
                assert all(i["instrumento"] == instrumento["codigo"] and i["escala"] in instrumento["escalas"] for i in items)
                todos.extend(i["codigo"] for i in items)
            assert len(todos) == len(set(todos)) == {"TEST-AUTO": 10, "TEST-HAB": 24, "TEST-INT": 43, "TEST-RIASEC": 60}[instrumento["codigo"]]
    hab = cliente.get("/actividades/LAB-HAB/items").json()
    assert [i["numero"] for i in hab if i["inverso"]] == [3, 5, 8, 20]
    aut_entrada = cliente.get("/actividades/LAB-AUT-E/items").json()
    assert aut_entrada == cliente.get("/actividades/LAB-AUT-S/items").json()
    assert all(i["dimension"] is None and not i["inverso"] for i in aut_entrada)


@pytest.mark.parametrize("cuenta", ["apo-rosa", "inexistente"])
@pytest.mark.parametrize("ruta", [
    "/cuentas/{cuenta}/instrumentos", "/cuentas/{cuenta}/actividades/LAB-RIA1/respuestas",
    "/cuentas/{cuenta}/instrumentos/TEST-RIASEC/resultado",
    "/cuentas/{cuenta}/instrumentos/TEST-RIASEC/historial",
    "/cuentas/{cuenta}/instrumentos/TEST-AUTO/comparacion",
])
def test_consultas_de_instrumentos_rechazan_apoderados_y_cuentas_inexistentes(cliente, cuenta, ruta):
    assert cliente.get(ruta.format(cuenta=cuenta)).status_code == 404


@pytest.mark.parametrize("ruta", [
    "/actividades/inexistente/items", "/actividades/ACT-P01/items",
    "/cuentas/est-ana/actividades/inexistente/respuestas", "/cuentas/est-ana/actividades/ACT-P01/respuestas",
    "/cuentas/est-ana/instrumentos/inexistente/resultado", "/cuentas/est-ana/instrumentos/inexistente/historial",
    "/cuentas/est-ana/instrumentos/TEST-RIASEC/resultado?aplicacion=APL-HAB",
    "/cuentas/est-ana/instrumentos/TEST-AUTO/resultado?aplicacion=inexistente",
])
def test_consultas_rechazan_referencias_y_aplicaciones_ajenas(cliente, ruta):
    assert cliente.get(ruta).status_code == 404


def test_resultado_exige_aplicacion_y_devuelve_avance_sin_resultado(cliente):
    ruta = "/cuentas/est-ana/instrumentos/TEST-AUTO/resultado"
    assert cliente.get(ruta).status_code == 422
    for codigo in ("APL-AUTO-ENT", "APL-AUTO-SAL"):
        respuesta = cliente.get(ruta, params={"aplicacion": codigo})
        assert respuesta.status_code == 409
        avance = respuesta.json()["detail"]["avance"]
        assert avance["aplicacion"] == codigo and avance["estado"] == "NO_INICIADO"
        assert avance["items"] == {"respondidos": 0, "total": 10}
    assert cliente.get("/actividades/ACT-01/items").json() == []
    assert cliente.get("/cuentas/est-ana/actividades/ACT-01/respuestas").json() == {
        "cuenta": "est-ana", "actividad": "ACT-01", "respuestas": [],
    }


def test_respuestas_publicas_se_aislan_por_cuenta_y_aplicacion(cliente):
    guardar(cliente, "LAB-AUT-E", [{"item": "AUT-01", "opcion": 2}])
    for cuenta, actividad in (("est-ana", "LAB-AUT-S"), ("est-luis", "LAB-AUT-E")):
        assert cliente.get(f"/cuentas/{cuenta}/actividades/{actividad}/respuestas").json()["respuestas"] == []
    assert [a["items"]["respondidos"] for a in avance_publico(cliente, "TEST-AUTO")] == [1, 0]
    assert [a["items"]["respondidos"] for a in avance_publico(cliente, "TEST-AUTO", "est-luis")] == [0, 0]


@REQUIERE_OCUPACIONES
def test_historial_conserva_dimensiones_coincidencias_y_ordena_fecha_y_desempate(cliente, aplicacion):
    # Prepara resultados históricos en SQL; el reinicio público se implementa en fase 5.
    list(aplicar_cadena(cliente, CADENA_A))
    original = resultado_publico(cliente)
    from app.database import Base

    with aplicacion.state.fabrica_sesiones.begin() as sesion:
        antiguo = sesion.scalar(select(modelos.ResultadoInstrumento))
        antiguo.anulado_en = datetime(2026, 10, 2, 10)
        detalles = sesion.scalars(select(modelos.ResultadoDimension)).all()
        afines = sesion.scalars(select(modelos.Coincidencia)).all()
        for fecha in (antiguo.calculado_en, datetime(2026, 9, 30, 10)):
            copia = modelos.ResultadoInstrumento(cuenta_id=antiguo.cuenta_id, aplicacion_id=antiguo.aplicacion_id,
                calculado_en=fecha, anulado_en=datetime(2026, 10, 3, 10), perfil_plano=False)
            sesion.add(copia)
            sesion.flush()
            sesion.add_all(modelos.ResultadoDimension(resultado_id=copia.id, dimension_id=d.dimension_id,
                puntaje=d.puntaje, puntaje_maximo=d.puntaje_maximo, porcentaje=d.porcentaje) for d in detalles)
            sesion.add_all(modelos.Coincidencia(resultado_id=copia.id, ocupacion_id=c.ocupacion_id,
                posicion=c.posicion, correlacion=c.correlacion, ajuste=c.ajuste) for c in afines)

    def fotografia():
        with aplicacion.state.fabrica_sesiones() as sesion:
            return {nombre: sesion.execute(select(tabla)).all() for nombre, tabla in Base.metadata.tables.items()}

    antes = fotografia()
    historial = cliente.get("/cuentas/est-ana/instrumentos/TEST-RIASEC/historial").json()
    assert len(historial) == 3
    assert [r["calculado_en"] for r in historial] == [FECHA, FECHA, "2026-09-30T10:00:00"]
    assert [r["anulado_en"] for r in historial] == ["2026-10-03T10:00:00", "2026-10-02T10:00:00", "2026-10-03T10:00:00"]
    assert all(r["dimensiones"] == original["dimensiones"] and r["coincidencias"] == original["coincidencias"]
               and r["codigo_interes"] == original["codigo_interes"] and r["carreras_recomendadas"] == original["carreras_recomendadas"] for r in historial)
    pendiente = cliente.get("/cuentas/est-ana/instrumentos/TEST-RIASEC/resultado")
    assert pendiente.status_code == 409
    assert pendiente.json()["detail"]["avance"] == {"aplicacion": "APL-RIASEC", "estado": "EN_PROGRESO",
        "actividades": {"completadas": 4, "total": 4, "faltantes": []}, "items": {"respondidos": 60, "total": 60},
        "hay_resultado_vigente": False}
    assert cliente.get("/cuentas/est-luis/instrumentos/TEST-RIASEC/historial").json() == []
    assert fotografia() == antes


def test_todas_las_consultas_son_de_lectura_y_exponen_solo_codigos_publicos(cliente, aplicacion):
    from app.database import Base
    list(aplicar_cadena(cliente, "3" * 60))
    guardar(cliente, "LAB-AUT-E", [{"item": "AUT-01", "opcion": 2}])

    def fotografia():
        with aplicacion.state.fabrica_sesiones() as sesion:
            return {nombre: sesion.execute(select(tabla)).all() for nombre, tabla in Base.metadata.tables.items()}

    def verificar_claves(valor):
        if isinstance(valor, dict):
            assert all(clave != "id" and not clave.endswith("_id") for clave in valor)
            for contenido in valor.values():
                verificar_claves(contenido)
        elif isinstance(valor, list):
            for contenido in valor:
                verificar_claves(contenido)

    antes = fotografia()
    for ruta in ("/instrumentos", "/actividades/LAB-RIA2/items", "/cuentas/est-ana/actividades/LAB-AUT-E/respuestas",
                 "/cuentas/est-ana/instrumentos", "/cuentas/est-ana/instrumentos/TEST-RIASEC/resultado",
                 "/cuentas/est-ana/instrumentos/TEST-RIASEC/historial",
                 "/cuentas/est-ana/instrumentos/TEST-AUTO/comparacion"):
        respuesta = cliente.get(ruta)
        assert respuesta.status_code == (409 if ruta.endswith("comparacion") else 200), respuesta.text
        verificar_claves(respuesta.json())
    assert fotografia() == antes


@REQUIERE_OCUPACIONES
def test_i11_reinicio_riasec_conserva_historia_y_permite_nuevo_resultado(cliente, aplicacion):
    list(aplicar_cadena(cliente, CADENA_A))
    anterior = resultado_publico(cliente)
    eventos = cliente.get("/cuentas/est-ana/eventos").json()
    desbloqueos = cliente.get("/cuentas/est-ana/desbloqueos").json()
    resultado, = resultados(aplicacion)
    detalles = dimensiones(aplicacion, resultado)
    afines = coincidencias(aplicacion, resultado)
    verificar_invariantes_persistidos(aplicacion)
    respuesta = reiniciar(cliente)
    assert respuesta == {
        "cuenta": "est-ana", "instrumento": "TEST-RIASEC", "aplicacion": "APL-RIASEC",
        "resultado_anulado": {"instrumento": "TEST-RIASEC", "aplicacion": "APL-RIASEC",
                              "calculado_en": FECHA, "anulado_en": "2026-10-02T10:00:00"},
        "actividades_reiniciadas": [f"LAB-RIA{n}" for n in range(1, 5)],
        "eventos_registrados": [{"tipo": "REINICIA_INSTRUMENTO", "referencia": "TEST-RIASEC", "fecha_hora": "2026-10-02T10:00:00"}],
        "nuevos_desbloqueos": [],
    }
    assert cliente.get("/cuentas/est-ana/desbloqueos").json() == desbloqueos
    assert cliente.get("/cuentas/est-ana/eventos").json() == respuesta["eventos_registrados"] + eventos
    assert [estado_actividades(cliente)[f"LAB-RIA{n}"] for n in range(1, 5)] == ["EN_CURSO"] * 4
    for n in range(1, 5):
        assert cliente.get(f"/cuentas/est-ana/actividades/LAB-RIA{n}/respuestas").json()["respuestas"] == []
    pendiente = cliente.get("/cuentas/est-ana/instrumentos/TEST-RIASEC/resultado")
    assert pendiente.status_code == 409
    assert pendiente.json()["detail"]["avance"] == {"aplicacion": "APL-RIASEC", "estado": "EN_PROGRESO",
        "actividades": {"completadas": 0, "total": 4, "faltantes": [f"LAB-RIA{n}" for n in range(1, 5)]},
        "items": {"respondidos": 0, "total": 60}, "hay_resultado_vigente": False}
    assert dimensiones(aplicacion, resultado) == detalles
    assert coincidencias(aplicacion, resultado) == afines
    assert cliente.get("/cuentas/est-ana/instrumentos/TEST-RIASEC/historial").json() == [
        {**anterior, "anulado_en": "2026-10-02T10:00:00"}]
    verificar_invariantes_persistidos(aplicacion)
    for respuesta in aplicar_cadena(cliente, CADENA_B, fecha="2026-10-03T10:00:00"):
        verificar_invariantes_persistidos(aplicacion)
    nuevo = resultado_publico(cliente)
    assert [d["puntaje"] for d in nuevo["dimensiones"]] == [27, 24, 18, 17, 23, 18]
    assert nuevo["codigo_interes"] == {"codigo": "RIE", "hay_empate": False}
    assert [c["codigo"] for c in nuevo["carreras_recomendadas"]] == ["CAR-FOR", "CAR-AMB", "CAR-AGR"]
    historial = cliente.get("/cuentas/est-ana/instrumentos/TEST-RIASEC/historial").json()
    assert historial == [{**nuevo, "anulado_en": None}, {**anterior, "anulado_en": "2026-10-02T10:00:00"}]
    assert len(resultados(aplicacion)) == 2
    id_vigente = resultados(aplicacion)[-1].id
    for n in range(1, 5):
        assert completar(cliente, f"LAB-RIA{n}")["resultados_generados"] == []
    assert resultados(aplicacion)[-1].id == id_vigente
    verificar_invariantes_persistidos(aplicacion)


def test_i12_reinicio_solo_de_salida_conserva_entrada_y_exige_seleccion(cliente, aplicacion):
    for actividad, letras in (("LAB-AUT-E", "BCCDBCACDB"), ("LAB-AUT-S", "AABCAACBBA")):
        guardar(cliente, actividad, [{"item": f"AUT-{n:02}", "opcion": ord(letra) - ord("A") + 1}
                                    for n, letra in enumerate(letras, start=1)])
        completar(cliente, actividad)
    entrada = cliente.get("/cuentas/est-ana/actividades/LAB-AUT-E/respuestas").json()
    comparacion = cliente.get("/cuentas/est-ana/instrumentos/TEST-AUTO/comparacion").json()
    eventos = cliente.get("/cuentas/est-ana/eventos").json()
    assert cliente.post("/acciones/reiniciar-instrumento", json={"cuenta": "est-ana", "instrumento": "TEST-AUTO"}).status_code == 422
    assert cliente.get("/cuentas/est-ana/eventos").json() == eventos
    respuesta = reiniciar(cliente, "TEST-AUTO", codigo="APL-AUTO-SAL")
    assert respuesta["resultado_anulado"] is None
    assert respuesta["actividades_reiniciadas"] == ["LAB-AUT-S"]
    assert cliente.get("/cuentas/est-ana/actividades/LAB-AUT-E/respuestas").json() == entrada
    assert cliente.get("/cuentas/est-ana/actividades/LAB-AUT-S/respuestas").json()["respuestas"] == []
    assert estado_actividades(cliente)["LAB-AUT-E"] == "COMPLETADA"
    assert estado_actividades(cliente)["LAB-AUT-S"] == "EN_CURSO"
    assert [a["estado"] for a in avance_publico(cliente, "TEST-AUTO")] == ["COMPLETADO", "EN_PROGRESO"]
    assert cliente.get("/cuentas/est-ana/instrumentos/TEST-AUTO/comparacion").status_code == 409
    eventos = cliente.get("/cuentas/est-ana/eventos").json()
    assert cliente.post("/acciones/reiniciar-instrumento", json={
        "cuenta": "est-ana", "instrumento": "TEST-AUTO", "aplicacion": "APL-AUTO-SAL"}).status_code == 409
    assert cliente.get("/cuentas/est-ana/eventos").json() == eventos
    guardar(cliente, "LAB-AUT-S", [{"item": f"AUT-{n:02}", "opcion": ord(letra) - ord("A") + 1}
                                    for n, letra in enumerate("AABCAACBBA", start=1)])
    assert completar(cliente, "LAB-AUT-S")["resultados_generados"] == []
    assert cliente.get("/cuentas/est-ana/instrumentos/TEST-AUTO/comparacion").json() == comparacion
    assert contar(aplicacion, modelos.ResultadoInstrumento) == 0
    verificar_invariantes_persistidos(aplicacion)


@REQUIERE_OCUPACIONES
def test_i13_cuentas_intercaladas_con_resultados_y_reinicio_aislados(cliente, aplicacion):
    ana = aplicar_cadena(cliente, CADENA_A)
    luis = aplicar_cadena(cliente, CADENA_B, cuenta="est-luis")
    for _ in range(4):
        next(ana)
        next(luis)
        verificar_invariantes_persistidos(aplicacion)
    resultado_ana = resultado_publico(cliente)
    resultado_luis = resultado_publico(cliente, cuenta="est-luis")
    assert [d["puntaje"] for d in resultado_ana["dimensiones"]] == [21, 9, 17, 20, 28, 15]
    assert [d["puntaje"] for d in resultado_luis["dimensiones"]] == [27, 24, 18, 17, 23, 18]
    assert resultado_ana["codigo_interes"] == {"codigo": "ERS", "hay_empate": False}
    assert resultado_luis["codigo_interes"] == {"codigo": "RIE", "hay_empate": False}
    for cuenta in ("est-ana", "est-luis"):
        for n in range(1, 5):
            ruta = f"/cuentas/{cuenta}/actividades/LAB-RIA{n}/respuestas"
            respuestas = cliente.get(ruta).json()
            assert cliente.post("/acciones/responder-items", json={"cuenta": cuenta, "actividad": f"LAB-RIA{n}",
                "respuestas": [{"item": f"RIASEC-{15 * (n - 1) + 1:02}", "opcion": 1}]}).status_code == 409
            assert cliente.get(ruta).json() == respuestas
    fotografia_luis = {ruta: cliente.get(ruta).json() for ruta in (
        "/cuentas/est-luis/estado", "/cuentas/est-luis/eventos", "/cuentas/est-luis/desbloqueos",
        "/cuentas/est-luis/instrumentos", "/cuentas/est-luis/instrumentos/TEST-RIASEC/resultado",
        "/cuentas/est-luis/instrumentos/TEST-RIASEC/historial",
        *[f"/cuentas/est-luis/actividades/LAB-RIA{n}/respuestas" for n in range(1, 5)],
    )}
    reiniciar(cliente)
    for ruta, esperado in fotografia_luis.items():
        assert cliente.get(ruta).json() == esperado
    assert cliente.post("/acciones/reiniciar-instrumento", json={"cuenta": "apo-rosa", "instrumento": "TEST-RIASEC"}).status_code == 404
    verificar_invariantes_persistidos(aplicacion)


def test_i14_fallo_del_calculo_riasec_revierte_ultima_actividad(cliente, aplicacion, monkeypatch):
    list(aplicar_cadena(cliente, "3" * 60, hasta=3))
    guardar(cliente, "LAB-RIA4", [{"item": f"RIASEC-{n:02}", "opcion": 3} for n in range(46, 61)])
    eventos = cliente.get("/cuentas/est-ana/eventos").json()
    desbloqueos = cliente.get("/cuentas/est-ana/desbloqueos").json()
    respuestas = respuestas_persistidas(aplicacion, "LAB-RIA4")
    original = resultados_instrumentos.generar_resultado

    def fallar_despues_del_calculo(sesion, cuenta, aplicacion_instrumento, fecha):
        original(sesion, cuenta, aplicacion_instrumento, fecha)
        assert sesion.scalar(select(func.count()).select_from(modelos.ResultadoDimension)) == 6
        raise RuntimeError("Cálculo RIASEC forzado a fallar")

    monkeypatch.setattr(resultados_instrumentos, "generar_resultado", fallar_despues_del_calculo)
    with pytest.raises(RuntimeError, match="RIASEC forzado"):
        completar(cliente, "LAB-RIA4")
    assert estado_actividades(cliente)["LAB-RIA4"] == "EN_CURSO"
    assert cliente.get("/cuentas/est-ana/eventos").json() == eventos
    assert cliente.get("/cuentas/est-ana/desbloqueos").json() == desbloqueos
    assert respuestas_persistidas(aplicacion, "LAB-RIA4") == respuestas
    assert contar(aplicacion, modelos.ResultadoInstrumento) == contar(aplicacion, modelos.ResultadoDimension) == 0
    assert cliente.get("/cuentas/est-ana/instrumentos/TEST-RIASEC/resultado").status_code == 409
    verificar_invariantes_persistidos(aplicacion)


@pytest.mark.parametrize("entrada, estado", [
    ({"cuenta": "no-existe", "instrumento": "TEST-RIASEC"}, 404),
    ({"cuenta": "apo-rosa", "instrumento": "TEST-RIASEC"}, 404),
    ({"cuenta": "est-ana", "instrumento": "no-existe"}, 404),
    ({"cuenta": "est-ana", "instrumento": "TEST-RIASEC", "aplicacion": "no-existe"}, 404),
    ({"cuenta": "est-ana", "instrumento": "TEST-RIASEC", "aplicacion": "APL-HAB"}, 404),
    ({"cuenta": "est-ana", "instrumento": "TEST-AUTO"}, 422),
    ({"cuenta": "est-ana"}, 422),
    ({"instrumento": "TEST-RIASEC"}, 422),
    ({"cuenta": "est-ana", "instrumento": "TEST-RIASEC", "fecha_hora": "inválida"}, 422),
])
def test_reinicio_invalido_no_modifica_estado(cliente, aplicacion, entrada, estado):
    guardar(cliente, "LAB-RIA1", [{"item": "RIASEC-01", "opcion": 5}])
    antes = respuestas_persistidas(aplicacion)
    assert cliente.post("/acciones/reiniciar-instrumento", json=entrada).status_code == estado
    assert respuestas_persistidas(aplicacion) == antes
    assert estado_actividades(cliente)["LAB-RIA1"] == "EN_CURSO"
    assert contar(aplicacion, modelos.EventoUso) == contar(aplicacion, modelos.ResultadoInstrumento) == 0


@pytest.mark.parametrize("instrumento, codigo", [
    ("TEST-RIASEC", None), ("TEST-HAB", None), ("TEST-INT", None),
    ("TEST-AUTO", "APL-AUTO-ENT"), ("TEST-AUTO", "APL-AUTO-SAL"),
])
def test_reinicio_sin_respuestas_ni_resultado_devuelve_409(cliente, aplicacion, instrumento, codigo):
    entrada = {"cuenta": "est-ana", "instrumento": instrumento, "aplicacion": codigo}
    respuesta = cliente.post("/acciones/reiniciar-instrumento", json=entrada)
    assert respuesta.status_code == 409
    assert respuesta.json()["detail"]["mensaje"] == "Nada que reiniciar"
    assert contar(aplicacion, modelos.ProgresoActividad) == contar(aplicacion, modelos.EventoUso) == 0


def test_reinicio_parcial_no_crea_progresos_y_no_abre_actividades(cliente, aplicacion):
    guardar(cliente, "LAB-RIA1", [{"item": "RIASEC-01", "opcion": 5}])
    respuesta = reiniciar(cliente, codigo="APL-RIASEC")
    assert respuesta["resultado_anulado"] is None
    assert respuesta["actividades_reiniciadas"] == ["LAB-RIA1"]
    assert contar(aplicacion, modelos.ProgresoActividad) == 1
    assert contar(aplicacion, modelos.RespuestaItem) == 0
    assert [estado_actividades(cliente)[f"LAB-RIA{n}"] for n in range(1, 5)] == ["EN_CURSO", "BLOQUEADA", "BLOQUEADA", "BLOQUEADA"]
    eventos = cliente.get("/cuentas/est-ana/eventos").json()
    assert cliente.post("/acciones/reiniciar-instrumento", json={"cuenta": "est-ana", "instrumento": "TEST-RIASEC"}).status_code == 409
    assert cliente.get("/cuentas/est-ana/eventos").json() == eventos
    assert avance_publico(cliente)[0]["estado"] == "EN_PROGRESO"
    verificar_invariantes_persistidos(aplicacion)


@pytest.mark.parametrize("ciclos", [1, 3])
def test_ciclos_planos_mantienen_un_solo_vigente_y_todo_el_historial(cliente, aplicacion, ciclos):
    for ciclo in range(ciclos + 1):
        list(aplicar_cadena(cliente, "3" * 60, fecha=f"2026-10-{ciclo + 1:02}T10:00:00"))
        vigente = resultado_publico(cliente)
        verificar_invariantes_persistidos(aplicacion)
        if ciclo < ciclos:
            reiniciar(cliente, fecha=f"2026-10-{ciclo + 1:02}T12:00:00")
            verificar_invariantes_persistidos(aplicacion)
            assert contar(aplicacion, modelos.ResultadoInstrumento) == ciclo + 1
            assert contar(aplicacion, modelos.ResultadoDimension) == 6 * (ciclo + 1)
    historial = cliente.get("/cuentas/est-ana/instrumentos/TEST-RIASEC/historial").json()
    assert len(historial) == ciclos + 1
    assert sum(r["anulado_en"] is None for r in historial) == 1
    assert historial[0] == {**vigente, "anulado_en": None}
    assert all(r["anulado_en"] is not None for r in historial[1:])
    # Las respuestas congeladas no cambian, ni siquiera al enviar la misma opción.
    antes = respuestas_persistidas(aplicacion)
    assert cliente.post("/acciones/responder-items", json={"cuenta": "est-ana", "actividad": "LAB-RIA1",
        "respuestas": [{"item": "RIASEC-01", "opcion": 3}]}).status_code == 409
    assert respuestas_persistidas(aplicacion) == antes
    verificar_invariantes_persistidos(aplicacion)


def test_reinicio_borra_solo_respuestas_del_instrumento_en_los_progresos_elegidos(cliente, aplicacion):
    # Un ítem ajeno en el progreso y otra aplicación son datos exclusivos de prueba.
    guardar(cliente, "LAB-RIA1", [{"item": "RIASEC-01", "opcion": 5}])
    guardar(cliente, "LAB-HAB", [{"item": "HAB-01", "opcion": 1}])
    with aplicacion.state.fabrica_sesiones.begin() as sesion:
        progreso = sesion.scalar(select(modelos.ProgresoActividad).join(modelos.Actividad).where(modelos.Actividad.codigo == "LAB-RIA1"))
        item = sesion.scalar(select(modelos.ItemInstrumento).where(modelos.ItemInstrumento.codigo == "HAB-02"))
        opcion = sesion.scalar(select(modelos.OpcionEscala).where(modelos.OpcionEscala.escala_id == item.escala_id,
                                                                  modelos.OpcionEscala.orden == 1))
        ajena = modelos.RespuestaItem(progreso_id=progreso.id, item_id=item.id, opcion_id=opcion.id,
            creada_en=datetime(2026, 10, 1, 10), actualizada_en=datetime(2026, 10, 1, 10))
        sesion.add(ajena)
        sesion.flush()
        id_ajena = ajena.id
    hab = cliente.get("/cuentas/est-ana/actividades/LAB-HAB/respuestas").json()
    reiniciar(cliente)
    with aplicacion.state.fabrica_sesiones() as sesion:
        assert sesion.get(modelos.RespuestaItem, id_ajena) is not None
    assert cliente.get("/cuentas/est-ana/actividades/LAB-HAB/respuestas").json() == hab
    assert contar(aplicacion, modelos.RespuestaItem) == 2


@pytest.mark.parametrize("resultado_completo", [False, True])
def test_fallo_al_registrar_reinicio_revierte_anulacion_respuestas_y_progresos(cliente, aplicacion, monkeypatch, resultado_completo):
    from app.database import Base
    if resultado_completo:
        list(aplicar_cadena(cliente, "3" * 60))
    else:
        guardar(cliente, "LAB-RIA1", [{"item": "RIASEC-01", "opcion": 5}])

    def fotografia():
        with aplicacion.state.fabrica_sesiones() as sesion:
            return {nombre: sesion.execute(select(tabla)).all() for nombre, tabla in Base.metadata.tables.items()}

    antes = fotografia()
    original = acciones.registrar_eventos

    def fallar_despues_del_evento(sesion, cuenta, eventos, fecha):
        respuesta = original(sesion, cuenta, eventos, fecha)
        assert sesion.scalar(select(func.count()).select_from(modelos.RespuestaItem)) == 0
        assert sesion.scalar(select(func.count()).select_from(modelos.ProgresoActividad).where(
            modelos.ProgresoActividad.estado == modelos.EstadoProgreso.COMPLETADA)) == 0
        assert sesion.scalar(select(modelos.EventoUso.id).where(modelos.EventoUso.tipo == modelos.TipoEventoUso.REINICIA_INSTRUMENTO)) is not None
        if resultado_completo:
            resultado = sesion.scalar(select(modelos.ResultadoInstrumento))
            assert resultado.anulado_en == datetime(2026, 10, 2, 10)
        raise RuntimeError("Fallo forzado en reinicio")

    monkeypatch.setattr(acciones, "registrar_eventos", fallar_despues_del_evento)
    with pytest.raises(RuntimeError, match="Fallo forzado en reinicio"):
        reiniciar(cliente)
    assert fotografia() == antes
    verificar_invariantes_persistidos(aplicacion)
