"""Resolución de códigos públicos compartida por el motor y las consultas."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.contexto import contexto, usar_contexto
from app.core.definiciones import MODELOS_FIJOS
from app.models import (
    Actividad, Bloque, Carrera, Conversacion, Entrevista, Ficha, Insignia, Instrumento, Nivel,
    PreguntaDiario, ReglaDesbloqueo, Testimonio, TipoEventoUso, TipoObjetivo, VinculoFamiliar,
)
from app.schemas.motor import ObjetivoLegible


MODELOS_OBJETIVO = {
    TipoObjetivo.BLOQUE: Bloque, TipoObjetivo.ACTIVIDAD: Actividad,
    TipoObjetivo.FICHA: Ficha, TipoObjetivo.TESTIMONIO: Testimonio,
    TipoObjetivo.PREGUNTA_DIARIO: PreguntaDiario, TipoObjetivo.INSIGNIA: Insignia,
    TipoObjetivo.NIVEL: Nivel,
}
MODELOS_REFERENCIA = {
    TipoEventoUso.COMPLETA_ACTIVIDAD: Actividad,
    TipoEventoUso.COMPLETA_BLOQUE: Bloque,
    TipoEventoUso.SUPERA_CASO: Actividad,
    TipoEventoUso.VISTA_CARRERA: Carrera,
    TipoEventoUso.PUBLICA_ENTREVISTA: Entrevista,
    TipoEventoUso.ESCRIBE_CARTA: VinculoFamiliar,
    TipoEventoUso.COMPLETA_CONVERSACION: Conversacion,
    TipoEventoUso.REINICIA_INSTRUMENTO: Instrumento,
}


def precargar_referencias(sesion: Session, referencias):
    """Las referencias de tablas mutables se leen por tabla, no por objeto."""
    datos = contexto(sesion)
    if not hasattr(datos, 'referencias_dinamicas'):
        datos.referencias_dinamicas = {}
    por_modelo = {}
    for tipo, identificador in referencias:
        modelo = MODELOS_REFERENCIA.get(tipo)
        if modelo is not None and modelo not in MODELOS_FIJOS and identificador is not None:
            if (modelo, identificador) not in datos.referencias_dinamicas:
                por_modelo.setdefault(modelo, set()).add(identificador)
    for modelo, identificadores in por_modelo.items():
        datos.referencias_dinamicas.update({(modelo, identificador): None for identificador in identificadores})
        datos.referencias_dinamicas.update({(modelo, entidad.id): entidad for entidad in sesion.scalars(
            select(modelo).where(modelo.id.in_(identificadores)),
        )})


@usar_contexto
def objetivo_legible(sesion: Session, regla: ReglaDesbloqueo) -> ObjetivoLegible:
    if regla.tipo_objetivo == TipoObjetivo.CONVERSACIONES:
        return ObjetivoLegible(codigo="-", nombre="Conversaciones")
    objetivo = contexto(sesion).definiciones.obtener(MODELOS_OBJETIVO[regla.tipo_objetivo], regla.id_objetivo)
    if objetivo is None:
        raise ValueError(f"Objetivo inexistente en {regla.codigo}")
    if regla.tipo_objetivo == TipoObjetivo.NIVEL:
        return ObjetivoLegible(codigo=f"N{objetivo.numero}", nombre=objetivo.titulo)
    nombre = (
        objetivo.nombre if regla.tipo_objetivo in (TipoObjetivo.BLOQUE, TipoObjetivo.INSIGNIA) else
        objetivo.pregunta if regla.tipo_objetivo == TipoObjetivo.PREGUNTA_DIARIO else objetivo.titulo
    )
    return ObjetivoLegible(codigo=objetivo.codigo, nombre=nombre)


@usar_contexto
def referencia_legible(
    sesion: Session, tipo_evento: TipoEventoUso, id_referencia: int | None,
) -> str | None:
    if id_referencia is None:
        return None
    if tipo_evento in (
        TipoEventoUso.ESCRIBE_ENTRADA_DIARIO, TipoEventoUso.ESCRIBE_ENTRADA_LIBRE,
        TipoEventoUso.REGISTRA_CHECK_IN,
    ):
        return None
    modelo = MODELOS_REFERENCIA.get(tipo_evento)
    if modelo is None:
        raise ValueError(f"Referencia sin código público para {tipo_evento}")
    if modelo in MODELOS_FIJOS:
        entidad = contexto(sesion).definiciones.obtener(modelo, id_referencia)
    else:
        datos = contexto(sesion)
        if not hasattr(datos, 'referencias_dinamicas'):
            datos.referencias_dinamicas = {}
        clave = (modelo, id_referencia)
        if clave not in datos.referencias_dinamicas:
            datos.referencias_dinamicas[clave] = sesion.get(modelo, id_referencia)
        entidad = datos.referencias_dinamicas[clave]
    if entidad is None:
        raise ValueError(f"Referencia inexistente para {tipo_evento}")
    return entidad.codigo
