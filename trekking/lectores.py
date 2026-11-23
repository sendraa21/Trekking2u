"""Lectura de archivos GPX y FIT al modelo común (Actividad)."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

from .modelo import Actividad, Descartada, Punto

EXTENSIONES = {".gpx", ".fit"}


def leer(ruta: Path) -> Actividad:
    sufijo = ruta.suffix.lower()
    if sufijo == ".gpx":
        return leer_gpx(ruta)
    if sufijo == ".fit":
        return leer_fit(ruta)
    raise ValueError(f"formato no soportado: {ruta.suffix}")


# --------------------------------------------------------------------- GPX

def _local(tag: str) -> str:
    """Nombre de etiqueta sin espacio de nombres: '{ns}trkpt' -> 'trkpt'."""
    return tag.rsplit("}", 1)[-1]


def _fecha(texto: str | None) -> datetime | None:
    if not texto:
        return None
    try:
        t = datetime.fromisoformat(texto.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def _num(texto: str | None) -> float | None:
    try:
        return float(texto)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _punto_gpx(pt: ET.Element) -> Punto | None:
    lat, lon = _num(pt.get("lat")), _num(pt.get("lon"))
    if lat is None or lon is None or (lat == 0 and lon == 0):
        return None
    p = Punto(lat=lat, lon=lon)
    for e in pt.iter():
        tag = _local(e.tag)
        if tag == "ele":
            p.ele = _num(e.text)
        elif tag == "time":
            p.t = _fecha(e.text)
        elif tag in ("hr", "heartrate"):
            v = _num(e.text)
            p.fc = int(v) if v else None
    return p


def leer_gpx(ruta: Path) -> Actividad:
    raiz = ET.parse(ruta).getroot()
    nombre = tipo = nombre_meta = None
    fecha_meta = None
    puntos: list[Punto] = []

    for elem in raiz:
        tag = _local(elem.tag)
        if tag == "metadata":
            for m in elem:
                if _local(m.tag) == "time":
                    fecha_meta = _fecha(m.text)
                elif _local(m.tag) == "name" and m.text:
                    nombre_meta = m.text.strip()
        elif tag == "trk":
            for hijo in elem:
                t = _local(hijo.tag)
                if t == "name" and nombre is None and hijo.text:
                    nombre = hijo.text.strip()
                elif t == "type" and tipo is None and hijo.text:
                    tipo = hijo.text.strip()
                elif t == "trkseg":
                    for pt in hijo:
                        if _local(pt.tag) == "trkpt" and (p := _punto_gpx(pt)):
                            puntos.append(p)

    if len(puntos) < 2:
        raise Descartada("el GPX no tiene un track con puntos")
    return Actividad(
        origen="gpx",
        nombre=nombre or nombre_meta or ruta.stem,
        tipo_original=tipo or "",
        puntos=puntos,
        fecha_archivo=fecha_meta,
    )


# --------------------------------------------------------------------- FIT

_SEMICIRCULO = 180.0 / 2**31


def _grados(v) -> float | None:
    """Semicírculos (unidad de posición de los FIT) a grados.

    Siempre se convierte: cerca del meridiano 0 o del ecuador los valores en
    semicírculos son pequeños y no se pueden distinguir de grados por su tamaño.
    """
    return None if v is None else float(v) * _SEMICIRCULO


def _valor(frame, nombre: str):
    if not frame.has_field(nombre):
        return None
    return frame.get_value(nombre, fallback=None)


def leer_fit(ruta: Path) -> Actividad:
    import fitdecode  # import aquí para que leer GPX no dependa de fitdecode

    puntos: list[Punto] = []
    sesion: dict | None = None
    perfil = ""
    tipo_archivo = None

    with fitdecode.FitReader(str(ruta)) as fit:
        for frame in fit:
            if not isinstance(frame, fitdecode.FitDataMessage):
                continue
            nombre = frame.name
            if nombre == "file_id":
                tipo_archivo = _valor(frame, "type")
            elif nombre == "record":
                lat = _grados(_valor(frame, "position_lat"))
                lon = _grados(_valor(frame, "position_long"))
                if lat is None or lon is None or (lat == 0 and lon == 0):
                    continue
                ele = _valor(frame, "enhanced_altitude")
                if ele is None:
                    ele = _valor(frame, "altitude")
                fc = _valor(frame, "heart_rate")
                puntos.append(Punto(
                    lat=lat, lon=lon,
                    ele=float(ele) if ele is not None else None,
                    t=_valor(frame, "timestamp"),
                    fc=int(fc) if fc else None,
                ))
            elif nombre == "session" and sesion is None:
                sesion = {f.name: f.value for f in frame.fields}
            elif nombre == "sport" and not perfil:
                perfil = str(_valor(frame, "name") or "")

    if tipo_archivo not in (None, "activity"):
        raise Descartada(f"no es una actividad (FIT de tipo {tipo_archivo})")
    if sesion is None:
        raise Descartada("FIT sin resumen de sesión")
    if len(puntos) < 2:
        raise Descartada("actividad sin GPS")

    deporte = str(sesion.get("sport") or "")
    subdeporte = str(sesion.get("sub_sport") or "")
    tipo = deporte if subdeporte in ("", "generic") else f"{deporte}/{subdeporte}"

    def num(*claves):
        for c in claves:
            if sesion.get(c) is not None:
                return float(sesion[c])
        return None

    totales = {
        "distancia_m": num("total_distance"),
        "desnivel_pos_m": num("total_ascent"),
        "desnivel_neg_m": num("total_descent"),
        "fc_media": num("avg_heart_rate"),
        "fc_max": num("max_heart_rate"),
        "alt_max_m": num("enhanced_max_altitude", "max_altitude"),
        "alt_min_m": num("enhanced_min_altitude", "min_altitude"),
    }
    return Actividad(
        origen="fit",
        # El FIT no guarda el título de la actividad; lo pondrá el importador
        # del export de Garmin. Mientras, usamos el perfil ("Navegar").
        nombre=perfil or deporte or ruta.stem,
        tipo_original=tipo,
        perfil=perfil,
        puntos=puntos,
        fecha_archivo=sesion.get("start_time"),
        totales_dispositivo={k: v for k, v in totales.items() if v is not None},
    )
