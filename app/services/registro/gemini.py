"""Adaptador síncrono Gemini: una petición, sin sesiones de base de datos."""

import json
import logging
from dataclasses import asdict
from math import ceil
from threading import local
from time import perf_counter
from urllib.parse import quote

import httpx
from google import genai
from google.genai import errors, types
from pydantic import ValidationError

from app.config import Configuracion, ErrorConfiguracionRegistro
from app.core.parametros import TEMPERATURA_REGISTRO
from app.services.registro.evaluacion import (
    ContextoEvaluacion, ErrorResultadoEvaluacion, ResultadoEvaluacion, validar_resultado,
)
from app.services.registro.prompt import PROMPT_REGISTRO_V2


class ErrorClienteGemini(RuntimeError):
    """Mensaje fijo del adaptador, sin excepciones ni contenido externos."""


class FiltroSecretos(logging.Filter):
    def __init__(self, clave):
        super().__init__()
        self.secretos = (clave, quote(clave, safe=''))

    def filter(self, registro):
        # Tampoco conservar traceback/argumentos externos si contienen la clave.
        mensaje = logging.Formatter().format(registro)
        if any(secreto in mensaje for secreto in self.secretos):
            registro.msg = 'Mensaje externo omitido para proteger la configuración de Gemini'
            registro.args = ()
            registro.exc_info = registro.exc_text = registro.stack_info = None
        return True


def razonamiento_minimo(modelo):
    nombre = modelo.removeprefix('models/')
    if nombre in ('gemini-3.1-flash-lite', 'gemini-3.1-flash-lite-preview', 'gemini-3-flash-preview'):
        return types.ThinkingConfig(thinking_level='minimal')
    if nombre in ('gemini-3.1-pro-preview', 'gemini-3-pro-preview'):
        return types.ThinkingConfig(thinking_level='low')
    if nombre in ('gemini-2.5-flash', 'gemini-2.5-flash-lite'):
        return types.ThinkingConfig(thinking_budget=0)
    if nombre == 'gemini-2.5-pro':
        return types.ThinkingConfig(thinking_budget=128)
    # No descubrir capacidades con una petición ni asumirlas para modelos desconocidos.
    return None


class EvaluadorGemini:
    def __init__(self, configuracion: Configuracion, *, cliente=None):
        if not configuracion.clave:
            raise ErrorConfiguracionRegistro('Falta GEMINI_API_KEY para usar EVALUADOR=gemini')
        self.configuracion = configuracion
        self._metricas = local()
        self._cliente_propio = cliente is None
        self._filtro = FiltroSecretos(configuracion.clave)
        nombres = {'google.genai', 'httpx', 'httpcore'} | {
            nombre for nombre in logging.Logger.manager.loggerDict
            if nombre.startswith(('google.genai.', 'httpx.', 'httpcore.'))
        }
        self._loggers = [logging.getLogger(nombre) for nombre in nombres]
        for logger in self._loggers:
            logger.addFilter(self._filtro)
        try:
            self._cliente = cliente if cliente is not None else genai.Client(
                api_key=configuracion.clave, vertexai=False,
                http_options=types.HttpOptions(
                    timeout=max(1, ceil(configuracion.timeout_segundos * 1000)),
                    retry_options=types.HttpRetryOptions(attempts=1),
                ),
            )
        except Exception:
            self._quitar_filtros()
            raise ErrorClienteGemini('No se pudo inicializar el cliente Gemini') from None

    def evaluar(self, contexto: ContextoEvaluacion) -> ResultadoEvaluacion:
        inicio = perf_counter()
        try:
            return self._evaluar(contexto)
        finally:
            self._metricas.latencia_ms = max(0, round((perf_counter() - inicio) * 1000))

    @property
    def latencia_ms(self):
        return getattr(self._metricas, 'latencia_ms', None)

    def _evaluar(self, contexto: ContextoEvaluacion) -> ResultadoEvaluacion:
        try:
            respuesta = self._cliente.models.generate_content(
                model=self.configuracion.modelo,
                contents=json.dumps(asdict(contexto), ensure_ascii=False),
                config=types.GenerateContentConfig(
                    system_instruction=PROMPT_REGISTRO_V2,
                    temperature=TEMPERATURA_REGISTRO, candidate_count=1,
                    response_mime_type='application/json',
                    response_json_schema=ResultadoEvaluacion.model_json_schema(),
                    thinking_config=razonamiento_minimo(self.configuracion.modelo),
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                ),
            )
            # No usar .text: el SDK puede registrar partes no textuales en sus avisos.
            candidatos = respuesta.candidates or []
            partes = candidatos[0].content.parts if candidatos and candidatos[0].content else []
            texto = ''.join(parte.text for parte in (partes or []) if parte.text and not parte.thought)
            resultado = ResultadoEvaluacion.model_validate_json(texto)
            return validar_resultado(resultado, contexto)
        except (TimeoutError, httpx.TimeoutException):
            raise TimeoutError('Se agotó el tiempo máximo de evaluación') from None
        except errors.APIError as error:
            if error.code in (408, 504):
                raise TimeoutError('Se agotó el tiempo máximo de evaluación') from None
            raise ErrorClienteGemini('Falló la petición a Gemini') from None
        except (ValidationError, ErrorResultadoEvaluacion):
            raise ErrorResultadoEvaluacion('Gemini devolvió un resultado inválido') from None
        except Exception:
            raise ErrorClienteGemini('Falló la petición a Gemini') from None

    def _quitar_filtros(self):
        for logger in self._loggers:
            logger.removeFilter(self._filtro)

    def cerrar(self):
        try:
            if self._cliente_propio:
                self._cliente.close()
        except Exception:
            raise ErrorClienteGemini('No se pudo cerrar el cliente Gemini') from None
        finally:
            self._quitar_filtros()
