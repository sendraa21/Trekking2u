# Trekking2u

Una web para ver las rutas de senderismo que hacemos Gema y yo: mapa con todas
las rutas, totales por año y una ficha de cada ruta con su perfil de elevación y
vista 3D con relieve. La idea es de Gema; la web, de los dos.

Es una **plantilla**: puedes usarla para publicar tus propias rutas (botón
**Use this template** arriba en GitHub). Nuestras rutas están dentro, pero
**cifradas**: sin nuestra contraseña solo se ven datos ilegibles. Cuando proceses
las tuyas, las nuestras desaparecen solas.

Uso del día a día: [INSTRUCCIONES.md](INSTRUCCIONES.md) · Cambios: [CHANGELOG.md](CHANGELOG.md)

- Web estática (HTML + JavaScript), sin servidor: se publica gratis en GitHub Pages.
- Mapas con [MapLibre GL](https://maplibre.org/) y [MapTiler](https://www.maptiler.com/).
- Un script de Python lee los archivos del reloj (FIT del export de Garmin y GPX),
  calcula las métricas, simplifica los trazados y genera los datos de la web.
- Datos cifrados con contraseña (AES-256-GCM): el repositorio puede ser público
  sin que nadie vea las rutas.

---

## Cómo funciona

```
data/raw/*.gpx, *.fit   →  python -m trekking procesar  →  docs/data/  →  GitHub Pages
 (tus archivos, privados)       (solo lo nuevo)             (cifrado)       (la web)
```

| Carpeta / archivo | Qué es | ¿Se sube a GitHub? |
|---|---|---|
| `data/raw/` | Tus GPX y FIT originales | **No**, nunca |
| `data/procesadas/`, `data/estado.json` | Caché del procesado | No |
| `data/notas.json` | Tus títulos, descripciones y rutas ocultas | Sí |
| `docs/` | La web; `docs/data/` son los datos ya simplificados (y cifrados) | Sí |
| `docs/config.js` | Clave de MapTiler y textos de la web | Sí |
| `trekking.toml` | Ajustes del procesado y de privacidad | Sí |
| `.env` | La contraseña de la web | **No**, nunca |

### Qué calcula de cada ruta

Fecha, nombre, tipo (senderismo, navegación, trail u otra), distancia, desnivel
positivo y negativo, duración total, tiempo en movimiento, ritmo medio, altitud
máxima y mínima, y frecuencia cardiaca media y máxima si el reloj la grabó.

- **Desnivel**: en los FIT se usa el total del reloj (barómetro). En los GPX se
  calcula con un umbral para que el ruido no lo infle (`umbral_desnivel_m`).
- **Tiempo en movimiento**: solo cuentan los tramos en los que se avanza.
- **Incremental**: cada archivo se procesa una sola vez; si lo cambias o lo
  borras de `data/raw`, se actualiza o desaparece de la web.
- Si la misma salida llega como FIT y como GPX, solo aparece una vez (gana el FIT).

---

## Usar la plantilla con tus rutas

### 1. Crea tu copia

1. Crea una cuenta en [GitHub](https://github.com/signup).
2. En esta página pulsa **Use this template → Create a new repository**.
   Ponle nombre (por ejemplo `mis-rutas`) y déjalo **Public** (GitHub Pages
   gratis necesita repositorio público; tus datos irán cifrados).

### 2. Prepara el PC (Windows)

Abre PowerShell e instala lo necesario:

```powershell
winget install -e --id Python.Python.3.13 --scope user
winget install -e --id Git.Git
winget install -e --id GitHub.cli
```

Cierra y abre PowerShell, conéctate a GitHub y descarga tu copia
(cambia `TU_USUARIO/mis-rutas`):

```powershell
gh auth login --web --git-protocol https
cd D:\
gh repo clone TU_USUARIO/mis-rutas
cd mis-rutas
py -3.13 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 3. Mapas: clave de MapTiler

1. Crea una cuenta gratis en [MapTiler Cloud](https://cloud.maptiler.com/).
2. En **Account → API keys** copia tu clave y pégala en `docs/config.js`
   (`maptilerKey`). La clave que viene es la nuestra y **solo funciona en
   nuestra web**.
3. En esa clave, rellena **Allowed HTTP Origins** con
   `TU_USUARIO.github.io,127.0.0.1,localhost` y guarda. Así nadie puede usar tu
   clave en otra web (la clave se ve en el código; es normal).
4. En `docs/config.js` cambia también los textos: `lema` y `firma`.

### 4. Contraseña (opcional, recomendada)

```powershell
.venv\Scripts\python.exe -m trekking clave
```

Se guarda solo en tu PC (archivo `.env`). Usa varias palabras, por ejemplo
`pino-lago-nube-2026`: los datos cifrados son públicos y una contraseña corta se
puede adivinar probando. Si prefieres publicar sin contraseña, pon
`requiere_contrasena = false` en `trekking.toml`.

### 5. Tus rutas

- **Ruta suelta**: en [Garmin Connect](https://connect.garmin.com/modern/activities)
  (desde el ordenador) abre la actividad → ⚙ → **Exportar archivo original**
  (FIT, el mejor) o **Exportar a GPX**, y guárdalo en `data/raw/`.
- **Todo el historial**: pídelo en
  [Garmin → Exportar datos](https://www.garmin.com/account/datamanagement/exportdata/).
  Cuando te llegue el ZIP, déjalo tal cual en `data/entrada/` y ejecuta
  `publicar.bat`; o impórtalo a mano:

  ```powershell
  .venv\Scripts\python.exe -m trekking importar C:\ruta\al\export.zip
  ```

  Solo se copian a `data/raw/garmin/` las actividades de montaña, con su
  nombre real de Garmin. Puedes volver a importar un export nuevo: lo que ya
  estaba no se duplica.

Los FIT se filtran por tipo de actividad: entran senderismo, montañismo, trail
running y el modo «Navegar» del reloj. Los GPX que pongas a mano entran siempre.
Las palabras de cada tipo se cambian en `trekking.toml`.

Para empezar de cero (y quitar nuestras rutas), vacía `data/notas.json` dejando
`"rutas": {}` y procesa todo:

```powershell
.venv\Scripts\python.exe -m trekking procesar --todo
```

### 6. Mírala y publícala

- **`ver_web.bat`** (doble clic): abre la web en tu PC.
- **`publicar.bat`** (doble clic): procesa las rutas nuevas, regenera la web,
  comprueba que no se cuela nada privado y la sube a GitHub.

La primera vez, activa GitHub Pages en tu repositorio: **Settings → Pages →
Build and deployment → Deploy from a branch → `main` / `/docs` → Save**.
Tu web quedará en `https://TU_USUARIO.github.io/mis-rutas/`.

---

## Ajustes útiles

- **`data/notas.json`**: cambia el título o el tipo de una ruta, añade una
  descripción u ocúltala. Usa el id de la ruta (está en la dirección de su ficha):

  ```json
  {
    "rutas": {
      "2025-06-14-collado": { "nombre": "Mirador del Pinar", "descripcion": "¡Qué día!", "tipo": "senderismo" },
      "2026-08-01-paseo":   { "ocultar": true }
    },
    "incluir_archivos": []
  }
  ```

  Después: `python -m trekking regenerar` o `publicar.bat`.
- **`trekking.toml`**: privacidad (recortar el inicio y el final de cada ruta para
  no mostrar desde dónde sales, ocultar la frecuencia cardiaca), umbrales de
  cálculo y nivel de simplificación del trazado.

## Órdenes

```powershell
.venv\Scripts\python.exe -m trekking publicar     # todo: procesar + regenerar + subir
.venv\Scripts\python.exe -m trekking procesar     # solo procesar y regenerar (sin subir)
.venv\Scripts\python.exe -m trekking regenerar    # solo regenerar (tras editar notas.json)
.venv\Scripts\python.exe -m trekking servir       # ver la web en local
.venv\Scripts\python.exe -m trekking clave        # poner o cambiar la contraseña
.venv\Scripts\python.exe -m trekking importar X.zip  # importar el export completo de Garmin
.venv\Scripts\python.exe -m pytest                # tests
```

## Seguridad, en claro

- Los archivos originales del reloj (`data/raw`) nunca se suben. `publicar`
  se niega a subir si detecta algo privado.
- Con contraseña, en GitHub solo hay datos cifrados: ni los nombres de archivo
  revelan lugares o fechas. Quien tenga la contraseña puede ver y guardar los
  datos de la web (trazados simplificados), como en cualquier web.
- El navegador guarda una clave derivada (nunca la contraseña) si marcas
  «Recordarla en este dispositivo». «Cerrar sesión», al pie de la web, la borra.

## Próximamente

- Descarga automática opcional desde Garmin Connect (`trekking/fuentes/garmin_connect.py`).
