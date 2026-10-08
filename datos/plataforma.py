"""Semilla de prueba de la iteración 1 (§4.3), sin estado de estudiantes.

DATO DE PRUEBA: tablas estáticas adaptadas de la spec y del frontend.
La transacción pertenece al llamador; este módulo no confirma ni migra.
"""

from sqlalchemy import insert
from sqlalchemy.orm import Session

from app import models as modelos
from app.core.parametros import DIMENSIONES_RIASEC, transformar_opcion_onet
from datos.ocupaciones import RUTA_OCUPACIONES, leer_ocupaciones, validar_distribucion_items


CUENTAS = (('est-ana', 'Ana', 'ESTUDIANTE'), ('est-luis', 'Luis', 'ESTUDIANTE'), ('apo-rosa', 'Rosa', 'APODERADO'))

BLOQUES = (('CAMINO', 1, 'El camino', 'MISIONES_CAMPO', 'ESTUDIANTE'),
 ('CIUDAD', 2, 'La ciudad', 'CIUDAD', 'ESTUDIANTE'))

ACTIVIDADES_CAMINO = (('mission-welcome', 'El inicio del viaje', 'INFORMATIVA'),
 ('enc-mitos', 'La plaza de los rumores', 'INFORMATIVA'),
 ('act-07', 'Mis propios pregones', 'REGISTRO'),
 ('mission-story', 'Las huellas que traigo', 'REGISTRO'),
 ('mission-future', 'Mi horizonte', 'REGISTRO'),
 ('mission-compass', 'Mi brújula personal', 'CUESTIONARIO'),
 ('act-06', 'Mi mapa de ruta', 'REGISTRO'),
 ('mission-expectations', 'Preparar la mochila', 'REGISTRO'),
 ('mission-next-step', 'Elegir mi siguiente paso', 'REGISTRO'))

# DATO DE PRUEBA: títulos de las interacciones 02–14 según §4.3.2.
ACTIVIDADES_CIUDAD = (('act-tip-01', 'Una vuelta por el molino', 'CUESTIONARIO'),
 ('act-tip-02', 'Mara: interacción 2 de 14', 'CUESTIONARIO'),
 ('act-tip-03', 'Mara: interacción 3 de 14', 'CUESTIONARIO'),
 ('act-tip-04', 'Mara: interacción 4 de 14', 'CUESTIONARIO'),
 ('act-tip-05', 'Mara: interacción 5 de 14', 'CUESTIONARIO'),
 ('act-tip-06', 'Mara: interacción 6 de 14', 'CUESTIONARIO'),
 ('act-tip-07', 'Mara: interacción 7 de 14', 'CUESTIONARIO'),
 ('act-tip-08', 'Mara: interacción 8 de 14', 'CUESTIONARIO'),
 ('act-tip-09', 'Mara: interacción 9 de 14', 'CUESTIONARIO'),
 ('act-tip-10', 'Mara: interacción 10 de 14', 'CUESTIONARIO'),
 ('act-tip-11', 'Mara: interacción 11 de 14', 'CUESTIONARIO'),
 ('act-tip-12', 'Mara: interacción 12 de 14', 'CUESTIONARIO'),
 ('act-tip-13', 'Mara: interacción 13 de 14', 'CUESTIONARIO'),
 ('act-tip-14', 'Mara: interacción 14 de 14', 'CUESTIONARIO'),
 ('act-tip-final', 'Las pistas que hablan de ti', 'INFORMATIVA'))

CONTENIDOS_ACTIVIDADES = {
    'mission-welcome': 'mision_bienvenida',
    'enc-mitos': 'encuentro_mitos',
    'act-07': 'registro_mis_pregones',
    'mission-story': 'registro_huellas',
    'mission-future': 'registro_horizonte',
    'mission-compass': 'mision_brujula',
    'act-06': 'registro_linea_tiempo',
    'mission-expectations': 'registro_mochila',
    'mission-next-step': 'registro_siguiente_paso',
    **{f'act-tip-{numero:02}': 'instrumento_mara' for numero in range(1, 15)},
    'act-tip-final': 'encuentro_resultado_elena',
}

