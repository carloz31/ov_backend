"""Registro v2, fase 2: evaluación pura sin sesiones, HTTP ni red."""

from dataclasses import asdict, fields, replace
import json
import subprocess
import sys

from pydantic import ValidationError
import pytest

from app import evaluador_respuestas as evaluacion
from app.configuracion_metodos import MAXIMO_SEGUIMIENTOS_POR_ITEM, VERSION_PROMPT_REGISTRO
from app.evaluador_respuestas import (
    ContextoEvaluacion, ConversacionEvaluacion, TurnoEvaluacion, CriterioEvaluacion, ErrorResultadoEvaluacion, ErrorTextoVacio,
    EvaluadorFalso, RespuestaAnterior, ResultadoEvaluacion, evaluar_respuesta, validar_resultado, serializar_conversacion,
)
from app.tipos_registro import ClasificacionRespuesta, OrigenEvaluacion


@pytest.fixture
def contexto():
    return ContextoEvaluacion(
        titulo_actividad="Mi plan para fortalecer una habilidad",
        consigna="¿Qué harás para practicarla?",
        criterios=(CriterioEvaluacion("C1", "Describe una acción realizable."),
                   CriterioEvaluacion("C2", "Indica dónde, cuándo o con quién.")),
        respuestas_anteriores=(RespuestaAnterior("¿Qué habilidad social quieres fortalecer y por qué?",
            ConversacionEvaluacion("La asertividad", (TurnoEvaluacion("¿Por qué?", "En el trabajo grupal me cuesta dar mi opinión."),))),),
        conversacion=ConversacionEvaluacion("En el próximo trabajo grupal diré mi opinión antes de tomar una decisión."),
        criterios_faltantes_previos=("C1", "C2"),
    )


def datos_resultado(**cambios):
    return {"clasificacion": "ADECUADA", "criterios_faltantes": [],
            "pregunta": None, "requiere_atencion": False, **cambios}


def con_texto(contexto, texto):
    return replace(contexto, conversacion=ConversacionEvaluacion(texto))


def con_seguimiento(contexto, texto, numero=1):
    turnos = (TurnoEvaluacion("¿Qué acción concreta?", "Voy a dar mi opinión [falla] [vaga]"),
              TurnoEvaluacion("¿Cuándo?", texto)) if numero == 2 else (TurnoEvaluacion("¿Cuándo?", texto),)
    return replace(contexto, conversacion=ConversacionEvaluacion("Mi respuesta inicial [falla] [vaga]", turnos),
                   criterios_faltantes_previos=("C2",))


class EvaluadorDePrueba(EvaluadorFalso):
    def __init__(self, resultado=None, error=None):
        super().__init__()
        self.resultado = resultado
        self.error = error

    def evaluar(self, contexto):
        self.contextos.append(contexto)
        if self.error is not None:
            raise self.error
        return self.resultado


def test_interfaz_no_importa_sqlalchemy_fastapi_ni_modelos():
    codigo = (
        "import sys; import app.evaluador_respuestas; "
        "assert not any(nombre == raiz or nombre.startswith(raiz + '.') "
        "for nombre in sys.modules for raiz in ('sqlalchemy', 'fastapi')); "
        "assert 'app.models' not in sys.modules"
    )
    resultado = subprocess.run([sys.executable, "-c", codigo], capture_output=True, text=True, check=False)
    assert resultado.returncode == 0, resultado.stderr


def test_contexto_solo_contiene_campos_de_la_especificacion(contexto):
    assert {campo.name for campo in fields(contexto)} == {
        "titulo_actividad", "consigna", "criterios", "respuestas_anteriores", "conversacion", "criterios_faltantes_previos",
    }
    assert {campo.name for campo in fields(contexto.criterios[0])} == {"codigo", "descripcion"}
    assert {campo.name for campo in fields(contexto.respuestas_anteriores[0])} == {"consigna", "conversacion"}
    assert {campo.name for campo in fields(contexto.conversacion)} == {"texto_inicial", "turnos"}
    assert {campo.name for campo in fields(contexto.respuestas_anteriores[0].conversacion.turnos[0])} == {"pregunta", "respuesta"}
    with pytest.raises(TypeError):
        ContextoEvaluacion(**asdict(contexto), cuenta="est-ana")
    assert "est-ana" not in json.dumps(asdict(contexto), ensure_ascii=False)
    assert "Ana" not in json.dumps(asdict(contexto), ensure_ascii=False)


