"""Configuración de la aplicación, sin selección de conjuntos de datos."""

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from math import isfinite
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

from app.core.parametros import MODELO_GEMINI_REGISTRO, TIEMPO_MAXIMO_EVALUACION_SEGUNDOS


RAIZ_PROYECTO = Path(__file__).resolve().parents[1]
RUTA_ENV = Path(__file__).resolve().parent.parent / '.env'


class ErrorConfiguracionRegistro(RuntimeError):
    """Mensaje propio, seguro para mostrar al arrancar o en el script manual."""


@dataclass(frozen=True, slots=True)
class Configuracion:
    url_bd: str = f'sqlite:///{(RAIZ_PROYECTO / "ov.db").as_posix()}'
    entorno: str = 'desarrollo'
    evaluador: str = 'falso'
    modelo: str = MODELO_GEMINI_REGISTRO
    timeout_segundos: float = TIEMPO_MAXIMO_EVALUACION_SEGUNDOS
    clave: str | None = field(default=None, repr=False)


def cargar_configuracion(
    entorno: Mapping[str, str] | None = None, ruta_env: Path = RUTA_ENV,
) -> Configuracion:
    try:
        valores = dotenv_values(ruta_env, interpolate=False)
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
    ambiente = leer('ENTORNO', 'desarrollo')
    if ambiente not in ('desarrollo', 'produccion'):
        raise ValueError('ENTORNO debe ser desarrollo o produccion')
    url_bd = leer('DATABASE_URL', 'sqlite:///ov.db')
    if not url_bd or not url_bd.strip():
        raise ValueError('DATABASE_URL no puede estar vacía')
    try:
        url = make_url(url_bd)
    except (ArgumentError, ValueError):
        raise ValueError('DATABASE_URL no es una URL válida') from None
    if url.get_backend_name() == 'sqlite' and url.database not in (None, '', ':memory:'):
        ruta = Path(url.database)
        if not ruta.is_absolute():
            ruta = RAIZ_PROYECTO / ruta
        url_bd = url.set(database=ruta.as_posix()).render_as_string(hide_password=False)
    return Configuracion(url_bd, ambiente, proveedor, modelo, timeout, clave)


def crear_evaluador_registro(configuracion: Configuracion):
    if configuracion.evaluador == 'falso':
        from app.services.registro.evaluacion import EvaluadorFalso
        return EvaluadorFalso()
    from app.services.registro.gemini import EvaluadorGemini
    return EvaluadorGemini(configuracion)
