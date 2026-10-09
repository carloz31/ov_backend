"""Evaluador gemini."""

import json
import logging
from dataclasses import replace
import httpx
import pytest
from google import genai
from google.genai import errors, types
from app.config import Configuracion
from app.services.registro.evaluacion import ContextoEvaluacion, ConversacionEvaluacion, CriterioEvaluacion, RespuestaAnterior, TurnoEvaluacion, evaluar_respuesta
from app.services.registro.gemini import EvaluadorGemini, razonamiento_minimo
from app.services.registro.prompt import PROMPT_REGISTRO_V2
from soporte_red import impedir_red


CLAVE_SIMULADA = 'clave-sintetica-solo-pruebas'


CONFIGURACION = Configuracion(evaluador='gemini', clave=CLAVE_SIMULADA)


CONTEXTO = ContextoEvaluacion(
    'Mi plan para fortalecer una habilidad', '¿Qué harás para practicarla?',
    (CriterioEvaluacion('C1', 'Acción concreta'), CriterioEvaluacion('C2', 'Situación concreta')),
    (RespuestaAnterior('¿Qué habilidad?', ConversacionEvaluacion('Asertividad en los trabajos grupales')),),
    ConversacionEvaluacion('En el trabajo de Comunicación del jueves voy a decir mi opinión al menos una vez.'),
    ('C1', 'C2'),
)


ADECUADA = dict(clasificacion='ADECUADA', criterios_faltantes=[], pregunta=None, requiere_atencion=False)


VAGA = dict(clasificacion='VAGA', criterios_faltantes=['C2'], pregunta='¿Cuándo lo practicarías?', requiere_atencion=False)


def respuesta_sdk(datos=ADECUADA):
    return types.GenerateContentResponse(candidates=[types.Candidate(
        content=types.Content(parts=[types.Part(text=json.dumps(datos, ensure_ascii=False))]),
        finish_reason='STOP',
    )])


class ClienteSimulado:
    def __init__(self, respuesta=None, error=None, observar=None):
        self.models = self
        self.respuesta = respuesta if respuesta is not None else respuesta_sdk()
        self.error = error
        self.observar = observar
        self.llamadas = []
        self.cierres = 0

    def generate_content(self, **argumentos):
        self.llamadas.append(argumentos)
        if self.observar:
            self.observar()
        if self.error:
            raise self.error
        return self.respuesta

    def close(self):
        self.cierres += 1


def procesar(cliente, contexto=CONTEXTO, configuracion=CONFIGURACION):
    adaptador = EvaluadorGemini(configuracion, cliente=cliente)
    try:
        resultado = evaluar_respuesta(contexto, 40, 'Cuéntame más', adaptador,
                                      modelo=configuracion.modelo, tiempo_maximo_segundos=configuracion.timeout_segundos)
        assert adaptador.latencia_ms is not None
        return resultado
    finally:
        adaptador.cerrar()


def test_peticion_salida_estructurada_contexto_exclusivo_y_latencia():
    cliente = ClienteSimulado()
    adaptador = EvaluadorGemini(CONFIGURACION, cliente=cliente)
    try:
        assert adaptador.latencia_ms is None
        resultado = adaptador.evaluar(CONTEXTO)
        assert resultado.model_dump() == ADECUADA
        assert adaptador.latencia_ms >= 0
        assert len(cliente.llamadas) == 1
        llamada = cliente.llamadas[0]
        datos = json.loads(llamada['contents'])
        assert set(datos) == {'titulo_actividad', 'consigna', 'criterios', 'respuestas_anteriores', 'conversacion', 'criterios_faltantes_previos'}
        assert datos['criterios'] == [{'codigo': c.codigo, 'descripcion': c.descripcion} for c in CONTEXTO.criterios]
        assert datos['respuestas_anteriores'] == [{'consigna': CONTEXTO.respuestas_anteriores[0].consigna,
                                                  'conversacion': {'texto_inicial': CONTEXTO.respuestas_anteriores[0].conversacion.texto_inicial, 'turnos': []}}]
        assert CLAVE_SIMULADA not in llamada['contents']
        configuracion = llamada['config']
        assert configuracion.system_instruction == PROMPT_REGISTRO_V2
        assert configuracion.temperature == 0.2
        assert configuracion.response_mime_type == 'application/json'
        assert configuracion.response_json_schema['required'] == list(ADECUADA)
        assert configuracion.response_json_schema['additionalProperties'] is False
        assert configuracion.thinking_config.thinking_level == 'MINIMAL'
        assert configuracion.automatic_function_calling.disable is True
    finally:
        adaptador.cerrar()
    assert cliente.cierres == 0  # El cliente inyectado pertenece al llamador.