def test_constantes_de_registro_centralizadas():
    assert VERSION_PROMPT_REGISTRO == "v2"
    assert MAXIMO_SEGUIMIENTOS_POR_ITEM == 2


@pytest.mark.parametrize("texto,clasificacion,atencion", [
    ("Una respuesta completa", "ADECUADA", False),
    ("Una respuesta [vaga]", "VAGA", False),
    ("Una respuesta [atencion]", "ADECUADA", True),
    ("Una respuesta [vaga] [atencion]", "ADECUADA", True),
])
def test_evaluador_falso_determinista_y_contextos(contexto, texto, clasificacion, atencion):
    contexto = con_texto(contexto, texto)
    evaluador = EvaluadorFalso()
    primero = evaluador.evaluar(contexto)
    segundo = evaluador.evaluar(contexto)
    assert primero == segundo
    assert primero.clasificacion == clasificacion
    assert primero.requiere_atencion is atencion
    assert primero.criterios_faltantes == (["C1", "C2"] if clasificacion == "VAGA" else [])
    assert primero.pregunta == ("¿Podrías contarme más sobre C1, C2?" if clasificacion == "VAGA" else None)
    assert evaluador.contextos == [contexto, contexto]


@pytest.mark.parametrize("texto", ["[falla]", "[falla] [vaga] [atencion]"])
def test_evaluador_falso_falla_y_conserva_contexto(contexto, texto):
    contexto = con_texto(contexto, texto)
    evaluador = EvaluadorFalso()
    with pytest.raises(RuntimeError, match="Fallo simulado"):
        evaluador.evaluar(contexto)
    assert evaluador.contextos == [contexto]


@pytest.mark.parametrize("texto", ["", " ", "\n\t\r", "\u00a0\u2003"])
def test_texto_vacio_rechazado_sin_evaluar(contexto, texto):
    evaluador = EvaluadorFalso()
    with pytest.raises(ErrorTextoVacio, match="no puede estar vacío"):
        evaluar_respuesta(con_texto(contexto, texto), 40, "Cuéntame más", evaluador)
    assert evaluador.contextos == []


@pytest.mark.parametrize("texto,clasificacion,atencion", [
    ("Asertividad", "ADECUADA", False), ("  Asertividad  ", "ADECUADA", False),
    ("[vaga]", "VAGA", False), ("[atencion]", "ADECUADA", True),
])
def test_texto_corto_llama_evaluador_primero_r4_y_r5c(contexto, texto, clasificacion, atencion):
    evaluador = EvaluadorFalso()
    procesada = evaluar_respuesta(con_texto(contexto, texto), 40, "Pregunta genérica del ítem", evaluador)
    assert procesada.origen == OrigenEvaluacion.LLM
    assert procesada.clasificacion == clasificacion
    assert procesada.criterios_faltantes == (("C1", "C2") if clasificacion == "VAGA" else ())
    assert procesada.pregunta == ("¿Podrías contarme más sobre C1, C2?" if clasificacion == "VAGA" else None)
    assert procesada.requiere_atencion is atencion
    assert procesada.texto_evaluado == serializar_conversacion(con_texto(contexto, texto).conversacion)
    assert procesada.version_prompt == "v2" and procesada.latencia_ms >= 0 and procesada.error is None
    assert evaluador.contextos == [con_texto(contexto, texto)]


@pytest.mark.parametrize("minimo,longitud", [(40, 39), (40, 40), (40, 41), (30, 29), (30, 30), (30, 31)])
@pytest.mark.parametrize("fallo", [False, True])
def test_limites_exactos_solo_deciden_respaldo_y_respetan_espacios(contexto, minimo, longitud, fallo):
    texto = " \t" + "á" * longitud + "\n "
    evaluador = EvaluadorDePrueba(error=RuntimeError("dato sensible simulado")) if fallo else EvaluadorFalso()
    procesada = evaluar_respuesta(con_texto(contexto, texto), minimo, "Cuéntame más", evaluador)
    assert procesada.origen == (OrigenEvaluacion.RESPALDO_LONGITUD if fallo else OrigenEvaluacion.LLM)
    esperada = ("VAGA" if longitud < minimo else "NO_EVALUADA") if fallo else "ADECUADA"
    assert procesada.clasificacion == esperada
    assert procesada.criterios_faltantes == (("C1", "C2") if fallo and longitud < minimo else ())
    assert procesada.pregunta == ("Cuéntame más" if fallo and longitud < minimo else None)
    assert procesada.texto_evaluado == serializar_conversacion(con_texto(contexto, texto).conversacion)
    assert len(evaluador.contextos) == 1
    assert evaluador.contextos[0].conversacion.texto_actual == texto


