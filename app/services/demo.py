from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Actividad, Base, Carrera, Conversacion, Cuenta, FamiliaCarrera, VinculoFamiliar


TABLAS_DE_ESTADO = (
    'progreso_actividad', 'resultado_caso', 'entrada_diario', 'check_in',
    'entrevista', 'entrevista_autor', 'conversacion_vinculo', 'evento_uso',
    'desbloqueo', 'respuesta_item', 'resultado_instrumento', 'resultado_dimension',
    'coincidencia', 'respuesta_registro', 'turno_seguimiento', 'evaluacion_respuesta',
)


def consultar_catalogo(sesion: Session):
    """Opciones públicas para los formularios; la disponibilidad viene de /estado."""
    cuentas = {cuenta.id: cuenta.codigo for cuenta in sesion.scalars(select(Cuenta))}
    return {
        "actividades": [
            {"codigo": actividad.codigo, "tipo": actividad.tipo,
             "puntaje_minimo": actividad.puntaje_minimo}
            for actividad in sesion.scalars(select(Actividad).order_by(Actividad.codigo))
        ],
        "carreras": [
            {"codigo": carrera.codigo, "nombre": carrera.nombre,
             "familia": familia.nombre}
            for carrera, familia in sesion.execute(
                select(Carrera, FamiliaCarrera).join(FamiliaCarrera).order_by(Carrera.codigo)
            )
        ],
        "conversaciones": [
            {"codigo": conversacion.codigo, "titulo": conversacion.titulo}
            for conversacion in sesion.scalars(select(Conversacion).order_by(Conversacion.codigo))
        ],
        "vinculos": [
            {"codigo": vinculo.codigo, "estudiante": cuentas[vinculo.estudiante_id],
             "apoderado": cuentas[vinculo.apoderado_id]}
            for vinculo in sesion.scalars(select(VinculoFamiliar).order_by(VinculoFamiliar.codigo))
        ],
    }


def reiniciar_demo(sesion: Session) -> None:
    """El llamador delimita la transacción; el catálogo permanece intacto."""
    for tabla in reversed(Base.metadata.sorted_tables):
        if tabla.name in TABLAS_DE_ESTADO:
            sesion.execute(delete(tabla))
