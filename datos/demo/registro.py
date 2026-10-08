"""Definiciones de registro de §5; no crea respuestas, evaluaciones ni reglas."""

from sqlalchemy.orm import Session

from app.models import (
    Actividad, ActividadItemRegistro, Audiencia, Bloque, CriterioCompletitud, Espacio,
    ItemRegistro, TipoActividad,
)


def cargar_definiciones_registro(sesion: Session) -> None:
    bloque = Bloque(codigo="REG", numero=0, nombre="Laboratorio de registros (solo demo)",
                    espacio=Espacio.MISIONES_CAMPO, audiencia=Audiencia.ESTUDIANTE)
    sesion.add(bloque)
    sesion.flush()
    actividad = Actividad(codigo="REG-ACT08", titulo="Mi plan para fortalecer una habilidad",
                          contenido="reg_act08",
                          tipo=TipoActividad.REGISTRO, orden=1, bloque_id=bloque.id)
    sesion.add(actividad)
    sesion.flush()
    definiciones = (
        (
            "REG-HAB-1", "Habilidad a fortalecer",
            "¿Qué habilidad social quieres fortalecer y por qué?", 40,
            "Cuéntame un poco más: ¿qué habilidad elegiste y en qué momento de tu vida sientes que te haría falta?",
            (
                "Nombra una habilidad social concreta, por ejemplo asertividad, empatía, comunicación o trabajo en equipo.",
                "La relaciona con una situación de su propia vida en la que la necesita o le cuesta.",
            ),
        ),
        (
            "REG-HAB-2", "Mi acción", "¿Qué harás para practicarla?", 40,
            "Cuéntame un poco más: ¿qué harás exactamente y en qué momento?",
            (
                'Describe una acción que puede realizar, no solo una intención general como "esforzarme" o "mejorar".',
                "Indica dónde, cuándo o con quién la realizará.",
            ),
        ),
        (
            "REG-HAB-3", "Cómo sabré que mejoro", "¿Cómo sabrás que estás mejorando?", 30,
            "Cuéntame un poco más: ¿qué notarías tú que cambia cuando mejores?",
            (
                'Describe algo que él mismo puede observar o notar, no solo un sentimiento general como "me sentiré mejor".',
                "Se relaciona con la habilidad y la acción que eligió.",
            ),
        ),
    )
    items = [ItemRegistro(codigo=codigo, nombre=nombre, consigna=consigna,
                          min_caracteres=minimo, obligatorio=True, repregunta_generica=repregunta)
             for codigo, nombre, consigna, minimo, repregunta, _ in definiciones]
    sesion.add_all(items)
    sesion.flush()
    sesion.add_all([
        ActividadItemRegistro(actividad_id=actividad.id, item_registro_id=item.id, orden=orden)
        for orden, item in enumerate(items, start=1)
    ])
    sesion.add_all([
        CriterioCompletitud(item_registro_id=item.id, codigo=f"C{orden}", descripcion=descripcion, orden=orden)
        for item, definicion in zip(items, definiciones, strict=True)
        for orden, descripcion in enumerate(definicion[-1], start=1)
    ])
    sesion.flush()
