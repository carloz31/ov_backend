"""R07: una insignia oculta no filtra su explicación."""

from soporte_plataforma import pedir, progreso


def test_r07_progreso_oculto_antes_y_despues(cliente):
    respuesta = cliente.get('/cuentas/est-ana/progreso/INSIGNIA/I10')
    assert respuesta.status_code == 403
    assert 'I10' not in respuesta.text and 'VENCE_DESAFIO_INTACTO' not in respuesta.text
    pedir(cliente, 'POST', '/eventos', {'cuenta': 'est-ana', 'tipo': 'VENCE_DESAFIO_INTACTO'})
    obtenido = progreso(cliente, 'INSIGNIA', 'I10')
    assert obtenido['disponible'] is True and obtenido['reglas'][0]['cumplida'] is True
    assert obtenido['reglas'][0]['condiciones'][0]['actual'] == 1