def test_conversacion_enviada_y_auditada_coinciden_con_cliente_simulado():
    contexto = replace(CONTEXTO, conversacion=ConversacionEvaluacion("Voy a dar mi opinión.", (
        TurnoEvaluacion("¿Cuándo?", "El jueves en Comunicación."),
    )), criterios_faltantes_previos=('C2',), respuestas_anteriores=(RespuestaAnterior(
        '¿Qué habilidad y por qué?', ConversacionEvaluacion('Asertividad', (
            TurnoEvaluacion('¿Por qué?', 'Me cuesta dar mi opinión.'),
        ))),))
    cliente = ClienteSimulado()
    resultado = procesar(cliente, contexto)
    contenido = json.loads(cliente.llamadas[0]['contents'])
    assert contenido['conversacion'] == json.loads(resultado.texto_evaluado)
    assert contenido['criterios_faltantes_previos'] == ['C2']
    assert contenido['respuestas_anteriores'][0]['conversacion']['turnos'] == [
        {'pregunta': '¿Por qué?', 'respuesta': 'Me cuesta dar mi opinión.'}]
    assert len(cliente.llamadas) == 1 and resultado.clasificacion == 'ADECUADA'


@pytest.mark.parametrize('fallo', [False, True])
def test_texto_corto_llega_a_gemini_simulado_antes_de_decidir_respaldo(fallo):
    contexto = replace(CONTEXTO, conversacion=ConversacionEvaluacion('Asertividad'))
    cliente = ClienteSimulado(error=httpx.ReadTimeout(CLAVE_SIMULADA) if fallo else None)
    resultado = procesar(cliente, contexto)
    assert len(cliente.llamadas) == 1
    assert json.loads(cliente.llamadas[0]['contents'])['conversacion']['texto_inicial'] == 'Asertividad'
    assert resultado.origen == ('RESPALDO_LONGITUD' if fallo else 'LLM')
    assert resultado.clasificacion == ('VAGA' if fallo else 'ADECUADA')
    assert resultado.pregunta == ('Cuéntame más' if fallo else None)
    assert resultado.modelo == CONFIGURACION.modelo and resultado.version_prompt == 'v2'
    assert CLAVE_SIMULADA not in (resultado.error or '')


@pytest.mark.parametrize('modelo,campo,valor', [
    ('gemini-3.1-flash-lite', 'thinking_level', 'MINIMAL'),
    ('models/gemini-3.1-flash-lite-preview', 'thinking_level', 'MINIMAL'),
    ('gemini-3-flash-preview', 'thinking_level', 'MINIMAL'),
    ('gemini-3.1-pro-preview', 'thinking_level', 'LOW'),
    ('gemini-2.5-flash', 'thinking_budget', 0),
    ('gemini-2.5-flash-lite', 'thinking_budget', 0),
    ('gemini-2.5-pro', 'thinking_budget', 128),
])
def test_razonamiento_minimo_compatible(modelo, campo, valor):
    assert getattr(razonamiento_minimo(modelo), campo) == valor


def test_modelo_desconocido_sin_supuestos_ni_descubrimiento():
    assert razonamiento_minimo('modelo-desconocido') is None
    cliente = ClienteSimulado()
    procesar(cliente, configuracion=replace(CONFIGURACION, modelo='modelo-desconocido'))
    assert cliente.llamadas[0]['config'].thinking_config is None


@pytest.mark.parametrize('datos', [ADECUADA, VAGA, {**ADECUADA, 'requiere_atencion': True}])
def test_respuestas_validas_y_metadatos(datos):
    resultado = procesar(ClienteSimulado(respuesta_sdk(datos)))
    assert resultado.origen == 'LLM'
    assert resultado.clasificacion == datos['clasificacion']
    assert resultado.criterios_faltantes == tuple(datos['criterios_faltantes'])
    assert resultado.requiere_atencion is datos['requiere_atencion']
    assert resultado.modelo == CONFIGURACION.modelo
    assert resultado.version_prompt == 'v2'
    assert resultado.latencia_ms >= 0