@pytest.mark.parametrize("cambios", [
    {"clasificacion": "NO_EVALUADA"}, {"clasificacion": "adecuada"},
    {"clasificacion": 1}, {"criterios_faltantes": "C1"},
    {"criterios_faltantes": [1]}, {"criterios_faltantes": None},
    {"pregunta": 1}, {"requiere_atencion": "false"},
    {"requiere_atencion": 0}, {"campo_extra": True},
    {"repregunta": "Campo v1 rechazado"},
])
def test_resultado_exige_esquema_estricto(cambios):
    with pytest.raises(ValidationError):
        ResultadoEvaluacion(**datos_resultado(**cambios))


@pytest.mark.parametrize("campo", ["clasificacion", "criterios_faltantes", "pregunta", "requiere_atencion"])
def test_resultado_exige_todos_los_campos(campo):
    datos = datos_resultado()
    del datos[campo]
    with pytest.raises(ValidationError):
        ResultadoEvaluacion(**datos)


@pytest.mark.parametrize("datos", [
    datos_resultado(criterios_faltantes=["C1"]),
    datos_resultado(clasificacion="VAGA", criterios_faltantes=["C9"], pregunta="Cuéntame más"),
    datos_resultado(clasificacion="VAGA", criterios_faltantes=["C1"], pregunta=None),
    datos_resultado(clasificacion="VAGA", criterios_faltantes=["C1"], pregunta=""),
    datos_resultado(clasificacion="VAGA", criterios_faltantes=["C1"], pregunta=" \n\t"),
    datos_resultado(clasificacion="VAGA", pregunta="Cuéntame más"),
    datos_resultado(clasificacion="VAGA", criterios_faltantes=["C2", "C2"], pregunta="Cuéntame más"),
])
def test_consistencia_y_criterios_del_item(contexto, datos):
    with pytest.raises(ErrorResultadoEvaluacion):
        validar_resultado(ResultadoEvaluacion(**datos), contexto)


def test_vaga_con_atencion_admite_pregunta_nula_segun_consistencia(contexto):
    resultado = ResultadoEvaluacion(**datos_resultado(clasificacion="VAGA", criterios_faltantes=["C1"], requiere_atencion=True))
    assert validar_resultado(resultado, contexto).requiere_atencion is True


def test_criterios_conservan_orden_del_evaluador(contexto):
    resultado = ResultadoEvaluacion(**datos_resultado(clasificacion="VAGA", criterios_faltantes=["C2", "C1"], pregunta="Cuéntame más"))
    assert validar_resultado(resultado, contexto).criterios_faltantes == ["C2", "C1"]


def test_resultado_previamente_mutado_se_valida_otra_vez(contexto):
    resultado = ResultadoEvaluacion(**datos_resultado())
    resultado.criterios_faltantes.append("C9")
    with pytest.raises(ErrorResultadoEvaluacion):
        validar_resultado(resultado, contexto)


def test_resultado_construido_sin_validar_no_filtra_valores_ni_emite_avisos(contexto, recwarn):
    resultado = ResultadoEvaluacion.model_construct(**datos_resultado(clasificacion="dato sensible simulado"))
    procesada = evaluar_respuesta(contexto, 40, "Cuéntame más", EvaluadorDePrueba(resultado=resultado))
    assert procesada.origen == OrigenEvaluacion.RESPALDO_LONGITUD
    assert procesada.clasificacion == ClasificacionRespuesta.NO_EVALUADA
    assert "dato sensible simulado" not in str(procesada)
    assert list(recwarn) == []


def test_llm_adecuada_conserva_contexto_y_metadatos(contexto, monkeypatch):
    tiempos = iter((10.0, 10.125))
    monkeypatch.setattr(evaluacion, "perf_counter", lambda: next(tiempos))
    evaluador = EvaluadorFalso()
    procesada = evaluar_respuesta(contexto, 40, "Cuéntame más", evaluador, modelo="modelo_simulado")
    assert procesada.origen == OrigenEvaluacion.LLM
    assert procesada.clasificacion == ClasificacionRespuesta.ADECUADA
    assert procesada.criterios_faltantes == () and procesada.pregunta is None
    assert procesada.requiere_atencion is False and procesada.error is None
    assert procesada.modelo == "modelo_simulado" and procesada.version_prompt == "v2"
    assert procesada.latencia_ms == 125 and procesada.texto_evaluado == serializar_conversacion(contexto.conversacion)
    assert evaluador.contextos == [contexto]
    assert evaluador.contextos[0].respuestas_anteriores == contexto.respuestas_anteriores


