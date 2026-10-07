"use strict";

const buscar = (id) => document.getElementById(id);
const datos_demo = { cuentas: [], catalogo: null, estado: null, eventos: [], novedades: [],
  cuenta: "", seccion: "ruta", ocupado: false, carga: 0, resaltados: new Map() };
const nombres_eventos = {
  INGRESO: "Ingreso", COMPLETA_ACTIVIDAD: "Actividad completada", COMPLETA_BLOQUE: "Bloque completado",
  RESPUESTA_REFLEXIVA: "Respuesta reflexiva", ESCRIBE_ENTRADA_DIARIO: "Entrada de diario",
  ESCRIBE_ENTRADA_LIBRE: "Entrada libre", REGISTRA_CHECK_IN: "Check-in",
  VISTA_CARRERA: "Carrera revisada", SUPERA_CASO: "Caso superado",
  PUBLICA_ENTREVISTA: "Entrevista publicada", ESCRIBE_CARTA: "Carta escrita",
  COMPLETA_CONVERSACION: "Conversación completada",
};
const nombres_estados = { DISPONIBLE: "Disponible", BLOQUEADA: "Bloqueada", COMPLETADA: "Completada",
  OBTENIDA: "Obtenida", OBTENIDO: "Obtenido", BLOQUEADO: "Bloqueado" };

function elemento(etiqueta, clase = "", texto = "") {
  const nodo = document.createElement(etiqueta);
  if (clase) nodo.className = clase;
  if (texto !== "") nodo.textContent = texto;
  return nodo;
}

function boton(texto, ejecutar, clase = "", bloqueado = false, mutacion = false) {
  const nodo = elemento("button", clase, texto);
  nodo.type = "button";
  nodo.dataset.bloqueado = String(bloqueado);
  if (mutacion) nodo.dataset.mutacion = "";
  nodo.disabled = bloqueado || (mutacion && datos_demo.ocupado);
  nodo.addEventListener("click", ejecutar);
  return nodo;
}

function estado_visual(estado) {
  return elemento("span", `estado ${estado.toLowerCase()}`, nombres_estados[estado] || estado);
}

function poner_conexion(texto, estado = "conectado") {
  buscar("conexion").className = `conexion ${estado}`;
  buscar("conexion-texto").textContent = texto;
}

class ErrorPeticion extends Error {
  constructor(estado, datos) {
    const detalle = datos.detail;
    const mensaje = typeof detalle === "string" ? detalle : detalle?.mensaje;
    super(mensaje || (Array.isArray(detalle) ? "Revisa los campos de la acción." : `Error HTTP ${estado}`));
    this.estado = estado;
    this.datos = datos;
  }
}

async function solicitar(ruta, cuerpo) {
  const opciones = cuerpo === undefined ? {} : {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(cuerpo),
  };
  const respuesta = await fetch(ruta, opciones);
  const datos = await respuesta.json();
  if (!respuesta.ok) throw new ErrorPeticion(respuesta.status, datos);
  return datos;
}

function ocupar(ocupado) {
  datos_demo.ocupado = ocupado;
  document.body.classList.toggle("ocupado", ocupado);
  for (const nodo of document.querySelectorAll("[data-mutacion]")) {
    nodo.disabled = ocupado || nodo.dataset.bloqueado === "true" || !datos_demo.estado;
  }
  buscar("cuenta").disabled = ocupado || !datos_demo.cuentas.length;
  buscar("accion").disabled = ocupado || !datos_demo.estado;
  buscar("fecha").disabled = ocupado;
  buscar("actualizar").disabled = ocupado;
}

function fecha_cuerpo() {
  const fecha = buscar("fecha").value;
  return fecha ? { fecha_hora: fecha.length === 16 ? `${fecha}:00` : fecha } : {};
}

function actividades_actuales() {
  return datos_demo.estado.bloques.flatMap((bloque) => bloque.actividades.map((actividad) => ({
    ...actividad, bloque: bloque.codigo,
    ...datos_demo.catalogo.actividades.find((item) => item.codigo === actividad.codigo),
  })));
}

function nombre_cuenta(codigo) {
  return datos_demo.cuentas.find((cuenta) => cuenta.codigo === codigo)?.nombre || codigo;
}

function es_nuevo(tipo, codigo) {
  return datos_demo.resaltados.get(datos_demo.cuenta)?.has(`${tipo}:${codigo}`);
}

async function cargar_cuenta() {
  const secuencia = ++datos_demo.carga;
  const cuenta = datos_demo.cuenta;
  const ruta = `/cuentas/${encodeURIComponent(cuenta)}`;
  const [estado, eventos, novedades] = await Promise.all([
    solicitar(`${ruta}/estado`), solicitar(`${ruta}/eventos`),
    solicitar(`${ruta}/desbloqueos?solo_no_vistos=true`),
  ]);
  if (secuencia !== datos_demo.carga) return;
  datos_demo.estado = estado;
  datos_demo.eventos = eventos;
  datos_demo.novedades = novedades;
  pintar_resumen();
  pintar_tablero();
  preparar_formulario(true);
  pintar_novedades();
  ocupar(datos_demo.ocupado);
  poner_conexion("Conectado · motor activo");
}

