"""R4: esquema migrado, integridad y compilación de ambos dialectos."""

from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from fastapi.testclient import TestClient
from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint, inspect, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.schema import CreateIndex, CreateTable

from app import database
from app.main import crear_aplicacion
from app.models import Base
from datos.cargar import preparar_base


RUTA_CONFIGURACION = Path(__file__).resolve().parents[1] / 'alembic.ini'


@pytest.fixture
def base_migrada(tmp_path, monkeypatch):
    url = f'sqlite:///{(tmp_path / "migrada.db").as_posix()}'
    monkeypatch.setenv('DATABASE_URL', url)
    configuracion = Config(str(RUTA_CONFIGURACION))
    command.upgrade(configuracion, 'head')
    motor = database.crear_motor_bd(url)
    try:
        yield url, configuracion, motor
    finally:
        motor.dispose()


def normalizar(sql):
    return ' '.join(str(sql).split())


def test_migracion_inicial_coincide_completamente_con_modelos(base_migrada):
    _, _, motor = base_migrada
    inspector = inspect(motor)
    assert len(Base.metadata.tables) == 44
    assert set(inspector.get_table_names()) == set(Base.metadata.tables) | {'alembic_version'}
    with motor.connect() as conexion:
        assert compare_metadata(MigrationContext.configure(conexion), Base.metadata) == []
        assert conexion.scalar(text('SELECT version_num FROM alembic_version')) == '0001'
        assert conexion.scalar(text('PRAGMA foreign_keys')) == 1
        assert conexion.execute(text('PRAGMA foreign_key_check')).all() == []
    for tabla in Base.metadata.sorted_tables:
        columnas = inspector.get_columns(tabla.name)
        assert {c['name'] for c in columnas} == set(tabla.columns.keys())
        for columna in columnas:
            modelo = tabla.c[columna['name']]
            assert columna['nullable'] == modelo.nullable
            assert normalizar(columna['type'].compile(dialect=motor.dialect)) == normalizar(
                modelo.type.compile(dialect=motor.dialect))
            esperado = (normalizar(modelo.server_default.arg.compile(dialect=motor.dialect))
                        if modelo.server_default is not None else None)
            assert columna['default'] == esperado
        pk = inspector.get_pk_constraint(tabla.name)
        assert pk['name'] == tabla.primary_key.name
        assert pk['constrained_columns'] == [c.name for c in tabla.primary_key.columns]
        unicas = {(c['name'], tuple(c['column_names']))
                  for c in inspector.get_unique_constraints(tabla.name)}
        assert unicas == {(c.name, tuple(c.columns.keys())) for c in tabla.constraints
                          if isinstance(c, UniqueConstraint)}
        foraneas = {(c['name'], tuple(c['constrained_columns']), c['referred_table'],
                     tuple(c['referred_columns'])) for c in inspector.get_foreign_keys(tabla.name)}
        assert foraneas == {(c.name, tuple(c.columns.keys()), c.referred_table.name,
                             tuple(e.column.name for e in c.elements)) for c in tabla.constraints
                            if isinstance(c, ForeignKeyConstraint)}
        checks = {c['name']: normalizar(c['sqltext'])
                  for c in inspector.get_check_constraints(tabla.name)}
        assert checks == {c.name: normalizar(c.sqltext.compile(
            dialect=motor.dialect, compile_kwargs={'literal_binds': True, 'include_table': False}))
            for c in tabla.constraints if isinstance(c, CheckConstraint)}
        indices = inspector.get_indexes(tabla.name)
        assert {(i['name'], tuple(i['column_names']), bool(i['unique'])) for i in indices} == {
            (i.name, tuple(i.columns.keys()), bool(i.unique)) for i in tabla.indexes}
        for indice in indices:
            modelo = next(i for i in tabla.indexes if i.name == indice['name'])
            condicion = modelo.dialect_options['sqlite'].get('where')
            if condicion is not None:
                assert normalizar(indice['dialect_options']['sqlite_where']) == normalizar(condicion)


def test_upgrade_repetible_downgrade_y_nuevo_upgrade(base_migrada):
    _, configuracion, motor = base_migrada
    command.upgrade(configuracion, 'head')
    with motor.connect() as conexion:
        assert conexion.execute(text('SELECT version_num FROM alembic_version')).all() == [('0001',)]
    command.downgrade(configuracion, 'base')
    assert inspect(motor).get_table_names() == ['alembic_version']
    with motor.connect() as conexion:
        assert conexion.execute(text('SELECT version_num FROM alembic_version')).all() == []
    command.upgrade(configuracion, 'head')
    assert set(inspect(motor).get_table_names()) == set(Base.metadata.tables) | {'alembic_version'}


