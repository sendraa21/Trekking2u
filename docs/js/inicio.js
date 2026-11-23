// Página de inicio: totales, filtros, mapa con todas las rutas y listado.
import {
  TIPOS, tipo, fmt, esc, crearMapa, alCargarEstilo, colorPorTipo,
  limitesDe, pintarPie, etiquetaTipo,
} from "./comun.js";
import { iniciarDatos, leerDatos } from "./datos.js";

const $ = (s) => document.querySelector(s);
const params = new URLSearchParams(location.search);
const estado = { anio: params.get("anio") || "todos", tipo: params.get("tipo") || "todos" };
let rutas = [];
let mapa = null;
let activa = null;
let popup = null;

const filtradas = () =>
  rutas.filter((r) =>
    (estado.anio === "todos" || String(r.anio) === estado.anio) &&
    (estado.tipo === "todos" || r.tipo === estado.tipo));

async function iniciar() {
  pintarPie();
  let todas;
  try {
    await iniciarDatos();
    const [datos, geo] = await Promise.all([leerDatos("rutas.json"), leerDatos("todas.json")]);
    rutas = datos.rutas || [];
    todas = geo;
  } catch (e) {
    $("#lista").innerHTML = '<p class="vacio">No hemos podido cargar las rutas. Prueba a recargar la página.</p>';
    console.error(e);
    return;
  }
  if (!rutas.length) {
    $("#lista").innerHTML = '<p class="vacio">Todavía no hay rutas. ¡A por la primera!</p>';
    return;
  }
  const anios = new Set(rutas.map((r) => String(r.anio)));
  if (!anios.has(estado.anio)) estado.anio = "todos";
  if (!rutas.some((r) => r.tipo === estado.tipo)) estado.tipo = "todos";

  pintarFiltros();
  iniciarMapa(todas);
  actualizar(false);
}

// ----------------------------------------------------------------- filtros
function chip(filtro, valor, texto) {
  const activo = estado[filtro] === valor;
  return `<button type="button" class="chip" data-filtro="${filtro}" data-valor="${esc(valor)}" aria-pressed="${activo}">${texto}</button>`;
}

function pintarFiltros() {
  const anios = [...new Set(rutas.map((r) => r.anio))].sort((a, b) => b - a);
  $("#filtro-anio").innerHTML =
    chip("anio", "todos", "Todas") + anios.map((a) => chip("anio", String(a), a)).join("");

  const tipos = Object.keys(TIPOS).filter((t) => rutas.some((r) => r.tipo === t));
  const filaTipo = $("#filtro-tipo");
  filaTipo.hidden = tipos.length < 2;
  filaTipo.innerHTML = chip("tipo", "todos", "Todos los tipos") +
    tipos.map((t) => chip("tipo", t, `<i class="punto" style="--c:${TIPOS[t].color}" aria-hidden="true"></i>${esc(TIPOS[t].nombre)}`)).join("");

  document.querySelector(".filtros").addEventListener("click", (e) => {
    const b = e.target.closest(".chip");
    if (!b) return;
    estado[b.dataset.filtro] = b.dataset.valor;
    for (const otro of document.querySelectorAll(`.chip[data-filtro="${b.dataset.filtro}"]`)) {
      otro.setAttribute("aria-pressed", String(otro === b));
    }
    const q = new URLSearchParams();
    if (estado.anio !== "todos") q.set("anio", estado.anio);
    if (estado.tipo !== "todos") q.set("tipo", estado.tipo);
    history.replaceState(null, "", q.toString() ? `?${q}` : location.pathname);
    actualizar(true);
  });
}

function actualizar(encuadrar) {
  const lista = filtradas();
  pintarTotales(lista);
  pintarLista(lista);
  filtrarMapa(lista, encuadrar);
}

