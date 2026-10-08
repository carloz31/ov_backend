"""Fase 6: exclusivamente clientes y transportes simulados; sin red."""

import json
import logging
import re
import socket
from dataclasses import replace
from pathlib import Path
from urllib.parse import quote

import httpx
import pytest
from fastapi.testclient import TestClient
from google import genai
from google.genai import errors, types
from scripts import evaluar_gemini as script
from sqlalchemy import event

from app import main as modulo_main
from app.config import (
    ConfiguracionRegistro, cargar_configuracion_registro, crear_evaluador_registro,
)
from app.services.registro.evaluacion import (
    ContextoEvaluacion, ConversacionEvaluacion, CriterioEvaluacion, EvaluadorFalso,
    RespuestaAnterior, TurnoEvaluacion, evaluar_respuesta,
)
from app.services.registro.gemini import EvaluadorGemini, razonamiento_minimo
from app.services.registro.prompt import PROMPT_REGISTRO_V2


CLAVE_SIMULADA = 'clave-sintetica-solo-pruebas'
CONFIGURACION = ConfiguracionRegistro('gemini', clave=CLAVE_SIMULADA)
CONTEXTO = ContextoEvaluacion(
    'Mi plan para fortalecer una habilidad', '¿Qué harás para practicarla?',
    (CriterioEvaluacion('C1', 'Acción concreta'), CriterioEvaluacion('C2', 'Situación concreta')),
    (RespuestaAnterior('¿Qué habilidad?', ConversacionEvaluacion('Asertividad en los trabajos grupales')),),
    ConversacionEvaluacion('En el trabajo de Comunicación del jueves voy a decir mi opinión al menos una vez.'),
    ('C1', 'C2'),
)
ADECUADA = dict(clasificacion='ADECUADA', criterios_faltantes=[], pregunta=None, requiere_atencion=False)
VAGA = dict(clasificacion='VAGA', criterios_faltantes=['C2'], pregunta='¿Cuándo lo practicarías?', requiere_atencion=False)


@pytest.fixture(autouse=True)
def impedir_red(monkeypatch):
    conectar = socket.socket.connect
    def conectar_solo_bucle_interno(instancia, direccion):
        # Windows crea el socketpair de asyncio mediante TCP de loopback.
        if isinstance(direccion, tuple) and direccion[0] in ('127.0.0.1', '::1'):
            return conectar(instancia, direccion)
        raise AssertionError('Las pruebas Gemini no pueden acceder a la red')
    def prohibida(*args, **kwargs):
        raise AssertionError('Las pruebas Gemini no pueden acceder a la red')
    monkeypatch.setattr(socket.socket, 'connect', conectar_solo_bucle_interno)
    monkeypatch.setattr(socket, 'create_connection', prohibida)


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


class ClienteConversacionesSimulado(ClienteSimulado):
    def __init__(self, *, respuestas=None, errores=None, observar=None):
        super().__init__(observar=observar)
        self.respuestas = respuestas or {}
        self.errores = errores or {}

    def generate_content(self, **argumentos):
        contexto = json.loads(argumentos['contents'])
        numero = next(n for n, caso in enumerate(script.CASOS, 1)
                      if caso.texto == contexto['conversacion']['texto_inicial'])
        turno = len(contexto['conversacion']['turnos'])
        datos = ADECUADA
        if numero == 14:
            datos = {**ADECUADA, 'requiere_atencion': True}
        elif numero == 15 and turno == 0:
            datos = {**VAGA, 'pregunta': '¿En qué situaciones notas que te cuesta comunicarte?'}
        elif numero == 16:
            datos = {**VAGA, 'criterios_faltantes': ['C1', 'C2'], 'pregunta': (
                '¿Qué harás exactamente y en qué momento?' if turno == 0 else
                '¿Qué acción concreta podrías probar en tu próximo trabajo grupal?')}
        self.respuesta = respuesta_sdk(self.respuestas.get((numero, turno), datos))
        self.error = self.errores.get((numero, turno))
        return super().generate_content(**argumentos)


