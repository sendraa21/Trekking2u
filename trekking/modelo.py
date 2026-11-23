"""Modelo común al que se convierten los GPX y los FIT."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


class Descartada(Exception):
    """El archivo se ha leído bien pero no es una ruta que nos interese."""


@dataclass(slots=True)
class Punto:
    lat: float
    lon: float
    ele: float | None = None
    t: datetime | None = None
    fc: int | None = None


@dataclass
class Actividad:
    origen: str                 # "gpx" | "fit"
    nombre: str                 # nombre tal cual viene del archivo
    tipo_original: str          # deporte según el archivo: "hiking", "running/trail"...
    puntos: list[Punto]
    perfil: str = ""            # perfil de actividad del reloj ("Navegar"), si lo hay
    fecha_archivo: datetime | None = None
    # Totales calculados por el propio reloj (solo FIT). Son más fiables que
    # recalcularlos, sobre todo el desnivel (barómetro).
    totales_dispositivo: dict = field(default_factory=dict)