function pintar_resumen() {
  const estado = datos_demo.estado;
  const estudiante = estado.cuenta.rol === "ESTUDIANTE";
  buscar("rol").textContent = `${estudiante ? "Estudiante" : "Apoderada"} · ${estado.cuenta.codigo}`;
  buscar("bienvenida").textContent = `Estás explorando como ${estado.cuenta.nombre}. Cada acción abre nuevas posibilidades.`;
  buscar("nivel-etiqueta").textContent = estudiante ? `NIVEL ${estado.nivel_actual.numero} DE 5` : "ACOMPAÑAMIENTO FAMILIAR";
  buscar("nivel-titulo").textContent = estudiante ? estado.nivel_actual.titulo : "Tu rol también abre caminos";
  buscar("niveles").replaceChildren(...estado.niveles.map((nivel) => {
    const nodo = elemento("span", nivel.estado === "OBTENIDO" ? "obtenido" : "", String(nivel.numero));
    if (nivel.numero === estado.nivel_actual?.numero) nodo.classList.add("actual");
    nodo.title = `${nivel.titulo} · ${nombres_estados[nivel.estado]}`;
    return nodo;
  }));
  const actividades = actividades_actuales();
  buscar("total-completadas").textContent = `${actividades.filter((item) => item.estado === "COMPLETADA").length} / ${actividades.length}`;
  buscar("total-insignias").textContent = `${estado.insignias.filter((item) => item.estado === "OBTENIDA").length} / ${estado.insignias.length}`;
  buscar("total-novedades").textContent = datos_demo.novedades.length;
  buscar("total-eventos").textContent = datos_demo.eventos.length;
}

function pintar_tablero() {
  if (!datos_demo.estado) return;
  const secciones = { ruta: ["MISIONES DE CAMPO", "Mi recorrido"], ciudad: ["EXPLORACIÓN PROFESIONAL", "La ciudad"],
    contenido: ["REFLEXIÓN Y FAMILIA", "Contenido y diario"], insignias: ["PEQUEÑOS GRANDES LOGROS", "Mis insignias"],
    historial: ["LO QUE PASÓ", "Historial de eventos"] };
  const [etiqueta, titulo] = secciones[datos_demo.seccion];
  buscar("seccion-etiqueta").textContent = etiqueta;
  buscar("seccion-titulo").textContent = titulo;
  buscar("leyenda").hidden = !["ruta", "ciudad"].includes(datos_demo.seccion);
  buscar("panel").replaceChildren();
  pintar_siguiente();
  if (["ruta", "ciudad"].includes(datos_demo.seccion)) pintar_bloques();
  else if (datos_demo.seccion === "contenido") pintar_contenido();
  else if (datos_demo.seccion === "insignias") pintar_insignias();
  else pintar_historial();
}

function pintar_siguiente() {
  const panel = buscar("siguiente");
  panel.hidden = datos_demo.seccion !== "ruta";
  panel.replaceChildren();
  if (panel.hidden) return;
  const actividad = actividades_actuales().find((item) => item.estado === "DISPONIBLE");
  const texto = elemento("div");
  texto.append(elemento("span", "etiqueta", "TU SIGUIENTE PASO"));
  if (actividad) {
    texto.append(elemento("h3", "", actividad.titulo), elemento("p", "", `${actividad.codigo} · Una actividad disponible para seguir avanzando.`));
    panel.append(texto, boton(actividad.tipo === "CASO" ? "Elegir puntaje ↗" : "Completar ↗",
      () => actuar_actividad(actividad), "", false, true));
  } else {
    texto.append(elemento("h3", "", "Todas las actividades disponibles están completadas"),
      elemento("p", "", "Explora el contenido o consulta qué falta para los siguientes objetivos."));
    panel.append(texto);
  }
}

