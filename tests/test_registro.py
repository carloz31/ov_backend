"""Registro: estructura y escenarios de acciones/consultas con evaluador falso."""

import json
import re
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, func, inspect, select, text
from sqlalchemy.exc import IntegrityError

from app import models as modelos
from datos.cargar import preparar_base
from app.main import crear_aplicacion
from app.models.base import Base
from app.services.registro import contenido as contenido_registro
from app.services.registro.evaluacion import EvaluadorFalso, ResultadoEvaluacion


FECHA = datetime(2026, 10, 1, 10)
CODIGOS_ITEMS = ["REG-HAB-1", "REG-HAB-2", "REG-HAB-3"]


def buscar(sesion, modelo, codigo):
    return sesion.scalar(select(modelo).where(modelo.codigo == codigo))


def fotografia(aplicacion):
    with aplicacion.state.motor_bd.connect() as conexion:
        return {tabla.name: conexion.execute(select(tabla)).all() for tabla in Base.metadata.sorted_tables}


@pytest.fixture
def respuesta_registro(sesion):
    cuenta = buscar(sesion, modelos.Cuenta, "est-ana")
    actividad = buscar(sesion, modelos.Actividad, "REG-ACT08")
    item = buscar(sesion, modelos.ItemRegistro, "REG-HAB-1")
    progreso = modelos.ProgresoActividad(cuenta_id=cuenta.id, actividad_id=actividad.id,
                                         estado=modelos.EstadoProgreso.EN_CURSO, posicion="plan")
    sesion.add(progreso)
    sesion.flush()
    respuesta = modelos.RespuestaRegistro(progreso_id=progreso.id, item_registro_id=item.id,
        texto_inicial="Un borrador", estado=modelos.EstadoRespuestaRegistro.BORRADOR,
        creada_en=FECHA, actualizada_en=FECHA)
    sesion.add(respuesta)
    sesion.flush()
    return respuesta


def evaluacion(respuesta, **cambios):
    return modelos.EvaluacionRespuesta(**{
        "respuesta_id": respuesta.id, "numero": 1, "origen": modelos.OrigenEvaluacion.RESPALDO_LONGITUD,
        "clasificacion": modelos.ClasificacionRespuesta.VAGA, "criterios_faltantes": ["C1", "C2"],
        "pregunta_generada": "Cuéntame más", "texto_evaluado": respuesta.texto_inicial, "fecha_hora": FECHA,
        **cambios,
    })


def test_esquema_registro_columnas_y_enumerados(cliente, aplicacion):
    inspector = inspect(aplicacion.state.motor_bd)
    columnas = {
        "item_registro": {"id", "codigo", "nombre", "consigna", "min_caracteres", "obligatorio", "repregunta_generica"},
        "criterio_completitud": {"id", "item_registro_id", "codigo", "descripcion", "orden"},
        "actividad_item_registro": {"actividad_id", "item_registro_id", "orden"},
        "respuesta_registro": {"id", "progreso_id", "item_registro_id", "texto_inicial", "estado",
                               "clasificacion_inicial", "ampliada", "creada_en", "actualizada_en"},
        "turno_seguimiento": {"id", "respuesta_id", "orden", "pregunta", "criterios_objetivo", "respuesta",
                             "respondido_en", "creado_en"},
        "evaluacion_respuesta": {"id", "respuesta_id", "numero", "origen", "clasificacion", "criterios_faltantes",
                                 "pregunta_generada", "requiere_atencion", "modelo", "version_prompt", "latencia_ms",
                                 "error", "texto_evaluado", "fecha_hora"},
    }
    for tabla, esperadas in columnas.items():
        assert {columna["name"] for columna in inspector.get_columns(tabla)} == esperadas
    progreso = {columna["name"]: columna for columna in inspector.get_columns("progreso_actividad")}
    assert set(progreso) == {"id", "cuenta_id", "actividad_id", "estado", "posicion"}
    assert progreso["posicion"]["nullable"] is True
    assert inspector.get_pk_constraint("actividad_item_registro")["constrained_columns"] == [
        "actividad_id", "item_registro_id",
    ]
    assert list(modelos.ClasificacionRespuesta) == ["ADECUADA", "VAGA", "NO_EVALUADA"]
    assert list(modelos.EstadoRespuestaRegistro) == ["BORRADOR", "PENDIENTE_SEGUIMIENTO", "FINAL"]
    assert list(modelos.OrigenEvaluacion) == ["LLM", "RESPALDO_LONGITUD"]


def test_semilla_registro_coincide_con_especificacion(cliente, sesion):
    assert cliente.post("/demo/reiniciar").status_code == 200
    bloque = buscar(sesion, modelos.Bloque, "REG")
    actividad = buscar(sesion, modelos.Actividad, "REG-ACT08")
    assert (bloque.nombre, bloque.numero, bloque.espacio, bloque.audiencia) == (
        "Laboratorio de registros (solo demo)", 0, "MISIONES_CAMPO", "ESTUDIANTE",
    )
    assert (actividad.titulo, actividad.tipo, actividad.orden, actividad.bloque_id, actividad.puntaje_minimo) == (
        "Mi plan para fortalecer una habilidad", "REGISTRO", 1, bloque.id, None,
    )
    ruta = contenido_registro.RUTA_CONTENIDO_REGISTRO.parents[3] / "docs" / "spec-demo-registro-gemini.md"
    especificacion = ruta.read_text(encoding="utf-8")
    items = list(sesion.scalars(select(modelos.ItemRegistro).order_by(modelos.ItemRegistro.codigo)))
    assert [item.codigo for item in items] == CODIGOS_ITEMS
    relaciones = list(sesion.scalars(select(modelos.ActividadItemRegistro).order_by(modelos.ActividadItemRegistro.orden)))
    assert [(fila.actividad_id, fila.item_registro_id, fila.orden) for fila in relaciones] == [
        (actividad.id, item.id, orden) for orden, item in enumerate(items, start=1)
    ]
    for item in items:
        apartado = re.search(rf'^\*\*{item.codigo}, "([^"]+)"\*\*\n(.*?)(?=^\*\*|^###)',
                             especificacion, re.MULTILINE | re.DOTALL)
        assert apartado is not None
        nombre, contenido = apartado.groups()
        assert item.nombre == nombre
        assert item.consigna == re.search(r"^- Consigna: (.+)$", contenido, re.MULTILINE)[1]
        assert item.min_caracteres == int(re.search(r"^- Mínimo: (\d+) caracteres", contenido, re.MULTILINE)[1])
        assert item.obligatorio is True
        assert item.repregunta_generica == re.search(r"^- Repregunta genérica: (.+)$", contenido, re.MULTILINE)[1]
        criterios = list(sesion.scalars(select(modelos.CriterioCompletitud).where(
            modelos.CriterioCompletitud.item_registro_id == item.id,
        ).order_by(modelos.CriterioCompletitud.orden)))
        esperados = re.findall(r"^  - `(C\d+)`: (.+)$", contenido, re.MULTILINE)
        assert [(criterio.codigo, criterio.descripcion, criterio.orden) for criterio in criterios] == [
            (codigo, descripcion, orden) for orden, (codigo, descripcion) in enumerate(esperados, start=1)
        ]
    assert sesion.scalar(select(func.count()).select_from(modelos.CriterioCompletitud)) == 6
    assert sesion.scalar(select(func.count()).select_from(modelos.ReglaDesbloqueo)) == 47
    assert sesion.scalar(select(func.count()).select_from(modelos.CondicionDesbloqueo)) == 58
    for modelo in (modelos.ProgresoActividad, modelos.RespuestaRegistro, modelos.TurnoSeguimiento, modelos.EvaluacionRespuesta):
        assert sesion.scalar(select(func.count()).select_from(modelo)) == 0


def test_reg_disponible_solo_para_estudiantes(cliente):
    assert cliente.post("/demo/reiniciar").status_code == 200
    for cuenta in ("est-ana", "est-luis"):
        bloques = cliente.get(f"/cuentas/{cuenta}/estado").json()["bloques"]
        registro = next(bloque for bloque in bloques if bloque["codigo"] == "REG")
        assert registro["estado"] == "DISPONIBLE"
        assert registro["actividades"] == [{
            "codigo": "REG-ACT08", "titulo": "Mi plan para fortalecer una habilidad", "estado": "DISPONIBLE",
        }]
    assert "REG" not in [bloque["codigo"] for bloque in cliente.get("/cuentas/apo-rosa/estado").json()["bloques"]]
    reglas = cliente.get("/reglas").json()
    assert all(regla["objetivo"]["codigo"] not in ("REG", "REG-ACT08") for regla in reglas)


def test_respuestas_y_evaluaciones_guardan_json_y_campos_opcionales(sesion, respuesta_registro):
    respuesta = respuesta_registro
    assert respuesta.texto_inicial == "Un borrador" and respuesta.clasificacion_inicial is None
    assert respuesta.ampliada is False
    respuesta.clasificacion_inicial = modelos.ClasificacionRespuesta.VAGA
    primera = evaluacion(respuesta)
    segunda = evaluacion(respuesta, numero=2, origen=modelos.OrigenEvaluacion.RESPALDO_LONGITUD,
        clasificacion=modelos.ClasificacionRespuesta.NO_EVALUADA, criterios_faltantes=[],
        pregunta_generada=None, error="Fallo simulado", requiere_atencion=False)
    tercera = evaluacion(respuesta, numero=3, origen=modelos.OrigenEvaluacion.LLM,
        clasificacion=modelos.ClasificacionRespuesta.ADECUADA, criterios_faltantes=[], pregunta_generada=None)
    sesion.add_all([primera, segunda, tercera])
    sesion.flush()
    sesion.expire_all()
    assert primera.criterios_faltantes == ["C1", "C2"]
    assert primera.requiere_atencion is False
    assert primera.modelo is None and primera.version_prompt is None and primera.latencia_ms is None
    assert segunda.clasificacion == "NO_EVALUADA" and segunda.error == "Fallo simulado"
    assert respuesta.texto_inicial == "Un borrador"
    assert tercera.numero == 3
    assert sesion.scalar(select(func.count()).select_from(modelos.EvaluacionRespuesta)) == 3


@pytest.mark.parametrize("modelo", [modelos.ItemRegistro, modelos.CriterioCompletitud,
                                  modelos.ActividadItemRegistro, modelos.RespuestaRegistro])
