// Perfil de elevación en SVG, con cruceta al pasar el ratón o el dedo.
// filas: [[km, altitud, lon, lat], ...]

import { fmt } from "./comun.js";

const NS = "http://www.w3.org/2000/svg";

function el(nombre, attrs = {}, padre) {
  const e = document.createElementNS(NS, nombre);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (padre) padre.appendChild(e);
  return e;
}

function escala(lo, hi, n) {
  const paso0 = (hi - lo) / n || 1;
  const mag = 10 ** Math.floor(Math.log10(paso0));
  const r = paso0 / mag;
  const paso = (r >= 7.5 ? 10 : r >= 3.5 ? 5 : r >= 1.5 ? 2 : 1) * mag;
  const ini = Math.floor(lo / paso) * paso;
  const fin = Math.ceil(hi / paso) * paso;
  const marcas = [];
  for (let v = ini; v <= fin + paso / 2; v += paso) marcas.push(Math.round(v * 1000) / 1000);
  return { lo: ini, hi: fin, marcas };
}

export function crearPerfil(contenedor, filas, { color, alMover, alSalir } = {}) {
  const datos = (filas || []).filter((f) => f[1] != null);
  if (datos.length < 2) {
    contenedor.innerHTML = '<p class="vacio">Esta ruta no tiene datos de altitud.</p>';
    return;
  }
  const eles = datos.map((f) => f[1]);
  const min = Math.min(...eles);
  const max = Math.max(...eles);
  const kmTotal = datos[datos.length - 1][0];

  const svg = el("svg", {
    class: "perfil-svg",
    role: "img",
    tabindex: "0",
    "aria-label": `Perfil de elevación: de ${fmt.m(min)} a ${fmt.m(max)} en ${fmt.km(kmTotal)}`,
  });
  const ayuda = document.createElement("div");
  ayuda.className = "perfil-tooltip";
  ayuda.hidden = true;
  contenedor.replaceChildren(svg, ayuda);

  let x, y, ancho, alto, m, indice = -1;

  function dibujar() {
    ancho = contenedor.clientWidth;
    alto = ancho < 600 ? 190 : 230;
    m = { izq: 52, der: 14, arr: 14, aba: 30 };
    svg.setAttribute("viewBox", `0 0 ${ancho} ${alto}`);
    svg.setAttribute("height", alto);
    svg.replaceChildren();

    const pad = Math.max(10, (max - min) * 0.08);
    const ey = escala(min - pad, max + pad, 4);
    const ex = escala(0, kmTotal, ancho < 600 ? 4 : 8);
    const fx = (km) => m.izq + (km / kmTotal) * (ancho - m.izq - m.der);
    const fy = (e) => m.arr + ((ey.hi - e) / (ey.hi - ey.lo)) * (alto - m.arr - m.aba);
    x = fx;
    y = fy;

    const rejilla = el("g", { class: "perfil-rejilla" }, svg);
    for (const v of ey.marcas) {
      el("line", { x1: m.izq, x2: ancho - m.der, y1: fy(v), y2: fy(v) }, rejilla);
      const t = el("text", { x: m.izq - 8, y: fy(v), "text-anchor": "end", "dominant-baseline": "middle" }, rejilla);
      t.textContent = fmt.m(v);
    }
    for (const v of ex.marcas.filter((v) => v <= kmTotal + 1e-9)) {
      const t = el("text", { x: fx(v), y: alto - 8, "text-anchor": "middle" }, rejilla);
      t.textContent = v === 0 ? "0 km" : fmt.num(v, v % 1 ? 1 : 0);
    }

    const linea = datos.map((f, i) => `${i ? "L" : "M"}${fx(f[0]).toFixed(1)},${fy(f[1]).toFixed(1)}`).join("");
    const base = fy(ey.lo);
    el("path", {
      d: `${linea}L${fx(kmTotal).toFixed(1)},${base}L${fx(0).toFixed(1)},${base}Z`,
      class: "perfil-area", fill: color,
    }, svg);
    el("path", { d: linea, class: "perfil-linea", stroke: color }, svg);
    el("line", { class: "perfil-base", x1: m.izq, x2: ancho - m.der, y1: base, y2: base }, svg);

    const cruz = el("g", { class: "perfil-cruz", visibility: "hidden" }, svg);
    el("line", { y1: m.arr, y2: base }, cruz);
    el("circle", { r: 5, fill: color }, cruz);
    if (indice >= 0) mostrar(indice);
  }

  function mostrar(i) {
    indice = i;
    const f = datos[i];
    const cruz = svg.querySelector(".perfil-cruz");
    const px = x(f[0]);
    cruz.setAttribute("visibility", "visible");
    cruz.querySelector("line").setAttribute("x1", px);
    cruz.querySelector("line").setAttribute("x2", px);
    cruz.querySelector("circle").setAttribute("cx", px);
    cruz.querySelector("circle").setAttribute("cy", y(f[1]));
    ayuda.hidden = false;
    ayuda.innerHTML = `<strong>${fmt.m(f[1])}</strong><span>km ${fmt.num(f[0], 1)}</span>`;
    const w = ayuda.offsetWidth;
    ayuda.style.left = `${Math.min(Math.max(px - w / 2, 0), ancho - w)}px`;
    alMover?.(f);
  }

  function ocultar() {
    indice = -1;
    svg.querySelector(".perfil-cruz")?.setAttribute("visibility", "hidden");
    ayuda.hidden = true;
    alSalir?.();
  }

  function indiceEn(clientX) {
    const r = svg.getBoundingClientRect();
    const px = ((clientX - r.left) / r.width) * ancho;
    const km = ((px - m.izq) / (ancho - m.izq - m.der)) * kmTotal;
    let lo = 0, hi = datos.length - 1;
    while (hi - lo > 1) {
      const mid = (lo + hi) >> 1;
      if (datos[mid][0] < km) lo = mid; else hi = mid;
    }
    return Math.abs(datos[lo][0] - km) <= Math.abs(datos[hi][0] - km) ? lo : hi;
  }

  svg.addEventListener("pointermove", (e) => mostrar(indiceEn(e.clientX)));
  svg.addEventListener("pointerdown", (e) => mostrar(indiceEn(e.clientX)));
  svg.addEventListener("pointerleave", ocultar);
  svg.addEventListener("pointercancel", ocultar);
  svg.addEventListener("blur", ocultar);
  svg.addEventListener("keydown", (e) => {
    const salto = e.shiftKey ? 10 : 1;
    if (e.key === "ArrowRight") mostrar(Math.min(datos.length - 1, Math.max(indice, 0) + salto));
    else if (e.key === "ArrowLeft") mostrar(Math.max(0, (indice < 0 ? 0 : indice) - salto));
    else return;
    e.preventDefault();
  });

  new ResizeObserver(() => {
    if (contenedor.clientWidth && contenedor.clientWidth !== ancho) dibujar();
  }).observe(contenedor);
  dibujar();
}
