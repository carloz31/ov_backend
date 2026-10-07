"""Sección 9.1: pruebas puras, sin sesiones SQL ni lectura del Excel."""

import pytest

from app.calculo_instrumentos import (
    CodigoInteresCalculado, DimensionCalculada, ItemParaCalculo, PerfilOcupacion,
    calcular_codigo_interes, calcular_coincidencias, calcular_dimension, calcular_dimensiones_destacadas, calcular_pearson,
    calcular_porcentaje, calcular_puntaje_item, clasificar_ajuste,
)


VECTOR_A = (21, 9, 17, 20, 28, 15)
VECTOR_B = (27, 24, 18, 17, 23, 18)


@pytest.mark.parametrize("vector_ocupacion, esperado, ajuste", [
    ((4.2, 1.8, 3.4, 4.0, 5.6, 3.0), 1.000000, "BEST_FIT"),
    ((5.0, 1.0, 2.0, 4.0, 6.0, 4.5), 0.845946, "BEST_FIT"),
    ((3.0, 2.5, 3.5, 5.0, 4.5, 2.0), 0.681419, "GREAT_FIT"),
    ((1.00, 1.69, 3.87, 3.14, 7.00, 4.43), 0.584176, "GOOD_FIT"),
])
def test_pearson_y_ajuste_con_vectores_de_la_especificacion(vector_ocupacion, esperado, ajuste):
    correlacion = calcular_pearson(VECTOR_A, vector_ocupacion)
    assert correlacion == pytest.approx(esperado, abs=1e-6, rel=0)
    assert clasificar_ajuste(correlacion) == ajuste


def test_correlacion_negativa_del_notebook_se_descarta():
    ocupacion = PerfilOcupacion("11-1021.00", "General and Operations Managers", (2.20, 2.37, 1.29, 3.38, 7, 5.34))
    correlacion = calcular_pearson(VECTOR_B, ocupacion.puntajes)
    assert correlacion == pytest.approx(-0.061193, abs=1e-6, rel=0)
    assert clasificar_ajuste(correlacion) is None
    resultado = calcular_coincidencias(VECTOR_B, [ocupacion])
    assert resultado.perfil_plano is False
    assert resultado.coincidencias == ()


@pytest.mark.parametrize("correlacion, esperado", [
    (-1, None), (-0.000001, None), (0, "GOOD_FIT"), (0.607999, "GOOD_FIT"),
    (0.608, "GREAT_FIT"), (0.728999, "GREAT_FIT"), (0.729, "BEST_FIT"), (1, "BEST_FIT"),
])
def test_umbrales_de_ajuste_inclusivos_sin_redondear(correlacion, esperado):
    assert clasificar_ajuste(correlacion) == esperado


@pytest.mark.parametrize("puntaje, minimo, maximo, inverso, esperado", [
    (1, 0, 1, True, 0), (0, 0, 1, True, 1), (1, 0, 4, True, 3),
    (4, 0, 4, True, 0), (0, 0, 4, True, 4), (3, 1, 4, True, 2),
    (0, 0, 4, False, 0), (3, 0, 4, False, 3),
])
def test_puntuacion_e_inversion_segun_limites_de_la_escala(puntaje, minimo, maximo, inverso, esperado):
    assert calcular_puntaje_item(puntaje, minimo, maximo, inverso) == esperado


@pytest.mark.parametrize("puntaje, maximo, esperado", [
    (0, 40, 0), (40, 40, 100), (21, 40, 52.5), (4, 7, 57.14), (1, 3, 33.33),
])
def test_porcentaje_redondeado_a_dos_decimales(puntaje, maximo, esperado):
    assert calcular_porcentaje(puntaje, maximo) == esperado


def test_dimension_suma_puntajes_y_maximos_con_escalas_distintas():
    # Máximos 1+4+4=9; puntajes 1+(4-1)+(4+1-4)=5.
    items = [ItemParaCalculo(1, 0, 1), ItemParaCalculo(1, 0, 4, inverso=True),
             ItemParaCalculo(4, 1, 4, inverso=True)]
    assert calcular_dimension("DIM-DEMO", iter(items)) == DimensionCalculada("DIM-DEMO", 5, 9, 55.56)