def procesar(cliente, contexto=CONTEXTO, configuracion=CONFIGURACION):
    adaptador = EvaluadorGemini(configuracion, cliente=cliente)
    try:
        resultado = evaluar_respuesta(contexto, 40, 'Cuéntame más', adaptador,
                                      modelo=configuracion.modelo, tiempo_maximo_segundos=configuracion.timeout_segundos)
        assert adaptador.latencia_ms is not None
        return resultado
    finally:
        adaptador.cerrar()


def test_configuracion_predeterminada_sin_clave(tmp_path):
    configuracion = cargar_configuracion_registro(tmp_path / 'ausente', entorno={})
    assert configuracion == ConfiguracionRegistro()
    assert isinstance(crear_evaluador_registro(configuracion), EvaluadorFalso)


def test_env_precedencia_sin_mutar_entorno_ni_interpolar(tmp_path, monkeypatch):
    ruta = tmp_path / '.env'
    ruta.write_text('EVALUADOR=gemini\nGEMINI_API_KEY=valor-${NO_INTERPOLAR}\n'
                    'GEMINI_MODELO=desde-archivo\nGEMINI_TIMEOUT_SEGUNDOS=3.5\n', encoding='utf-8')
    monkeypatch.setenv('GEMINI_MODELO', 'desde-proceso')
    configuracion = cargar_configuracion_registro(ruta, entorno={'GEMINI_MODELO': 'desde-proceso'})
    assert configuracion.modelo == 'desde-proceso'
    assert configuracion.timeout_segundos == 3.5
    assert configuracion.clave == 'valor-${NO_INTERPOLAR}'
    assert 'valor-' not in repr(configuracion)
    assert cargar_configuracion_registro(ruta, entorno={'EVALUADOR': 'falso'}).clave is None


@pytest.mark.parametrize('valores,mensaje', [
    ({'EVALUADOR': 'gemini'}, 'Falta GEMINI_API_KEY'),
    ({'EVALUADOR': 'gemini', 'GEMINI_API_KEY': '  '}, 'Falta GEMINI_API_KEY'),
    ({'EVALUADOR': CLAVE_SIMULADA}, 'EVALUADOR debe ser'),
    ({'EVALUADOR': ''}, 'EVALUADOR debe ser'),
    ({'GEMINI_MODELO': '  '}, 'GEMINI_MODELO no puede'),
    *[({'GEMINI_TIMEOUT_SEGUNDOS': valor}, 'GEMINI_TIMEOUT_SEGUNDOS debe ser')
      for valor in ('', '0', '-1', 'NaN', 'inf', '-inf', CLAVE_SIMULADA)],
])
def test_configuracion_invalida_saneada(tmp_path, valores, mensaje):
    with pytest.raises(RuntimeError, match=mensaje) as error:
        cargar_configuracion_registro(tmp_path / 'ausente', entorno=valores)
    assert CLAVE_SIMULADA not in str(error.value)


def test_clave_faltante_impide_arranque_sin_crear_bd(tmp_path, monkeypatch):
    def cargar():
        return cargar_configuracion_registro(tmp_path / 'ausente', entorno={'EVALUADOR': 'gemini'})
    monkeypatch.setattr(modulo_main, 'cargar_configuracion_registro', cargar)
    ruta = tmp_path / 'no_creada.db'
    with pytest.raises(RuntimeError, match='Falta GEMINI_API_KEY'):
        with TestClient(modulo_main.crear_aplicacion(f'sqlite:///{ruta.as_posix()}')):
            pass
    assert not ruta.exists()


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


