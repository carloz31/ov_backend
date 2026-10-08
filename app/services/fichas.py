from sqlalchemy.orm import Session

from app.core.contexto import usar_contexto
from app.models import Cuenta, Ficha, Rol, TipoObjetivo
from app.schemas.comun import ContenidoEstado
from app.services.comun import estado_contenido


@usar_contexto
def listar_fichas_cuenta(sesion: Session, cuenta: Cuenta) -> list[ContenidoEstado]:
    if cuenta.rol != Rol.ESTUDIANTE:
        return []
    return estado_contenido(sesion, cuenta, Ficha, TipoObjetivo.FICHA)