FICHAS = (('first-steps', 'Tres pistas para comenzar el viaje', 'Observar, conversar y probar: tu primera brújula.'),
 ('ficha-mitos',
  'Ficha: Mitos y realidades del futuro profesional',
  'Cuatro creencias sobre tu futuro, vistas con otros ojos.'),
 ('rec-ponteencarrera',
  'Ponte en Carrera: compara carreras e instituciones',
  'Una guía para comparar caminos de formación.'),
 ('rec-unesco-stem',
  'Ciencia sin etiquetas',
  'El talento no tiene género. Explora la ciencia sin estereotipos.'))

NIVELES = ((1, 'Observador del horizonte'),
 (2, 'Recolector de pistas'),
 (3, 'Cartógrafo de posibilidades'),
 (4, 'Explorador de la ciudad'),
 (5, 'Autor de su rumbo'))

INSIGNIAS = (('I1',
  'La primera chispa',
  'Te animaste a comenzar sin necesitar todas las respuestas.',
  'Completa la introducción de tu viaje.',
  False),
 ('I2',
  'Coleccionista de pistas',
  'Reuniste señales sobre tus gustos, fortalezas y preguntas.',
  'Completa tres Misiones de Campo.',
  False),
 ('I3',
  'La llave de la ciudad',
  'Tus descubrimientos abrieron la puerta a nuevos escenarios.',
  'Completa todas las Misiones de Campo.',
  False),
 ('I4',
  'Una invitación abre caminos',
  'Invitaste a alguien a mirar el camino contigo.',
  'Invita a un compañero a tu Crew.',
  False),
 ('I5',
  'Nadie viaja solo',
  'Formaste un equipo para acompañar la exploración.',
  'Forma un Crew con un compañero que acepte tu invitación.',
  False),
 ('I6',
  'Una mesa para conversar',
  'Convertiste una conversación familiar en una nueva pista.',
  'Completen la primera conversación en familia.',
  False),
 ('I7',
  'Aquí para ayudar',
  'Usaste tus talentos para responder a un reto real.',
  'Resuelve tu primer caso.',
  False),
 ('I8',
  'Historias que inspiran',
  'Investigaste una profesión y compartiste lo aprendido.',
  'Publica una misión de investigación.',
  False),
 ('I9',
  'Una ciudad que sonríe',
  'Completaste todos los retos y construiste tu propia lectura de la ciudad.',
  'Resuelve todos los llamados de la Central de casos.',
  False),
 # DATO DE PRUEBA: descripción de I10 aprobada para F2.
 ('I10',
  'Luz sin fisuras',
  'Venciste al enemigo sin perder destellos en tu primera victoria',
  'Vence al enemigo sin perder destellos en tu primera victoria.',
  True))

# DATO DE PRUEBA: los 60 enunciados de §4.3.7, sin texto narrativo del front.
ENUNCIADOS_RIASEC = {'R': ('Reparar una bicicleta o un electrodoméstico.',
       'Armar muebles siguiendo un plano.',
       'Cultivar un huerto o cuidar plantas.',
       'Manejar maquinaria o herramientas eléctricas.',
       'Instalar el cableado eléctrico de una casa.',
       'Construir una maqueta o una estructura de madera.',
       'Cuidar animales en una granja o un refugio.',
       'Trabajar al aire libre, en el campo o en una obra.',
       'Pintar o reparar paredes y techos.',
       'Ensamblar las piezas de una computadora.'),
 'I': ('Hacer experimentos en un laboratorio.',
       'Investigar por qué ocurre un fenómeno natural.',
       'Resolver problemas de matemáticas o de lógica.',
       'Analizar datos para encontrar patrones.',
       'Leer sobre descubrimientos científicos.',
       'Estudiar cómo funciona el cuerpo humano.',
       'Observar el cielo y aprender sobre los planetas.',
       'Investigar las causas de una enfermedad.',
       'Programar una solución para un problema.',
       'Comparar información de distintas fuentes antes de concluir.'),
 'A': ('Dibujar o pintar.',
       'Escribir cuentos, poemas o guiones.',
       'Tocar un instrumento o componer música.',
       'Actuar en una obra de teatro.',
       'Diseñar un afiche o la portada de una revista.',
       'Tomar fotografías o grabar videos creativos.',
       'Decorar un espacio con un estilo propio.',
       'Bailar o crear una coreografía.',
       'Diseñar ropa o accesorios.',
       'Inventar personajes para una historia o un videojuego.'),
 'S': ('Enseñar algo a un niño o a un compañero.',
       'Escuchar y aconsejar a alguien que tiene un problema.',
       'Cuidar a personas enfermas o mayores.',
       'Organizar actividades para ayudar a la comunidad.',
       'Trabajar como voluntario en una campaña.',
       'Explicar un tema difícil a un grupo.',
       'Mediar en una discusión entre amigos.',
       'Acompañar a alguien en su primer día en un lugar nuevo.',
       'Orientar a otros estudiantes sobre sus estudios.',
       'Atender a personas que llegan buscando ayuda.'),
 'E': ('Vender un producto o una idea.',
       'Liderar un equipo para cumplir una meta.',
       'Iniciar un negocio propio.',
       'Convencer a otros en un debate.',
       'Organizar un evento y conseguir auspiciadores.',
       'Negociar un acuerdo o un precio.',
       'Representar a tu salón ante la dirección.',
       'Planificar cómo hacer crecer un emprendimiento.',
       'Dirigir una reunión y tomar decisiones.',
       'Promocionar una actividad en redes sociales.'),
 'C': ('Ordenar y clasificar documentos.',
       'Llevar las cuentas de ingresos y gastos.',
       'Registrar datos en una hoja de cálculo.',
       'Revisar un texto para corregir errores.',
       'Seguir un procedimiento paso a paso.',
       'Organizar un inventario de materiales.',
       'Preparar un horario o un calendario de actividades.',
       'Archivar información para encontrarla rápido.',
       'Verificar que una factura esté correcta.',
       'Mantener al día una base de datos.')}

