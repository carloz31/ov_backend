"""R36: eventos crudos evalúan sin crear registros de dominio."""

from soporte_plataforma import filas_base, pedir


def test_r36_eventos_crudos_no_escriben_progreso_ni_entrevista(cliente, aplicacion):
    antes = filas_base(aplicacion)
    completar = pedir(cliente, 'POST', '/eventos', {'cuenta': 'est-ana', 'tipo': 'COMPLETA_ACTIVIDAD', 'referencia': 'mission-welcome'})
    assert 'R-enc-mitos' in {d['regla'] for d in completar['nuevos_desbloqueos']}
    entrevista = pedir(cliente, 'POST', '/eventos', {'cuenta': 'est-ana', 'tipo': 'PUBLICA_ENTREVISTA'})
    assert 'R-I8' in {d['regla'] for d in entrevista['nuevos_desbloqueos']}
    despues = filas_base(aplicacion)
    assert all(despues[nombre] == filas for nombre, filas in antes.items() if nombre not in {'evento_uso', 'desbloqueo'})