@pytest.mark.parametrize('respuesta,error', [(respuesta_sdk(VAGA), None), (None, httpx.ReadTimeout(CLAVE_SIMULADA))])
def test_integracion_aplicacion_cliente_simulado_sin_conexion_y_con_metadatos(tmp_path, monkeypatch, respuesta, error):
    app = modulo_main.crear_aplicacion(f'sqlite:///{(tmp_path / "registro.db").as_posix()}')
    def observar():
        assert app.state.motor_bd.pool.checkedout() == 0
    cliente_simulado = ClienteSimulado(respuesta, error, observar)
    monkeypatch.setattr(modulo_main, 'cargar_configuracion_registro', lambda: CONFIGURACION)
    monkeypatch.setattr(genai, 'Client', lambda **kwargs: cliente_simulado)
    with TestClient(app) as cliente:
        envio = cliente.post('/acciones/registro/enviar', json={
            'cuenta': 'est-ana', 'actividad': 'REG-ACT08', 'item': 'REG-HAB-2', 'texto': CONTEXTO.conversacion.texto_inicial,
        })
        assert envio.status_code == 200
        assert envio.json()['estado'] == ('FINAL' if error else 'PENDIENTE_SEGUIMIENTO')
        assert not set(envio.json()) & {'clasificacion', 'criterios_faltantes', 'requiere_atencion', 'modelo', 'error'}
        auditoria = cliente.get('/demo/registro/est-ana/REG-ACT08/evaluaciones').json()[0]
        assert auditoria['modelo'] == CONFIGURACION.modelo
        assert auditoria['version_prompt'] == 'v2'
        assert auditoria['latencia_ms'] >= 0
        assert auditoria['origen'] == ('RESPALDO_LONGITUD' if error else 'LLM')
        assert CLAVE_SIMULADA not in json.dumps(auditoria)
    assert cliente_simulado.cierres == 1


def test_script_16_casos_contextos_y_reporte_simulado(tmp_path):
    assert len(script.CASOS) == 16
    assert script.CASOS[11].texto == 'Empatía, aunque creo que está sobrevalorada; igual me serviría, porque cuando mis amigos me cuentan sus problemas no sé qué decirles.'
    assert script.CASOS[13].esperada == 'requiere atención'
    assert script.CASOS[6].texto == 'Voy a practicar hablando más.'
    assert script.CASOS[6].esperada == 'VAGA (falta C2)'
    assert script.CASOS[15].texto == 'Voy a esforzarme más.'
    ruta = tmp_path / 'reporte.md'
    esperas = []
    cliente = ClienteConversacionesSimulado()
    adaptador = EvaluadorGemini(CONFIGURACION, cliente=cliente)
    try:
        resultados = script.ejecutar_casos(adaptador, CONFIGURACION, ruta, pausa=7, esperar=esperas.append)
    finally:
        adaptador.cerrar()
    assert esperas == [7] * 17
    assert len(cliente.llamadas) == len(resultados) == 18
    assert all(r.evaluacion.origen == 'LLM' for r in resultados)
    llamadas_iniciales = [llamada for llamada in cliente.llamadas
                          if not json.loads(llamada['contents'])['conversacion']['turnos']]
    for caso, llamada in zip(script.CASOS, llamadas_iniciales, strict=True):
        datos = json.loads(llamada['contents'])
        assert datos['conversacion']['texto_inicial'] == caso.texto
        orden = int(caso.item[-1]) - 1
        assert [r['conversacion']['texto_inicial'] for r in datos['respuestas_anteriores']] == [script.CASOS[1].texto, script.CASOS[5].texto][:orden]
        assert [c['codigo'] for c in datos['criterios']] == ['C1', 'C2']
    for numero, faltantes in [(15, ['C2']), (16, ['C1', 'C2'])]:
        inicial, turno = [fila for fila in resultados if fila.numero == numero]
        llamada = cliente.llamadas[15 if numero == 15 else 17]
        datos = json.loads(llamada['contents'])
        assert datos['criterios_faltantes_previos'] == faltantes
        assert datos['conversacion']['texto_inicial'] == script.CASOS[numero - 1].texto
        assert datos['conversacion']['turnos'] == [{
            'pregunta': inicial.evaluacion.pregunta, 'respuesta': script.CASOS[numero - 1].respuesta_turno_1}]
        assert turno.pregunta_respondida == inicial.evaluacion.pregunta
        assert json.loads(turno.evaluacion.texto_evaluado) == datos['conversacion']
        assert turno.evaluacion.clasificacion == ('ADECUADA' if numero == 15 else 'VAGA')
        if numero == 16:
            assert turno.evaluacion.pregunta != inicial.evaluacion.pregunta
    reporte = ruta.read_text(encoding='utf-8')
    assert reporte.count('\n| ') == 19
    assert 'requiere atención' in reporte
    assert 'Turno 1' in reporte and 'Pregunta respondida' in reporte and 'Pregunta generada' in reporte
    assert resultados[-1].evaluacion.pregunta in reporte
    assert CLAVE_SIMULADA not in reporte