function pintar_bloques() {
  const espacio = datos_demo.seccion === "ciudad" ? "CIUDAD" : "MISIONES_CAMPO";
  const bloques = datos_demo.estado.bloques.filter((bloque) => bloque.espacio === espacio);
  if (!bloques.length) {
    buscar("panel").append(elemento("div", "vacio", "La ciudad pertenece al recorrido de los estudiantes. Explora la ruta del apoderado en Mi recorrido."));
    return;
  }
  for (const bloque of bloques) {
    const caja = elemento("article", `bloque${es_nuevo("BLOQUE", bloque.codigo) ? " nuevo" : ""}`);
    const cabecera = elemento("div", "bloque-cabecera");
    const titulos = elemento("div");
    titulos.append(elemento("h3", "", bloque.nombre), elemento("p", "", `${bloque.actividades.filter((item) => item.estado === "COMPLETADA").length} de ${bloque.actividades.length} actividades completadas`));
    cabecera.append(elemento("span", "numero-bloque", bloque.codigo), titulos, estado_visual(bloque.estado));
    caja.append(cabecera);
    for (const actividad of bloque.actividades) {
      const completa = actividad.estado === "COMPLETADA";
      const disponible = actividad.estado !== "BLOQUEADA";
      const catalogo = datos_demo.catalogo.actividades.find((item) => item.codigo === actividad.codigo);
      const fila = elemento("div", `actividad ${actividad.estado.toLowerCase()}${es_nuevo("ACTIVIDAD", actividad.codigo) ? " nuevo" : ""}`);
      const informacion = elemento("div", "actividad-info");
      informacion.append(elemento("span", "etiqueta", actividad.codigo), elemento("h3", "", actividad.titulo), estado_visual(actividad.estado));
      const controles = elemento("div", "actividad-botones");
      const consultar = boton("Ver requisitos", () => mostrar_progreso("ACTIVIDAD", actividad.codigo, actividad.titulo, bloque.codigo), "boton-texto");
      consultar.setAttribute("aria-label", `Ver requisitos de ${actividad.codigo}`);
      const completar = boton(catalogo.tipo === "CASO" ? "Resolver caso" : completa ? "Rehacer" : "Completar",
        () => actuar_actividad({ ...actividad, ...catalogo }), "", !disponible, true);
      completar.setAttribute("aria-label", `${catalogo.tipo === "CASO" ? "Resolver" : completa ? "Rehacer" : "Completar"} ${actividad.codigo}`);
      controles.append(consultar, completar);
      fila.append(elemento("span", "actividad-estado", completa ? "✓" : disponible ? "↗" : "·"), informacion, controles);
      caja.append(fila);
    }
    buscar("panel").append(caja);
  }
}

function actuar_actividad(actividad) {
  if (actividad.tipo === "CASO") {
    buscar("accion").value = "resolver-caso";
    preparar_formulario();
    buscar("campo-actividad").value = actividad.codigo;
    buscar("campo-puntaje").focus();
    buscar("formulario").scrollIntoView({ block: "center", behavior: "smooth" });
    return;
  }
  ejecutar_accion("completar-actividad", { cuenta: datos_demo.cuenta, actividad: actividad.codigo }, actividad.titulo);
}

function pintar_contenido() {
  for (const [clave, titulo, tipo] of [["fichas", "Fichas para explorar", "FICHA"], ["testimonios", "Experiencias reales", "TESTIMONIO"],
    ["preguntas_diario", "Preguntas de tu diario", "PREGUNTA_DIARIO"]]) {
    const items = datos_demo.estado[clave];
    if (!items.length) continue;
    buscar("panel").append(elemento("h3", "subtitulo", titulo));
    const rejilla = elemento("div", "rejilla");
    for (const item of items) {
      const tarjeta = elemento("article", `tarjeta${es_nuevo(tipo, item.codigo) ? " nuevo" : ""}`);
      tarjeta.append(elemento("span", "etiqueta", item.codigo), elemento("h3", "", item.titulo || item.pregunta), estado_visual(item.estado));
      if (tipo === "PREGUNTA_DIARIO") {
        tarjeta.append(elemento("p", "", item.respondida ? "Ya respondiste esta pregunta." : "Una invitación a reflexionar."));
        if (item.estado === "DISPONIBLE" && !item.respondida) tarjeta.append(boton("Responder en el diario", () => {
          buscar("accion").value = "escribir-entrada";
          preparar_formulario();
          buscar("campo-origen").value = "GUIADA";
          actualizar_pregunta();
          buscar("campo-pregunta").value = item.codigo;
          buscar("campo-texto").focus();
        }));
      }
      tarjeta.append(boton("Ver requisitos", () => mostrar_progreso(tipo, item.codigo, item.titulo || item.pregunta), "boton-texto"));
      rejilla.append(tarjeta);
    }
    buscar("panel").append(rejilla);
  }
  buscar("panel").append(elemento("h3", "subtitulo", "Conversaciones en familia"));
  const caja = elemento("article", `tarjeta${es_nuevo("CONVERSACIONES", "-") ? " nuevo" : ""}`);
  caja.append(estado_visual(datos_demo.estado.conversaciones.estado), elemento("h3", "", "Un espacio para escucharse"),
    elemento("p", "", "Cada cuenta abre esta sección a su propio ritmo. Una conversación registra eventos en ambas."),
    boton("Ver qué falta", () => mostrar_progreso("CONVERSACIONES", "-", "Conversaciones en familia")));
  buscar("panel").append(caja);
}

