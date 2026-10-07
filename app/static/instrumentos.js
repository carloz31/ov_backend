"use strict";

const buscar = (id) => document.getElementById(id);
const laboratorio = { cuentas: [], catalogo: [], avance: [], estado: null, cuenta: "",
  instrumento: "", aplicacion: "", actividad: "", items: [],
  ocupado: false, borradores: new Map(), cadenas: new Map(), reinicio: null };
const cadenas_riasec = {
  "Cadena A": "511222115515411122551525542552114321231141335215514152553521",
  "Cadena B": "333322223322343333233333443333333333444433333433444433334433",
  "Perfil plano": "3".repeat(60),
};
// Ejemplos de la demo; las características y validaciones se leen de la API.
const ejemplos_instrumentos = {
  "TEST-RIASEC": cadenas_riasec,
  "TEST-INT": { "Impares Sí": Array.from({ length: 43 }, (_, n) => n % 2 ? "2" : "1").join("") },
  "TEST-HAB": { "1–12 Casi siempre": "1".repeat(12) + "2".repeat(12) },
  "TEST-AUTO": { "Entrada de prueba": "BCCDBCACDB", "Salida de prueba": "AABCAACBBA" },
};
const nombres_estados = { NO_INICIADO: "No iniciado", EN_PROGRESO: "En progreso", COMPLETADO: "Completado",
  DISPONIBLE: "Disponible", EN_CURSO: "En curso", COMPLETADA: "Completada", BLOQUEADA: "Bloqueada" };

function elemento(etiqueta, texto = "", clase = "") {
  const nodo = document.createElement(etiqueta);
  nodo.textContent = texto;
  nodo.className = clase;
  return nodo;
}

function bloquear(nodo, bloqueado) {
  nodo.dataset.bloqueado = String(bloqueado);
  nodo.disabled = laboratorio.ocupado || bloqueado;
}

function boton(texto, accion, bloqueado = false, clase = "") {
  const nodo = elemento("button", texto, clase);
  nodo.type = "button";
  bloquear(nodo, bloqueado);
  nodo.addEventListener("click", accion);
  return nodo;
}

function ocupar(ocupado) {
  laboratorio.ocupado = ocupado;
  document.body.setAttribute("aria-busy", String(ocupado));
  for (const nodo of document.querySelectorAll("button,input,select,textarea")) {
    nodo.disabled = ocupado || nodo.dataset.bloqueado === "true";
  }
}

function registrar(ruta, metodo, estado, datos) {
  const entrada = elemento("details");
  entrada.append(elemento("summary", `${metodo} ${ruta} · ${estado}`, estado >= 400 ? "error-consulta" : ""),
    elemento("pre", JSON.stringify(datos, null, 2)));
  buscar("registro").prepend(entrada);
  while (buscar("registro").children.length > 25) buscar("registro").lastElementChild.remove();
}

class ErrorApi extends Error {
  constructor(estado, datos) {
    super(typeof datos.detail === "string" ? datos.detail : datos.detail?.mensaje || `Error HTTP ${estado}`);
    this.estado = estado;
    this.datos = datos;
  }
}

async function solicitar(ruta, cuerpo, visible = false) {
  const metodo = cuerpo === undefined ? "GET" : "POST";
  const respuesta = await fetch(ruta, cuerpo === undefined ? {} : {
    method: metodo, headers: { "Content-Type": "application/json" }, body: JSON.stringify(cuerpo),
  });
  const datos = await respuesta.json();
  if (visible || cuerpo !== undefined || !respuesta.ok) registrar(ruta, metodo, respuesta.status, datos);
  if (!respuesta.ok) throw new ErrorApi(respuesta.status, datos);
  return datos;
}

async function operar(accion) {
  if (laboratorio.ocupado) return;
  ocupar(true);
  buscar("estado-conexion").textContent = "Consultando la plataforma…";
  try {
    await accion();
    buscar("estado-conexion").textContent = `Conectado · ${laboratorio.cuenta}`;
  } catch (error) {
    buscar("estado-conexion").textContent = error.message;
    if (!(error instanceof ErrorApi)) registrar("Interfaz", "ERROR", 0, { mensaje: error.message });
  } finally {
    ocupar(false);
  }
}

