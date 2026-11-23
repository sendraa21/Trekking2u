// Ficha de una ruta: mapa (2D/3D, mapa/satélite), datos y perfil de elevación.
import {
  hayClave, tipo, fmt, esc, crearMapa, alCargarEstilo, estiloURL,
  urlTerreno, pintarPie, etiquetaTipo,
} from "./comun.js";
import { iniciarDatos, leerDatos } from "./datos.js";
import { crearPerfil } from "./perfil.js";

const $ = (s) => document.querySelector(s);
const id = new URLSearchParams(location.search).get("id");
let mapa = null;
let ruta = null;
let feature = null;
let en3d = false;
let satelite = false;
let cursor = null;

async function iniciar() {
  pintarPie();
  if (!id) return noEncontrada();
  let indice;
  try {
    await iniciarDatos();
    indice = await leerDatos("rutas.json");
    const r = (indice.rutas || []).find((x) => x.id === id);
    if (!r) return noEncontrada();
    feature = await leerDatos(r.archivo);
  } catch (e) {
    console.error(e);
    return noEncontrada();
  }
  ruta = feature.properties;
  document.title = `${ruta.nombre} · Trekking2u`;
  pintarCabecera();
  pintarDatos();
  pintarVecinas(indice.rutas || []);
  iniciarMapa();
  crearPerfil($("#perfil"), ruta.perfil, {
    color: tipo(ruta.tipo).color,
    alMover: moverCursor,
    alSalir: () => moverCursor(null),
  });
}

function noEncontrada() {
  $("#ficha").innerHTML = `
    <div class="vacio">
      <p>No encontramos esta ruta.</p>
      <p><a href="./">Volver a todas las rutas</a></p>
    </div>`;
}

function pintarCabecera() {
  $("#titulo").textContent = ruta.nombre;
  $("#meta").innerHTML = `
    <span>${esc(fmt.fechaLarga(ruta.inicio))}</span>
    <span>Salida a las ${esc(fmt.hora(ruta.inicio))}</span>
    ${etiquetaTipo(ruta.tipo)}`;
  const desc = $("#descripcion");
  desc.hidden = !ruta.descripcion;
  desc.textContent = ruta.descripcion || "";
}

function pintarDatos() {
  const fc = (v) => (v ? `${v} ppm` : null);
  const datos = [
    ["Distancia", fmt.km(ruta.distancia_km, 2), true],
    ["Desnivel +", fmt.m(ruta.desnivel_pos_m), true],
    ["En movimiento", fmt.duracion(ruta.movimiento_s), true],
    ["Desnivel −", fmt.m(ruta.desnivel_neg_m)],
    ["Tiempo total", fmt.duracion(ruta.duracion_s)],
    ["Ritmo medio", fmt.ritmo(ruta.ritmo_s_km)],
    ["Altitud máxima", fmt.m(ruta.alt_max_m)],
    ["Altitud mínima", fmt.m(ruta.alt_min_m)],
    ["FC media", fc(ruta.fc_media)],
    ["FC máxima", fc(ruta.fc_max)],
  ].filter(([, v]) => v != null);
  $("#datos").innerHTML = datos.map(([etq, valor, destacado]) => `
    <div class="dato${destacado ? " dato-destacado" : ""}">
      <span class="dato-etiqueta">${etq}</span>
      <span class="dato-valor">${esc(valor)}</span>
    </div>`).join("");
}

function pintarVecinas(rutas) {
  const i = rutas.findIndex((r) => r.id === ruta.id);
  if (i < 0) return;
  const enlace = (r, clase, texto) => r
    ? `<a class="vecina ${clase}" href="ruta.html?id=${encodeURIComponent(r.id)}"><span>${texto}</span><strong>${esc(r.nombre)}</strong></a>`
    : "<span></span>";
  // rutas.json va de la más reciente a la más antigua
  $("#vecinas").innerHTML = enlace(rutas[i + 1], "anterior", "← Ruta anterior") +
    enlace(rutas[i - 1], "siguiente", "Ruta siguiente →");
}

