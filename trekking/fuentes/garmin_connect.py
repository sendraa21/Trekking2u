"""Descarga automática desde Garmin Connect (PENDIENTE, solo en local).

Plan previsto (no implementado todavía):
- Usar la librería `garminconnect` (python-garminconnect), instalada aparte:
  .venv\\Scripts\\python -m pip install garminconnect
- Credenciales en un archivo .env (ignorado por git), nunca en el código.
- Pedir las actividades desde la fecha de la última ruta procesada,
  filtrar por tipo (senderismo, navegar, trail) y descargar el FIT original
  de cada una en data/raw/garmin_connect/<id_actividad>.fit.
- Guardar también el título de cada actividad para que el procesado lo use
  en lugar del nombre genérico del perfil ("Navegar").
"""


def descargar_nuevas(*_args, **_kwargs):  # pragma: no cover - aún no implementado
    raise NotImplementedError("La descarga desde Garmin Connect aún no está implementada.")
