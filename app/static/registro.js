"use strict";

const actividad_registro = "REG-ACT08";
const buscar = (id) => document.getElementById(id);
const registro = { cuentas: [], items: [], contenido: null, cuenta: "", item: "", datos: null,
  mapa: null, novedades: [], ocupado: false, generacion: 0, consulta_tecnica: 0, textos: new Map(), orden_edicion: null };
const nombres_respuestas = { BORRADOR: "Borrador", PENDIENTE_SEGUIMIENTO: "Pregunta pendiente", FINAL: "Listo" };
const nombres_progreso = { DISPONIBLE: "Disponible", EN_CURSO: "En curso", COMPLETADA: "Completada", BLOQUEADA: "Bloqueada" };
const trazos_iconos = [
  ["M8 16H5l-3 3V4h16v9", "M10 10h12v10h-3l-3 3v-3h-6z"],
  ["M4 20 20 4", "M8 4h12v12", "M4 10v10h10"],
  ["M12 3a9 9 0 1 0 9 9", "M12 7a5 5 0 1 0 5 5", "M12 12 21 3", "M17 3h4v4"],
];
const cuenta_actual = () => registro.cuentas.find((cuenta) => cuenta.codigo === registro.cuenta);
const es_estudiante = () => cuenta_actual()?.rol === "ESTUDIANTE";
const item_actual = () => registro.items.find((item) => item.codigo === registro.item);
const respuesta_actual = () => registro.datos?.respuestas.find((respuesta) => respuesta.item === registro.item);
const momento = (tipo) => registro.contenido.momentos.find((entrada) => entrada.tipo === tipo);
const en_plan = () => registro.datos && registro.datos.posicion === momento("registro").id;
const ruta_cuenta = () => `/cuentas/${encodeURIComponent(registro.cuenta)}`;
const ruta_registro = () => `${ruta_cuenta()}/actividades/${actividad_registro}/registro`;

function objetivo_editor() {
  const respuesta = respuesta_actual();
  const conversacion = respuesta?.conversacion || [];
  const pendiente = respuesta?.estado === "PENDIENTE_SEGUIMIENTO";
  const orden = pendiente ? conversacion.filter((entrada) => entrada.tipo === "pregunta").at(-1)?.orden :
    respuesta?.estado === "FINAL" ? registro.orden_edicion : null;
  const guardado = conversacion.find((entrada) => entrada.tipo === "respuesta" && (entrada.orden ?? null) === (orden ?? null));
  return { pendiente, orden: orden ?? null, clave: `${registro.item}:${orden ?? "inicial"}`, guardado: guardado?.texto || "",
    existe: Boolean(guardado), borrador: respuesta?.estado === "BORRADOR" || guardado?.borrador === true };
}

function elemento(etiqueta, texto = "", clase = "") {
  const nodo = document.createElement(etiqueta);
  nodo.textContent = texto;
  nodo.className = clase;
  return nodo;
}

function mensaje(texto, error = false) {
  buscar("mensaje").textContent = texto;
  buscar("mensaje").parentElement.classList.toggle("error", error);
}

function actualizar_url() {
  const url = new URL(location.href);
  url.searchParams.set("cuenta", registro.cuenta);
  if (registro.item) url.searchParams.set("item", registro.item);
  else url.searchParams.delete("item");
  url.searchParams.set("fecha", buscar("fecha").value);
  history.replaceState(null, "", url);
}

function cuerpo(extra = {}) {
  const fecha = buscar("fecha").value;
  return { cuenta: registro.cuenta, actividad: actividad_registro, ...extra,
    ...(fecha ? { fecha_hora: fecha.length === 16 ? `${fecha}:00` : fecha } : {}) };
}

class ErrorApi extends Error {
  constructor(estado, datos) {
    super(typeof datos.detail === "string" ? datos.detail : datos.detail?.mensaje || `No se pudo realizar la acción (${estado}).`);
    this.estado = estado;
    this.faltantes = datos.detail?.items_faltantes || [];
  }
}

async function solicitar(ruta, datos) {
  const respuesta = await fetch(ruta, datos === undefined ? { cache: "no-store" } : {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(datos),
  });
  const contenido = await respuesta.json();
  if (!respuesta.ok) throw new ErrorApi(respuesta.status, contenido);
  return contenido;
}

