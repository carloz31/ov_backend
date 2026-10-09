"""Las pruebas de carga siembran directamente, sin usar plantillas."""

import pytest

from app.main import crear_aplicacion
from datos.cargar import preparar_base


@pytest.fixture
def aplicacion(tmp_path):
    url = f"sqlite:///{(tmp_path / 'carga-plataforma.db').as_posix()}"
    preparar_base(url, 'plataforma', crear_tablas=True)
    aplicacion = crear_aplicacion(url)
    try:
        yield aplicacion
    finally:
        aplicacion.state.motor_bd.dispose()
