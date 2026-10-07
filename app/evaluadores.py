from collections.abc import Callable
from app.contexto_consultas import contexto, usar_contexto

from sqlalchemy.orm import Session

from app.models import Carrera, Cuenta, ReglaDesbloqueo, TipoEventoUso


@usar_contexto
def carreras_de_3_familias(sesion: Session, cuenta: Cuenta) -> bool:
    datos = contexto(sesion)
    regla = getattr(datos, 'regla_en_evaluacion', None)
    if regla is None:
        # Compatibilidad para llamadas directas al evaluador de la semilla.
        reglas = [regla for regla in datos.definiciones.listar(ReglaDesbloqueo)
                  if regla.evaluador_especial == carreras_de_3_familias.__name__]
        if len(reglas) != 1:
            raise ValueError("Debe indicar la regla para evaluar las familias")
        regla = reglas[0]
    minimo = regla.parametro_evaluador
    if minimo is None or minimo < 1:
        raise ValueError("El evaluador de familias requiere un parámetro entero positivo")
    datos.cargar_conteos([cuenta.id])
    familias = set()
    for tipo, referencia in datos.conteos[cuenta.id]:
        if tipo == TipoEventoUso.VISTA_CARRERA and referencia is not None:
            carrera = datos.definiciones.obtener(Carrera, referencia)
            if carrera is not None:
                familias.add(carrera.familia_id)
    return len(familias) >= minimo


EVALUADORES: dict[str, Callable[[Session, Cuenta], bool]] = {
    "carreras_de_3_familias": carreras_de_3_familias,
}