// ----------------------------------------------------------------- totales
function pintarTotales(lista) {
  const suma = (k) => lista.reduce((s, r) => s + (r[k] || 0), 0);
  const km = suma("distancia_km");
  const datos = [
    ["Kilómetros", fmt.num(km, km < 100 ? 1 : 0), "km"],
    ["Desnivel positivo", fmt.num(suma("desnivel_pos_m")), "m"],
    ["Rutas", lista.length, ""],
    ["En movimiento", fmt.horas(suma("movimiento_s")), "h"],
  ];
  const cuando = estado.anio === "todos" ? "desde la primera ruta" : `en ${estado.anio}`;
  $("#totales-titulo").textContent = `Juntos, ${cuando}`;
  $("#totales").innerHTML = datos.map(([etq, valor, unidad]) => `
    <div class="dato">
      <span class="dato-etiqueta">${etq}</span>
      <span class="dato-valor">${valor}${unidad ? `<small> ${unidad}</small>` : ""}</span>
    </div>`).join("");
}

// ------------------------------------------------------------------ listado
function pintarLista(lista) {
  const cont = $("#lista");
  if (!lista.length) {
    cont.innerHTML = '<p class="vacio">No hay rutas con estos filtros.</p>';
    return;
  }
  const grupos = new Map();
  for (const r of lista) {
    if (!grupos.has(r.anio)) grupos.set(r.anio, []);
    grupos.get(r.anio).push(r);
  }
  cont.innerHTML = [...grupos].map(([anio, rs]) => `
    <section class="grupo">
      <h3 class="grupo-titulo">${anio} <span>${rs.length} ${rs.length === 1 ? "ruta" : "rutas"}</span></h3>
      <ul class="tarjetas">${rs.map(tarjeta).join("")}</ul>
    </section>`).join("");

  for (const a of cont.querySelectorAll(".tarjeta")) {
    a.addEventListener("mouseenter", () => resaltar(a.dataset.id));
    a.addEventListener("mouseleave", () => resaltar(null));
  }
}

function tarjeta(r) {
  const datos = [fmt.km(r.distancia_km), r.desnivel_pos_m != null ? `+${fmt.m(r.desnivel_pos_m)}` : null,
    fmt.duracion(r.movimiento_s ?? r.duracion_s)].filter(Boolean);
  return `
    <li><a class="tarjeta" href="ruta.html?id=${encodeURIComponent(r.id)}" data-id="${esc(r.id)}">
      <div class="tarjeta-cabeza">
        <h4>${esc(r.nombre)}</h4>
        ${etiquetaTipo(r.tipo)}
      </div>
      <p class="tarjeta-fecha">${fmt.fecha(r.inicio)}</p>
      <p class="tarjeta-datos">${datos.map((d) => `<span>${d}</span>`).join("")}</p>
    </a></li>`;
}