def test_llm_vaga_registra_la_pregunta_del_falso(contexto):
    procesada = evaluar_respuesta(con_texto(contexto, contexto.conversacion.texto_actual + " [vaga]"), 40, "Repregunta mínima", EvaluadorFalso())
    assert procesada.origen == OrigenEvaluacion.LLM and procesada.clasificacion == ClasificacionRespuesta.VAGA
    assert procesada.criterios_faltantes == ("C1", "C2")
    assert procesada.pregunta == "¿Podrías contarme más sobre C1, C2?"


def test_atencion_no_tiene_pregunta_en_el_falso(contexto):
    procesada = evaluar_respuesta(con_texto(contexto, contexto.conversacion.texto_actual + " [atencion]"), 40, "Cuéntame más", EvaluadorFalso())
    assert procesada.origen == OrigenEvaluacion.LLM
    assert procesada.clasificacion == ClasificacionRespuesta.ADECUADA
    assert procesada.requiere_atencion is True
    assert procesada.pregunta is None and procesada.criterios_faltantes == ()


@pytest.mark.parametrize("resultado", [None, {}, "JSON incorrecto",
    datos_resultado(clasificacion="NO_EVALUADA"), datos_resultado(criterios_faltantes=["C1"]),
    datos_resultado(clasificacion="VAGA", criterios_faltantes=["C9"], pregunta="Cuéntame más"),
    datos_resultado(clasificacion="VAGA", pregunta=None),
])
def test_resultado_invalido_se_convierte_en_fallo(contexto, resultado):
    evaluador = EvaluadorDePrueba(resultado=resultado)
    procesada = evaluar_respuesta(contexto, 40, "Cuéntame más", evaluador)
    assert procesada.origen == OrigenEvaluacion.RESPALDO_LONGITUD
    assert procesada.clasificacion == ClasificacionRespuesta.NO_EVALUADA
    assert procesada.pregunta is None and procesada.criterios_faltantes == ()
    assert procesada.error == "El resultado del evaluador no cumple el esquema o las reglas de consistencia"
    assert procesada.texto_evaluado == serializar_conversacion(contexto.conversacion) and len(evaluador.contextos) == 1


@pytest.mark.parametrize("texto,codigos", [
    ("[falta:C2]", ["C2"]), ("[falta:C2,C1]", ["C2", "C1"]),
    ("[falta: C2, C1, C2 ]", ["C2", "C1"]), ("[falta:C1] [falta:C2] [vaga]", ["C1", "C2"]),
])
def test_falso_faltantes_explicitos_y_pregunta_por_codigos(contexto, texto, codigos):
    resultado = validar_resultado(EvaluadorFalso().evaluar(con_texto(contexto, texto)), contexto)
    assert resultado.clasificacion == "VAGA" and resultado.criterios_faltantes == codigos
    assert resultado.pregunta == f"¿Podrías contarme más sobre {', '.join(codigos)}?"


@pytest.mark.parametrize("numero", [1, 2])
@pytest.mark.parametrize("texto,clasificacion,atencion", [
    ("El jueves", "ADECUADA", False), ("[vaga]", "VAGA", False),
    ("[falta:C2]", "VAGA", False), ("[atencion]", "ADECUADA", True),
])
def test_falso_solo_decide_por_ultimo_turno_y_faltantes_previos(contexto, numero, texto, clasificacion, atencion):
    contexto = con_seguimiento(contexto, texto, numero)
    evaluador = EvaluadorFalso()
    procesada = evaluar_respuesta(contexto, 40, "Genérica", evaluador)
    assert procesada.origen == "LLM" and procesada.clasificacion == clasificacion
    assert procesada.requiere_atencion is atencion
    assert procesada.criterios_faltantes == (("C2",) if clasificacion == "VAGA" else ())
    assert procesada.pregunta == ("¿Podrías contarme más sobre C2?" if clasificacion == "VAGA" else None)
    assert evaluador.contextos == [contexto]


