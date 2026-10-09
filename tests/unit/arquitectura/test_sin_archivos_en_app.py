"""La aplicación obtiene sus datos exclusivamente de la base conectada."""

from pathlib import Path


def test_app_no_lee_archivos_de_datos():
    raiz = Path(__file__).resolve().parents[3] / 'app'
    prohibidos = ('read_text(', 'open(', 'json.load', 'StaticFiles', 'FileResponse')
    encontrados = [(str(archivo.relative_to(raiz)), patron)
                   for archivo in raiz.rglob('*.py') if archivo != raiz / 'config.py'
                   for patron in prohibidos if patron in archivo.read_text(encoding='utf-8')]
    assert encontrados == []
