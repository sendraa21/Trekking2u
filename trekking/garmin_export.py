"""Importa el ZIP del export completo de Garmin Connect.

Estructura del export (lo que usamos):
  DI_CONNECT/DI-Connect-Fitness/<cuenta>_<n>_summarizedActivities.json   nombres y tipos
  DI_CONNECT/DI-Connect-Uploaded-Files/UploadedFiles_*.zip               los FIT

Los FIT no llevan el título de la actividad ni su id: se emparejan con el JSON
por la hora de inicio. Solo se copian a data/raw/garmin/ las actividades de
montaña (según [clasificacion] de trekking.toml); el título de cada una se
guarda en data/raw/garmin/actividades.json para que el procesado lo use.

Nunca se usan las rutas internas del ZIP para escribir: los nombres de destino
se generan aquí (fecha + id), así un ZIP raro no puede escribir fuera.
"""
from __future__ import annotations

import collections
import io
import json
import re
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .config import Config
from .modelo import Actividad
from .procesar import clasificar, escribir_json, leer_json

SUBCARPETA = "garmin"
METADATOS = "actividades.json"
MARGEN_EMPAREJADO_S = 600


@dataclass
class InformeImportacion:
    fit_revisados: int = 0
    nuevas: list[str] = field(default_factory=list)
    ya_estaban: int = 0
    descartadas: collections.Counter = field(default_factory=collections.Counter)


def _actividades_json(zf: zipfile.ZipFile) -> list[dict]:
    acts: list[dict] = []
    for nombre in zf.namelist():
        if nombre.endswith("summarizedActivities.json"):
            for bloque in json.loads(zf.read(nombre)):
                acts.extend(bloque.get("summarizedActivitiesExport", []))
    return acts


def _fits(zf: zipfile.ZipFile):
    """Recorre los FIT de los ZIP internos UploadedFiles_*.zip (y FIT sueltos)."""
    for nombre in zf.namelist():
        bajo = nombre.lower()
        if "uploadedfiles" in bajo and bajo.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(zf.read(nombre))) as interno:
                for i in interno.infolist():
                    if i.filename.lower().endswith(".fit"):
                        yield interno.read(i)
        elif bajo.endswith(".fit") and "uploadedfiles" in bajo:
            yield zf.read(nombre)


def _cabecera_fit(datos: bytes) -> dict:
    """Lee solo el principio del FIT: tipo de archivo, hora y deporte."""
    import fitdecode

    info: dict = {}
    try:
        with fitdecode.FitReader(io.BytesIO(datos)) as fit:
            for frame in fit:
                if not isinstance(frame, fitdecode.FitDataMessage):
                    continue
                if frame.name == "file_id":
                    info["tipo"] = frame.get_value("type", fallback=None)
                    info["creado"] = frame.get_value("time_created", fallback=None)
                    if info["tipo"] != "activity":
                        break
                elif frame.name == "sport":
                    info["deporte"] = frame.get_value("sport", fallback=None)
                    info["subdeporte"] = frame.get_value("sub_sport", fallback=None)
                    info["perfil"] = frame.get_value("name", fallback=None)
                elif frame.name == "record":
                    break  # lo que necesitamos va antes de los puntos
    except Exception:  # noqa: BLE001 - FIT dañado o raro: se ignora
        info.setdefault("tipo", None)
    return info


def _emparejar(creado: datetime | None, por_hora: list[tuple[float, dict]]) -> dict | None:
    if creado is None:
        return None
    t = creado.timestamp()
    mejor = min(por_hora, key=lambda x: abs(x[0] - t), default=None)
    return mejor[1] if mejor and abs(mejor[0] - t) <= MARGEN_EMPAREJADO_S else None


def importar_zip(cfg: Config, ruta_zip: Path) -> InformeImportacion:
    inf = InformeImportacion()
    destino = cfg.dir_raw / SUBCARPETA
    destino.mkdir(parents=True, exist_ok=True)
    archivo_meta = destino / METADATOS
    meta = leer_json(archivo_meta, {})

    with zipfile.ZipFile(ruta_zip) as zf:
        acts = _actividades_json(zf)
        por_hora = [(a["startTimeGmt"] / 1000, a) for a in acts if a.get("startTimeGmt")]
        for datos in _fits(zf):
            inf.fit_revisados += 1
            cab = _cabecera_fit(datos)
            if cab.get("tipo") != "activity":
                inf.descartadas["no es una actividad"] += 1
                continue
            act_json = _emparejar(cab.get("creado"), por_hora)
            nombre = (act_json or {}).get("name") or cab.get("perfil") or ""
            tipo_garmin = (act_json or {}).get("activityType") or ""
            deporte = str(cab.get("deporte") or "")
            sub = str(cab.get("subdeporte") or "")
            provisional = Actividad(
                origen="fit", nombre=nombre, puntos=[],
                tipo_original=f"{deporte}/{sub} {tipo_garmin}".strip(),
                perfil=str(cab.get("perfil") or ""))
            if clasificar(provisional, cfg) is None:
                inf.descartadas[tipo_garmin or deporte or "desconocido"] += 1
                continue

            creado = cab.get("creado") or datetime.now(timezone.utc)
            ident = str((act_json or {}).get("activityId") or f"{int(creado.timestamp())}")
            ident = re.sub(r"[^0-9A-Za-z_-]", "", ident)
            nombre_archivo = f"{creado:%Y-%m-%d}_{ident}.fit"
            ruta = destino / nombre_archivo
            if ruta.exists() and ruta.read_bytes() == datos:
                inf.ya_estaban += 1
            else:
                ruta.write_bytes(datos)
                inf.nuevas.append(nombre_archivo)
            if act_json:
                meta[nombre_archivo] = {"id": act_json.get("activityId"), "nombre": nombre,
                                        "tipo_garmin": tipo_garmin}
    escribir_json(archivo_meta, meta)
    return inf


def metadatos_de(ruta_fit: Path, cache: dict) -> dict | None:
    """Título y tipo de Garmin de un FIT importado (si los hay)."""
    carpeta = ruta_fit.parent
    if carpeta not in cache:
        cache[carpeta] = leer_json(carpeta / METADATOS, {})
    return cache[carpeta].get(ruta_fit.name)


def importar_pendientes(cfg: Config) -> list[tuple[Path, InformeImportacion]]:
    """Importa los ZIP que haya en data/entrada/ y los mueve a data/entrada/importados/."""
    entrada = cfg.dir_datos / "entrada"
    hechos = []
    if not entrada.exists():
        return hechos
    for z in sorted(entrada.glob("*.zip")):
        inf = importar_zip(cfg, z)
        (entrada / "importados").mkdir(exist_ok=True)
        z.replace(entrada / "importados" / z.name)
        hechos.append((z, inf))
    return hechos
