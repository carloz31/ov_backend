from datetime import datetime, timedelta

import pytest
from sqlalchemy import func, select
from soporte_dominios import consultar_dominios, RUTAS_DOMINIO

from app import models as modelos
from app.database import crear_motor_bd
from app.services.motor.reglas import registrar_eventos
from app.services.registro.evaluacion import EvaluadorFalso, ResultadoEvaluacion
from datos.cargar import preparar_base
from datos.ocupaciones import RUTA_OCUPACIONES


FECHA = datetime(2026, 10, 1, 10)


def buscar(sesion, modelo, codigo):
    entidad = sesion.scalar(select(modelo).where(modelo.codigo == codigo))
    assert entidad is not None
    return entidad


def registrar(sesion, tipo, modelo=None, codigo=None, cuenta="est-ana", fecha=FECHA):
    """Prepara eventos para probar consultas; no sustituye acciones HTTP."""
    cuenta = buscar(sesion, modelos.Cuenta, cuenta)
    referencia = None if modelo is None else buscar(sesion, modelo, codigo).id
    nuevos = registrar_eventos(sesion, cuenta, [(tipo, referencia)], fecha)
    sesion.commit()
    return nuevos


def preparar_actividad_completada(sesion, codigo):
    ana = buscar(sesion, modelos.Cuenta, "est-ana")
    actividad = buscar(sesion, modelos.Actividad, codigo)
    sesion.add(modelos.ProgresoActividad(cuenta_id=ana.id, actividad_id=actividad.id,
                                         estado=modelos.EstadoProgreso.COMPLETADA))
    registrar(sesion, modelos.TipoEventoUso.COMPLETA_ACTIVIDAD, modelos.Actividad, codigo)


def preparar_ciudad(sesion):
    for codigo in ("ACT-01", "ACT-02", "ACT-03"):
        preparar_actividad_completada(sesion, codigo)
    registrar(sesion, modelos.TipoEventoUso.COMPLETA_BLOQUE, modelos.Bloque, "B0")
    for codigo in ("ACT-04", "ACT-05", "ACT-06", "ACT-12", "ACT-13"):
        preparar_actividad_completada(sesion, codigo)


def consultar_estado(cliente, cuenta="est-ana"):
    respuesta = cliente.get(f"/cuentas/{cuenta}/resumen")
    assert respuesta.status_code == 200
    return consultar_dominios(cliente, cuenta, resumen=respuesta.json())


def actividades_por_codigo(estado):
    return {actividad["codigo"]: actividad for bloque in estado["bloques"] for actividad in bloque["actividades"]}


def test_lista_cuentas_con_codigos_publicos(cliente):
    respuesta = cliente.get("/cuentas")
    assert respuesta.status_code == 200
    assert respuesta.json() == [
        {"codigo": "apo-rosa", "nombre": "Rosa", "rol": "APODERADO"},
        {"codigo": "est-ana", "nombre": "Ana", "rol": "ESTUDIANTE"},
        {"codigo": "est-luis", "nombre": "Luis", "rol": "ESTUDIANTE"},
    ]


def test_estado_refleja_progreso_y_nivel(sesion, cliente):
    preparar_actividad_completada(sesion, "ACT-01")
    actividades = actividades_por_codigo(consultar_estado(cliente))
    assert actividades["ACT-01"]["estado"] == "COMPLETADA"
    assert actividades["ACT-02"]["estado"] == "DISPONIBLE"
    assert actividades_por_codigo(consultar_estado(cliente, "est-luis"))["ACT-01"]["estado"] == "DISPONIBLE"
    preparar_actividad_completada(sesion, "ACT-02")
    preparar_actividad_completada(sesion, "ACT-03")
    registrar(sesion, modelos.TipoEventoUso.COMPLETA_BLOQUE, modelos.Bloque, "B0")
    estado = consultar_estado(cliente)
    assert estado["nivel_actual"] == {"numero": 2, "titulo": "Explorador de caminos"}
    assert [nivel["estado"] for nivel in estado["niveles"]] == [
        "OBTENIDO", "OBTENIDO", "BLOQUEADO", "BLOQUEADO", "BLOQUEADO",
    ]
    assert next(insignia for insignia in estado["insignias"]
                if insignia["codigo"] == "INS-PRIMER-PASO")["estado"] == "OBTENIDA"


def test_estado_ciudad_hereda_bloques_sin_perder_reglas(sesion, cliente):
    preparar_ciudad(sesion)
    estado = consultar_estado(cliente)
    actividades = actividades_por_codigo(estado)
    for codigo in ("HEL-01", "HEL-03", "CASO-01", "COMP-13"):
        assert actividades[codigo]["estado"] == "DISPONIBLE"
    for codigo in ("HEL-02", "CASO-02", "INV-01", "ACT-17"):
        assert actividades[codigo]["estado"] == "BLOQUEADA"
    assert estado["nivel_actual"]["numero"] == 3
    assert estado["conversaciones"]["estado"] == "BLOQUEADA"
    assert all(ficha["estado"] == "DISPONIBLE" for ficha in estado["fichas"]
               if ficha["codigo"] in ("FIC-PROFESIONES", "FIC-MERCADO"))
    assert all(pregunta["estado"] == "DISPONIBLE" for pregunta in estado["preguntas_diario"]
               if pregunta["codigo"] in ("PD-HISTORIA", "PD-ASPIRACIONES"))
    assert next(insignia for insignia in estado["insignias"]
                if insignia["codigo"] == "LOG-INCANSABLE")["estado"] == "OBTENIDA"


def test_actividad_de_bloque_bloqueado_se_muestra_bloqueada_aunque_tenga_progreso(sesion, cliente):
    ana = buscar(sesion, modelos.Cuenta, "est-ana")
    helena = buscar(sesion, modelos.Actividad, "HEL-01")
    sesion.add(modelos.ProgresoActividad(cuenta_id=ana.id, actividad_id=helena.id,
                                         estado=modelos.EstadoProgreso.COMPLETADA))
    sesion.commit()
    assert actividades_por_codigo(consultar_estado(cliente))["HEL-01"]["estado"] == "BLOQUEADA"


def test_estado_expone_en_curso_con_progreso_parcial(sesion, cliente):
    ana = buscar(sesion, modelos.Cuenta, "est-ana")
    bienvenida = buscar(sesion, modelos.Actividad, "ACT-01")
    sesion.add(modelos.ProgresoActividad(cuenta_id=ana.id, actividad_id=bienvenida.id,
                                         estado=modelos.EstadoProgreso.EN_CURSO))
    sesion.commit()
    assert actividades_por_codigo(consultar_estado(cliente))["ACT-01"]["estado"] == "EN_CURSO"


def test_pregunta_respondida_solo_depende_de_entradas_de_la_cuenta(sesion, cliente):
    preparar_ciudad(sesion)
    ana = buscar(sesion, modelos.Cuenta, "est-ana")
    luis = buscar(sesion, modelos.Cuenta, "est-luis")
    historia = buscar(sesion, modelos.PreguntaDiario, "PD-HISTORIA")
    aspiraciones = buscar(sesion, modelos.PreguntaDiario, "PD-ASPIRACIONES")
    sesion.add_all([
        modelos.EntradaDiario(cuenta_id=ana.id, origen=modelos.OrigenEntrada.GUIADA,
                             pregunta_id=historia.id, texto="Mi historia", fecha_hora=FECHA),
        modelos.EntradaDiario(cuenta_id=luis.id, origen=modelos.OrigenEntrada.GUIADA,
                             pregunta_id=aspiraciones.id, texto="Otra cuenta", fecha_hora=FECHA),
        modelos.EntradaDiario(cuenta_id=ana.id, origen=modelos.OrigenEntrada.LIBRE,
                             texto="Una entrada libre", fecha_hora=FECHA),
    ])
    sesion.commit()
    preguntas = {pregunta["codigo"]: pregunta for pregunta in consultar_estado(cliente)["preguntas_diario"]}
    assert preguntas["PD-HISTORIA"]["respondida"] is True
    assert preguntas["PD-HISTORIA"]["pregunta"] == historia.pregunta
    assert preguntas["PD-ASPIRACIONES"]["respondida"] is False


@pytest.mark.parametrize("codigo", ["LOG-PLUMA", "LOG-CONSTANCIA", "LOG-PENSADOR", "LOG-INCANSABLE"])
def test_progreso_oculto_responde_403_sin_explicacion(cliente, codigo):
    respuesta = cliente.get(f"/cuentas/est-ana/progreso/INSIGNIA/{codigo}")
    assert respuesta.status_code == 403
    assert set(respuesta.json()) == {"detail"}
    assert codigo not in respuesta.text


def test_logro_oculto_obtenido_revela_estado_y_progreso(sesion, cliente):
    registrar(sesion, modelos.TipoEventoUso.ESCRIBE_ENTRADA_LIBRE)
    estado = consultar_estado(cliente)
    pluma = next(insignia for insignia in estado["insignias"] if insignia["codigo"] == "LOG-PLUMA")
    assert pluma["nombre"] == "Pluma libre"
    assert pluma["descripcion"] and pluma["requisito"]
    assert pluma["estado"] == "OBTENIDA"
    assert len([insignia for insignia in estado["insignias"] if insignia["codigo"] == "???"]) == 3
    respuesta = cliente.get("/cuentas/est-ana/progreso/INSIGNIA/LOG-PLUMA")
    assert respuesta.status_code == 200
    progreso = respuesta.json()
    assert progreso["disponible"] is True
    assert progreso["reglas"][0]["cumplida"] is True
    assert progreso["reglas"][0]["condiciones"][0]["referencia"] is None
    assert "evaluador_especial" not in progreso["reglas"][0]


def test_progreso_compuesto_muestra_lo_que_falta(sesion, cliente):
    registrar(sesion, modelos.TipoEventoUso.COMPLETA_ACTIVIDAD, modelos.Actividad, "ACT-13")
    respuesta = cliente.get("/cuentas/est-ana/progreso/ACTIVIDAD/ACT-17")
    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "objetivo": {"tipo": "ACTIVIDAD", "codigo": "ACT-17"}, "disponible": False,
        "reglas": [{"regla": "R-ACT-17", "cumplida": False, "condiciones": [
            {"tipo_evento": "COMPLETA_ACTIVIDAD", "referencia": "ACT-13", "tipo_conteo": "EVENTOS",
             "actual": 1, "requerido": 1, "cumplida": True},
            {"tipo_evento": "COMPLETA_BLOQUE", "referencia": "C1", "tipo_conteo": "EVENTOS",
             "actual": 0, "requerido": 1, "cumplida": False},
        ]}],
    }


@pytest.mark.parametrize("tipo,codigo", [("ACTIVIDAD", "ACT-01"), ("NIVEL", "N1")])
def test_progreso_objetivo_sin_reglas(cliente, tipo, codigo):
    respuesta = cliente.get(f"/cuentas/est-ana/progreso/{tipo}/{codigo}")
    assert respuesta.status_code == 200
    assert respuesta.json() == {"objetivo": {"tipo": tipo, "codigo": codigo}, "disponible": True, "reglas": []}


