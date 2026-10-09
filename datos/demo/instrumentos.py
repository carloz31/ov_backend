import logging

from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from app.core.parametros import (
    DESCRIPCIONES_RIASEC, DIMENSIONES_RIASEC, OPCION_ONET_MAXIMA, OPCION_ONET_MINIMA, transformar_opcion_onet,
)
from app.models import (
    Actividad, ActividadItem, Aplicacion, AplicacionActividad, Audiencia, Bloque, Carrera,
    CarreraOcupacion, CondicionDesbloqueo, Dimension, EscalaRespuesta, Espacio, FamiliaCarrera,
    Instrumento, ItemInstrumento, MomentoAplicacion, Ocupacion, OpcionEscala, PuntajeOcupacion,
    ReglaDesbloqueo, TipoActividad, TipoConteo, TipoEventoUso, TipoObjetivo, TipoResultado,
)
from datos import ocupaciones as datos_ocupaciones
from datos.ocupaciones import OcupacionArchivo


REGISTRO = logging.getLogger(__name__)

# Iteración 1, anexo de cierre, perfil y resultados · F2: textos de TEST-INT.
DESCRIPCIONES_INTELIGENCIAS = {
    "INT-LIN": "Usar las palabras para expresarte, contar historias, explicar y convencer.",
    "INT-LOG": "Razonar con números, patrones y relaciones de causa y efecto.",
    "INT-ESP": "Imaginar, dibujar y orientarte en el espacio, viendo las cosas en tu mente.",
    "INT-CIN": "Usar el cuerpo con precisión para moverte, crear o expresarte.",
    "INT-MUS": "Percibir ritmos, melodías y sonidos, y crear con ellos.",
    "INT-INTER": "Entender a otras personas, ponerte en su lugar y trabajar en equipo.",
    "INT-INTRA": "Conocerte, reconocer lo que sientes y saber qué te motiva.",
}