function pintar_insignias() {
  const rejilla = elemento("div", "rejilla");
  for (const insignia of datos_demo.estado.insignias) {
    const oculta = insignia.codigo === "???";
    const tarjeta = elemento("article", `tarjeta${es_nuevo("INSIGNIA", insignia.codigo) ? " nuevo" : ""}`);
    tarjeta.append(elemento("span", `insignia-simbolo ${insignia.estado.toLowerCase()}`, oculta ? "?" : "◇"),
      elemento("h3", "", insignia.nombre), estado_visual(insignia.estado),
      elemento("p", "", oculta ? "Un logro por descubrir. Se revelará cuando lo obtengas." : insignia.requisito || insignia.descripcion));
    if (!oculta) tarjeta.append(boton("Ver progreso", () => mostrar_progreso("INSIGNIA", insignia.codigo, insignia.nombre), "boton-texto"));
    rejilla.append(tarjeta);
  }
  buscar("panel").append(rejilla);
}

function pintar_historial() {
  if (!datos_demo.eventos.length) {
    buscar("panel").append(elemento("div", "vacio", "Todavía no hay eventos. Completa una actividad o simula una acción para empezar."));
    return;
  }
  for (const evento of datos_demo.eventos) {
    const fila = elemento("article", "evento");
    const texto = elemento("div");
    texto.append(elemento("h3", "", `${nombres_eventos[evento.tipo] || evento.tipo}${evento.referencia ? ` · ${evento.referencia}` : ""}`),
      elemento("p", "", evento.fecha_hora.replace("T", " · ")));
    fila.append(elemento("span", "icono-evento", "↗"), texto);
    buscar("panel").append(fila);
  }
}

function pintar_novedades() {
  const panel = buscar("novedades");
  panel.replaceChildren();
  buscar("marcar-vistos").dataset.bloqueado = String(!datos_demo.novedades.length);
  if (!datos_demo.novedades.length) panel.append(elemento("p", "texto-suave", "No hay novedades pendientes para esta cuenta."));
  for (const novedad of datos_demo.novedades) {
    const fila = elemento("div", "novedad", novedad.objetivo.nombre);
    fila.append(elemento("small", "", `${novedad.objetivo.codigo} · ${novedad.regla}`));
    panel.append(fila);
  }
}

function pintar_condiciones(contenedor, regla) {
  for (const condicion of regla.condiciones) {
    const caja = elemento("div", "condicion");
    const fila = elemento("div", "fila");
    fila.append(elemento("span", "", `${condicion.cumplida ? "✓ " : "○ "}${nombres_eventos[condicion.tipo_evento] || condicion.tipo_evento}${condicion.referencia ? ` · ${condicion.referencia}` : ""}`),
      elemento("strong", "", `${condicion.actual} / ${condicion.requerido}`));
    const progreso = elemento("progress");
    progreso.max = condicion.requerido;
    progreso.value = Math.min(condicion.actual, condicion.requerido);
    progreso.setAttribute("aria-label", `${nombres_eventos[condicion.tipo_evento]}: ${condicion.actual} de ${condicion.requerido}`);
    caja.append(fila, progreso);
    if (condicion.tipo_conteo !== "EVENTOS") caja.append(elemento("small", "", condicion.tipo_conteo === "DIAS_DISTINTOS" ? "Se cuentan días distintos." : "Se cuentan actividades o referencias distintas."));
    contenedor.append(caja);
  }
  if (regla.evaluador_especial) contenedor.append(elemento("p", "comprobacion", `${regla.evaluador_especial.cumplido ? "✓" : "○"} Evaluación especial: carreras de tres familias distintas.`));
}

function pintar_progreso(contenedor, progreso) {
  contenedor.append(estado_visual(progreso.disponible ? "DISPONIBLE" : "BLOQUEADA"));
  if (!progreso.reglas.length) contenedor.append(elemento("p", "guia-formulario", "Este objetivo no tiene reglas propias. Su disponibilidad también depende del rol y, para actividades, del bloque contenedor."));
  for (const regla of progreso.reglas) {
    const caja = elemento("div", "explicacion");
    caja.append(elemento("strong", "", regla.regla), elemento("p", "", regla.cumplida ? "Condiciones cumplidas" : "Esto es lo que falta"));
    pintar_condiciones(caja, regla);
    contenedor.append(caja);
  }
  if (progreso.reglas.length > 1) contenedor.append(elemento("p", "guia-formulario", "Estas reglas son alternativas: basta obtener una para abrir el objetivo."));
}