@pytest.mark.parametrize('datos', [
    {}, {**ADECUADA, 'clasificacion': 'NO_EVALUADA'}, {**ADECUADA, 'requiere_atencion': 'false'},
    {**ADECUADA, 'extra': CLAVE_SIMULADA}, {**ADECUADA, 'criterios_faltantes': ['C1']},
    {**VAGA, 'criterios_faltantes': ['inexistente']}, {**VAGA, 'pregunta': None},
    {**VAGA, 'pregunta': '   '}, {**ADECUADA, 'pregunta': 9},
])
def test_resultados_invalidos_se_convierten_en_fallo(datos):
    cliente = ClienteSimulado(respuesta_sdk(datos))
    resultado = procesar(cliente)
    assert resultado.origen == 'RESPALDO_LONGITUD'
    assert resultado.clasificacion == 'NO_EVALUADA'
    assert resultado.pregunta is None
    assert 'esquema' in resultado.error
    assert CLAVE_SIMULADA not in resultado.error
    assert len(cliente.llamadas) == 1


@pytest.mark.parametrize('respuesta', [
    types.GenerateContentResponse(),
    types.GenerateContentResponse(candidates=[types.Candidate()]),
    types.GenerateContentResponse(candidates=[types.Candidate(content=types.Content(parts=[types.Part(text='no JSON')]))]),
    types.GenerateContentResponse(candidates=[types.Candidate(content=types.Content(parts=[types.Part(text=json.dumps(ADECUADA), thought=True)]))]),
])
def test_salida_ausente_bloqueada_o_malformada(respuesta):
    assert procesar(ClienteSimulado(respuesta)).origen == 'RESPALDO_LONGITUD'


@pytest.mark.parametrize('error,timeout', [
    (RuntimeError(CLAVE_SIMULADA), False), (httpx.ConnectError(CLAVE_SIMULADA), False),
    (httpx.ReadTimeout(CLAVE_SIMULADA), True), (TimeoutError(CLAVE_SIMULADA), True),
    (errors.ClientError(429, {'error': {'message': CLAVE_SIMULADA, 'code': 429}}), False),
    (errors.ServerError(504, {'error': {'message': CLAVE_SIMULADA, 'code': 504}}), True),
])
def test_fallos_timeout_sin_reintentar_ni_filtrar_secretos(error, timeout, caplog):
    cliente = ClienteSimulado(error=error)
    resultado = procesar(cliente)
    assert resultado.origen == 'RESPALDO_LONGITUD'
    assert ('tiempo máximo' in resultado.error) is timeout
    assert CLAVE_SIMULADA not in resultado.error + caplog.text
    assert len(cliente.llamadas) == 1


def test_error_directo_del_adaptador_sin_causa_externa():
    adaptador = EvaluadorGemini(CONFIGURACION, cliente=ClienteSimulado(error=RuntimeError(CLAVE_SIMULADA)))
    try:
        with pytest.raises(RuntimeError) as error:
            adaptador.evaluar(CONTEXTO)
        assert error.value.__suppress_context__ is True
        assert error.value.__cause__ is None
        assert CLAVE_SIMULADA not in str(error.value)
    finally:
        adaptador.cerrar()


def test_log_externo_con_clave_y_traceback_se_sanea(caplog):
    def observar():
        try:
            raise RuntimeError(CLAVE_SIMULADA)
        except RuntimeError:
            logging.getLogger('google.genai').exception('Falló %s', CLAVE_SIMULADA)
    procesar(ClienteSimulado(observar=observar))
    assert 'omitido' in caplog.text
    assert CLAVE_SIMULADA not in caplog.text


def test_sdk_real_con_transporte_simulado_no_reintenta_429(monkeypatch):
    llamadas = []
    constructor = genai.Client
    def transporte(peticion):
        llamadas.append(peticion)
        assert peticion.extensions['timeout']['read'] == 1.25
        return httpx.Response(429, json={'error': {'code': 429, 'message': CLAVE_SIMULADA, 'status': 'RESOURCE_EXHAUSTED'}})
    cliente_http = httpx.Client(transport=httpx.MockTransport(transporte))
    def crear(**argumentos):
        assert argumentos['vertexai'] is False
        assert argumentos['http_options'].retry_options.attempts == 1
        assert argumentos['http_options'].timeout == 1250
        argumentos['http_options'].httpx_client = cliente_http
        return constructor(**argumentos)
    monkeypatch.setattr(genai, 'Client', crear)
    adaptador = EvaluadorGemini(replace(CONFIGURACION, timeout_segundos=1.25))
    try:
        resultado = evaluar_respuesta(CONTEXTO, 40, 'Más', adaptador)
        assert resultado.origen == 'RESPALDO_LONGITUD'
        assert len(llamadas) == 1
        assert CLAVE_SIMULADA not in resultado.error
    finally:
        adaptador.cerrar()
        cliente_http.close()


