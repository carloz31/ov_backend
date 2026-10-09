"""Invariantes plataforma."""

from soporte_plataforma import CAMINO, actividades, completar, estado, eventos, filas_base
from sqlalchemy import select
from app import models as modelos


def test_invariantes_desbloqueos_nivel_audiencia_y_eventos(cliente, aplicacion):
    anteriores, nivel = {}, 1
    for codigo in CAMINO + ('enc-mitos', 'mission-next-step'):
        completar(cliente, codigo)
        with aplicacion.state.fabrica_sesiones() as sesion:
            actuales = {(d.cuenta_id, d.regla_id): (d.id, d.fecha_hora, d.visto) for d in sesion.scalars(select(modelos.Desbloqueo))}
        assert anteriores.items() <= actuales.items()
        assert len(actuales) == len(filas_base(aplicacion)['desbloqueo'])
        actual = estado(cliente)['nivel_actual']['numero']
        assert actual >= nivel
        anteriores, nivel = actuales, actual
    historial = eventos(cliente)
    assert sum(e['tipo'] == 'COMPLETA_BLOQUE' and e['referencia'] == 'CAMINO' for e in historial) == 1
    assert sum(e['tipo'] == 'COMPLETA_ACTIVIDAD' and e['referencia'] == 'mission-next-step' for e in historial) == 2
    assert actividades(cliente)['mission-next-step'] == 'COMPLETADA'
    assert eventos(cliente, 'est-luis') == [] and estado(cliente, 'est-luis')['nivel_actual']['numero'] == 1
    assert estado(cliente, 'apo-rosa')['bloques'] == []