// --------------------------------------------------------------------- mapa
function iniciarMapa(todas) {
  mapa = crearMapa("mapa", { bounds: limitesDe(filtradas().length ? filtradas() : rutas), fitBoundsOptions: { padding: 40, maxZoom: 13 } });
  window.mapaTrekking = mapa; // para depurar desde la consola

  alCargarEstilo(mapa, () => {
    mapa.addSource("rutas", { type: "geojson", data: todas, promoteId: "id" });
    const activaExpr = ["boolean", ["feature-state", "activa"], false];
    mapa.addLayer({
      id: "rutas-borde", type: "line", source: "rutas",
      layout: { "line-join": "round", "line-cap": "round" },
      paint: { "line-color": "#ffffff", "line-width": ["case", activaExpr, 10, 6], "line-opacity": 0.95 },
    });
    mapa.addLayer({
      id: "rutas-linea", type: "line", source: "rutas",
      layout: { "line-join": "round", "line-cap": "round" },
      paint: { "line-color": colorPorTipo, "line-width": ["case", activaExpr, 6, 3] },
    });
    mapa.addLayer({
      id: "rutas-toque", type: "line", source: "rutas",
      paint: { "line-color": "#000000", "line-opacity": 0, "line-width": 20 },
    });
    // Punto de salida de cada ruta: con el mapa alejado, las líneas son
    // demasiado pequeñas para verse; los puntos se desvanecen al acercarse.
    mapa.addSource("inicios", { type: "geojson", data: puntosInicio(), promoteId: "id" });
    mapa.addLayer({
      id: "inicios", type: "circle", source: "inicios",
      paint: {
        "circle-radius": ["case", activaExpr, 9, 6.5],
        "circle-color": colorPorTipo,
        "circle-stroke-color": "#ffffff",
        "circle-stroke-width": 2,
        "circle-opacity": ["interpolate", ["linear"], ["zoom"], 10, 1, 12, 0],
        "circle-stroke-opacity": ["interpolate", ["linear"], ["zoom"], 10, 1, 12, 0],
      },
    });
    filtrarMapa(filtradas(), false);
  });

  for (const capa of ["rutas-toque", "inicios"]) {
    mapa.on("mousemove", capa, (e) => {
      mapa.getCanvas().style.cursor = "pointer";
      resaltar(e.features[0].properties.id);
    });
    mapa.on("mouseleave", capa, () => {
      mapa.getCanvas().style.cursor = "";
      resaltar(null);
    });
    mapa.on("click", capa, (e) => abrirPopup(e.features[0].properties.id, e.lngLat));
  }

  const tipos = Object.keys(TIPOS).filter((t) => rutas.some((r) => r.tipo === t));
  const leyenda = $("#leyenda");
  leyenda.hidden = tipos.length < 2;
  leyenda.innerHTML = tipos.map((t) =>
    `<li><i class="trazo" style="--c:${TIPOS[t].color}" aria-hidden="true"></i>${esc(TIPOS[t].nombre)}</li>`).join("");
}

function puntosInicio() {
  return {
    type: "FeatureCollection",
    features: rutas.map((r) => ({
      type: "Feature",
      geometry: { type: "Point", coordinates: r.punto_inicio },
      properties: { id: r.id, tipo: r.tipo },
    })),
  };
}

function filtrarMapa(lista, encuadrar) {
  if (!mapa) return;
  const filtro = ["in", ["get", "id"], ["literal", lista.map((r) => r.id)]];
  for (const capa of ["rutas-borde", "rutas-linea", "rutas-toque", "inicios"]) {
    if (mapa.getLayer(capa)) mapa.setFilter(capa, filtro);
  }
  popup?.remove();
  if (encuadrar && lista.length) {
    mapa.fitBounds(limitesDe(lista), { padding: 40, maxZoom: 13, duration: 800 });
  }
}

function resaltar(id) {
  if (id === activa) return;
  for (const fuente of ["rutas", "inicios"]) {
    if (!mapa?.getSource(fuente)) continue;
    if (activa) mapa.setFeatureState({ source: fuente, id: activa }, { activa: false });
    if (id) mapa.setFeatureState({ source: fuente, id }, { activa: true });
  }
  document.querySelector(".tarjeta.activa")?.classList.remove("activa");
  if (id) document.querySelector(`.tarjeta[data-id="${CSS.escape(id)}"]`)?.classList.add("activa");
  activa = id;
}

function abrirPopup(id, lngLat) {
  const r = rutas.find((x) => x.id === id);
  if (!r) return;
  popup?.remove();
  popup = new maplibregl.Popup({ maxWidth: "260px", offset: 8 })
    .setLngLat(lngLat)
    .setHTML(`
      <a class="popup" href="ruta.html?id=${encodeURIComponent(r.id)}">
        <strong>${esc(r.nombre)}</strong>
        <span>${fmt.fecha(r.inicio)} · ${esc(tipo(r.tipo).nombre)}</span>
        <span>${fmt.km(r.distancia_km)} · +${fmt.m(r.desnivel_pos_m ?? 0)}</span>
        <span class="popup-ir">Ver la ruta →</span>
      </a>`)
    .addTo(mapa);
}

iniciar();
