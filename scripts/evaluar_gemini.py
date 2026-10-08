"""Prueba manual de §10. Ejecutar solo tras autorizar llamadas reales a Gemini."""

import argparse
from dataclasses import dataclass, replace
from math import isfinite
import os
from pathlib import Path
import sys
from time import sleep
from urllib.parse import quote

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm import Session

from app.core.parametros import PAUSA_CASOS_GEMINI_SEGUNDOS, VERSION_PROMPT_REGISTRO
from app.config import cargar_configuracion_registro, ErrorConfiguracionRegistro
from app.models.base import Base
from app.database import crear_motor_bd
from app.core.definiciones import Definiciones
from app.services.registro.gemini import EvaluadorGemini, ErrorClienteGemini
from app.services.registro.evaluacion import (
    ContextoEvaluacion, ConversacionEvaluacion, CriterioEvaluacion, EvaluacionProcesada,
    RespuestaAnterior, TurnoEvaluacion, evaluar_respuesta,
)
from app.models import Actividad, ItemRegistro
from datos.demo.registro import cargar_definiciones_registro


RUTA_REPORTE = Path(__file__).resolve().parent.parent / 'docs' / 'evaluacion_gemini.md'


@dataclass(frozen=True, slots=True)
class CasoGemini:
    item: str
    texto: str
    esperada: str
    respuesta_turno_1: str | None = None
    esperada_turno_1: str | None = None


@dataclass(frozen=True, slots=True)
class CasoPreparado:
    contexto: ContextoEvaluacion
    min_caracteres: int
    repregunta_generica: str


@dataclass(frozen=True, slots=True)
class ResultadoCasoGemini:
    numero: int
    item: str
    turno: int
    texto: str
    esperada: str
    evaluacion: EvaluacionProcesada | None
    pregunta_respondida: str = ''
    observacion: str = ''


CASOS = (
    CasoGemini('REG-HAB-1', 'Asertividad, porque es importante para el futuro.', 'VAGA (falta C2)'),
    CasoGemini('REG-HAB-1', 'La asertividad, porque en los trabajos grupales me quedo callado aunque no esté de acuerdo.', 'ADECUADA'),
    CasoGemini('REG-HAB-1', 'Quiero mejorar en todo, la verdad no sé bien qué elegir.', 'VAGA'),
    CasoGemini('REG-HAB-1', 'Trabajo en equipo, porque cuando hacemos proyectos en el colegio siempre termino haciendo todo yo solo.', 'ADECUADA'),
    CasoGemini('REG-HAB-2', 'Voy a esforzarme más y ser mejor persona con los demás.', 'VAGA'),
    CasoGemini('REG-HAB-2', 'En el próximo trabajo de Comunicación voy a decir mi opinión al menos una vez antes de que decidamos.', 'ADECUADA'),
    CasoGemini('REG-HAB-2', 'Voy a practicar hablando más.', 'VAGA (falta C2)'),
    CasoGemini('REG-HAB-2', 'Los sábados, cuando juego fútbol con mi barrio, voy a pedir el balón y organizar al equipo.', 'ADECUADA'),
    CasoGemini('REG-HAB-3', 'Me sentiré mejor conmigo mismo y más feliz.', 'VAGA'),
    CasoGemini('REG-HAB-3', 'Cuando en una reunión diga que no estoy de acuerdo sin quedarme pensando en eso después.', 'ADECUADA'),
    CasoGemini('REG-HAB-3', 'Mis notas van a subir.', 'VAGA (falta C2)'),
    CasoGemini('REG-HAB-1', 'Empatía, aunque creo que está sobrevalorada; igual me serviría, porque cuando mis amigos me cuentan sus problemas no sé qué decirles.', 'ADECUADA (opinión discutible, pero cumple C1 y C2)'),
    CasoGemini('REG-HAB-2', 'jajaja no sé, lo que sea', 'VAGA'),
    CasoGemini('REG-HAB-1', 'Ninguna, porque en mi casa me dicen que no sirvo para nada y ya no me importa.', 'requiere atención'),
    CasoGemini('REG-HAB-1', 'Me gustaría mejorar mi comunicación, porque siento que es un punto débil mío.',
               'VAGA (falta C2)', 'En los trabajos grupales, cuando no estoy de acuerdo, me quedo callado.', 'ADECUADA'),
    CasoGemini('REG-HAB-2', 'Voy a esforzarme más.', 'VAGA (faltan C1 y C2)',
               'No sé, más seguido.', 'VAGA (segunda pregunta distinta de la primera)'),
)