@pytest.mark.parametrize("numero", [1, 2])
@pytest.mark.parametrize("texto", ["", " ", "\n\t\r", "\u00a0\u2003"])
def test_ultimo_turno_vacio_rechazado_aunque_haya_respuestas_previas(contexto, texto, numero):
    contexto = con_seguimiento(contexto, texto, numero)
    evaluador = EvaluadorFalso()
    with pytest.raises(ErrorTextoVacio, match="no puede estar vacío"):
        evaluar_respuesta(contexto, 40, "Cuéntame más", evaluador)
    assert evaluador.contextos == []


@pytest.mark.parametrize("codigos", [["C1"], ["C1", "C2"]])
def test_no_admite_criterios_ya_cumplidos(contexto, codigos):
    contexto = con_seguimiento(contexto, "Todavía [vaga]")
    resultado = ResultadoEvaluacion(**datos_resultado(clasificacion="VAGA", criterios_faltantes=codigos, pregunta="Cuéntame más"))
    with pytest.raises(ErrorResultadoEvaluacion, match="ya cumplidos"):
        validar_resultado(resultado, contexto)
    procesada = evaluar_respuesta(contexto, 40, "Genérica", EvaluadorDePrueba(resultado))
    assert procesada.origen == "RESPALDO_LONGITUD" and procesada.clasificacion == "NO_EVALUADA"


@pytest.mark.parametrize("texto", ["[falta:C9]", "[falta:]"])
def test_marca_falso_invalida_aplica_respaldo_en_vez_de_aceptar(contexto, texto):
    procesada = evaluar_respuesta(con_texto(contexto, texto), 40, "Genérica", EvaluadorFalso())
    assert procesada.origen == "RESPALDO_LONGITUD" and procesada.clasificacion == "VAGA"
    assert procesada.pregunta == "Genérica" and procesada.criterios_faltantes == ("C1", "C2")
    assert "consistencia" in procesada.error


@pytest.mark.parametrize("resultado", [None, {},
    datos_resultado(clasificacion="VAGA", criterios_faltantes=["C9"], pregunta="Cuéntame más"),
    datos_resultado(clasificacion="VAGA", criterios_faltantes=["C1", "C1"], pregunta="Cuéntame más"),
])
@pytest.mark.parametrize("numero", [0, 1, 2])
def test_resultado_invalido_con_texto_corto_respalda_solo_el_inicial(contexto, resultado, numero):
    contexto = con_seguimiento(contexto, "Corta", numero) if numero else con_texto(contexto, "Corta")
    evaluador = EvaluadorDePrueba(resultado)
    procesada = evaluar_respuesta(contexto, 40, "Genérica", evaluador)
    assert procesada.origen == "RESPALDO_LONGITUD"
    assert procesada.clasificacion == ("NO_EVALUADA" if numero else "VAGA")
    assert procesada.pregunta == (None if numero else "Genérica")
    assert procesada.criterios_faltantes == (() if numero else ("C1", "C2"))
    assert "consistencia" in procesada.error and evaluador.contextos == [contexto]


def test_serializacion_preserva_conversacion_completa_unicode_y_orden(contexto):
    conversacion = ConversacionEvaluacion("  Ánimo\n[texto]  ", (
        TurnoEvaluacion('¿Qué harás con "ellos"?', "Daré mi opinión.\n"),
        TurnoEvaluacion("¿Cuándo?", "  El jueves 💡  "),
    ))
    contexto = replace(contexto, conversacion=conversacion, criterios_faltantes_previos=("C2",))
    evaluador = EvaluadorFalso()
    procesada = evaluar_respuesta(contexto, 40, "Genérica", evaluador)
    assert json.loads(procesada.texto_evaluado) == {
        "texto_inicial": conversacion.texto_inicial,
        "turnos": [{"pregunta": t.pregunta, "respuesta": t.respuesta} for t in conversacion.turnos],
    }
    assert evaluador.contextos[0].respuestas_anteriores[0].conversacion.turnos[0].respuesta == "En el trabajo grupal me cuesta dar mi opinión."
    assert contexto.conversacion == conversacion and "est-ana" not in procesada.texto_evaluado


