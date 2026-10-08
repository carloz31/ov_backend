"""DATO DE PRUEBA: variante pequeña de plataforma para la fase B3 (§5.5)."""

from sqlalchemy.orm import Session

from app.models import Visibilidad
from datos import plataforma
from datos.ocupaciones import validar_distribucion_items


# DATO DE PRUEBA: cinco pasos, con títulos, tipos y contenidos de plataforma.
CODIGOS_CAMINO = ('mission-welcome', 'enc-mitos', 'act-07', 'mission-story', 'mission-compass')
ACTIVIDADES_CAMINO = tuple(fila for fila in plataforma.ACTIVIDADES_CAMINO if fila[0] in CODIGOS_CAMINO)
ACTIVIDADES_CIUDAD = (
    *plataforma.ACTIVIDADES_CIUDAD,
    ('cdd-sin-contenido', 'Actividad de prueba sin contenido', 'INFORMATIVA'),
)
CONTENIDOS_ACTIVIDADES = {
    **plataforma.CONTENIDOS_ACTIVIDADES,
    'cdd-sin-contenido': 'sin_contenido_prueba',
}

# DATO DE PRUEBA: secuencia del Camino reducido y Ciudad abierta al segundo paso.
# Las demás reglas se reutilizan sin modificar condiciones ni umbrales.
REGLAS = (
    *[(f'R-{codigo}', 'ACTIVIDAD', codigo,
       (('COMPLETA_ACTIVIDAD', CODIGOS_CAMINO[numero - 1], 'EVENTOS', 1),), None)
      for numero, codigo in enumerate(CODIGOS_CAMINO) if numero > 0],
    ('R-ciudad', 'BLOQUE', 'CIUDAD', (('COMPLETA_ACTIVIDAD', 'enc-mitos', 'EVENTOS', 1),), None),
    *[regla for regla in plataforma.REGLAS
      if regla[0] != 'R-ciudad'
      and not (regla[1] == 'ACTIVIDAD' and regla[2] in {fila[0] for fila in plataforma.ACTIVIDADES_CAMINO})],
)


def cargar(sesion: Session) -> None:
    """Reutiliza los cargadores de plataforma dentro de la transacción del llamador."""
    archivo = plataforma._leer_catalogo_seleccionado()
    objetivos = plataforma._cargar_estructura(
        sesion, camino=ACTIVIDADES_CAMINO, ciudad=ACTIVIDADES_CIUDAD, contenidos=CONTENIDOS_ACTIVIDADES,
    )
    # DATO DE PRUEBA: Elena se envía siempre, pero solo se muestra al desbloquearse.
    objetivos['ACTIVIDAD']['act-tip-final'].visibilidad = Visibilidad.AL_DESBLOQUEAR
    dimensiones = plataforma._cargar_riasec(sesion, objetivos['ACTIVIDAD'])
    plataforma._cargar_catalogo(sesion, archivo, dimensiones)
    plataforma._cargar_reglas(sesion, objetivos, REGLAS)
    sesion.flush()
    validar_distribucion_items(sesion)