function actualizar_controles() {
  const listo = Boolean(registro.datos && es_estudiante());
  const respuesta = respuesta_actual();
  const editar = listo && en_plan() && Boolean(item_actual());
  const bloqueos = {
    cuenta: !registro.cuentas.length, actualizar: false, reiniciar: !registro.cuentas.length,
    "confirmar-borrar": !registro.cuentas.length, "cancelar-reinicio": false,
    fecha: !registro.cuentas.length, "siguiente-dia": !registro.cuentas.length, "hora-actual": !registro.cuentas.length,
    continuar: !listo, "volver-explicacion": !listo, texto: !editar,
    "guardar-borrador": !editar || respuesta?.estado === "FINAL",
    enviar: !editar || !buscar("texto").value.trim(),
    "continuar-sin-responder": !editar || respuesta?.estado !== "PENDIENTE_SEGUIMIENTO",
    completar: !listo || !registro.items.filter((item) => item.obligatorio).every((item) =>
      registro.datos.respuestas.some((respuesta) => respuesta.item === item.codigo && respuesta.estado === "FINAL")),
    "marcar-vistos": !listo || !registro.novedades.length,
  };
  for (const [id, bloqueado] of Object.entries(bloqueos)) buscar(id).disabled = registro.ocupado || bloqueado;
  for (const nodo of buscar("iconos-items").querySelectorAll("button")) nodo.disabled = registro.ocupado || !listo;
  for (const nodo of buscar("conversacion").querySelectorAll("button")) nodo.disabled = registro.ocupado || !editar;
  buscar("formulario").setAttribute("aria-busy", String(registro.ocupado));
}

async function operar(accion, aviso = "Recuperando tu plan…", evaluando = false) {
  if (registro.ocupado) return;
  registro.ocupado = true;
  actualizar_controles();
  buscar("rueda-espera").hidden = !evaluando;
  mensaje(aviso);
  try {
    await accion();
  } catch (error) {
    let detalle = error instanceof ErrorApi ? error.message : "No pudimos conectar con la plataforma. Pulsa Actualizar para volver a intentarlo.";
    if (error.faltantes?.length) detalle += ` Falta finalizar: ${error.faltantes.map((codigo) =>
      registro.items.find((item) => item.codigo === codigo)?.nombre || codigo).join(", ")}.`;
    if (error instanceof ErrorApi && error.estado === 409 && es_estudiante()) {
      // Releer el servidor sin reenviar ni descartar el texto local de quien escribe.
      try { await recuperar(); } catch { /* El mensaje del conflicto conserva su prioridad. */ }
      detalle += " Revisa el estado actual antes de volver a enviar.";
    }
    mensaje(detalle, true);
  } finally {
    registro.ocupado = false;
    buscar("rueda-espera").hidden = true;
    actualizar_controles();
  }
}

function icono(indice) {
  const contenedor = elemento("span", "", "icono");
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  for (const trazo of trazos_iconos[indice % trazos_iconos.length]) {
    const linea = document.createElementNS("http://www.w3.org/2000/svg", "path");
    linea.setAttribute("d", trazo);
    svg.append(linea);
  }
  contenedor.append(svg);
  return contenedor;
}

function pintar_items() {
  buscar("iconos-items").replaceChildren(...registro.items.map((item, indice) => {
    const estado = registro.datos.respuestas.find((respuesta) => respuesta.item === item.codigo)?.estado;
    const nodo = elemento("button", "", "item-icono");
    nodo.type = "button";
    nodo.dataset.item = item.codigo;
    nodo.setAttribute("aria-pressed", String(item.codigo === registro.item));
    nodo.append(icono(indice), elemento("strong", item.nombre),
      elemento("span", nombres_respuestas[estado] || "Vacío", `estado-item ${estado?.toLowerCase() || "vacio"}`));
    nodo.addEventListener("click", () => {
      if (registro.ocupado) return;
      registro.item = item.codigo;
      registro.orden_edicion = null;
      actualizar_url();
      pintar_items();
      pintar_editor();
      buscar("texto").focus({ preventScroll: true });
    });
    return nodo;
  }));
}