def test_progreso_regla_cumplida_con_bloque_contenedor_pendiente(sesion, cliente):
    registrar(sesion, modelos.TipoEventoUso.COMPLETA_ACTIVIDAD, modelos.Actividad, "HEL-01")
    progreso = cliente.get("/cuentas/est-ana/progreso/ACTIVIDAD/HEL-02").json()
    assert progreso["disponible"] is False
    assert progreso["reglas"][0]["cumplida"] is True
    assert actividades_por_codigo(consultar_estado(cliente))["HEL-02"]["estado"] == "BLOQUEADA"


def test_progreso_conversaciones_muestra_alternativas_y_cuentas_independientes(sesion, cliente):
    registrar(sesion, modelos.TipoEventoUso.COMPLETA_ACTIVIDAD, modelos.Actividad, "ACT-13")
    registrar(sesion, modelos.TipoEventoUso.ESCRIBE_CARTA, modelos.VinculoFamiliar, "VIN-ANA")
    respuesta = cliente.get("/cuentas/est-ana/progreso/CONVERSACIONES/-")
    assert respuesta.status_code == 200
    progreso = respuesta.json()
    assert progreso["objetivo"] == {"tipo": "CONVERSACIONES", "codigo": "-"}
    assert progreso["disponible"] is True
    assert {regla["regla"]: regla["cumplida"] for regla in progreso["reglas"]} == {
        "R-FAM-APODERADO": False, "R-FAM-ESTUDIANTE": True,
    }
    assert consultar_estado(cliente)["conversaciones"]["estado"] == "DISPONIBLE"
    assert consultar_estado(cliente, "apo-rosa")["conversaciones"]["estado"] == "BLOQUEADA"


def test_progreso_evaluador_especial_se_muestra_separado(sesion, cliente):
    ruta = "/cuentas/est-ana/progreso/INSIGNIA/INS-EXPLORADOR"
    for codigo in ("CAR-ENF", "CAR-MED", "CAR-CIV"):
        registrar(sesion, modelos.TipoEventoUso.VISTA_CARRERA, modelos.Carrera, codigo)
    respuesta = cliente.get(ruta)
    assert respuesta.status_code == 200
    regla = respuesta.json()["reglas"][0]
    assert regla["condiciones"][0]["actual"] == 3
    assert regla["condiciones"][0]["cumplida"] is True
    assert regla["evaluador_especial"] == {"nombre": "carreras_de_3_familias", "cumplido": False}
    assert regla["cumplida"] is False
    assert respuesta.json()["disponible"] is False
    registrar(sesion, modelos.TipoEventoUso.VISTA_CARRERA, modelos.Carrera, "CAR-DIS")
    progreso = cliente.get(ruta).json()
    assert progreso["disponible"] is True
    assert progreso["reglas"][0]["cumplida"] is True
    assert progreso["reglas"][0]["evaluador_especial"]["cumplido"] is True


@pytest.mark.parametrize("ruta", [
    "/cuentas/no-existe/resumen", "/cuentas/no-existe/progreso/ACTIVIDAD/ACT-01",
    "/cuentas/no-existe/eventos", "/cuentas/no-existe/desbloqueos",
    "/cuentas/est-ana/progreso/ACTIVIDAD/ACT-NO-EXISTE",
    "/cuentas/est-ana/progreso/NIVEL/N0", "/cuentas/est-ana/progreso/NIVEL/N6",
    "/cuentas/est-ana/progreso/NIVEL/1", "/cuentas/est-ana/progreso/NIVEL/N01",
    "/cuentas/est-ana/progreso/CONVERSACIONES/CONV-01",
    "/cuentas/est-ana/progreso/ACTIVIDAD/ACT-P01",
    "/cuentas/apo-rosa/progreso/PREGUNTA_DIARIO/PD-HISTORIA",
    "/cuentas/apo-rosa/progreso/NIVEL/N1",
])
def test_consultas_inexistentes_o_de_otra_audiencia_devuelven_404(cliente, ruta):
    assert cliente.get(ruta).status_code == 404


def test_validacion_de_tipo_y_filtro(cliente):
    assert cliente.get("/cuentas/est-ana/progreso/NO_EXISTE/ACT-01").status_code == 422
    assert cliente.get("/cuentas/est-ana/desbloqueos?solo_no_vistos=incorrecto").status_code == 422
    assert cliente.post("/cuentas/no-existe/desbloqueos/marcar-vistos").status_code == 404


def test_linea_de_tiempo_por_fecha_y_cuenta_con_codigos(sesion, cliente):
    registrar(sesion, modelos.TipoEventoUso.COMPLETA_ACTIVIDAD, modelos.Actividad, "ACT-01", fecha=FECHA)
    registrar(sesion, modelos.TipoEventoUso.VISTA_CARRERA, modelos.Carrera, "CAR-ENF", fecha=FECHA + timedelta(days=1))
    registrar(sesion, modelos.TipoEventoUso.RESPUESTA_REFLEXIVA, fecha=FECHA + timedelta(days=1))
    registrar(sesion, modelos.TipoEventoUso.INGRESO, fecha=FECHA - timedelta(days=1))
    registrar(sesion, modelos.TipoEventoUso.INGRESO, cuenta="est-luis", fecha=FECHA + timedelta(days=2))
    respuesta = cliente.get("/cuentas/est-ana/eventos")
    assert respuesta.status_code == 200
    assert [(evento["tipo"], evento["referencia"]) for evento in respuesta.json()] == [
        ("RESPUESTA_REFLEXIVA", None), ("VISTA_CARRERA", "CAR-ENF"),
        ("COMPLETA_ACTIVIDAD", "ACT-01"), ("INGRESO", None),
    ]
    assert all(set(evento) == {"tipo", "referencia", "fecha_hora"} for evento in respuesta.json())
    assert len(cliente.get("/cuentas/est-luis/eventos").json()) == 1


def test_eventos_diario_y_check_in_no_exponen_ids(sesion, cliente):
    ana = buscar(sesion, modelos.Cuenta, "est-ana")
    entrada = modelos.EntradaDiario(cuenta_id=ana.id, origen=modelos.OrigenEntrada.LIBRE,
                                   texto="Una entrada", fecha_hora=FECHA)
    check_in = modelos.CheckIn(cuenta_id=ana.id, fecha=FECHA.date(), nivel_seguridad=3)
    sesion.add_all([entrada, check_in])
    sesion.flush()
    registrar_eventos(sesion, ana, [
        (modelos.TipoEventoUso.ESCRIBE_ENTRADA_DIARIO, entrada.id),
        (modelos.TipoEventoUso.ESCRIBE_ENTRADA_LIBRE, entrada.id),
        (modelos.TipoEventoUso.REGISTRA_CHECK_IN, check_in.id),
    ], FECHA)
    sesion.commit()
    respuesta = cliente.get("/cuentas/est-ana/eventos")
    assert respuesta.status_code == 200
    assert len(respuesta.json()) == 3
    assert all(evento["referencia"] is None for evento in respuesta.json())
    assert all("id_referencia" not in evento for evento in respuesta.json())


def test_desbloqueos_no_vistos_marcado_idempotente_y_aislado(sesion, cliente):
    registrar(sesion, modelos.TipoEventoUso.COMPLETA_ACTIVIDAD, modelos.Actividad, "ACT-01")
    registrar(sesion, modelos.TipoEventoUso.COMPLETA_ACTIVIDAD, modelos.Actividad, "ACT-01", cuenta="est-luis")
    ruta = "/cuentas/est-ana/desbloqueos"
    pendientes = cliente.get(f"{ruta}?solo_no_vistos=true").json()
    assert len(pendientes) == 1 and pendientes[0]["regla"] == "R-ACT-02"
    assert pendientes[0]["visto"] is False
    assert pendientes[0]["objetivo"]["codigo"] == "ACT-02"
    assert pendientes[0]["fecha_hora"] == FECHA.isoformat()
    assert cliente.post(f"{ruta}/marcar-vistos").json() == {"marcados": 1}
    assert cliente.get(f"{ruta}?solo_no_vistos=true").json() == []
    assert cliente.get(ruta).json()[0]["visto"] is True
    assert cliente.post(f"{ruta}/marcar-vistos").json() == {"marcados": 0}
    assert len(cliente.get("/cuentas/est-luis/desbloqueos?solo_no_vistos=true").json()) == 1
    registrar(sesion, modelos.TipoEventoUso.COMPLETA_ACTIVIDAD, modelos.Actividad, "ACT-02", fecha=FECHA + timedelta(days=1))
    assert [desbloqueo["regla"] for desbloqueo in cliente.get(ruta).json()] == ["R-ACT-03", "R-ACT-02"]
    assert [desbloqueo["regla"] for desbloqueo in cliente.get(f"{ruta}?solo_no_vistos=true").json()] == ["R-ACT-03"]


def test_gets_no_generan_eventos_ni_desbloqueos(sesion, cliente):
    ana = buscar(sesion, modelos.Cuenta, "est-ana")
    actividad = buscar(sesion, modelos.Actividad, "ACT-01")
    sesion.add(modelos.EventoUso(cuenta_id=ana.id, tipo=modelos.TipoEventoUso.COMPLETA_ACTIVIDAD,
                                 id_referencia=actividad.id, fecha_hora=FECHA))
    sesion.commit()
    for _ in range(2):
        for ruta in ("/cuentas", "/reglas", *(f"/cuentas/est-ana/{dominio}" for dominio in RUTAS_DOMINIO), "/cuentas/est-ana/eventos",
                     "/cuentas/est-ana/desbloqueos", "/cuentas/est-ana/progreso/ACTIVIDAD/ACT-02"):
            assert cliente.get(ruta).status_code == 200
    progreso = cliente.get("/cuentas/est-ana/progreso/ACTIVIDAD/ACT-02").json()
    assert progreso["reglas"][0]["cumplida"] is True
    assert progreso["disponible"] is False
    assert sesion.scalar(select(func.count()).select_from(modelos.EventoUso)) == 1
    assert sesion.scalar(select(func.count()).select_from(modelos.Desbloqueo)) == 0


def test_respuestas_no_exponen_ids_internos(sesion, cliente):
    preparar_ciudad(sesion)

    def verificar(valor):
        if isinstance(valor, dict):
            assert not any(clave == "id" or clave.startswith("id_") or clave.endswith("_id") for clave in valor)
            for contenido in valor.values():
                verificar(contenido)
        elif isinstance(valor, list):
            for contenido in valor:
                verificar(contenido)

    for ruta in ("/cuentas", "/reglas", *(f"/cuentas/est-ana/{dominio}" for dominio in RUTAS_DOMINIO), "/cuentas/est-ana/eventos",
                 "/cuentas/est-ana/desbloqueos", "/cuentas/est-ana/progreso/ACTIVIDAD/ACT-17"):
        respuesta = cliente.get(ruta)
        assert respuesta.status_code == 200
        verificar(respuesta.json())


