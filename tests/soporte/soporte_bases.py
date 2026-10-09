"""Copia de una plantilla cerrada a una base exclusiva de la prueba."""

from shutil import copyfile


def copiar_plantilla(plantilla, destino):
    copyfile(plantilla, destino)
    return f'sqlite:///{destino.as_posix()}'