function pintar_aviso_texto() {
  const texto = buscar("texto").value;
  const { guardado, existe, borrador } = objetivo_editor();
  buscar("aviso-texto").textContent = `${texto.trim().length} caracteres · ${texto !== guardado ? "Cambios sin guardar" :
    existe ? borrador ? "Borrador guardado" : "Respuesta guardada" : "Todavía sin respuesta"}`;
  actualizar_controles();
}

function pintar_conversacion() {
  const respuesta = respuesta_actual();
  const mensajes = respuesta?.estado === "BORRADOR" ? [] : respuesta?.conversacion || [];
  const objetivo = objetivo_editor();
  buscar("conversacion").hidden = !mensajes.length;
  buscar("conversacion").replaceChildren(...mensajes.filter((entrada) => !entrada.borrador).map((entrada) => {
    const pregunta = entrada.tipo === "pregunta";
    const tarjeta = elemento("li", "", `mensaje-conversacion ${pregunta ? "mensaje-lumi" : "mensaje-estudiante"}`);
    tarjeta.dataset.tipo = entrada.tipo;
    if (entrada.orden != null) tarjeta.dataset.orden = entrada.orden;
    tarjeta.append(elemento("p", pregunta ? "✦ Lumi" : entrada.orden ? `Tu respuesta · ${entrada.orden}` : "Tu respuesta inicial", "autor-mensaje"),
      elemento("p", entrada.texto, "texto-mensaje"));
    if (pregunta && respuesta.estado === "FINAL" && !mensajes.some((mensaje) =>
      mensaje.tipo === "respuesta" && mensaje.orden === entrada.orden)) tarjeta.append(elemento("p", "Preferiste seguir.", "texto-suave turno-omitido"));
    if (pregunta && objetivo.pendiente && entrada.orden === objetivo.orden) {
      tarjeta.classList.add("pregunta-pendiente");
      tarjeta.id = "pregunta-lumi";
    }
    if (!pregunta && respuesta.estado === "FINAL") {
      const boton = elemento("button", entrada.orden ? `Editar respuesta ${entrada.orden}` : "Editar respuesta inicial", "boton-enlace editar-respuesta");
      boton.type = "button";
      boton.dataset.editarOrden = entrada.orden ?? "inicial";
      boton.setAttribute("aria-pressed", String((entrada.orden ?? null) === objetivo.orden));
      boton.addEventListener("click", () => {
        if (registro.ocupado) return;
        registro.orden_edicion = entrada.orden ?? null;
        pintar_editor();
        buscar("texto").focus({ preventScroll: true });
      });
      tarjeta.append(boton);
    }
    return tarjeta;
  }));
}

function pintar_editor() {
  const item = item_actual();
  buscar("formulario").hidden = !item;
  if (!item) return;
  const respuesta = respuesta_actual();
  const pendiente = respuesta?.estado === "PENDIENTE_SEGUIMIENTO";
  const objetivo = objetivo_editor();
  buscar("item-nombre").textContent = item.nombre;
  buscar("item-estado").textContent = nombres_respuestas[respuesta?.estado] || "Vacío";
  buscar("item-estado").className = `estado-item ${respuesta?.estado.toLowerCase() || "vacio"}`;
  buscar("consigna").textContent = item.consigna;
  pintar_conversacion();
  buscar("texto").value = registro.textos.has(objetivo.clave) ? registro.textos.get(objetivo.clave) : objetivo.guardado;
  buscar("etiqueta-texto").textContent = pendiente ? "Tu respuesta a Lumi" : respuesta?.estado === "FINAL" ?
    objetivo.orden ? `Editar tu respuesta ${objetivo.orden}` : "Editar tu respuesta inicial" : "Tu respuesta";
  buscar("texto").placeholder = pendiente ? "Responde a la pregunta de Lumi…" : "Escribe aquí tu respuesta…";
  buscar("texto").setAttribute("aria-describedby", pendiente ? "aviso-texto pregunta-lumi" : "aviso-texto");
  buscar("enviar").textContent = pendiente ? "Responder" : respuesta?.estado === "FINAL" ? "Guardar cambios" : "Enviar";
  buscar("continuar-sin-responder").hidden = !pendiente;
  pintar_aviso_texto();
}

