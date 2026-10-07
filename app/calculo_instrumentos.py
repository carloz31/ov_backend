"""Cálculos puros de instrumentos: sin base de datos, archivos ni routers."""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from fractions import Fraction
from math import isfinite
import statistics
from typing import Literal

from app.configuracion_metodos import (
    CORRELACION_MINIMA, DECIMALES_PORCENTAJE, FACTOR_PORCENTAJE,
    LIMITE_COINCIDENCIAS, LONGITUD_CODIGO_INTERES, UMBRAL_BEST_FIT, UMBRAL_GREAT_FIT,
)


AjusteCalculado = Literal["BEST_FIT", "GREAT_FIT", "GOOD_FIT"]


def orden_canonico_riasec():
    """Compatibilidad de llamadas puras; las peticiones pasan el orden de la BD."""
    from app.semilla_instrumentos import DIMENSIONES_RIASEC
    return tuple(codigo for codigo, _ in DIMENSIONES_RIASEC)


@dataclass(frozen=True)
class ItemParaCalculo:
    puntaje: float
    minimo: float
    maximo: float
    inverso: bool = False


@dataclass(frozen=True)
class DimensionCalculada:
    codigo: str
    puntaje: float
    puntaje_maximo: float
    porcentaje: float


@dataclass(frozen=True)
class PerfilOcupacion:
    codigo_onet: str
    titulo: str
    puntajes: tuple[float, ...]  # Mismo orden de dimensiones que el estudiante.


@dataclass(frozen=True)
class CoincidenciaCalculada:
    posicion: int
    codigo_onet: str
    titulo: str
    correlacion: float
    ajuste: AjusteCalculado


@dataclass(frozen=True)
class CoincidenciasCalculadas:
    perfil_plano: bool
    coincidencias: tuple[CoincidenciaCalculada, ...]


@dataclass(frozen=True)
class CodigoInteresCalculado:
    codigo: str
    hay_empate: bool


def calcular_puntaje_item(puntaje: float, minimo: float, maximo: float, inverso: bool = False) -> float:
    """Recibe el puntaje de la opción, no su orden en la escala."""
    if not all(isfinite(valor) for valor in (puntaje, minimo, maximo)):
        raise ValueError("El puntaje y los límites de la escala deben ser finitos")
    if minimo > maximo or not minimo <= puntaje <= maximo:
        raise ValueError("El puntaje debe pertenecer a los límites de la escala")
    return maximo + minimo - puntaje if inverso else puntaje


def calcular_porcentaje(puntaje: float, puntaje_maximo: float) -> float:
    if not isfinite(puntaje) or not isfinite(puntaje_maximo) or puntaje_maximo <= 0:
        raise ValueError("El puntaje debe ser finito y el máximo debe ser finito y positivo")
    if not 0 <= puntaje <= puntaje_maximo:
        raise ValueError("El puntaje debe estar entre cero y el máximo")
    return round(FACTOR_PORCENTAJE * puntaje / puntaje_maximo, DECIMALES_PORCENTAJE)


def calcular_dimension(codigo: str, items: Iterable[ItemParaCalculo]) -> DimensionCalculada:
    puntaje = 0.0
    puntaje_maximo = 0.0
    for item in items:
        puntaje += calcular_puntaje_item(item.puntaje, item.minimo, item.maximo, item.inverso)
        puntaje_maximo += item.maximo
    return DimensionCalculada(codigo, puntaje, puntaje_maximo, calcular_porcentaje(puntaje, puntaje_maximo))


def calcular_dimensiones_destacadas(dimensiones: Sequence[DimensionCalculada]) -> tuple[str, ...]:
    """Conserva el orden recibido y compara proporciones sin redondearlas."""
    proporciones = []
    for dimension in dimensiones:
        calcular_porcentaje(dimension.puntaje, dimension.puntaje_maximo)  # Valida los límites.
        proporciones.append(Fraction(dimension.puntaje) / Fraction(dimension.puntaje_maximo))
    if not proporciones:
        return ()
    mayor = max(proporciones)
    return tuple(d.codigo for d, proporcion in zip(dimensiones, proporciones, strict=True) if proporcion == mayor)


