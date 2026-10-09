"""Configuracion bd."""

from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from sqlalchemy.exc import OperationalError
from app import database


@pytest.mark.parametrize('url, opciones, escucha', [
    ('sqlite:///:memory:', {'connect_args': {'check_same_thread': False}}, True),
    ('postgresql+psycopg://ov:ov@localhost/ov', {'pool_pre_ping': True}, False),
])
def test_motor_configura_solo_su_dialecto(monkeypatch, url, opciones, escucha):
    crear = Mock(return_value=object())
    registrar = Mock(return_value=lambda funcion: funcion)
    monkeypatch.setattr(database, 'create_engine', crear)
    monkeypatch.setattr(database.event, 'listens_for', registrar)
    assert database.crear_motor_bd(url) is crear.return_value
    crear.assert_called_once_with(url, **opciones)
    assert bool(registrar.call_count) == escucha


@pytest.mark.parametrize('atributos, esperado', [
    ({'sqlite_errorname': 'SQLITE_BUSY'}, True),
    ({'sqlite_errorname': 'SQLITE_BUSY_SNAPSHOT'}, True),
    ({'sqlite_errorname': 'SQLITE_LOCKED'}, True),
    ({'pgcode': '40001'}, True), ({'pgcode': '55P03'}, True),
    ({'sqlstate': '40001'}, True), ({'sqlstate': '55P03'}, True),
    ({'sqlite_errorname': 'SQLITE_ERROR'}, False),
    ({'pgcode': '23505'}, False), ({'sqlstate': '23505'}, False), ({}, False),
])
def test_clasificacion_de_bloqueos(atributos, esperado):
    error = OperationalError('consulta', {}, SimpleNamespace(**atributos))
    assert database.es_bloqueo_temporal(error) is esperado