function pintar() {
  const disponible = es_estudiante() && Boolean(registro.datos);
  buscar("sin-acceso").hidden = es_estudiante() || !cuenta_actual();
  buscar("explicacion").hidden = !disponible || en_plan();
  buscar("plan").hidden = !disponible || !en_plan();
  buscar("detalle-tecnico").hidden = !disponible;
  buscar("paso-explicacion").classList.toggle("actual", disponible && !en_plan());
  buscar("paso-plan").classList.toggle("actual", Boolean(disponible && en_plan()));
  buscar("rol").textContent = cuenta_actual() ? `${cuenta_actual().nombre} · ${es_estudiante() ? "Estudiante" : "Apoderada/o"}` : "Cargando cuenta…";
  const actividad = registro.mapa?.bloques.flatMap((bloque) => bloque.actividades).find((entrada) => entrada.codigo === actividad_registro);
  buscar("titulo-actividad").textContent = actividad?.titulo || "Mi plan con Lumi";
  buscar("estado-actividad").textContent = actividad ? `${actividad.codigo} · ${nombres_progreso[actividad.estado] || actividad.estado}` : "";
  if (disponible) {
    if (!item_actual()) registro.item = registro.items.find((item) => !registro.datos.respuestas.some((respuesta) =>
      respuesta.item === item.codigo && respuesta.estado === "FINAL"))?.codigo || registro.items[0]?.codigo || "";
    pintar_items();
    pintar_editor();
    const cantidad = registro.items.filter((item) => registro.datos.respuestas.some((respuesta) =>
      respuesta.item === item.codigo && respuesta.estado === "FINAL")).length;
    const completada = registro.datos.estado === "COMPLETADA";
    buscar("aviso-completar").textContent = `${cantidad} de ${registro.items.length} respuestas listas. ${completada ? "Tu plan está completado y puedes editar tus respuestas." : "Cuando estén listas, completa la actividad."}`;
    buscar("completar").textContent = completada ? "Volver a completar" : "Completar actividad";
    actualizar_url();
  }
  buscar("novedades").hidden = !disponible || !registro.novedades.length;
  buscar("lista-novedades").replaceChildren(...registro.novedades.map((entrada) =>
    elemento("li", entrada.objetivo.nombre || entrada.objetivo.titulo || entrada.objetivo.codigo)));
  actualizar_controles();
}

async function recuperar() {
  const generacion = registro.generacion;
  const [mapa, datos, novedades] = await Promise.all([
    solicitar(`${ruta_cuenta()}/estado`), solicitar(ruta_registro()),
    solicitar(`${ruta_cuenta()}/desbloqueos?solo_no_vistos=true`),
  ]);
  if (generacion !== registro.generacion) return;
  registro.mapa = mapa;
  registro.datos = datos;
  registro.novedades = novedades;
  pintar();
  if (buscar("detalle-tecnico").open) await cargar_evaluaciones();
}

async function cargar_cuenta(codigo) {
  registro.generacion += 1;
  registro.consulta_tecnica += 1;
  registro.cuenta = codigo;
  registro.orden_edicion = null;
  registro.textos.clear();
  registro.datos = registro.mapa = null;
  registro.novedades = [];
  buscar("texto").value = "";
  buscar("conversacion").replaceChildren();
  buscar("iconos-items").replaceChildren();
  buscar("evaluaciones").replaceChildren();
  buscar("aviso-tecnico").textContent = "";
  buscar("detalle-tecnico").open = false;
  pintar();
  actualizar_url();
  if (es_estudiante()) {
    await recuperar();
    mensaje("Tu plan está actualizado.");
  } else {
    mensaje("Elige una cuenta de estudiante para hacer tu plan.");
  }
}

