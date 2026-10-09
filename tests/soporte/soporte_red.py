"""Bloqueo de red para las pruebas con Gemini simulado."""

import socket

import pytest


@pytest.fixture(autouse=True)
def impedir_red(monkeypatch):
    conectar = socket.socket.connect
    def conectar_solo_bucle_interno(instancia, direccion):
        # Windows crea el socketpair de asyncio mediante TCP de loopback.
        if isinstance(direccion, tuple) and direccion[0] in ('127.0.0.1', '::1'):
            return conectar(instancia, direccion)
        raise AssertionError('Las pruebas Gemini no pueden acceder a la red')
    def prohibida(*args, **kwargs):
        raise AssertionError('Las pruebas Gemini no pueden acceder a la red')
    monkeypatch.setattr(socket.socket, 'connect', conectar_solo_bucle_interno)
    monkeypatch.setattr(socket, 'create_connection', prohibida)
