"""Fixtures de medición compartidos, sin preparar bases."""

import pytest
from soporte_consultas import ContadorConsultas


@pytest.fixture
def contador_consultas():
    return ContadorConsultas