async function cargar_evaluaciones() {
  if (!es_estudiante() || !buscar("detalle-tecnico").open) return;
  const generacion = registro.generacion;
  const consulta = ++registro.consulta_tecnica;
  buscar("evaluaciones").replaceChildren();
  buscar("aviso-tecnico").textContent = "Cargando evaluaciones…";
  try {
    const filas = await solicitar(`/demo/registro/${encodeURIComponent(registro.cuenta)}/${actividad_registro}/evaluaciones`);
    if (generacion !== registro.generacion || consulta !== registro.consulta_tecnica || !buscar("detalle-tecnico").open) return;
    buscar("evaluaciones").replaceChildren(...filas.map((fila) => {
      const tarjeta = elemento("article", "", "evaluacion");
      tarjeta.append(elemento("h3", `${fila.item} · Evaluación ${fila.numero}`));
      const detalles = elemento("dl");
      for (const [nombre, valor] of Object.entries({ Origen: fila.origen, Clasificación: fila.clasificacion,
        "Criterios faltantes": fila.criterios_faltantes.join(", ") || "Ninguno",
        Latencia: fila.latencia_ms === null ? "—" : `${fila.latencia_ms} ms`, Modelo: fila.modelo || "—",
        Prompt: fila.version_prompt || "—", "Pregunta generada": fila.pregunta_generada || "—",
        "Requiere atención": fila.requiere_atencion ? "Sí" : "No", ...(fila.error ? { Error: fila.error } : {}) })) {
        detalles.append(elemento("dt", nombre), elemento("dd", valor));
      }
      tarjeta.append(detalles);
      const contexto = elemento("details", "", "contexto-evaluacion");
      contexto.append(elemento("summary", "Conversación evaluada"), elemento("pre", fila.texto_evaluado));
      tarjeta.append(contexto);
      return tarjeta;
    }));
    buscar("aviso-tecnico").textContent = filas.length ? `${filas.length} evaluaciones registradas.` : "Todavía no hay evaluaciones.";
  } catch {
    if (generacion === registro.generacion && consulta === registro.consulta_tecnica) buscar("aviso-tecnico").textContent = "No se pudo cargar el detalle. Ciérralo y vuelve a abrirlo para reintentar.";
  }
}

async function confirmar_accion(ruta, datos, aviso, aplicar = () => {}) {
  await solicitar(ruta, datos);
  aplicar();
  try {
    await recuperar();
    mensaje(aviso);
  } catch {
    mensaje(`${aviso} No pudimos actualizar la vista. Pulsa Actualizar para recuperar el estado guardado.`, true);
  }
}

