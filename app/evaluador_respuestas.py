"""Evaluación de completitud de §6; sin base de datos, routers ni configuración de red."""

from dataclasses import asdict, dataclass
import json
import re
from math import isfinite
from time import perf_counter
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, ValidationError

from app.configuracion_metodos import TIEMPO_MAXIMO_EVALUACION_SEGUNDOS, VERSION_PROMPT_REGISTRO
from app.tipos_registro import ClasificacionRespuesta, OrigenEvaluacion


@dataclass(frozen=True, slots=True)
class CriterioEvaluacion:
    codigo: str
    descripcion: str


@dataclass(frozen=True, slots=True)
class TurnoEvaluacion:
    pregunta: str
    respuesta: str | None


@dataclass(frozen=True, slots=True)
class ConversacionEvaluacion:
    texto_inicial: str
    turnos: tuple[TurnoEvaluacion, ...] = ()

    @property
    def texto_actual(self) -> str | None:
        return self.turnos[-1].respuesta if self.turnos else self.texto_inicial


def serializar_conversacion(conversacion: ConversacionEvaluacion) -> str:
    return json.dumps(asdict(conversacion), ensure_ascii=False)


@dataclass(frozen=True, slots=True)
class RespuestaAnterior:
    consigna: str
    conversacion: ConversacionEvaluacion


@dataclass(frozen=True, slots=True)
class ContextoEvaluacion:
    titulo_actividad: str
    consigna: str
    criterios: tuple[CriterioEvaluacion, ...]
    respuestas_anteriores: tuple[RespuestaAnterior, ...]
    conversacion: ConversacionEvaluacion
    criterios_faltantes_previos: tuple[str, ...]