def test_unicidad_de_definiciones_y_respuestas(sesion, respuesta_registro, modelo):
    original = sesion.scalar(select(modelo))
    datos = {columna.name: getattr(original, columna.name) for columna in modelo.__table__.columns
             if columna.name != "id"}
    with pytest.raises(IntegrityError):
        with sesion.begin_nested():
            sesion.execute(modelo.__table__.insert(), datos)


@pytest.mark.parametrize("tabla,columna,valor", [
    ("respuesta_registro", "progreso_id", 999999),
    ("respuesta_registro", "item_registro_id", 999999),
    ("respuesta_registro", "estado", "INVALIDO"),
    ("respuesta_registro", "clasificacion_inicial", "INVALIDA"),
    ("criterio_completitud", "item_registro_id", 999999),
    ("actividad_item_registro", "actividad_id", 999999),
    ("actividad_item_registro", "item_registro_id", 999999),
    ("evaluacion_respuesta", "respuesta_id", 999999),
    ("evaluacion_respuesta", "numero", 0),
    ("evaluacion_respuesta", "numero", -1),
    ("evaluacion_respuesta", "numero", 1.5),
    ("evaluacion_respuesta", "origen", "INVALIDO"),
    ("evaluacion_respuesta", "clasificacion", "INVALIDA"),
    ("evaluacion_respuesta", "criterios_faltantes", "{}"),
    ("evaluacion_respuesta", "criterios_faltantes", None),
])
def test_restricciones_sql_registro(sesion, respuesta_registro, tabla, columna, valor):
    sesion.add(evaluacion(respuesta_registro))
    sesion.flush()
    with pytest.raises(IntegrityError):
        with sesion.begin_nested():
            sesion.execute(text(f"UPDATE {tabla} SET {columna} = :valor"), {"valor": valor})


def test_mismo_item_admite_respuestas_de_cuentas_distintas(sesion, respuesta_registro):
    luis = buscar(sesion, modelos.Cuenta, "est-luis")
    actividad = buscar(sesion, modelos.Actividad, "REG-ACT08")
    progreso = modelos.ProgresoActividad(cuenta_id=luis.id, actividad_id=actividad.id, estado=modelos.EstadoProgreso.EN_CURSO)
    sesion.add(progreso)
    sesion.flush()
    sesion.add(modelos.RespuestaRegistro(progreso_id=progreso.id, item_registro_id=respuesta_registro.item_registro_id,
        texto_inicial="Borrador de Luis", estado=modelos.EstadoRespuestaRegistro.BORRADOR, creada_en=FECHA, actualizada_en=FECHA))
    sesion.flush()
    assert progreso.posicion is None
    assert sesion.scalar(select(func.count()).select_from(modelos.RespuestaRegistro)) == 2


def crear_turno(registro, **cambios):
    return modelos.TurnoSeguimiento(**{
        'respuesta_id': registro.id, 'orden': 1, 'pregunta': '¿En qué situación te cuesta?',
        'criterios_objetivo': ['C2'], 'creado_en': FECHA, **cambios,
    })


def test_turnos_persisten_pregunta_borrador_respuesta_y_texto_inicial(sesion, respuesta_registro):
    respuesta = respuesta_registro
    respuesta.estado = modelos.EstadoRespuestaRegistro.PENDIENTE_SEGUIMIENTO
    primero = crear_turno(respuesta)
    segundo = crear_turno(respuesta, orden=2, criterios_objetivo=['C1', 'C2'], respuesta='Borrador del turno')
    sesion.add_all([primero, segundo])
    sesion.flush()
    sesion.expire_all()
    assert primero.respuesta is None and primero.respondido_en is None
    assert primero.criterios_objetivo == ['C2'] and primero.creado_en == FECHA
    assert segundo.respuesta == 'Borrador del turno' and segundo.respondido_en is None
    assert segundo.criterios_objetivo == ['C1', 'C2']
    primero.respuesta = 'En el trabajo de Comunicación.'
    primero.respondido_en = FECHA
    respuesta.ampliada = True
    sesion.flush()
    sesion.expire_all()
    assert respuesta.texto_inicial == 'Un borrador' and respuesta.ampliada is True
    assert primero.respuesta == 'En el trabajo de Comunicación.' and primero.respondido_en == FECHA
    assert [turno.orden for turno in sesion.scalars(select(modelos.TurnoSeguimiento).order_by(
        modelos.TurnoSeguimiento.orden))] == [1, 2]


def test_turno_unico_por_respuesta_y_orden(sesion, respuesta_registro):
    sesion.add(crear_turno(respuesta_registro))
    sesion.flush()
    with pytest.raises(IntegrityError):
        with sesion.begin_nested():
            sesion.add(crear_turno(respuesta_registro, pregunta='Otra pregunta'))
            sesion.flush()


@pytest.mark.parametrize('columna,valor', [
    ('respuesta_id', 999999), ('orden', 0), ('orden', 3), ('orden', 1.5),
    ('criterios_objetivo', '{}'), ('criterios_objetivo', None), ('criterios_objetivo', '"C2"'),
])
def test_restricciones_sql_turno_seguimiento(sesion, respuesta_registro, columna, valor):
    sesion.add(crear_turno(respuesta_registro))
    sesion.flush()
    with pytest.raises(IntegrityError):
        with sesion.begin_nested():
            sesion.execute(text(f'UPDATE turno_seguimiento SET {columna} = :valor'), {'valor': valor})


def test_reinicio_borra_turnos_y_conserva_cache(cliente, aplicacion):
    with aplicacion.state.fabrica_sesiones.begin() as sesion:
        cuenta = buscar(sesion, modelos.Cuenta, 'est-ana')
        actividad = buscar(sesion, modelos.Actividad, 'REG-ACT08')
        item = buscar(sesion, modelos.ItemRegistro, 'REG-HAB-1')
        progreso = modelos.ProgresoActividad(cuenta_id=cuenta.id, actividad_id=actividad.id,
            estado=modelos.EstadoProgreso.EN_CURSO, posicion='plan')
        sesion.add(progreso)
        sesion.flush()
        respuesta = modelos.RespuestaRegistro(progreso_id=progreso.id, item_registro_id=item.id,
            texto_inicial='Comunicación', estado=modelos.EstadoRespuestaRegistro.PENDIENTE_SEGUIMIENTO,
            clasificacion_inicial=modelos.ClasificacionRespuesta.VAGA, creada_en=FECHA, actualizada_en=FECHA)
        sesion.add(respuesta)
        sesion.flush()
        sesion.add(crear_turno(respuesta, respuesta='Borrador'))
    cache = aplicacion.state.motor_bd.cache_definiciones.actual
    assert cliente.post('/demo/reiniciar').status_code == 200
    assert aplicacion.state.motor_bd.cache_definiciones.actual is cache
    with aplicacion.state.fabrica_sesiones() as sesion:
        assert sesion.scalar(select(func.count()).select_from(modelos.TurnoSeguimiento)) == 0
        assert sesion.scalar(select(func.count()).select_from(modelos.RespuestaRegistro)) == 0
    definiciones = aplicacion.state.motor_bd.cache_definiciones.actual
    assert modelos.TurnoSeguimiento not in definiciones.tablas
    assert definiciones.por_codigo(modelos.ItemRegistro, 'REG-HAB-1').repregunta_generica


def test_contenido_json_valido_y_publico_sin_escrituras(cliente, aplicacion):
    antes = fotografia(aplicacion)
    contenido = cliente.get("/demo/recursos/contenido/REG-ACT08.json")
    assert contenido.status_code == 200
    documento = contenido.json()
    assert documento["actividad"] == "REG-ACT08" and documento["plantilla"] == "registro-guiado"
    assert documento["momentos"][0]["personaje"] == "Lumi"
    assert len(documento["momentos"][0]["lineas"]) == 3
    assert documento["momentos"][1]["items"] == CODIGOS_ITEMS
    with aplicacion.state.fabrica_sesiones.begin() as sesion:
        assert contenido_registro.validar_contenido_registro(sesion) == ("explicacion", "plan")
    assert fotografia(aplicacion) == antes