def test_script_fallo_no_interrumpe_casos_ni_expone_clave(tmp_path):
    ruta = tmp_path / 'fallos.md'
    resultados = script.ejecutar_casos(EvaluadorFalso(), CONFIGURACION, ruta, pausa=0, esperar=lambda _: None)
    assert len(resultados) == 18
    assert all(fila.evaluacion is None for fila in resultados if fila.turno)
    cliente = ClienteSimulado(error=RuntimeError(CLAVE_SIMULADA))
    adaptador = EvaluadorGemini(CONFIGURACION, cliente=cliente)
    try:
        resultados = script.ejecutar_casos(adaptador, CONFIGURACION, ruta, pausa=0, esperar=lambda _: None)
    finally:
        adaptador.cerrar()
    assert len(cliente.llamadas) == 16
    assert all(r.evaluacion.origen == 'RESPALDO_LONGITUD' for r in resultados if r.evaluacion is not None)
    assert resultados[-1].evaluacion is None and 'genérico' in resultados[-1].observacion
    assert CLAVE_SIMULADA not in ruta.read_text(encoding='utf-8')
    assert script.celda('a|b\n<script>') == 'a&#124;b<br>&lt;script&gt;'


@pytest.mark.parametrize('pausa', [-1, float('nan'), float('inf')])
def test_script_rechaza_pausa_invalida_antes_de_llamar(tmp_path, pausa):
    cliente = ClienteSimulado()
    with pytest.raises(ValueError, match='pausa'):
        script.ejecutar_casos(cliente, CONFIGURACION, tmp_path / 'no_creado', pausa=pausa)
    assert cliente.llamadas == []


def test_cli_ayuda_no_inicializa_cliente(monkeypatch, capsys):
    def prohibida(*args, **kwargs):
        raise AssertionError('La ayuda no crea un cliente')
    monkeypatch.setattr(script, 'EvaluadorGemini', prohibida)
    with pytest.raises(SystemExit) as salida:
        script.main(['--help'])
    assert salida.value.code == 0
    assert '--pausa' in capsys.readouterr().out


def test_cli_fallo_externo_saneado_y_cliente_cerrado(monkeypatch, capsys):
    cliente = ClienteSimulado()
    # No escribir el reporte real; esta prueba solo verifica el límite del CLI.
    monkeypatch.setattr(script, 'cargar_configuracion_registro', lambda **kwargs: CONFIGURACION)
    monkeypatch.setattr(script, 'EvaluadorGemini', lambda _: cliente)
    cliente.cerrar = cliente.close
    def fallar(*args, **kwargs):
        raise RuntimeError(CLAVE_SIMULADA)
    monkeypatch.setattr(script, 'ejecutar_casos', fallar)
    assert script.main(['--pausa', '0']) == 1
    salida = capsys.readouterr()
    assert 'No se pudo generar' in salida.err
    assert CLAVE_SIMULADA not in salida.err + salida.out
    assert cliente.cierres == 1


def test_prompt_y_casos_coinciden_con_la_especificacion_v2():
    especificacion = (Path(__file__).resolve().parents[1] / 'docs' / 'spec-demo-registro-gemini.md').read_text(encoding='utf-8')
    prompt = especificacion.split('Instrucción de sistema (versión `v2`):', 1)[1].split('```', 2)[1].strip()
    assert PROMPT_REGISTRO_V2 == prompt
    apartado = especificacion.split('## 10. Prueba con Gemini real', 1)[1].split('## 11.', 1)[0]
    iniciales = re.findall(r'^\| (\d+) \| (REG-HAB-\d) \| ([^|]*?) \| ([^|]*?) \|$', apartado, re.MULTILINE)
    assert len(iniciales) == 14
    for numero, item, texto, esperada in iniciales:
        caso = script.CASOS[int(numero) - 1]
        assert (caso.item, caso.texto, caso.esperada) == (item, texto, esperada)
    conversaciones = re.findall(r'^\| (15|16) \| (REG-HAB-\d) \| (.*?) \| (.*?) \| (.*?) \|$', apartado, re.MULTILINE)
    assert len(conversaciones) == 2
    for numero, item, texto, respuesta, revision in conversaciones:
        caso = script.CASOS[int(numero) - 1]
        assert (caso.item, caso.texto, caso.respuesta_turno_1) == (item, texto, respuesta)