OCUPACIONES = (('sound-technician', 'Técnico/a de sonido', '27-4014.00'),
 ('electrician', 'Electricista', '47-2111.00'),
 ('event-coordinator', 'Coordinador/a de eventos', '13-1121.00'),
 ('translator', 'Traductor/a', '27-3091.00'),
 ('community-manager', 'Community manager', '27-3031.00'),
 ('graphic-designer', 'Diseñador/a gráfico/a', '27-1024.00'),
 ('event-assistant', 'Asistente de eventos', '39-3031.00'),
 ('security-guard', 'Guardia de seguridad', '33-9032.00'),
 ('paramedic', 'Paramédico/a', '29-2043.00'),
 ('photographer', 'Fotógrafo/a', '27-4021.00'),
 ('lawyer', 'Abogado/a', '23-1011.00'),
 ('cook', 'Cocinero/a', '35-2014.00'),
 ('illustrator', 'Ilustrador/a', '27-1013.00'),
 ('firefighter', 'Bombero/a', '33-2011.00'),
 ('meteorologist', 'Meteorólogo/a', '19-2021.00'),
 ('municipal-police', 'Policía municipal', '33-3051.00'),
 ('medical-specialist', 'Médico/a especialista', '29-1216.00'),
 ('veterinarian', 'Veterinario/a', '29-1131.00'),
 ('biologist', 'Biólogo/a', '19-1029.04'),
 ('environmental-engineer', 'Ingeniero/a medioambiental', '17-2081.00'),
 ('civil-engineer', 'Ingeniero/a civil', '17-2051.00'),
 ('machinery-operator', 'Operador/a de maquinaria', '47-2073.00'),
 ('social-worker', 'Trabajador/a social', '21-1021.00'),
 ('psychologist', 'Psicólogo/a', '19-3033.00'),
 ('logistics-coordinator', 'Coordinador/a logístico/a', '13-1081.00'),
 ('journalist', 'Periodista', '27-3023.00'),
 ('teacher', 'Docente', '25-2031.00'),
 ('architect', 'Arquitecto/a', '17-1011.00'),
 ('geologist', 'Geólogo/a', '19-2042.00'),
 ('agricultural-engineer', 'Ingeniero/a agrónomo/a', '17-2021.00'),
 ('public-administrator', 'Gestor/a público/a', '11-3012.00'),
 ('sociologist', 'Sociólogo/a', '19-3041.00'),
 ('data-analyst', 'Analista de datos', '15-2051.00'),
 ('urban-planner', 'Urbanista', '19-3051.00'),
 ('documentary-filmmaker', 'Documentalista', '27-2012.00'),
 # DATO DE PRUEBA: nurse no existe en el catálogo del frontend.
 ('nurse', 'Enfermero/a', '29-1141.00'))