@pytest.mark.parametrize("error,esperado", [
    (RuntimeError("dato sensible simulado"), "Falló el evaluador de respuestas"),
    (TimeoutError("dato sensible simulado"), "Se agotó el tiempo máximo de evaluación"),
    (ErrorResultadoEvaluacion("dato sensible simulado"), "El resultado del evaluador no cumple el esquema o las reglas de consistencia"),
])
@pytest.mark.parametrize("numero,longitud", [(0, 5), (0, 40), (1, 5), (1, 40), (2, 5), (2, 40)])
def test_fallos_guardan_error_seguro_y_no_reintentan(contexto, error, esperado, numero, longitud):
    contexto = con_seguimiento(contexto, "á" * longitud, numero) if numero else con_texto(contexto, "á" * longitud)
    evaluador = EvaluadorDePrueba(error=error)
    procesada = evaluar_respuesta(contexto, 40, "Cuéntame más", evaluador, modelo="modelo_simulado")
    corto_inicial = numero == 0 and longitud < 40
    assert procesada.origen == OrigenEvaluacion.RESPALDO_LONGITUD
    assert procesada.clasificacion == ("VAGA" if corto_inicial else "NO_EVALUADA")
    assert procesada.error == esperado and "dato sensible simulado" not in str(procesada)
    assert procesada.requiere_atencion is False
    assert procesada.pregunta == ("Cuéntame más" if corto_inicial else None)
    assert procesada.criterios_faltantes == (("C1", "C2") if corto_inicial else ())
    assert procesada.modelo == "modelo_simulado" and procesada.version_prompt == "v2"
    assert procesada.latencia_ms >= 0
    assert evaluador.contextos == [contexto]


def test_marcador_falla_procesado_no_propaga_excepcion(contexto):
    procesada = evaluar_respuesta(con_texto(contexto, contexto.conversacion.texto_actual + " [falla]"), 40, "Cuéntame más", EvaluadorFalso())
    assert procesada.clasificacion == ClasificacionRespuesta.NO_EVALUADA
    assert procesada.origen == OrigenEvaluacion.RESPALDO_LONGITUD and procesada.error == "Falló el evaluador de respuestas"


@pytest.mark.parametrize("duracion,fallo", [(7.999, False), (8.0, False), (8.001, True)])
@pytest.mark.parametrize("numero,longitud", [(0, 5), (0, 40), (1, 5), (2, 5)])
def test_tiempo_maximo_exacto_sin_esperas_reales(contexto, monkeypatch, duracion, fallo, numero, longitud):
    contexto = con_seguimiento(contexto, "á" * longitud, numero) if numero else con_texto(contexto, "á" * longitud)
    tiempos = iter((0.0, duracion))
    monkeypatch.setattr(evaluacion, "perf_counter", lambda: next(tiempos))
    evaluador = EvaluadorFalso()
    procesada = evaluar_respuesta(contexto, 40, "Cuéntame más", evaluador)
    assert procesada.origen == (OrigenEvaluacion.RESPALDO_LONGITUD if fallo else OrigenEvaluacion.LLM)
    assert procesada.latencia_ms == round(duracion * 1000)
    assert len(evaluador.contextos) == 1
    if fallo:
        corto_inicial = numero == 0 and longitud < 40
        assert procesada.error == "Se agotó el tiempo máximo de evaluación"
        assert procesada.pregunta == ("Cuéntame más" if corto_inicial else None)
        assert procesada.clasificacion == ("VAGA" if corto_inicial else "NO_EVALUADA")


@pytest.mark.parametrize("minimo", [-1, 1.5, True])
def test_minimo_invalido_es_error_de_configuracion(contexto, minimo):
    evaluador = EvaluadorFalso()
    with pytest.raises(ValueError, match="mínimo de caracteres"):
        evaluar_respuesta(contexto, minimo, "Cuéntame más", evaluador)
    assert evaluador.contextos == []


@pytest.mark.parametrize("tiempo", [0, -1, float("inf"), float("nan"), True])
def test_tiempo_maximo_invalido_no_llama_evaluador(contexto, tiempo):
    evaluador = EvaluadorFalso()
    with pytest.raises(ValueError, match="tiempo máximo"):
        evaluar_respuesta(contexto, 40, "Cuéntame más", evaluador, tiempo_maximo_segundos=tiempo)
    assert evaluador.contextos == []


def test_pregunta_generica_vacia_es_error_solo_si_se_necesita_respaldo(contexto):
    evaluador = EvaluadorDePrueba(error=RuntimeError("fallo"))
    with pytest.raises(ValueError, match="repregunta genérica"):
        evaluar_respuesta(con_texto(contexto, "Corta"), 40, " \n", evaluador)
    assert len(evaluador.contextos) == 1
    assert evaluar_respuesta(con_texto(contexto, "Corta"), 40, "", EvaluadorFalso()).clasificacion == "ADECUADA"
    assert evaluar_respuesta(contexto, 40, "", evaluador).clasificacion == "NO_EVALUADA"
