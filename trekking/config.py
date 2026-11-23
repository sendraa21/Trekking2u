"""Carga de trekking.toml y rutas de carpetas del proyecto."""
from __future__ import annotations

import copy
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

RAIZ_PROYECTO = Path(__file__).resolve().parents[1]

DEFECTOS: dict = {
    "zona_horaria": "Europe/Madrid",
    "clasificacion": {
        "trail": ["trail", "trail_running"],
        "senderismo": ["hiking", "mountaineering", "senderismo"],
        "navegacion": ["navigate", "navegar"],
    },
    "nombres": {"quitar_sufijos": []},
    "calculo": {
        "umbral_desnivel_m": 3.0,
        "velocidad_min_movimiento_ms": 0.3,
        "velocidad_min_vertical_ms": 0.05,
        "duplicado_margen_s": 120,
        "velocidad_max_gps_ms": 8.0,
    },
    "simplificacion": {
        "tolerancia_ruta_m": 5.0,
        "tolerancia_mapa_general_m": 25.0,
        "max_puntos_perfil": 400,
    },
    "privacidad": {"requiere_contrasena": False, "recorte_inicio_m": 0, "recorte_fin_m": 0,
                   "mostrar_fc": True},
}


def _fusionar(base: dict, extra: dict) -> dict:
    res = copy.deepcopy(base)
    for k, v in extra.items():
        if isinstance(v, dict) and isinstance(res.get(k), dict):
            res[k] = _fusionar(res[k], v)
        else:
            res[k] = v
    return res


@dataclass
class Config:
    raiz: Path
    ajustes: dict = field(default_factory=lambda: copy.deepcopy(DEFECTOS))

    # --- carpetas ---------------------------------------------------------
    @property
    def dir_datos(self) -> Path:
        return self.raiz / "data"

    @property
    def dir_raw(self) -> Path:
        return self.dir_datos / "raw"

    @property
    def dir_procesadas(self) -> Path:
        return self.dir_datos / "procesadas"

    @property
    def archivo_estado(self) -> Path:
        return self.dir_datos / "estado.json"

    @property
    def archivo_notas(self) -> Path:
        return self.dir_datos / "notas.json"

    @property
    def dir_web_datos(self) -> Path:
        return self.raiz / "docs" / "data"

    # --- ajustes ----------------------------------------------------------
    def __getitem__(self, seccion: str):
        return self.ajustes[seccion]

    @property
    def zona_horaria(self) -> str:
        return self.ajustes["zona_horaria"]


def cargar_config(raiz: Path | None = None) -> Config:
    raiz = Path(raiz) if raiz else RAIZ_PROYECTO
    archivo = raiz / "trekking.toml"
    ajustes = DEFECTOS
    if archivo.exists():
        with archivo.open("rb") as f:
            ajustes = _fusionar(DEFECTOS, tomllib.load(f))
    return Config(raiz=raiz, ajustes=copy.deepcopy(ajustes))