CARRERAS = (('environmental-engineering',
  'Ingeniería Ambiental',
  'Ingeniería y ambiente',
  ('environmental-engineer', 'agricultural-engineer', 'geologist', 'data-analyst')),
 ('journalism',
  'Periodismo',
  'Comunicación',
  ('journalist', 'documentary-filmmaker', 'photographer', 'community-manager', 'translator')),
 ('nursing', 'Enfermería', 'Salud', ('nurse', 'paramedic')),
 ('civil-engineering',
  'Ingeniería Civil',
  'Ingeniería e infraestructura',
  ('civil-engineer', 'architect', 'urban-planner', 'geologist', 'machinery-operator')),
 ('veterinary-medicine',
  'Medicina Veterinaria',
  'Salud y ciencias naturales',
  ('veterinarian', 'agricultural-engineer', 'biologist')),
 ('psychology',
  'Psicología',
  'Ciencias sociales y salud',
  ('psychologist', 'teacher', 'sociologist', 'social-worker')))


PATRON_RIASEC = 'RRIIAASSEECC'
DISTRIBUCION_ITEMS = tuple(
    (f'act-tip-{n:02}', 5 * (n - 1) + 1, 5 * n) if n <= 4 else
    (f'act-tip-{n:02}', 21 + 4 * (n - 5), 24 + 4 * (n - 5))
    for n in range(1, 15)
)

# Cada condición: evento, referencia legible, conteo, mínimo.
CONDICION_MISIONES = ('COMPLETA_ACTIVIDAD', None, 'EVENTOS', 1)
CONDICION_CAMINO = ('COMPLETA_BLOQUE', 'CAMINO', 'EVENTOS', 1)
REGLAS = (
    *[(f'R-{codigo}', 'ACTIVIDAD', codigo,
       (('COMPLETA_ACTIVIDAD', ACTIVIDADES_CAMINO[n - 1][0], 'EVENTOS', 1),), None)
      for n, (codigo, _, _) in enumerate(ACTIVIDADES_CAMINO) if n > 0],
    ('R-ciudad', 'BLOQUE', 'CIUDAD', (CONDICION_CAMINO,), None),
    *[(f'R-act-tip-{n:02}', 'ACTIVIDAD', f'act-tip-{n:02}',
       (('COMPLETA_ACTIVIDAD', f'act-tip-{n - 1:02}', 'EVENTOS', 1),), None)
      for n in range(2, 15)],
    ('R-act-tip-final', 'ACTIVIDAD', 'act-tip-final',
     (('COMPLETA_ACTIVIDAD', 'act-tip-14', 'EVENTOS', 1),), None),
    *[(f'R-{codigo}', 'FICHA', codigo,
       (('COMPLETA_ACTIVIDAD', 'mission-welcome' if codigo == 'first-steps' else 'enc-mitos', 'EVENTOS', 1),), None)
      for codigo, _, _ in FICHAS],
    ('R-I1', 'INSIGNIA', 'I1', (('COMPLETA_ACTIVIDAD', 'mission-welcome', 'EVENTOS', 1),), None),
    ('R-I2', 'INSIGNIA', 'I2', (CONDICION_MISIONES,), 3),
    ('R-I3', 'INSIGNIA', 'I3', (CONDICION_CAMINO,), None),
    *[(f'R-I{n}', 'INSIGNIA', f'I{n}', ((evento, None, 'EVENTOS', 1),), None)
      for n, evento in ((4, 'INVITA_A_CREW'), (5, 'FORMA_CREW'), (6, 'COMPLETA_CONVERSACION'),
                        (7, 'SUPERA_CASO'), (8, 'PUBLICA_ENTREVISTA'), (10, 'VENCE_DESAFIO_INTACTO'))],
    ('R-I9', 'INSIGNIA', 'I9', (('SUPERA_CASO', None, 'REFERENCIAS_DISTINTAS', 6),), None),
    ('R-FAM-ESTUDIANTE', 'CONVERSACIONES', None, (CONDICION_CAMINO,), None),
    ('R-FAM-APODERADO', 'CONVERSACIONES', None, (('ESCRIBE_CARTA', None, 'EVENTOS', 1),), None),
    ('R-NIV-2', 'NIVEL', 2, (CONDICION_MISIONES,), 3),
    ('R-NIV-3', 'NIVEL', 3, (CONDICION_MISIONES, CONDICION_CAMINO), 3),
    ('R-NIV-4-CASO', 'NIVEL', 4,
     (CONDICION_MISIONES, CONDICION_CAMINO, ('SUPERA_CASO', None, 'EVENTOS', 1)), 3),
    ('R-NIV-4-INV', 'NIVEL', 4,
     (CONDICION_MISIONES, CONDICION_CAMINO, ('PUBLICA_ENTREVISTA', None, 'EVENTOS', 1)), 3),
    ('R-NIV-5', 'NIVEL', 5,
     (CONDICION_MISIONES, CONDICION_CAMINO, ('SUPERA_CASO', None, 'REFERENCIAS_DISTINTAS', 6),
      ('PUBLICA_ENTREVISTA', None, 'EVENTOS', 1), ('COMPLETA_CONVERSACION', None, 'EVENTOS', 1)), 3),
)