@pytest.mark.parametrize('datos', [ADECUADA, {**ADECUADA, 'requiere_atencion': True},
                                  {**VAGA, 'requiere_atencion': True}])
def test_script_no_inventa_turnos_si_el_inicial_finaliza(tmp_path, datos):
    cliente = ClienteConversacionesSimulado(respuestas={(15, 0): datos, (16, 0): datos})
    adaptador = EvaluadorGemini(CONFIGURACION, cliente=cliente)
    esperas = []
    try:
        filas = script.ejecutar_casos(adaptador, CONFIGURACION, tmp_path / 'omitidos.md', pausa=2, esperar=esperas.append)
    finally:
        adaptador.cerrar()
    assert len(cliente.llamadas) == 16 and esperas == [2] * 15
    turnos = [fila for fila in filas if fila.turno]
    assert len(turnos) == 2
    assert all(fila.evaluacion is None and fila.pregunta_respondida == '' and 'No ejecutado' in fila.observacion
               for fila in turnos)


@pytest.mark.parametrize('numero', [15, 16])
@pytest.mark.parametrize('fallo', ['timeout', 'invalido', 'externo'])
def test_script_fallo_del_turno_sigue_con_los_demas_casos_y_no_reintenta(tmp_path, numero, fallo):
    errores = {(numero, 1): (httpx.ReadTimeout(CLAVE_SIMULADA) if fallo == 'timeout' else RuntimeError(CLAVE_SIMULADA))}
    respuestas = {}
    if fallo == 'invalido':
        errores = {}
        respuestas[numero, 1] = {**ADECUADA, 'criterios_faltantes': ['C1']}
    cliente = ClienteConversacionesSimulado(respuestas=respuestas, errores=errores)
    adaptador = EvaluadorGemini(CONFIGURACION, cliente=cliente)
    ruta = tmp_path / 'fallo-turno.md'
    try:
        filas = script.ejecutar_casos(adaptador, CONFIGURACION, ruta, pausa=0, esperar=lambda _: None)
    finally:
        adaptador.cerrar()
    assert len(cliente.llamadas) == 18
    turno = next(fila for fila in filas if fila.numero == numero and fila.turno == 1)
    assert turno.evaluacion.origen == 'RESPALDO_LONGITUD'
    assert turno.evaluacion.clasificacion == 'NO_EVALUADA' and turno.evaluacion.pregunta is None
    assert turno.evaluacion.error and CLAVE_SIMULADA not in turno.evaluacion.error
    assert CLAVE_SIMULADA not in ruta.read_text(encoding='utf-8')


def test_script_respaldo_corto_genera_turno_generico_sin_evaluar_ni_pausar_otra_vez(tmp_path):
    cliente = ClienteConversacionesSimulado(errores={(16, 0): httpx.ReadTimeout(CLAVE_SIMULADA)})
    adaptador = EvaluadorGemini(CONFIGURACION, cliente=cliente)
    esperas = []
    try:
        filas = script.ejecutar_casos(adaptador, CONFIGURACION, tmp_path / 'generico.md', pausa=3, esperar=esperas.append)
    finally:
        adaptador.cerrar()
    assert len(cliente.llamadas) == 17 and esperas == [3] * 16
    inicial, turno = [fila for fila in filas if fila.numero == 16]
    assert inicial.evaluacion.origen == 'RESPALDO_LONGITUD' and inicial.evaluacion.clasificacion == 'VAGA'
    assert inicial.evaluacion.criterios_faltantes == ('C1', 'C2')
    assert turno.evaluacion is None and turno.pregunta_respondida == inicial.evaluacion.pregunta
    assert 'sin nueva evaluación' in turno.observacion
    assert json.loads(cliente.llamadas[-1]['contents'])['conversacion']['texto_inicial'] == 'Voy a esforzarme más.'


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


