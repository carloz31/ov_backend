import pytest


@pytest.fixture(autouse=True)
def usar_evaluador_falso(monkeypatch):
    monkeypatch.setenv("EVALUADOR", "falso")