# Mediciones reproducibles. Los presupuestos se exigirán tras optimizar; los
# conteos iniciales quedan en decisiones.md, no como expectativas del motor.
CADENA_MEDICION = "333322223322343333233333443333333333444433333433444433334433"
RUTA_HASTA_CIUDAD = ("ACT-01", "ACT-02", "ACT-03", "ACT-04", "ACT-05", "ACT-06", "ACT-12", "ACT-13")


def datos_medicion(actividad):
    return {"cuenta": "est-ana", "actividad": actividad, "fecha_hora": FECHA.isoformat()}


def preparar_peticion(cliente, ruta, datos):
    respuesta = cliente.post(ruta, json=datos)
    assert respuesta.status_code == 200, respuesta.text
    return respuesta.json()


def preparar_ruta_medicion(cliente):
    for actividad in RUTA_HASTA_CIUDAD:
        preparar_peticion(cliente, "/acciones/completar-actividad", datos_medicion(actividad))


def respuestas_medicion(actividad, desde, hasta, prefijo="RIASEC"):
    return {**datos_medicion(actividad), "respuestas": [
        {"item": f"{prefijo}-{numero:02}",
         "opcion": int(CADENA_MEDICION[numero - 1]) if prefijo == "RIASEC" else 1}
        for numero in range(desde, hasta + 1)
    ]}


def preparar_riasec_medicion(cliente):
    for parte in range(4):
        actividad = f"LAB-RIA{parte + 1}"
        preparar_peticion(cliente, "/acciones/responder-items",
                          respuestas_medicion(actividad, parte * 15 + 1, parte * 15 + 15))
        preparar_peticion(cliente, "/acciones/completar-actividad", datos_medicion(actividad))


def test_contador_cuenta_lecturas_escrituras_y_lotes_sin_preparacion(contador_consultas):
    motor_bd = crear_motor_bd("sqlite:///:memory:")
    try:
        contador = contador_consultas(motor_bd)
        with motor_bd.begin() as conexion:
            conexion.exec_driver_sql("CREATE TABLE prueba (numero INTEGER)")
            with contador:
                conexion.exec_driver_sql("SELECT 1")
                conexion.exec_driver_sql("INSERT INTO prueba VALUES (1)")
                conexion.exec_driver_sql("INSERT INTO prueba VALUES (?)", [(2,), (3,)])
                conexion.exec_driver_sql("UPDATE prueba SET numero = 4 WHERE numero = 3")
                conexion.exec_driver_sql("DELETE FROM prueba WHERE numero = 4")
            conexion.exec_driver_sql("SELECT 2")
        assert contador.cantidad == 5
        assert contador.por_tipo == {"SELECT": 1, "INSERT": 2, "UPDATE": 1, "DELETE": 1}
        assert [ejecucion.en_lote for ejecucion in contador.ejecuciones] == [False, False, True, False, False]
        assert "INSERT INTO prueba" in contador.diagnostico
    finally:
        motor_bd.dispose()


def test_contador_retira_listener_tras_error_y_se_puede_reutilizar(contador_consultas):
    motor_bd = crear_motor_bd("sqlite:///:memory:")
    try:
        contador = contador_consultas(motor_bd)
        with motor_bd.connect() as conexion:
            with pytest.raises(RuntimeError, match="Fallo de prueba"):
                with contador:
                    conexion.exec_driver_sql("SELECT 1")
                    raise RuntimeError("Fallo de prueba")
            conexion.exec_driver_sql("SELECT 2")
            assert contador.cantidad == 1
            with contador:
                conexion.exec_driver_sql("SELECT 3")
            assert contador.cantidad == 1
            assert contador.ejecuciones[0].sentencia == "SELECT 3"
    finally:
        motor_bd.dispose()


def test_contadores_aislan_motores_y_permiten_contextos_independientes(contador_consultas):
    primero = crear_motor_bd("sqlite:///:memory:")
    segundo = crear_motor_bd("sqlite:///:memory:")
    try:
        with primero.connect() as conexion, segundo.connect() as otra:
            with contador_consultas(primero) as exterior:
                conexion.exec_driver_sql("SELECT 1")
                otra.exec_driver_sql("SELECT 9")
                with contador_consultas(primero) as interior:
                    conexion.exec_driver_sql("SELECT 2")
                conexion.exec_driver_sql("SELECT 3")
            assert exterior.cantidad == 3
            assert interior.cantidad == 1
    finally:
        primero.dispose()
        segundo.dispose()


def test_medicion_base_estado_progreso_y_actividades(cliente, medidor_peticiones):
    medir = medidor_peticiones.medir
    estado = medir("estado_inicial", "GET", "/cuentas/est-ana/resumen")
    assert estado["nivel_actual"]["numero"] == 1
    medir("progreso_ACT17_inicial", "GET", "/cuentas/est-ana/progreso/ACTIVIDAD/ACT-17")
    simple = medir("completar_ACT01", "POST", "/acciones/completar-actividad", datos_medicion("ACT-01"))
    assert [nuevo["regla"] for nuevo in simple["nuevos_desbloqueos"]] == ["R-ACT-02"]
    for actividad in RUTA_HASTA_CIUDAD[1:-1]:
        preparar_peticion(cliente, "/acciones/completar-actividad", datos_medicion(actividad))
    ciudad = medir("completar_ACT13", "POST", "/acciones/completar-actividad", datos_medicion("ACT-13"))
    assert {f"R-CIUDAD-C{numero}" for numero in range(1, 5)} <= {
        nuevo["regla"] for nuevo in ciudad["nuevos_desbloqueos"]
    }
    estado = medir("estado_ciudad", "GET", "/cuentas/est-ana/resumen")
    assert estado["nivel_actual"]["numero"] == 3
    medir("progreso_ACT17_ciudad", "GET", "/cuentas/est-ana/progreso/ACTIVIDAD/ACT-17")


@pytest.mark.skipif(not RUTA_OCUPACIONES.is_file(), reason=f"Falta el catálogo O*NET: {RUTA_OCUPACIONES}")
def test_medicion_base_respuestas_calculo_y_resultado_riasec(cliente, medidor_peticiones):
    preparar_ruta_medicion(cliente)
    medir = medidor_peticiones.medir
    for parte in range(4):
        actividad = f"LAB-RIA{parte + 1}"
        datos = respuestas_medicion(actividad, parte * 15 + 1, parte * 15 + 15)
        if parte == 0:
            guardado = medir("responder_15_items_nuevos", "POST", "/acciones/responder-items", datos)
            assert guardado["progreso"] == {"estado": "EN_CURSO", "respondidos": 15, "total": 15}
            medir("responder_15_items_existentes", "POST", "/acciones/responder-items", datos)
        else:
            preparar_peticion(cliente, "/acciones/responder-items", datos)
        if parte == 3:
            completado = medir("completar_LAB_RIA4", "POST", "/acciones/completar-actividad", datos_medicion(actividad))
            assert completado["resultados_generados"] == [{"instrumento": "TEST-RIASEC", "aplicacion": "APL-RIASEC"}]
        else:
            preparar_peticion(cliente, "/acciones/completar-actividad", datos_medicion(actividad))
    resultado = medir("resultado_RIASEC", "GET", "/cuentas/est-ana/instrumentos/TEST-RIASEC/resultado")
    assert resultado["codigo_interes"] == {"codigo": "RIE", "hay_empate": False}
    assert len(resultado["coincidencias"]) == 10
    medir("responder_24_items_nuevos", "POST", "/acciones/responder-items",
          respuestas_medicion("LAB-HAB", 1, 24, prefijo="HAB"))
    medir("estado_avanzado", "GET", "/cuentas/est-ana/actividades")


@pytest.mark.skipif(not RUTA_OCUPACIONES.is_file(), reason=f"Falta el catálogo O*NET: {RUTA_OCUPACIONES}")
def test_medicion_base_otras_vistas_y_acciones(cliente, medidor_peticiones):
    medir = medidor_peticiones.medir
    medir("cuentas", "GET", "/cuentas")
    medir("catalogo_instrumentos", "GET", "/instrumentos")
    medir("items_RIA1", "GET", "/actividades/LAB-RIA1/items")
    medir("avance_inicial", "GET", "/cuentas/est-ana/instrumentos")
    medir("respuestas_iniciales", "GET", "/cuentas/est-ana/actividades/LAB-RIA1/respuestas")
    medir("resultado_pendiente", "GET", "/cuentas/est-ana/instrumentos/TEST-RIASEC/resultado", estado_http=409)
    medir("ingresar", "POST", "/acciones/ingresar", {"cuenta": "est-ana", "fecha_hora": FECHA.isoformat()})
    medir("responder_registro", "POST", "/acciones/responder-registro",
          {"cuenta": "est-ana", "clasificacion": "ADECUADA", "ampliada": False, "fecha_hora": FECHA.isoformat()})
    medir("entrada_libre", "POST", "/acciones/escribir-entrada",
          {"cuenta": "est-ana", "origen": "LIBRE", "texto": "Medición", "fecha_hora": FECHA.isoformat()})
    medir("check_in", "POST", "/acciones/check-in",
          {"cuenta": "est-ana", "nivel_seguridad": 3, "fecha_hora": FECHA.isoformat()})
    medir("ver_carrera", "POST", "/acciones/ver-carrera",
          {"cuenta": "est-ana", "carrera": "CAR-ENF", "fecha_hora": FECHA.isoformat()})
    medir("entrevista_dos_autores", "POST", "/acciones/publicar-entrevista",
          {"autores": ["est-ana", "est-luis"], "resumen": "Medición", "fecha_hora": FECHA.isoformat()})
    preparar_ruta_medicion(cliente)
    medir("resolver_caso_superado", "POST", "/acciones/resolver-caso", {**datos_medicion("CASO-01"), "puntaje": 85})
    medir("escribir_carta", "POST", "/acciones/escribir-carta", {"cuenta": "est-ana", "texto": "Medición"})
    medir("conversacion", "POST", "/acciones/completar-conversacion", {"cuenta": "est-ana", "conversacion": "CONV-01"})
    medir("desbloqueos", "GET", "/cuentas/est-ana/desbloqueos")
    medir("marcar_vistos", "POST", "/cuentas/est-ana/desbloqueos/marcar-vistos")
    preparar_riasec_medicion(cliente)
    medir("historial_un_resultado", "GET", "/cuentas/est-ana/instrumentos/TEST-RIASEC/historial")
    medir("respuestas_15", "GET", "/cuentas/est-ana/actividades/LAB-RIA1/respuestas")
    medir("avance_con_resultado", "GET", "/cuentas/est-ana/instrumentos")
    medir("reiniciar_instrumento", "POST", "/acciones/reiniciar-instrumento", {"cuenta": "est-ana", "instrumento": "TEST-RIASEC"})
    for actividad in ("LAB-AUT-E", "LAB-AUT-S"):
        preparar_peticion(cliente, "/acciones/responder-items", {
            **datos_medicion(actividad), "respuestas": [{"item": f"AUT-{numero:02}", "opcion": 2} for numero in range(1, 11)],
        })
        preparar_peticion(cliente, "/acciones/completar-actividad", datos_medicion(actividad))
    medir("comparacion_autopercepcion", "GET", "/cuentas/est-ana/instrumentos/TEST-AUTO/comparacion")