def preparar_casos():
    # Definiciones oficiales, sin catálogo Excel ni abrir/modificar demo.db.
    motor = crear_motor_bd('sqlite:///:memory:')
    try:
        Base.metadata.create_all(motor)
        with Session(motor) as sesion, sesion.begin():
            cargar_definiciones_registro(sesion)
        with motor.connect() as conexion:
            definiciones = Definiciones(conexion)
        actividad = definiciones.por_codigo(Actividad, 'REG-ACT08')
        items = definiciones.items_registro_por_actividad[actividad.id]
        anteriores = (
            RespuestaAnterior(items[0].consigna, ConversacionEvaluacion(CASOS[1].texto)),
            RespuestaAnterior(items[1].consigna, ConversacionEvaluacion(CASOS[5].texto)),
        )
        preparados = []
        for caso in CASOS:
            item = definiciones.por_codigo(ItemRegistro, caso.item)
            orden = items.index(item)
            contexto = ContextoEvaluacion(
                actividad.titulo, item.consigna,
                tuple(CriterioEvaluacion(c.codigo, c.descripcion)
                      for c in definiciones.criterios_por_item_registro[item.id]),
                anteriores[:orden], ConversacionEvaluacion(caso.texto),
                tuple(c.codigo for c in definiciones.criterios_por_item_registro[item.id]),
            )
            preparados.append(CasoPreparado(contexto, item.min_caracteres, item.repregunta_generica))
        return tuple(preparados)
    finally:
        motor.dispose()


def celda(valor):
    from html import escape
    return escape(str(valor)).replace('|', '&#124;').replace('\r', '').replace('\n', '<br>')


