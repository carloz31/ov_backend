from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models import Base


TABLAS_DE_ESTADO = (
    'progreso_actividad', 'resultado_caso', 'entrada_diario', 'check_in',
    'entrevista', 'entrevista_autor', 'conversacion_vinculo', 'evento_uso',
    'desbloqueo', 'respuesta_item', 'resultado_instrumento', 'resultado_dimension',
    'coincidencia', 'respuesta_registro', 'turno_seguimiento', 'evaluacion_respuesta',
)


def reiniciar_estado(sesion: Session) -> None:
    """El llamador delimita la transacción; el catálogo permanece intacto."""
    for tabla in reversed(Base.metadata.sorted_tables):
        if tabla.name in TABLAS_DE_ESTADO:
            sesion.execute(delete(tabla))