def cargar_definiciones_instrumentos(sesion: Session) -> None:
    bloque = Bloque(codigo="LAB", numero=0, nombre="Laboratorio de Helena (solo demo)",
                    espacio=Espacio.CIUDAD, audiencia=Audiencia.ESTUDIANTE)
    sesion.add(bloque)
    sesion.flush()
    actividades = {}
    for orden, (codigo, titulo) in enumerate((
        ("LAB-AUT-E", "Autopercepción de entrada"),
        ("LAB-AUT-S", "Autopercepción de salida"),
        ("LAB-HAB", "Mi comportamiento con los demás"),
        ("LAB-INT1", "Explorando mis inteligencias I"),
        ("LAB-INT2", "Explorando mis inteligencias II"),
        ("LAB-RIA1", "Mis intereses I"), ("LAB-RIA2", "Mis intereses II"),
        ("LAB-RIA3", "Mis intereses III"), ("LAB-RIA4", "Mis intereses IV"),
    ), start=1):
        actividades[codigo] = Actividad(codigo=codigo, titulo=titulo, tipo=TipoActividad.CUESTIONARIO,
                                      contenido=codigo.lower().replace("-", "_"),
                                      orden=orden, bloque_id=bloque.id)
    sesion.add_all(actividades.values())
    escalas = {}
    for codigo, nombre in (
        ("ESC-LIKERT5", "Preferencia en cinco opciones"), ("ESC-SI-NO", "Sí o No"),
        ("ESC-FRECUENCIA", "Frecuencia"), ("ESC-A-D", "Autopercepción de A a D"),
    ):
        escalas[codigo] = EscalaRespuesta(codigo=codigo, nombre=nombre)
    sesion.add_all(escalas.values())
    instrumentos = {}
    for codigo, nombre, tipo_resultado in (
        ("TEST-RIASEC", "O*NET Interest Profiler (forma corta)", TipoResultado.COINCIDENCIAS),
        ("TEST-INT", "Explorando mis inteligencias", TipoResultado.DESTACADAS),
        ("TEST-HAB", "Mi comportamiento con los demás", TipoResultado.DESTACADAS),
        ("TEST-AUTO", "Cuestionario de autopercepción", TipoResultado.COMPARACION),
    ):
        instrumentos[codigo] = Instrumento(codigo=codigo, nombre=nombre,
                                          descripcion=f"Instrumento de demostración: {nombre}.", tipo_resultado=tipo_resultado)
    sesion.add_all(instrumentos.values())
    sesion.flush()
    for codigo, opciones in {
        "ESC-LIKERT5": list(zip(
            ("Me disgusta mucho", "Me disgusta", "No estoy seguro", "Me gusta", "Me gusta mucho"),
            (transformar_opcion_onet(orden) for orden in range(OPCION_ONET_MINIMA, OPCION_ONET_MAXIMA + 1)),
            strict=True,
        )),
        "ESC-SI-NO": [("Sí", 1), ("No", 0)],
        "ESC-FRECUENCIA": [("Casi siempre", 1), ("Casi nunca", 0)],
        "ESC-A-D": [("A (Bastante)", 4), ("B (Regular)", 3), ("C (Poco)", 2), ("D (Nada)", 1)],
    }.items():
        sesion.add_all(OpcionEscala(escala_id=escalas[codigo].id, orden=orden,
                                   etiqueta=etiqueta, puntaje=puntaje)
                       for orden, (etiqueta, puntaje) in enumerate(opciones, start=1))

    rejillas = {
        "TEST-RIASEC": [
            (codigo, nombre, [n for n in range(1, 61) if "RRIIAASSEECC"[(n - 1) % 12] == codigo])
            for codigo, nombre in DIMENSIONES_RIASEC
        ],
        "TEST-INT": [
            ("INT-LIN", "Lingüística", [1, 8, 11, 17, 21, 24, 27, 36, 41, 43]),
            ("INT-LOG", "Lógico-matemática", [3, 6, 13, 20, 25, 28, 37]),
            ("INT-ESP", "Espacial", [7, 18, 26, 29]),
            ("INT-CIN", "Cinestésico-corporal", [2, 14, 19, 30, 38]),
            ("INT-MUS", "Musical", [5, 10, 31, 39]),
            ("INT-INTER", "Interpersonal", [4, 9, 16, 22, 32, 34, 40, 42]),
            ("INT-INTRA", "Intrapersonal", [12, 15, 23, 33, 35]),
        ],
        "TEST-HAB": [
            ("HAB-ASE", "Asertividad (oficial)", [1, 10, 15, 19, 21]),
            ("HAB-EMP", "Empatía (provisional)", [4, 7, 16, 22]),
            ("HAB-LID", "Liderazgo (provisional)", [5, 14, 20]),
            ("HAB-RES", "Resolución de problemas (provisional)", [6, 13, 17, 24]),
            ("HAB-EXP", "Expresión de sentimientos (provisional)", [3, 8, 23]),
            ("HAB-VAL", "Valores y participación (provisional)", [2, 9, 11, 12, 18]),
        ],
    }
    dimensiones_por_item = {}
    for instrumento, filas in rejillas.items():
        for orden, (codigo, nombre, numeros) in enumerate(filas, start=1):
            descripcion = (
                DESCRIPCIONES_RIASEC[codigo] if instrumento == "TEST-RIASEC" else
                DESCRIPCIONES_INTELIGENCIAS[codigo] if instrumento == "TEST-INT" else
                f"Dimensión de demostración: {nombre}."
            )
            dimension = Dimension(instrumento_id=instrumentos[instrumento].id, codigo=codigo,
                                  nombre=nombre, descripcion=descripcion, orden=orden)
            sesion.add(dimension)
            for numero in numeros:
                if (instrumento, numero) in dimensiones_por_item:
                    raise ValueError(f"Ítem con más de una dimensión: {instrumento}, {numero}")
                dimensiones_por_item[instrumento, numero] = dimension
    sesion.flush()
    enunciados_auto = (
        "Tengo información acerca de cómo se desempeña un profesional en la carrera que me gusta.",
        "Conozco las instituciones dónde estudiar la carrera que me gusta.",
        "La elección de mi futura profesión está influenciada por los consejos de mi grupo de amigos/as.",
        "Mis padres o algún otro pariente han contribuido mucho a la decisión de mi futura profesión.",
        "Tengo razones para decir que me gusta mi futura profesión porque goza de buena reputación y de reconocimiento social.",
        "La decisión de mi futura profesión está influenciada por el dinero que podré recibir de ella.",
        "Siendo consciente de los recursos económicos de mi familia, me siento obligado a elegir una profesión que no es de mi total satisfacción.",
        "Pienso que una carrera de mando intermedio no tiene la reputación social que deseo, por ello no la considero una posibilidad.",
        "En realidad estoy seguro(a) de lo que voy a estudiar.",
        "Los calificativos más altos que he obtenido están en los cursos que considero elementales para mi futura profesión.",
    )
    items = {}
    for instrumento, prefijo, cantidad, escala in (
        ("TEST-RIASEC", "RIASEC", 60, "ESC-LIKERT5"), ("TEST-INT", "INT", 43, "ESC-SI-NO"),
        ("TEST-HAB", "HAB", 24, "ESC-FRECUENCIA"), ("TEST-AUTO", "AUT", 10, "ESC-A-D"),
    ):
        for numero in range(1, cantidad + 1):
            dimension = dimensiones_por_item.get((instrumento, numero))
            if instrumento != "TEST-AUTO" and dimension is None:
                raise ValueError(f"Ítem sin dimensión: {instrumento}, {numero}")
            item = ItemInstrumento(
                instrumento_id=instrumentos[instrumento].id, codigo=f"{prefijo}-{numero:02}", numero=numero,
                enunciado=enunciados_auto[numero - 1] if instrumento == "TEST-AUTO" else
                f"Ítem {numero} de {instrumentos[instrumento].nombre}",
                dimension_id=None if dimension is None else dimension.id, escala_id=escalas[escala].id,
                inverso=instrumento == "TEST-HAB" and numero in {3, 5, 8, 20},
            )
            items[instrumento, numero] = item
            sesion.add(item)
    aplicaciones = {}
    for codigo, instrumento, nombre, momento in (
        ("APL-RIASEC", "TEST-RIASEC", "Intereses", MomentoAplicacion.UNICA),
        ("APL-INT", "TEST-INT", "Inteligencias", MomentoAplicacion.UNICA),
        ("APL-HAB", "TEST-HAB", "Habilidades sociales", MomentoAplicacion.UNICA),
        ("APL-AUTO-ENT", "TEST-AUTO", "Autopercepción de entrada", MomentoAplicacion.ENTRADA),
        ("APL-AUTO-SAL", "TEST-AUTO", "Autopercepción de salida", MomentoAplicacion.SALIDA),
    ):
        aplicaciones[codigo] = Aplicacion(codigo=codigo, instrumento_id=instrumentos[instrumento].id,
                                         nombre=nombre, momento=momento)
    sesion.add_all(aplicaciones.values())
    sesion.flush()
    for aplicacion, actividad, instrumento, inicio, fin in (
        ("APL-AUTO-ENT", "LAB-AUT-E", "TEST-AUTO", 1, 10),
        ("APL-AUTO-SAL", "LAB-AUT-S", "TEST-AUTO", 1, 10),
        ("APL-HAB", "LAB-HAB", "TEST-HAB", 1, 24),
        ("APL-INT", "LAB-INT1", "TEST-INT", 1, 22), ("APL-INT", "LAB-INT2", "TEST-INT", 23, 43),
        ("APL-RIASEC", "LAB-RIA1", "TEST-RIASEC", 1, 15),
        ("APL-RIASEC", "LAB-RIA2", "TEST-RIASEC", 16, 30),
        ("APL-RIASEC", "LAB-RIA3", "TEST-RIASEC", 31, 45),
        ("APL-RIASEC", "LAB-RIA4", "TEST-RIASEC", 46, 60),
    ):
        sesion.add(AplicacionActividad(aplicacion_id=aplicaciones[aplicacion].id, actividad_id=actividades[actividad].id))
        sesion.add_all(ActividadItem(actividad_id=actividades[actividad].id, item_id=items[instrumento, numero].id,
                                     orden=orden)
                       for orden, numero in enumerate(range(inicio, fin + 1), start=1))
    for objetivo, anterior in (
        ("LAB-AUT-S", "LAB-AUT-E"), ("LAB-INT2", "LAB-INT1"),
        ("LAB-RIA2", "LAB-RIA1"), ("LAB-RIA3", "LAB-RIA2"), ("LAB-RIA4", "LAB-RIA3"),
    ):
        regla = ReglaDesbloqueo(codigo=f"R-{objetivo}", nombre=f"Desbloquear {objetivo}",
                               tipo_objetivo=TipoObjetivo.ACTIVIDAD, id_objetivo=actividades[objetivo].id)
        regla.condiciones.append(CondicionDesbloqueo(tipo_evento=TipoEventoUso.COMPLETA_ACTIVIDAD,
                                                   id_referencia=actividades[anterior].id,
                                                   tipo_conteo=TipoConteo.EVENTOS, cantidad_minima=1))
        sesion.add(regla)
    familia = sesion.scalar(select(FamiliaCarrera).where(FamiliaCarrera.codigo == "FAM-INGENIERIA"))
    for codigo, nombre in (("CAR-AGR", "Ingeniería agrícola"), ("CAR-FOR", "Ingeniería forestal"),
                           ("CAR-AMB", "Ingeniería ambiental")):
        sesion.add(Carrera(codigo=codigo, nombre=nombre, familia_id=familia.id))
    sesion.flush()
    datos_ocupaciones.validar_distribucion_items(sesion)