def test_cliente_propio_se_cierra_y_error_inicial_saneado(monkeypatch):
    cliente = ClienteSimulado()
    monkeypatch.setattr(genai, 'Client', lambda **kwargs: cliente)
    adaptador = EvaluadorGemini(CONFIGURACION)
    adaptador.cerrar()
    assert cliente.cierres == 1
    def fallar(**kwargs):
        raise RuntimeError(CLAVE_SIMULADA)
    monkeypatch.setattr(genai, 'Client', fallar)
    with pytest.raises(RuntimeError, match='No se pudo inicializar') as error:
        EvaluadorGemini(CONFIGURACION)
    assert CLAVE_SIMULADA not in str(error.value)


@pytest.mark.parametrize('faltantes', [['C1'], ['C1', 'C2']])
def test_adaptador_rechaza_criterios_ya_cumplidos_en_el_seguimiento(faltantes):
    contexto = replace(CONTEXTO, criterios_faltantes_previos=('C2',), conversacion=ConversacionEvaluacion(
        CONTEXTO.conversacion.texto_inicial, (TurnoEvaluacion('¿Cuándo?', 'En el siguiente trabajo.'),)))
    cliente = ClienteSimulado(respuesta_sdk({**VAGA, 'criterios_faltantes': faltantes}))
    resultado = procesar(cliente, contexto)
    assert len(cliente.llamadas) == 1 and resultado.origen == 'RESPALDO_LONGITUD'
    assert resultado.clasificacion == 'NO_EVALUADA' and resultado.pregunta is None
    assert CLAVE_SIMULADA not in resultado.error


def test_sdk_con_transporte_simulado_envia_inicial_y_ambos_turnos_con_esquema_v2(monkeypatch):
    llamadas = []
    salidas = [VAGA, VAGA, ADECUADA]
    constructor = genai.Client
    def transporte(peticion):
        llamada = json.loads(peticion.content)
        llamadas.append(llamada)
        return httpx.Response(200, json={'candidates': [{
            'content': {'role': 'model', 'parts': [{'text': json.dumps(salidas[len(llamadas) - 1])}]},
            'finishReason': 'STOP'}]})
    cliente_http = httpx.Client(transport=httpx.MockTransport(transporte))
    def crear(**argumentos):
        assert argumentos['http_options'].retry_options.attempts == 1
        argumentos['http_options'].httpx_client = cliente_http
        return constructor(**argumentos)
    monkeypatch.setattr(genai, 'Client', crear)
    adaptador = EvaluadorGemini(CONFIGURACION)
    contexto = replace(CONTEXTO, respuestas_anteriores=(RespuestaAnterior('¿Qué habilidad?', ConversacionEvaluacion(
        'Comunicación', (TurnoEvaluacion('¿En qué situación?', 'En grupos.'), TurnoEvaluacion('¿Por qué?', None)))),))
    try:
        for orden in range(3):
            resultado = evaluar_respuesta(contexto, 40, 'Cuéntame más', adaptador)
            assert resultado.origen == 'LLM'
            configuracion = llamadas[-1]['generationConfig']
            assert configuracion['temperature'] == 0.2 and configuracion['candidateCount'] == 1
            assert configuracion['responseMimeType'] == 'application/json'
            assert configuracion['responseJsonSchema']['required'] == list(ADECUADA)
            pensamiento = configuracion['thinkingConfig']
            # ProtoJSON admite el nombre original y su equivalente lowerCamelCase.
            assert pensamiento.get('thinkingLevel', pensamiento.get('thinking_level')) == 'MINIMAL'
            assert llamadas[-1]['systemInstruction']['parts'][0]['text'] == PROMPT_REGISTRO_V2
            assert CLAVE_SIMULADA not in json.dumps(llamadas[-1])
            datos = json.loads(llamadas[-1]['contents'][0]['parts'][0]['text'])
            assert datos['conversacion'] == json.loads(resultado.texto_evaluado)
            assert len(datos['conversacion']['turnos']) == orden
            assert datos['criterios_faltantes_previos'] == (['C1', 'C2'] if orden == 0 else ['C2'])
            assert datos['respuestas_anteriores'][0]['conversacion']['turnos'][-1]['respuesta'] is None
            if orden < 2:
                contexto = replace(contexto, criterios_faltantes_previos=resultado.criterios_faltantes,
                    conversacion=ConversacionEvaluacion(contexto.conversacion.texto_inicial,
                        contexto.conversacion.turnos + (TurnoEvaluacion(resultado.pregunta, f'Respuesta del turno {orden + 1}'),)))
        assert len(llamadas) == 3 and resultado.clasificacion == 'ADECUADA'
    finally:
        adaptador.cerrar()
        cliente_http.close()
