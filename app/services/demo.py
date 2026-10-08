from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import recrear_esquema_demo
from app.models import Actividad, Carrera, Conversacion, Cuenta, FamiliaCarrera, VinculoFamiliar
from app.services.registro.contenido import cargar_posiciones_registro


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

def reiniciar_demo(motor_bd, semilla, obtener_cargador_semilla):
    cargar = obtener_cargador_semilla(semilla)
    with motor_bd.begin() as conexion:
        recrear_esquema_demo(conexion)
        with Session(bind=conexion) as sesion:
            cargar(sesion)
            posiciones = cargar_posiciones_registro(sesion) if semilla == 'demo' else {}
    return posiciones


def recargar_cache_demo(motor_bd) -> None:
    motor_bd.cache_definiciones.recargar()