def _validar_vector(vector: Sequence[float], cantidad_dimensiones: int | None = None) -> None:
    cantidad = len(orden_canonico_riasec()) if cantidad_dimensiones is None else cantidad_dimensiones
    if len(vector) != cantidad or not all(isfinite(valor) for valor in vector):
        raise ValueError("El vector RIASEC debe tener seis puntajes finitos en el orden R, I, A, S, E, C")


def calcular_pearson(vector_estudiante: Sequence[float], vector_ocupacion: Sequence[float],
                     cantidad_dimensiones: int | None = None) -> float:
    _validar_vector(vector_estudiante, cantidad_dimensiones)
    _validar_vector(vector_ocupacion, cantidad_dimensiones)
    try:
        return statistics.correlation(vector_estudiante, vector_ocupacion)
    except statistics.StatisticsError as error:
        raise ValueError("La correlación de Pearson no está definida para un vector constante") from error


def clasificar_ajuste(correlacion: float) -> AjusteCalculado | None:
    """Las correlaciones negativas no tienen ajuste y se descartan."""
    if not isfinite(correlacion) or not -1 <= correlacion <= 1:
        raise ValueError("La correlación debe ser finita y estar entre -1 y 1")
    if correlacion < CORRELACION_MINIMA:
        return None
    if correlacion >= UMBRAL_BEST_FIT:
        return "BEST_FIT"
    if correlacion >= UMBRAL_GREAT_FIT:
        return "GREAT_FIT"
    return "GOOD_FIT"


def calcular_coincidencias(
    vector_estudiante: Sequence[float], ocupaciones: Iterable[PerfilOcupacion],
    cantidad_dimensiones: int | None = None,
) -> CoincidenciasCalculadas:
    _validar_vector(vector_estudiante, cantidad_dimensiones)
    if len(set(vector_estudiante)) == 1:
        return CoincidenciasCalculadas(perfil_plano=True, coincidencias=())
    candidatas = []
    for ocupacion in ocupaciones:
        try:
            correlacion = calcular_pearson(vector_estudiante, ocupacion.puntajes, cantidad_dimensiones)
        except ValueError as error:
            raise ValueError(f"No se puede calcular Pearson para la ocupación {ocupacion.codigo_onet}: {error}") from error
        ajuste = clasificar_ajuste(correlacion)
        if ajuste is not None:
            candidatas.append((ocupacion, correlacion, ajuste))
    candidatas.sort(key=lambda candidata: (-candidata[1], candidata[0].codigo_onet))
    coincidencias = tuple(
        CoincidenciaCalculada(posicion, ocupacion.codigo_onet, ocupacion.titulo, correlacion, ajuste)
        for posicion, (ocupacion, correlacion, ajuste) in enumerate(candidatas[:LIMITE_COINCIDENCIAS], start=1)
    )
    return CoincidenciasCalculadas(perfil_plano=False, coincidencias=coincidencias)


def calcular_codigo_interes(puntajes: Sequence[float], orden: Sequence[str] | None = None) -> CodigoInteresCalculado:
    orden = orden_canonico_riasec() if orden is None else orden
    _validar_vector(puntajes, len(orden))
    if len(orden) <= LONGITUD_CODIGO_INTERES:
        raise ValueError("Faltan dimensiones para el código de interés y su desempate")
    posiciones = sorted(range(len(orden)), key=lambda posicion: (-puntajes[posicion], posicion))
    return CodigoInteresCalculado(
        codigo="".join(orden[posicion] for posicion in posiciones[:LONGITUD_CODIGO_INTERES]),
        hay_empate=puntajes[posiciones[LONGITUD_CODIGO_INTERES - 1]] == puntajes[posiciones[LONGITUD_CODIGO_INTERES]],
    )