const instrumento_actual = () => laboratorio.catalogo.find((i) => i.codigo === laboratorio.instrumento);
const aplicacion_actual = () => instrumento_actual()?.aplicaciones.find((a) => a.codigo === laboratorio.aplicacion);
const avance_actual = () => laboratorio.avance.find((i) => i.instrumento === laboratorio.instrumento)?.aplicaciones.find((a) => a.aplicacion === laboratorio.aplicacion);
const ruta_cuenta = () => `/cuentas/${encodeURIComponent(laboratorio.cuenta)}`;
const clave_actividad = (codigo = laboratorio.actividad) => `${laboratorio.cuenta}|${codigo}`;
const clave_cadena = () => `${laboratorio.cuenta}|${laboratorio.instrumento}|${laboratorio.aplicacion}`;
const fecha_cuerpo = () => {
  const fecha = buscar("fecha").value;
  return fecha ? { fecha_hora: fecha.length === 16 ? `${fecha}:00` : fecha } : {};
};
const actividad_estado = (codigo) => laboratorio.estado?.bloques.flatMap((b) => b.actividades).find((a) => a.codigo === codigo);
const respuestas_fijas = (codigo = laboratorio.actividad) => Boolean(avance_actual()?.hay_resultado_vigente
  || (instrumento_actual()?.tipo_resultado === "COMPARACION" && actividad_estado(codigo)?.estado === "COMPLETADA"));

function insignia_estado(estado) {
  return elemento("span", nombres_estados[estado] || estado, `estado ${estado.toLowerCase()}`);
}

function pintar_navegacion() {
  buscar("instrumentos").replaceChildren(...laboratorio.catalogo.map((instrumento) => {
    const nodo = boton(instrumento.nombre, () => operar(async () => {
      laboratorio.instrumento = instrumento.codigo;
      laboratorio.aplicacion = (instrumento.aplicaciones.find((aplicacion) => aplicacion.momento === "ENTRADA")
        || instrumento.aplicaciones.find((aplicacion) => aplicacion.momento === "UNICA") || instrumento.aplicaciones[0]).codigo;
      laboratorio.actividad = "";
      await pintar_seleccion();
    }), !laboratorio.estado || laboratorio.estado.cuenta.rol !== "ESTUDIANTE", `nav${instrumento.codigo === laboratorio.instrumento ? " activo" : ""}`);
    nodo.append(elemento("small", instrumento.codigo));
    if (instrumento.codigo === laboratorio.instrumento) nodo.setAttribute("aria-current", "page");
    return nodo;
  }));
}

async function actualizar() {
  const [estado, avance] = await Promise.all([
    solicitar(`${ruta_cuenta()}/estado`), solicitar(`${ruta_cuenta()}/instrumentos`),
  ]);
  laboratorio.estado = estado;
  laboratorio.avance = avance;
  buscar("rol").textContent = `${estado.cuenta.nombre} · ${estado.cuenta.rol}`;
  await pintar_seleccion();
}