LIMITES_SQL = {
    "estado_inicial": 10, "estado_ciudad": 10, "estado_avanzado": 10,
    "progreso_ACT17_inicial": 8, "progreso_ACT17_ciudad": 8,
    "completar_ACT01": 15, "completar_ACT13": 15, "completar_LAB_RIA4": 20,
    "responder_15_items_nuevos": 10, "responder_15_items_existentes": 10,
    "responder_24_items_nuevos": 10, "resultado_RIASEC": 10,
    "cuentas": 1, "catalogo_instrumentos": 10, "items_RIA1": 10,
    "avance_inicial": 10, "respuestas_iniciales": 10, "resultado_pendiente": 10,
    "ingresar": 10, "responder_registro": 10, "entrada_libre": 10,
    "check_in": 10, "ver_carrera": 10, "entrevista_dos_autores": 10,
    "resolver_caso_superado": 12, "escribir_carta": 10, "conversacion": 12,
    "desbloqueos": 10, "marcar_vistos": 2, "historial_un_resultado": 10,
    "respuestas_15": 10, "avance_con_resultado": 10,
    "reiniciar_instrumento": 12, "comparacion_autopercepcion": 10,
    "guardar_posicion_registro": 4, "guardar_borrador_registro": 6,
    "enviar_registro": 12, "responder_seguimiento_registro": 12, "continuar_registro": 8,
    "items_registro": 1, "estado_registro": 4, "completar_REG_ACT08": 15,
    "evaluaciones_registro": 4,
}


@pytest.fixture(autouse=True)
def exigir_presupuestos_de_mediciones(request):
    """Exige límites también en los recorridos de fase 1, sin modificarlos."""
    if "medidor_peticiones" not in request.fixturenames:
        yield
        return
    medidor = request.getfixturevalue("medidor_peticiones")
    yield
    for nombre in medidor.mediciones:
        medidor.exigir_limite(nombre, LIMITES_SQL[nombre])


def peticion_contada(cliente, motor_bd, contador_consultas, metodo, ruta, datos=None, esperado=200):
    with contador_consultas(motor_bd) as contador:
        respuesta = cliente.request(metodo, ruta, json=datos)
    assert respuesta.status_code == esperado, respuesta.text
    return respuesta.json(), contador


@pytest.mark.parametrize("etapa", ["inicial", "ciudad"])
def test_consultas_no_crecen_con_100_reglas_y_500_eventos(
    cliente, aplicacion, tmp_path, contador_consultas, monkeypatch, etapa,
):
    from collections import Counter
    from fastapi.testclient import TestClient
    from app.main import crear_aplicacion
    from app.services.motor import reglas as motor

    preparar_base(f"sqlite:///{(tmp_path / 'ampliada.db').as_posix()}", 'demo', crear_tablas=True)
    ampliada = crear_aplicacion(f"sqlite:///{(tmp_path / 'ampliada.db').as_posix()}")
    with TestClient(ampliada) as otro_cliente:
        actividad = "ACT-01" if etapa == "inicial" else "ACT-13"
        objetivo = "FIC-PROFESIONES" if etapa == "inicial" else "FIC-MERCADO"
        if etapa == "ciudad":
            for otro in (cliente, otro_cliente):
                for codigo in RUTA_HASTA_CIUDAD[:-1]:
                    preparar_peticion(otro, "/acciones/completar-actividad", datos_medicion(codigo))
        with ampliada.state.fabrica_sesiones.begin() as sesion:
            cuenta = buscar(sesion, modelos.Cuenta, "est-ana")
            disparador = buscar(sesion, modelos.Actividad, actividad)
            ficha = buscar(sesion, modelos.Ficha, objetivo)
            referencias = [buscar(sesion, modelos.Actividad, codigo).id for codigo in ("ACT-01", "ACT-02")]
            for numero in range(100):
                sesion.add(modelos.ReglaDesbloqueo(
                    codigo=f"SINT-{numero:03}", nombre="Regla sintética activa",
                    tipo_objetivo=modelos.TipoObjetivo.FICHA, id_objetivo=ficha.id,
                    condiciones=[modelos.CondicionDesbloqueo(
                        tipo_evento=modelos.TipoEventoUso.COMPLETA_ACTIVIDAD, id_referencia=disparador.id,
                        tipo_conteo=modelos.TipoConteo.EVENTOS, cantidad_minima=1,
                    )],
                ))
            sesion.add_all([modelos.EventoUso(
                cuenta_id=cuenta.id, tipo=modelos.TipoEventoUso.COMPLETA_ACTIVIDAD,
                id_referencia=referencias[numero % 2], fecha_hora=FECHA + timedelta(days=numero % 7),
            ) for numero in range(500)])
        # La confirmación reconstruye la caché fuera del contador. No se hace
        # ninguna petición de calentamiento a la base ampliada.
        assert len(ampliada.state.motor_bd.cache_definiciones.actual.listar(modelos.ReglaDesbloqueo)) == 147
        for ruta, limite in (*((f"/cuentas/est-ana/{dominio}", 10) for dominio in RUTAS_DOMINIO),
                             (f"/cuentas/est-ana/progreso/FICHA/{objetivo}", 8)):
            _, normal = peticion_contada(cliente, aplicacion.state.motor_bd, contador_consultas, "GET", ruta)
            _, grande = peticion_contada(otro_cliente, ampliada.state.motor_bd, contador_consultas, "GET", ruta)
            assert normal.cantidad == grande.cantidad <= limite, grande.diagnostico

        original = motor.evaluar_regla
        evaluadas = []

        def observar(sesion, cuenta, regla):
            if regla.codigo.startswith("SINT-"):
                evaluadas.append(regla.codigo)
            return original(sesion, cuenta, regla)

        monkeypatch.setattr(motor, "evaluar_regla", observar)
        _, normal = peticion_contada(cliente, aplicacion.state.motor_bd, contador_consultas,
                                     "POST", "/acciones/completar-actividad", datos_medicion(actividad))
        respuesta, grande = peticion_contada(otro_cliente, ampliada.state.motor_bd, contador_consultas,
                                             "POST", "/acciones/completar-actividad", datos_medicion(actividad))
        assert normal.cantidad == grande.cantidad <= 15, grande.diagnostico
        assert len(evaluadas) == 100 and set(Counter(evaluadas).values()) == {1}
        sinteticas = [nuevo for nuevo in respuesta["nuevos_desbloqueos"] if nuevo["regla"].startswith("SINT-")]
        assert len(sinteticas) == 100
        assert all(nuevo["condiciones"][0]["cumplida"] for nuevo in sinteticas)
        with ampliada.state.fabrica_sesiones() as sesion:
            assert sesion.scalar(select(func.count()).select_from(modelos.Desbloqueo).join(modelos.ReglaDesbloqueo).where(
                modelos.ReglaDesbloqueo.codigo.startswith("SINT-"),
            )) == 100
            assert sesion.scalar(select(func.count()).select_from(modelos.EventoUso)) >= 501
        for otro, motor_bd in ((cliente, aplicacion.state.motor_bd), (otro_cliente, ampliada.state.motor_bd)):
            _, repetida = peticion_contada(otro, motor_bd, contador_consultas,
                                           "POST", "/acciones/completar-actividad", datos_medicion(actividad))
            assert repetida.cantidad <= 15


@pytest.mark.parametrize("modo", ["nuevas", "reemplazadas"])
def test_responder_un_item_o_24_cuesta_lo_mismo(cliente, aplicacion, contador_consultas, modo):
    cantidades = []
    for cuenta, cantidad in (("est-ana", 1), ("est-luis", 24)):
        if modo == "reemplazadas":
            preparar_peticion(cliente, "/acciones/responder-items", {
                **respuestas_medicion("LAB-HAB", 1, 24, prefijo="HAB"), "cuenta": cuenta,
            })
        datos = {**datos_medicion("LAB-HAB"), "cuenta": cuenta, "fecha_hora": "2026-10-02T10:00:00",
                 "respuestas": [{"item": f"HAB-{numero:02}", "opcion": 2} for numero in range(1, cantidad + 1)]}
        respuesta, contador = peticion_contada(cliente, aplicacion.state.motor_bd, contador_consultas,
                                               "POST", "/acciones/responder-items", datos)
        cantidades.append(contador.cantidad)
        assert contador.cantidad <= 10, contador.diagnostico
        assert len(respuesta["respuestas_guardadas"]) == cantidad
        assert respuesta["progreso"]["respondidos"] == (24 if modo == "reemplazadas" else cantidad)
        guardadas = cliente.get(f"/cuentas/{cuenta}/actividades/LAB-HAB/respuestas").json()["respuestas"]
        cambiadas = guardadas[:cantidad]
        assert all(respuesta["opcion"]["orden"] == 2 for respuesta in cambiadas)
        assert all(respuesta["actualizada_en"] == "2026-10-02T10:00:00" for respuesta in cambiadas)
        fecha_creada = "2026-10-01T10:00:00" if modo == "reemplazadas" else "2026-10-02T10:00:00"
        assert all(respuesta["creada_en"] == fecha_creada for respuesta in cambiadas)
    assert cantidades[0] == cantidades[1]


def test_lote_mixto_valida_antes_de_escribir_y_respeta_limite(cliente, aplicacion, contador_consultas):
    preparar_peticion(cliente, "/acciones/responder-items", respuestas_medicion("LAB-HAB", 1, 12, prefijo="HAB"))
    ruta = "/cuentas/est-ana/actividades/LAB-HAB/respuestas"
    antes = cliente.get(ruta).json()
    invalido = {**respuestas_medicion("LAB-HAB", 1, 24, prefijo="HAB"), "respuestas": [
        {"item": "HAB-01", "opcion": 2}, {"item": "HAB-13", "opcion": 2}, {"item": "NO-EXISTE", "opcion": 1},
    ]}
    _, contador = peticion_contada(cliente, aplicacion.state.motor_bd, contador_consultas,
                                   "POST", "/acciones/responder-items", invalido, esperado=409)
    assert contador.cantidad <= 10
    assert cliente.get(ruta).json() == antes
    valido = {**respuestas_medicion("LAB-HAB", 1, 24, prefijo="HAB"),
              "respuestas": [{"item": f"HAB-{numero:02}", "opcion": 2} for numero in range(1, 25)]}
    respuesta, contador = peticion_contada(cliente, aplicacion.state.motor_bd, contador_consultas,
                                           "POST", "/acciones/responder-items", valido)
    assert contador.cantidad <= 10, contador.diagnostico
    assert respuesta["progreso"]["respondidos"] == 24
    assert all(respuesta["opcion"]["orden"] == 2 for respuesta in cliente.get(ruta).json()["respuestas"])