async function mostrar_progreso(tipo, codigo, titulo, bloque) {
  const cuenta = datos_demo.cuenta;
  const dialogo = buscar("detalle");
  const panel = buscar("detalle-contenido");
  buscar("detalle-titulo").textContent = titulo;
  panel.replaceChildren(elemento("p", "texto-suave", "Consultando las reglas…"));
  if (!dialogo.open) dialogo.showModal();
  try {
    const progreso = await solicitar(`/cuentas/${encodeURIComponent(cuenta)}/progreso/${tipo}/${encodeURIComponent(codigo)}`);
    panel.replaceChildren();
    pintar_progreso(panel, progreso);
    const bloque_estado = datos_demo.estado.bloques.find((item) => item.codigo === bloque);
    if (bloque_estado?.estado === "BLOQUEADA") {
      const progreso_bloque = await solicitar(`/cuentas/${encodeURIComponent(cuenta)}/progreso/BLOQUE/${encodeURIComponent(bloque)}`);
      panel.append(elemento("p", "aviso-bloque", `También necesitas abrir el bloque ${bloque}: ${bloque_estado.nombre}.`));
      pintar_progreso(panel, progreso_bloque);
    }
    if (tipo === "ACTIVIDAD" && !progreso.disponible) panel.append(boton("Probar intento bloqueado", () => {
      const actividad = actividades_actuales().find((item) => item.codigo === codigo);
      dialogo.close();
      const caso = actividad.tipo === "CASO";
      ejecutar_accion(caso ? "resolver-caso" : "completar-actividad",
        { cuenta, actividad: codigo, ...(caso ? { puntaje: 85 } : {}) }, "Intento de actividad bloqueada");
    }, "", false, true));
  } catch (error) {
    panel.replaceChildren(elemento("p", "error-texto", error.message));
  }
}

function agregar_campo(nombre, titulo, tipo = "text", valor = "") {
  const etiqueta = elemento("label", "", titulo);
  etiqueta.htmlFor = `campo-${nombre}`;
  const campo = elemento(tipo === "textarea" ? "textarea" : "input");
  if (tipo !== "textarea") campo.type = tipo;
  campo.id = `campo-${nombre}`;
  campo.name = nombre;
  campo.value = valor;
  buscar("campos").append(etiqueta, campo);
  return campo;
}

function agregar_seleccion(nombre, titulo, opciones) {
  const etiqueta = elemento("label", "", titulo);
  etiqueta.htmlFor = `campo-${nombre}`;
  const campo = elemento("select");
  campo.id = `campo-${nombre}`;
  campo.name = nombre;
  for (const [valor, texto] of opciones) {
    const opcion = elemento("option", "", texto);
    opcion.value = valor;
    campo.append(opcion);
  }
  buscar("campos").append(etiqueta, campo);
  return campo;
}

