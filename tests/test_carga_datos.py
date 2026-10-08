"""R3: carga explícita, atomicidad y clasificación completa del reinicio."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, select
from sqlalchemy.exc import IntegrityError

from app.database import crear_motor_bd
from app import models as modelos
from app.main import crear_aplicacion
from app.models import Base
from app.services.demo import TABLAS_DE_ESTADO
from datos import cargar as carga
from datos import demo, plataforma


CATALOGO = {
    'cuenta', 'vinculo_familiar', 'bloque', 'actividad', 'ficha', 'testimonio',
    'pregunta_diario', 'conversacion', 'insignia', 'nivel', 'familia_carrera', 'carrera',
    'regla_desbloqueo', 'condicion_desbloqueo', 'instrumento', 'dimension',
    'escala_respuesta', 'opcion_escala', 'item_instrumento', 'actividad_item',
    'aplicacion', 'aplicacion_actividad', 'ocupacion', 'puntaje_ocupacion',
    'carrera_ocupacion', 'item_registro', 'criterio_completitud', 'actividad_item_registro',
}
ESTADO = {
    'progreso_actividad', 'resultado_caso', 'entrada_diario', 'check_in', 'entrevista',
    'entrevista_autor', 'conversacion_vinculo', 'evento_uso', 'desbloqueo',
    'respuesta_item', 'resultado_instrumento', 'resultado_dimension', 'coincidencia',
    'respuesta_registro', 'turno_seguimiento', 'evaluacion_respuesta',
}


def filas(motor):
    with motor.connect() as conexion:
        return {tabla.name: conexion.execute(select(tabla).order_by(*tabla.primary_key.columns)).all()
                for tabla in Base.metadata.sorted_tables}


def test_todas_las_tablas_clasificadas_sin_solapamientos():
    assert CATALOGO.isdisjoint(ESTADO)
    assert CATALOGO | ESTADO == set(Base.metadata.tables)
    assert set(TABLAS_DE_ESTADO) == ESTADO
    assert len(TABLAS_DE_ESTADO) == len(ESTADO)


@pytest.mark.parametrize('conjunto', ['demo', 'plataforma'])
def test_carga_conteos_recarga_rechazada_y_vaciado(tmp_path, conjunto):
    url = f'sqlite:///{(tmp_path / "carga.db").as_posix()}'
    conteos = carga.preparar_base(url, conjunto, crear_tablas=True)
    assert set(conteos) == set(carga.TABLAS_PRINCIPALES)
    assert conteos['cuenta'] == 3 and conteos['actividad'] > 0
    motor = crear_motor_bd(url)
    try:
        antes = filas(motor)
        with pytest.raises(ValueError, match='--vaciar'):
            carga.preparar_base(url, conjunto)
        assert filas(motor) == antes
        assert carga.preparar_base(url, conjunto, vaciar=True) == conteos
        assert filas(motor) == antes
    finally:
        motor.dispose()


@pytest.mark.parametrize('vaciar', [False, True])
def test_carga_fallida_es_atomica(tmp_path, monkeypatch, vaciar):
    url = f'sqlite:///{(tmp_path / "atomica.db").as_posix()}'
    motor = crear_motor_bd(url)
    if vaciar:
        carga.preparar_base(url, 'demo', crear_tablas=True)
    else:
        Base.metadata.create_all(motor)
    antes = filas(motor)
    def fallar(sesion):
        demo.cargar(sesion)
        raise ValueError('Fallo después de la carga completa')
    monkeypatch.setitem(carga.CONJUNTOS, 'demo', fallar)
    try:
        with pytest.raises(ValueError, match='Fallo después'):
            carga.preparar_base(url, 'demo', vaciar=vaciar)
        assert filas(motor) == antes
    finally:
        motor.dispose()


def test_conjunto_invalido_no_abre_base(tmp_path):
    ruta = tmp_path / 'no_creada.db'
    with pytest.raises(ValueError, match='conjunto'):
        carga.preparar_base(f'sqlite:///{ruta.as_posix()}', 'otro', crear_tablas=True)
    assert not ruta.exists()


def test_cli_rechaza_crear_tablas(tmp_path, monkeypatch, capsys):
    ruta = tmp_path / 'no_creada.db'
    monkeypatch.setenv('DATABASE_URL', f'sqlite:///{ruta.as_posix()}')
    with pytest.raises(SystemExit) as error:
        carga.main(['plataforma', '--crear-tablas'])
    assert error.value.code == 2
    assert '--crear-tablas' in capsys.readouterr().err
    assert not ruta.exists()


def test_cli_sin_esquema_y_carga_tras_migracion(tmp_path, monkeypatch, capsys):
    from alembic import command
    from alembic.config import Config
    from pathlib import Path

    url = f'sqlite:///{(tmp_path / "cli.db").as_posix()}'
    monkeypatch.setenv('DATABASE_URL', url)
    with pytest.raises(SystemExit) as error:
        carga.main(['plataforma'])
    assert error.value.code == 1
    assert 'uv run alembic upgrade head' in capsys.readouterr().err
    command.upgrade(Config(str(Path(__file__).resolve().parents[1] / 'alembic.ini')), 'head')
    assert carga.main(['plataforma']) == 0
    salida = capsys.readouterr().out
    assert 'cuenta: 3' in salida and 'ocupacion: 36' in salida
    with pytest.raises(SystemExit) as error:
        carga.main(['plataforma'])
    assert error.value.code == 1
    assert '--vaciar' in capsys.readouterr().err
    assert carga.main(['demo', '--vaciar']) == 0


@pytest.mark.parametrize('conjunto', ['demo', 'plataforma'])
def test_reinicio_preserva_catalogo_cache_posiciones_y_no_usa_cargadores(tmp_path, monkeypatch, conjunto):
    url = f'sqlite:///{(tmp_path / "reinicio.db").as_posix()}'
    carga.preparar_base(url, conjunto, crear_tablas=True)
    aplicacion = crear_aplicacion(url)
    with TestClient(aplicacion) as cliente:
        motor = aplicacion.state.motor_bd
        antes = filas(motor)
        cache = motor.cache_definiciones.actual
        posiciones = aplicacion.state.posiciones_registro
        def prohibido(*args, **kwargs):
            pytest.fail('El reinicio no debe cargar datos ni recrear tablas')
        monkeypatch.setattr(demo, 'cargar', prohibido)
        monkeypatch.setattr(plataforma, 'cargar', prohibido)
        monkeypatch.setitem(carga.CONJUNTOS, 'demo', prohibido)
        monkeypatch.setitem(carga.CONJUNTOS, 'plataforma', prohibido)
        monkeypatch.setattr(Base.metadata, 'create_all', prohibido)
        monkeypatch.setattr(Base.metadata, 'drop_all', prohibido)
        assert cliente.post('/acciones/ingresar', json={'cuenta': 'est-ana'}).status_code == 200
        for _ in range(2):
            assert cliente.post('/demo/reiniciar').json() == {'mensaje': 'Demo reiniciada'}
            despues = filas(motor)
            assert all(despues[nombre] == antes[nombre] for nombre in CATALOGO)
            assert all(despues[nombre] == [] for nombre in ESTADO)
            assert motor.cache_definiciones.actual is cache
            assert aplicacion.state.posiciones_registro is posiciones


def test_reinicio_fallido_revierte_borrados(cliente, aplicacion):
    assert cliente.post('/acciones/ingresar', json={'cuenta': 'est-ana'}).status_code == 200
    motor = aplicacion.state.motor_bd
    antes = filas(motor)
    def fallar(conexion, cursor, sentencia, parametros, contexto, varios):
        if sentencia.startswith('DELETE FROM progreso_actividad'):
            raise IntegrityError(sentencia, parametros, RuntimeError('Fallo de prueba'))
    event.listen(motor, 'before_cursor_execute', fallar)
    try:
        assert cliente.post('/demo/reiniciar').status_code == 409
    finally:
        event.remove(motor, 'before_cursor_execute', fallar)
    assert filas(motor) == antes


def test_reinicio_vacia_las_dieciseis_tablas_con_datos(cliente, aplicacion):
    # DATO DE PRUEBA: una fila válida en cada tabla de estado, con sus dependencias.
    fecha = datetime(2026, 10, 8, 10)
    with aplicacion.state.fabrica_sesiones.begin() as sesion:
        cuenta = sesion.scalar(select(modelos.Cuenta).where(modelos.Cuenta.codigo == 'est-ana'))
        actividad = sesion.scalar(select(modelos.Actividad).where(modelos.Actividad.codigo == 'REG-ACT08'))
        vinculo = sesion.scalar(select(modelos.VinculoFamiliar))
        conversacion = sesion.scalar(select(modelos.Conversacion))
        regla = sesion.scalar(select(modelos.ReglaDesbloqueo))
        aplicacion_instrumento = sesion.scalar(select(modelos.Aplicacion))
        dimension = sesion.scalar(select(modelos.Dimension).where(
            modelos.Dimension.instrumento_id == aplicacion_instrumento.instrumento_id))
        item = sesion.scalar(select(modelos.ItemInstrumento))
        opcion = sesion.scalar(select(modelos.OpcionEscala).where(modelos.OpcionEscala.escala_id == item.escala_id))
        item_registro = sesion.scalar(select(modelos.ItemRegistro))
        ocupacion = sesion.scalar(select(modelos.Ocupacion))
        if ocupacion is None:
            ocupacion = modelos.Ocupacion(codigo_onet='PRUEBA-REINICIO', titulo='DATO DE PRUEBA')
            sesion.add(ocupacion)
        progreso = modelos.ProgresoActividad(cuenta_id=cuenta.id, actividad_id=actividad.id, estado='EN_CURSO')
        entrevista = modelos.Entrevista(codigo='ENT-REINICIO', resumen='DATO DE PRUEBA', fecha_hora=fecha)
        resultado = modelos.ResultadoInstrumento(cuenta_id=cuenta.id, aplicacion_id=aplicacion_instrumento.id, calculado_en=fecha)
        sesion.add_all([progreso, entrevista, resultado])
        sesion.flush()
        respuesta = modelos.RespuestaRegistro(progreso_id=progreso.id, item_registro_id=item_registro.id,
            texto_inicial='DATO DE PRUEBA', estado='PENDIENTE_SEGUIMIENTO', creada_en=fecha, actualizada_en=fecha)
        sesion.add(respuesta)
        sesion.flush()
        sesion.add_all([
            modelos.ResultadoCaso(progreso_id=progreso.id, puntaje=85, fecha_hora=fecha),
            modelos.EntradaDiario(cuenta_id=cuenta.id, origen='LIBRE', texto='DATO DE PRUEBA', fecha_hora=fecha),
            modelos.CheckIn(cuenta_id=cuenta.id, fecha=fecha.date(), nivel_seguridad=3),
            modelos.EntrevistaAutor(entrevista_id=entrevista.id, cuenta_id=cuenta.id),
            modelos.ConversacionVinculo(vinculo_id=vinculo.id, conversacion_id=conversacion.id, conversado=True),
            modelos.EventoUso(cuenta_id=cuenta.id, tipo='INGRESO', fecha_hora=fecha),
            modelos.Desbloqueo(cuenta_id=cuenta.id, regla_id=regla.id, fecha_hora=fecha),
            modelos.RespuestaItem(progreso_id=progreso.id, item_id=item.id, opcion_id=opcion.id, creada_en=fecha, actualizada_en=fecha),
            modelos.ResultadoDimension(resultado_id=resultado.id, dimension_id=dimension.id, puntaje=1, puntaje_maximo=5, porcentaje=20),
            modelos.Coincidencia(resultado_id=resultado.id, ocupacion_id=ocupacion.id, posicion=1, correlacion=0.9, ajuste='BEST_FIT'),
            modelos.TurnoSeguimiento(respuesta_id=respuesta.id, orden=1, pregunta='DATO DE PRUEBA', criterios_objetivo=['C1'], creado_en=fecha),
            modelos.EvaluacionRespuesta(respuesta_id=respuesta.id, numero=1, origen='RESPALDO_LONGITUD', clasificacion='VAGA',
                criterios_faltantes=['C1'], texto_evaluado='DATO DE PRUEBA', fecha_hora=fecha),
        ])
    antes = filas(aplicacion.state.motor_bd)
    assert all(antes[nombre] for nombre in ESTADO)
    assert cliente.post('/demo/reiniciar').json() == {'mensaje': 'Demo reiniciada'}
    despues = filas(aplicacion.state.motor_bd)
    assert all(despues[nombre] == [] for nombre in ESTADO)
    assert all(despues[nombre] == antes[nombre] for nombre in CATALOGO)


def test_json_con_actividad_ausente_no_valida_momentos(tmp_path, monkeypatch):
    from app.services.registro import contenido

    url = f'sqlite:///{(tmp_path / "plataforma.db").as_posix()}'
    carga.preparar_base(url, 'plataforma', crear_tablas=True)
    ruta = tmp_path / 'REG-ACT08.json'
    ruta.write_text('{"actividad":"REG-ACT08","momentos":null}', encoding='utf-8')
    monkeypatch.setattr(contenido, 'RUTA_CONTENIDO_REGISTRO', ruta)
    aplicacion = crear_aplicacion(url)
    with TestClient(aplicacion):
        assert aplicacion.state.posiciones_registro == {}


def test_auxiliar_registro_rechaza_base_persistente(tmp_path):
    ruta = tmp_path / 'protegida.db'
    motor = crear_motor_bd(f'sqlite:///{ruta.as_posix()}')
    try:
        with pytest.raises(ValueError, match='en memoria'):
            carga.preparar_base_registro_en_memoria(motor)
        assert not ruta.exists()
    finally:
        motor.dispose()
