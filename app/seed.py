"""Datos de la sección 7; no evalúa reglas ni crea estado de usuario."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import Base, VERSION_ESQUEMA
from app.models import (
    Actividad, Audiencia, Bloque, Carrera, CondicionDesbloqueo, Conversacion,
    Cuenta, Espacio, EsquemaVersion, FamiliaCarrera, Ficha, Insignia, Nivel, PreguntaDiario,
    ReglaDesbloqueo, Rol, Testimonio, TipoActividad, TipoConteo,
    TipoEventoUso, TipoObjetivo, VinculoFamiliar,
)


def cargar_semilla_si_vacia(sesion: Session) -> None:
    if any(
        sesion.execute(select(tabla).limit(1)).first() is not None
        for tabla in Base.metadata.sorted_tables
    ):
        return
    cargar_semilla(sesion)


def cargar_semilla(sesion: Session) -> None:
    """Carga una base vacía. La transacción pertenece al llamador."""
    cuentas = {
        codigo: Cuenta(codigo=codigo, nombre=nombre, rol=rol)
        for codigo, nombre, rol in (
            ("est-ana", "Ana", Rol.ESTUDIANTE),
            ("est-luis", "Luis", Rol.ESTUDIANTE),
            ("apo-rosa", "Rosa", Rol.APODERADO),
        )
    }
    sesion.add_all(cuentas.values())
    sesion.flush()
    sesion.add(VinculoFamiliar(
        codigo="VIN-ANA", estudiante_id=cuentas["est-ana"].id,
        apoderado_id=cuentas["apo-rosa"].id,
    ))

    bloques = {}
    for codigo, nombre in (
        ("B0", "Inicio"), ("B1", "Mi historia"),
        ("B3", "Exploro el mundo profesional"), ("B5", "Mi decisión"),
        ("C1", "Misiones de Helena"), ("C2", "Central de Casos"),
        ("C3", "Comprobaciones"), ("C4", "Investigaciones"),
        ("P1", "Ruta del apoderado"),
    ):
        bloques[codigo] = Bloque(
            codigo=codigo, numero=int(codigo[1:]), nombre=nombre,
            espacio=Espacio.CIUDAD if codigo.startswith("C") else Espacio.MISIONES_CAMPO,
            audiencia=Audiencia.APODERADO if codigo == "P1" else Audiencia.ESTUDIANTE,
        )
    sesion.add_all(bloques.values())
    sesion.flush()

    actividades = {}
    for bloque, filas in {
        "B0": [("ACT-01", "Bienvenida", "CUESTIONARIO"),
               ("ACT-02", "Mis expectativas", "REGISTRO"),
               ("ACT-03", "Mi diario", "INFORMATIVA")],
        "B1": [("ACT-04", "Mi historia personal", "REGISTRO"),
               ("ACT-05", "Mis aspiraciones", "REGISTRO"),
               ("ACT-06", "Mi línea de tiempo", "REGISTRO")],
        "B3": [("ACT-12", "Exploro profesiones", "INFORMATIVA"),
               ("ACT-13", "Mercado laboral y oferta educativa", "INFORMATIVA")],
        "B5": [("ACT-17", "Mi perfil y carreras afines", "REGISTRO"),
               ("ACT-18", "Mi proyecto vocacional", "REGISTRO"),
               ("ACT-19", "Evaluación final", "CUESTIONARIO")],
        "C1": [("HEL-01", "Intereses I", "CUESTIONARIO"),
               ("HEL-02", "Intereses II", "CUESTIONARIO"),
               ("HEL-03", "Habilidades sociales", "CUESTIONARIO")],
        "C2": [("CASO-01", "El hospital", "CASO"), ("CASO-02", "La obra", "CASO")],
        "C3": [("COMP-13", "Comprobación de mercado laboral", "INFORMATIVA")],
        "C4": [("INV-01", "Mi investigación vocacional", "REGISTRO")],
        "P1": [("ACT-P01", "Mi rol en el proceso", "INFORMATIVA"),
               ("ACT-P02", "Me fortalezco para acompañarte", "INFORMATIVA")],
    }.items():
        for orden, (codigo, titulo, tipo) in enumerate(filas, start=1):
            actividades[codigo] = Actividad(
                codigo=codigo, titulo=titulo, tipo=TipoActividad(tipo), orden=orden,
                bloque_id=bloques[bloque].id, puntaje_minimo=70.0 if tipo == "CASO" else None,
            )

    fichas = {
        codigo: Ficha(codigo=codigo, titulo=titulo, contenido=f"Contenido de demo: {titulo}.")
        for codigo, titulo in (
            ("FIC-PROFESIONES", "Profesiones y ocupaciones"),
            ("FIC-MERCADO", "Mercado laboral en Lima"),
            ("FIC-INSTITUCIONES", "Oferta educativa"),
        )
    }
    testimonios = {
        codigo: Testimonio(
            codigo=codigo, titulo=titulo, descripcion=f"Descripción de demo: {titulo}.",
            enlace=f"https://example.com/{codigo.lower()}",
        )
        for codigo, titulo in (
            ("TES-HOSPITAL", "Testimonio de una enfermera"),
            ("TES-OBRA", "Testimonio de un maestro de obra"),
        )
    }
    preguntas = {
        codigo: PreguntaDiario(codigo=codigo, pregunta=pregunta)
        for codigo, pregunta in (
            ("PD-HISTORIA", "¿Qué descubriste de tu historia que no habías notado?"),
            ("PD-ASPIRACIONES", "¿Tus aspiraciones son tuyas o de tu entorno?"),
            ("PD-CONV-01", "¿Qué aprendiste de la conversación con tu familia?"),
        )
    }
    conversaciones = {
        codigo: Conversacion(codigo=codigo, titulo=titulo, tema=titulo)
        for codigo, titulo in (
            ("CONV-01", "Lo que esperamos del futuro"),
            ("CONV-02", "Mis fortalezas vistas por mi familia"),
        )
    }
    insignias = {}
    for codigo, nombre, requisito in (
        ("INS-PRIMER-PASO", "Primer paso", "Completa el bloque de inicio"),
        ("INS-CIUDAD", "Bienvenido a la ciudad", "Llega a la ciudad"),
        ("INS-PRIMER-CASO", "Primer caso resuelto", "Supera un caso de la Central de Casos"),
        ("INS-INVESTIGADOR", "Investigador", "Publica tu primera entrevista"),
        ("INS-EXPLORADOR", "Explorador diverso", "Revisa carreras de al menos 3 familias distintas"),
        ("INS-CONOZCO-MI-ROL", "Conozco mi rol", "Completa tu ruta"),
        ("LOG-PLUMA", "Pluma libre", "primera entrada libre"),
        ("LOG-CONSTANCIA", "Constancia", "check-in en 3 días distintos"),
        ("LOG-PENSADOR", "Pensador profundo", "3 respuestas reflexivas"),
        ("LOG-INCANSABLE", "Incansable", "8 actividades distintas completadas"),
    ):
        insignias[codigo] = Insignia(
            codigo=codigo, nombre=nombre, descripcion=f"Logro de demo: {nombre}.",
            requisito=requisito, es_oculta=codigo.startswith("LOG-"),
            audiencia=Audiencia.APODERADO if codigo == "INS-CONOZCO-MI-ROL" else Audiencia.ESTUDIANTE,
        )
    niveles = {
        f"N{numero}": Nivel(numero=numero, titulo=titulo)
        for numero, titulo in enumerate((
            "Viajero novato", "Explorador de caminos", "Habitante de la ciudad",
            "Mago del autoconocimiento", "Arquitecto de su futuro",
        ), start=1)
    }
    familias = {
        codigo: FamiliaCarrera(codigo=codigo, nombre=nombre)
        for codigo, nombre in (
            ("FAM-SALUD", "Salud"), ("FAM-INGENIERIA", "Ingeniería"),
            ("FAM-ARTE", "Arte"), ("FAM-NEGOCIOS", "Negocios"),
        )
    }
    for catalogo in (actividades, fichas, testimonios, preguntas, conversaciones,
                     insignias, niveles, familias):
        sesion.add_all(catalogo.values())
    sesion.flush()
    for codigo, nombre, familia in (
        ("CAR-ENF", "Enfermería", "FAM-SALUD"), ("CAR-MED", "Medicina", "FAM-SALUD"),
        ("CAR-CIV", "Ingeniería civil", "FAM-INGENIERIA"),
        ("CAR-DIS", "Diseño gráfico", "FAM-ARTE"),
        ("CAR-ADM", "Administración", "FAM-NEGOCIOS"),
    ):
        sesion.add(Carrera(codigo=codigo, nombre=nombre, familia_id=familias[familia].id))

    objetivos = {
        TipoObjetivo.ACTIVIDAD: actividades, TipoObjetivo.BLOQUE: bloques,
        TipoObjetivo.FICHA: fichas, TipoObjetivo.TESTIMONIO: testimonios,
        TipoObjetivo.PREGUNTA_DIARIO: preguntas, TipoObjetivo.INSIGNIA: insignias,
        TipoObjetivo.NIVEL: niveles,
    }
    referencias = {
        TipoEventoUso.COMPLETA_ACTIVIDAD: actividades,
        TipoEventoUso.COMPLETA_BLOQUE: bloques,
        TipoEventoUso.SUPERA_CASO: actividades,
        TipoEventoUso.COMPLETA_CONVERSACION: conversaciones,
    }

    def condicion(evento, referencia=None, conteo="EVENTOS", minimo=1):
        return (evento, referencia, conteo, minimo)

    def agregar_regla(codigo, tipo, objetivo, condiciones, evaluador=None):
        tipo = TipoObjetivo(tipo)
        regla = ReglaDesbloqueo(
            codigo=codigo, nombre=f"Desbloquear {objetivo}", tipo_objetivo=tipo,
            id_objetivo=None if tipo == TipoObjetivo.CONVERSACIONES else objetivos[tipo][objetivo].id,
            evaluador_especial=evaluador,
            parametro_evaluador=3 if evaluador == "carreras_de_3_familias" else None,
        )
        for evento, referencia, conteo, minimo in condiciones:
            evento = TipoEventoUso(evento)
            regla.condiciones.append(CondicionDesbloqueo(
                tipo_evento=evento,
                id_referencia=None if referencia is None else referencias[evento][referencia].id,
                tipo_conteo=TipoConteo(conteo), cantidad_minima=minimo,
            ))
        sesion.add(regla)

    for objetivo, anterior in (
        ("ACT-02", "ACT-01"), ("ACT-03", "ACT-02"), ("ACT-04", "ACT-03"),
        ("ACT-05", "ACT-04"), ("ACT-06", "ACT-05"), ("ACT-12", "ACT-06"),
        ("ACT-13", "ACT-12"), ("ACT-17", "ACT-13"), ("ACT-18", "ACT-17"),
        ("ACT-19", "ACT-18"), ("ACT-P02", "ACT-P01"),
        ("HEL-02", "HEL-01"), ("CASO-02", "CASO-01"),
    ):
        condiciones = [condicion("COMPLETA_ACTIVIDAD", anterior)]
        if objetivo == "ACT-17":
            condiciones.append(condicion("COMPLETA_BLOQUE", "C1"))
        agregar_regla(f"R-{objetivo}", "ACTIVIDAD", objetivo, condiciones)
    for objetivo in ("C1", "C2", "C3", "C4"):
        agregar_regla(f"R-CIUDAD-{objetivo}", "BLOQUE", objetivo,
                      [condicion("COMPLETA_ACTIVIDAD", "ACT-13")])
    agregar_regla("R-INV-01", "ACTIVIDAD", "INV-01", [condicion("SUPERA_CASO")])

    for objetivo, tipo, evento, referencia in (
        ("FIC-PROFESIONES", "FICHA", "COMPLETA_ACTIVIDAD", "ACT-12"),
        ("FIC-MERCADO", "FICHA", "COMPLETA_ACTIVIDAD", "ACT-13"),
        ("FIC-INSTITUCIONES", "FICHA", "COMPLETA_ACTIVIDAD", "COMP-13"),
        ("TES-HOSPITAL", "TESTIMONIO", "SUPERA_CASO", "CASO-01"),
        ("TES-OBRA", "TESTIMONIO", "SUPERA_CASO", "CASO-02"),
        ("PD-HISTORIA", "PREGUNTA_DIARIO", "COMPLETA_ACTIVIDAD", "ACT-04"),
        ("PD-ASPIRACIONES", "PREGUNTA_DIARIO", "COMPLETA_ACTIVIDAD", "ACT-05"),
        ("PD-CONV-01", "PREGUNTA_DIARIO", "COMPLETA_CONVERSACION", "CONV-01"),
    ):
        agregar_regla(f"R-{objetivo}", tipo, objetivo, [condicion(evento, referencia)])
    for rol, actividad in (("ESTUDIANTE", "ACT-13"), ("APODERADO", "ACT-P02")):
        agregar_regla(f"R-FAM-{rol}", "CONVERSACIONES", "-", [
            condicion("ESCRIBE_CARTA"), condicion("COMPLETA_ACTIVIDAD", actividad),
        ])

    for objetivo, evento, referencia, conteo, minimo in (
        ("INS-PRIMER-PASO", "COMPLETA_BLOQUE", "B0", "EVENTOS", 1),
        ("INS-CIUDAD", "COMPLETA_ACTIVIDAD", "ACT-13", "EVENTOS", 1),
        ("INS-PRIMER-CASO", "SUPERA_CASO", None, "EVENTOS", 1),
        ("INS-INVESTIGADOR", "PUBLICA_ENTREVISTA", None, "EVENTOS", 1),
        ("INS-EXPLORADOR", "VISTA_CARRERA", None, "EVENTOS", 1),
        ("INS-CONOZCO-MI-ROL", "COMPLETA_BLOQUE", "P1", "EVENTOS", 1),
        ("LOG-PLUMA", "ESCRIBE_ENTRADA_LIBRE", None, "EVENTOS", 1),
        ("LOG-CONSTANCIA", "REGISTRA_CHECK_IN", None, "DIAS_DISTINTOS", 3),
        ("LOG-PENSADOR", "RESPUESTA_REFLEXIVA", None, "EVENTOS", 3),
        ("LOG-INCANSABLE", "COMPLETA_ACTIVIDAD", None, "REFERENCIAS_DISTINTAS", 8),
    ):
        agregar_regla(f"R-{objetivo}", "INSIGNIA", objetivo,
                      [condicion(evento, referencia, conteo, minimo)],
                      "carreras_de_3_familias" if objetivo == "INS-EXPLORADOR" else None)

    condiciones_nivel = [condicion("COMPLETA_BLOQUE", "B0")]
    agregar_regla("R-NIV-2", "NIVEL", "N2", condiciones_nivel)
    condiciones_nivel = condiciones_nivel + [condicion("COMPLETA_ACTIVIDAD", "ACT-13")]
    agregar_regla("R-NIV-3", "NIVEL", "N3", condiciones_nivel)
    condiciones_nivel = condiciones_nivel + [condicion("COMPLETA_BLOQUE", "C1"), condicion("SUPERA_CASO")]
    agregar_regla("R-NIV-4", "NIVEL", "N4", condiciones_nivel)
    condiciones_nivel = condiciones_nivel + [condicion("COMPLETA_ACTIVIDAD", "ACT-18")]
    agregar_regla("R-NIV-5", "NIVEL", "N5", condiciones_nivel)
    sesion.flush()
    # Se agrega después del catálogo original para conservar sus referencias internas.
    from app.semilla_instrumentos import cargar_definiciones_instrumentos, cargar_catalogo_ocupaciones

    cargar_definiciones_instrumentos(sesion)
    cargar_catalogo_ocupaciones(sesion)
    from app.semilla_registro import cargar_definiciones_registro

    cargar_definiciones_registro(sesion)
    sesion.add(EsquemaVersion(id=1, version=VERSION_ESQUEMA))
    sesion.flush()