function preparar_formulario(conservar = false) {
  const anterior = conservar ? new FormData(buscar("formulario")) : null;
  const estudiante = datos_demo.estado.cuenta.rol === "ESTUDIANTE";
  const vinculo = datos_demo.catalogo.vinculos.some((item) => [item.estudiante, item.apoderado].includes(datos_demo.cuenta));
  const opciones = [["ingresar", "Registrar ingreso"], ["responder-registro", "Respuesta reflexiva"],
    ...(estudiante ? [["resolver-caso", "Resolver un caso"], ["escribir-entrada", "Escribir en el diario"], ["check-in", "Hacer check-in"]] : []),
    ["ver-carrera", "Revisar una carrera"], ...(estudiante ? [["publicar-entrevista", "Publicar entrevista"]] : []),
    ...(vinculo ? [["escribir-carta", "Escribir carta familiar"], ["completar-conversacion", "Marcar conversación"]] : [])];
  const elegida = buscar("accion").value;
  buscar("accion").replaceChildren(...opciones.map(([valor, texto]) => {
    const opcion = elemento("option", "", texto);
    opcion.value = valor;
    return opcion;
  }));
  buscar("accion").value = opciones.some(([valor]) => valor === elegida) ? elegida : estudiante ? "check-in" : "escribir-carta";
  const accion = buscar("accion").value;
  buscar("campos").replaceChildren();
  if (accion === "resolver-caso") {
    const casos = actividades_actuales().filter((item) => item.tipo === "CASO");
    const seleccion = agregar_seleccion("actividad", "Caso", casos.map((item) => [item.codigo, `${item.codigo} · ${item.titulo} (${nombres_estados[item.estado]})`]));
    const puntaje = agregar_campo("puntaje", "Puntaje", "number", "85");
    const actualizar_minimo = () => {
      const caso = casos.find((item) => item.codigo === seleccion.value);
      buscar("campos").querySelector('label[for="campo-puntaje"]').textContent = caso
        ? `Puntaje (mínimo ${caso.puntaje_minimo} para superar)` : "Puntaje";
    };
    seleccion.addEventListener("change", actualizar_minimo);
    actualizar_minimo();
    puntaje.min = "0"; puntaje.max = "100"; puntaje.step = "any"; puntaje.required = true;
  } else if (accion === "responder-registro") {
    agregar_seleccion("clasificacion", "Clasificación simulada", [["ADECUADA", "Adecuada"], ["VAGA", "Vaga"]]);
    const etiqueta = elemento("label", "checkbox-label");
    const campo = elemento("input");
    campo.type = "checkbox"; campo.name = "ampliada"; campo.id = "campo-ampliada";
    etiqueta.append(campo, document.createTextNode("La respuesta fue ampliada"));
    buscar("campos").append(etiqueta);
  } else if (accion === "escribir-entrada") {
    agregar_seleccion("origen", "Tipo de entrada", [["LIBRE", "Libre"], ["GUIADA", "Guiada por una pregunta"]]).addEventListener("change", actualizar_pregunta);
    agregar_seleccion("pregunta", "Pregunta", datos_demo.estado.preguntas_diario.map((item) => [item.codigo, `${item.codigo} · ${item.respondida ? "Respondida" : nombres_estados[item.estado]}`]));
    agregar_campo("texto", "Tu reflexión de prueba", "textarea", "Hoy descubrí algo sobre mi futuro.");
  } else if (accion === "check-in") {
    agregar_seleccion("nivel_seguridad", "¿Qué tan seguro te sientes?", [[1, "1 · Poco seguro"], [2, "2"], [3, "3 · En proceso"], [4, "4"], [5, "5 · Muy seguro"]]);
    buscar("campo-nivel_seguridad").value = "3";
    buscar("campos").append(elemento("p", "guia-formulario", "Puedes hacer uno por día. Usa + Un día para probar la constancia."));
  } else if (accion === "ver-carrera") {
    agregar_seleccion("carrera", "Carrera", datos_demo.catalogo.carreras.map((item) => [item.codigo, `${item.nombre} · ${item.familia}`]));
  } else if (accion === "publicar-entrevista") {
    buscar("campos").append(elemento("label", "", "Autores de la entrevista"));
    for (const cuenta of datos_demo.cuentas.filter((item) => item.rol === "ESTUDIANTE")) {
      const etiqueta = elemento("label", "checkbox-label");
      const campo = elemento("input");
      campo.type = "checkbox"; campo.name = "autores"; campo.value = cuenta.codigo;
      campo.checked = cuenta.codigo === datos_demo.cuenta;
      etiqueta.append(campo, document.createTextNode(cuenta.nombre));
      buscar("campos").append(etiqueta);
    }
    agregar_campo("resumen", "Resumen de prueba", "textarea", "Conversamos sobre una profesión y su día a día.");
  } else if (accion === "escribir-carta") {
    agregar_campo("texto", "Tu carta de prueba", "textarea", "Quiero conversar sobre lo que espero del futuro.");
  } else if (accion === "completar-conversacion") {
    agregar_seleccion("conversacion", "Conversación", datos_demo.catalogo.conversaciones.map((item) => [item.codigo, item.titulo]));
    buscar("campos").append(elemento("p", "guia-formulario", `Tu sección está ${nombres_estados[datos_demo.estado.conversaciones.estado].toLowerCase()}. La primera vez genera eventos para las dos cuentas del vínculo.`));
  } else buscar("campos").append(elemento("p", "guia-formulario", "Registrará un ingreso en el historial de esta cuenta."));
  if (anterior) for (const campo of buscar("campos").querySelectorAll("[name]")) {
    if (!anterior.has(campo.name) && campo.type !== "checkbox") continue;
    if (campo.type === "checkbox") campo.checked = anterior.getAll(campo.name).includes(campo.value);
    else campo.value = anterior.get(campo.name);
  }
  if (accion === "resolver-caso") buscar("campo-actividad").dispatchEvent(new Event("change"));
  if (accion === "escribir-entrada") actualizar_pregunta();
}

function actualizar_pregunta() {
  const campo = buscar("campo-pregunta");
  const guiada = buscar("campo-origen").value === "GUIADA";
  campo.hidden = !guiada;
  campo.disabled = !guiada;
  campo.previousElementSibling.hidden = !guiada;
}

function cuerpo_formulario() {
  const formulario = new FormData(buscar("formulario"));
  const accion = buscar("accion").value;
  const cuerpo = Object.fromEntries(formulario.entries());
  if (accion === "publicar-entrevista") cuerpo.autores = formulario.getAll("autores");
  else cuerpo.cuenta = datos_demo.cuenta;
  if (accion === "responder-registro") cuerpo.ampliada = formulario.has("ampliada");
  if (cuerpo.puntaje !== undefined) cuerpo.puntaje = Number(cuerpo.puntaje);
  if (cuerpo.nivel_seguridad !== undefined) cuerpo.nivel_seguridad = Number(cuerpo.nivel_seguridad);
  return cuerpo;
}

