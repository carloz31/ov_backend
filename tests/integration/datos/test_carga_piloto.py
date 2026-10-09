"""Carga piloto."""

import os
import subprocess
import sys
from sqlalchemy import select
from app.main import crear_aplicacion
from app.models import Base
from datos.cargar import preparar_base


def test_cargador_cli_admite_piloto_y_vaciado(tmp_path):
    url = f"sqlite:///{(tmp_path / 'cli-piloto.db').as_posix()}"
    preparar_base(url, 'plataforma', crear_tablas=True)
    codigo = "from datos.cargar import main; raise SystemExit(main(['piloto', '--vaciar']))"
    entorno = {**os.environ, 'DATABASE_URL': url, 'EVALUADOR': 'falso'}
    resultado = subprocess.run([sys.executable, '-c', codigo], env=entorno, capture_output=True, text=True)
    assert resultado.returncode == 0, resultado.stderr
    assert 'actividad: 21' in resultado.stdout
    app = crear_aplicacion(url)
    try:
        with app.state.fabrica_sesiones() as sesion:
            assert len(sesion.execute(select(Base.metadata.tables['actividad'])).all()) == 21
    finally:
        app.state.motor_bd.dispose()