@pytest.mark.parametrize("valores, esperadas", [
    ([(3, 4), (3, 4), (2, 4)], ("D-2", "D-1")),
    ([(4, 7), (1, 2)], ("D-2",)),
    ([(0, 7), (0, 4), (0, 5)], ("D-2", "D-1", "D-0")),
    ([(4, 7), (5714, 10000)], ("D-2",)),
    ([(4, 7), (8, 14)], ("D-2", "D-1")),
])
def test_dimensiones_destacadas_compara_proporciones_exactas_y_conserva_empates(valores, esperadas):
    dimensiones = [DimensionCalculada(f"D-{2 - n}", puntaje, maximo, calcular_porcentaje(puntaje, maximo))
                   for n, (puntaje, maximo) in enumerate(valores)]
    assert calcular_dimensiones_destacadas(dimensiones) == esperadas


@pytest.mark.parametrize("numeros, puntaje, maximo, porcentaje", [
    ([1, 8, 11, 17, 21, 24, 27, 36, 41, 43], 7, 10, 70),
    ([3, 6, 13, 20, 25, 28, 37], 4, 7, 57.14),
    ([7, 18, 26, 29], 2, 4, 50), ([2, 14, 19, 30, 38], 1, 5, 20),
    ([5, 10, 31, 39], 3, 4, 75), ([4, 9, 16, 22, 32, 34, 40, 42], 1, 8, 12.5),
    ([12, 15, 23, 33, 35], 4, 5, 80),
])
def test_calculo_de_inteligencias_con_si_en_impares(numeros, puntaje, maximo, porcentaje):
    items = [ItemParaCalculo(1 if numero % 2 else 0, 0, 1) for numero in numeros]
    resultado = calcular_dimension("INT", items)
    assert (resultado.puntaje, resultado.puntaje_maximo, resultado.porcentaje) == (puntaje, maximo, porcentaje)


@pytest.mark.parametrize("codigo, numeros, inversos, puntaje, maximo, porcentaje", [
    ("HAB-ASE", [1, 10, 15, 19, 21], set(), 2, 5, 40),
    ("HAB-EMP", [4, 7, 16, 22], set(), 2, 4, 50),
    ("HAB-LID", [5, 14, 20], {5, 20}, 1, 3, 33.33),
    ("HAB-RES", [6, 13, 17, 24], set(), 1, 4, 25),
    ("HAB-EXP", [3, 8, 23], {3, 8}, 0, 3, 0),
    ("HAB-VAL", [2, 9, 11, 12, 18], set(), 4, 5, 80),
])
def test_calculo_de_habilidades_con_items_inversos(codigo, numeros, inversos, puntaje, maximo, porcentaje):
    items = [ItemParaCalculo(1 if numero <= 12 else 0, 0, 1, inverso=numero in inversos) for numero in numeros]
    assert calcular_dimension(codigo, items) == DimensionCalculada(codigo, puntaje, maximo, porcentaje)


@pytest.mark.parametrize("cadena, puntajes, porcentajes, codigo", [
    ("511222115515411122551525542552114321231141335215514152553521",
     (21, 9, 17, 20, 28, 15), (52.5, 22.5, 42.5, 50, 70, 37.5), "ERS"),
    ("333322223322343333233333443333333333444433333433444433334433",
     (27, 24, 18, 17, 23, 18), (67.5, 60, 45, 42.5, 57.5, 45), "RIE"),
])
def test_puntuacion_de_las_cadenas_riasec_completas(cadena, puntajes, porcentajes, codigo):
    resultados = []
    for dimension in "RIASEC":
        items = [ItemParaCalculo(int(opcion) - 1, 0, 4) for indice, opcion in enumerate(cadena)
                 if "RRIIAASSEECC"[indice % 12] == dimension]
        resultados.append(calcular_dimension(dimension, items))
    assert tuple(r.puntaje for r in resultados) == puntajes
    assert tuple(r.puntaje_maximo for r in resultados) == (40,) * 6
    assert tuple(r.porcentaje for r in resultados) == porcentajes
    assert calcular_codigo_interes(puntajes) == CodigoInteresCalculado(codigo, hay_empate=False)