function pintar_resultado(respuesta, cuenta, titulo) {
  const resultados = respuesta.por_cuenta || { [cuenta]: respuesta };
  const nuevos = Object.values(resultados).reduce((total, item) => total + item.nuevos_desbloqueos.length, 0);
  buscar("resultado-titulo").textContent = nuevos ? `${nuevos} ${nuevos === 1 ? "nuevo desbloqueo" : "nuevos desbloqueos"}` : "Acción registrada";
  const panel = buscar("resultado");
  panel.parentElement.classList.remove("error");
  panel.replaceChildren(elemento("p", "texto-suave", `${titulo} · ${nombre_cuenta(cuenta)}`));
  for (const [codigo_cuenta, resultado] of Object.entries(resultados)) {
    if (respuesta.por_cuenta) panel.append(elemento("h3", "", nombre_cuenta(codigo_cuenta)));
    panel.append(elemento("p", "texto-suave", resultado.eventos_registrados.length
      ? resultado.eventos_registrados.map((evento) => `${nombres_eventos[evento.tipo]}${evento.referencia ? ` · ${evento.referencia}` : ""}`).join("; ")
      : "No se registraron eventos nuevos para esta cuenta."));
    for (const nuevo of resultado.nuevos_desbloqueos) {
      const caja = elemento("div", "explicacion");
      caja.append(elemento("strong", "", `↗ ${nuevo.objetivo.nombre}`), elemento("p", "", `${nuevo.objetivo.codigo} · ${nuevo.regla}`));
      pintar_condiciones(caja, nuevo);
      panel.append(caja);
    }
    if (!resultado.nuevos_desbloqueos.length) panel.append(elemento("p", "texto-suave", "Sin nuevos desbloqueos. Puedes consultar los requisitos del siguiente objetivo."));
  }
  agregar_json(panel, respuesta);
}

function agregar_json(panel, datos) {
  const detalle = elemento("details");
  detalle.append(elemento("summary", "", "Ver respuesta de la API"), elemento("pre", "", JSON.stringify(datos, null, 2)));
  panel.append(detalle);
}

function mostrar_error(error, accion_guardada = false) {
  const panel = buscar("resultado");
  panel.parentElement.classList.add("error");
  buscar("resultado-titulo").textContent = accion_guardada ? "Acción guardada; falta actualizar el tablero" : error.estado === 409 ? "Acción no permitida" : "No se pudo confirmar la respuesta";
  panel.replaceChildren(elemento("p", "error-texto", error.message || "No se pudo conectar con el servidor."));
  if (accion_guardada) panel.append(elemento("p", "texto-suave", "Pulsa Actualizar para consultar el estado. La acción ya fue guardada; no hace falta repetirla."));
  else if (!error.estado) panel.append(elemento("p", "texto-suave", "Actualiza el tablero antes de repetir una acción: el servidor podría haberla guardado aunque no se recibiera la respuesta."));
  if (error.datos?.detail?.progreso) pintar_progreso(panel, error.datos.detail.progreso);
  if (error.datos) agregar_json(panel, error.datos);
  if (!error.estado) poner_conexion("Sin conexión · prueba Actualizar", "error");
}

async function ejecutar_accion(nombre, cuerpo, titulo) {
  if (datos_demo.ocupado) return;
  ocupar(true);
  let guardada = false;
  const cuenta = datos_demo.cuenta;
  const anteriores = actividades_actuales();
  try {
    const respuesta = await solicitar(`/acciones/${nombre}`, { ...cuerpo, ...fecha_cuerpo() });
    guardada = true;
    datos_demo.resaltados.clear();
    for (const [autor, resultado] of Object.entries(respuesta.por_cuenta || { [cuenta]: respuesta })) {
      datos_demo.resaltados.set(autor, new Set(resultado.nuevos_desbloqueos.map((nuevo) => `${nuevo.tipo_objetivo}:${nuevo.objetivo.codigo}`)));
    }
    pintar_resultado(respuesta, cuenta, titulo);
    await cargar_cuenta();
    const resaltados = datos_demo.resaltados.get(cuenta) || new Set();
    for (const actividad of actividades_actuales()) {
      if (actividad.estado !== "BLOQUEADA" && anteriores.find((item) => item.codigo === actividad.codigo)?.estado === "BLOQUEADA") resaltados.add(`ACTIVIDAD:${actividad.codigo}`);
    }
    datos_demo.resaltados.set(cuenta, resaltados);
    pintar_tablero();
  } catch (error) { mostrar_error(error, guardada); }
  finally { ocupar(false); }
}

async function inicializar() {
  ocupar(true);
  try {
    const [cuentas, catalogo] = await Promise.all([solicitar("/cuentas"), solicitar("/demo/catalogo")]);
    datos_demo.cuentas = cuentas;
    datos_demo.catalogo = catalogo;
    buscar("confirmar-reinicio").querySelector("h2").textContent = `¿Reiniciar las ${cuentas.length} cuentas?`;
    buscar("cuenta").replaceChildren(...cuentas.map((cuenta) => {
      const opcion = elemento("option", "", `${cuenta.nombre} · ${cuenta.rol === "ESTUDIANTE" ? "Estudiante" : "Apoderada"}`);
      opcion.value = cuenta.codigo;
      return opcion;
    }));
    datos_demo.cuenta = cuentas.find((cuenta) => cuenta.codigo === "est-ana")?.codigo || cuentas[0].codigo;
    buscar("cuenta").value = datos_demo.cuenta;
    await cargar_cuenta();
  } catch (error) { mostrar_error(error); }
  finally { ocupar(false); }
}

