"""Enumerados compartidos del registro, independientes de la persistencia."""

from enum import StrEnum


class ClasificacionRespuesta(StrEnum):
    ADECUADA = "ADECUADA"
    VAGA = "VAGA"
    NO_EVALUADA = "NO_EVALUADA"


class EstadoRespuestaRegistro(StrEnum):
    BORRADOR = "BORRADOR"
    PENDIENTE_SEGUIMIENTO = "PENDIENTE_SEGUIMIENTO"
    FINAL = "FINAL"


class OrigenEvaluacion(StrEnum):
    LLM = "LLM"
    RESPALDO_LONGITUD = "RESPALDO_LONGITUD"