async function pintar_seleccion() {
  pintar_navegacion();
  const instrumento = instrumento_actual();
  buscar("instrumento-titulo").textContent = instrumento.nombre;
  buscar("instrumento-codigo").textContent = instrumento.codigo;
  buscar("instrumento-descripcion").textContent = instrumento.descripcion;
  buscar("aplicacion").replaceChildren(...instrumento.aplicaciones.map((aplicacion) => {
    const opcion = elemento("option", `${aplicacion.nombre} · ${aplicacion.codigo}`);
    opcion.value = aplicacion.codigo;
    return opcion;
  }));
  buscar("aplicacion").value = laboratorio.aplicacion;
  bloquear(buscar("aplicacion"), instrumento.aplicaciones.length === 1);
  const avances = laboratorio.avance.find((i) => i.instrumento === instrumento.codigo).aplicaciones;
  buscar("avances").replaceChildren(...avances.map((avance) => {
    const nodo = elemento("div", "", `avance${avance.aplicacion === laboratorio.aplicacion ? " activo" : ""}`);
    nodo.append(elemento("strong", avance.aplicacion), insignia_estado(avance.estado),
      elemento("p", `${avance.actividades.completadas}/${avance.actividades.total} actividades · ${avance.items.respondidos}/${avance.items.total} ítems`),
      elemento("p", avance.hay_resultado_vigente ? "Resultado vigente disponible" : "Sin resultado vigente", "texto-suave"));
    return nodo;
  }));
  const actividades = aplicacion_actual().actividades;
  if (!actividades.some((a) => a.codigo === laboratorio.actividad)) {
    laboratorio.actividad = actividades.find((a) => actividad_estado(a.codigo)?.estado !== "BLOQUEADA"
      && actividad_estado(a.codigo)?.estado !== "COMPLETADA")?.codigo
      || actividades.find((a) => actividad_estado(a.codigo)?.estado !== "BLOQUEADA")?.codigo || "";
  }
  buscar("actividades").replaceChildren(...actividades.map((actividad) => {
    const estado = actividad_estado(actividad.codigo)?.estado || "BLOQUEADA";
    const nodo = elemento("div", "", "actividad-lab");
    const elegir = boton(actividad.titulo, () => operar(async () => {
      laboratorio.actividad = actividad.codigo;
      await pintar_seleccion();
    }), estado === "BLOQUEADA", actividad.codigo === laboratorio.actividad ? "seleccionada" : "");
    elegir.append(elemento("small", `${actividad.codigo} · ${nombres_estados[estado]}`));
    nodo.append(elegir);
    if (estado === "BLOQUEADA") nodo.append(boton(`Requisitos ${actividad.codigo}`, () => operar(() => mostrar_requisitos(actividad.codigo)), false, "requisito"));
    return nodo;
  }));
  const ejemplos = ejemplos_instrumentos[instrumento.codigo] || {};
  buscar("cadenas-ejemplo").replaceChildren(...Object.entries(ejemplos).map(([nombre, cadena]) =>
    boton(nombre, () => operar(async () => { buscar("cadena").value = cadena; await rellenar(); }), respuestas_fijas())));
  buscar("cadena").value = laboratorio.cadenas.get(clave_cadena()) || "";
  bloquear(buscar("reiniciar-instrumento"), false);
  await Promise.all([cargar_actividad(), cargar_resultados()]);
}

async function cargar_actividad() {
  laboratorio.items = [];
  buscar("items").replaceChildren();
  const actividad = aplicacion_actual().actividades.find((a) => a.codigo === laboratorio.actividad);
  buscar("actividad-codigo").textContent = actividad?.codigo || "ACTIVIDAD";
  buscar("actividad-titulo").textContent = actividad?.titulo || "Esta aplicación todavía está bloqueada";
  if (actividad) {
    const [items, respuestas] = await Promise.all([
      solicitar(`/actividades/${encodeURIComponent(actividad.codigo)}/items`),
      solicitar(`${ruta_cuenta()}/actividades/${encodeURIComponent(actividad.codigo)}/respuestas`),
    ]);
    laboratorio.items = items;
    const guardadas = Object.fromEntries(respuestas.respuestas.map((r) => [r.item, r.opcion.orden]));
    const borrador = laboratorio.borradores.get(clave_actividad()) || {};
    const cadena = laboratorio.cadenas.get(clave_cadena());
    buscar("items").replaceChildren(...items.map((item) => {
      const campo = elemento("fieldset", "", "item-pregunta");
      campo.append(elemento("legend", `${item.numero}. ${item.enunciado}`));
      const opciones = elemento("div", "", "opciones");
      const valor = respuestas_fijas() ? guardadas[item.codigo]
        : borrador[item.codigo] ?? (cadena ? valor_cadena(cadena[item.numero - 1]) : guardadas[item.codigo]);
      for (const opcion of item.escala.opciones) {
        const etiqueta = elemento("label", "", "opcion-radio");
        const entrada = document.createElement("input");
        entrada.type = "radio";
        entrada.name = item.codigo;
        entrada.value = String(opcion.orden);
        entrada.checked = valor === opcion.orden;
        bloquear(entrada, respuestas_fijas());
        entrada.addEventListener("change", guardar_borrador);
        etiqueta.append(entrada, elemento("span", opcion.etiqueta));
        opciones.append(etiqueta);
      }
      campo.append(opciones);
      return campo;
    }));
  }
  const fijo = !actividad || respuestas_fijas();
  buscar("actividad-aviso").textContent = fijo && actividad ? "Respuestas fijas. Puedes rehacer la actividad o reiniciar esta aplicación."
    : actividad ? "Guardar respuestas no registra eventos. Completar verifica que todos los ítems estén respondidos." : "Consulta los requisitos para continuar.";
  for (const id of ["guardar", "rellenar", "guardar-disponibles", "cadena"]) bloquear(buscar(id), fijo);
  bloquear(buscar("completar"), !actividad);
}

