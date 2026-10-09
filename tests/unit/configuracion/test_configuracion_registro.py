"""Configuracion registro."""

import pytest
from app.config import Configuracion, cargar_configuracion, crear_evaluador_registro
from app.services.registro.evaluacion import EvaluadorFalso
from soporte_red import impedir_red


CLAVE_SIMULADA = 'clave-sintetica-solo-pruebas'


def test_configuracion_predeterminada_sin_clave(tmp_path):
    configuracion = cargar_configuracion(ruta_env=tmp_path / 'ausente', entorno={})
    assert configuracion == Configuracion()
    assert isinstance(crear_evaluador_registro(configuracion), EvaluadorFalso)


def test_env_precedencia_sin_mutar_entorno_ni_interpolar(tmp_path, monkeypatch):
    ruta = tmp_path / '.env'
    ruta.write_text('EVALUADOR=gemini\nGEMINI_API_KEY=valor-${NO_INTERPOLAR}\n'
                    'GEMINI_MODELO=desde-archivo\nGEMINI_TIMEOUT_SEGUNDOS=3.5\n', encoding='utf-8')
    monkeypatch.setenv('GEMINI_MODELO', 'desde-proceso')
    configuracion = cargar_configuracion(ruta_env=ruta, entorno={'GEMINI_MODELO': 'desde-proceso'})
    assert configuracion.modelo == 'desde-proceso'
    assert configuracion.timeout_segundos == 3.5
    assert configuracion.clave == 'valor-${NO_INTERPOLAR}'
    assert 'valor-' not in repr(configuracion)
    assert cargar_configuracion(ruta_env=ruta, entorno={'EVALUADOR': 'falso'}).clave is None


@pytest.mark.parametrize('valores,mensaje', [
    ({'EVALUADOR': 'gemini'}, 'Falta GEMINI_API_KEY'),
    ({'EVALUADOR': 'gemini', 'GEMINI_API_KEY': '  '}, 'Falta GEMINI_API_KEY'),
    ({'EVALUADOR': CLAVE_SIMULADA}, 'EVALUADOR debe ser'),
    ({'EVALUADOR': ''}, 'EVALUADOR debe ser'),
    ({'GEMINI_MODELO': '  '}, 'GEMINI_MODELO no puede'),
    *[({'GEMINI_TIMEOUT_SEGUNDOS': valor}, 'GEMINI_TIMEOUT_SEGUNDOS debe ser')
      for valor in ('', '0', '-1', 'NaN', 'inf', '-inf', CLAVE_SIMULADA)],
])
def test_configuracion_invalida_saneada(tmp_path, valores, mensaje):
    with pytest.raises(RuntimeError, match=mensaje) as error:
        cargar_configuracion(ruta_env=tmp_path / 'ausente', entorno=valores)
    assert CLAVE_SIMULADA not in str(error.value)