def test_estado_no_crece_con_100_objetos_adicionales(cliente, aplicacion, contador_consultas):
    estado, antes = peticion_contada(cliente, aplicacion.state.motor_bd, contador_consultas,
                                     "GET", "/cuentas/est-ana/fichas")
    with aplicacion.state.fabrica_sesiones.begin() as sesion:
        sesion.add_all([modelos.Ficha(codigo=f"FIC-SINT-{numero:03}", titulo="Ficha sintética", contenido="Prueba")
                       for numero in range(100)])
    ampliado, despues = peticion_contada(cliente, aplicacion.state.motor_bd, contador_consultas,
                                         "GET", "/cuentas/est-ana/fichas")
    estado, ampliado = {"fichas": estado}, {"fichas": ampliado}
    assert despues.cantidad == antes.cantidad <= 10
    assert len(ampliado["fichas"]) == len(estado["fichas"]) + 100
    assert all(ficha["estado"] == "DISPONIBLE" for ficha in ampliado["fichas"] if ficha["codigo"].startswith("FIC-SINT-"))


def test_cache_aislada_detecta_commit_y_conserva_rollback(cliente, aplicacion, tmp_path, contador_consultas):
    from fastapi.testclient import TestClient
    from app.main import crear_aplicacion

    preparar_base(f"sqlite:///{(tmp_path / 'aislada.db').as_posix()}", 'demo', crear_tablas=True)
    otra = crear_aplicacion(f"sqlite:///{(tmp_path / 'aislada.db').as_posix()}")
    with TestClient(otra) as otro_cliente:
        cache = aplicacion.state.motor_bd.cache_definiciones
        original = cache.actual
        otra_original = otra.state.motor_bd.cache_definiciones.actual
        with pytest.raises(RuntimeError, match="Revertir definición"):
            with aplicacion.state.fabrica_sesiones.begin() as sesion:
                sesion.add(modelos.Ficha(codigo="FIC-REVERTIDA", titulo="Temporal", contenido="Temporal"))
                sesion.flush()
                raise RuntimeError("Revertir definición")
        assert cache.actual is original
        with aplicacion.state.fabrica_sesiones.begin() as sesion:
            actividad = buscar(sesion, modelos.Actividad, "ACT-01")
            sesion.add(modelos.ReglaDesbloqueo(
                codigo="SINT-CACHE", nombre="Requiere ingreso", tipo_objetivo=modelos.TipoObjetivo.ACTIVIDAD,
                id_objetivo=actividad.id, condiciones=[modelos.CondicionDesbloqueo(
                    tipo_evento=modelos.TipoEventoUso.INGRESO, tipo_conteo=modelos.TipoConteo.EVENTOS, cantidad_minima=1,
                )],
            ))
        assert cache.actual is not original
        assert otra.state.motor_bd.cache_definiciones.actual is otra_original
        estado, contador = peticion_contada(cliente, aplicacion.state.motor_bd, contador_consultas,
                                            "GET", "/cuentas/est-ana/actividades")
        estado = {"bloques": estado}
        assert contador.cantidad <= 10
        assert actividades_por_codigo(estado)["ACT-01"]["estado"] == "BLOQUEADA"
        assert actividades_por_codigo(consultar_dominios(otro_cliente))["ACT-01"]["estado"] == "DISPONIBLE"


def test_reinicio_conserva_cache_tras_exito_y_fallo(cliente, aplicacion, contador_consultas, monkeypatch):
    from app.services import demo as servicio_demo
    from sqlalchemy.exc import IntegrityError

    preparar_peticion(cliente, "/acciones/completar-actividad", datos_medicion("ACT-01"))
    antes = consultar_dominios(cliente)
    original = aplicacion.state.motor_bd.cache_definiciones.actual

    def fallar(sesion):
        servicio_demo_original(sesion)
        raise IntegrityError('DELETE', {}, RuntimeError('Fallo de prueba'))

    servicio_demo_original = servicio_demo.reiniciar_demo
    with monkeypatch.context() as parche:
        parche.setattr(servicio_demo, 'reiniciar_demo', fallar)
        assert cliente.post("/demo/reiniciar").status_code == 409
    assert aplicacion.state.motor_bd.cache_definiciones.actual is original
    assert consultar_dominios(cliente) == antes
    assert cliente.post("/demo/reiniciar").status_code == 200
    assert aplicacion.state.motor_bd.cache_definiciones.actual is original
    estado, contador = peticion_contada(cliente, aplicacion.state.motor_bd, contador_consultas,
                                        "GET", "/cuentas/est-ana/actividades")
    estado = {"bloques": estado}
    assert contador.cantidad <= 10
    assert actividades_por_codigo(estado)["ACT-01"]["estado"] == "DISPONIBLE"


def preparar_ultima_actividad_riasec(cliente):
    for parte in range(4):
        actividad = f"LAB-RIA{parte + 1}"
        preparar_peticion(cliente, "/acciones/responder-items",
                          respuestas_medicion(actividad, parte * 15 + 1, parte * 15 + 15))
        if parte < 3:
            preparar_peticion(cliente, "/acciones/completar-actividad", datos_medicion(actividad))


@pytest.mark.skipif(not RUTA_OCUPACIONES.is_file(), reason=f"Falta el catálogo O*NET: {RUTA_OCUPACIONES}")
def test_calculo_riasec_no_crece_con_100_ocupaciones(cliente, aplicacion, tmp_path, contador_consultas):
    from fastapi.testclient import TestClient
    from app.main import crear_aplicacion

    preparar_base(f"sqlite:///{(tmp_path / 'ocupaciones.db').as_posix()}", 'demo', crear_tablas=True)
    ampliada = crear_aplicacion(f"sqlite:///{(tmp_path / 'ocupaciones.db').as_posix()}")
    with TestClient(ampliada) as otro_cliente:
        with ampliada.state.fabrica_sesiones.begin() as sesion:
            dimensiones = list(sesion.scalars(select(modelos.Dimension).where(modelos.Dimension.codigo.in_(list("RIASEC"))).order_by(modelos.Dimension.orden)))
            for numero in range(100):
                ocupacion = modelos.Ocupacion(codigo_onet=f"SINT-{numero:03}", titulo="Ocupación sintética")
                sesion.add(ocupacion)
                sesion.flush()
                sesion.add_all([modelos.PuntajeOcupacion(ocupacion_id=ocupacion.id, dimension_id=dimension.id, valor=indice + 1)
                               for indice, dimension in enumerate(dimensiones)])
        cantidades = []
        for otro, motor_bd in ((cliente, aplicacion.state.motor_bd), (otro_cliente, ampliada.state.motor_bd)):
            preparar_ultima_actividad_riasec(otro)
            respuesta, contador = peticion_contada(otro, motor_bd, contador_consultas,
                                                   "POST", "/acciones/completar-actividad", datos_medicion("LAB-RIA4"))
            assert respuesta["resultados_generados"] == [{"instrumento": "TEST-RIASEC", "aplicacion": "APL-RIASEC"}]
            assert contador.cantidad <= 20
            assert sum("JOIN puntaje_ocupacion" in ejecucion.sentencia for ejecucion in contador.ejecuciones) == 1
            cantidades.append(contador.cantidad)
        assert cantidades[0] == cantidades[1]


@pytest.mark.skipif(not RUTA_OCUPACIONES.is_file(), reason=f"Falta el catálogo O*NET: {RUTA_OCUPACIONES}")
def test_historial_no_crece_con_20_resultados_extra(cliente, aplicacion, contador_consultas):
    preparar_riasec_medicion(cliente)
    ruta = "/cuentas/est-ana/instrumentos/TEST-RIASEC/historial"
    _, antes = peticion_contada(cliente, aplicacion.state.motor_bd, contador_consultas, "GET", ruta)
    with aplicacion.state.fabrica_sesiones.begin() as sesion:
        resultado = sesion.scalar(select(modelos.ResultadoInstrumento))
        dimensiones = list(sesion.scalars(select(modelos.ResultadoDimension)))
        coincidencias = list(sesion.scalars(select(modelos.Coincidencia)))
        for numero in range(20):
            copia = modelos.ResultadoInstrumento(cuenta_id=resultado.cuenta_id, aplicacion_id=resultado.aplicacion_id,
                calculado_en=FECHA - timedelta(days=numero + 1), anulado_en=FECHA, perfil_plano=False)
            sesion.add(copia)
            sesion.flush()
            sesion.add_all([modelos.ResultadoDimension(resultado_id=copia.id, dimension_id=dimension.dimension_id,
                puntaje=dimension.puntaje, puntaje_maximo=dimension.puntaje_maximo, porcentaje=dimension.porcentaje) for dimension in dimensiones])
            sesion.add_all([modelos.Coincidencia(resultado_id=copia.id, ocupacion_id=afin.ocupacion_id,
                posicion=afin.posicion, correlacion=afin.correlacion, ajuste=afin.ajuste) for afin in coincidencias])
    historial, despues = peticion_contada(cliente, aplicacion.state.motor_bd, contador_consultas, "GET", ruta)
    assert despues.cantidad == antes.cantidad <= 10
    assert len(historial) == 21
    assert all(len(resultado["coincidencias"]) == 10 for resultado in historial)


def test_publicar_entrevista_no_crece_con_20_autores(cliente, aplicacion, contador_consultas):
    _, antes = peticion_contada(cliente, aplicacion.state.motor_bd, contador_consultas,
                               "POST", "/acciones/publicar-entrevista", {"autores": ["est-ana", "est-luis"], "resumen": "Dos autores"})
    codigos = [f"est-sint-{numero:02}" for numero in range(20)]
    with aplicacion.state.fabrica_sesiones.begin() as sesion:
        sesion.add_all([modelos.Cuenta(codigo=codigo, nombre=codigo, rol=modelos.Rol.ESTUDIANTE) for codigo in codigos])
    respuesta, despues = peticion_contada(cliente, aplicacion.state.motor_bd, contador_consultas,
                                          "POST", "/acciones/publicar-entrevista", {"autores": codigos, "resumen": "Veinte autores"})
    assert despues.cantidad == antes.cantidad <= 10
    assert list(respuesta["por_cuenta"]) == codigos
    assert all([nuevo["regla"] for nuevo in autor["nuevos_desbloqueos"]] == ["R-INS-INVESTIGADOR"]
               for autor in respuesta["por_cuenta"].values())


