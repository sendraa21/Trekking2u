# Trekking2u: instrucciones de uso

Guía rápida para el día a día con nuestra web de rutas. La guía para montar la
plantilla desde cero está en el [README](README.md).

- **Web:** https://sendraa21.github.io/Trekking2u/
- **Código:** https://github.com/sendraa21/Trekking2u
- **Carpeta en el PC:** `D:\Trekking2u`

---

## Ver la web

1. Abre la web y escribe la contraseña.
2. Marca **«Recordarla en este dispositivo»** para que no te la vuelva a pedir.
3. En un móvil o PC que no sea vuestro, usa **«Cerrar sesión en este
   dispositivo»**, al pie de la página.

Para compartir la web con alguien, pásale el enlace y la contraseña.

---

## Añadir una ruta nueva

1. Entra en [Garmin Connect](https://connect.garmin.com/modern/activities)
   desde el ordenador (la app del móvil no exporta archivos).
2. Abre la actividad, pulsa el engranaje **⚙** y elige **«Exportar archivo
   original»**. Se descarga un ZIP; dentro está el `.fit`.
   - Si solo tienes un GPX, también vale: **⚙ → «Exportar a GPX»**.
3. Copia el `.fit` (o el `.gpx`) a `D:\Trekking2u\data\raw\`.
4. Doble clic en **`publicar.bat`**.
5. Espera 1-2 minutos y recarga la web.

Entran solas las actividades de **senderismo**, **«Navegar»** y **trail
running**. Los GPX que pongáis a mano entran siempre.

## Importar el historial completo de Garmin

Si pedís otro export completo a Garmin:

1. Deja el ZIP, sin descomprimir, en `D:\Trekking2u\data\entrada\`.
2. Doble clic en **`publicar.bat`**.

Solo coge las rutas de montaña, con su nombre real, y no duplica las que ya
estaban. El ZIP se mueve a `data\entrada\importados\`.

---

## Cambiar el título, el tipo o la descripción de una ruta, u ocultarla

Edita `D:\Trekking2u\data\notas.json` (con el Bloc de notas sirve). Cada ruta se
identifica por su **id**, que aparece en la dirección de su ficha:
`.../ruta.html?id=`**`2025-06-14-collado`** (fecha + nombre).

Ejemplo (con rutas inventadas):

```json
{
  "rutas": {
    "2025-06-14-collado": {
      "nombre": "Collado del Pinar",
      "descripcion": "Con niebla al subir y sol al bajar."
    },
    "2025-07-20-mirador": { "tipo": "senderismo" },
    "2025-11-02-pinar": { "ocultar": true }
  },
  "incluir_archivos": []
}
```

- `tipo` puede ser `senderismo`, `navegacion`, `trail` u `otro`.
- Ojo con las comas y las comillas: si el archivo queda mal escrito, `publicar.bat` dará error.
- Después, doble clic en **`publicar.bat`**.

Si exportáis a mano un FIT de otro tipo (por ejemplo, una caminata) y
`publicar.bat` lo descarta, añadid el nombre del archivo a
`"incluir_archivos"` (por ejemplo `"incluir_archivos": ["paseo.fit"]`) y
volved a publicar.

---

## Ver la web en el PC antes de publicar

Doble clic en **`ver_web.bat`**: se abre en http://127.0.0.1:8000/. Para
pararla, cierra la ventana negra.

## Cambiar la contraseña

Abre PowerShell en `D:\Trekking2u` y ejecuta:

```powershell
.venv\Scripts\python.exe -m trekking clave
```

Luego, doble clic en **`publicar.bat`**. La contraseña antigua deja de
funcionar y todos tendréis que escribir la nueva.

---

## Copias de seguridad (importante)

Estas cosas **solo están en este PC**: GitHub no las tiene.

| Qué | Dónde | Por qué importa |
|---|---|---|
| Los archivos originales del reloj | `D:\Trekking2u\data\raw\` | Sin ellos no se pueden volver a generar las rutas |
| La contraseña | `D:\Trekking2u\.env` | Sin ella no se puede publicar |

Cópialos de vez en cuando a un disco externo o a la nube. El resto, incluido
`notas.json`, ya está guardado en GitHub.

## Si algo falla

- **La web no muestra la ruta nueva:** espera 2 minutos y recarga con
  `Ctrl+F5` (en el móvil, cierra la pestaña y vuelve a abrirla).
- **`publicar.bat` dice que falta la contraseña:** el archivo `.env` no está.
  Recupéralo de la copia de seguridad o pon una nueva con la orden `clave`.
- **`publicar.bat` dice que «se iban a subir archivos privados»:** no ha subido
  nada. Es una protección; avisadme antes de tocar nada.
- **Una ruta sale rara en el mapa:** decidme cuál. Se puede corregir al
  procesar o, si no tiene arreglo, ocultarla en `notas.json`.

## Montarlo en otro PC

```powershell
winget install -e --id Python.Python.3.13 --scope user
winget install -e --id Git.Git
winget install -e --id GitHub.cli
```

Cierra y abre PowerShell, y luego:

```powershell
gh auth login --web --git-protocol https
cd D:\
gh repo clone sendraa21/Trekking2u
cd Trekking2u
py -3.13 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Por último, copia de la copia de seguridad el archivo `.env` y la carpeta
`data\raw\`, y ejecuta `publicar.bat`.