@pytest.mark.parametrize('conjunto', ['demo', 'plataforma'])
def test_carga_vaciado_y_reinicio_conservan_revision(base_migrada, conjunto):
    url, _, motor = base_migrada
    preparar_base(url, conjunto)
    aplicacion = crear_aplicacion(url)
    with TestClient(aplicacion) as cliente:
        assert cliente.post('/demo/reiniciar').json() == {'mensaje': 'Demo reiniciada'}
    preparar_base(url, conjunto, vaciar=True)
    with motor.connect() as conexion:
        assert conexion.execute(text('SELECT version_num FROM alembic_version')).all() == [('0001',)]
        assert conexion.execute(text('PRAGMA foreign_key_check')).all() == []


def test_esquema_migrado_vacio_arranca_y_rechaza_enumerado_invalido(base_migrada):
    url, _, motor = base_migrada
    with TestClient(crear_aplicacion(url)) as cliente:
        assert cliente.get('/cuentas').json() == []
    with pytest.raises(IntegrityError), motor.begin() as conexion:
        conexion.execute(text("INSERT INTO cuenta (codigo, nombre, rol) VALUES ('prueba', 'Prueba', 'INVALIDO')"))


def test_migracion_y_modelos_compilan_para_postgresql(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'postgresql+psycopg://ov:ov@localhost/ov')
    salida = StringIO()
    command.upgrade(Config(str(RUTA_CONFIGURACION), output_buffer=salida), 'head', sql=True)
    sql = salida.getvalue()
    assert sql.count('CREATE TABLE ') == 45
    assert 'esquema_version' not in sql
    assert "json_typeof(criterios_objetivo) = 'array'" in sql
    assert "json_typeof(criterios_faltantes) = 'array'" in sql
    assert 'json_type(' not in sql and 'PRAGMA' not in sql
    assert "WHERE origen = 'GUIADA'" in sql
    assert 'WHERE anulado_en IS NULL' in sql
    assert sql.count('BOOLEAN DEFAULT false') == 6
    dialecto = postgresql.dialect()
    for tabla in Base.metadata.sorted_tables:
        ddl = str(CreateTable(tabla).compile(dialect=dialecto))
        assert 'json_type(' not in ddl
        for restriccion in tabla.constraints:
            assert restriccion.name is not None
            # PostgreSQL trunca determinísticamente los nombres que exceden su límite.
            assert dialecto.identifier_preparer.format_constraint(restriccion) in ddl
        for indice in tabla.indexes:
            ddl_indice = str(CreateIndex(indice).compile(dialect=dialecto))
            condicion = indice.dialect_options['sqlite'].get('where')
            if condicion is not None:
                assert str(indice.dialect_options['postgresql']['where']) == str(condicion)
                assert f'WHERE {condicion}' in ddl_indice


@pytest.mark.parametrize('url, opciones, escucha', [
    ('sqlite:///:memory:', {'connect_args': {'check_same_thread': False}}, True),
    ('postgresql+psycopg://ov:ov@localhost/ov', {'pool_pre_ping': True}, False),
])
def test_motor_configura_solo_su_dialecto(monkeypatch, url, opciones, escucha):
    crear = Mock(return_value=object())
    registrar = Mock(return_value=lambda funcion: funcion)
    monkeypatch.setattr(database, 'create_engine', crear)
    monkeypatch.setattr(database.event, 'listens_for', registrar)
    assert database.crear_motor_bd(url) is crear.return_value
    crear.assert_called_once_with(url, **opciones)
    assert bool(registrar.call_count) == escucha


@pytest.mark.parametrize('atributos, esperado', [
    ({'sqlite_errorname': 'SQLITE_BUSY'}, True),
    ({'sqlite_errorname': 'SQLITE_BUSY_SNAPSHOT'}, True),
    ({'sqlite_errorname': 'SQLITE_LOCKED'}, True),
    ({'pgcode': '40001'}, True), ({'pgcode': '55P03'}, True),
    ({'sqlstate': '40001'}, True), ({'sqlstate': '55P03'}, True),
    ({'sqlite_errorname': 'SQLITE_ERROR'}, False),
    ({'pgcode': '23505'}, False), ({'sqlstate': '23505'}, False), ({}, False),
])
def test_clasificacion_de_bloqueos(atributos, esperado):
    error = OperationalError('consulta', {}, SimpleNamespace(**atributos))
    assert database.es_bloqueo_temporal(error) is esperado
