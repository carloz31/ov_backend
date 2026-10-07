from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint, Date, DateTime, Enum, ForeignKey, Index, JSON, Text,
    UniqueConstraint, false, text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.configuracion_metodos import (
    CORRELACION_MINIMA, LIMITE_COINCIDENCIAS, UMBRAL_BEST_FIT, UMBRAL_GREAT_FIT,
)
from app.tipos_registro import ClasificacionRespuesta, EstadoRespuestaRegistro, OrigenEvaluacion


class Rol(StrEnum):
    ESTUDIANTE = "ESTUDIANTE"
    APODERADO = "APODERADO"


class Espacio(StrEnum):
    MISIONES_CAMPO = "MISIONES_CAMPO"
    CIUDAD = "CIUDAD"


class Audiencia(StrEnum):
    ESTUDIANTE = "ESTUDIANTE"
    APODERADO = "APODERADO"


class TipoActividad(StrEnum):
    INFORMATIVA = "INFORMATIVA"
    REGISTRO = "REGISTRO"
    CUESTIONARIO = "CUESTIONARIO"
    CASO = "CASO"


class EstadoProgreso(StrEnum):
    EN_CURSO = "EN_CURSO"
    COMPLETADA = "COMPLETADA"


class TipoEventoUso(StrEnum):
    INGRESO = "INGRESO"
    COMPLETA_ACTIVIDAD = "COMPLETA_ACTIVIDAD"
    COMPLETA_BLOQUE = "COMPLETA_BLOQUE"
    RESPUESTA_REFLEXIVA = "RESPUESTA_REFLEXIVA"
    ESCRIBE_ENTRADA_DIARIO = "ESCRIBE_ENTRADA_DIARIO"
    ESCRIBE_ENTRADA_LIBRE = "ESCRIBE_ENTRADA_LIBRE"
    REGISTRA_CHECK_IN = "REGISTRA_CHECK_IN"
    VISTA_CARRERA = "VISTA_CARRERA"
    SUPERA_CASO = "SUPERA_CASO"
    PUBLICA_ENTREVISTA = "PUBLICA_ENTREVISTA"
    ESCRIBE_CARTA = "ESCRIBE_CARTA"
    COMPLETA_CONVERSACION = "COMPLETA_CONVERSACION"
    REINICIA_INSTRUMENTO = "REINICIA_INSTRUMENTO"


class NivelAjuste(StrEnum):
    BEST_FIT = "BEST_FIT"
    GREAT_FIT = "GREAT_FIT"
    GOOD_FIT = "GOOD_FIT"


class TipoResultado(StrEnum):
    COINCIDENCIAS = "COINCIDENCIAS"
    DESTACADAS = "DESTACADAS"
    COMPARACION = "COMPARACION"


class MomentoAplicacion(StrEnum):
    UNICA = "UNICA"
    ENTRADA = "ENTRADA"
    SALIDA = "SALIDA"


class TipoObjetivo(StrEnum):
    BLOQUE = "BLOQUE"
    ACTIVIDAD = "ACTIVIDAD"
    FICHA = "FICHA"
    TESTIMONIO = "TESTIMONIO"
    PREGUNTA_DIARIO = "PREGUNTA_DIARIO"
    CONVERSACIONES = "CONVERSACIONES"
    INSIGNIA = "INSIGNIA"
    NIVEL = "NIVEL"


class TipoConteo(StrEnum):
    EVENTOS = "EVENTOS"
    REFERENCIAS_DISTINTAS = "REFERENCIAS_DISTINTAS"
    DIAS_DISTINTOS = "DIAS_DISTINTOS"


class OrigenEntrada(StrEnum):
    GUIADA = "GUIADA"
    LIBRE = "LIBRE"


def enumerado(clase: type[StrEnum]) -> Enum:
    return Enum(
        clase, native_enum=False, create_constraint=True, validate_strings=True,
        values_callable=lambda valores: [valor.value for valor in valores],
    )


