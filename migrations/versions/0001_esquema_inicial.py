"""esquema inicial

Revisión: 0001
Revisión anterior: ninguna
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.database import TipoJSON


revision: str = '0001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Generada sobre una base vacía y revisada: CHECK JSON portables y dos dialectos.
    op.create_table('bloque',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('codigo', sa.String(), nullable=False),
    sa.Column('numero', sa.Integer(), nullable=False),
    sa.Column('nombre', sa.String(), nullable=False),
    sa.Column('espacio', sa.Enum('MISIONES_CAMPO', 'CIUDAD', name='espacio', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('audiencia', sa.Enum('ESTUDIANTE', 'APODERADO', name='audiencia', native_enum=False, create_constraint=True), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_bloque')),
    sa.UniqueConstraint('codigo', name=op.f('uq_bloque_codigo'))
    )
    op.create_table('conversacion',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('codigo', sa.String(), nullable=False),
    sa.Column('titulo', sa.String(), nullable=False),
    sa.Column('tema', sa.Text(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_conversacion')),
    sa.UniqueConstraint('codigo', name=op.f('uq_conversacion_codigo'))
    )
    op.create_table('cuenta',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('codigo', sa.String(), nullable=False),
    sa.Column('nombre', sa.String(), nullable=False),
    sa.Column('rol', sa.Enum('ESTUDIANTE', 'APODERADO', name='rol', native_enum=False, create_constraint=True), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_cuenta')),
    sa.UniqueConstraint('codigo', name=op.f('uq_cuenta_codigo'))
    )
    op.create_table('entrevista',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('codigo', sa.String(), nullable=False),
    sa.Column('resumen', sa.Text(), nullable=False),
    sa.Column('fecha_hora', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_entrevista')),
    sa.UniqueConstraint('codigo', name=op.f('uq_entrevista_codigo'))
    )
    op.create_table('escala_respuesta',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('codigo', sa.String(), nullable=False),
    sa.Column('nombre', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_escala_respuesta')),
    sa.UniqueConstraint('codigo', name=op.f('uq_escala_respuesta_codigo'))
    )
    op.create_table('familia_carrera',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('codigo', sa.String(), nullable=False),
    sa.Column('nombre', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_familia_carrera')),
    sa.UniqueConstraint('codigo', name=op.f('uq_familia_carrera_codigo'))
    )
    op.create_table('ficha',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('codigo', sa.String(), nullable=False),
    sa.Column('titulo', sa.String(), nullable=False),
    sa.Column('contenido', sa.Text(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_ficha')),
    sa.UniqueConstraint('codigo', name=op.f('uq_ficha_codigo'))
    )
    op.create_table('insignia',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('codigo', sa.String(), nullable=False),
    sa.Column('nombre', sa.String(), nullable=False),
    sa.Column('descripcion', sa.Text(), nullable=False),
    sa.Column('requisito', sa.Text(), nullable=False),
    sa.Column('es_oculta', sa.Boolean(), nullable=False),
    sa.Column('audiencia', sa.Enum('ESTUDIANTE', 'APODERADO', name='audiencia', native_enum=False, create_constraint=True), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_insignia')),
    sa.UniqueConstraint('codigo', name=op.f('uq_insignia_codigo'))
    )
    op.create_table('instrumento',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('codigo', sa.String(), nullable=False),
    sa.Column('nombre', sa.String(), nullable=False),
    sa.Column('descripcion', sa.Text(), nullable=False),
    sa.Column('tipo_resultado', sa.Enum('COINCIDENCIAS', 'DESTACADAS', 'COMPARACION', name='tiporesultado', native_enum=False, create_constraint=True), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_instrumento')),
    sa.UniqueConstraint('codigo', name=op.f('uq_instrumento_codigo'))
    )
    op.create_table('item_registro',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('codigo', sa.String(), nullable=False),
    sa.Column('nombre', sa.String(), nullable=False),
    sa.Column('consigna', sa.Text(), nullable=False),
    sa.Column('min_caracteres', sa.Integer(), nullable=False),
    sa.Column('obligatorio', sa.Boolean(), nullable=False),
    sa.Column('repregunta_generica', sa.Text(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_item_registro')),
    sa.UniqueConstraint('codigo', name=op.f('uq_item_registro_codigo'))
    )
    op.create_table('nivel',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('numero', sa.Integer(), nullable=False),
    sa.Column('titulo', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_nivel')),
    sa.UniqueConstraint('numero', name=op.f('uq_nivel_numero'))
    )
    op.create_table('ocupacion',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('codigo', sa.String(), nullable=True),
    sa.Column('codigo_onet', sa.String(), nullable=False),
    sa.Column('titulo', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_ocupacion')),
    sa.UniqueConstraint('codigo', name=op.f('uq_ocupacion_codigo')),
    sa.UniqueConstraint('codigo_onet', name=op.f('uq_ocupacion_codigo_onet'))
    )
    op.create_table('pregunta_diario',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('codigo', sa.String(), nullable=False),
    sa.Column('pregunta', sa.Text(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_pregunta_diario')),
    sa.UniqueConstraint('codigo', name=op.f('uq_pregunta_diario_codigo'))
    )
    op.create_table('regla_desbloqueo',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('codigo', sa.String(), nullable=False),
    sa.Column('nombre', sa.String(), nullable=False),
    sa.Column('tipo_objetivo', sa.Enum('BLOQUE', 'ACTIVIDAD', 'FICHA', 'TESTIMONIO', 'PREGUNTA_DIARIO', 'CONVERSACIONES', 'INSIGNIA', 'NIVEL', name='tipoobjetivo', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('id_objetivo', sa.Integer(), nullable=True),
    sa.Column('evaluador_especial', sa.String(), nullable=True),
    sa.Column('parametro_evaluador', sa.Integer(), nullable=True),
    sa.CheckConstraint("(tipo_objetivo = 'CONVERSACIONES' AND id_objetivo IS NULL) OR (tipo_objetivo != 'CONVERSACIONES' AND id_objetivo IS NOT NULL)", name=op.f('ck_regla_desbloqueo_objetivo_segun_tipo')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_regla_desbloqueo')),
    sa.UniqueConstraint('codigo', name=op.f('uq_regla_desbloqueo_codigo'))
    )
    op.create_table('testimonio',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('codigo', sa.String(), nullable=False),
    sa.Column('titulo', sa.String(), nullable=False),
    sa.Column('descripcion', sa.Text(), nullable=False),
    sa.Column('enlace', sa.String(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_testimonio')),
    sa.UniqueConstraint('codigo', name=op.f('uq_testimonio_codigo'))
    )
    op.create_table('actividad',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('codigo', sa.String(), nullable=False),
    sa.Column('titulo', sa.String(), nullable=False),
    sa.Column('tipo', sa.Enum('INFORMATIVA', 'REGISTRO', 'CUESTIONARIO', 'CASO', name='tipoactividad', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('orden', sa.Integer(), nullable=False),
    sa.Column('bloque_id', sa.Integer(), nullable=False),
    sa.Column('puntaje_minimo', sa.Float(), nullable=True),
    sa.CheckConstraint("(tipo = 'CASO' AND puntaje_minimo BETWEEN 0 AND 100 AND puntaje_minimo IS NOT NULL) OR (tipo != 'CASO' AND puntaje_minimo IS NULL)", name=op.f('ck_actividad_puntaje_minimo_solo_caso')),
    sa.ForeignKeyConstraint(['bloque_id'], ['bloque.id'], name=op.f('fk_actividad_bloque_id_bloque')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_actividad')),
    sa.UniqueConstraint('codigo', name=op.f('uq_actividad_codigo'))
    )
    op.create_table('aplicacion',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('instrumento_id', sa.Integer(), nullable=False),
    sa.Column('codigo', sa.String(), nullable=False),
    sa.Column('nombre', sa.String(), nullable=False),
    sa.Column('momento', sa.Enum('UNICA', 'ENTRADA', 'SALIDA', name='momentoaplicacion', native_enum=False, create_constraint=True), nullable=False),
    sa.ForeignKeyConstraint(['instrumento_id'], ['instrumento.id'], name=op.f('fk_aplicacion_instrumento_id_instrumento')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_aplicacion')),
    sa.UniqueConstraint('codigo', name=op.f('uq_aplicacion_codigo'))
    )
    op.create_table('carrera',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('codigo', sa.String(), nullable=False),
    sa.Column('nombre', sa.String(), nullable=False),
    sa.Column('familia_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['familia_id'], ['familia_carrera.id'], name=op.f('fk_carrera_familia_id_familia_carrera')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_carrera')),
    sa.UniqueConstraint('codigo', name=op.f('uq_carrera_codigo'))
    )
    op.create_table('check_in',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('cuenta_id', sa.Integer(), nullable=False),
    sa.Column('fecha', sa.Date(), nullable=False),
    sa.Column('nivel_seguridad', sa.Integer(), nullable=False),
    sa.CheckConstraint('nivel_seguridad BETWEEN 1 AND 5', name=op.f('ck_check_in_nivel_seguridad_valido')),
    sa.ForeignKeyConstraint(['cuenta_id'], ['cuenta.id'], name=op.f('fk_check_in_cuenta_id_cuenta')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_check_in')),
    sa.UniqueConstraint('cuenta_id', 'fecha', name=op.f('uq_check_in_cuenta_id'))
    )
    op.create_table('condicion_desbloqueo',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('regla_id', sa.Integer(), nullable=False),
    sa.Column('tipo_evento', sa.Enum('INGRESO', 'COMPLETA_ACTIVIDAD', 'COMPLETA_BLOQUE', 'RESPUESTA_REFLEXIVA', 'ESCRIBE_ENTRADA_DIARIO', 'ESCRIBE_ENTRADA_LIBRE', 'REGISTRA_CHECK_IN', 'VISTA_CARRERA', 'SUPERA_CASO', 'PUBLICA_ENTREVISTA', 'ESCRIBE_CARTA', 'COMPLETA_CONVERSACION', 'REINICIA_INSTRUMENTO', 'INVITA_A_CREW', 'FORMA_CREW', 'VENCE_DESAFIO_INTACTO', name='tipoeventouso', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('id_referencia', sa.Integer(), nullable=True),
    sa.Column('tipo_conteo', sa.Enum('EVENTOS', 'REFERENCIAS_DISTINTAS', 'DIAS_DISTINTOS', name='tipoconteo', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('cantidad_minima', sa.Integer(), nullable=False),
    sa.CheckConstraint('cantidad_minima >= 1', name=op.f('ck_condicion_desbloqueo_cantidad_minima_valida')),
    sa.ForeignKeyConstraint(['regla_id'], ['regla_desbloqueo.id'], name=op.f('fk_condicion_desbloqueo_regla_id_regla_desbloqueo')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_condicion_desbloqueo'))
    )
    op.create_table('criterio_completitud',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('item_registro_id', sa.Integer(), nullable=False),
    sa.Column('codigo', sa.String(), nullable=False),
    sa.Column('descripcion', sa.Text(), nullable=False),
    sa.Column('orden', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['item_registro_id'], ['item_registro.id'], name=op.f('fk_criterio_completitud_item_registro_id_item_registro')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_criterio_completitud')),
    sa.UniqueConstraint('item_registro_id', 'codigo', name=op.f('uq_criterio_completitud_item_registro_id'))
    )
    op.create_table('desbloqueo',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('cuenta_id', sa.Integer(), nullable=False),
    sa.Column('regla_id', sa.Integer(), nullable=False),
    sa.Column('fecha_hora', sa.DateTime(), nullable=False),
    sa.Column('visto', sa.Boolean(), server_default=sa.false(), nullable=False),
    sa.ForeignKeyConstraint(['cuenta_id'], ['cuenta.id'], name=op.f('fk_desbloqueo_cuenta_id_cuenta')),
    sa.ForeignKeyConstraint(['regla_id'], ['regla_desbloqueo.id'], name=op.f('fk_desbloqueo_regla_id_regla_desbloqueo')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_desbloqueo')),
    sa.UniqueConstraint('cuenta_id', 'regla_id', name=op.f('uq_desbloqueo_cuenta_id'))
    )
    op.create_table('dimension',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('instrumento_id', sa.Integer(), nullable=False),
    sa.Column('codigo', sa.String(), nullable=False),
    sa.Column('nombre', sa.String(), nullable=False),
    sa.Column('descripcion', sa.Text(), nullable=False),
    sa.Column('orden', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['instrumento_id'], ['instrumento.id'], name=op.f('fk_dimension_instrumento_id_instrumento')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_dimension')),
    sa.UniqueConstraint('codigo', name=op.f('uq_dimension_codigo'))
    )
    op.create_table('entrada_diario',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('cuenta_id', sa.Integer(), nullable=False),
    sa.Column('origen', sa.Enum('GUIADA', 'LIBRE', name='origenentrada', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('pregunta_id', sa.Integer(), nullable=True),
    sa.Column('texto', sa.Text(), nullable=False),
    sa.Column('fecha_hora', sa.DateTime(), nullable=False),
    sa.CheckConstraint("(origen = 'GUIADA' AND pregunta_id IS NOT NULL) OR (origen = 'LIBRE' AND pregunta_id IS NULL)", name=op.f('ck_entrada_diario_pregunta_segun_origen')),
    sa.ForeignKeyConstraint(['cuenta_id'], ['cuenta.id'], name=op.f('fk_entrada_diario_cuenta_id_cuenta')),
    sa.ForeignKeyConstraint(['pregunta_id'], ['pregunta_diario.id'], name=op.f('fk_entrada_diario_pregunta_id_pregunta_diario')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_entrada_diario'))
    )
    with op.batch_alter_table('entrada_diario', schema=None) as batch_op:
        batch_op.create_index('entrada_guiada_unica', ['cuenta_id', 'pregunta_id'], unique=True, sqlite_where=sa.text("origen = 'GUIADA'"), postgresql_where=sa.text("origen = 'GUIADA'"))

    op.create_table('entrevista_autor',
    sa.Column('entrevista_id', sa.Integer(), nullable=False),
    sa.Column('cuenta_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['cuenta_id'], ['cuenta.id'], name=op.f('fk_entrevista_autor_cuenta_id_cuenta')),
    sa.ForeignKeyConstraint(['entrevista_id'], ['entrevista.id'], name=op.f('fk_entrevista_autor_entrevista_id_entrevista')),
    sa.PrimaryKeyConstraint('entrevista_id', 'cuenta_id', name=op.f('pk_entrevista_autor'))
    )
    op.create_table('evento_uso',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('cuenta_id', sa.Integer(), nullable=False),
    sa.Column('tipo', sa.Enum('INGRESO', 'COMPLETA_ACTIVIDAD', 'COMPLETA_BLOQUE', 'RESPUESTA_REFLEXIVA', 'ESCRIBE_ENTRADA_DIARIO', 'ESCRIBE_ENTRADA_LIBRE', 'REGISTRA_CHECK_IN', 'VISTA_CARRERA', 'SUPERA_CASO', 'PUBLICA_ENTREVISTA', 'ESCRIBE_CARTA', 'COMPLETA_CONVERSACION', 'REINICIA_INSTRUMENTO', 'INVITA_A_CREW', 'FORMA_CREW', 'VENCE_DESAFIO_INTACTO', name='tipoeventouso', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('fecha_hora', sa.DateTime(), nullable=False),
    sa.Column('id_referencia', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['cuenta_id'], ['cuenta.id'], name=op.f('fk_evento_uso_cuenta_id_cuenta')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_evento_uso'))
    )
    with op.batch_alter_table('evento_uso', schema=None) as batch_op:
        batch_op.create_index('evento_cuenta_tipo', ['cuenta_id', 'tipo'], unique=False)

    op.create_table('opcion_escala',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('escala_id', sa.Integer(), nullable=False),
    sa.Column('orden', sa.Integer(), nullable=False),
    sa.Column('etiqueta', sa.String(), nullable=False),
    sa.Column('puntaje', sa.Float(), nullable=False),
    sa.ForeignKeyConstraint(['escala_id'], ['escala_respuesta.id'], name=op.f('fk_opcion_escala_escala_id_escala_respuesta')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_opcion_escala')),
    sa.UniqueConstraint('escala_id', 'orden', name=op.f('uq_opcion_escala_escala_id'))
    )
    op.create_table('vinculo_familiar',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('codigo', sa.String(), nullable=False),
    sa.Column('estudiante_id', sa.Integer(), nullable=False),
    sa.Column('apoderado_id', sa.Integer(), nullable=False),
    sa.Column('carta_estudiante', sa.Text(), nullable=True),
    sa.Column('carta_apoderado', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['apoderado_id'], ['cuenta.id'], name=op.f('fk_vinculo_familiar_apoderado_id_cuenta')),
    sa.ForeignKeyConstraint(['estudiante_id'], ['cuenta.id'], name=op.f('fk_vinculo_familiar_estudiante_id_cuenta')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_vinculo_familiar')),
    sa.UniqueConstraint('codigo', name=op.f('uq_vinculo_familiar_codigo'))
    )
    op.create_table('actividad_item_registro',
    sa.Column('actividad_id', sa.Integer(), nullable=False),
    sa.Column('item_registro_id', sa.Integer(), nullable=False),
    sa.Column('orden', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['actividad_id'], ['actividad.id'], name=op.f('fk_actividad_item_registro_actividad_id_actividad')),
    sa.ForeignKeyConstraint(['item_registro_id'], ['item_registro.id'], name=op.f('fk_actividad_item_registro_item_registro_id_item_registro')),
    sa.PrimaryKeyConstraint('actividad_id', 'item_registro_id', name=op.f('pk_actividad_item_registro'))
    )
    op.create_table('aplicacion_actividad',
    sa.Column('aplicacion_id', sa.Integer(), nullable=False),
    sa.Column('actividad_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['actividad_id'], ['actividad.id'], name=op.f('fk_aplicacion_actividad_actividad_id_actividad')),
    sa.ForeignKeyConstraint(['aplicacion_id'], ['aplicacion.id'], name=op.f('fk_aplicacion_actividad_aplicacion_id_aplicacion')),
    sa.PrimaryKeyConstraint('aplicacion_id', 'actividad_id', name=op.f('pk_aplicacion_actividad'))
    )
    op.create_table('carrera_ocupacion',
    sa.Column('carrera_id', sa.Integer(), nullable=False),
    sa.Column('ocupacion_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['carrera_id'], ['carrera.id'], name=op.f('fk_carrera_ocupacion_carrera_id_carrera')),
    sa.ForeignKeyConstraint(['ocupacion_id'], ['ocupacion.id'], name=op.f('fk_carrera_ocupacion_ocupacion_id_ocupacion')),
    sa.PrimaryKeyConstraint('carrera_id', 'ocupacion_id', name=op.f('pk_carrera_ocupacion'))
    )
    op.create_table('conversacion_vinculo',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('vinculo_id', sa.Integer(), nullable=False),
    sa.Column('conversacion_id', sa.Integer(), nullable=False),
    sa.Column('conversado', sa.Boolean(), server_default=sa.false(), nullable=False),
    sa.Column('conversado_en', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['conversacion_id'], ['conversacion.id'], name=op.f('fk_conversacion_vinculo_conversacion_id_conversacion')),
    sa.ForeignKeyConstraint(['vinculo_id'], ['vinculo_familiar.id'], name=op.f('fk_conversacion_vinculo_vinculo_id_vinculo_familiar')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_conversacion_vinculo')),
    sa.UniqueConstraint('vinculo_id', 'conversacion_id', name=op.f('uq_conversacion_vinculo_vinculo_id'))
    )
    op.create_table('item_instrumento',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('instrumento_id', sa.Integer(), nullable=False),
    sa.Column('codigo', sa.String(), nullable=False),
    sa.Column('numero', sa.Integer(), nullable=False),
    sa.Column('enunciado', sa.Text(), nullable=False),
    sa.Column('dimension_id', sa.Integer(), nullable=True),
    sa.Column('escala_id', sa.Integer(), nullable=False),
    sa.Column('inverso', sa.Boolean(), server_default=sa.false(), nullable=False),
    sa.ForeignKeyConstraint(['dimension_id'], ['dimension.id'], name=op.f('fk_item_instrumento_dimension_id_dimension')),
    sa.ForeignKeyConstraint(['escala_id'], ['escala_respuesta.id'], name=op.f('fk_item_instrumento_escala_id_escala_respuesta')),
    sa.ForeignKeyConstraint(['instrumento_id'], ['instrumento.id'], name=op.f('fk_item_instrumento_instrumento_id_instrumento')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_item_instrumento')),
    sa.UniqueConstraint('codigo', name=op.f('uq_item_instrumento_codigo')),
    sa.UniqueConstraint('instrumento_id', 'numero', name=op.f('uq_item_instrumento_instrumento_id'))
    )
    op.create_table('progreso_actividad',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('cuenta_id', sa.Integer(), nullable=False),
    sa.Column('actividad_id', sa.Integer(), nullable=False),
    sa.Column('estado', sa.Enum('EN_CURSO', 'COMPLETADA', name='estadoprogreso', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('posicion', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['actividad_id'], ['actividad.id'], name=op.f('fk_progreso_actividad_actividad_id_actividad')),
    sa.ForeignKeyConstraint(['cuenta_id'], ['cuenta.id'], name=op.f('fk_progreso_actividad_cuenta_id_cuenta')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_progreso_actividad')),
    sa.UniqueConstraint('cuenta_id', 'actividad_id', name=op.f('uq_progreso_actividad_cuenta_id'))
    )
    op.create_table('puntaje_ocupacion',
    sa.Column('ocupacion_id', sa.Integer(), nullable=False),
    sa.Column('dimension_id', sa.Integer(), nullable=False),
    sa.Column('valor', sa.Float(), nullable=False),
    sa.ForeignKeyConstraint(['dimension_id'], ['dimension.id'], name=op.f('fk_puntaje_ocupacion_dimension_id_dimension')),
    sa.ForeignKeyConstraint(['ocupacion_id'], ['ocupacion.id'], name=op.f('fk_puntaje_ocupacion_ocupacion_id_ocupacion')),
    sa.PrimaryKeyConstraint('ocupacion_id', 'dimension_id', name=op.f('pk_puntaje_ocupacion'))
    )
    op.create_table('resultado_instrumento',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('cuenta_id', sa.Integer(), nullable=False),
    sa.Column('aplicacion_id', sa.Integer(), nullable=False),
    sa.Column('calculado_en', sa.DateTime(), nullable=False),
    sa.Column('anulado_en', sa.DateTime(), nullable=True),
    sa.Column('perfil_plano', sa.Boolean(), server_default=sa.false(), nullable=False),
    sa.ForeignKeyConstraint(['aplicacion_id'], ['aplicacion.id'], name=op.f('fk_resultado_instrumento_aplicacion_id_aplicacion')),
    sa.ForeignKeyConstraint(['cuenta_id'], ['cuenta.id'], name=op.f('fk_resultado_instrumento_cuenta_id_cuenta')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_resultado_instrumento'))
    )
    with op.batch_alter_table('resultado_instrumento', schema=None) as batch_op:
        batch_op.create_index('resultado_vigente_unico', ['cuenta_id', 'aplicacion_id'], unique=True, sqlite_where=sa.text('anulado_en IS NULL'), postgresql_where=sa.text('anulado_en IS NULL'))

    op.create_table('actividad_item',
    sa.Column('actividad_id', sa.Integer(), nullable=False),
    sa.Column('item_id', sa.Integer(), nullable=False),
    sa.Column('orden', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['actividad_id'], ['actividad.id'], name=op.f('fk_actividad_item_actividad_id_actividad')),
    sa.ForeignKeyConstraint(['item_id'], ['item_instrumento.id'], name=op.f('fk_actividad_item_item_id_item_instrumento')),
    sa.PrimaryKeyConstraint('actividad_id', 'item_id', name=op.f('pk_actividad_item'))
    )
    op.create_table('coincidencia',
    sa.Column('resultado_id', sa.Integer(), nullable=False),
    sa.Column('ocupacion_id', sa.Integer(), nullable=False),
    sa.Column('posicion', sa.Integer(), nullable=False),
    sa.Column('correlacion', sa.Float(), nullable=False),
    sa.Column('ajuste', sa.Enum('BEST_FIT', 'GREAT_FIT', 'GOOD_FIT', name='nivelajuste', native_enum=False, create_constraint=True), nullable=False),
    sa.CheckConstraint("(correlacion >= 0.729 AND ajuste = 'BEST_FIT') OR (correlacion >= 0.608 AND correlacion < 0.729 AND ajuste = 'GREAT_FIT') OR (correlacion >= 0 AND correlacion < 0.608 AND ajuste = 'GOOD_FIT')", name=op.f('ck_coincidencia_ajuste_segun_correlacion')),
    sa.CheckConstraint('posicion BETWEEN 1 AND 10', name=op.f('ck_coincidencia_posicion_valida')),
    sa.ForeignKeyConstraint(['ocupacion_id'], ['ocupacion.id'], name=op.f('fk_coincidencia_ocupacion_id_ocupacion')),
    sa.ForeignKeyConstraint(['resultado_id'], ['resultado_instrumento.id'], name=op.f('fk_coincidencia_resultado_id_resultado_instrumento')),
    sa.PrimaryKeyConstraint('resultado_id', 'ocupacion_id', name=op.f('pk_coincidencia')),
    sa.UniqueConstraint('resultado_id', 'posicion', name=op.f('uq_coincidencia_resultado_id'))
    )
    op.create_table('respuesta_item',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('progreso_id', sa.Integer(), nullable=False),
    sa.Column('item_id', sa.Integer(), nullable=False),
    sa.Column('opcion_id', sa.Integer(), nullable=False),
    sa.Column('creada_en', sa.DateTime(), nullable=False),
    sa.Column('actualizada_en', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['item_id'], ['item_instrumento.id'], name=op.f('fk_respuesta_item_item_id_item_instrumento')),
    sa.ForeignKeyConstraint(['opcion_id'], ['opcion_escala.id'], name=op.f('fk_respuesta_item_opcion_id_opcion_escala')),
    sa.ForeignKeyConstraint(['progreso_id'], ['progreso_actividad.id'], name=op.f('fk_respuesta_item_progreso_id_progreso_actividad')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_respuesta_item')),
    sa.UniqueConstraint('progreso_id', 'item_id', name=op.f('uq_respuesta_item_progreso_id'))
    )
    op.create_table('respuesta_registro',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('progreso_id', sa.Integer(), nullable=False),
    sa.Column('item_registro_id', sa.Integer(), nullable=False),
    sa.Column('texto_inicial', sa.Text(), nullable=False),
    sa.Column('estado', sa.Enum('BORRADOR', 'PENDIENTE_SEGUIMIENTO', 'FINAL', name='estadorespuestaregistro', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('clasificacion_inicial', sa.Enum('ADECUADA', 'VAGA', 'NO_EVALUADA', name='clasificacionrespuesta', native_enum=False, create_constraint=True), nullable=True),
    sa.Column('ampliada', sa.Boolean(), server_default=sa.false(), nullable=False),
    sa.Column('creada_en', sa.DateTime(), nullable=False),
    sa.Column('actualizada_en', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['item_registro_id'], ['item_registro.id'], name=op.f('fk_respuesta_registro_item_registro_id_item_registro')),
    sa.ForeignKeyConstraint(['progreso_id'], ['progreso_actividad.id'], name=op.f('fk_respuesta_registro_progreso_id_progreso_actividad')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_respuesta_registro')),
    sa.UniqueConstraint('progreso_id', 'item_registro_id', name=op.f('uq_respuesta_registro_progreso_id'))
    )
    op.create_table('resultado_caso',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('progreso_id', sa.Integer(), nullable=False),
    sa.Column('puntaje', sa.Float(), nullable=False),
    sa.Column('fecha_hora', sa.DateTime(), nullable=False),
    sa.CheckConstraint('puntaje BETWEEN 0 AND 100', name=op.f('ck_resultado_caso_puntaje_valido')),
    sa.ForeignKeyConstraint(['progreso_id'], ['progreso_actividad.id'], name=op.f('fk_resultado_caso_progreso_id_progreso_actividad')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_resultado_caso'))
    )
    op.create_table('resultado_dimension',
    sa.Column('resultado_id', sa.Integer(), nullable=False),
    sa.Column('dimension_id', sa.Integer(), nullable=False),
    sa.Column('puntaje', sa.Float(), nullable=False),
    sa.Column('puntaje_maximo', sa.Float(), nullable=False),
    sa.Column('porcentaje', sa.Float(), nullable=False),
    sa.ForeignKeyConstraint(['dimension_id'], ['dimension.id'], name=op.f('fk_resultado_dimension_dimension_id_dimension')),
    sa.ForeignKeyConstraint(['resultado_id'], ['resultado_instrumento.id'], name=op.f('fk_resultado_dimension_resultado_id_resultado_instrumento')),
    sa.PrimaryKeyConstraint('resultado_id', 'dimension_id', name=op.f('pk_resultado_dimension'))
    )
    op.create_table('evaluacion_respuesta',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('respuesta_id', sa.Integer(), nullable=False),
    sa.Column('numero', sa.Integer(), nullable=False),
    sa.Column('origen', sa.Enum('LLM', 'RESPALDO_LONGITUD', name='origenevaluacion', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('clasificacion', sa.Enum('ADECUADA', 'VAGA', 'NO_EVALUADA', name='clasificacionrespuesta', native_enum=False, create_constraint=True), nullable=False),
    sa.Column('criterios_faltantes', sa.JSON(none_as_null=True), nullable=False),
    sa.Column('pregunta_generada', sa.Text(), nullable=True),
    sa.Column('requiere_atencion', sa.Boolean(), server_default=sa.false(), nullable=False),
    sa.Column('modelo', sa.String(), nullable=True),
    sa.Column('version_prompt', sa.String(), nullable=True),
    sa.Column('latencia_ms', sa.Integer(), nullable=True),
    sa.Column('error', sa.Text(), nullable=True),
    sa.Column('texto_evaluado', sa.Text(), nullable=False),
    sa.Column('fecha_hora', sa.DateTime(), nullable=False),
    sa.CheckConstraint(TipoJSON(sa.column('criterios_faltantes')) == 'array', name=op.f('ck_evaluacion_respuesta_criterios_faltantes_lista')),
    sa.CheckConstraint('numero >= 1 AND numero = CAST(numero AS INTEGER)', name=op.f('ck_evaluacion_respuesta_numero_evaluacion_valido')),
    sa.ForeignKeyConstraint(['respuesta_id'], ['respuesta_registro.id'], name=op.f('fk_evaluacion_respuesta_respuesta_id_respuesta_registro')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_evaluacion_respuesta'))
    )
    op.create_table('turno_seguimiento',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('respuesta_id', sa.Integer(), nullable=False),
    sa.Column('orden', sa.Integer(), nullable=False),
    sa.Column('pregunta', sa.Text(), nullable=False),
    sa.Column('criterios_objetivo', sa.JSON(none_as_null=True), nullable=False),
    sa.Column('respuesta', sa.Text(), nullable=True),
    sa.Column('respondido_en', sa.DateTime(), nullable=True),
    sa.Column('creado_en', sa.DateTime(), nullable=False),
    sa.CheckConstraint(TipoJSON(sa.column('criterios_objetivo')) == 'array', name=op.f('ck_turno_seguimiento_criterios_objetivo_lista')),
    sa.CheckConstraint('orden IN (1, 2)', name=op.f('ck_turno_seguimiento_orden_seguimiento_valido')),
    sa.ForeignKeyConstraint(['respuesta_id'], ['respuesta_registro.id'], name=op.f('fk_turno_seguimiento_respuesta_id_respuesta_registro')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_turno_seguimiento')),
    sa.UniqueConstraint('respuesta_id', 'orden', name=op.f('uq_turno_seguimiento_respuesta_id'))
    )


def downgrade() -> None:
    # Orden inverso de dependencias, sin CASCADE ni tablas ajenas a esta revisión.
    op.drop_table('turno_seguimiento')
    op.drop_table('evaluacion_respuesta')
    op.drop_table('resultado_dimension')
    op.drop_table('resultado_caso')
    op.drop_table('respuesta_registro')
    op.drop_table('respuesta_item')
    op.drop_table('coincidencia')
    op.drop_table('actividad_item')
    with op.batch_alter_table('resultado_instrumento', schema=None) as batch_op:
        batch_op.drop_index('resultado_vigente_unico', sqlite_where=sa.text('anulado_en IS NULL'), postgresql_where=sa.text('anulado_en IS NULL'))

    op.drop_table('resultado_instrumento')
    op.drop_table('puntaje_ocupacion')
    op.drop_table('progreso_actividad')
    op.drop_table('item_instrumento')
    op.drop_table('conversacion_vinculo')
    op.drop_table('carrera_ocupacion')
    op.drop_table('aplicacion_actividad')
    op.drop_table('actividad_item_registro')
    op.drop_table('vinculo_familiar')
    op.drop_table('opcion_escala')
    with op.batch_alter_table('evento_uso', schema=None) as batch_op:
        batch_op.drop_index('evento_cuenta_tipo')

    op.drop_table('evento_uso')
    op.drop_table('entrevista_autor')
    with op.batch_alter_table('entrada_diario', schema=None) as batch_op:
        batch_op.drop_index('entrada_guiada_unica', sqlite_where=sa.text("origen = 'GUIADA'"), postgresql_where=sa.text("origen = 'GUIADA'"))

    op.drop_table('entrada_diario')
    op.drop_table('dimension')
    op.drop_table('desbloqueo')
    op.drop_table('criterio_completitud')
    op.drop_table('condicion_desbloqueo')
    op.drop_table('check_in')
    op.drop_table('carrera')
    op.drop_table('aplicacion')
    op.drop_table('actividad')
    op.drop_table('testimonio')
    op.drop_table('regla_desbloqueo')
    op.drop_table('pregunta_diario')
    op.drop_table('ocupacion')
    op.drop_table('nivel')
    op.drop_table('item_registro')
    op.drop_table('instrumento')
    op.drop_table('insignia')
    op.drop_table('ficha')
    op.drop_table('familia_carrera')
    op.drop_table('escala_respuesta')
    op.drop_table('entrevista')
    op.drop_table('cuenta')
    op.drop_table('conversacion')
    op.drop_table('bloque')