// --------------------------------------------------------------------- mapa
function marca(clase, titulo) {
  const e = document.createElement("div");
  e.className = `marca ${clase}`;
  e.title = titulo;
  return e;
}

function iniciarMapa() {
  const [o, s, e, n] = ruta.bbox;
  const color = tipo(ruta.tipo).color;
  mapa = crearMapa("mapa", { bounds: [[o, s], [e, n]], fitBoundsOptions: { padding: 48 } });

  alCargarEstilo(mapa, () => {
    mapa.addSource("ruta", { type: "geojson", data: feature });
    mapa.addLayer({
      id: "ruta-borde", type: "line", source: "ruta",
      layout: { "line-join": "round", "line-cap": "round" },
      paint: { "line-color": "#ffffff", "line-width": 8, "line-opacity": 0.95 },
    });
    mapa.addLayer({
      id: "ruta-linea", type: "line", source: "ruta",
      layout: { "line-join": "round", "line-cap": "round" },
      paint: { "line-color": color, "line-width": 4.5 },
    });
    if (en3d) activarTerreno();
  });

  const coords = feature.geometry.coordinates;
  const ini = coords[0];
  const fin = coords[coords.length - 1];
  const circular = Math.hypot(ini[0] - fin[0], ini[1] - fin[1]) < 0.001;
  new maplibregl.Marker({ element: marca("marca-salida", circular ? "Salida y llegada" : "Salida") })
    .setLngLat(ini.slice(0, 2)).addTo(mapa);
  if (!circular) {
    new maplibregl.Marker({ element: marca("marca-llegada", "Llegada") }).setLngLat(fin.slice(0, 2)).addTo(mapa);
  }
  const elCursor = marca("marca-cursor", "");
  elCursor.style.setProperty("--c", color);
  cursor = new maplibregl.Marker({ element: elCursor }).setLngLat(ini.slice(0, 2));

  const b3d = $("#boton-3d");
  const bSat = $("#boton-satelite");
  if (!hayClave) {
    b3d.disabled = true;
    b3d.title = "Necesita la clave de MapTiler en config.js";
    bSat.hidden = true;
  }
  b3d.addEventListener("click", alternar3D);
  bSat.addEventListener("click", () => {
    satelite = !satelite;
    bSat.setAttribute("aria-pressed", String(satelite));
    bSat.textContent = satelite ? "Mapa" : "Satélite";
    mapa.setStyle(estiloURL(satelite), { diff: false });
  });
}

function activarTerreno() {
  if (!mapa.getSource("dem")) {
    mapa.addSource("dem", { type: "raster-dem", url: urlTerreno(), tileSize: 256 });
  }
  mapa.setTerrain({ source: "dem", exaggeration: 1.3 });
  try {
    mapa.setSky({
      "sky-color": "#8fc1ea", "horizon-color": "#e6eef4", "fog-color": "#ffffff",
      "sky-horizon-blend": 0.6, "horizon-fog-blend": 0.6, "fog-ground-blend": 0.4,
    });
  } catch { /* versiones sin cielo */ }
}

function alternar3D() {
  en3d = !en3d;
  const b = $("#boton-3d");
  b.setAttribute("aria-pressed", String(en3d));
  b.textContent = en3d ? "Ver en 2D" : "Ver en 3D";
  if (en3d) {
    activarTerreno();
    mapa.easeTo({ pitch: 62, bearing: mapa.getBearing() || -25, duration: 1600 });
  } else {
    mapa.setTerrain(null);
    mapa.easeTo({ pitch: 0, bearing: 0, duration: 1000 });
  }
}

function moverCursor(fila) {
  if (!cursor) return;
  if (!fila || fila[2] == null) {
    cursor.remove();
    return;
  }
  cursor.setLngLat([fila[2], fila[3]]).addTo(mapa);
}

iniciar();