function guardar_borrador() {
  laboratorio.borradores.set(clave_actividad(), Object.fromEntries([...buscar("items").querySelectorAll("input:checked")]
    .map((entrada) => [entrada.name, Number(entrada.value)])));
}

const valor_cadena = (caracter) => /[A-Z]/.test(caracter) ? caracter.charCodeAt(0) - 64 : Number(caracter);

async function validar_cadena() {
  const cadena = buscar("cadena").value.replace(/\s/g, "").toUpperCase();
  const total = avance_actual().items.total;
  const grupos = await Promise.all(aplicacion_actual().actividades.map((actividad) =>
    solicitar(`/actividades/${encodeURIComponent(actividad.codigo)}/items`)));
  const items = grupos.flat().sort((a, b) => a.numero - b.numero);
  const valida = cadena.length === total && items.length === total && items.every((item) => {
    const caracter = cadena[item.numero - 1];
    if (!/^[A-Z0-9]$/.test(caracter || "")) return false;
    const orden = /[A-Z]/.test(caracter) ? caracter.charCodeAt(0) - 64 : Number(caracter);
    return item.escala.opciones.some((opcion) => opcion.orden === orden
      && (!/[A-Z]/.test(caracter) || opcion.etiqueta.startsWith(`${caracter} (`)));
  });
  if (!valida) throw new Error(`La cadena debe tener ${total} opciones válidas para este instrumento.`);
  laboratorio.cadenas.set(clave_cadena(), cadena);
  buscar("cadena").value = cadena;
  return cadena;
}

async function rellenar() {
  const cadena = await validar_cadena();
  for (const entrada of buscar("items").querySelectorAll("input")) {
    const item = laboratorio.items.find((i) => i.codigo === entrada.name);
    entrada.checked = Number(entrada.value) === valor_cadena(cadena[item.numero - 1]);
  }
  guardar_borrador();
}

async function guardar_formulario() {
  guardar_borrador();
  const respuestas = Object.entries(laboratorio.borradores.get(clave_actividad())).map(([item, opcion]) => ({ item, opcion }));
  await solicitar("/acciones/responder-items", { cuenta: laboratorio.cuenta, actividad: laboratorio.actividad, respuestas, ...fecha_cuerpo() });
  await actualizar();
}

async function guardar_disponibles() {
  await rellenar();
  const cadena = laboratorio.cadenas.get(clave_cadena());
  for (const actividad of aplicacion_actual().actividades) {
    if (actividad_estado(actividad.codigo)?.estado === "BLOQUEADA" || respuestas_fijas(actividad.codigo)) continue;
    const items = await solicitar(`/actividades/${encodeURIComponent(actividad.codigo)}/items`);
    const respuestas = items.map((item) => ({ item: item.codigo, opcion: valor_cadena(cadena[item.numero - 1]) }));
    await solicitar("/acciones/responder-items", { cuenta: laboratorio.cuenta, actividad: actividad.codigo, respuestas, ...fecha_cuerpo() });
    laboratorio.borradores.set(clave_actividad(actividad.codigo), Object.fromEntries(respuestas.map((r) => [r.item, r.opcion])));
  }
  await actualizar();
}

async function completar_actividad() {
  await solicitar("/acciones/completar-actividad", { cuenta: laboratorio.cuenta, actividad: laboratorio.actividad, ...fecha_cuerpo() });
  const actual = laboratorio.actividad;
  await actualizar();
  const actividades = aplicacion_actual().actividades;
  const siguiente = actividades.slice(actividades.findIndex((a) => a.codigo === actual) + 1)
    .find((a) => actividad_estado(a.codigo)?.estado !== "BLOQUEADA" && actividad_estado(a.codigo)?.estado !== "COMPLETADA");
  if (siguiente) { laboratorio.actividad = siguiente.codigo; await pintar_seleccion(); }
}