def test_script_reporte_escapa_html_y_omite_clave_literal_y_codificada(tmp_path):
    clave = 'clave &"sintetica?'  # Solo dato inventado para la prueba.
    configuracion = replace(CONFIGURACION, clave=clave)
    pregunta = f'<script>|\n{clave} / {quote(clave, safe="")}'
    cliente = ClienteSimulado(respuesta_sdk({**VAGA, 'pregunta': pregunta}))
    adaptador = EvaluadorGemini(configuracion, cliente=cliente)
    ruta = tmp_path / 'saneado.md'
    try:
        script.ejecutar_casos(adaptador, configuracion, ruta, pausa=0, esperar=lambda _: None)
    finally:
        adaptador.cerrar()
    reporte = ruta.read_text(encoding='utf-8')
    assert clave not in reporte and quote(clave, safe='') not in reporte and script.celda(clave) not in reporte
    assert '[secreto omitido]' in reporte and '&lt;script&gt;&#124;<br>' in reporte
    assert '<script>' not in reporte and reporte.count('\n| ') == 19


def test_script_libera_conexiones_antes_del_evaluador_y_solo_prepara_definiciones_en_memoria(tmp_path, monkeypatch):
    crear_original = script.crear_motor_bd
    activas, sentencias = set(), []
    preparado = []
    def crear(url):
        assert url == 'sqlite:///:memory:'
        motor = crear_original(url)
        event.listen(motor, 'checkout', lambda conexion, registro, proxy: activas.add(id(conexion)))
        event.listen(motor, 'checkin', lambda conexion, registro: activas.discard(id(conexion)))
        event.listen(motor, 'before_cursor_execute', lambda *args: sentencias.append(args[2]))
        return motor
    monkeypatch.setattr(script, 'crear_motor_bd', crear)
    def observar():
        assert not activas
        if not preparado:
            preparado.append(len(sentencias))
        assert len(sentencias) == preparado[0]
    cliente = ClienteConversacionesSimulado(observar=observar)
    adaptador = EvaluadorGemini(CONFIGURACION, cliente=cliente)
    try:
        script.ejecutar_casos(adaptador, CONFIGURACION, tmp_path / 'sin-bd.md', pausa=0, esperar=lambda _: None)
    finally:
        adaptador.cerrar()
    assert len(cliente.llamadas) == 18 and preparado[0] > 0 and not activas
    assert not any(sentencia.startswith(('INSERT INTO respuesta_registro ', 'INSERT INTO turno_seguimiento ',
                                         'INSERT INTO evaluacion_respuesta ', 'INSERT INTO evento_uso '))
                   for sentencia in sentencias)


def test_cli_exito_simulado_cierra_cliente_y_conserva_el_proveedor_del_entorno(tmp_path, monkeypatch, capsys):
    import os
    previo = os.environ['EVALUADOR']
    cliente = ClienteConversacionesSimulado()
    monkeypatch.setattr(genai, 'Client', lambda **kwargs: cliente)
    def configurar(**argumentos):
        assert argumentos['entorno']['EVALUADOR'] == 'gemini'
        return CONFIGURACION
    monkeypatch.setattr(script, 'cargar_configuracion_registro', configurar)
    ejecutar_original = script.ejecutar_casos
    ruta = tmp_path / 'cli.md'
    monkeypatch.setattr(script, 'ejecutar_casos', lambda evaluador, configuracion, **opciones:
        ejecutar_original(evaluador, configuracion, ruta, esperar=lambda _: None, **opciones))
    assert script.main(['--pausa', '0']) == 0
    assert ruta.exists() and len(cliente.llamadas) == 18 and cliente.cierres == 1
    assert os.environ['EVALUADOR'] == previo
    salida = capsys.readouterr()
    assert 'Reporte generado' in salida.out and salida.err == ''
    assert CLAVE_SIMULADA not in salida.out