def test_completar_no_crece_con_mas_aplicaciones(cliente, aplicacion, tmp_path, contador_consultas):
    from fastapi.testclient import TestClient
    from app.main import crear_aplicacion

    preparar_base(f"sqlite:///{(tmp_path / 'aplicaciones.db').as_posix()}", 'demo', crear_tablas=True)
    ampliada = crear_aplicacion(f"sqlite:///{(tmp_path / 'aplicaciones.db').as_posix()}")
    with TestClient(ampliada) as otro_cliente:
        with ampliada.state.fabrica_sesiones.begin() as sesion:
            instrumento = buscar(sesion, modelos.Instrumento, "TEST-HAB")
            actividad = buscar(sesion, modelos.Actividad, "LAB-HAB")
            for numero in range(5):
                nueva = modelos.Aplicacion(codigo=f"APL-SINT-{numero}", nombre="Aplicación adicional", instrumento_id=instrumento.id)
                sesion.add(nueva)
                sesion.flush()
                sesion.add(modelos.AplicacionActividad(aplicacion_id=nueva.id, actividad_id=actividad.id))
        cantidades = []
        for otro, motor_bd, esperados in ((cliente, aplicacion.state.motor_bd, 1), (otro_cliente, ampliada.state.motor_bd, 6)):
            preparar_peticion(otro, "/acciones/responder-items", respuestas_medicion("LAB-HAB", 1, 24, prefijo="HAB"))
            respuesta, contador = peticion_contada(otro, motor_bd, contador_consultas,
                                                   "POST", "/acciones/completar-actividad", datos_medicion("LAB-HAB"))
            assert len(respuesta["resultados_generados"]) == esperados
            cantidades.append(contador.cantidad)
        assert cantidades[0] == cantidades[1] <= 20


# Registro: presupuestos de la petición completa, con preparación fuera del contador.
TEXTO_REGISTRO_SQL = "Quiero practicar la asertividad al opinar en los trabajos de mi colegio."
ITEMS_REGISTRO_SQL = ('REG-HAB-1', 'REG-HAB-2', 'REG-HAB-3')
RUTA_ESTADO_REGISTRO_SQL = '/cuentas/est-ana/actividades/REG-ACT08/registro'


@pytest.fixture
def registro_sql(cliente, aplicacion):
    assert cliente.post('/demo/reiniciar').status_code == 200
    assert isinstance(aplicacion.state.evaluador_respuestas, EvaluadorFalso)


def datos_registro_sql(texto=TEXTO_REGISTRO_SQL, item='REG-HAB-1'):
    return {**datos_medicion('REG-ACT08'), 'item': item, 'texto': texto}


def preparar_registro_final(cliente):
    for item in ITEMS_REGISTRO_SQL:
        preparar_peticion(cliente, '/acciones/registro/enviar', datos_registro_sql(item=item))


def preparar_seguimiento_registro(cliente, orden=1, item='REG-HAB-1'):
    preparar_peticion(cliente, '/acciones/registro/enviar', datos_registro_sql('Inicial [falta:C2]', item))
    if orden == 2:
        preparar_peticion(cliente, '/acciones/registro/responder-seguimiento', datos_registro_sql('Turno 1 [vaga]', item))


def preparar_final_registro_con_turnos(cliente, item):
    preparar_seguimiento_registro(cliente, orden=2, item=item)
    preparar_peticion(cliente, '/acciones/registro/responder-seguimiento', datos_registro_sql(item=item))


@pytest.mark.parametrize('modo', ['nuevo', 'existente', 'completada'])
def test_limite_sql_guardar_posicion_registro(cliente, registro_sql, medidor_peticiones, modo):
    datos = {**datos_medicion('REG-ACT08'), 'posicion': 'plan'}
    if modo == 'existente':
        preparar_peticion(cliente, '/acciones/guardar-posicion', {**datos, 'posicion': 'explicacion'})
    elif modo == 'completada':
        preparar_registro_final(cliente)
        preparar_peticion(cliente, '/acciones/completar-actividad', datos_medicion('REG-ACT08'))
    respuesta = medidor_peticiones.medir('guardar_posicion_registro', 'POST', '/acciones/guardar-posicion', datos)
    assert respuesta == {'posicion': 'plan', 'estado': 'COMPLETADA' if modo == 'completada' else 'EN_CURSO'}


@pytest.mark.parametrize('modo', ['nuevo', 'existente', 'pendiente', 'llm_turno_1', 'llm_turno_2'])
def test_limite_sql_guardar_borrador_registro(cliente, registro_sql, medidor_peticiones, modo):
    if modo.startswith('llm_turno_'):
        preparar_seguimiento_registro(cliente, orden=int(modo[-1]))
    elif modo != 'nuevo':
        accion = 'guardar-borrador' if modo == 'existente' else 'enviar'
        preparar_peticion(cliente, f'/acciones/registro/{accion}', datos_registro_sql('Corto [falla]'))
    respuesta = medidor_peticiones.medir('guardar_borrador_registro', 'POST',
                                         '/acciones/registro/guardar-borrador', datos_registro_sql('Nuevo borrador'))
    assert respuesta['estado'] == ('PENDIENTE_SEGUIMIENTO' if modo in ('pendiente', 'llm_turno_1', 'llm_turno_2') else 'BORRADOR')


class EvaluadorFalloSQL(EvaluadorFalso):
    def __init__(self, tipo):
        super().__init__()
        self.tipo = tipo

    def evaluar(self, contexto):
        self.contextos.append(contexto)
        if self.tipo == 'timeout':
            raise TimeoutError('Timeout simulado')
        return ResultadoEvaluacion(clasificacion='ADECUADA', criterios_faltantes=['C1'],
                                   pregunta=None, requiere_atencion=False)


@pytest.mark.parametrize('previo', ['ausente', 'progreso', 'borrador', 'pendiente'])
@pytest.mark.parametrize('resultado', ['minimo', 'adecuada', 'adecuada_corta', 'vaga', 'atencion', 'fallo', 'timeout', 'invalido'])
def test_limite_sql_envio_registro_cualquier_origen(
        cliente, aplicacion, registro_sql, medidor_peticiones, previo, resultado):
    if previo == 'progreso':
        preparar_peticion(cliente, '/acciones/guardar-posicion', {**datos_medicion('REG-ACT08'), 'posicion': 'plan'})
    elif previo in ('borrador', 'pendiente'):
        preparar_peticion(cliente, '/acciones/registro/' + ('guardar-borrador' if previo == 'borrador' else 'enviar'),
                          datos_registro_sql('Inicial [vaga]'))
    if resultado in ('timeout', 'invalido'):
        aplicacion.state.evaluador_respuestas = EvaluadorFalloSQL(resultado)
    textos = {'minimo': 'Corto [falla]', 'adecuada': TEXTO_REGISTRO_SQL, 'adecuada_corta': 'Asertividad', 'vaga': TEXTO_REGISTRO_SQL + '[vaga]',
              'atencion': TEXTO_REGISTRO_SQL + '[atencion]', 'fallo': TEXTO_REGISTRO_SQL + '[falla]',
              'timeout': TEXTO_REGISTRO_SQL, 'invalido': TEXTO_REGISTRO_SQL}
    accion = 'responder-seguimiento' if previo == 'pendiente' else 'enviar'
    presupuesto = 'responder_seguimiento_registro' if previo == 'pendiente' else 'enviar_registro'
    respuesta = medidor_peticiones.medir(presupuesto, 'POST', f'/acciones/registro/{accion}',
                                         datos_registro_sql(textos[resultado]))
    pendiente = resultado == 'vaga' or (previo != 'pendiente' and resultado == 'minimo')
    assert respuesta['estado'] == ('PENDIENTE_SEGUIMIENTO' if pendiente else 'FINAL')
    assert len(respuesta['eventos_registrados']) == int(not pendiente and (previo == 'pendiente' or resultado in ('adecuada', 'adecuada_corta', 'atencion')))
    historial = cliente.get('/demo/registro/est-ana/REG-ACT08/evaluaciones').json()
    origen = 'RESPALDO_LONGITUD' if resultado == 'minimo' else ('RESPALDO_LONGITUD' if resultado in ('fallo', 'timeout', 'invalido') else 'LLM')
    assert historial[-1]['origen'] == origen and historial[-1]['numero'] == (2 if previo == 'pendiente' else 1)


def test_limite_sql_editar_final_registro(cliente, aplicacion, registro_sql, medidor_peticiones):
    preparar_peticion(cliente, '/acciones/registro/enviar', datos_registro_sql())
    llamadas = len(aplicacion.state.evaluador_respuestas.contextos)
    respuesta = medidor_peticiones.medir('enviar_registro', 'POST', '/acciones/registro/enviar',
                                         datos_registro_sql('Edición breve [falla]'))
    assert respuesta['estado'] == 'FINAL' and respuesta['eventos_registrados'] == []
    assert len(aplicacion.state.evaluador_respuestas.contextos) == llamadas


@pytest.mark.parametrize('orden', [1, 2])
@pytest.mark.parametrize('resultado', ['adecuada', 'vaga', 'atencion', 'fallo', 'timeout', 'invalido'])
def test_limite_sql_seguimiento_con_otras_conversaciones_finales(
        cliente, aplicacion, registro_sql, medidor_peticiones, orden, resultado):
    for item in ITEMS_REGISTRO_SQL[1:]:
        preparar_final_registro_con_turnos(cliente, item)
    preparar_seguimiento_registro(cliente, orden=orden)
    preparar_peticion(cliente, '/acciones/registro/guardar-borrador', datos_registro_sql('Borrador del turno actual'))
    if resultado in ('timeout', 'invalido'):
        aplicacion.state.evaluador_respuestas = EvaluadorFalloSQL(resultado)
    marcadores = {'vaga': '[vaga]', 'atencion': '[atencion]', 'fallo': '[falla]'}
    texto = TEXTO_REGISTRO_SQL + marcadores.get(resultado, '')
    respuesta = medidor_peticiones.medir('responder_seguimiento_registro', 'POST',
        '/acciones/registro/responder-seguimiento', datos_registro_sql(texto))
    pendiente = resultado == 'vaga' and orden == 1
    assert respuesta['estado'] == ('PENDIENTE_SEGUIMIENTO' if pendiente else 'FINAL')
    assert len(respuesta['eventos_registrados']) == int(not pendiente)
    contexto = aplicacion.state.evaluador_respuestas.contextos[-1]
    assert len(contexto.respuestas_anteriores) == 2
    assert all(len(anterior.conversacion.turnos) == 2 for anterior in contexto.respuestas_anteriores)
    assert contexto.conversacion.turnos[-1].respuesta == texto
    historial = cliente.get('/demo/registro/est-ana/REG-ACT08/evaluaciones').json()
    ultima = next(e for e in reversed(historial) if e['item'] == 'REG-HAB-1')
    assert ultima['numero'] == orden + 1
    assert ultima['origen'] == ('RESPALDO_LONGITUD' if resultado in ('fallo', 'timeout', 'invalido') else 'LLM')


