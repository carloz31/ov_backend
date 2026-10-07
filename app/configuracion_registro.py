"""Configuración del proveedor; se lee al arrancar, nunca al importar."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from math import isfinite
import os
from pathlib import Path

from dotenv import dotenv_values

from app.configuracion_metodos import MODELO_GEMINI_REGISTRO, TIEMPO_MAXIMO_EVALUACION_SEGUNDOS


RUTA_ENV = Path(__file__).resolve().parent.parent / '.env'


class ErrorConfiguracionRegistro(RuntimeError):
    """Mensaje propio, seguro para mostrar al arrancar o en el script manual."""


@dataclass(frozen=True, slots=True)
class ConfiguracionRegistro:
    evaluador: str = 'falso'
    modelo: str = MODELO_GEMINI_REGISTRO
    timeout_segundos: float = TIEMPO_MAXIMO_EVALUACION_SEGUNDOS
    clave: str | None = field(default=None, repr=False)


def cargar_configuracion_registro(
    ruta: Path = RUTA_ENV, *, entorno: Mapping[str, str] | None = None,
) -> ConfiguracionRegistro:
    try:
        valores = dotenv_values(ruta, interpolate=False)
    except (OSError, UnicodeError):
        raise ErrorConfiguracionRegistro('No se pudo leer la configuración de registro desde .env') from None
    variables = os.environ if entorno is None else entorno
    def leer(nombre, defecto):
        return variables.get(nombre, valores.get(nombre, defecto))

    proveedor = (leer('EVALUADOR', 'falso') or '').strip().lower()
    if proveedor not in ('falso', 'gemini'):
        raise ErrorConfiguracionRegistro('EVALUADOR debe ser falso o gemini')
    modelo = (leer('GEMINI_MODELO', MODELO_GEMINI_REGISTRO) or '').strip()
    if not modelo:
        raise ErrorConfiguracionRegistro('GEMINI_MODELO no puede estar vacío')
    try:
        timeout = float(leer('GEMINI_TIMEOUT_SEGUNDOS', TIEMPO_MAXIMO_EVALUACION_SEGUNDOS))
        if not isfinite(timeout) or timeout <= 0:
            raise ValueError
    except (ValueError, TypeError, OverflowError):
        raise ErrorConfiguracionRegistro('GEMINI_TIMEOUT_SEGUNDOS debe ser positivo y finito') from None
    clave = (leer('GEMINI_API_KEY', None) or '').strip() if proveedor == 'gemini' else None
    if proveedor == 'gemini' and not clave:
        raise ErrorConfiguracionRegistro('Falta GEMINI_API_KEY para usar EVALUADOR=gemini')
    return ConfiguracionRegistro(proveedor, modelo, timeout, clave)


def crear_evaluador_registro(configuracion: ConfiguracionRegistro):
    if configuracion.evaluador == 'falso':
        from app.evaluador_respuestas import EvaluadorFalso
        return EvaluadorFalso()
    from app.evaluador_gemini import EvaluadorGemini
    return EvaluadorGemini(configuracion)
