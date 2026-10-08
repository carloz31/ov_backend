from uuid import uuid4

from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from app.core.contexto import contexto, usar_contexto
from app.exceptions import ErrorAccion
from app.models import (
    Conversacion, ConversacionVinculo, Cuenta, Entrevista, EntrevistaAutor, Rol, TipoEventoUso,
    TipoObjetivo, VinculoFamiliar,
)
from app.schemas.acciones import (
    CompletarConversacionEntrada, EscribirCartaEntrada, PublicarEntrevistaEntrada, RespuestaAccion,
    RespuestaAgrupada,
)
from app.schemas.comunidad import ConversacionesEstado
from app.services.comun import (
    buscar_por_codigo, exigir_disponible, exigir_estudiante, existe_evento, fecha_accion,
    responder_con_eventos, responder_varias_cuentas,
)
from app.services.motor.reglas import objetivo_disponible


@usar_contexto
def publicar_entrevista(sesion: Session, entrada: PublicarEntrevistaEntrada) -> RespuestaAgrupada:
    por_codigo = {cuenta.codigo: cuenta for cuenta in sesion.scalars(select(Cuenta).where(Cuenta.codigo.in_(entrada.autores)))}
    if any(codigo not in por_codigo for codigo in entrada.autores):
        raise ErrorAccion("Cuenta o referencia no encontrada", estado_http=404)
    cuentas = [por_codigo[codigo] for codigo in entrada.autores]
    for cuenta in cuentas:
        exigir_estudiante(cuenta)
    fecha = fecha_accion(entrada)
    entrevista = Entrevista(codigo=f"ENT-{uuid4().hex}", resumen=entrada.resumen, fecha_hora=fecha)
    sesion.add(entrevista)
    sesion.flush()
    sesion.execute(insert(EntrevistaAutor.__table__), [dict(entrevista_id=entrevista.id, cuenta_id=cuenta.id) for cuenta in cuentas])
    return responder_varias_cuentas(sesion, cuentas, {
        cuenta.id: [(TipoEventoUso.PUBLICA_ENTREVISTA, entrevista.id)] for cuenta in cuentas
    }, fecha)


def vinculo_de_cuenta(sesion: Session, cuenta: Cuenta) -> VinculoFamiliar:
    filtro = VinculoFamiliar.estudiante_id == cuenta.id if cuenta.rol == Rol.ESTUDIANTE else (
        VinculoFamiliar.apoderado_id == cuenta.id
    )
    vinculo = sesion.scalar(select(VinculoFamiliar).where(filtro).order_by(VinculoFamiliar.codigo).limit(1))
    if vinculo is None:
        raise ErrorAccion("La cuenta no pertenece a un vínculo familiar")
    return vinculo


@usar_contexto
def escribir_carta(sesion: Session, entrada: EscribirCartaEntrada) -> RespuestaAccion:
    cuenta = buscar_por_codigo(sesion, Cuenta, entrada.cuenta)
    vinculo = vinculo_de_cuenta(sesion, cuenta)
    columna = "carta_estudiante" if cuenta.rol == Rol.ESTUDIANTE else "carta_apoderado"
    primera = getattr(vinculo, columna) is None and not existe_evento(
        sesion, cuenta, TipoEventoUso.ESCRIBE_CARTA, vinculo.id,
    )
    setattr(vinculo, columna, entrada.texto)
    eventos = [(TipoEventoUso.ESCRIBE_CARTA, vinculo.id)] if primera else []
    return responder_con_eventos(sesion, cuenta, eventos, fecha_accion(entrada))


@usar_contexto
def completar_conversacion(sesion: Session, entrada: CompletarConversacionEntrada) -> RespuestaAgrupada:
    cuenta = buscar_por_codigo(sesion, Cuenta, entrada.cuenta)
    conversacion = buscar_por_codigo(sesion, Conversacion, entrada.conversacion)
    vinculo = vinculo_de_cuenta(sesion, cuenta)
    contexto(sesion).cargar_desbloqueos([vinculo.estudiante_id, vinculo.apoderado_id])
    exigir_disponible(sesion, cuenta, TipoObjetivo.CONVERSACIONES)
    ids_cuentas = (vinculo.estudiante_id, vinculo.apoderado_id)
    por_id = {otra.id: otra for otra in sesion.scalars(select(Cuenta).where(Cuenta.id.in_(ids_cuentas)))}
    cuentas = [por_id[identificador] for identificador in ids_cuentas]
    contexto(sesion).cargar_desbloqueos(ids_cuentas)
    registro = sesion.scalar(select(ConversacionVinculo).where(
        ConversacionVinculo.vinculo_id == vinculo.id, ConversacionVinculo.conversacion_id == conversacion.id,
    ))
    primera = registro is None or not registro.conversado
    fecha = fecha_accion(entrada)
    if primera:
        if registro is None:
            registro = ConversacionVinculo(vinculo_id=vinculo.id, conversacion_id=conversacion.id)
            sesion.add(registro)
        registro.conversado = True
        registro.conversado_en = fecha
    if primera:
        contexto(sesion).cargar_conteos(ids_cuentas)
    eventos_por_cuenta = {
        otra.id: [(TipoEventoUso.COMPLETA_CONVERSACION, conversacion.id)] if primera and not existe_evento(
            sesion, otra, TipoEventoUso.COMPLETA_CONVERSACION, conversacion.id,
        ) else [] for otra in cuentas
    }
    return responder_varias_cuentas(sesion, cuentas, eventos_por_cuenta, fecha)


@usar_contexto
def estado_conversaciones(sesion: Session, cuenta: Cuenta) -> ConversacionesEstado:
    return ConversacionesEstado(
        estado="DISPONIBLE" if objetivo_disponible(sesion, cuenta, TipoObjetivo.CONVERSACIONES, None)
        else "BLOQUEADA",
    )
