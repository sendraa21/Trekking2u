// Utilidades compartidas por todas las páginas.

export const CFG = Object.assign(
  {
    maptilerKey: "",
    estiloMapa: "outdoor-v2",
    estiloSatelite: "hybrid",
    titulo: "Trekking2u",
    lema: "Las rutas que hacemos juntos",
    firma: "Una idea de Gema, hecha entre los dos.",
  },
  window.TREKKING || {},
);

export const hayClave = Boolean(CFG.maptilerKey && CFG.maptilerKey.trim());
const ZONA = "Europe/Madrid";

// Colores por tipo de ruta (paleta categórica validada; el orden importa).
// El mapa base siempre es claro, así que se usan los tonos para fondo claro.
export const TIPOS = {
  senderismo: { nombre: "Senderismo", color: "#2a78d6" },
  navegacion: { nombre: "Navegación", color: "#eb6834" },
  trail: { nombre: "Trail", color: "#1baf7a" },
  otro: { nombre: "Otra", color: "#898781" },
};
export const tipo = (t) => TIPOS[t] || TIPOS.otro;

export const colorPorTipo = [
  "match", ["get", "tipo"],
  "senderismo", TIPOS.senderismo.color,
  "navegacion", TIPOS.navegacion.color,
  "trail", TIPOS.trail.color,
  TIPOS.otro.color,
];

// ---------------------------------------------------------------- formatos
const numero = (dec) =>
  new Intl.NumberFormat("es-ES", { minimumFractionDigits: dec, maximumFractionDigits: dec });

export const fmt = {
  num: (v, dec = 0) => (v == null ? null : numero(dec).format(v)),
  km: (v, dec = 1) => (v == null ? null : `${numero(dec).format(v)} km`),
  m: (v) => (v == null ? null : `${numero(0).format(v)} m`),
  duracion(s) {
    if (s == null) return null;
    const min = Math.round(s / 60);
    const h = Math.floor(min / 60);
    const m = min % 60;
    return h ? `${h} h ${String(m).padStart(2, "0")} min` : `${m} min`;
  },
  horas(s) {
    if (s == null) return null;
    return numero(s < 36000 ? 1 : 0).format(s / 3600);
  },
  ritmo(s) {
    if (s == null) return null;
    const t = Math.round(s);
    return `${Math.floor(t / 60)}:${String(t % 60).padStart(2, "0")} min/km`;
  },
  fecha: (iso) =>
    new Intl.DateTimeFormat("es-ES", { day: "numeric", month: "short", year: "numeric", timeZone: ZONA })
      .format(new Date(iso)),
  fechaLarga: (iso) =>
    new Intl.DateTimeFormat("es-ES", { weekday: "long", day: "numeric", month: "long", year: "numeric", timeZone: ZONA })
      .format(new Date(iso)),
  hora: (iso) =>
    new Intl.DateTimeFormat("es-ES", { hour: "numeric", minute: "2-digit", timeZone: ZONA }).format(new Date(iso)),
};

export function esc(texto) {
  return String(texto ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[c]);
}

export async function cargarJSON(url) {
  const r = await fetch(url, { cache: "no-cache" });
  if (!r.ok) throw new Error(`${url}: ${r.status}`);
  return r.json();
}

export function limitesDe(rutas) {
  const b = [180, 90, -180, -90];
  for (const r of rutas) {
    b[0] = Math.min(b[0], r.bbox[0]);
    b[1] = Math.min(b[1], r.bbox[1]);
    b[2] = Math.max(b[2], r.bbox[2]);
    b[3] = Math.max(b[3], r.bbox[3]);
  }
  return [[b[0], b[1]], [b[2], b[3]]];
}

// ------------------------------------------------------------------- mapas
export function estiloURL(satelite = false) {
  if (!hayClave) return "https://tiles.openfreemap.org/styles/liberty";
  const estilo = satelite ? CFG.estiloSatelite : CFG.estiloMapa;
  return `https://api.maptiler.com/maps/${estilo}/style.json?key=${encodeURIComponent(CFG.maptilerKey)}`;
}

export function urlTerreno() {
  return `https://api.maptiler.com/tiles/terrain-rgb-v2/tiles.json?key=${encodeURIComponent(CFG.maptilerKey)}`;
}

export function crearMapa(contenedor, opciones = {}) {
  const tactil = window.matchMedia("(pointer: coarse)").matches;
  const mapa = new maplibregl.Map({
    container: contenedor,
    style: estiloURL(false),
    attributionControl: { compact: true },
    cooperativeGestures: tactil, // en el móvil, un dedo desplaza la página y dos mueven el mapa
    maxPitch: 75,
    ...opciones,
  });
  mapa.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-right");
  mapa.addControl(new maplibregl.FullscreenControl(), "top-right");
  mapa.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");
  if (!hayClave) avisoSinClave(mapa.getContainer());
  return mapa;
}

// Se ejecuta con el estilo inicial y cada vez que se cambia (mapa/satélite),
// porque al cambiar de estilo se pierden las capas propias.
export function alCargarEstilo(mapa, fn) {
  mapa.on("style.load", fn);
}

function avisoSinClave(contenedor) {
  const aviso = document.createElement("p");
  aviso.className = "mapa-aviso";
  aviso.textContent = "Mapa básico: falta la clave de MapTiler en config.js";
  contenedor.appendChild(aviso);
}

// ------------------------------------------------------------- comunes UI
export function pintarPie() {
  for (const el of document.querySelectorAll("[data-firma]")) el.textContent = CFG.firma;
  for (const el of document.querySelectorAll("[data-lema]")) el.textContent = CFG.lema;
}

export function etiquetaTipo(t) {
  const info = tipo(t);
  return `<span class="etiqueta" style="--c:${info.color}"><i aria-hidden="true"></i>${esc(info.nombre)}</span>`;
}
