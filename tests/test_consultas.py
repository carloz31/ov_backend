from datetime import datetime

import pytest
from sqlalchemy import select

from app import models as modelos
from app.database import crear_motor_bd
from app.services.motor.reglas import registrar_eventos


FECHA = datetime(2026, 10, 1, 10)


def buscar(sesion, modelo, codigo):
    entidad = sesion.scalar(select(modelo).where(modelo.codigo == codigo))
    assert entidad is not None
    return entidad


def test_lista_cuentas_con_codigos_publicos(cliente):
    respuesta = cliente.get("/cuentas")
    assert respuesta.status_code == 200
    assert respuesta.json() == [
        {"codigo": "apo-rosa", "nombre": "Rosa", "rol": "APODERADO"},
        {"codigo": "est-ana", "nombre": "Ana", "rol": "ESTUDIANTE"},
        {"codigo": "est-luis", "nombre": "Luis", "rol": "ESTUDIANTE"},
    ]


def test_validacion_de_tipo_y_filtro(cliente):
    assert cliente.get("/cuentas/est-ana/progreso/NO_EXISTE/ACT-01").status_code == 422
    assert cliente.get("/cuentas/est-ana/desbloqueos?solo_no_vistos=incorrecto").status_code == 422
    assert cliente.post("/cuentas/no-existe/desbloqueos/marcar-vistos").status_code == 404


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


# Mediciones reproducibles. Los presupuestos se exigirán tras optimizar; los
# conteos iniciales quedan en decisiones.md, no como expectativas del motor.


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


def peticion_contada(cliente, motor_bd, contador_consultas, metodo, ruta, datos=None, esperado=200):
    with contador_consultas(motor_bd) as contador:
        respuesta = cliente.request(metodo, ruta, json=datos)
    assert respuesta.status_code == esperado, respuesta.text
    return respuesta.json(), contador


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


# Registro: presupuestos de la petición completa, con preparación fuera del contador.
