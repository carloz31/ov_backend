"""Servidor de comprobación visual: evaluador falso y SQLite descartable.

uv run python tests/soporte/servidor_registro_ui.py
Ctrl+C termina el servidor y elimina su base temporal.
"""

import argparse
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def main():
    analizador = argparse.ArgumentParser(description=__doc__)
    analizador.add_argument('--puerto', type=int, default=8787)
    opciones = analizador.parse_args()
    from app.core.parametros import MODELO_GEMINI_REGISTRO, TIEMPO_MAXIMO_EVALUACION_SEGUNDOS
    os.environ['EVALUADOR'] = 'falso'
    os.environ['GEMINI_MODELO'] = MODELO_GEMINI_REGISTRO
    os.environ['GEMINI_TIMEOUT_SEGUNDOS'] = str(TIEMPO_MAXIMO_EVALUACION_SEGUNDOS)
    import uvicorn
    from app.main import crear_aplicacion
    from datos.cargar import preparar_base
    with TemporaryDirectory(prefix='ov-registro-ui-') as carpeta:
        url = f'sqlite:///{(Path(carpeta) / "registro.db").as_posix()}'
        preparar_base(url, 'demo', crear_tablas=True)
        aplicacion = crear_aplicacion(url)
        uvicorn.run(aplicacion, host='127.0.0.1', port=opciones.puerto, log_level='warning')


if __name__ == '__main__':
    main()
