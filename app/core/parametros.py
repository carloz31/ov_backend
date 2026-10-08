"""Parámetros de la demo; fuentes: especificaciones de instrumentos y registro.

Los umbrales son los criterios de §5.4, no una atribución bibliográfica
adicional. Las opciones persistidas siguen siendo la fuente de sus puntajes.
"""

# §5.4: ajuste inclusivo y cantidad máxima de coincidencias guardadas.
UMBRAL_BEST_FIT = 0.729
UMBRAL_GREAT_FIT = 0.608
CORRELACION_MINIMA = 0
LIMITE_COINCIDENCIAS = 10

# §5.6: longitud del código de interés y corte para detectar empates.
LONGITUD_CODIGO_INTERES = 3

# §5.3 y §6.2: representación; Pearson se persiste sin redondear.
FACTOR_PORCENTAJE = 100
DECIMALES_PORCENTAJE = 2
DECIMALES_CORRELACION = 6

# §4.2: opción O*NET 1..5 -> puntaje 0..4, aplicada solo al sembrar.
OPCION_ONET_MINIMA = 1
OPCION_ONET_MAXIMA = 5
PUNTAJE_ONET_MINIMO = 0

# Registro §3 y §6: valores iniciales; el adaptador leerá el timeout del entorno.
VERSION_PROMPT_REGISTRO = "v2"
MAXIMO_SEGUIMIENTOS_POR_ITEM = 2
TIEMPO_MAXIMO_EVALUACION_SEGUNDOS = 8
MODELO_GEMINI_REGISTRO = "gemini-3.1-flash-lite"
TEMPERATURA_REGISTRO = 0.2
PAUSA_CASOS_GEMINI_SEGUNDOS = 5


def transformar_opcion_onet(orden):
    return orden - OPCION_ONET_MINIMA + PUNTAJE_ONET_MINIMO


DIMENSIONES_RIASEC = (
    ("R", "Realista"), ("I", "Investigativa"), ("A", "Artística"),
    ("S", "Social"), ("E", "Emprendedora"), ("C", "Convencional"),
)
