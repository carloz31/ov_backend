from sqlalchemy.orm import Session

from datos.demo.motor import cargar_motor


def cargar(sesion: Session) -> None:
    """Carga una base vacía; conserva el orden y las referencias de la demo."""
    cargar_motor(sesion)
    # Se agrega después del catálogo original para conservar sus referencias internas.
    from datos.demo.instrumentos import cargar_definiciones_instrumentos, cargar_catalogo_ocupaciones

    cargar_definiciones_instrumentos(sesion)
    cargar_catalogo_ocupaciones(sesion)
    from datos.demo.registro import cargar_definiciones_registro

    cargar_definiciones_registro(sesion)
    sesion.flush()