class Cuenta(Base):
    __tablename__ = "cuenta"
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(unique=True)
    nombre: Mapped[str]
    rol: Mapped[Rol] = mapped_column(enumerado(Rol))


class VinculoFamiliar(Base):
    __tablename__ = "vinculo_familiar"
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(unique=True)
    estudiante_id: Mapped[int] = mapped_column(ForeignKey("cuenta.id"))
    apoderado_id: Mapped[int] = mapped_column(ForeignKey("cuenta.id"))
    carta_estudiante: Mapped[str | None] = mapped_column(Text)
    carta_apoderado: Mapped[str | None] = mapped_column(Text)


class Bloque(Base):
    __tablename__ = "bloque"
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(unique=True)
    numero: Mapped[int]
    nombre: Mapped[str]
    espacio: Mapped[Espacio] = mapped_column(enumerado(Espacio))
    audiencia: Mapped[Audiencia] = mapped_column(enumerado(Audiencia))


class Actividad(Base):
    __tablename__ = "actividad"
    __table_args__ = (
        CheckConstraint(
            "(tipo = 'CASO' AND puntaje_minimo BETWEEN 0 AND 100 "
            "AND puntaje_minimo IS NOT NULL) OR "
            "(tipo != 'CASO' AND puntaje_minimo IS NULL)",
            name="puntaje_minimo_solo_caso",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(unique=True)
    titulo: Mapped[str]
    tipo: Mapped[TipoActividad] = mapped_column(enumerado(TipoActividad))
    orden: Mapped[int]
    bloque_id: Mapped[int] = mapped_column(ForeignKey("bloque.id"))
    puntaje_minimo: Mapped[float | None]


class Ficha(Base):
    __tablename__ = "ficha"
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(unique=True)
    titulo: Mapped[str]
    contenido: Mapped[str] = mapped_column(Text)


class Testimonio(Base):
    __tablename__ = "testimonio"
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(unique=True)
    titulo: Mapped[str]
    descripcion: Mapped[str] = mapped_column(Text)
    enlace: Mapped[str]


class PreguntaDiario(Base):
    __tablename__ = "pregunta_diario"
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(unique=True)
    pregunta: Mapped[str] = mapped_column(Text)


class Conversacion(Base):
    __tablename__ = "conversacion"
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(unique=True)
    titulo: Mapped[str]
    tema: Mapped[str] = mapped_column(Text)


class Insignia(Base):
    __tablename__ = "insignia"
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(unique=True)
    nombre: Mapped[str]
    descripcion: Mapped[str] = mapped_column(Text)
    requisito: Mapped[str] = mapped_column(Text)
    es_oculta: Mapped[bool]
    audiencia: Mapped[Audiencia] = mapped_column(enumerado(Audiencia))


class Nivel(Base):
    __tablename__ = "nivel"
    id: Mapped[int] = mapped_column(primary_key=True)
    numero: Mapped[int] = mapped_column(unique=True)
    titulo: Mapped[str]


class FamiliaCarrera(Base):
    __tablename__ = "familia_carrera"
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(unique=True)
    nombre: Mapped[str]


class Carrera(Base):
    __tablename__ = "carrera"
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(unique=True)
    nombre: Mapped[str]
    familia_id: Mapped[int] = mapped_column(ForeignKey("familia_carrera.id"))


class ProgresoActividad(Base):
    __tablename__ = "progreso_actividad"
    __table_args__ = (UniqueConstraint("cuenta_id", "actividad_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("cuenta.id"))
    actividad_id: Mapped[int] = mapped_column(ForeignKey("actividad.id"))
    estado: Mapped[EstadoProgreso] = mapped_column(enumerado(EstadoProgreso))
    posicion: Mapped[str | None] = mapped_column(Text)


class ResultadoCaso(Base):
    __tablename__ = "resultado_caso"
    __table_args__ = (CheckConstraint("puntaje BETWEEN 0 AND 100"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    progreso_id: Mapped[int] = mapped_column(ForeignKey("progreso_actividad.id"))
    puntaje: Mapped[float]
    fecha_hora: Mapped[datetime] = mapped_column(DateTime)


class EntradaDiario(Base):
    __tablename__ = "entrada_diario"
    __table_args__ = (
        Index(
            "entrada_guiada_unica", "cuenta_id", "pregunta_id", unique=True,
            sqlite_where=text("origen = 'GUIADA'"),
        ),
        CheckConstraint(
            "(origen = 'GUIADA' AND pregunta_id IS NOT NULL) OR "
            "(origen = 'LIBRE' AND pregunta_id IS NULL)",
            name="pregunta_segun_origen",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("cuenta.id"))
    origen: Mapped[OrigenEntrada] = mapped_column(enumerado(OrigenEntrada))
    pregunta_id: Mapped[int | None] = mapped_column(ForeignKey("pregunta_diario.id"))
    texto: Mapped[str] = mapped_column(Text)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime)


class CheckIn(Base):
    __tablename__ = "check_in"
    __table_args__ = (
        UniqueConstraint("cuenta_id", "fecha"),
        CheckConstraint("nivel_seguridad BETWEEN 1 AND 5"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("cuenta.id"))
    fecha: Mapped[date] = mapped_column(Date)
    nivel_seguridad: Mapped[int]


class Entrevista(Base):
    __tablename__ = "entrevista"
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(unique=True)
    resumen: Mapped[str] = mapped_column(Text)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime)


class EntrevistaAutor(Base):
    __tablename__ = "entrevista_autor"
    entrevista_id: Mapped[int] = mapped_column(ForeignKey("entrevista.id"), primary_key=True)
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("cuenta.id"), primary_key=True)


class ConversacionVinculo(Base):
    __tablename__ = "conversacion_vinculo"
    __table_args__ = (UniqueConstraint("vinculo_id", "conversacion_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    vinculo_id: Mapped[int] = mapped_column(ForeignKey("vinculo_familiar.id"))
    conversacion_id: Mapped[int] = mapped_column(ForeignKey("conversacion.id"))
    conversado: Mapped[bool] = mapped_column(default=False, server_default=false())
    conversado_en: Mapped[datetime | None] = mapped_column(DateTime)


class EventoUso(Base):
    __tablename__ = "evento_uso"
    __table_args__ = (Index("evento_cuenta_tipo", "cuenta_id", "tipo"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("cuenta.id"))
    tipo: Mapped[TipoEventoUso] = mapped_column(enumerado(TipoEventoUso))
    fecha_hora: Mapped[datetime] = mapped_column(DateTime)
    id_referencia: Mapped[int | None]


class ReglaDesbloqueo(Base):
    __tablename__ = "regla_desbloqueo"
    __table_args__ = (
        CheckConstraint(
            "(tipo_objetivo = 'CONVERSACIONES' AND id_objetivo IS NULL) OR "
            "(tipo_objetivo != 'CONVERSACIONES' AND id_objetivo IS NOT NULL)",
            name="objetivo_segun_tipo",
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(unique=True)
    nombre: Mapped[str]
    tipo_objetivo: Mapped[TipoObjetivo] = mapped_column(enumerado(TipoObjetivo))
    id_objetivo: Mapped[int | None]
    evaluador_especial: Mapped[str | None]
    parametro_evaluador: Mapped[int | None] = mapped_column(default=None)
    condiciones: Mapped[list["CondicionDesbloqueo"]] = relationship(
        back_populates="regla", order_by="CondicionDesbloqueo.id", lazy="selectin",
    )


class CondicionDesbloqueo(Base):
    __tablename__ = "condicion_desbloqueo"
    __table_args__ = (CheckConstraint("cantidad_minima >= 1"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    regla_id: Mapped[int] = mapped_column(ForeignKey("regla_desbloqueo.id"))
    tipo_evento: Mapped[TipoEventoUso] = mapped_column(enumerado(TipoEventoUso))
    id_referencia: Mapped[int | None]
    tipo_conteo: Mapped[TipoConteo] = mapped_column(enumerado(TipoConteo))
    cantidad_minima: Mapped[int]
    regla: Mapped[ReglaDesbloqueo] = relationship(back_populates="condiciones")


class Desbloqueo(Base):
    __tablename__ = "desbloqueo"
    __table_args__ = (UniqueConstraint("cuenta_id", "regla_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("cuenta.id"))
    regla_id: Mapped[int] = mapped_column(ForeignKey("regla_desbloqueo.id"))
    fecha_hora: Mapped[datetime] = mapped_column(DateTime)
    visto: Mapped[bool] = mapped_column(default=False, server_default=false())


class EsquemaVersion(Base):
    __tablename__ = "esquema_version"
    __table_args__ = (CheckConstraint("id = 1"),)
    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    version: Mapped[int]
    semilla: Mapped[str]


class Instrumento(Base):
    __tablename__ = "instrumento"
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(unique=True)
    nombre: Mapped[str]
    descripcion: Mapped[str] = mapped_column(Text)
    tipo_resultado: Mapped[TipoResultado] = mapped_column(enumerado(TipoResultado), default=TipoResultado.DESTACADAS)


class Dimension(Base):
    __tablename__ = "dimension"
    id: Mapped[int] = mapped_column(primary_key=True)
    instrumento_id: Mapped[int] = mapped_column(ForeignKey("instrumento.id"))
    codigo: Mapped[str] = mapped_column(unique=True)
    nombre: Mapped[str]
    descripcion: Mapped[str] = mapped_column(Text)
    orden: Mapped[int]


class EscalaRespuesta(Base):
    __tablename__ = "escala_respuesta"
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(unique=True)
    nombre: Mapped[str]


class OpcionEscala(Base):
    __tablename__ = "opcion_escala"
    __table_args__ = (UniqueConstraint("escala_id", "orden"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    escala_id: Mapped[int] = mapped_column(ForeignKey("escala_respuesta.id"))
    orden: Mapped[int]
    etiqueta: Mapped[str]
    puntaje: Mapped[float]


class ItemInstrumento(Base):
    __tablename__ = "item_instrumento"
    __table_args__ = (UniqueConstraint("instrumento_id", "numero"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    instrumento_id: Mapped[int] = mapped_column(ForeignKey("instrumento.id"))
    codigo: Mapped[str] = mapped_column(unique=True)
    numero: Mapped[int]
    enunciado: Mapped[str] = mapped_column(Text)
    dimension_id: Mapped[int | None] = mapped_column(ForeignKey("dimension.id"))
    escala_id: Mapped[int] = mapped_column(ForeignKey("escala_respuesta.id"))
    inverso: Mapped[bool] = mapped_column(default=False, server_default=false())


class ActividadItem(Base):
    __tablename__ = "actividad_item"
    actividad_id: Mapped[int] = mapped_column(ForeignKey("actividad.id"), primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("item_instrumento.id"), primary_key=True)
    orden: Mapped[int]


class Aplicacion(Base):
    __tablename__ = "aplicacion"
    id: Mapped[int] = mapped_column(primary_key=True)
    instrumento_id: Mapped[int] = mapped_column(ForeignKey("instrumento.id"))
    codigo: Mapped[str] = mapped_column(unique=True)
    nombre: Mapped[str]
    momento: Mapped[MomentoAplicacion] = mapped_column(enumerado(MomentoAplicacion), default=MomentoAplicacion.UNICA)


class AplicacionActividad(Base):
    __tablename__ = "aplicacion_actividad"
    aplicacion_id: Mapped[int] = mapped_column(ForeignKey("aplicacion.id"), primary_key=True)
    actividad_id: Mapped[int] = mapped_column(ForeignKey("actividad.id"), primary_key=True)


class Ocupacion(Base):
    __tablename__ = "ocupacion"
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str | None] = mapped_column(unique=True)
    codigo_onet: Mapped[str] = mapped_column(unique=True)
    titulo: Mapped[str]


class PuntajeOcupacion(Base):
    __tablename__ = "puntaje_ocupacion"
    ocupacion_id: Mapped[int] = mapped_column(ForeignKey("ocupacion.id"), primary_key=True)
    dimension_id: Mapped[int] = mapped_column(ForeignKey("dimension.id"), primary_key=True)
    valor: Mapped[float]


class CarreraOcupacion(Base):
    __tablename__ = "carrera_ocupacion"
    carrera_id: Mapped[int] = mapped_column(ForeignKey("carrera.id"), primary_key=True)
    ocupacion_id: Mapped[int] = mapped_column(ForeignKey("ocupacion.id"), primary_key=True)


class RespuestaItem(Base):
    __tablename__ = "respuesta_item"
    __table_args__ = (UniqueConstraint("progreso_id", "item_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    progreso_id: Mapped[int] = mapped_column(ForeignKey("progreso_actividad.id"))
    item_id: Mapped[int] = mapped_column(ForeignKey("item_instrumento.id"))
    opcion_id: Mapped[int] = mapped_column(ForeignKey("opcion_escala.id"))
    creada_en: Mapped[datetime] = mapped_column(DateTime)
    actualizada_en: Mapped[datetime] = mapped_column(DateTime)


class ResultadoInstrumento(Base):
    __tablename__ = "resultado_instrumento"
    __table_args__ = (
        Index("resultado_vigente_unico", "cuenta_id", "aplicacion_id", unique=True,
              sqlite_where=text("anulado_en IS NULL")),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    cuenta_id: Mapped[int] = mapped_column(ForeignKey("cuenta.id"))
    aplicacion_id: Mapped[int] = mapped_column(ForeignKey("aplicacion.id"))
    calculado_en: Mapped[datetime] = mapped_column(DateTime)
    anulado_en: Mapped[datetime | None] = mapped_column(DateTime)
    perfil_plano: Mapped[bool] = mapped_column(default=False, server_default=false())


class ResultadoDimension(Base):
    __tablename__ = "resultado_dimension"
    resultado_id: Mapped[int] = mapped_column(ForeignKey("resultado_instrumento.id"), primary_key=True)
    dimension_id: Mapped[int] = mapped_column(ForeignKey("dimension.id"), primary_key=True)
    puntaje: Mapped[float]
    puntaje_maximo: Mapped[float]
    porcentaje: Mapped[float]


class Coincidencia(Base):
    __tablename__ = "coincidencia"
    __table_args__ = (
        UniqueConstraint("resultado_id", "posicion"),
        CheckConstraint(f"posicion BETWEEN 1 AND {LIMITE_COINCIDENCIAS}"),
        CheckConstraint(
            f"(correlacion >= {UMBRAL_BEST_FIT} AND ajuste = 'BEST_FIT') OR "
            f"(correlacion >= {UMBRAL_GREAT_FIT} AND correlacion < {UMBRAL_BEST_FIT} AND ajuste = 'GREAT_FIT') OR "
            f"(correlacion >= {CORRELACION_MINIMA} AND correlacion < {UMBRAL_GREAT_FIT} AND ajuste = 'GOOD_FIT')",
            name="ajuste_segun_correlacion",
        ),
    )
    resultado_id: Mapped[int] = mapped_column(ForeignKey("resultado_instrumento.id"), primary_key=True)
    ocupacion_id: Mapped[int] = mapped_column(ForeignKey("ocupacion.id"), primary_key=True)
    posicion: Mapped[int]
    correlacion: Mapped[float]
    ajuste: Mapped[NivelAjuste] = mapped_column(enumerado(NivelAjuste))


class ItemRegistro(Base):
    __tablename__ = "item_registro"
    id: Mapped[int] = mapped_column(primary_key=True)
    codigo: Mapped[str] = mapped_column(unique=True)
    nombre: Mapped[str]
    consigna: Mapped[str] = mapped_column(Text)
    min_caracteres: Mapped[int]
    obligatorio: Mapped[bool]
    repregunta_generica: Mapped[str] = mapped_column(Text)


class CriterioCompletitud(Base):
    __tablename__ = "criterio_completitud"
    __table_args__ = (UniqueConstraint("item_registro_id", "codigo"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    item_registro_id: Mapped[int] = mapped_column(ForeignKey("item_registro.id"))
    codigo: Mapped[str]
    descripcion: Mapped[str] = mapped_column(Text)
    orden: Mapped[int]


class ActividadItemRegistro(Base):
    __tablename__ = "actividad_item_registro"
    actividad_id: Mapped[int] = mapped_column(ForeignKey("actividad.id"), primary_key=True)
    item_registro_id: Mapped[int] = mapped_column(ForeignKey("item_registro.id"), primary_key=True)
    orden: Mapped[int]


class RespuestaRegistro(Base):
    __tablename__ = "respuesta_registro"
    __table_args__ = (UniqueConstraint("progreso_id", "item_registro_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    progreso_id: Mapped[int] = mapped_column(ForeignKey("progreso_actividad.id"))
    item_registro_id: Mapped[int] = mapped_column(ForeignKey("item_registro.id"))
    texto_inicial: Mapped[str] = mapped_column(Text)
    estado: Mapped[EstadoRespuestaRegistro] = mapped_column(enumerado(EstadoRespuestaRegistro))
    clasificacion_inicial: Mapped[ClasificacionRespuesta | None] = mapped_column(enumerado(ClasificacionRespuesta))
    ampliada: Mapped[bool] = mapped_column(default=False, server_default=false())
    creada_en: Mapped[datetime] = mapped_column(DateTime)
    actualizada_en: Mapped[datetime] = mapped_column(DateTime)


class TurnoSeguimiento(Base):
    __tablename__ = "turno_seguimiento"
    __table_args__ = (
        UniqueConstraint("respuesta_id", "orden"),
        CheckConstraint("orden IN (1, 2)", name="orden_seguimiento_valido"),
        CheckConstraint("json_type(criterios_objetivo) = 'array'", name="criterios_objetivo_lista"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    respuesta_id: Mapped[int] = mapped_column(ForeignKey("respuesta_registro.id"))
    orden: Mapped[int]
    pregunta: Mapped[str] = mapped_column(Text)
    criterios_objetivo: Mapped[list[str]] = mapped_column(JSON(none_as_null=True))
    respuesta: Mapped[str | None] = mapped_column(Text)
    respondido_en: Mapped[datetime | None] = mapped_column(DateTime)
    creado_en: Mapped[datetime] = mapped_column(DateTime)


class EvaluacionRespuesta(Base):
    __tablename__ = "evaluacion_respuesta"
    __table_args__ = (
        CheckConstraint("numero >= 1 AND numero = CAST(numero AS INTEGER)", name="numero_evaluacion_valido"),
        CheckConstraint("json_type(criterios_faltantes) = 'array'", name="criterios_faltantes_lista"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    respuesta_id: Mapped[int] = mapped_column(ForeignKey("respuesta_registro.id"))
    numero: Mapped[int]
    origen: Mapped[OrigenEvaluacion] = mapped_column(enumerado(OrigenEvaluacion))
    clasificacion: Mapped[ClasificacionRespuesta] = mapped_column(enumerado(ClasificacionRespuesta))
    criterios_faltantes: Mapped[list[str]] = mapped_column(JSON(none_as_null=True))
    pregunta_generada: Mapped[str | None] = mapped_column(Text)
    requiere_atencion: Mapped[bool] = mapped_column(default=False, server_default=false())
    modelo: Mapped[str | None]
    version_prompt: Mapped[str | None]
    latencia_ms: Mapped[int | None]
    error: Mapped[str | None] = mapped_column(Text)
    texto_evaluado: Mapped[str] = mapped_column(Text)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime)