def _leer_catalogo_seleccionado():
    archivo = {fila.codigo_onet: fila for fila in leer_ocupaciones(RUTA_OCUPACIONES)}
    for codigo, _, codigo_onet in OCUPACIONES:
        if codigo_onet not in archivo:
            raise ValueError(f'Falta la ocupación O*NET {codigo_onet}, requerida por {codigo}')
    return {codigo: archivo[codigo_onet] for codigo, _, codigo_onet in OCUPACIONES}


def _cargar_estructura(sesion, *, camino=ACTIVIDADES_CAMINO, ciudad=ACTIVIDADES_CIUDAD,
                       contenidos=CONTENIDOS_ACTIVIDADES):
    cuentas = {c: modelos.Cuenta(codigo=c, nombre=n, rol=modelos.Rol(r)) for c, n, r in CUENTAS}
    bloques = {c: modelos.Bloque(codigo=c, numero=num, nombre=n, espacio=modelos.Espacio(e),
                                audiencia=modelos.Audiencia(a)) for c, num, n, e, a in BLOQUES}
    fichas = {c: modelos.Ficha(codigo=c, titulo=t, contenido=resumen) for c, t, resumen in FICHAS}
    insignias = {c: modelos.Insignia(codigo=c, nombre=n, descripcion=d, requisito=r, es_oculta=o,
                                   audiencia=modelos.Audiencia.ESTUDIANTE) for c, n, d, r, o in INSIGNIAS}
    niveles = {num: modelos.Nivel(numero=num, titulo=t) for num, t in NIVELES}
    sesion.add_all([*cuentas.values(), *bloques.values(), *fichas.values(), *insignias.values(), *niveles.values()])
    sesion.flush()
    sesion.add(modelos.VinculoFamiliar(codigo='VIN-ANA', estudiante_id=cuentas['est-ana'].id,
                                      apoderado_id=cuentas['apo-rosa'].id))
    actividades = {}
    for bloque, filas in (('CAMINO', camino), ('CIUDAD', ciudad)):
        actividades.update({c: modelos.Actividad(codigo=c, titulo=t, tipo=modelos.TipoActividad(tipo),
                                                contenido=contenidos[c],
                                                orden=orden, bloque_id=bloques[bloque].id)
                            for orden, (c, t, tipo) in enumerate(filas, start=1)})
    sesion.add_all(actividades.values())
    sesion.flush()
    return {'BLOQUE': bloques, 'ACTIVIDAD': actividades, 'FICHA': fichas, 'INSIGNIA': insignias, 'NIVEL': niveles}


