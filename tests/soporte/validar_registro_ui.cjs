/* Validación v2 con Playwright. Solo servidor local falso y SQLite descartable.
 * node tests/soporte/validar_registro_ui.cjs http://127.0.0.1:8790 docs/evidencias/registro-v2
 * Reinicia exclusivamente esa demo temporal. No usar una base persistente.
 */
"use strict";
const { chromium } = require("playwright");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const base = new URL(process.argv[2] || "http://127.0.0.1:8787");
const evidencias = process.argv[3] || "docs/evidencias/registro-v2";
assert.equal(base.hostname, "127.0.0.1");
const pasos = [];
const registrar = (texto) => { pasos.push(texto); process.stdout.write(`${texto}\n`); };

async function ejecutar() {
  const navegador = await chromium.launch({ headless: true, channel: process.env.CANAL_NAVEGADOR || "msedge" });
  const contexto = await navegador.newContext({ viewport: { width: 1440, height: 1000 } });
  const api = contexto.request, errores = [], peticiones = [];
  fs.mkdirSync(evidencias, { recursive: true });
  const datos = (cuenta, extra = {}) => ({ cuenta, actividad: "REG-ACT08", ...extra });
  async function pedir(ruta, cuerpo) {
    const respuesta = cuerpo === undefined ? await api.get(`${base.origin}${ruta}`) : await api.post(`${base.origin}${ruta}`, { data: cuerpo });
    assert.equal(respuesta.status(), 200, await respuesta.text());
    return respuesta.json();
  }
  const consultar = (cuenta) => pedir(`/cuentas/${cuenta}/actividades/REG-ACT08/registro`);
  const auditoria = (cuenta) => pedir(`/demo/registro/${cuenta}/REG-ACT08/evaluaciones`);
  const inicial = (registro, item) => registro.respuestas.find((fila) => fila.item === item).conversacion[0].texto;
  const registrar_peticion = (peticion) => peticiones.push({ ruta: new URL(peticion.url()).pathname,
    metodo: peticion.method(), datos: peticion.postDataJSON() });
  async function preparar(pagina, ctx) {
    pagina.on("pageerror", (error) => errores.push(error.message));
    pagina.on("request", registrar_peticion);
    await ctx.route("**/*", (ruta) => new URL(ruta.request().url()).origin === base.origin ? ruta.continue() : ruta.abort());
  }
  const listo = (pagina) => pagina.waitForFunction(() => !document.querySelector("#actualizar").disabled);
  const pulsar = async (pagina, id) => { await pagina.locator(`#${id}`).click(); await listo(pagina); };
  const elegir = async (pagina, numero) => { await listo(pagina); await pagina.locator(`[data-item="REG-HAB-${numero}"]`).click(); };
  const cambiar = async (pagina, cuenta) => { await pagina.locator("#cuenta").selectOption(cuenta); await listo(pagina); };
  const recargar = async (pagina) => { await pagina.reload(); await listo(pagina); };
  const escribir = async (pagina, texto, boton = "enviar") => { await pagina.locator("#texto").fill(texto); await pulsar(pagina, boton); };
  const captura = async (pagina, nombre) => {
    await pagina.evaluate(() => { document.activeElement.blur(); window.scrollTo(0, 0); });
    await pagina.screenshot({ path: path.join(evidencias, nombre), fullPage: true });
  };
  try {
    await pedir("/demo/reiniciar", {});
    const pagina = await contexto.newPage();
    await preparar(pagina, contexto);
    let fallo_inicio = true;
    await pagina.route("**/actividades/REG-ACT08/items-registro", async (ruta) => {
      if (fallo_inicio) { fallo_inicio = false; await ruta.fulfill({ status: 503, json: { detail: "Carga temporalmente no disponible" } }); }
      else await ruta.continue();
    });
    await pagina.goto(`${base.origin}/demo/registro`);
    await listo(pagina);
    assert.equal(await pagina.locator("#continuar").isDisabled(), true);
    await pulsar(pagina, "actualizar");
    assert.equal(await pagina.locator("#lineas-lumi p").count(), 3);
    await pagina.locator(".salto").focus(); await pagina.keyboard.press("Enter");
    assert.equal(await pagina.evaluate(() => document.activeElement.id), "actividad");
    await captura(pagina, "explicacion-desktop.png");
    await pulsar(pagina, "siguiente-dia");
    await pulsar(pagina, "continuar");
    await recargar(pagina);
    assert.equal((await consultar("est-ana")).posicion, "plan");
    assert.equal(await pagina.locator("#fecha").inputValue(), "2026-10-02T10:00");
    assert.equal(await pagina.locator("#iconos-items button").count(), 3);
    assert.equal(await pagina.locator("#completar").isDisabled(), true);
    registrar("Escritorio: reintento de carga, explicación, teclado, fecha y posición recuperable.");

    const texto_inicial = "Comunicación [falta:C2]";
    await escribir(pagina, texto_inicial, "guardar-borrador");
    await recargar(pagina);
    assert.equal(await pagina.locator("#texto").inputValue(), texto_inicial);
    assert.equal(await pagina.locator("#conversacion").isVisible(), false);
    await pulsar(pagina, "enviar");
    assert.equal(await pagina.locator("#texto").inputValue(), "");
    assert.equal(await pagina.locator("#enviar").innerText(), "Responder");
    assert.equal(await pagina.locator("#item-estado").innerText(), "Pregunta pendiente");
    assert.equal(await pagina.locator(".editar-respuesta").count(), 0);
    assert.equal(await pagina.locator(".mensaje-estudiante .texto-mensaje").innerText(), texto_inicial);
    const pregunta_1 = await pagina.locator(".pregunta-pendiente .texto-mensaje").innerText();
    assert.match(pregunta_1, /C2/); assert.doesNotMatch(pregunta_1, /C1/);
    const turno_1 = "En grupo todavía me cuesta [vaga]";
    await escribir(pagina, turno_1, "guardar-borrador");
    await recargar(pagina);
    assert.equal(await pagina.locator("#texto").inputValue(), turno_1);
    assert.equal(await pagina.locator(".pregunta-pendiente .texto-mensaje").innerText(), pregunta_1);
    await pulsar(pagina, "enviar");
    assert.equal(await pagina.locator("#texto").inputValue(), "");
    assert.equal(await pagina.locator(".mensaje-lumi").count(), 2);
    assert.equal(await pagina.locator(".mensaje-estudiante").count(), 2);
    assert.equal(inicial(await consultar("est-ana"), "REG-HAB-1"), texto_inicial);
    const turno_2 = "También en los debates [vaga]";
    await escribir(pagina, turno_2, "guardar-borrador");
    await recargar(pagina);
    assert.equal(await pagina.locator("#texto").inputValue(), turno_2);
    await captura(pagina, "turno-2-desktop.png");
    assert.equal(peticiones.some((peticion) => peticion.ruta.endsWith("/evaluaciones")), false);
    await pulsar(pagina, "enviar");
    assert.equal(await pagina.locator("#item-estado").innerText(), "Listo");
    assert.equal(await pagina.locator(".mensaje-lumi").count(), 2);
    assert.equal(await pagina.locator(".mensaje-estudiante").count(), 3);
    assert.equal(await pagina.locator("#continuar-sin-responder").isVisible(), false);
    const audit_antes = await auditoria("est-ana");
    assert.equal(audit_antes.length, 3);
    for (const [orden, texto] of [["inicial", "Comunicación editada al terminar"], [1, "Primera respuesta editada"], [2, "Segunda respuesta editada"]]) {
      await pagina.locator(`[data-editar-orden="${orden}"]`).click();
      await escribir(pagina, texto);
      assert.equal(await pagina.locator("#texto").inputValue(), texto);
      assert.equal(await pagina.locator("#guardar-borrador").isDisabled(), true);
    }
    assert.deepEqual(await auditoria("est-ana"), audit_antes);
    await recargar(pagina);
    assert.match(await pagina.locator("#conversacion").innerText(), /Primera respuesta editada/);
    registrar("Dos seguimientos: borradores y recarga en ambos, inicial intacto, máximo dos, edición individual sin reevaluar.");

    // Los buffers de edición no se mezclan al elegir otra respuesta.
    await pagina.locator('[data-editar-orden="1"]').click();
    await pagina.locator("#texto").fill("Edición local del primer turno");
    await pagina.locator('[data-editar-orden="2"]').click();
    assert.equal(await pagina.locator("#texto").inputValue(), "Segunda respuesta editada");
    await pagina.locator('[data-editar-orden="1"]').click();
    assert.equal(await pagina.locator("#texto").inputValue(), "Edición local del primer turno");
    await elegir(pagina, 2);
    await escribir(pagina, "Acción [falla]");
    assert.equal(await pagina.locator("#item-estado").innerText(), "Pregunta pendiente");
    const antes_generico = await auditoria("est-ana");
    await escribir(pagina, "En el próximo trabajo grupal diré una idea");
    assert.deepEqual(await auditoria("est-ana"), antes_generico);
    await elegir(pagina, 3);
    await escribir(pagina, "Participaré"); // Corto, adecuado por el falso: siempre se evaluó.
    assert.equal(await pagina.locator("#item-estado").innerText(), "Listo");
    assert.match(await pagina.locator("#lista-novedades").innerText(), /Pensador/i);
    await pulsar(pagina, "marcar-vistos");
    await pulsar(pagina, "completar");
    await recargar(pagina);
    assert.match(await pagina.locator("#estado-actividad").innerText(), /Completada/);
    assert.doesNotMatch(await pagina.locator("#actividad").innerText(), /ADECUADA|VAGA|NO_EVALUADA|RESPALDO_LONGITUD|requiere_atencion/);
    registrar("Respaldo genérico sin reevaluación, inicial corto evaluado, LOG-PENSADOR, completar y recargar.");

    await cambiar(pagina, "est-luis");
    assert.equal(await pagina.locator("#explicacion").isVisible(), true);
    assert.equal(await pagina.locator("#texto").inputValue(), "");
    assert.equal(await pagina.locator("#conversacion li").count(), 0);
    await pulsar(pagina, "continuar"); await elegir(pagina, 1);
    await escribir(pagina, "Empatía [vaga]");
    await escribir(pagina, "Borrador que prefiero omitir", "guardar-borrador");
    await pulsar(pagina, "continuar-sin-responder");
    const omitida = (await consultar("est-luis")).respuestas[0];
    assert.equal(omitida.estado, "FINAL"); assert.equal(omitida.conversacion.length, 2);
    assert.equal(await pagina.locator(".turno-omitido").innerText(), "Preferiste seguir.");
    assert.equal(await pagina.locator(".editar-respuesta").count(), 1);
    await cambiar(pagina, "apo-rosa");
    assert.equal(await pagina.locator("#sin-acceso").isVisible(), true);
    assert.equal(await pagina.locator("#detalle-tecnico").isVisible(), false);
    assert.equal(await pagina.locator("#conversacion li").count(), 0);
    await cambiar(pagina, "est-ana"); await elegir(pagina, 1);
    assert.equal(await pagina.locator("#texto").inputValue(), "Comunicación editada al terminar");
    registrar("Aislamiento entre cuentas y borradores locales; Prefiero seguir conserva la pregunta y descarta su borrador.");

    // Un conflicto en un turno conserva su texto local, sin reenviar automáticamente.
    await cambiar(pagina, "est-luis"); await elegir(pagina, 2);
    await escribir(pagina, "Voy a hablar [vaga]");
    let conflicto = true, inicio_espera, liberar_espera;
    const esperando = new Promise((resolver) => { inicio_espera = resolver; });
    const continuar_espera = new Promise((resolver) => { liberar_espera = resolver; });
    await pagina.route("**/acciones/registro/responder-seguimiento", async (ruta) => {
      const cuerpo = ruta.request().postDataJSON();
      if (conflicto && cuerpo.texto.includes("[conflicto]")) {
        conflicto = false;
        await pedir("/acciones/registro/guardar-borrador", { ...cuerpo, texto: "Borrador paralelo" });
        await ruta.fulfill({ status: 409, json: { detail: { mensaje: "El registro cambió durante el envío" } } });
      } else { if (cuerpo.texto.includes("[espera]")) { inicio_espera(); await continuar_espera; } await ruta.continue(); }
    });
    await escribir(pagina, "Mi turno local [conflicto]");
    assert.match(await pagina.locator("#mensaje").innerText(), /Revisa el estado actual/);
    assert.equal(await pagina.locator("#texto").inputValue(), "Mi turno local [conflicto]");
    await pagina.locator("#texto").fill("En el trabajo de mañana [espera]");
    await pagina.locator("#enviar").click(); await esperando;
    assert.equal(await pagina.locator("#mensaje").innerText(), "Lumi está leyendo tu respuesta…");
    assert.equal(await pagina.locator("#rueda-espera").isVisible(), true);
    assert.equal(await pagina.locator("#cuenta").isDisabled(), true);
    await captura(pagina, "espera-desktop.png");
    liberar_espera(); await listo(pagina);
    registrar("Conflicto de seguimiento 409 sin reenvío; espera visible y controles bloqueados.");

    await elegir(pagina, 3);
    const texto_literal = '<img src=x onerror="alert(1)"> [vaga]';
    await escribir(pagina, texto_literal);
    assert.equal(await pagina.locator("#conversacion img").count(), 0);
    assert.equal(await pagina.locator(".mensaje-estudiante .texto-mensaje").innerText(), texto_literal);
    await pagina.locator("#texto").fill("   ");
    assert.equal(await pagina.locator("#enviar").isDisabled(), true);
    await escribir(pagina, "Mi primera respuesta de seguimiento [vaga]");
    await escribir(pagina, "Mi borrador que no enviaré", "guardar-borrador");
    await pulsar(pagina, "continuar-sin-responder");
    assert.equal(await pagina.locator(".mensaje-estudiante").count(), 2);
    assert.equal(await pagina.locator(".mensaje-lumi").count(), 2);
    assert.equal(await pagina.locator(".editar-respuesta").count(), 2);
    assert.equal(await pagina.locator(".turno-omitido").count(), 1);
    const antes_editar = await auditoria("est-luis");
    await pagina.locator('[data-editar-orden="1"]').click();
    let fallo_lectura = true;
    await pagina.route("**/cuentas/est-luis/actividades/REG-ACT08/registro", async (ruta) => {
      if (fallo_lectura) { fallo_lectura = false; await ruta.fulfill({ status: 503, json: { detail: "Lectura temporalmente no disponible" } }); }
      else await ruta.continue();
    });
    await escribir(pagina, "Turno editado aunque falle la actualización");
    assert.match(await pagina.locator("#mensaje").innerText(), /Respuesta guardada.*Pulsa Actualizar/);
    await pulsar(pagina, "actualizar");
    assert.equal(await pagina.locator("#texto").inputValue(), "Turno editado aunque falle la actualización");
    assert.deepEqual(await auditoria("est-luis"), antes_editar);
    registrar("Prefiero seguir tras el primer turno: conserva respuestas y omite el segundo; texto literal seguro, vacío bloqueado y lectura fallida recuperable.");

    // Auditoría diferida se descarta si se cambia de cuenta.
    let comenzar_auditoria;
    const lectura_auditoria = new Promise((resolver) => { comenzar_auditoria = resolver; });
    await pagina.route("**/demo/registro/est-luis/REG-ACT08/evaluaciones", async (ruta) => {
      const respuesta = await ruta.fetch(); comenzar_auditoria();
      await new Promise((resolver) => setTimeout(resolver, 700)); await ruta.fulfill({ response: respuesta });
    });
    await pagina.locator("#detalle-tecnico summary").click(); await lectura_auditoria;
    await cambiar(pagina, "est-ana"); await pagina.locator("#detalle-tecnico summary").click();
    await pagina.waitForFunction(() => document.querySelectorAll(".evaluacion").length === 5);
    await new Promise((resolver) => setTimeout(resolver, 850));
    assert.equal(await pagina.locator(".evaluacion").count(), 5);
    assert.match(await pagina.locator(".evaluacion").first().innerText(), /Evaluación 1/);
    await captura(pagina, "tecnico-desktop.png");
    registrar("Detalle técnico plegado, números v2 y auditoría tardía aislada entre cuentas.");

    await pedir("/demo/reiniciar", {});
    const movil = await navegador.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
    const pantalla = await movil.newPage(); await preparar(pantalla, movil);
    await pantalla.goto(`${base.origin}/demo/registro?cuenta=est-ana`); await listo(pantalla);
    await captura(pantalla, "explicacion-movil.png"); await pulsar(pantalla, "continuar");
    await escribir(pantalla, "Empatía [vaga]");
    await escribir(pantalla, "Escucharé cuando hablemos [vaga]");
    await escribir(pantalla, "Mi borrador del segundo turno móvil", "guardar-borrador");
    await recargar(pantalla);
    assert.equal(await pantalla.locator("#texto").inputValue(), "Mi borrador del segundo turno móvil");
    for (const ancho of [390, 360]) {
      await pantalla.setViewportSize({ width: ancho, height: 844 });
      assert.equal(await pantalla.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true);
    }
    await captura(pantalla, "turno-2-movil.png"); await pulsar(pantalla, "enviar");
    for (const [item, texto] of [[2, "[falla] Practicaré expresando una idea durante el próximo trabajo de mi colegio."],
      [3, "[atencion] Notaré que puedo contar mi idea con tranquilidad."]]) {
      await elegir(pantalla, item); await escribir(pantalla, texto);
      assert.equal(await pantalla.locator("#item-estado").innerText(), "Listo");
      assert.equal(await pantalla.locator(".mensaje-lumi").count(), 0);
      assert.equal(await pantalla.locator("#mensaje").innerText(), "Respuesta guardada.");
    }
    await pulsar(pantalla, "completar"); await captura(pantalla, "completado-movil.png");
    assert.doesNotMatch(await pantalla.locator("#actividad").innerText(), /ADECUADA|VAGA|NO_EVALUADA|RESPALDO_LONGITUD|requiere_atencion/);
    await pantalla.locator("#reiniciar").click(); await pantalla.locator("#cancelar-reinicio").click();
    assert.equal((await consultar("est-ana")).respuestas.length, 3);
    await pantalla.locator("#reiniciar").click(); await pantalla.locator("#confirmar-borrar").click(); await listo(pantalla);
    assert.equal(await pantalla.locator("#explicacion").isVisible(), true);
    assert.equal((await consultar("est-ana")).respuestas.length, 0);
    assert.equal((await consultar("est-luis")).respuestas.length, 0);
    assert.equal(await pantalla.locator("#conversacion li").count(), 0);
    registrar("Móvil 390/360 px: dos turnos, recarga de borrador, fallo y atención sin marcas técnicas, completar y reinicio confirmado.");
    await movil.close();

    const permitida = (peticion) => peticion.metodo === "GET" ?
      /^\/demo\/(registro$|recursos\/)/.test(peticion.ruta) || peticion.ruta === "/cuentas" ||
      peticion.ruta === "/actividades/REG-ACT08/items-registro" ||
      /^\/cuentas\/(est-ana|est-luis)\/(estado|actividades\/REG-ACT08\/registro|desbloqueos)$/.test(peticion.ruta) ||
      /^\/demo\/registro\/(est-ana|est-luis)\/REG-ACT08\/evaluaciones$/.test(peticion.ruta) :
      /^\/acciones\/(guardar-posicion|completar-actividad|registro\/(guardar-borrador|enviar|responder-seguimiento|continuar-sin-responder))$/.test(peticion.ruta) ||
      /^\/cuentas\/(est-ana|est-luis)\/desbloqueos\/marcar-vistos$/.test(peticion.ruta) || peticion.ruta === "/demo/reiniciar";
    assert.deepEqual(peticiones.filter((peticion) => !permitida(peticion)), []);
    const turnos = peticiones.filter((peticion) => peticion.ruta.endsWith("/responder-seguimiento"));
    assert.ok(turnos.some((peticion) => peticion.datos.orden === 1));
    assert.ok(turnos.some((peticion) => peticion.datos.orden === 2));
    assert.ok(turnos.some((peticion) => !("orden" in peticion.datos)));
    assert.deepEqual(errores, []);
    fs.writeFileSync(path.join(evidencias, "comprobaciones.json"), JSON.stringify({ version: "v2", evaluador: "falso",
      navegador: "Edge / Chromium", escritorio: "1440 × 1000", movil: "390 y 360 × 844",
      errores_javascript: errores, peticiones_interfaz: peticiones.length, pasos }, null, 2) + "\n");
    registrar("Sin errores JavaScript, sin llamadas externas ni endpoints auxiliares nuevos.");
  } finally { await navegador.close(); }
}
ejecutar().catch((error) => { process.stderr.write(`${error.stack}\n`); process.exitCode = 1; });