def relaciones_carreras(ocupaciones: list[OcupacionArchivo]) -> dict[str, tuple[str, ...]]:
    relaciones = {
        "CAR-ENF": ("29-1141.00",), "CAR-MED": ("29-1216.00",), "CAR-CIV": ("17-2051.00",),
        "CAR-DIS": ("27-1024.00",), "CAR-ADM": ("11-1021.00",), "CAR-AGR": ("17-2021.00",),
        "CAR-FOR": ("19-1031.02", "19-1032.00"), "CAR-AMB": ("17-2199.11", "19-2041.02"),
    }
    codigos = {ocupacion.codigo_onet for ocupacion in ocupaciones}
    if "29-1216.00" not in codigos:
        alternativo = next((o.codigo_onet for o in ocupaciones if o.codigo_onet.startswith("29-12")), None)
        if alternativo is not None:
            relaciones["CAR-MED"] = (alternativo,)
            REGISTRO.warning("CAR-MED: falta 29-1216.00; se usa %s, primero con prefijo 29-12 en el archivo", alternativo)
    for carrera, referencias in relaciones.items():
        for codigo in referencias:
            if codigo not in codigos:
                raise ValueError(f"Falta la ocupación O*NET {codigo}, requerida por {carrera}")
    return relaciones


def cargar_catalogo_ocupaciones(sesion: Session) -> None:
    filas = datos_ocupaciones.leer_ocupaciones(datos_ocupaciones.RUTA_OCUPACIONES)
    relaciones = relaciones_carreras(filas)
    sesion.execute(insert(Ocupacion), [{"codigo_onet": fila.codigo_onet, "titulo": fila.titulo} for fila in filas])
    ocupaciones = dict(sesion.execute(select(Ocupacion.codigo_onet, Ocupacion.id)).all())
    dimensiones = dict(sesion.execute(select(Dimension.codigo, Dimension.id).join(
        Instrumento, Instrumento.id == Dimension.instrumento_id,
    ).where(Instrumento.tipo_resultado == TipoResultado.COINCIDENCIAS)).all())
    columnas = {codigo: posicion for posicion, codigo in enumerate(datos_ocupaciones.COLUMNAS_OCUPACIONES[2:])}
    sesion.execute(insert(PuntajeOcupacion), [
        {"ocupacion_id": ocupaciones[fila.codigo_onet], "dimension_id": dimension_id,
         "valor": fila.valores[columnas[dimension]]}
        for fila in filas for dimension, dimension_id in dimensiones.items()
    ])
    carreras = dict(sesion.execute(select(Carrera.codigo, Carrera.id)).all())
    sesion.execute(insert(CarreraOcupacion), [
        {"carrera_id": carreras[carrera], "ocupacion_id": ocupaciones[codigo]}
        for carrera, codigos in relaciones.items() for codigo in codigos
    ])