def ejecutar_casos(evaluador, configuracion, ruta=RUTA_REPORTE, *, pausa=PAUSA_CASOS_GEMINI_SEGUNDOS,
                  esperar=sleep):
    if not isfinite(pausa) or pausa < 0:
        raise ValueError('La pausa debe ser no negativa y finita')
    preparados = preparar_casos()
    filas = [
        '# Evaluación Gemini de registro', '',
        f'Modelo: {celda(configuracion.modelo)}. Prompt: {VERSION_PROMPT_REGISTRO}.', '',
        'Los 16 textos iniciales llegan al LLM, incluidos los cortos. '
        'Las respuestas previas usan los casos 2 y 6; no se persisten respuestas ni eventos.', '',
        'Casos 15 y 16: se responde el turno 1 solo si fue generado. Se usa la pregunta '
        'recibida y se evalúa la conversación completa. El caso 16 termina al observar '
        'la segunda pregunta: no se inventa una respuesta al turno 2. Si falla el LLM, '
        'se aplica el mismo respaldo por longitud que en la aplicación.', '',
        'Revisión manual: en el caso 15 la primera pregunta debe tratar solo C2; en el '
        'caso 16 debe tratar C1 y C2, y la segunda debe ser distinta de la primera. '
        'La salida estructurada no acredita por sí sola esos resultados semánticos.', '',
        '| # | Ítem | Envío | Texto | Pregunta respondida | Esperada | Obtenida | Criterios faltantes | Pregunta generada | Requiere atención | Latencia ms | Origen | Error | Observación |',
        '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|',
    ]
    resultados = []
    llamadas = 0
    def evaluar(contexto, preparado):
        nonlocal llamadas
        if llamadas:
            esperar(pausa)
        llamadas += 1
        return evaluar_respuesta(
            contexto, preparado.min_caracteres, preparado.repregunta_generica, evaluador, modelo=configuracion.modelo,
            tiempo_maximo_segundos=configuracion.timeout_segundos,
        )

    for numero, (caso, preparado) in enumerate(zip(CASOS, preparados, strict=True), start=1):
        contexto = preparado.contexto
        inicial = evaluar(contexto, preparado)
        resultados.append(ResultadoCasoGemini(numero, caso.item, 0, caso.texto, caso.esperada, inicial))
        if caso.respuesta_turno_1 is None:
            continue
        seguimiento, pregunta, observacion = None, '', ''
        if inicial.clasificacion != 'VAGA' or inicial.requiere_atencion:
            observacion = 'No ejecutado: el inicial finalizó sin seguimiento.'
        elif inicial.origen == 'RESPALDO_LONGITUD':
            pregunta = inicial.pregunta
            observacion = 'Turno genérico respondido y aceptado sin nueva evaluación.'
        else:
            pregunta = inicial.pregunta
            contexto_turno = replace(contexto,
                conversacion=ConversacionEvaluacion(caso.texto, (TurnoEvaluacion(pregunta, caso.respuesta_turno_1),)),
                criterios_faltantes_previos=inicial.criterios_faltantes)
            seguimiento = evaluar(contexto_turno, preparado)
        resultados.append(ResultadoCasoGemini(numero, caso.item, 1, caso.respuesta_turno_1,
            caso.esperada_turno_1, seguimiento, pregunta, observacion))

    for fila in resultados:
        resultado = fila.evaluacion
        columnas = (fila.numero, fila.item, 'Inicial' if fila.turno == 0 else f'Turno {fila.turno}',
                    fila.texto, fila.pregunta_respondida, fila.esperada,
                    resultado.clasificacion if resultado is not None else 'Sin nueva evaluación',
                    ', '.join(resultado.criterios_faltantes) if resultado is not None else '',
                    (resultado.pregunta or '') if resultado is not None else '',
                    resultado.requiere_atencion if resultado is not None else '',
                    resultado.latencia_ms if resultado is not None else '',
                    resultado.origen if resultado is not None else '',
                    (resultado.error or '') if resultado is not None else '', fila.observacion)
        filas.append('| ' + ' | '.join(celda(valor) for valor in columnas) + ' |')
    reporte = '\n'.join(filas) + '\n'
    # Protección adicional frente a una respuesta externa que reproduzca la clave.
    if configuracion.clave:
        for secreto in (configuracion.clave, quote(configuracion.clave, safe='')):
            reporte = reporte.replace(celda(secreto), '[secreto omitido]')
    ruta.write_text(reporte, encoding='utf-8')
    return tuple(resultados)


def main(argumentos=None):
    analizador = argparse.ArgumentParser(description=__doc__)
    analizador.add_argument('--pausa', type=float, default=PAUSA_CASOS_GEMINI_SEGUNDOS,
                            help='Segundos entre llamadas; ajustar a la cuota disponible (por defecto 5).')
    opciones = analizador.parse_args(argumentos)
    if not isfinite(opciones.pausa) or opciones.pausa < 0:
        analizador.error('La pausa debe ser no negativa y finita')
    evaluador = None
    try:
        # Este comando manual siempre pide Gemini; no cambia el entorno de la aplicación.
        configuracion = cargar_configuracion_registro(entorno={**os.environ, 'EVALUADOR': 'gemini'})
        evaluador = EvaluadorGemini(configuracion)
        ejecutar_casos(evaluador, configuracion, pausa=opciones.pausa)
        print('Reporte generado en docs/evaluacion_gemini.md')
        return 0
    except (ErrorConfiguracionRegistro, ErrorClienteGemini) as error:
        # Los errores propios de configuración/cliente ya contienen mensajes saneados.
        print(str(error), file=sys.stderr)
        return 1
    except Exception:
        print('No se pudo generar el reporte de evaluación Gemini', file=sys.stderr)
        return 1
    finally:
        if evaluador is not None:
            try:
                evaluador.cerrar()
            except RuntimeError:
                print('No se pudo cerrar el cliente Gemini', file=sys.stderr)


if __name__ == '__main__':
    raise SystemExit(main())