buscar("cuenta").addEventListener("change", () => operar(() => cargar_cuenta(buscar("cuenta").value)));
buscar("actualizar").addEventListener("click", () => operar(async () => {
  if (!registro.cuentas.length || !registro.contenido || registro.items.some((item) => !item)) {
    await iniciar();
    return;
  }
  if (es_estudiante()) await recuperar();
  mensaje("Vista actualizada. Los cambios sin guardar se mantienen en este texto.");
}));
buscar("reiniciar").addEventListener("click", () => buscar("confirmar-reinicio").showModal());
buscar("cancelar-reinicio").addEventListener("click", () => buscar("confirmar-reinicio").close());
buscar("confirmar-borrar").addEventListener("click", () => {
  buscar("confirmar-reinicio").close();
  operar(async () => {
    await solicitar("/demo/reiniciar", {});
    // El POST confirmado borra también los buffers locales y las lecturas antiguas.
    registro.generacion += 1;
    registro.consulta_tecnica += 1;
    registro.textos.clear();
    registro.datos = registro.mapa = registro.contenido = null;
    registro.items = [];
    registro.item = "";
    registro.orden_edicion = null;
    registro.novedades = [];
    buscar("texto").value = "";
    buscar("conversacion").replaceChildren();
    buscar("iconos-items").replaceChildren();
    buscar("evaluaciones").replaceChildren();
    buscar("aviso-tecnico").textContent = "";
    buscar("detalle-tecnico").open = false;
    pintar();
    actualizar_url();
    try {
      await iniciar();
      mensaje("Demo reiniciada. Las respuestas de todas las cuentas se borraron; puedes empezar desde cero.");
    } catch {
      mensaje("Demo reiniciada. No pudimos cargar la vista inicial. Pulsa Actualizar para recuperarla.", true);
    }
  }, "Reiniciando la demo…");
});
buscar("texto").addEventListener("input", () => {
  registro.textos.set(objetivo_editor().clave, buscar("texto").value);
  pintar_aviso_texto();
});
buscar("fecha").addEventListener("change", actualizar_url);
buscar("siguiente-dia").addEventListener("click", () => {
  const fecha = buscar("fecha").value;
  if (!fecha) { mensaje("Elige una fecha simulada antes de avanzar un día.", true); return; }
  const siguiente = new Date(`${fecha}Z`);
  siguiente.setUTCDate(siguiente.getUTCDate() + 1);
  buscar("fecha").value = siguiente.toISOString().slice(0, 16);
  actualizar_url();
});
buscar("hora-actual").addEventListener("click", () => {
  const fecha = new Date();
  buscar("fecha").value = new Date(fecha.getTime() - fecha.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
  actualizar_url();
});
buscar("continuar").addEventListener("click", () => operar(() => confirmar_accion("/acciones/guardar-posicion",
  cuerpo({ posicion: momento("registro").id }), "Tu plan te espera. Elige uno de sus tres pasos.")));
buscar("volver-explicacion").addEventListener("click", () => operar(() => confirmar_accion("/acciones/guardar-posicion",
  cuerpo({ posicion: momento("dialogo").id }), "Volvamos a la idea de Lumi.")));
buscar("guardar-borrador").addEventListener("click", () => {
  const objetivo = objetivo_editor();
  operar(() => confirmar_accion("/acciones/registro/guardar-borrador",
    cuerpo({ item: registro.item, texto: buscar("texto").value }), "Borrador guardado.", () => registro.textos.delete(objetivo.clave)), "Guardando tu borrador…");
});
buscar("formulario").addEventListener("submit", (evento) => {
  evento.preventDefault();
  if (!buscar("texto").value.trim()) return;
  const edicion = respuesta_actual()?.estado === "FINAL";
  const objetivo = objetivo_editor();
  const seguimiento = objetivo.orden !== null;
  operar(() => confirmar_accion(`/acciones/registro/${seguimiento ? "responder-seguimiento" : "enviar"}`,
    cuerpo({ item: registro.item, texto: buscar("texto").value, ...(edicion && seguimiento ? { orden: objetivo.orden } : {}) }),
    "Respuesta guardada.", () => registro.textos.delete(objetivo.clave)),
    edicion ? "Guardando tus cambios…" : "Lumi está leyendo tu respuesta…", !edicion);
});
buscar("continuar-sin-responder").addEventListener("click", () => {
  const objetivo = objetivo_editor();
  operar(() => confirmar_accion("/acciones/registro/continuar-sin-responder",
    cuerpo({ item: registro.item }), "Continuaste con tu conversación guardada.", () => registro.textos.delete(objetivo.clave)));
});
buscar("completar").addEventListener("click", () => operar(() => confirmar_accion("/acciones/completar-actividad",
  cuerpo(), "¡Tu plan está completado! Ya puedes ponerlo en práctica."), "Completando tu actividad…"));
buscar("marcar-vistos").addEventListener("click", () => operar(() => confirmar_accion(`${ruta_cuenta()}/desbloqueos/marcar-vistos`,
  {}, "Novedades marcadas como vistas.")));
buscar("detalle-tecnico").addEventListener("toggle", () => {
  if (buscar("detalle-tecnico").open && !registro.ocupado) cargar_evaluaciones();
  else registro.consulta_tecnica += 1;
});

async function iniciar() {
  const [cuentas, contenido, items] = await Promise.all([
    solicitar("/cuentas"), solicitar(`/demo/recursos/contenido/${actividad_registro}.json`),
    solicitar(`/actividades/${actividad_registro}/items-registro`),
  ]);
  registro.cuentas = cuentas;
  registro.contenido = contenido;
  const plan = momento("registro");
  registro.items = plan.items.map((codigo) => items.find((item) => item.codigo === codigo));
  if (contenido.actividad !== actividad_registro || registro.items.some((item) => !item)) throw new Error("Contenido inválido");
  const explicacion = momento("dialogo");
  buscar("lumi-titulo").textContent = explicacion.personaje;
  buscar("lineas-lumi").replaceChildren(...explicacion.lineas.map((linea) => elemento("p", linea)));
  buscar("cuenta").replaceChildren(...cuentas.map((cuenta) => {
    const opcion = elemento("option", cuenta.nombre);
    opcion.value = cuenta.codigo;
    return opcion;
  }));
  const parametros = new URLSearchParams(location.search);
  registro.item = parametros.get("item") || "";
  if (parametros.has("fecha")) buscar("fecha").value = parametros.get("fecha");
  const cuenta = cuentas.find((entrada) => entrada.codigo === parametros.get("cuenta")) || cuentas.find((entrada) => entrada.rol === "ESTUDIANTE") || cuentas[0];
  buscar("cuenta").value = cuenta.codigo;
  await cargar_cuenta(cuenta.codigo);
}

operar(iniciar);