function tabla(titulos, filas) {
  const contenedor = elemento("div", "", "tabla-contenedor");
  contenedor.tabIndex = 0;
  const nodo = elemento("table");
  const cabeza = elemento("thead");
  const cabecera = elemento("tr");
  titulos.forEach((titulo) => { const th = elemento("th", titulo); th.scope = "col"; cabecera.append(th); });
  cabeza.append(cabecera);
  const cuerpo = elemento("tbody");
  filas.forEach((fila) => {
    const tr = elemento("tr");
    fila.forEach((valor) => { const td = elemento("td"); td.append(valor instanceof Node ? valor : document.createTextNode(String(valor))); tr.append(td); });
    cuerpo.append(tr);
  });
  nodo.append(cabeza, cuerpo);
  contenedor.append(nodo);
  return contenedor;
}

function pintar_resultado(resultado) {
  const contenedor = elemento("div");
  contenedor.append(elemento("p", `${resultado.aplicacion} · ${resultado.calculado_en}`, "texto-suave"));
  contenedor.append(tabla(["Dimensión", "Puntaje", "Porcentaje"], resultado.dimensiones.map((dimension) => {
    const porcentaje = elemento("div", `${dimension.porcentaje}%`);
    const barra = document.createElement("meter");
    barra.min = 0; barra.max = 100; barra.value = dimension.porcentaje;
    barra.setAttribute("aria-label", `${dimension.nombre}: ${dimension.porcentaje}%`);
    porcentaje.append(barra);
    return [dimension.nombre, `${dimension.puntaje}/${dimension.puntaje_maximo}`, porcentaje];
  })));
  if (resultado.dimensiones_destacadas) {
    contenedor.append(elemento("h3", resultado.dimensiones_destacadas.length === 1 ? "Dimensión destacada" : "Dimensiones destacadas"),
      elemento("p", resultado.dimensiones_destacadas.map((d) => `${d.nombre} (${d.porcentaje}%)`).join(" · "), "mensaje-pendiente"));
  }
  if (resultado.codigo_interes) {
    const codigo = elemento("div", "", "codigo-interes");
    codigo.append(elemento("strong", resultado.codigo_interes.codigo), elemento("p", `Código de interés${resultado.codigo_interes.hay_empate ? " · Hay empate" : ""}`));
    contenedor.append(codigo);
    if (resultado.perfil_plano) contenedor.append(elemento("p", "Perfil plano: los seis puntajes son iguales; no se calculan coincidencias.", "mensaje-pendiente"));
    contenedor.append(elemento("h3", "Ocupaciones afines"), tabla(["Pos.", "Ocupación", "Pearson", "Ajuste"], resultado.coincidencias.map((c) =>
      [c.posicion, `${c.titulo} · ${c.codigo_onet}`, c.correlacion.toFixed(6), c.ajuste])));
    contenedor.append(elemento("h3", "Carreras recomendadas"));
    if (!resultado.carreras_recomendadas.length) contenedor.append(elemento("p", "Sin carreras recomendadas para este resultado.", "texto-suave"));
    for (const carrera of resultado.carreras_recomendadas) {
      const tarjeta = elemento("div", "", "carrera-recomendada");
      tarjeta.append(elemento("h3", carrera.nombre), elemento("p", `${carrera.codigo} · ${carrera.familia}`, "texto-suave"));
      const vias = elemento("ul");
      carrera.via.forEach((v) => vias.append(elemento("li", `Vía ${v.posicion}: ${v.titulo} (${v.codigo_onet}) · ${v.correlacion.toFixed(6)} · ${v.ajuste}`)));
      tarjeta.append(vias);
      contenedor.append(tarjeta);
    }
  }
  return contenedor;
}

