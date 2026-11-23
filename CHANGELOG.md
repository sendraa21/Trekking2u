# Cambios

## 1.0.0 (23/11/2026)

Primera versión.

**Datos**
- Lectura de FIT (Garmin) y GPX en un formato común.
- Importación del export completo de Garmin: solo las actividades de montaña
  (senderismo, «Navegar» y trail running), con su nombre real.
- Métricas de cada ruta: distancia, desnivel +/−, duración, tiempo en
  movimiento (cuenta también las subidas lentas), ritmo, altitud máxima y
  mínima, y FC media y máxima.
- Trazado simplificado y perfil de elevación remuestreado.
- Procesado incremental: solo lo nuevo o lo que ha cambiado, sin duplicados
  entre FIT y GPX de la misma salida.
- Filtro de saltos imposibles del GPS.
- `data/notas.json` para cambiar el título, el tipo o la descripción de una
  ruta, u ocultarla.

**Web**
- Inicio con totales, filtros por año y tipo, mapa con todas las rutas y
  listado por fecha.
- Ficha de ruta con mapa, datos, perfil de elevación interactivo enlazado con
  el mapa, vista 3D con relieve, satélite y enlaces a la ruta anterior y la
  siguiente.
- Diseño pensado primero para el móvil, con modo oscuro automático.

**Privacidad y publicación**
- Datos cifrados con contraseña (AES-256-GCM); en GitHub solo hay datos ilegibles.
- `publicar.bat`: un solo paso para procesar, regenerar y subir, con
  comprobaciones para no subir nunca nada privado.
- Repositorio plantilla, con guía para usarlo con otras rutas.

**Ideas para próximas versiones**
- Descarga automática desde Garmin Connect (preparada en
  `trekking/fuentes/garmin_connect.py`).
- Otras formas de clasificar y ver las rutas.
- Lo que vayamos hablando Gema y yo.