@pytest.mark.parametrize('con_borrador', [False, True])
def test_limite_sql_seguimiento_generico_sin_nueva_evaluacion(
        cliente, aplicacion, registro_sql, medidor_peticiones, con_borrador):
    preparar_peticion(cliente, '/acciones/registro/enviar', datos_registro_sql('Corto [falla]'))
    if con_borrador:
        preparar_peticion(cliente, '/acciones/registro/guardar-borrador', datos_registro_sql('Borrador recuperado'))
    llamadas = len(aplicacion.state.evaluador_respuestas.contextos)
    historial = cliente.get('/demo/registro/est-ana/REG-ACT08/evaluaciones').json()
    respuesta = medidor_peticiones.medir('responder_seguimiento_registro', 'POST',
        '/acciones/registro/responder-seguimiento', datos_registro_sql('Sí [falla]'))
    assert respuesta['estado'] == 'FINAL' and len(respuesta['eventos_registrados']) == 1
    assert len(aplicacion.state.evaluador_respuestas.contextos) == llamadas
    assert cliente.get('/demo/registro/est-ana/REG-ACT08/evaluaciones').json() == historial


@pytest.mark.parametrize('orden', [1, 2])
def test_limite_sql_editar_turno_final_sin_nueva_evaluacion(
        cliente, aplicacion, registro_sql, medidor_peticiones, orden):
    preparar_final_registro_con_turnos(cliente, 'REG-HAB-1')
    llamadas = len(aplicacion.state.evaluador_respuestas.contextos)
    historial = cliente.get('/demo/registro/est-ana/REG-ACT08/evaluaciones').json()
    respuesta = medidor_peticiones.medir('responder_seguimiento_registro', 'POST',
        '/acciones/registro/responder-seguimiento', datos_registro_sql('Edición [falla]') | {'orden': orden})
    assert respuesta['estado'] == 'FINAL' and respuesta['eventos_registrados'] == []
    assert respuesta['conversacion'][orden * 2]['texto'] == 'Edición [falla]'
    assert len(aplicacion.state.evaluador_respuestas.contextos) == llamadas
    assert cliente.get('/demo/registro/est-ana/REG-ACT08/evaluaciones').json() == historial


@pytest.mark.parametrize('orden', [0, 1, 2], ids=['inicial', 'turno_1', 'turno_2'])
def test_contador_del_envio_incluye_ambas_transacciones_y_excluye_sql_al_evaluar(
        cliente, aplicacion, registro_sql, contador_consultas, orden):
    if orden:
        preparar_seguimiento_registro(cliente, orden=orden)
    contador = contador_consultas(aplicacion.state.motor_bd)
    observadas = []
    class EvaluadorObservaSQL(EvaluadorFalso):
        def evaluar(self, contexto):
            assert aplicacion.state.motor_bd.pool.checkedout() == 0
            observadas.append(contador.cantidad)
            resultado = super().evaluar(contexto)
            assert contador.cantidad == observadas[-1]
            return resultado
    aplicacion.state.evaluador_respuestas = EvaluadorObservaSQL()
    with contador:
        accion = 'responder-seguimiento' if orden else 'enviar'
        respuesta = cliente.post(f'/acciones/registro/{accion}', json=datos_registro_sql())
    assert respuesta.status_code == 200
    assert respuesta.json()['eventos_registrados'][0]['tipo'] == 'RESPUESTA_REFLEXIVA'
    presupuesto = 'responder_seguimiento_registro' if orden else 'enviar_registro'
    assert len(observadas) == 1 and 0 < observadas[0] < contador.cantidad <= LIMITES_SQL[presupuesto]
    lecturas_cuenta = [e for e in contador.ejecuciones if 'FROM cuenta' in e.sentencia]
    lecturas_respuestas = [e for e in contador.ejecuciones if 'LEFT OUTER JOIN respuesta_registro' in e.sentencia]
    assert len(lecturas_cuenta) == len(lecturas_respuestas) == 2
    assert any(e.sentencia.startswith('INSERT INTO evaluacion_respuesta ') for e in contador.ejecuciones)


@pytest.mark.parametrize('origen', ['minimo', 'llm', 'llm_turno_2'])
def test_limite_sql_continuar_registro(cliente, registro_sql, medidor_peticiones, origen):
    if origen == 'llm_turno_2':
        preparar_seguimiento_registro(cliente, orden=2)
        preparar_peticion(cliente, '/acciones/registro/guardar-borrador', datos_registro_sql('Borrador por descartar'))
    else:
        preparar_peticion(cliente, '/acciones/registro/enviar',
                          datos_registro_sql('Corto [falla]' if origen == 'minimo' else TEXTO_REGISTRO_SQL + '[vaga]'))
    datos = datos_medicion('REG-ACT08') | {'item': 'REG-HAB-1'}
    respuesta = medidor_peticiones.medir('continuar_registro', 'POST', '/acciones/registro/continuar-sin-responder', datos)
    assert respuesta['estado'] == 'FINAL' and len(respuesta['eventos_registrados']) == int(origen == 'llm_turno_2')


def test_limite_sql_items_registro_desde_cache(cliente, registro_sql, medidor_peticiones):
    items = medidor_peticiones.medir('items_registro', 'GET', '/actividades/REG-ACT08/items-registro')
    assert [item['codigo'] for item in items] == list(ITEMS_REGISTRO_SQL)
    assert all('criterios' not in item for item in items)


@pytest.mark.parametrize('estado', ['sin_progreso', 'posicion', 'borrador', 'pendiente', 'final', 'completada',
                                  'llm_turno_1', 'llm_turno_2', 'final_con_turnos', 'completada_con_turnos'])
def test_limite_sql_estado_registro(cliente, registro_sql, medidor_peticiones, estado):
    if estado.startswith('llm_turno_'):
        preparar_seguimiento_registro(cliente, orden=int(estado[-1]))
        preparar_peticion(cliente, '/acciones/registro/guardar-borrador', datos_registro_sql('Borrador visible'))
    elif estado in ('final_con_turnos', 'completada_con_turnos'):
        for item in ITEMS_REGISTRO_SQL:
            preparar_final_registro_con_turnos(cliente, item)
        if estado == 'completada_con_turnos':
            preparar_peticion(cliente, '/acciones/completar-actividad', datos_medicion('REG-ACT08'))
    elif estado == 'posicion':
        preparar_peticion(cliente, '/acciones/guardar-posicion', {**datos_medicion('REG-ACT08'), 'posicion': 'plan'})
    elif estado in ('borrador', 'pendiente', 'final'):
        accion = 'guardar-borrador' if estado == 'borrador' else 'enviar'
        preparar_peticion(cliente, f'/acciones/registro/{accion}',
                          datos_registro_sql('Corto [falla]' if estado == 'pendiente' else TEXTO_REGISTRO_SQL))
    elif estado == 'completada':
        preparar_registro_final(cliente)
        preparar_peticion(cliente, '/acciones/completar-actividad', datos_medicion('REG-ACT08'))
    registro = medidor_peticiones.medir('estado_registro', 'GET', RUTA_ESTADO_REGISTRO_SQL)
    if estado == 'pendiente':
        assert registro['respuestas'][0]['conversacion'][-1]['tipo'] == 'pregunta'
    elif estado.startswith('llm_turno_'):
        assert registro['respuestas'][0]['estado'] == 'PENDIENTE_SEGUIMIENTO'
        assert registro['respuestas'][0]['conversacion'][-1] == {
            'tipo': 'respuesta', 'orden': int(estado[-1]), 'texto': 'Borrador visible', 'borrador': True}
    elif estado in ('final_con_turnos', 'completada_con_turnos'):
        assert len(registro['respuestas']) == 3
        assert all(len(r['conversacion']) == 5 for r in registro['respuestas'])
    else:
        assert all(len(r['conversacion']) == 1 for r in registro['respuestas'])


@pytest.mark.parametrize('modo', ['vacio', 'primeros', 'dos_intentos', 'tres_evaluaciones'])
def test_limite_sql_evaluaciones_registro(cliente, registro_sql, medidor_peticiones, modo):
    if modo != 'vacio':
        for item in ITEMS_REGISTRO_SQL:
            if modo == 'tres_evaluaciones':
                preparar_final_registro_con_turnos(cliente, item)
                continue
            if modo == 'dos_intentos':
                preparar_peticion(cliente, '/acciones/registro/enviar', datos_registro_sql('Inicial [vaga]', item))
            accion = 'responder-seguimiento' if modo == 'dos_intentos' else 'enviar'
            preparar_peticion(cliente, f'/acciones/registro/{accion}', datos_registro_sql(item=item))
    historial = medidor_peticiones.medir('evaluaciones_registro', 'GET', '/demo/registro/est-ana/REG-ACT08/evaluaciones')
    assert len(historial) == {'vacio': 0, 'primeros': 3, 'dos_intentos': 6, 'tres_evaluaciones': 9}[modo]


@pytest.mark.parametrize('modo', ['faltantes', 'primera', 'rehacer', 'pendiente_turno_2',
                                'primera_con_turnos', 'rehacer_con_turnos'])
def test_limite_sql_completar_registro(cliente, registro_sql, medidor_peticiones, modo):
    if modo == 'pendiente_turno_2':
        for item in ITEMS_REGISTRO_SQL[:2]:
            preparar_final_registro_con_turnos(cliente, item)
        preparar_seguimiento_registro(cliente, orden=2, item='REG-HAB-3')
    elif modo.endswith('_con_turnos'):
        for item in ITEMS_REGISTRO_SQL:
            preparar_final_registro_con_turnos(cliente, item)
        if modo == 'rehacer_con_turnos':
            preparar_peticion(cliente, '/acciones/completar-actividad', datos_medicion('REG-ACT08'))
    elif modo != 'faltantes':
        preparar_registro_final(cliente)
        if modo == 'rehacer':
            preparar_peticion(cliente, '/acciones/completar-actividad', datos_medicion('REG-ACT08'))
    faltantes = modo in ('faltantes', 'pendiente_turno_2')
    respuesta = medidor_peticiones.medir('completar_REG_ACT08', 'POST', '/acciones/completar-actividad',
                                         datos_medicion('REG-ACT08'), estado_http=409 if faltantes else 200)
    if faltantes:
        assert respuesta['detail']['items_faltantes'] == (['REG-HAB-3'] if modo == 'pendiente_turno_2' else list(ITEMS_REGISTRO_SQL))
    else:
        assert [e['tipo'] for e in respuesta['eventos_registrados']] == (
            ['COMPLETA_ACTIVIDAD', 'COMPLETA_BLOQUE'] if modo in ('primera', 'primera_con_turnos') else ['COMPLETA_ACTIVIDAD'])


