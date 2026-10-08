from datetime import datetime, timedelta, timezone

from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from app.core.contexto import contexto, usar_contexto
from app.core.definiciones import MODELOS_FIJOS
from app.exceptions import ErrorAccion
from app.models import Cuenta, Desbloqueo, EventoUso, Rol, TipoEventoUso, TipoObjetivo
from app.schemas.acciones import FechaAccion, RespuestaAccion, RespuestaAgrupada
from app.schemas.comun import ContenidoEstado
from app.schemas.cuentas import EventoLegible
from app.schemas.motor import DesbloqueoNuevo
from app.services.motor.referencias import referencia_legible
from app.services.motor.reglas import objetivo_disponible, registrar_eventos


def fecha_accion(entrada: FechaAccion) -> datetime:
    fecha = entrada.fecha_hora or datetime.now(timezone(timedelta(hours=-5)))
    # Se conserva el calendario simulado, como en los conteos de la fase 2.
    return fecha.replace(tzinfo=None)


@usar_contexto
def buscar_por_codigo(sesion: Session, modelo, codigo: str):
    entidad = (contexto(sesion).definiciones.por_codigo(modelo, codigo) if modelo in MODELOS_FIJOS
               else sesion.scalar(select(modelo).where(modelo.codigo == codigo)))
    if entidad is None:
        raise ErrorAccion("Cuenta o referencia no encontrada", estado_http=404)
    return entidad


def exigir_estudiante(cuenta: Cuenta) -> None:
    if cuenta.rol != Rol.ESTUDIANTE:
        raise ErrorAccion("Esta acción solo está permitida para estudiantes")


def exigir_disponible(sesion: Session, cuenta: Cuenta, tipo: TipoObjetivo, entidad=None) -> None:
    from app.services.cuentas import progreso_objetivo

    identificador = None if entidad is None else entidad.id
    if objetivo_disponible(sesion, cuenta, tipo, identificador):
        return
    codigo = "-" if entidad is None else entidad.codigo
    try:
        progreso = progreso_objetivo(sesion, cuenta, tipo, codigo)
    except (LookupError, PermissionError):
        progreso = None
    raise ErrorAccion("El objetivo no está disponible para esta cuenta", progreso=progreso)


@usar_contexto
def existe_evento(sesion: Session, cuenta: Cuenta, tipo: TipoEventoUso, referencia: int) -> bool:
    from app.models import TipoConteo
    return contexto(sesion).contar(cuenta.id, tipo, referencia, TipoConteo.EVENTOS) > 0


@usar_contexto
def responder_con_eventos(
    sesion: Session, cuenta: Cuenta, eventos: list[tuple[TipoEventoUso, int | None]], fecha: datetime,
) -> RespuestaAccion:
    nuevos = registrar_eventos(sesion, cuenta, eventos, fecha)
    # Permite omitir solo el evaluador ausente, conservando referencias null en la API.
    nuevos = [nuevo if nuevo.evaluador_especial is not None else DesbloqueoNuevo.model_validate(
        nuevo.model_dump(exclude={"evaluador_especial"}),
    ) for nuevo in nuevos]
    return RespuestaAccion(
        eventos_registrados=[EventoLegible(
            tipo=tipo, referencia=referencia_legible(sesion, tipo, referencia), fecha_hora=fecha,
        ) for tipo, referencia in eventos],
        nuevos_desbloqueos=nuevos,
    )


@usar_contexto
def responder_varias_cuentas(sesion, cuentas, eventos_por_cuenta, fecha):
    filas = [dict(cuenta_id=cuenta.id, tipo=tipo, id_referencia=referencia, fecha_hora=fecha)
             for cuenta in cuentas for tipo, referencia in eventos_por_cuenta[cuenta.id]]
    if not filas:
        return RespuestaAgrupada(por_cuenta={cuenta.codigo: responder_con_eventos(sesion, cuenta, [], fecha) for cuenta in cuentas})
    sesion.flush()
    sesion.execute(insert(EventoUso.__table__), filas)
    datos = contexto(sesion)
    ids_cuentas = [cuenta.id for cuenta in cuentas]
    for cuenta_id in ids_cuentas:
        datos.invalidar_eventos(cuenta_id)
    datos.cargar_conteos(ids_cuentas)
    datos.cargar_desbloqueos(ids_cuentas)
    sesion.info['lote_eventos'] = set(ids_cuentas)
    sesion.info['lote_desbloqueos'] = []
    try:
        respuestas = {cuenta.codigo: responder_con_eventos(sesion, cuenta, eventos_por_cuenta[cuenta.id], fecha)
                      for cuenta in cuentas}
        pendientes = sesion.info['lote_desbloqueos']
        if pendientes:
            sesion.execute(insert(Desbloqueo.__table__), pendientes)
        return RespuestaAgrupada(por_cuenta=respuestas)
    finally:
        sesion.info.pop('lote_eventos', None)
        sesion.info.pop('lote_desbloqueos', None)


@usar_contexto
def estado_contenido(sesion: Session, cuenta: Cuenta, modelo, tipo: TipoObjetivo) -> list[ContenidoEstado]:
    return [ContenidoEstado(
        codigo=contenido.codigo, titulo=contenido.titulo,
        estado="DISPONIBLE" if objetivo_disponible(sesion, cuenta, tipo, contenido.id) else "BLOQUEADA",
    ) for contenido in sorted(contexto(sesion).definiciones.listar(modelo), key=lambda contenido: contenido.codigo)]
