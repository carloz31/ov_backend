"""Clasificacion tablas."""

from app.models import Base
from app.services.desarrollo import TABLAS_DE_ESTADO


CATALOGO = {
    'cuenta', 'vinculo_familiar', 'bloque', 'actividad', 'ficha', 'testimonio',
    'pregunta_diario', 'conversacion', 'insignia', 'nivel', 'familia_carrera', 'carrera',
    'regla_desbloqueo', 'condicion_desbloqueo', 'instrumento', 'dimension',
    'escala_respuesta', 'opcion_escala', 'item_instrumento', 'actividad_item',
    'aplicacion', 'aplicacion_actividad', 'ocupacion', 'puntaje_ocupacion',
    'carrera_ocupacion', 'item_registro', 'criterio_completitud', 'actividad_item_registro',
}


ESTADO = {
    'progreso_actividad', 'resultado_caso', 'entrada_diario', 'check_in', 'entrevista',
    'entrevista_autor', 'conversacion_vinculo', 'evento_uso', 'desbloqueo',
    'respuesta_item', 'resultado_instrumento', 'resultado_dimension', 'coincidencia',
    'respuesta_registro', 'turno_seguimiento', 'evaluacion_respuesta',
}


def test_todas_las_tablas_clasificadas_sin_solapamientos():
    assert CATALOGO.isdisjoint(ESTADO)
    assert CATALOGO | ESTADO == set(Base.metadata.tables)
    assert set(TABLAS_DE_ESTADO) == ESTADO
    assert len(TABLAS_DE_ESTADO) == len(ESTADO)