@pytest.mark.parametrize("puntajes, codigo, hay_empate", [
    (VECTOR_A, "ERS", False), (VECTOR_B, "RIE", False), ((20,) * 6, "RIA", True),
    ((10, 10, 30, 30, 20, 20), "ASE", True), ((30, 30, 20, 10, 5, 0), "RIA", False),
])
def test_codigo_de_interes_y_empate_solo_en_el_corte(puntajes, codigo, hay_empate):
    assert calcular_codigo_interes(puntajes) == CodigoInteresCalculado(codigo, hay_empate)


def test_top_diez_desempata_por_codigo_y_asigna_posiciones():
    ocupaciones = [PerfilOcupacion(f"O-{numero:02}", f"Ocupación {numero}", VECTOR_A) for numero in range(12, 0, -1)]
    resultado = calcular_coincidencias(VECTOR_A, iter(ocupaciones))
    assert resultado.perfil_plano is False
    assert [c.codigo_onet for c in resultado.coincidencias] == [f"O-{numero:02}" for numero in range(1, 11)]
    assert [c.posicion for c in resultado.coincidencias] == list(range(1, 11))
    assert all(c.correlacion == pytest.approx(1) and c.ajuste == "BEST_FIT" for c in resultado.coincidencias)
    assert [o.codigo_onet for o in ocupaciones] == [f"O-{numero:02}" for numero in range(12, 0, -1)]


def test_top_ordena_por_pearson_y_conserva_precision_y_titulos():
    ocupaciones = [
        PerfilOcupacion("01-GOOD", "Advertising and Promotions Managers", (1, 1.69, 3.87, 3.14, 7, 4.43)),
        PerfilOcupacion("02-GREAT", "GREAT", (3, 2.5, 3.5, 5, 4.5, 2)),
        PerfilOcupacion("03-BEST", "BEST", (5, 1, 2, 4, 6, 4.5)),
    ]
    coincidencias = calcular_coincidencias(VECTOR_A, ocupaciones).coincidencias
    assert [c.codigo_onet for c in coincidencias] == ["03-BEST", "02-GREAT", "01-GOOD"]
    assert [c.ajuste for c in coincidencias] == ["BEST_FIT", "GREAT_FIT", "GOOD_FIT"]
    assert [c.posicion for c in coincidencias] == [1, 2, 3]
    assert coincidencias[-1].titulo == "Advertising and Promotions Managers"
    for coincidencia, esperado in zip(coincidencias, (0.845946, 0.681419, 0.584176), strict=True):
        assert coincidencia.correlacion == pytest.approx(esperado, abs=1e-6, rel=0)
        assert coincidencia.correlacion != round(coincidencia.correlacion, 6)


def test_perfil_plano_no_evalua_ocupaciones():
    def ocupaciones():
        raise AssertionError("Un perfil plano no debe consultar ni calcular ocupaciones")
        yield

    resultado = calcular_coincidencias((20,) * 6, ocupaciones())
    assert resultado.perfil_plano is True
    assert resultado.coincidencias == ()
    assert calcular_codigo_interes((20,) * 6) == CodigoInteresCalculado("RIA", True)


@pytest.mark.parametrize("operacion", [
    lambda: calcular_puntaje_item(5, 0, 4), lambda: calcular_puntaje_item(1, 4, 0),
    lambda: calcular_puntaje_item(float("nan"), 0, 4),
    lambda: calcular_porcentaje(0, 0), lambda: calcular_porcentaje(2, -1),
    lambda: calcular_porcentaje(float("inf"), 40), lambda: calcular_porcentaje(41, 40),
    lambda: calcular_dimension("VACIA", []), lambda: calcular_codigo_interes((1, 2)),
    lambda: calcular_pearson(VECTOR_A, (1, 2, 3)),
    lambda: calcular_pearson(VECTOR_A, (1, 2, 3, 4, 5, float("nan"))),
    lambda: clasificar_ajuste(float("nan")), lambda: clasificar_ajuste(1.01),
])
def test_calculo_rechaza_datos_invalidos_en_lugar_de_generar_resultados(operacion):
    with pytest.raises(ValueError):
        operacion()


def test_ocupacion_constante_provoca_error_identificando_su_codigo():
    ocupacion = PerfilOcupacion("O-PLANA", "Vector constante", (2,) * 6)
    with pytest.raises(ValueError, match="O-PLANA.*vector constante"):
        calcular_coincidencias(VECTOR_A, [ocupacion])