@pytest.mark.parametrize('modo', [
    'ausente', 'borrador', 'ampliacion', 'minimo', 'vaga', 'fallo', 'atencion', 'edicion',
    'seguimiento_1_vaga', 'seguimiento_1_fallo', 'seguimiento_1_timeout',
    'seguimiento_2_adecuada', 'seguimiento_2_vaga', 'seguimiento_2_fallo',
    'seguimiento_2_atencion', 'seguimiento_2_invalido', 'seguimiento_generico',
    'edicion_turno_1', 'edicion_turno_2',
])
def test_registro_sql_no_crece_con_100_reglas_reflexivas_y_500_eventos(
        cliente, aplicacion, registro_sql, tmp_path, contador_consultas, monkeypatch, modo):
    from collections import Counter
    from fastapi.testclient import TestClient
    from app.main import crear_aplicacion
    from app.services.motor import reglas as motor

    preparar_base(f"sqlite:///{(tmp_path / 'registro-ampliado.db').as_posix()}", 'demo', crear_tablas=True)
    ampliada = crear_aplicacion(f"sqlite:///{(tmp_path / 'registro-ampliado.db').as_posix()}")
    with TestClient(ampliada) as otro_cliente:
        for otro in (cliente, otro_cliente):
            if modo.startswith(('seguimiento_', 'edicion_turno_')):
                # La lectura agrupa además dos conversaciones FINAL con dos turnos cada una.
                for item in ITEMS_REGISTRO_SQL[1:]:
                    preparar_final_registro_con_turnos(otro, item)
                if modo == 'seguimiento_generico':
                    preparar_peticion(otro, '/acciones/registro/enviar', datos_registro_sql('Corto [falla]'))
                elif modo.startswith('edicion_turno_'):
                    preparar_final_registro_con_turnos(otro, 'REG-HAB-1')
                else:
                    preparar_seguimiento_registro(otro, orden=int(modo.split('_')[1]))
                    preparar_peticion(otro, '/acciones/registro/guardar-borrador', datos_registro_sql('Borrador pendiente'))
            elif modo in ('borrador', 'ampliacion', 'edicion'):
                accion = 'guardar-borrador' if modo == 'borrador' else 'enviar'
                texto = 'Inicial [vaga]' if modo == 'ampliacion' else (TEXTO_REGISTRO_SQL if modo == 'edicion' else 'Corto [falla]')
                preparar_peticion(otro, f'/acciones/registro/{accion}', datos_registro_sql(texto))
        for app in (aplicacion, ampliada):
            with app.state.fabrica_sesiones.begin() as sesion:
                cuenta = buscar(sesion, modelos.Cuenta, 'est-ana')
                # La próxima reflexión cumple la regla original también en la base normal.
                sesion.add_all([modelos.EventoUso(cuenta_id=cuenta.id, tipo=modelos.TipoEventoUso.RESPUESTA_REFLEXIVA,
                    id_referencia=None, fecha_hora=FECHA) for _ in range(2)])
                if app is ampliada:
                    ficha = buscar(sesion, modelos.Ficha, 'FIC-PROFESIONES')
                    sesion.add_all([modelos.ReglaDesbloqueo(codigo=f'REG-SINT-{numero:03}',
                        nombre='Regla reflexiva sintética', tipo_objetivo=modelos.TipoObjetivo.FICHA, id_objetivo=ficha.id,
                        condiciones=[modelos.CondicionDesbloqueo(tipo_evento=modelos.TipoEventoUso.RESPUESTA_REFLEXIVA,
                            id_referencia=None, tipo_conteo=modelos.TipoConteo.EVENTOS, cantidad_minima=3)])
                        for numero in range(100)])
                    sesion.add_all([modelos.EventoUso(cuenta_id=cuenta.id, tipo=modelos.TipoEventoUso.RESPUESTA_REFLEXIVA,
                        id_referencia=None, fecha_hora=FECHA + timedelta(days=numero % 7)) for numero in range(500)])
        # El commit carga las definiciones; la primera petición tras ampliarlas ya se mide.
        assert len(ampliada.state.motor_bd.cache_definiciones.actual.listar(modelos.ReglaDesbloqueo)) == 147
        original = motor.evaluar_regla
        evaluadas = []
        def observar(sesion, cuenta, regla):
            if regla.codigo.startswith('REG-SINT-'):
                evaluadas.append(regla.codigo)
            return original(sesion, cuenta, regla)
        monkeypatch.setattr(motor, 'evaluar_regla', observar)

        contadores = []
        antes = []
        for otro, app in ((cliente, aplicacion), (otro_cliente, ampliada)):
            estado, contador = peticion_contada(otro, app.state.motor_bd, contador_consultas,
                                               'GET', RUTA_ESTADO_REGISTRO_SQL)
            antes.append(estado)
            contadores.append(contador)
        assert antes[0] == antes[1]
        assert contadores[0].cantidad == contadores[1].cantidad <= LIMITES_SQL['estado_registro']
        assert contadores[0].por_tipo == contadores[1].por_tipo
        print(f'SQL crecimiento estado previo {modo}: {contadores[0].cantidad} = {contadores[1].cantidad}')

        textos = {'minimo': 'Corto [falla]', 'vaga': TEXTO_REGISTRO_SQL + '[vaga]',
                  'fallo': TEXTO_REGISTRO_SQL + '[falla]', 'atencion': TEXTO_REGISTRO_SQL + '[atencion]',
                  'edicion': 'Edición breve [falla]'}
        texto = textos.get(modo, TEXTO_REGISTRO_SQL)
        if modo.startswith('seguimiento_'):
            resultado = modo.rsplit('_', 1)[-1]
            marcador = {'vaga': '[vaga]', 'fallo': '[falla]', 'atencion': '[atencion]'}.get(resultado, '')
            texto = TEXTO_REGISTRO_SQL + marcador
            if resultado in ('timeout', 'invalido'):
                for app in (aplicacion, ampliada):
                    app.state.evaluador_respuestas = EvaluadorFalloSQL(resultado)
        elif modo.startswith('edicion_turno_'):
            texto = 'Edición breve [falla]'
        seguimiento = modo == 'ampliacion' or modo.startswith(('seguimiento_', 'edicion_turno_'))
        accion = 'responder-seguimiento' if seguimiento else 'enviar'
        presupuesto = 'responder_seguimiento_registro' if seguimiento else 'enviar_registro'
        respuestas = []
        contadores = []
        for otro, app in ((cliente, aplicacion), (otro_cliente, ampliada)):
            llamadas = len(app.state.evaluador_respuestas.contextos)
            datos = datos_registro_sql(texto)
            if modo.startswith('edicion_turno_'):
                datos['orden'] = int(modo[-1])
            respuesta, contador = peticion_contada(otro, app.state.motor_bd, contador_consultas,
                'POST', f'/acciones/registro/{accion}', datos)
            respuestas.append(respuesta)
            contadores.append(contador)
            evalua = modo not in ('edicion', 'seguimiento_generico') and not modo.startswith('edicion_turno_')
            assert len(app.state.evaluador_respuestas.contextos) == llamadas + int(evalua)
            assert not any('FROM regla_desbloqueo' in e.sentencia or 'FROM condicion_desbloqueo' in e.sentencia
                           for e in contador.ejecuciones)
        assert contadores[0].cantidad == contadores[1].cantidad <= LIMITES_SQL[presupuesto], contadores[1].diagnostico
        assert contadores[0].por_tipo == contadores[1].por_tipo
        print(f'SQL crecimiento registro {modo}: {contadores[0].cantidad} = {contadores[1].cantidad}')
        reflexiva = modo in ('ausente', 'borrador', 'ampliacion', 'atencion', 'seguimiento_generico') or (
            modo.startswith(('seguimiento_1_', 'seguimiento_2_')) and modo != 'seguimiento_1_vaga')
        assert len(respuestas[0]['eventos_registrados']) == len(respuestas[1]['eventos_registrados']) == int(reflexiva)
        assert len(evaluadas) == (100 if reflexiva else 0)
        if reflexiva:
            assert set(Counter(evaluadas).values()) == {1}
        sinteticas = [d for d in respuestas[1]['nuevos_desbloqueos'] if d['regla'].startswith('REG-SINT-')]
        assert len(sinteticas) == (100 if reflexiva else 0)
        assert all(d['condiciones'][0]['cumplida'] for d in sinteticas)
        if reflexiva:
            inserciones = [e for e in contadores[1].ejecuciones if e.sentencia.startswith('INSERT INTO desbloqueo ')]
            assert len(inserciones) == 1 and inserciones[0].en_lote
        with ampliada.state.fabrica_sesiones() as sesion:
            assert sesion.scalar(select(func.count()).select_from(modelos.Desbloqueo).join(modelos.ReglaDesbloqueo).where(
                modelos.ReglaDesbloqueo.codigo.startswith('REG-SINT-'))) == (100 if reflexiva else 0)
            assert sesion.scalar(select(func.count()).select_from(modelos.EventoUso)) >= 502
        despues = []
        contadores = []
        for otro, app in ((cliente, aplicacion), (otro_cliente, ampliada)):
            estado, contador = peticion_contada(otro, app.state.motor_bd, contador_consultas,
                                               'GET', RUTA_ESTADO_REGISTRO_SQL)
            despues.append(estado)
            contadores.append(contador)
        assert despues[0] == despues[1]
        assert contadores[0].cantidad == contadores[1].cantidad <= LIMITES_SQL['estado_registro']
        assert contadores[0].por_tipo == contadores[1].por_tipo
        print(f'SQL crecimiento estado posterior {modo}: {contadores[0].cantidad} = {contadores[1].cantidad}')


def test_preguntas_respondidas_no_se_mezclan_entre_cuentas(cliente, sesion):
    cuentas = {c.codigo: c for c in sesion.scalars(select(modelos.Cuenta))}
    preguntas = {p.codigo: p for p in sesion.scalars(select(modelos.PreguntaDiario))}
    sesion.add_all([
        modelos.EntradaDiario(cuenta_id=cuentas['est-ana'].id, origen=modelos.OrigenEntrada.GUIADA,
                      pregunta_id=preguntas['PD-HISTORIA'].id, texto='Mi historia', fecha_hora=datetime(2026, 10, 8)),
        modelos.EntradaDiario(cuenta_id=cuentas['est-luis'].id, origen=modelos.OrigenEntrada.GUIADA,
                      pregunta_id=preguntas['PD-ASPIRACIONES'].id, texto='Mis aspiraciones', fecha_hora=datetime(2026, 10, 8)),
        modelos.EntradaDiario(cuenta_id=cuentas['est-ana'].id, origen=modelos.OrigenEntrada.LIBRE,
                      texto='Una entrada libre', fecha_hora=datetime(2026, 10, 8)),
    ])
    sesion.commit()
    for cuenta, respondida in [('est-ana', 'PD-HISTORIA'), ('est-luis', 'PD-ASPIRACIONES')]:
        respuesta = cliente.get(f'/cuentas/{cuenta}/diario/preguntas')
        assert respuesta.status_code == 200
        filas = respuesta.json()
        assert [p['codigo'] for p in filas] == sorted(preguntas)
        assert {p['codigo'] for p in filas if p['respondida']} == {respondida}
        assert all(set(p) == {'codigo', 'pregunta', 'estado', 'respondida'} for p in filas)
        assert all(p['pregunta'] == preguntas[p['codigo']].pregunta for p in filas)
