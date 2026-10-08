"""Proyección temporal de /estado; piloto se agrega en B3 y el archivo se retira en X."""

from datetime import datetime

import pytest
from sqlalchemy import select

from app.main import crear_aplicacion
from app.models import Bloque, Cuenta, EntradaDiario, OrigenEntrada, PreguntaDiario
from datos.cargar import preparar_base
from soporte_plataforma import avanzar_camino, completar


@pytest.fixture(params=['plataforma', 'demo'])
def aplicacion(request, tmp_path):
    url = f"sqlite:///{(tmp_path / 'equivalencia.db').as_posix()}"
    preparar_base(url, request.param, crear_tablas=True)
    aplicacion = crear_aplicacion(url)
    aplicacion.state.conjunto_prueba = request.param
    return aplicacion


@pytest.mark.parametrize('momento', ['inicio', 'dos_actividades', 'camino_completo'])
def test_estado_equivalente_por_dominio(cliente, aplicacion, momento):
    if momento != 'inicio':
        if aplicacion.state.conjunto_prueba == 'plataforma':
            avanzar_camino(cliente, hasta='enc-mitos' if momento == 'dos_actividades' else None)
        else:
            for codigo in ('ACT-01', 'ACT-02') if momento == 'dos_actividades' else ('ACT-01', 'ACT-02', 'ACT-03'):
                completar(cliente, codigo)
    for cuenta in ('est-ana', 'est-luis', 'apo-rosa'):
        def consultar(ruta):
            respuesta = cliente.get(f'/cuentas/{cuenta}/{ruta}')
            assert respuesta.status_code == 200, respuesta.text
            return respuesta.json()

        estado = consultar('estado')
        resumen = consultar('resumen')
        logros = consultar('logros')
        bloques = consultar('actividades')
        bloques_anteriores = [{
            **{clave: bloque[clave] for clave in ('codigo', 'nombre', 'espacio', 'estado')},
            'actividades': [{clave: actividad[clave] for clave in ('codigo', 'titulo', 'estado')}
                            for actividad in bloque['actividades']],
        } for bloque in sorted(bloques, key=lambda bloque: bloque['codigo'])]
        assert estado == {
            **resumen, 'bloques': bloques_anteriores, **logros,
            'fichas': consultar('fichas'), 'testimonios': consultar('testimonios'),
            'preguntas_diario': consultar('diario/preguntas'), 'conversaciones': consultar('conversaciones'),
        }


def test_estado_conserva_orden_anterior_y_actividades_usa_numero(cliente, sesion):
    catalogo = list(sesion.scalars(select(Bloque).where(Bloque.audiencia == 'ESTUDIANTE')))
    nuevo = cliente.get('/cuentas/est-ana/actividades').json()
    anterior = cliente.get('/cuentas/est-ana/estado').json()['bloques']
    assert [b['codigo'] for b in nuevo] == [b.codigo for b in sorted(catalogo, key=lambda b: (b.numero, b.codigo))]
    assert [b['codigo'] for b in anterior] == sorted(b.codigo for b in catalogo)
    assert all(set(b) == {'codigo', 'nombre', 'espacio', 'estado', 'actividades'} for b in anterior)
    assert all(set(a) == {'codigo', 'titulo', 'estado'} for b in anterior for a in b['actividades'])


@pytest.mark.parametrize('aplicacion', ['demo'], indirect=True)
def test_preguntas_respondidas_no_se_mezclan_entre_cuentas(cliente, sesion):
    cuentas = {c.codigo: c for c in sesion.scalars(select(Cuenta))}
    preguntas = {p.codigo: p for p in sesion.scalars(select(PreguntaDiario))}
    sesion.add_all([
        EntradaDiario(cuenta_id=cuentas['est-ana'].id, origen=OrigenEntrada.GUIADA,
                      pregunta_id=preguntas['PD-HISTORIA'].id, texto='Mi historia', fecha_hora=datetime(2026, 10, 8)),
        EntradaDiario(cuenta_id=cuentas['est-luis'].id, origen=OrigenEntrada.GUIADA,
                      pregunta_id=preguntas['PD-ASPIRACIONES'].id, texto='Mis aspiraciones', fecha_hora=datetime(2026, 10, 8)),
        EntradaDiario(cuenta_id=cuentas['est-ana'].id, origen=OrigenEntrada.LIBRE,
                      texto='Una entrada libre', fecha_hora=datetime(2026, 10, 8)),
    ])
    sesion.commit()
    for cuenta, respondida in [('est-ana', 'PD-HISTORIA'), ('est-luis', 'PD-ASPIRACIONES')]:
        respuesta = cliente.get(f'/cuentas/{cuenta}/diario/preguntas')
        assert respuesta.status_code == 200
        filas = respuesta.json()
        assert [p['codigo'] for p in filas] == sorted(preguntas)
        assert {p['codigo'] for p in filas if p['respondida']} == {respondida}
        assert all(set(p) == {'codigo', 'pregunta', 'estado', 'respondida'} for p in filas)
        assert all(p['pregunta'] == preguntas[p['codigo']].pregunta for p in filas)
