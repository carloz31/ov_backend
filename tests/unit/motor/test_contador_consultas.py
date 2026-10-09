"""Contador consultas."""

import pytest
from app.database import crear_motor_bd


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