async function cargar_resultados() {
  buscar("resultado").replaceChildren();
  buscar("historial").replaceChildren();
  buscar("resultado-titulo").textContent = instrumento_actual().tipo_resultado === "COMPARACION" ? "Comparación de entrada y salida" : "Resultado vigente";
  const ruta = `${ruta_cuenta()}/instrumentos/${encodeURIComponent(laboratorio.instrumento)}`;
  try {
    if (instrumento_actual().tipo_resultado === "COMPARACION") {
      const comparacion = await solicitar(`${ruta}/comparacion`, undefined, true);
      const comparacion_tabla = tabla(["Ítem", "Entrada", "Salida", "Diferencia"], comparacion.items.map((i) => [
        `${i.item}. ${i.enunciado}`, `${i.entrada.etiqueta} (${i.entrada.puntaje})`,
        `${i.salida.etiqueta} (${i.salida.puntaje})`, `${i.diferencia > 0 ? "+" : ""}${i.diferencia}`,
      ]));
      comparacion_tabla.classList.add("tabla-comparacion");
      buscar("resultado").append(comparacion_tabla);
    } else {
      const resultado = await solicitar(`${ruta}/resultado?aplicacion=${encodeURIComponent(laboratorio.aplicacion)}`, undefined, true);
      buscar("resultado").append(pintar_resultado(resultado));
    }
  } catch (error) {
    if (!(error instanceof ErrorApi) || error.estado !== 409) throw error;
    const aviso = elemento("div", "", "mensaje-pendiente");
    aviso.append(elemento("p", error.message));
    const avances = Array.isArray(error.datos.detail.avance) ? error.datos.detail.avance : [error.datos.detail.avance];
    avances.forEach((a) => {
      const pendiente = a.estado === "COMPLETADO" ? "Aplicación completada."
        : a.actividades.faltantes.length ? `Falta completar: ${a.actividades.faltantes.join(", ")}.` : "Sin resultado vigente.";
      aviso.append(elemento("p", `${a.aplicacion}: ${a.items.respondidos}/${a.items.total} ítems. ${pendiente}`));
    });
    buscar("resultado").append(aviso);
  }
  const historial = await solicitar(`${ruta}/historial`, undefined, true);
  if (!historial.length) buscar("historial").append(elemento("p", "Todavía no hay resultados calculados.", "texto-suave"));
  historial.forEach((resultado) => {
    const detalle = elemento("details");
    detalle.append(elemento("summary", `${resultado.calculado_en} · ${resultado.aplicacion} · ${resultado.anulado_en ? "Anulado" : "Vigente"}`, resultado.anulado_en ? "anulado" : ""));
    if (resultado.anulado_en) detalle.append(elemento("p", `Anulado: ${resultado.anulado_en}`, "texto-suave"));
    detalle.append(pintar_resultado(resultado));
    buscar("historial").append(detalle);
  });
}

async function mostrar_requisitos(codigo) {
  const progreso = await solicitar(`${ruta_cuenta()}/progreso/ACTIVIDAD/${encodeURIComponent(codigo)}`, undefined, true);
  buscar("requisitos-titulo").textContent = `Requisitos de ${codigo}`;
  buscar("requisitos-contenido").replaceChildren(...progreso.reglas.map((regla) => {
    const nodo = elemento("div");
    nodo.append(elemento("h3", regla.regla));
    regla.condiciones.forEach((c) => nodo.append(elemento("p", `${c.tipo_evento} · ${c.referencia || ""}: ${c.actual}/${c.requerido}${c.cumplida ? " · Cumplida" : " · Pendiente"}`)));
    return nodo;
  }));
  buscar("requisitos").showModal();
}

function abrir_reinicio() {
  if (laboratorio.ocupado) return;
  laboratorio.reinicio = { cuenta: laboratorio.cuenta, instrumento: laboratorio.instrumento, aplicacion: laboratorio.aplicacion };
  buscar("reinicio-detalle").textContent = `${laboratorio.estado.cuenta.nombre} · ${instrumento_actual().nombre} · ${laboratorio.aplicacion}`;
  buscar("confirmar-reinicio").showModal();
}

