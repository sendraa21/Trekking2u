// Carga de datos, en claro o cifrados con contraseña.
//
// Si existe data/cripto.json, los datos están cifrados (AES-256-GCM, clave
// derivada con PBKDF2-SHA256; ver trekking/cripto.py). Se pide la contraseña,
// se deriva la clave y se guarda solo la clave derivada (nunca la contraseña)
// en este navegador, para no pedirla en cada página.

const enc = new TextEncoder();
const dec = new TextDecoder();
let llave = null; // CryptoKey AES-GCM, o null si los datos están en claro
let cabecera = null;

const de64 = (s) => Uint8Array.from(atob(s), (c) => c.charCodeAt(0));
const a64 = (b) => btoa(String.fromCharCode(...b));
const almacen = () => `trekking2u:${cabecera.sal}`;

function leerGuardada() {
  for (const s of [() => sessionStorage, () => localStorage]) {
    try {
      const v = s().getItem(almacen());
      if (v) return v;
    } catch { /* almacenamiento bloqueado */ }
  }
  return null;
}

function guardar(raw, recordar) {
  try {
    (recordar ? localStorage : sessionStorage).setItem(almacen(), a64(raw));
  } catch { /* sin almacenamiento: se pedirá otra vez */ }
}

export function olvidar() {
  for (const s of [() => sessionStorage, () => localStorage]) {
    try { if (cabecera) s().removeItem(almacen()); } catch { /* nada */ }
  }
}

async function importar(raw) {
  return crypto.subtle.importKey("raw", raw, { name: "AES-GCM" }, false, ["decrypt"]);
}

async function abrir(sobre, clave) {
  const plano = await crypto.subtle.decrypt({ name: "AES-GCM", iv: de64(sobre.iv) }, clave, de64(sobre.datos));
  return new Uint8Array(plano);
}

export async function derivar(contrasena, cab) {
  const base = await crypto.subtle.importKey("raw", enc.encode(contrasena), "PBKDF2", false, ["deriveBits"]);
  const bits = await crypto.subtle.deriveBits(
    { name: "PBKDF2", hash: "SHA-256", salt: de64(cab.sal), iterations: cab.iteraciones }, base, 512);
  return new Uint8Array(bits).slice(0, 32); // solo la parte AES
}

async function valida(raw) {
  try {
    const k = await importar(raw);
    return dec.decode(await abrir(cabecera.prueba, k)) === "trekking2u" ? k : null;
  } catch {
    return null;
  }
}

// ------------------------------------------------------------ pantalla
function pedirContrasena() {
  return new Promise((resolver) => {
    document.body.classList.add("bloqueado");
    const capa = document.createElement("div");
    capa.className = "candado";
    capa.innerHTML = `
      <form class="candado-caja" autocomplete="on">
        <svg class="candado-logo" viewBox="0 0 32 32" aria-hidden="true"><path d="M2 26 11.5 10l5.2 8.6L21 12l9 14Z"/></svg>
        <h1>Trekking<b>2u</b></h1>
        <p>Estas son nuestras rutas. Si te hemos dado la contraseña, adelante.</p>
        <input type="text" name="usuario" value="trekking2u" autocomplete="username" hidden>
        <label class="candado-campo">
          <span>Contraseña</span>
          <input type="password" name="contrasena" autocomplete="current-password" required>
        </label>
        <label class="candado-recordar">
          <input type="checkbox" name="recordar" checked>
          <span>Recordarla en este dispositivo</span>
        </label>
        <p class="candado-error" role="alert" hidden>Esa no es. Prueba otra vez.</p>
        <button type="submit" class="candado-boton">Entrar</button>
      </form>`;
    document.body.appendChild(capa);
    const form = capa.querySelector("form");
    const campo = form.contrasena;
    const boton = form.querySelector("button");
    const error = form.querySelector(".candado-error");
    campo.focus();

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      boton.disabled = true;
      boton.textContent = "Comprobando…";
      error.hidden = true;
      const raw = await derivar(campo.value, cabecera);
      const k = await valida(raw);
      if (k) {
        guardar(raw, form.recordar.checked);
        capa.remove();
        document.body.classList.remove("bloqueado");
        resolver(k);
      } else {
        error.hidden = false;
        boton.disabled = false;
        boton.textContent = "Entrar";
        campo.select();
      }
    });
  });
}

function botonSalir() {
  const pie = document.querySelector(".pie .contenedor");
  if (!pie) return;
  const b = document.createElement("button");
  b.type = "button";
  b.className = "salir";
  b.textContent = "Cerrar sesión en este dispositivo";
  b.addEventListener("click", () => {
    olvidar();
    location.reload();
  });
  pie.appendChild(b);
}

// ------------------------------------------------------------- pública
export async function iniciarDatos() {
  const r = await fetch("data/cripto.json", { cache: "no-cache" });
  if (r.status === 404) return; // datos en claro
  if (!r.ok) throw new Error(`data/cripto.json: ${r.status}`);
  cabecera = await r.json();
  const guardada = leerGuardada();
  llave = (guardada && (await valida(de64(guardada)))) || (await pedirContrasena());
  botonSalir();
}

export async function leerDatos(archivo) {
  const r = await fetch(`data/${archivo}`, { cache: "no-cache" });
  if (!r.ok) throw new Error(`data/${archivo}: ${r.status}`);
  const datos = await r.json();
  if (!llave) return datos;
  return JSON.parse(dec.decode(await abrir(datos, llave)));
}
