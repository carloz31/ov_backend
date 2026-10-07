"""Selección de semilla y archivo SQLite, sin abrir ni modificar la base."""

from collections.abc import Mapping
from dataclasses import dataclass
import os
from pathlib import Path


RAIZ_PROYECTO = Path(__file__).resolve().parents[1]
SEMILLAS = ('demo', 'plataforma')


@dataclass(frozen=True, slots=True)
class ConfiguracionBase:
    semilla: str
    url_bd: str


def cargar_configuracion_base(
    url_bd: str | None = None, semilla: str | None = None,
    *, entorno: Mapping[str, str] | None = None,
) -> ConfiguracionBase:
    variables = os.environ if entorno is None else entorno
    nombre = semilla if semilla is not None else variables.get('SEMILLA', 'demo')
    if nombre not in SEMILLAS:
        raise ValueError('SEMILLA debe ser demo o plataforma')
    if url_bd is None:
        ruta_configurada = variables.get('RUTA_BD', f'{nombre}.db')
        if not ruta_configurada.strip():
            raise ValueError('RUTA_BD no puede estar vacía')
        ruta = Path(ruta_configurada)
        if not ruta.is_absolute():
            ruta = RAIZ_PROYECTO / ruta
        url_bd = f'sqlite:///{ruta.as_posix()}'
    return ConfiguracionBase(nombre, url_bd)