async function confirmar_reinicio() {
  buscar("confirmar-reinicio").close();
  const entrada = laboratorio.reinicio;
  await solicitar("/acciones/reiniciar-instrumento", { ...entrada, ...fecha_cuerpo() });
  laboratorio.cadenas.delete(clave_cadena());
  aplicacion_actual().actividades.forEach((a) => laboratorio.borradores.delete(clave_actividad(a.codigo)));
  laboratorio.actividad = "";
  await actualizar();
}

async function cambiar_cuenta() {
  laboratorio.cuenta = buscar("cuenta").value;
  laboratorio.estado = null;
  laboratorio.avance = [];
  laboratorio.items = [];
  laboratorio.actividad = "";
  for (const id of ["items", "actividades", "avances", "resultado", "historial"]) buscar(id).replaceChildren();
  try { await actualizar(); } catch (error) {
    pintar_navegacion();
    buscar("rol").textContent = laboratorio.cuentas.find((c) => c.codigo === laboratorio.cuenta).rol;
    buscar("actividad-titulo").textContent = "Instrumentos disponibles para estudiantes";
    buscar("actividad-aviso").textContent = "Esta cuenta no tiene acceso al laboratorio.";
    for (const id of ["guardar", "completar", "rellenar", "guardar-disponibles", "cadena", "aplicacion", "reiniciar-instrumento"]) bloquear(buscar(id), true);
    buscar("cadena").value = "";
    buscar("cadenas-ejemplo").replaceChildren();
    throw error;
  }
}

buscar("cuenta").addEventListener("change", () => operar(cambiar_cuenta));
buscar("aplicacion").addEventListener("change", () => operar(async () => {
  laboratorio.aplicacion = buscar("aplicacion").value; laboratorio.actividad = ""; await pintar_seleccion();
}));
buscar("actualizar").addEventListener("click", () => operar(cambiar_cuenta));
buscar("formulario-items").addEventListener("submit", (evento) => { evento.preventDefault(); operar(guardar_formulario); });
buscar("completar").addEventListener("click", () => operar(completar_actividad));
buscar("rellenar").addEventListener("click", () => operar(rellenar));
buscar("guardar-disponibles").addEventListener("click", () => operar(guardar_disponibles));
buscar("reiniciar-instrumento").addEventListener("click", abrir_reinicio);
buscar("cancelar-reinicio").addEventListener("click", () => buscar("confirmar-reinicio").close());
buscar("confirmar-reiniciar").addEventListener("click", () => operar(confirmar_reinicio));
buscar("cerrar-requisitos").addEventListener("click", () => buscar("requisitos").close());
buscar("limpiar-registro").addEventListener("click", () => buscar("registro").replaceChildren());
buscar("hora-actual").addEventListener("click", () => { buscar("fecha").value = ""; });
buscar("siguiente-dia").addEventListener("click", () => {
  if (!buscar("fecha").value) return;
  const fecha = new Date(buscar("fecha").value);
  fecha.setDate(fecha.getDate() + 1);
  const dos = (valor) => String(valor).padStart(2, "0");
  buscar("fecha").value = `${fecha.getFullYear()}-${dos(fecha.getMonth() + 1)}-${dos(fecha.getDate())}T${dos(fecha.getHours())}:${dos(fecha.getMinutes())}`;
});

operar(async () => {
  [laboratorio.cuentas, laboratorio.catalogo] = await Promise.all([solicitar("/cuentas"), solicitar("/instrumentos")]);
  laboratorio.cuenta = laboratorio.cuentas.find((cuenta) => cuenta.rol === "ESTUDIANTE")?.codigo || laboratorio.cuentas[0].codigo;
  const inicial = laboratorio.catalogo.find((instrumento) => instrumento.tipo_resultado === "COINCIDENCIAS") || laboratorio.catalogo[0];
  laboratorio.instrumento = inicial.codigo;
  laboratorio.aplicacion = inicial.aplicaciones.find((aplicacion) => aplicacion.momento === "UNICA")?.codigo || inicial.aplicaciones[0].codigo;
  buscar("cuenta").replaceChildren(...laboratorio.cuentas.map((cuenta) => {
    const opcion = elemento("option", `${cuenta.nombre} · ${cuenta.codigo}`); opcion.value = cuenta.codigo; return opcion;
  }));
  buscar("cuenta").value = laboratorio.cuenta;
  await actualizar();
});
