from sqlalchemy.orm import Session

from app.core.contexto import contexto, usar_contexto
from app.models import Audiencia, Cuenta, Insignia, Nivel, Rol, TipoObjetivo
from app.schemas.logros import InsigniaEstado, LogrosCuenta, NivelEstado
from app.services.motor.reglas import objetivo_disponible


@usar_contexto
def logros_cuenta(sesion: Session, cuenta: Cuenta) -> LogrosCuenta:
    datos = contexto(sesion)
    insignias = []
    for insignia in sorted((insignia for insignia in datos.definiciones.listar(Insignia)
                           if insignia.audiencia == Audiencia(cuenta.rol.value)), key=lambda insignia: insignia.codigo):
        obtenida = objetivo_disponible(sesion, cuenta, TipoObjetivo.INSIGNIA, insignia.id)
        oculta = insignia.es_oculta and not obtenida
        insignias.append(InsigniaEstado(
            codigo="???" if oculta else insignia.codigo,
            nombre="Logro oculto" if oculta else insignia.nombre,
            descripcion=None if oculta else insignia.descripcion,
            requisito=None if oculta else insignia.requisito,
            estado="OBTENIDA" if obtenida else "BLOQUEADA",
        ))

    niveles = []
    if cuenta.rol == Rol.ESTUDIANTE:
        niveles = [NivelEstado(
            numero=nivel.numero, titulo=nivel.titulo,
            estado="OBTENIDO" if objetivo_disponible(sesion, cuenta, TipoObjetivo.NIVEL, nivel.id) else "BLOQUEADO",
        ) for nivel in sorted(datos.definiciones.listar(Nivel), key=lambda nivel: nivel.numero)]
    return LogrosCuenta(insignias=insignias, niveles=niveles)
