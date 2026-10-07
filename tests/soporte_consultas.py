"""Medición de ejecuciones SQL y peticiones, sin contar su preparación."""

from collections import Counter
from dataclasses import dataclass

from sqlalchemy import Engine, event


@dataclass(frozen=True)
class EjecucionSql:
    sentencia: str
    en_lote: bool


class ContadorConsultas:
    """Una ejecución del cursor suma uno, también cuando usa executemany.

    No guarda parámetros. El listener del Engine recibe también las consultas
    del hilo de TestClient, y se retira incluso si la petición falla.
    """

    def __init__(self, motor_bd: Engine):
        self.motor_bd = motor_bd
        self.ejecuciones: list[EjecucionSql] = []
        self._activo = False
        self._listener = self._contar

    def _contar(self, conexion, cursor, sentencia, parametros, contexto, en_lote):
        self.ejecuciones.append(EjecucionSql(sentencia=sentencia, en_lote=en_lote))

    def __enter__(self):
        if self._activo:
            raise RuntimeError("El contador ya está activo")
        self.ejecuciones.clear()
        event.listen(self.motor_bd, "before_cursor_execute", self._listener)
        self._activo = True
        return self

    def __exit__(self, tipo_error, error, traza):
        event.remove(self.motor_bd, "before_cursor_execute", self._listener)
        self._activo = False

    @property
    def cantidad(self) -> int:
        return len(self.ejecuciones)

    @property
    def por_tipo(self) -> dict[str, int]:
        return dict(Counter(ejecucion.sentencia.split()[0].upper()
                            for ejecucion in self.ejecuciones))

    @property
    def diagnostico(self) -> str:
        return "\n".join(f"{numero}. {ejecucion.sentencia}" for numero, ejecucion in
                         enumerate(self.ejecuciones, start=1))


class MedidorPeticiones:
    def __init__(self, cliente, motor_bd: Engine):
        self.cliente = cliente
        self.motor_bd = motor_bd
        self.mediciones: dict[str, ContadorConsultas] = {}

    def medir(self, nombre: str, metodo: str, ruta: str, datos=None, estado_http: int = 200):
        if nombre in self.mediciones:
            raise ValueError(f"Nombre de medición repetido: {nombre}")
        contador = ContadorConsultas(self.motor_bd)
        with contador:
            respuesta = self.cliente.request(metodo, ruta, json=datos)
        self.mediciones[nombre] = contador
        assert respuesta.status_code == estado_http, respuesta.text
        print(f"SQL {nombre}: {contador.cantidad} {contador.por_tipo}")
        return respuesta.json()

    def exigir_limite(self, nombre: str, limite: int):
        contador = self.mediciones[nombre]
        assert contador.cantidad <= limite, (
            f"{nombre}: {contador.cantidad} ejecuciones SQL; límite {limite}\n"
            f"{contador.diagnostico}"
        )