buscar("cuenta").addEventListener("change", async () => {
  datos_demo.cuenta = buscar("cuenta").value;
  datos_demo.estado = null;
  datos_demo.eventos = [];
  datos_demo.novedades = [];
  buscar("panel").replaceChildren(elemento("div", "vacio", `Cargando el recorrido de ${nombre_cuenta(datos_demo.cuenta)}…`));
  buscar("siguiente").hidden = true;
  buscar("rol").textContent = `Cargando ${nombre_cuenta(datos_demo.cuenta)}…`;
  buscar("bienvenida").textContent = "Consultando el progreso de la cuenta seleccionada.";
  buscar("nivel-titulo").textContent = "Cargando…";
  buscar("nivel-etiqueta").textContent = "PROGRESO DE LA CUENTA";
  buscar("niveles").replaceChildren();
  buscar("novedades").replaceChildren(elemento("p", "texto-suave", "Cargando…"));
  for (const id of ["total-completadas", "total-insignias", "total-novedades", "total-eventos"]) buscar(id).textContent = "—";
  buscar("campos").replaceChildren();
  ocupar(true);
  try { await cargar_cuenta(); }
  catch (error) {
    datos_demo.estado = null;
    buscar("panel").replaceChildren(elemento("div", "vacio error-texto", "No se pudo cargar esta cuenta. Pulsa Actualizar para reintentar."));
    mostrar_error(error);
  } finally { ocupar(false); }
});
buscar("accion").addEventListener("change", () => preparar_formulario());
buscar("formulario").addEventListener("submit", (evento) => {
  evento.preventDefault();
  if (!buscar("formulario").reportValidity()) return;
  ejecutar_accion(buscar("accion").value, cuerpo_formulario(), buscar("accion").selectedOptions[0].textContent);
});
buscar("navegacion").addEventListener("click", (evento) => {
  const boton_seccion = evento.target.closest("[data-seccion]");
  if (!boton_seccion) return;
  datos_demo.seccion = boton_seccion.dataset.seccion;
  for (const nodo of buscar("navegacion").querySelectorAll("button")) {
    nodo.classList.toggle("activo", nodo === boton_seccion);
    if (nodo === boton_seccion) nodo.setAttribute("aria-current", "page");
    else nodo.removeAttribute("aria-current");
  }
  pintar_tablero();
});
buscar("actualizar").addEventListener("click", async () => {
  if (!datos_demo.catalogo) { await inicializar(); return; }
  ocupar(true);
  try { await cargar_cuenta(); }
  catch (error) { mostrar_error(error); }
  finally { ocupar(false); }
});
buscar("siguiente-dia").addEventListener("click", () => {
  const valor = buscar("fecha").value;
  if (!valor) { buscar("fecha").value = "2026-10-01T10:00"; return; }
  const fecha = new Date(`${valor.slice(0, 10)}T12:00:00Z`);
  fecha.setUTCDate(fecha.getUTCDate() + 1);
  buscar("fecha").value = `${fecha.toISOString().slice(0, 10)}T${valor.slice(11)}`;
});
buscar("hora-actual").addEventListener("click", () => { buscar("fecha").value = ""; });
buscar("cerrar-detalle").addEventListener("click", () => buscar("detalle").close());
buscar("reiniciar").addEventListener("click", () => buscar("confirmar-reinicio").showModal());
buscar("cancelar-reinicio").addEventListener("click", () => buscar("confirmar-reinicio").close());
buscar("confirmar-borrar").addEventListener("click", async () => {
  buscar("confirmar-reinicio").close();
  ocupar(true);
  let guardada = false;
  try {
    await solicitar("/demo/reiniciar", {});
    guardada = true;
    datos_demo.resaltados.clear();
    buscar("resultado-titulo").textContent = "Una nueva oportunidad";
    buscar("resultado").parentElement.classList.remove("error");
    buscar("resultado").replaceChildren(elemento("p", "texto-suave", `Las ${datos_demo.cuentas.length} cuentas vuelven al estado inicial. Empieza por la primera actividad disponible.`));
    await cargar_cuenta();
  } catch (error) { mostrar_error(error, guardada); }
  finally { ocupar(false); }
});
buscar("marcar-vistos").addEventListener("click", async () => {
  ocupar(true);
  let guardada = false;
  try {
    await solicitar(`/cuentas/${encodeURIComponent(datos_demo.cuenta)}/desbloqueos/marcar-vistos`, {});
    guardada = true;
    await cargar_cuenta();
  } catch (error) { mostrar_error(error, guardada); }
  finally { ocupar(false); }
});

inicializar();
