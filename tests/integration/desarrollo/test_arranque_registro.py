"""Arranque registro."""

import pytest
from fastapi.testclient import TestClient
from app import main as modulo_main
from app.config import cargar_configuracion
from soporte_red import impedir_red


def test_clave_faltante_impide_arranque_sin_crear_bd(tmp_path, monkeypatch):
    def cargar(**kwargs):
        return cargar_configuracion(ruta_env=tmp_path / 'ausente', entorno={'EVALUADOR': 'gemini'})
    monkeypatch.setattr(modulo_main, 'cargar_configuracion', cargar)
    ruta = tmp_path / 'no_creada.db'
    with pytest.raises(RuntimeError, match='Falta GEMINI_API_KEY'):
        with TestClient(modulo_main.crear_aplicacion(f'sqlite:///{ruta.as_posix()}')):
            pass
    assert not ruta.exists()
