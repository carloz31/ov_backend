from soporte_dominios import consultar_dominios

import re

from sqlalchemy import func, select

from app import models as modelos


def test_pagina_y_recursos_no_modifican_el_estado(cliente, sesion):
    assert cliente.post("/acciones/completar-actividad", json={
        "cuenta": "est-ana", "actividad": "ACT-01",
    }).status_code == 200
    antes = consultar_dominios(cliente)
    eventos = cliente.get("/cuentas/est-ana/eventos").json()
    desbloqueos = cliente.get("/cuentas/est-ana/desbloqueos").json()
    respuesta = cliente.get("/demo")
    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"].startswith("text/html")
    assert '<html lang="es">' in respuesta.text
    recursos = re.findall(r'(?:src|href)="(/demo/recursos/[^\"]+)"', respuesta.text)
    assert len(recursos) == 2
    for recurso in recursos:
        contenido = cliente.get(recurso)
        assert contenido.status_code == 200
        assert len(contenido.content) > 0
    assert cliente.get("/demo/catalogo").status_code == 200
    assert consultar_dominios(cliente) == antes
    assert cliente.get("/cuentas/est-ana/eventos").json() == eventos
    assert cliente.get("/cuentas/est-ana/desbloqueos").json() == desbloqueos
    assert sesion.scalar(select(func.count()).select_from(modelos.ProgresoActividad)) == 1


def test_catalogo_solo_expone_opciones_publicas_sin_logros_ocultos(cliente):
    catalogo = cliente.get("/demo/catalogo").json()
    assert set(catalogo) == {"actividades", "carreras", "conversaciones", "vinculos"}
    assert len(catalogo["actividades"]) == 30
    casos = {item["codigo"]: item["puntaje_minimo"] for item in catalogo["actividades"] if item["tipo"] == "CASO"}
    assert casos == {"CASO-01": 70, "CASO-02": 70}
    assert {(item["codigo"], item["familia"]) for item in catalogo["carreras"]} == {
        ("CAR-ENF", "Salud"), ("CAR-MED", "Salud"), ("CAR-CIV", "Ingeniería"),
        ("CAR-DIS", "Arte"), ("CAR-ADM", "Negocios"),
        ("CAR-AGR", "Ingeniería"), ("CAR-FOR", "Ingeniería"), ("CAR-AMB", "Ingeniería"),
    }
    assert {item["codigo"] for item in catalogo["conversaciones"]} == {"CONV-01", "CONV-02"}
    assert catalogo["vinculos"] == [{"codigo": "VIN-ANA", "estudiante": "est-ana", "apoderado": "apo-rosa"}]
    for grupo in catalogo.values():
        for item in grupo:
            assert not any(clave == "id" or clave.endswith("_id") or clave.startswith("id_") for clave in item)
    assert "LOG-" not in str(catalogo)
    assert "carta_estudiante" not in str(catalogo)
    assert "carta_apoderado" not in str(catalogo)