class ResultadoEvaluacion(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    clasificacion: Literal["ADECUADA", "VAGA"]
    criterios_faltantes: list[str]
    pregunta: str | None
    requiere_atencion: bool


class EvaluadorRespuestas(Protocol):
    def evaluar(self, contexto: ContextoEvaluacion) -> ResultadoEvaluacion: ...


class ErrorTextoVacio(ValueError):
    """La acción traducirá este rechazo de entrada a HTTP 422."""


class ErrorResultadoEvaluacion(ValueError):
    """Resultado que no cumple el esquema o las reglas de consistencia."""


@dataclass(frozen=True, slots=True)
class EvaluacionProcesada:
    origen: OrigenEvaluacion
    clasificacion: ClasificacionRespuesta
    criterios_faltantes: tuple[str, ...]
    pregunta: str | None
    requiere_atencion: bool
    modelo: str | None
    version_prompt: str | None
    latencia_ms: int | None
    error: str | None
    texto_evaluado: str


class EvaluadorFalso:
    def __init__(self):
        self.contextos: list[ContextoEvaluacion] = []

    def evaluar(self, contexto: ContextoEvaluacion) -> ResultadoEvaluacion:
        self.contextos.append(contexto)
        texto = contexto.conversacion.texto_actual
        if "[falla]" in texto:
            raise RuntimeError("Fallo simulado del evaluador")
        atencion = "[atencion]" in texto
        marcas = re.findall(r"\[falta:([^\]]*)\]", texto)
        vaga = bool(marcas or "[vaga]" in texto) and not atencion
        faltantes = list(contexto.criterios_faltantes_previos)
        if marcas:
            faltantes = list(dict.fromkeys(
                codigo.strip() for marca in marcas for codigo in marca.split(',') if codigo.strip()
            ))
        return ResultadoEvaluacion(
            clasificacion="VAGA" if vaga else "ADECUADA",
            criterios_faltantes=faltantes if vaga else [],
            pregunta=f"¿Podrías contarme más sobre {', '.join(faltantes)}?" if vaga else None,
            requiere_atencion=atencion,
        )


def validar_resultado(resultado: ResultadoEvaluacion, contexto: ContextoEvaluacion) -> ResultadoEvaluacion:
    # Validar también instancias construidas sin validación o listas mutadas.
    datos = resultado.model_dump(warnings=False) if isinstance(resultado, ResultadoEvaluacion) else resultado
    try:
        validado = ResultadoEvaluacion.model_validate(datos)
    except ValidationError:
        raise ErrorResultadoEvaluacion("El resultado no cumple el esquema de evaluación") from None
    codigos = {criterio.codigo for criterio in contexto.criterios}
    if any(codigo not in codigos for codigo in validado.criterios_faltantes):
        raise ErrorResultadoEvaluacion("Los criterios faltantes no pertenecen al ítem")
    if not set(validado.criterios_faltantes).issubset(contexto.criterios_faltantes_previos):
        raise ErrorResultadoEvaluacion("No pueden faltar criterios ya cumplidos")
    if len(validado.criterios_faltantes) != len(set(validado.criterios_faltantes)):
        raise ErrorResultadoEvaluacion("Los criterios faltantes no pueden repetirse")
    if validado.clasificacion == "ADECUADA" and validado.criterios_faltantes:
        raise ErrorResultadoEvaluacion("Una respuesta adecuada no puede tener criterios faltantes")
    if validado.clasificacion == "VAGA" and not validado.requiere_atencion and (
        not validado.criterios_faltantes or validado.pregunta is None or not validado.pregunta.strip()
    ):
        raise ErrorResultadoEvaluacion("Una respuesta vaga requiere criterios y una pregunta no vacíos")
    return validado


def evaluar_respuesta(
    contexto: ContextoEvaluacion, min_caracteres: int, repregunta_generica: str, evaluador: EvaluadorRespuestas,
    *, modelo: str | None = None, version_prompt: str = VERSION_PROMPT_REGISTRO,
    tiempo_maximo_segundos: float = TIEMPO_MAXIMO_EVALUACION_SEGUNDOS,
) -> EvaluacionProcesada:
    """Procesa un envío; la acción guardará el resultado y decidirá su estado.

    El adaptador debe limitar la espera de su llamada. Aquí se capturan timeouts
    y también se descarta un resultado que llega después del tiempo máximo.
    """
    if contexto.conversacion.texto_actual is None or not contexto.conversacion.texto_actual.strip():
        raise ErrorTextoVacio("El texto de la respuesta no puede estar vacío")
    if type(min_caracteres) is not int or min_caracteres < 0:
        raise ValueError("El mínimo de caracteres debe ser un entero no negativo")
    if isinstance(tiempo_maximo_segundos, bool) or not isfinite(tiempo_maximo_segundos) or tiempo_maximo_segundos <= 0:
        raise ValueError("El tiempo máximo de evaluación debe ser positivo y finito")
    texto_evaluado = serializar_conversacion(contexto.conversacion)
    inicio = perf_counter()
    resultado, error = None, None
    try:
        resultado = validar_resultado(evaluador.evaluar(contexto), contexto)
    except TimeoutError:
        error = "Se agotó el tiempo máximo de evaluación"
    except (ErrorResultadoEvaluacion, ValidationError):
        error = "El resultado del evaluador no cumple el esquema o las reglas de consistencia"
    except Exception:
        # Nunca persistir el mensaje de una excepción externa: podría incluir secretos.
        error = "Falló el evaluador de respuestas"
    duracion = perf_counter() - inicio
    latencia_ms = max(0, round(duracion * 1000))
    if duracion > tiempo_maximo_segundos:
        error = "Se agotó el tiempo máximo de evaluación"
    if error is not None:
        corto = not contexto.conversacion.turnos and len(contexto.conversacion.texto_inicial.strip()) < min_caracteres
        if corto and not repregunta_generica.strip():
            raise ValueError("La repregunta genérica no puede estar vacía")
        return EvaluacionProcesada(
            origen=OrigenEvaluacion.RESPALDO_LONGITUD,
            clasificacion=ClasificacionRespuesta.VAGA if corto else ClasificacionRespuesta.NO_EVALUADA,
            criterios_faltantes=tuple(criterio.codigo for criterio in contexto.criterios) if corto else (),
            pregunta=repregunta_generica if corto else None, requiere_atencion=False,
            modelo=modelo, version_prompt=version_prompt, latencia_ms=latencia_ms,
            error=error, texto_evaluado=texto_evaluado,
        )
    return EvaluacionProcesada(
        origen=OrigenEvaluacion.LLM, clasificacion=ClasificacionRespuesta(resultado.clasificacion),
        criterios_faltantes=tuple(resultado.criterios_faltantes), pregunta=resultado.pregunta,
        requiere_atencion=resultado.requiere_atencion, modelo=modelo, version_prompt=version_prompt,
        latencia_ms=latencia_ms, error=None, texto_evaluado=texto_evaluado,
    )