def contenido_alterado(tmp_path, monkeypatch, variante):
    documento = json.loads(contenido_registro.RUTA_CONTENIDO_REGISTRO.read_text(encoding="utf-8"))
    if variante == "actividad":
        documento["actividad"] = "NO-EXISTE"
        mensaje = "la actividad no existe"
    elif variante == "item":
        documento["momentos"][1]["items"][0] = "REG-NO-EXISTE"
        mensaje = "el ítem no existe"
    elif variante in ("faltante", "orden", "duplicado"):
        items = documento["momentos"][1]["items"]
        if variante == "faltante":
            items.pop()
        elif variante == "orden":
            items.reverse()
        else:
            items.append(items[0])
        mensaje = "los ítems no coinciden"
    elif variante == "momentos_repetidos":
        documento["momentos"][1]["id"] = "explicacion"
        mensaje = "id de momento repetido"
    elif variante == "sin_id":
        documento["momentos"][0]["id"] = " "
        mensaje = "id no vacío"
    elif variante == "items_invalidos":
        documento["momentos"][1]["items"] = [None]
        mensaje = "lista de códigos"
    elif variante == "momentos_invalidos":
        documento["momentos"] = None
        mensaje = "lista de momentos"
    else:
        mensaje = "JSON válido"
    ruta = tmp_path / "REG-ACT08.json"
    if variante != "ausente":
        ruta.write_text("{" if variante == "json_invalido" else json.dumps(documento, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(contenido_registro, "RUTA_CONTENIDO_REGISTRO", ruta)
    return mensaje


@pytest.mark.parametrize('variante', ['item', 'faltante', 'orden', 'duplicado', 'momentos_repetidos',
                                     'sin_id', 'items_invalidos', 'momentos_invalidos', 'json_invalido', 'ausente'])
def test_r17_contenido_invalido_impide_arranque_sin_modificar_datos(tmp_path, monkeypatch, variante):
    url = f'sqlite:///{(tmp_path / "invalida.db").as_posix()}'
    preparar_base(url, 'demo', crear_tablas=True)
    mensaje = contenido_alterado(tmp_path, monkeypatch, variante)
    aplicacion = crear_aplicacion(url)
    antes = fotografia(aplicacion)
    with pytest.raises(ValueError, match=mensaje):
        with TestClient(aplicacion):
            pass
    assert fotografia(aplicacion) == antes
    aplicacion.state.motor_bd.dispose()


def test_arranque_valida_json_tambien_con_base_existente(tmp_path, monkeypatch):
    ruta = tmp_path / "persistencia.db"
    url = f"sqlite:///{ruta.as_posix()}"
    preparar_base(url, 'demo', crear_tablas=True)
    with TestClient(crear_aplicacion(url)) as cliente:
        assert cliente.post("/acciones/completar-actividad", json={"cuenta": "est-ana", "actividad": "ACT-01"}).status_code == 200
    antes = ruta.read_bytes()
    contenido_alterado(tmp_path, monkeypatch, "item")
    with pytest.raises(ValueError, match="el ítem no existe"):
        with TestClient(crear_aplicacion(url)):
            pass
    assert ruta.read_bytes() == antes


def test_reinicio_no_relee_json_y_conserva_cache(cliente, aplicacion, tmp_path, monkeypatch):
    assert cliente.post('/acciones/completar-actividad', json={'cuenta': 'est-ana', 'actividad': 'ACT-01'}).status_code == 200
    cache = aplicacion.state.motor_bd.cache_definiciones.actual
    posiciones = aplicacion.state.posiciones_registro
    contenido_alterado(tmp_path, monkeypatch, 'faltante')
    assert cliente.post('/demo/reiniciar').json() == {'mensaje': 'Demo reiniciada'}
    assert cliente.get('/cuentas/est-ana/eventos').json() == []
    assert aplicacion.state.motor_bd.cache_definiciones.actual is cache
    assert aplicacion.state.posiciones_registro is posiciones


def test_cache_registro_orden_criterios_por_item_y_reinicio(cliente, aplicacion, contador_consultas):
    cache = aplicacion.state.motor_bd.cache_definiciones
    for _ in range(2):
        assert cliente.post("/demo/reiniciar").status_code == 200
        with contador_consultas(aplicacion.state.motor_bd) as contador:
            definiciones = cache.actual
            actividad = definiciones.por_codigo(modelos.Actividad, "REG-ACT08")
            items = definiciones.items_registro_por_actividad[actividad.id]
            assert [item.codigo for item in items] == CODIGOS_ITEMS
            for item in items:
                criterios = definiciones.criterios_por_item_registro[item.id]
                assert [(criterio.codigo, criterio.orden) for criterio in criterios] == [("C1", 1), ("C2", 2)]
                assert definiciones.por_codigo(modelos.CriterioCompletitud, (item.id, "C1")) is criterios[0]
            assert len(definiciones.listar(modelos.CriterioCompletitud)) == 6
        assert contador.cantidad == 0


def test_cache_registro_reconstruye_tras_commit_y_conserva_tras_rollback(cliente, aplicacion):
    cache = aplicacion.state.motor_bd.cache_definiciones
    inicial = cache.actual
    with aplicacion.state.fabrica_sesiones() as sesion:
        criterio = sesion.scalar(select(modelos.CriterioCompletitud).where(modelos.CriterioCompletitud.codigo == "C1"))
        criterio.descripcion = "Cambio revertido"
        sesion.flush()
        sesion.rollback()
    assert cache.actual is inicial
    with aplicacion.state.fabrica_sesiones.begin() as sesion:
        item = buscar(sesion, modelos.ItemRegistro, "REG-HAB-1")
        item.min_caracteres = 45
    assert cache.actual is not inicial
    assert cache.actual.por_codigo(modelos.ItemRegistro, "REG-HAB-1").min_caracteres == 45
    assert inicial.por_codigo(modelos.ItemRegistro, "REG-HAB-1").min_caracteres == 40
    assert cliente.post("/demo/reiniciar").status_code == 200
    assert cache.actual.por_codigo(modelos.ItemRegistro, "REG-HAB-1").min_caracteres == 45


def test_accion_registro_anterior_sigue_rechazando_no_evaluada(cliente, aplicacion):
    antes = fotografia(aplicacion)
    respuesta = cliente.post("/acciones/responder-registro", json={
        "cuenta": "est-ana", "clasificacion": "NO_EVALUADA", "ampliada": False,
    })
    assert respuesta.status_code == 422
    assert fotografia(aplicacion) == antes


TEXTO_COMPLETO = "Quiero practicar la asertividad al opinar en los trabajos de mi colegio."


@pytest.fixture
def registro_demo(cliente, aplicacion):
    assert cliente.post('/demo/reiniciar').status_code == 200
    assert isinstance(aplicacion.state.evaluador_respuestas, EvaluadorFalso)
    return aplicacion.state.evaluador_respuestas


def accion_registro(cliente, accion, item='REG-HAB-1', texto=TEXTO_COMPLETO, **cambios):
    datos = dict(cuenta='est-ana', actividad='REG-ACT08', item=item, fecha_hora=FECHA.isoformat())
    if accion != 'continuar-sin-responder':
        datos['texto'] = texto
    return cliente.post(f'/acciones/registro/{accion}', json={**datos, **cambios})


def estado_registro(cliente, cuenta='est-ana', actividad='REG-ACT08'):
    return cliente.get(f'/cuentas/{cuenta}/actividades/{actividad}/registro')


def historial_registro(cliente, cuenta='est-ana', actividad='REG-ACT08'):
    return cliente.get(f'/demo/registro/{cuenta}/{actividad}/evaluaciones')


def fila_respuesta(aplicacion, cuenta='est-ana', item='REG-HAB-1'):
    with aplicacion.state.fabrica_sesiones() as sesion:
        fila = sesion.scalar(select(modelos.RespuestaRegistro).join(modelos.ProgresoActividad).join(
            modelos.Cuenta).join(modelos.ItemRegistro).where(
                modelos.Cuenta.codigo == cuenta, modelos.ItemRegistro.codigo == item))
        assert fila is not None
        datos = {columna.name: getattr(fila, columna.name) for columna in modelos.RespuestaRegistro.__table__.columns}
        # El primer texto permanece en la conversación de la auditoría inmutable.
        datos['primer_texto_evaluado'] = sesion.scalar(select(modelos.EvaluacionRespuesta.texto_evaluado).where(
            modelos.EvaluacionRespuesta.respuesta_id == fila.id).order_by(modelos.EvaluacionRespuesta.numero).limit(1))
        if datos['primer_texto_evaluado'] is not None:
            datos['primer_texto_evaluado'] = json.loads(datos['primer_texto_evaluado'])['texto_inicial']
        return datos


def comprobar_publico(respuesta):
    assert respuesta.status_code == 200, respuesta.text
    texto = respuesta.text
    for campo in ('clasificacion', 'criterios_faltantes', 'requiere_atencion', 'NO_EVALUADA',
                  'primer_texto_evaluado', 'actualizada_en', 'respuesta_id', 'latencia_ms', 'origen', 'error'):
        assert f'"{campo}"' not in texto
    return respuesta.json()


def test_r1_consultas_iniciales_ordenadas_sin_escrituras(cliente, aplicacion, registro_demo):
    antes = fotografia(aplicacion)
    items = cliente.get('/actividades/REG-ACT08/items-registro')
    assert items.status_code == 200
    assert [item['codigo'] for item in items.json()] == CODIGOS_ITEMS
    assert [item['min_caracteres'] for item in items.json()] == [40, 40, 30]
    assert all(set(item) == {'codigo', 'nombre', 'consigna', 'min_caracteres', 'obligatorio'} for item in items.json())
    assert estado_registro(cliente).json() == {'posicion': None, 'estado': None, 'respuestas': []}
    assert historial_registro(cliente).json() == []
    for consultar in (estado_registro, historial_registro):
        assert consultar(cliente, cuenta='apo-rosa').status_code == 404
    assert fotografia(aplicacion) == antes


def test_r2_posicion_valida_crea_progreso_y_se_retoma(cliente, aplicacion, registro_demo):
    datos = dict(cuenta='est-ana', actividad='REG-ACT08', posicion='plan', fecha_hora=FECHA.isoformat())
    respuesta = cliente.post('/acciones/guardar-posicion', json=datos)
    assert respuesta.json() == {'posicion': 'plan', 'estado': 'EN_CURSO'}
    assert estado_registro(cliente).json() == {'posicion': 'plan', 'estado': 'EN_CURSO', 'respuestas': []}
    bloques = cliente.get('/cuentas/est-ana/estado').json()['bloques']
    assert next(b for b in bloques if b['codigo'] == 'REG')['actividades'][0]['estado'] == 'EN_CURSO'
    antes = fotografia(aplicacion)
    assert cliente.post('/acciones/guardar-posicion', json={**datos, 'posicion': 'no-existe'}).status_code == 422
    assert fotografia(aplicacion) == antes
    assert cliente.post('/acciones/guardar-posicion', json={**datos, 'posicion': 'explicacion'}).status_code == 200
    assert estado_registro(cliente).json()['posicion'] == 'explicacion'
    assert registro_demo.contextos == []
    with aplicacion.state.fabrica_sesiones() as sesion:
        assert sesion.scalar(select(func.count()).select_from(modelos.EventoUso)) == 0


def turnos_guardados(aplicacion, item='REG-HAB-1', cuenta='est-ana'):
    with aplicacion.state.fabrica_sesiones() as sesion:
        return [{c.name: getattr(turno, c.name) for c in modelos.TurnoSeguimiento.__table__.columns}
            for turno in sesion.scalars(select(modelos.TurnoSeguimiento).join(modelos.RespuestaRegistro)
                .join(modelos.ProgresoActividad).join(modelos.Cuenta).join(modelos.ItemRegistro)
                .where(modelos.Cuenta.codigo == cuenta, modelos.ItemRegistro.codigo == item)
                .order_by(modelos.TurnoSeguimiento.orden))]


def mensajes_iniciales(texto):
    return [dict(tipo='respuesta', texto=texto)]


def test_r3_borrador_reemplaza_sin_evaluacion_ni_eventos(cliente, aplicacion, registro_demo):
    for texto in ('Mi borrador', 'El reemplazo'):
        assert comprobar_publico(accion_registro(cliente, 'guardar-borrador', texto=texto)) == {
            'item': 'REG-HAB-1', 'estado': 'BORRADOR'}
    assert estado_registro(cliente).json()['respuestas'] == [{
        'item': 'REG-HAB-1', 'estado': 'BORRADOR', 'conversacion': mensajes_iniciales('El reemplazo')}]
    assert historial_registro(cliente).json() == [] and registro_demo.contextos == []
    assert turnos_guardados(aplicacion) == []
    with aplicacion.state.fabrica_sesiones() as sesion:
        assert sesion.scalar(select(func.count()).select_from(modelos.RespuestaRegistro)) == 1
        assert sesion.scalar(select(func.count()).select_from(modelos.EventoUso)) == 0
    fila = fila_respuesta(aplicacion)
    assert fila['primer_texto_evaluado'] is None and fila['clasificacion_inicial'] is None
    assert fila['creada_en'] == FECHA


def test_r4_respaldo_corto_y_r5_turno_generico_sin_reevaluar(cliente, aplicacion, registro_demo):
    inicial = 'Asertividad [falla]'
    resultado = comprobar_publico(accion_registro(cliente, 'enviar', texto=inicial))
    item = aplicacion.state.motor_bd.cache_definiciones.actual.por_codigo(modelos.ItemRegistro, 'REG-HAB-1')
    assert resultado['estado'] == 'PENDIENTE_SEGUIMIENTO'
    assert resultado['conversacion'] == mensajes_iniciales(inicial) + [dict(tipo='pregunta', orden=1, texto=item.repregunta_generica)]
    assert resultado['eventos_registrados'] == resultado['nuevos_desbloqueos'] == []
    primera = historial_registro(cliente).json()
    assert [(e['origen'], e['numero'], e['clasificacion']) for e in primera] == [('RESPALDO_LONGITUD', 1, 'VAGA')]
    assert json.loads(primera[0]['texto_evaluado']) == dict(texto_inicial=inicial, turnos=[])
    assert primera[0]['fecha_hora'] == FECHA.isoformat() and primera[0]['error']
    assert primera[0]['version_prompt'] == 'v2' and primera[0]['latencia_ms'] >= 0
    assert len(registro_demo.contextos) == 1
    assert turnos_guardados(aplicacion)[0]['criterios_objetivo'] == ['C1', 'C2']
    resultado = comprobar_publico(accion_registro(cliente, 'responder-seguimiento', texto='En mi grupo [falla]'))
    assert resultado['estado'] == 'FINAL'
    assert resultado['conversacion'][-1] == dict(tipo='respuesta', orden=1, texto='En mi grupo [falla]', borrador=False)
    assert resultado['eventos_registrados'] == [{'tipo': 'RESPUESTA_REFLEXIVA', 'referencia': None, 'fecha_hora': FECHA.isoformat()}]
    fila = fila_respuesta(aplicacion)
    assert fila['texto_inicial'] == fila['primer_texto_evaluado'] == inicial
    assert fila['clasificacion_inicial'] == 'VAGA' and fila['ampliada'] is True
    assert turnos_guardados(aplicacion)[0]['respondido_en'] == FECHA
    assert historial_registro(cliente).json() == primera and len(registro_demo.contextos) == 1


def test_r5b_seguimiento_llm_evalua_conversacion_completa(cliente, aplicacion, registro_demo):
    inicial = TEXTO_COMPLETO + ' [vaga]'
    primera = comprobar_publico(accion_registro(cliente, 'enviar', item='REG-HAB-2', texto=inicial))
    resultado = comprobar_publico(accion_registro(cliente, 'responder-seguimiento', item='REG-HAB-2', texto='El jueves'))
    assert resultado['estado'] == 'FINAL' and len(resultado['eventos_registrados']) == 1
    contexto = registro_demo.contextos[-1]
    assert contexto.conversacion.texto_inicial == inicial
    assert [(t.pregunta, t.respuesta) for t in contexto.conversacion.turnos] == [(primera['conversacion'][1]['texto'], 'El jueves')]
    assert contexto.criterios_faltantes_previos == ('C1', 'C2')
    historial = historial_registro(cliente).json()
    assert [(e['numero'], e['origen']) for e in historial] == [(1, 'LLM'), (2, 'LLM')]
    assert json.loads(historial[-1]['texto_evaluado'])['turnos'][0]['respuesta'] == 'El jueves'
    assert fila_respuesta(aplicacion, item='REG-HAB-2')['texto_inicial'] == inicial


def test_r5c_corto_se_evalua_antes_del_minimo(cliente, aplicacion, registro_demo):
    resultado = comprobar_publico(accion_registro(cliente, 'enviar', texto='Asertividad'))
    assert resultado['estado'] == 'FINAL' and len(resultado['eventos_registrados']) == 1
    assert resultado['conversacion'] == mensajes_iniciales('Asertividad')
    assert historial_registro(cliente).json()[0]['origen'] == 'LLM'
    assert len(registro_demo.contextos) == 1 and turnos_guardados(aplicacion) == []


def test_r6_solo_faltantes_y_r7_dos_turnos_con_maximo(cliente, aplicacion, registro_demo):
    inicial = TEXTO_COMPLETO + ' [falta:C2]'
    primera = comprobar_publico(accion_registro(cliente, 'enviar', texto=inicial))
    assert primera['estado'] == 'PENDIENTE_SEGUIMIENTO'
    assert registro_demo.contextos[0].criterios_faltantes_previos == ('C1', 'C2')
    assert turnos_guardados(aplicacion)[0]['criterios_objetivo'] == ['C2']
    for orden in (1, 2):
        resultado = comprobar_publico(accion_registro(cliente, 'responder-seguimiento', texto=f'Turno {orden} [vaga]'))
        assert resultado['estado'] == ('PENDIENTE_SEGUIMIENTO' if orden == 1 else 'FINAL')
        assert len(resultado['eventos_registrados']) == (0 if orden == 1 else 1)
        assert registro_demo.contextos[-1].criterios_faltantes_previos == ('C2',)
        assert len(registro_demo.contextos[-1].conversacion.turnos) == orden
    turnos = turnos_guardados(aplicacion)
    assert [t['orden'] for t in turnos] == [1, 2]
    assert all(t['criterios_objetivo'] == ['C2'] and t['respondido_en'] == FECHA for t in turnos)
    assert fila_respuesta(aplicacion)['texto_inicial'] == inicial and fila_respuesta(aplicacion)['ampliada'] is True
    historial = historial_registro(cliente).json()
    assert [e['numero'] for e in historial] == [1, 2, 3] and all(e['origen'] == 'LLM' for e in historial)
    assert len(resultado['conversacion']) == 5


def test_r8_continuar_conserva_pregunta_sin_respuesta(cliente, aplicacion, registro_demo):
    inicial = TEXTO_COMPLETO + '[vaga]'
    primera = comprobar_publico(accion_registro(cliente, 'enviar', item='REG-HAB-2', texto=inicial))
    historial = historial_registro(cliente).json()
    resultado = comprobar_publico(accion_registro(cliente, 'continuar-sin-responder', item='REG-HAB-2'))
    assert resultado['estado'] == 'FINAL' and resultado['conversacion'] == primera['conversacion']
    assert resultado['eventos_registrados'] == resultado['nuevos_desbloqueos'] == []
    assert fila_respuesta(aplicacion, item='REG-HAB-2')['ampliada'] is False
    assert turnos_guardados(aplicacion, item='REG-HAB-2')[0]['respuesta'] is None
    assert historial_registro(cliente).json() == historial and len(registro_demo.contextos) == 1


def test_r9_adecuada_y_r12_atencion_solo_en_auditoria(cliente, aplicacion, registro_demo):
    for item, marcador, atencion in [('REG-HAB-3', '', False), ('REG-HAB-1', '[atencion]', True)]:
        resultado = comprobar_publico(accion_registro(cliente, 'enviar', item=item, texto=TEXTO_COMPLETO + marcador))
        assert resultado['estado'] == 'FINAL' and len(resultado['conversacion']) == 1
        assert len(resultado['eventos_registrados']) == 1 and turnos_guardados(aplicacion, item=item) == []
        fila = fila_respuesta(aplicacion, item=item)
        assert fila['clasificacion_inicial'] == 'ADECUADA' and fila['ampliada'] is False
        evaluacion = historial_registro(cliente).json()[-1]
        assert evaluacion['origen'] == 'LLM' and evaluacion['requiere_atencion'] is atencion
        assert evaluacion['version_prompt'] == 'v2' and evaluacion['latencia_ms'] >= 0
    comprobar_publico(estado_registro(cliente))


def test_r10_contexto_solo_finales_con_turnos_de_otros_items_y_misma_cuenta(cliente, registro_demo):
    assert accion_registro(cliente, 'enviar', cuenta='est-luis').status_code == 200
    assert accion_registro(cliente, 'enviar', item='REG-HAB-3', texto='Pendiente [vaga]').status_code == 200
    primera = accion_registro(cliente, 'enviar', texto=TEXTO_COMPLETO + '[falta:C2]').json()
    assert accion_registro(cliente, 'responder-seguimiento', texto='El jueves').status_code == 200
    assert accion_registro(cliente, 'enviar', item='REG-HAB-2').status_code == 200
    contexto = registro_demo.contextos[-1]
    assert contexto.titulo_actividad == 'Mi plan para fortalecer una habilidad' and contexto.consigna == '¿Qué harás para practicarla?'
    assert [(c.codigo, c.descripcion) for c in contexto.criterios] == [
        ('C1', 'Describe una acción que puede realizar, no solo una intención general como "esforzarme" o "mejorar".'),
        ('C2', 'Indica dónde, cuándo o con quién la realizará.')]
    assert len(contexto.respuestas_anteriores) == 1
    anterior = contexto.respuestas_anteriores[0]
    assert anterior.consigna == '¿Qué habilidad social quieres fortalecer y por qué?'
    assert anterior.conversacion.texto_inicial == TEXTO_COMPLETO + '[falta:C2]'
    assert [(t.pregunta, t.respuesta) for t in anterior.conversacion.turnos] == [(primera['conversacion'][1]['texto'], 'El jueves')]
    assert contexto.conversacion.texto_inicial == TEXTO_COMPLETO
    assert 'est-ana' not in repr(contexto) and 'Ana' not in repr(contexto) and 'est-luis' not in repr(contexto)


def test_r11_fallo_inicial_y_fallo_seguimiento_no_bloquean(cliente, aplicacion, registro_demo):
    resultado = comprobar_publico(accion_registro(cliente, 'enviar', texto=TEXTO_COMPLETO + '[falla]'))
    assert resultado['estado'] == 'FINAL' and resultado['eventos_registrados'] == []
    evaluacion = historial_registro(cliente).json()[0]
    assert evaluacion['origen'] == 'RESPALDO_LONGITUD' and evaluacion['clasificacion'] == 'NO_EVALUADA'
    assert evaluacion['error'] == 'Falló el evaluador de respuestas'
    assert fila_respuesta(aplicacion)['clasificacion_inicial'] == 'NO_EVALUADA'
    assert accion_registro(cliente, 'enviar', item='REG-HAB-2', texto='Inicial [vaga]').status_code == 200
    resultado = comprobar_publico(accion_registro(cliente, 'responder-seguimiento', item='REG-HAB-2', texto='[falla]'))
    assert resultado['estado'] == 'FINAL' and len(resultado['eventos_registrados']) == 1
    assert fila_respuesta(aplicacion, item='REG-HAB-2')['ampliada'] is True
    assert len(turnos_guardados(aplicacion, item='REG-HAB-2')) == 1
    assert historial_registro(cliente).json()[-1]['clasificacion'] == 'NO_EVALUADA'


@pytest.mark.parametrize('primer_texto', [TEXTO_COMPLETO, 'Corto [falla]', TEXTO_COMPLETO + '[falla]'])
def test_r13d_edicion_final_sin_cambiar_auditoria_ni_metricas(cliente, aplicacion, registro_demo, primer_texto):
    assert accion_registro(cliente, 'enviar', texto=primer_texto).status_code == 200
    if primer_texto == 'Corto [falla]':
        assert accion_registro(cliente, 'responder-seguimiento').status_code == 200
    fila = fila_respuesta(aplicacion)
    antes = historial_registro(cliente).json()
    llamadas = len(registro_demo.contextos)
    resultado = comprobar_publico(accion_registro(cliente, 'enviar', texto='Edición breve [falla]'))
    assert resultado['estado'] == 'FINAL' and resultado['eventos_registrados'] == []
    despues = fila_respuesta(aplicacion)
    for campo in ('primer_texto_evaluado', 'clasificacion_inicial', 'ampliada', 'creada_en'):
        assert despues[campo] == fila[campo]
    assert despues['texto_inicial'] == 'Edición breve [falla]' and despues['actualizada_en'] > fila['actualizada_en']
    if primer_texto == 'Corto [falla]':
        turnos = turnos_guardados(aplicacion)
        resultado = comprobar_publico(accion_registro(cliente, 'responder-seguimiento', orden=1, texto='Turno editado [vaga]'))
        assert resultado['estado'] == 'FINAL' and resultado['eventos_registrados'] == []
        editado = turnos_guardados(aplicacion)[0]
        assert editado['respuesta'] == 'Turno editado [vaga]'
        for campo in ('pregunta', 'criterios_objetivo', 'creado_en', 'respondido_en'):
            assert editado[campo] == turnos[0][campo]
    assert historial_registro(cliente).json() == antes and len(registro_demo.contextos) == llamadas
    antes = fotografia(aplicacion)
    assert accion_registro(cliente, 'guardar-borrador').status_code == 409
    assert fotografia(aplicacion) == antes


class EvaluadorInterviene(EvaluadorFalso):
    def __init__(self, intervencion):
        super().__init__()
        self.intervencion = intervencion
        self.intervino = False

    def evaluar(self, contexto):
        if not self.intervino:
            self.intervino = True
            self.intervencion()
        return super().evaluar(contexto)


@pytest.mark.parametrize('estado_previo', ['ausente', 'borrador', 'pendiente'])
@pytest.mark.parametrize('cambio', ['borrador', 'envio'])
def test_r14_concurrencia_descarta_toda_evaluacion_incluso_fecha_igual(
        cliente, aplicacion, registro_demo, estado_previo, cambio):
    if estado_previo == 'borrador':
        assert accion_registro(cliente, 'guardar-borrador', texto='Previo').status_code == 200
    elif estado_previo == 'pendiente':
        assert accion_registro(cliente, 'enviar', texto='Previo [vaga]').status_code == 200
    historial_antes = historial_registro(cliente).json()
    paralelo = TEXTO_COMPLETO + ' guardado en paralelo'
    def intervenir():
        accion = 'responder-seguimiento' if estado_previo == 'pendiente' else 'enviar'
        respuesta = accion_registro(cliente, 'guardar-borrador' if cambio == 'borrador' else accion, texto=paralelo)
        assert respuesta.status_code == 200, respuesta.text
    aplicacion.state.evaluador_respuestas = EvaluadorInterviene(intervenir)
    respuesta = accion_registro(cliente, 'responder-seguimiento' if estado_previo == 'pendiente' else 'enviar',
                                texto=TEXTO_COMPLETO + ' original')
    assert respuesta.status_code == 409
    if estado_previo == 'pendiente':
        assert fila_respuesta(aplicacion)['texto_inicial'] == 'Previo [vaga]'
        assert turnos_guardados(aplicacion)[0]['respuesta'] == paralelo
    else:
        assert fila_respuesta(aplicacion)['texto_inicial'] == paralelo
    historial = historial_registro(cliente).json()
    assert historial[:len(historial_antes)] == historial_antes
    if cambio == 'borrador':
        assert historial == historial_antes
    else:
        assert len(historial) == len(historial_antes) + 1
        evaluado = json.loads(historial[-1]['texto_evaluado'])
        assert (evaluado['turnos'][-1]['respuesta'] if estado_previo == 'pendiente' else evaluado['texto_inicial']) == paralelo
    assert all(' original' not in e['texto_evaluado'] for e in historial)


@pytest.mark.parametrize('seguimiento', [False, True])
def test_r15_sin_sesiones_transacciones_ni_conexiones_en_evaluacion(
        cliente, aplicacion, registro_demo, monkeypatch, seguimiento):
    if seguimiento:
        assert accion_registro(cliente, 'enviar', texto='Inicial [vaga]').status_code == 200
    sesiones = []
    fabrica = aplicacion.state.fabrica_sesiones
    iniciar_original = fabrica.class_.begin
    def iniciar(sesion, *args, **opciones):
        sesiones.append(sesion)
        return iniciar_original(sesion, *args, **opciones)
    monkeypatch.setattr(fabrica.class_, 'begin', iniciar)
    def comprobar():
        assert sesiones and not any(sesion.in_transaction() for sesion in sesiones)
        assert all(not sesion.is_active or sesion.get_transaction() is None for sesion in sesiones)
        assert aplicacion.state.motor_bd.pool.checkedout() == 0
    evaluador = EvaluadorInterviene(comprobar)
    aplicacion.state.evaluador_respuestas = evaluador
    assert accion_registro(cliente, 'responder-seguimiento' if seguimiento else 'enviar').status_code == 200
    assert evaluador.intervino and len(evaluador.contextos) == 1
    assert len(sesiones) == 2 and sesiones[0] is not sesiones[1]


def test_r16_aislamiento_posiciones_respuestas_y_evaluaciones(cliente, registro_demo):
    assert cliente.post('/acciones/guardar-posicion', json={
        'cuenta': 'est-ana', 'actividad': 'REG-ACT08', 'posicion': 'plan'}).status_code == 200
    assert accion_registro(cliente, 'enviar', texto='Corto Ana').status_code == 200
    assert accion_registro(cliente, 'guardar-borrador', item='REG-HAB-2', texto='Borrador Ana').status_code == 200
    assert estado_registro(cliente, cuenta='est-luis').json() == {'posicion': None, 'estado': None, 'respuestas': []}
    assert historial_registro(cliente, cuenta='est-luis').json() == []
    assert cliente.post('/acciones/guardar-posicion', json={
        'cuenta': 'est-luis', 'actividad': 'REG-ACT08', 'posicion': 'explicacion'}).status_code == 200
    assert accion_registro(cliente, 'enviar', texto=TEXTO_COMPLETO + ' Luis', cuenta='est-luis').status_code == 200
    assert estado_registro(cliente).json()['posicion'] == 'plan'
    assert estado_registro(cliente, cuenta='est-luis').json()['posicion'] == 'explicacion'
    assert len(historial_registro(cliente).json()) == len(historial_registro(cliente, cuenta='est-luis').json()) == 1
    assert 'Ana' not in estado_registro(cliente, cuenta='est-luis').text
    assert 'Luis' not in historial_registro(cliente).text


@pytest.mark.parametrize('item,minimo', [('REG-HAB-1', 40), ('REG-HAB-3', 30)])
@pytest.mark.parametrize('diferencia', [-1, 0, 1])
def test_envio_limites_exactos_y_preserva_espacios(cliente, registro_demo, item, minimo, diferencia):
    texto = '  ' + 'á' * (minimo + diferencia) + '\n'
    assert accion_registro(cliente, 'guardar-borrador', item=item, texto='borrador previo').status_code == 200
    resultado = comprobar_publico(accion_registro(cliente, 'enviar', item=item, texto=texto))
    evaluacion = historial_registro(cliente).json()[0]
    assert evaluacion['origen'] == 'LLM' and resultado['estado'] == 'FINAL'
    assert json.loads(evaluacion['texto_evaluado']) == dict(texto_inicial=texto, turnos=[])
    assert estado_registro(cliente).json()['respuestas'][0]['conversacion'] == mensajes_iniciales(texto)
    assert len(registro_demo.contextos) == 1


@pytest.mark.parametrize('texto', ['', ' \t\n', '\u2003\u00a0'])
@pytest.mark.parametrize('previo', ['ausente', 'final'])
def test_envio_vacio_422_sin_escrituras(cliente, aplicacion, registro_demo, texto, previo):
    if previo == 'final':
        assert accion_registro(cliente, 'enviar').status_code == 200
    antes = fotografia(aplicacion)
    llamadas = len(registro_demo.contextos)
    assert accion_registro(cliente, 'enviar', texto=texto).status_code == 422
    assert fotografia(aplicacion) == antes and len(registro_demo.contextos) == llamadas


def test_borrador_vacio_es_valido_sin_evaluar(cliente, registro_demo):
    assert accion_registro(cliente, 'guardar-borrador', texto='').status_code == 200
    assert estado_registro(cliente).json()['respuestas'][0]['conversacion'] == mensajes_iniciales('')
    assert registro_demo.contextos == []


@pytest.mark.parametrize('origen', ['generico', 'llm'])
def test_r13_borrador_de_turno_conserva_texto_inicial_pregunta_e_historial(cliente, aplicacion, registro_demo, origen):
    inicial = 'Corto [falla]' if origen == 'generico' else 'Inicial [vaga]'
    primera = accion_registro(cliente, 'enviar', texto=inicial).json()
    historial = historial_registro(cliente).json()
    fila = fila_respuesta(aplicacion)
    assert accion_registro(cliente, 'guardar-borrador', texto='Borrador para ampliar').json()['estado'] == 'PENDIENTE_SEGUIMIENTO'
    guardado = estado_registro(cliente).json()['respuestas'][0]
    assert guardado['conversacion'] == primera['conversacion'] + [
        dict(tipo='respuesta', orden=1, texto='Borrador para ampliar', borrador=True)]
    assert turnos_guardados(aplicacion)[0]['respondido_en'] is None
    despues = fila_respuesta(aplicacion)
    assert despues['actualizada_en'] > fila['actualizada_en']
    assert despues['texto_inicial'] == despues['primer_texto_evaluado'] == inicial
    assert despues['clasificacion_inicial'] == 'VAGA' and despues['ampliada'] is False
    assert historial_registro(cliente).json() == historial and len(registro_demo.contextos) == 1
    assert accion_registro(cliente, 'responder-seguimiento', texto='Envío definitivo').json()['estado'] == 'FINAL'
    assert [e['numero'] for e in historial_registro(cliente).json()] == ([1] if origen == 'generico' else [1, 2])


@pytest.mark.parametrize('segundo,origen,clasificacion', [
    (TEXTO_COMPLETO + '[vaga]', 'LLM', 'VAGA'),
    (TEXTO_COMPLETO + '[falla]', 'RESPALDO_LONGITUD', 'NO_EVALUADA'),
    ('Breve', 'LLM', 'ADECUADA'),
    (TEXTO_COMPLETO + '[atencion]', 'LLM', 'ADECUADA'),
])
def test_segundo_turno_siempre_final_sin_tercera_pregunta(
        cliente, aplicacion, registro_demo, segundo, origen, clasificacion):
    assert accion_registro(cliente, 'enviar', texto='Primer envío [vaga]').status_code == 200
    assert accion_registro(cliente, 'responder-seguimiento', texto='Turno 1 [vaga]').json()['estado'] == 'PENDIENTE_SEGUIMIENTO'
    primera = historial_registro(cliente).json()[0]
    resultado = comprobar_publico(accion_registro(cliente, 'responder-seguimiento', texto=segundo))
    assert resultado['estado'] == 'FINAL' and len(resultado['conversacion']) == 5
    assert resultado['eventos_registrados'] == [{
        'tipo': 'RESPUESTA_REFLEXIVA', 'referencia': None, 'fecha_hora': FECHA.isoformat()}]
    fila = fila_respuesta(aplicacion)
    assert fila['ampliada'] is True and fila['clasificacion_inicial'] == 'VAGA'
    assert fila['texto_inicial'] == fila['primer_texto_evaluado'] == 'Primer envío [vaga]'
    historial = historial_registro(cliente).json()
    assert historial[0] == primera
    assert (historial[2]['numero'], historial[2]['origen'], historial[2]['clasificacion']) == (3, origen, clasificacion)
    assert len(turnos_guardados(aplicacion)) == 2


@pytest.mark.parametrize('estado', ['ausente', 'borrador', 'final'])
def test_continuar_rechaza_estados_sin_repregunta(cliente, aplicacion, registro_demo, estado):
    if estado != 'ausente':
        assert accion_registro(cliente, 'guardar-borrador' if estado == 'borrador' else 'enviar').status_code == 200
    antes = fotografia(aplicacion)
    assert accion_registro(cliente, 'continuar-sin-responder').status_code == 409
    assert fotografia(aplicacion) == antes


@pytest.mark.parametrize('accion', ['guardar-borrador', 'enviar', 'responder-seguimiento', 'continuar-sin-responder', 'guardar-posicion'])
@pytest.mark.parametrize('cambio,valor,estado', [
    ('cuenta', 'apo-rosa', 404), ('cuenta', 'no-existe', 404),
    ('actividad', 'no-existe', 404), ('actividad', 'ACT-05', 409),
])
def test_acciones_registro_validan_cuenta_y_disponibilidad_sin_escrituras(
        cliente, aplicacion, registro_demo, accion, cambio, valor, estado):
    antes = fotografia(aplicacion)
    if accion == 'guardar-posicion':
        respuesta = cliente.post('/acciones/guardar-posicion', json={
            'cuenta': 'est-ana', 'actividad': 'REG-ACT08', 'posicion': 'plan', cambio: valor})
    else:
        respuesta = accion_registro(cliente, accion, **{cambio: valor})
    assert respuesta.status_code == estado, respuesta.text
    assert fotografia(aplicacion) == antes and registro_demo.contextos == []


@pytest.mark.parametrize('accion', ['guardar-borrador', 'enviar', 'responder-seguimiento', 'continuar-sin-responder'])
@pytest.mark.parametrize('actividad,item', [('REG-ACT08', 'NO-EXISTE'), ('ACT-01', 'REG-HAB-1')])
def test_acciones_registro_rechazan_items_ajenos(cliente, aplicacion, registro_demo, accion, actividad, item):
    antes = fotografia(aplicacion)
    assert accion_registro(cliente, accion, item=item, actividad=actividad).status_code == 409
    assert fotografia(aplicacion) == antes and registro_demo.contextos == []


def test_consultas_registro_404_y_lectura_de_actividades_sin_items(cliente, aplicacion, registro_demo):
    antes = fotografia(aplicacion)
    for consultar in (estado_registro, historial_registro):
        assert consultar(cliente, cuenta='no-existe').status_code == 404
        assert consultar(cliente, actividad='no-existe').status_code == 404
    assert cliente.get('/actividades/no-existe/items-registro').status_code == 404
    assert cliente.get('/actividades/ACT-05/items-registro').json() == []  # No exige disponibilidad para leer.
    assert estado_registro(cliente, actividad='ACT-05').json() == {'posicion': None, 'estado': None, 'respuestas': []}
    definiciones = aplicacion.state.motor_bd.cache_definiciones.actual
    bloques_apoderado = {b.id for b in definiciones.listar(modelos.Bloque) if b.audiencia.value == 'APODERADO'}
    actividad = next(a.codigo for a in definiciones.listar(modelos.Actividad) if a.bloque_id in bloques_apoderado)
    for ruta in (f'/actividades/{actividad}/items-registro',
                 f'/cuentas/est-ana/actividades/{actividad}/registro',
                 f'/demo/registro/est-ana/{actividad}/evaluaciones'):
        assert cliente.get(ruta).status_code == 404
    assert fotografia(aplicacion) == antes


@pytest.mark.parametrize('fallo', ['timeout', 'inconsistente', 'criterio_ajeno', 'excepcion'])
def test_evaluacion_invalida_o_timeout_finaliza_con_error_saneado(
        cliente, aplicacion, registro_demo, fallo):
    secreto_prueba = 'SECRETO_SIMULADO_NO_REAL'
    class EvaluadorResultadoInvalido(EvaluadorFalso):
        def evaluar(self, contexto):
            self.contextos.append(contexto)
            if fallo == 'timeout':
                raise TimeoutError(secreto_prueba)
            if fallo == 'excepcion':
                raise RuntimeError(secreto_prueba)
            return ResultadoEvaluacion.model_construct(clasificacion='ADECUADA',
                criterios_faltantes=['C1' if fallo == 'inconsistente' else secreto_prueba],
                pregunta=None, requiere_atencion=False)
    evaluador = EvaluadorResultadoInvalido()
    aplicacion.state.evaluador_respuestas = evaluador
    resultado = comprobar_publico(accion_registro(cliente, 'enviar'))
    assert resultado['estado'] == 'FINAL' and resultado['eventos_registrados'] == []
    historial = historial_registro(cliente)
    assert secreto_prueba not in historial.text
    evaluacion = historial.json()[0]
    assert evaluacion['origen'] == 'RESPALDO_LONGITUD' and evaluacion['clasificacion'] == 'NO_EVALUADA'
    assert evaluacion['error'] and evaluacion['pregunta_generada'] is None
    assert len(evaluador.contextos) == 1


def test_marca_concurrencia_monotonica_con_reloj_y_fecha_simulada_iguales(
        cliente, aplicacion, registro_demo, monkeypatch):
    from app.services.registro import acciones as acciones_registro
    class RelojFijo(datetime):
        @classmethod
        def now(cls, tz=None):
            return FECHA.replace(tzinfo=tz)
    monkeypatch.setattr(acciones_registro, 'datetime', RelojFijo)
    assert accion_registro(cliente, 'guardar-borrador').status_code == 200
    marca = fila_respuesta(aplicacion)['actualizada_en']
    for _ in range(3):
        assert accion_registro(cliente, 'guardar-borrador').status_code == 200
        siguiente = fila_respuesta(aplicacion)['actualizada_en']
        assert (siguiente - marca).total_seconds() == 0.000001
        marca = siguiente
    def cambiar():
        assert accion_registro(cliente, 'guardar-borrador', texto='Cambio paralelo').status_code == 200
    aplicacion.state.evaluador_respuestas = EvaluadorInterviene(cambiar)
    assert accion_registro(cliente, 'enviar').status_code == 409
    assert fila_respuesta(aplicacion)['texto_inicial'] == 'Cambio paralelo'
    assert historial_registro(cliente).json() == []


def test_comparacion_condicional_protege_relectura_hasta_escritura(cliente, aplicacion, registro_demo, monkeypatch):
    from app.services.registro import acciones as acciones_registro
    assert accion_registro(cliente, 'guardar-borrador', texto='Borrador inicial').status_code == 200
    comprobar_original = acciones_registro.comprobar_cambio
    def modificar_despues_de_releer(sesion, respuesta, valores):
        with aplicacion.state.fabrica_sesiones.begin() as otra:
            otra.execute(modelos.RespuestaRegistro.__table__.update().where(
                modelos.RespuestaRegistro.id == respuesta.id).values(texto_inicial='Cambio después de relectura',
                    actualizada_en=acciones_registro.marca_actualizacion(respuesta.actualizada_en)))
        return comprobar_original(sesion, respuesta, valores)
    monkeypatch.setattr(acciones_registro, 'comprobar_cambio', modificar_despues_de_releer)
    assert accion_registro(cliente, 'enviar').status_code == 409
    assert fila_respuesta(aplicacion)['texto_inicial'] == 'Cambio después de relectura'
    assert historial_registro(cliente).json() == []


@pytest.mark.parametrize('estado_previo', ['ausente', 'borrador', 'pendiente'])
@pytest.mark.parametrize('tabla_falla', ['evaluacion_respuesta', 'evento_uso', 'desbloqueo'])
def test_error_sql_revierte_respuesta_evaluacion_eventos_y_desbloqueos(
        cliente, aplicacion, registro_demo, estado_previo, tabla_falla):
    for _ in range(2):
        assert cliente.post('/acciones/responder-registro', json={
            'cuenta': 'est-ana', 'clasificacion': 'ADECUADA', 'ampliada': False}).status_code == 200
    if estado_previo != 'ausente':
        assert accion_registro(cliente, 'guardar-borrador' if estado_previo == 'borrador' else 'enviar', texto='Previo [vaga]').status_code == 200
    antes = fotografia(aplicacion)
    def provocar_fallo(conexion, cursor, sentencia, parametros, contexto_sql, muchos):
        if sentencia.startswith(f'INSERT INTO {tabla_falla} '):
            raise IntegrityError('Fallo SQL simulado', {}, Exception('Detalle interno'))
    event.listen(aplicacion.state.motor_bd, 'after_cursor_execute', provocar_fallo)
    try:
        respuesta = accion_registro(cliente, 'responder-seguimiento' if estado_previo == 'pendiente' else 'enviar')
    finally:
        event.remove(aplicacion.state.motor_bd, 'after_cursor_execute', provocar_fallo)
    assert respuesta.status_code == 409 and 'Detalle interno' not in respuesta.text
    assert fotografia(aplicacion) == antes


def test_envio_reconstruye_contexto_entre_transacciones(cliente, aplicacion, registro_demo, monkeypatch):
    from app.services.registro import acciones as acciones_registro
    from app.core.contexto import contexto
    capturados = []
    validar_original = acciones_registro.validar_registro
    def capturar(sesion, *args, **opciones):
        capturados.append(contexto(sesion))
        return validar_original(sesion, *args, **opciones)
    monkeypatch.setattr(acciones_registro, 'validar_registro', capturar)
    def agregar_eventos():
        for _ in range(2):
            assert cliente.post('/acciones/responder-registro', json={
                'cuenta': 'est-ana', 'clasificacion': 'ADECUADA', 'ampliada': False}).status_code == 200
    aplicacion.state.evaluador_respuestas = EvaluadorInterviene(agregar_eventos)
    resultado = accion_registro(cliente, 'enviar')
    assert resultado.status_code == 200
    assert len(capturados) == 2 and capturados[0] is not capturados[1]
    assert capturados[0].sesion is not capturados[1].sesion
    assert any(d['objetivo']['codigo'] == 'LOG-PENSADOR' for d in resultado.json()['nuevos_desbloqueos'])


def test_posiciones_permanecen_tras_reinicio(cliente, aplicacion, registro_demo, tmp_path, monkeypatch):
    posiciones = aplicacion.state.posiciones_registro
    contenido_alterado(tmp_path, monkeypatch, 'faltante')
    assert cliente.post('/demo/reiniciar').status_code == 200
    assert aplicacion.state.posiciones_registro is posiciones
    ruta = contenido_registro.RUTA_CONTENIDO_REGISTRO
    documento = json.loads(ruta.read_text(encoding='utf-8'))
    documento['momentos'][1]['items'] = CODIGOS_ITEMS
    documento['momentos'][1]['id'] = 'nuevo-plan'
    ruta.write_text(json.dumps(documento, ensure_ascii=False), encoding='utf-8')
    assert cliente.post('/demo/reiniciar').status_code == 200
    assert aplicacion.state.posiciones_registro is posiciones
    datos = dict(cuenta='est-ana', actividad='REG-ACT08', posicion='plan')
    assert cliente.post('/acciones/guardar-posicion', json=datos).status_code == 200
    assert cliente.post('/acciones/guardar-posicion', json={**datos, 'posicion': 'nuevo-plan'}).status_code == 422


def test_orden_de_respuestas_por_item_y_evaluaciones_por_insercion(cliente, registro_demo):
    for item in reversed(CODIGOS_ITEMS):
        assert accion_registro(cliente, 'enviar', item=item, texto='Corto [falla]').status_code == 200
    assert [r['item'] for r in estado_registro(cliente).json()['respuestas']] == CODIGOS_ITEMS
    assert [e['item'] for e in historial_registro(cliente).json()] == list(reversed(CODIGOS_ITEMS))


def test_registro_se_recupera_despues_de_reabrir_aplicacion(cliente, aplicacion, registro_demo):
    assert cliente.post('/acciones/guardar-posicion', json={
        'cuenta': 'est-ana', 'actividad': 'REG-ACT08', 'posicion': 'plan'}).status_code == 200
    assert accion_registro(cliente, 'enviar', texto='Corto [falla]').status_code == 200
    assert accion_registro(cliente, 'guardar-borrador', texto='Ampliación aún no enviada').status_code == 200
    registro = estado_registro(cliente).json()
    historial = historial_registro(cliente).json()
    nueva = crear_aplicacion(str(aplicacion.state.motor_bd.url))
    with TestClient(nueva) as otro_cliente:
        assert estado_registro(otro_cliente).json() == registro
        assert historial_registro(otro_cliente).json() == historial


def test_guardar_posicion_y_editar_preservan_progreso_completado(cliente, aplicacion, registro_demo):
    assert accion_registro(cliente, 'enviar').status_code == 200
    with aplicacion.state.fabrica_sesiones.begin() as sesion:
        progreso = sesion.scalar(select(modelos.ProgresoActividad))
        progreso.estado = modelos.EstadoProgreso.COMPLETADA
    respuesta = cliente.post('/acciones/guardar-posicion', json={
        'cuenta': 'est-ana', 'actividad': 'REG-ACT08', 'posicion': 'plan'})
    assert respuesta.json() == {'posicion': 'plan', 'estado': 'COMPLETADA'}
    assert accion_registro(cliente, 'enviar', texto='Respuesta editada').status_code == 200
    assert estado_registro(cliente).json()['estado'] == 'COMPLETADA'


def completar_registro(cliente, **cambios):
    return cliente.post('/acciones/completar-actividad', json={
        'cuenta': 'est-ana', 'actividad': 'REG-ACT08', 'fecha_hora': FECHA.isoformat(), **cambios})


def test_r11_borrador_impide_completar_y_finales_completan_actividad_y_bloque(
        cliente, aplicacion, registro_demo, contador_consultas):
    for item in CODIGOS_ITEMS[:2]:
        assert accion_registro(cliente, 'enviar', item=item).status_code == 200
    assert accion_registro(cliente, 'guardar-borrador', item='REG-HAB-3').status_code == 200
    antes = fotografia(aplicacion)
    with contador_consultas(aplicacion.state.motor_bd) as contador:
        rechazada = completar_registro(cliente)
    assert rechazada.status_code == 409
    assert rechazada.json()['detail'] == {
        'mensaje': 'Faltan ítems de registro por finalizar', 'items_faltantes': ['REG-HAB-3']}
    assert all(e.sentencia.lstrip().upper().startswith('SELECT') for e in contador.ejecuciones)
    assert fotografia(aplicacion) == antes
    assert accion_registro(cliente, 'enviar', item='REG-HAB-3').status_code == 200
    llamadas = len(registro_demo.contextos)
    resultado = comprobar_publico(completar_registro(cliente))
    assert resultado['eventos_registrados'] == [
        {'tipo': 'COMPLETA_ACTIVIDAD', 'referencia': 'REG-ACT08', 'fecha_hora': FECHA.isoformat()},
        {'tipo': 'COMPLETA_BLOQUE', 'referencia': 'REG', 'fecha_hora': FECHA.isoformat()},
    ]
    assert resultado['resultados_generados'] == [] and len(registro_demo.contextos) == llamadas
    registro = estado_registro(cliente).json()
    assert registro['estado'] == 'COMPLETADA'
    assert [r['estado'] for r in registro['respuestas']] == ['FINAL'] * 3
    bloques = cliente.get('/cuentas/est-ana/estado').json()['bloques']
    assert next(b for b in bloques if b['codigo'] == 'REG')['actividades'][0]['estado'] == 'COMPLETADA'


def test_r12_tres_reflexivas_desbloquean_pensador_sin_cambiar_reglas(cliente, aplicacion, registro_demo):
    antes = fotografia(aplicacion)
    regla = next(r for r in cliente.get('/reglas').json() if r['regla'] == 'R-LOG-PENSADOR')
    assert regla['condiciones'] == [{
        'tipo_evento': 'RESPUESTA_REFLEXIVA', 'referencia': None, 'tipo_conteo': 'EVENTOS', 'cantidad_minima': 3}]
    for numero, item in enumerate(CODIGOS_ITEMS, start=1):
        resultado = comprobar_publico(accion_registro(cliente, 'enviar', item=item))
        assert resultado['eventos_registrados'] == [{
            'tipo': 'RESPUESTA_REFLEXIVA', 'referencia': None, 'fecha_hora': FECHA.isoformat()}]
        logros = [d for d in resultado['nuevos_desbloqueos'] if d['objetivo']['codigo'] == 'LOG-PENSADOR']
        assert len(logros) == (1 if numero == 3 else 0)
        if logros:
            assert logros[0]['regla'] == 'R-LOG-PENSADOR'
            assert logros[0]['condiciones'] == [{
                'tipo_evento': 'RESPUESTA_REFLEXIVA', 'referencia': None, 'tipo_conteo': 'EVENTOS',
                'actual': 3, 'requerido': 3, 'cumplida': True}]
        with aplicacion.state.fabrica_sesiones() as sesion:
            eventos = list(sesion.scalars(select(modelos.EventoUso)))
            assert len(eventos) == numero
            assert all(e.tipo == 'RESPUESTA_REFLEXIVA' and e.id_referencia is None for e in eventos)
        assert fila_respuesta(aplicacion, item=item)['clasificacion_inicial'] == 'ADECUADA'
    historial = historial_registro(cliente).json()
    assert len(historial) == 3 and all(e['numero'] == 1 and e['origen'] == 'LLM' for e in historial)
    despues = fotografia(aplicacion)
    for tabla in ('regla_desbloqueo', 'condicion_desbloqueo'):
        assert despues[tabla] == antes[tabla]
    assert len(despues['desbloqueo']) == 1
    insignias = cliente.get('/cuentas/est-ana/estado').json()['insignias']
    assert next(i for i in insignias if i['codigo'] == 'LOG-PENSADOR')['estado'] == 'OBTENIDA'


@pytest.mark.parametrize('estado', ['ausente', 'borrador', 'pendiente'])
def test_completar_registro_rechaza_respuestas_no_finales_sin_escrituras(
        cliente, aplicacion, registro_demo, contador_consultas, estado):
    if estado != 'ausente':
        for item in reversed(CODIGOS_ITEMS):
            assert accion_registro(cliente, 'guardar-borrador' if estado == 'borrador' else 'enviar',
                                  item=item, texto='Corto [falla]').status_code == 200
    antes = fotografia(aplicacion)
    llamadas = len(registro_demo.contextos)
    with contador_consultas(aplicacion.state.motor_bd) as contador:
        rechazada = completar_registro(cliente)
    assert rechazada.status_code == 409 and rechazada.json()['detail']['items_faltantes'] == CODIGOS_ITEMS
    assert all(e.sentencia.lstrip().upper().startswith('SELECT') for e in contador.ejecuciones)
    assert fotografia(aplicacion) == antes and len(registro_demo.contextos) == llamadas


@pytest.mark.parametrize('forma', ['fallo', 'atencion', 'continuar', 'segundo_fallido'])
def test_completar_admite_finales_sin_exigir_clasificacion_adecuada(
        cliente, aplicacion, registro_demo, forma):
    for item in CODIGOS_ITEMS[:2]:
        assert accion_registro(cliente, 'enviar', item=item).status_code == 200
    if forma in ('continuar', 'segundo_fallido'):
        inicial = 'Inicial [vaga]' if forma == 'segundo_fallido' else 'Corto [falla]'
        assert accion_registro(cliente, 'enviar', item='REG-HAB-3', texto=inicial).status_code == 200
        accion = 'continuar-sin-responder' if forma == 'continuar' else 'responder-seguimiento'
        assert accion_registro(cliente, accion, item='REG-HAB-3', texto=TEXTO_COMPLETO + '[falla]').status_code == 200
    else:
        marcador = '[falla]' if forma == 'fallo' else '[atencion]'
        assert accion_registro(cliente, 'enviar', item='REG-HAB-3', texto=TEXTO_COMPLETO + marcador).status_code == 200
    historial = historial_registro(cliente).json()
    respuestas = [fila_respuesta(aplicacion, item=item) for item in CODIGOS_ITEMS]
    llamadas = len(registro_demo.contextos)
    assert completar_registro(cliente).status_code == 200
    assert estado_registro(cliente).json()['estado'] == 'COMPLETADA'
    assert historial_registro(cliente).json() == historial and len(registro_demo.contextos) == llamadas
    assert [fila_respuesta(aplicacion, item=item) for item in CODIGOS_ITEMS] == respuestas


@pytest.mark.parametrize('estado_opcional', ['ausente', 'borrador', 'pendiente'])
def test_completar_ignora_items_opcionales_no_finales(cliente, aplicacion, registro_demo, estado_opcional):
    # Solo esta base temporal cambia obligatoriedad; la semilla de producción permanece igual.
    with aplicacion.state.fabrica_sesiones.begin() as sesion:
        buscar(sesion, modelos.ItemRegistro, 'REG-HAB-3').obligatorio = False
    for item in CODIGOS_ITEMS[:2]:
        assert accion_registro(cliente, 'enviar', item=item).status_code == 200
    if estado_opcional != 'ausente':
        accion = 'guardar-borrador' if estado_opcional == 'borrador' else 'enviar'
        assert accion_registro(cliente, accion, item='REG-HAB-3', texto='Corto [falla]').status_code == 200
    antes = estado_registro(cliente).json()['respuestas']
    assert completar_registro(cliente).status_code == 200
    assert estado_registro(cliente).json()['respuestas'] == antes


def test_completar_con_todos_los_items_opcionales_no_exige_respuestas(cliente, aplicacion, registro_demo):
    with aplicacion.state.fabrica_sesiones.begin() as sesion:
        sesion.execute(modelos.ItemRegistro.__table__.update().values(obligatorio=False))
    resultado = completar_registro(cliente)
    assert resultado.status_code == 200
    assert [e['tipo'] for e in resultado.json()['eventos_registrados']] == ['COMPLETA_ACTIVIDAD', 'COMPLETA_BLOQUE']
    assert estado_registro(cliente).json() == {'posicion': None, 'estado': 'COMPLETADA', 'respuestas': []}
    assert historial_registro(cliente).json() == [] and registro_demo.contextos == []


def test_faltantes_siguen_el_orden_de_presentacion_y_excluyen_opcionales(cliente, aplicacion, registro_demo):
    with aplicacion.state.fabrica_sesiones.begin() as sesion:
        items = {i.codigo: i for i in sesion.scalars(select(modelos.ItemRegistro))}
        relaciones = {r.item_registro_id: r for r in sesion.scalars(select(modelos.ActividadItemRegistro))}
        for orden, codigo in enumerate(['REG-HAB-3', 'REG-HAB-1', 'REG-HAB-2'], start=1):
            relaciones[items[codigo].id].orden = orden
        items['REG-HAB-2'].obligatorio = False
    antes = fotografia(aplicacion)
    resultado = completar_registro(cliente)
    assert resultado.status_code == 409 and resultado.json()['detail']['items_faltantes'] == ['REG-HAB-3', 'REG-HAB-1']
    assert fotografia(aplicacion) == antes


@pytest.mark.parametrize('cuenta', ['apo-rosa', 'no-existe'])
def test_completar_registro_rechaza_cuenta_no_estudiante_sin_escrituras(
        cliente, aplicacion, registro_demo, cuenta):
    antes = fotografia(aplicacion)
    assert completar_registro(cliente, cuenta=cuenta).status_code == 404
    assert fotografia(aplicacion) == antes


def test_completar_registro_no_usa_finales_de_otra_cuenta(cliente, aplicacion, registro_demo):
    for item in CODIGOS_ITEMS:
        assert accion_registro(cliente, 'enviar', item=item, cuenta='est-luis').status_code == 200
    antes = fotografia(aplicacion)
    resultado = completar_registro(cliente)
    assert resultado.status_code == 409 and resultado.json()['detail']['items_faltantes'] == CODIGOS_ITEMS
    assert fotografia(aplicacion) == antes


def test_completar_registro_no_usa_finales_de_otra_actividad(cliente, aplicacion, registro_demo):
    with aplicacion.state.fabrica_sesiones.begin() as sesion:
        actividad = buscar(sesion, modelos.Actividad, 'ACT-01')
        for orden, codigo in enumerate(CODIGOS_ITEMS, start=1):
            item = buscar(sesion, modelos.ItemRegistro, codigo)
            sesion.add(modelos.ActividadItemRegistro(actividad_id=actividad.id, item_registro_id=item.id, orden=orden))
    for item in CODIGOS_ITEMS:
        assert accion_registro(cliente, 'enviar', item=item, actividad='ACT-01').status_code == 200
    antes = fotografia(aplicacion)
    resultado = completar_registro(cliente)
    assert resultado.status_code == 409 and resultado.json()['detail']['items_faltantes'] == CODIGOS_ITEMS
    assert fotografia(aplicacion) == antes


def test_rehacer_conserva_respuestas_posicion_evaluaciones_y_permite_edicion(cliente, aplicacion, registro_demo):
    assert cliente.post('/acciones/guardar-posicion', json={
        'cuenta': 'est-ana', 'actividad': 'REG-ACT08', 'posicion': 'plan'}).status_code == 200
    for item in CODIGOS_ITEMS:
        assert accion_registro(cliente, 'enviar', item=item).status_code == 200
    respuestas = [fila_respuesta(aplicacion, item=item) for item in CODIGOS_ITEMS]
    historial = historial_registro(cliente).json()
    llamadas = len(registro_demo.contextos)
    for intento in range(2):
        resultado = comprobar_publico(completar_registro(cliente))
        assert [e['tipo'] for e in resultado['eventos_registrados']] == (
            ['COMPLETA_ACTIVIDAD', 'COMPLETA_BLOQUE'] if intento == 0 else ['COMPLETA_ACTIVIDAD'])
        assert resultado['nuevos_desbloqueos'] == [] and resultado['resultados_generados'] == []
        assert [fila_respuesta(aplicacion, item=item) for item in CODIGOS_ITEMS] == respuestas
        assert historial_registro(cliente).json() == historial and estado_registro(cliente).json()['posicion'] == 'plan'
    edicion = comprobar_publico(accion_registro(cliente, 'enviar', texto='Edición breve [falla]'))
    assert edicion['estado'] == 'FINAL' and edicion['eventos_registrados'] == []
    editada = fila_respuesta(aplicacion)
    assert editada['texto_inicial'] == 'Edición breve [falla]' and editada['actualizada_en'] > respuestas[0]['actualizada_en']
    for campo in ('clasificacion_inicial', 'primer_texto_evaluado', 'ampliada', 'creada_en'):
        assert editada[campo] == respuestas[0][campo]
    assert len(registro_demo.contextos) == llamadas and historial_registro(cliente).json() == historial
    assert completar_registro(cliente).json()['eventos_registrados'] == [{
        'tipo': 'COMPLETA_ACTIVIDAD', 'referencia': 'REG-ACT08', 'fecha_hora': FECHA.isoformat()}]
    assert fila_respuesta(aplicacion) == editada
    with aplicacion.state.fabrica_sesiones() as sesion:
        eventos = list(sesion.scalars(select(modelos.EventoUso)))
        assert sum(e.tipo == 'RESPUESTA_REFLEXIVA' for e in eventos) == 3
        assert sum(e.tipo == 'COMPLETA_ACTIVIDAD' for e in eventos) == 3
        assert sum(e.tipo == 'COMPLETA_BLOQUE' for e in eventos) == 1
        assert sesion.scalar(select(func.count()).select_from(modelos.Desbloqueo)) == 1
