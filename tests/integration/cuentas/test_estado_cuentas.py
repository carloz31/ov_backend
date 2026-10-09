"""Estado cuentas."""

from soporte_plataforma import FECHA, eventos, pedir
from sqlalchemy import func, select
from app import models as modelos


def test_check_in_y_diario_aislados_por_cuenta(cliente, sesion):
    # DATO DE PRUEBA: la semilla no define preguntas; esta permite probar el invariante GUIADA.
    sesion.add(modelos.PreguntaDiario(codigo='pregunta-prueba', pregunta='DATO DE PRUEBA'))
    sesion.commit()
    for cuenta in ('est-ana', 'est-luis'):
        cuerpo = {'cuenta': cuenta, 'nivel_seguridad': 3, 'fecha_hora': FECHA}
        pedir(cliente, 'POST', '/acciones/check-in', cuerpo)
        pedir(cliente, 'POST', '/acciones/check-in', cuerpo, esperado=409)
        guiada = {'cuenta': cuenta, 'origen': 'GUIADA', 'pregunta': 'pregunta-prueba',
                  'texto': 'DATO DE PRUEBA', 'fecha_hora': FECHA}
        pedir(cliente, 'POST', '/acciones/escribir-entrada', guiada)
        pedir(cliente, 'POST', '/acciones/escribir-entrada', guiada, esperado=409)
        for _ in range(2):
            pedir(cliente, 'POST', '/acciones/escribir-entrada', {'cuenta': cuenta, 'origen': 'LIBRE', 'texto': 'DATO DE PRUEBA', 'fecha_hora': FECHA})
        historial = eventos(cliente, cuenta)
        assert sum(e['tipo'] == 'REGISTRA_CHECK_IN' for e in historial) == 1
        assert sum(e['tipo'] == 'ESCRIBE_ENTRADA_LIBRE' for e in historial) == 2
        # §5: toda entrada emite DIARIO; las libres emiten además LIBRE.
        assert sum(e['tipo'] == 'ESCRIBE_ENTRADA_DIARIO' for e in historial) == 3
        cuenta_id = sesion.scalar(select(modelos.Cuenta.id).where(modelos.Cuenta.codigo == cuenta))
        assert sesion.scalar(select(func.count()).select_from(modelos.EntradaDiario).where(
            modelos.EntradaDiario.cuenta_id == cuenta_id,
            modelos.EntradaDiario.origen == modelos.OrigenEntrada.GUIADA,
        )) == 1


def test_carta_se_registra_solo_la_primera_vez_por_cuenta(cliente):
    for cuenta in ('est-ana', 'apo-rosa'):
        for texto in ('Primera carta', 'Carta editada'):
            pedir(cliente, 'POST', '/acciones/escribir-carta',
                  {'cuenta': cuenta, 'vinculo': 'VIN-ANA', 'texto': texto, 'fecha_hora': FECHA})
        assert sum(e['tipo'] == 'ESCRIBE_CARTA' and e['referencia'] == 'VIN-ANA' for e in eventos(cliente, cuenta)) == 1
