"""R11: las consultas y acciones no multiplican SQL al crecer el catálogo."""

from collections import Counter
from app import models as m
from app.services.motor import reglas as motor
from soporte_dominios import RUTAS_DOMINIO
from soporte_retiro import FECHA_BD, agregar_eventos, buscar, condicion, medir, regla


def test_r11_presupuestos_con_cien_reglas_y_quinientos_eventos(cliente, aplicacion, monkeypatch):
    rutas = [f'/cuentas/est-ana/{r}' for r in RUTAS_DOMINIO] + ['/cuentas/est-ana/progreso/BLOQUE/CIUDAD']
    basales = [medir(cliente, aplicacion, 'GET', r, limite=8 if '/progreso/' in r else 10)[1].cantidad for r in rutas]
    with aplicacion.state.fabrica_sesiones.begin() as sesion:
        ana = buscar(sesion, m.Cuenta, 'est-ana')
        objetivo = buscar(sesion, m.Actividad, 'enc-mitos').id
        for n in range(100):
            regla(sesion, f'R-PRUEBA-SQL-{n}', 'ACTIVIDAD', objetivo,
                  [condicion('COMPLETA_ACTIVIDAD', 1000), condicion('INGRESO', 1000)])
        agregar_eventos(sesion, ana, [('INGRESO', None, FECHA_BD)] * 500)
    for _ in range(2):
        cantidades = [medir(cliente, aplicacion, 'GET', r, limite=8 if '/progreso/' in r else 10)[1].cantidad for r in rutas]
        assert cantidades == basales
    llamadas = Counter()
    original = motor.evaluar_regla
    def observar(s, c, r):
        llamadas[r.codigo] += 1
        return original(s, c, r)
    monkeypatch.setattr(motor, 'evaluar_regla', observar)
    medir(cliente, aplicacion, 'POST', '/acciones/completar-actividad',
        {'cuenta': 'est-ana', 'actividad': 'mission-welcome'}, limite=15)
    assert all(llamadas[f'R-PRUEBA-SQL-{n}'] == 1 for n in range(100))