def _cargar_riasec(sesion, actividades):
    instrumento = modelos.Instrumento(codigo='TEST-RIASEC', nombre='Test de intereses (RIASEC)',
        descripcion='Versión de prueba para la iteración 1.', tipo_resultado=modelos.TipoResultado.COINCIDENCIAS)
    escala = modelos.EscalaRespuesta(codigo='ESC-LIKERT5', nombre='Preferencia en cinco opciones')
    sesion.add_all([instrumento, escala])
    sesion.flush()
    sesion.add_all(modelos.OpcionEscala(escala_id=escala.id, orden=n, etiqueta=etiqueta,
                                      puntaje=transformar_opcion_onet(n))
                   for n, etiqueta in enumerate(('Me disgusta mucho', 'Me disgusta', 'No estoy seguro',
                                                  'Me gusta', 'Me gusta mucho'), start=1))
    dimensiones = {c: modelos.Dimension(codigo=c, nombre=n, instrumento_id=instrumento.id, orden=orden,
                                        descripcion=f'Dimensión de demostración: {n}.')
                   for orden, (c, n) in enumerate(DIMENSIONES_RIASEC, start=1)}
    aplicacion = modelos.Aplicacion(codigo='APL-RIASEC', nombre='Intereses', instrumento_id=instrumento.id,
                                    momento=modelos.MomentoAplicacion.UNICA)
    sesion.add_all([*dimensiones.values(), aplicacion])
    sesion.flush()
    items = {}
    for numero in range(1, 61):
        dimension = PATRON_RIASEC[(numero - 1) % 12]
        indice = 2 * ((numero - 1) // 12) + ((numero - 1) % 12) % 2
        items[numero] = modelos.ItemInstrumento(codigo=f'RIASEC-{numero:02}', numero=numero,
            enunciado=ENUNCIADOS_RIASEC[dimension][indice], instrumento_id=instrumento.id,
            dimension_id=dimensiones[dimension].id, escala_id=escala.id, inverso=False)
    sesion.add_all(items.values())
    sesion.flush()
    sesion.add_all(modelos.AplicacionActividad(aplicacion_id=aplicacion.id, actividad_id=actividades[c].id)
                   for c, _, _ in DISTRIBUCION_ITEMS)
    sesion.add_all(modelos.ActividadItem(actividad_id=actividades[c].id, item_id=items[numero].id, orden=orden)
                   for c, inicio, fin in DISTRIBUCION_ITEMS
                   for orden, numero in enumerate(range(inicio, fin + 1), start=1))
    return dimensiones


def _cargar_catalogo(sesion, archivo, dimensiones):
    ocupaciones = {c: modelos.Ocupacion(codigo=c, titulo=t, codigo_onet=onet) for c, t, onet in OCUPACIONES}
    familias = {c: modelos.FamiliaCarrera(codigo=f'family-{c}', nombre=f) for c, _, f, _ in CARRERAS}
    sesion.add_all([*ocupaciones.values(), *familias.values()])
    sesion.flush()
    carreras = {c: modelos.Carrera(codigo=c, nombre=n, familia_id=familias[c].id) for c, n, _, _ in CARRERAS}
    sesion.add_all(carreras.values())
    sesion.flush()
    sesion.execute(insert(modelos.PuntajeOcupacion), [
        {'ocupacion_id': ocupaciones[c].id, 'dimension_id': dimensiones[d].id, 'valor': fila.valores[n]}
        for c, fila in archivo.items() for n, (d, _) in enumerate(DIMENSIONES_RIASEC)
    ])
    sesion.execute(insert(modelos.CarreraOcupacion), [
        {'carrera_id': carreras[c].id, 'ocupacion_id': ocupaciones[o].id}
        for c, _, _, relaciones in CARRERAS for o in relaciones
    ])


def _cargar_reglas(sesion, objetivos, definiciones=REGLAS):
    referencias = {'COMPLETA_ACTIVIDAD': objetivos['ACTIVIDAD'], 'COMPLETA_BLOQUE': objetivos['BLOQUE']}
    reglas = []
    for codigo, tipo, objetivo, condiciones, minimo in definiciones:
        regla = modelos.ReglaDesbloqueo(codigo=codigo, nombre=f'Desbloquear {objetivo or "conversaciones"}',
            tipo_objetivo=modelos.TipoObjetivo(tipo),
            id_objetivo=None if objetivo is None else objetivos[tipo][objetivo].id,
            evaluador_especial='misiones_camino_sin_inicio' if minimo is not None else None,
            parametro_evaluador=minimo)
        regla.condiciones = [modelos.CondicionDesbloqueo(tipo_evento=modelos.TipoEventoUso(evento),
            id_referencia=None if referencia is None else referencias[evento][referencia].id,
            tipo_conteo=modelos.TipoConteo(conteo), cantidad_minima=cantidad)
            for evento, referencia, conteo, cantidad in condiciones]
        reglas.append(regla)
    sesion.add_all(reglas)


def cargar(sesion: Session) -> None:
    archivo = _leer_catalogo_seleccionado()
    objetivos = _cargar_estructura(sesion)
    dimensiones = _cargar_riasec(sesion, objetivos['ACTIVIDAD'])
    _cargar_catalogo(sesion, archivo, dimensiones)
    _cargar_reglas(sesion, objetivos)
    sesion.flush()
    validar_distribucion_items(sesion)
