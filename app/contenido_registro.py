"""Valida referencias del JSON contra la base; no interpreta su narrativa."""

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Actividad, ActividadItemRegistro, ItemRegistro


RUTA_CONTENIDO_REGISTRO = Path(__file__).resolve().parent / "static" / "contenido" / "REG-ACT08.json"


def cargar_posiciones_registro(sesion: Session, ruta: Path | None = None) -> dict[str, tuple[str, ...]]:
    ruta = ruta if ruta is not None else RUTA_CONTENIDO_REGISTRO

    def invalido(mensaje):
        return ValueError(f"Contenido de registro inválido ({ruta.name}): {mensaje}")

    try:
        contenido = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise invalido("no se puede leer un JSON válido") from error
    if not isinstance(contenido, dict) or not isinstance(contenido.get("actividad"), str):
        raise invalido("se requiere el código de actividad")
    momentos = contenido.get("momentos")
    if not isinstance(momentos, list) or not momentos:
        raise invalido("se requiere una lista de momentos no vacía")
    posiciones, codigos = [], []
    for momento in momentos:
        if not isinstance(momento, dict) or not isinstance(momento.get("id"), str) or not momento["id"].strip():
            raise invalido("cada momento debe tener un id no vacío")
        if momento["id"] in posiciones:
            raise invalido(f"id de momento repetido: {momento['id']}")
        posiciones.append(momento["id"])
        if momento.get("tipo") == "registro":
            items = momento.get("items")
            if not isinstance(items, list) or any(not isinstance(codigo, str) or not codigo.strip() for codigo in items):
                raise invalido("los ítems de un momento de registro deben ser una lista de códigos")
            codigos.extend(items)
    # Lecturas agrupadas, sin consultas SQL dentro de bucles.
    actividad_id = sesion.scalar(select(Actividad.id).where(Actividad.codigo == contenido["actividad"]))
    if actividad_id is None:
        raise invalido(f"la actividad no existe: {contenido['actividad']}")
    existentes = set(sesion.scalars(select(ItemRegistro.codigo)))
    for codigo in codigos:
        if codigo not in existentes:
            raise invalido(f"el ítem no existe: {codigo}")
    asignados = list(sesion.scalars(select(ItemRegistro.codigo).join(
        ActividadItemRegistro, ActividadItemRegistro.item_registro_id == ItemRegistro.id,
    ).where(ActividadItemRegistro.actividad_id == actividad_id).order_by(
        ActividadItemRegistro.orden, ItemRegistro.codigo,
    )))
    if codigos != asignados:
        raise invalido(f"los ítems no coinciden en orden con los asignados a {contenido['actividad']}")
    return {contenido["actividad"]: tuple(posiciones)}


def validar_contenido_registro(sesion: Session, ruta: Path | None = None) -> tuple[str, ...]:
    """Conserva la consulta de validación utilizada por las pruebas de contenido."""
    return next(iter(cargar_posiciones_registro(sesion, ruta).values()))
