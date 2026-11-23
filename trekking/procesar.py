"""Procesado incremental.

data/raw/*.gpx|*.fit  --procesar-->  data/procesadas/<id>.json  (caché privada, detalle completo)
                     --regenerar-->  docs/data/rutas.json, todas.geojson, rutas/<id>.geojson  (lo publicado)

`procesar` solo lee los archivos nuevos o modificados (lo controla data/estado.json).
`regenerar` reconstruye siempre docs/data aplicando notas.json y los ajustes de
privacidad, así que cambiar un título o el recorte no obliga a reprocesar.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from . import geo, metricas
from .config import Config
from .lectores import EXTENSIONES, leer
from .modelo import Actividad, Descartada

# Súbelo cuando cambie la forma de calcular algo: obliga a reprocesar todo.
VERSION_PROCESADO = 3  # 2: movimiento con distancias GPS sin escalar; 3: FIT cerca del meridiano 0 y saltos de GPS

TIPOS = ("trail", "senderismo", "navegacion")  # orden de prioridad al clasificar
CAMPOS_PRIVADOS = ("nombre_original", "tipo_original", "origen")
CAMPOS_FC = ("fc_media", "fc_max")


@dataclass
class Informe:
    nuevas: list[dict] = field(default_factory=list)
    descartadas: list[tuple[str, str]] = field(default_factory=list)
    duplicadas: list[tuple[str, str]] = field(default_factory=list)
    errores: list[tuple[str, str]] = field(default_factory=list)
    eliminadas: list[str] = field(default_factory=list)
    sin_cambios: int = 0


# ------------------------------------------------------------- utilidades

def leer_json(ruta: Path, defecto):
    if not ruta.exists():
        return defecto
    return json.loads(ruta.read_text(encoding="utf-8"))


def escribir_json(ruta: Path, datos, compacto: bool = False) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    if compacto:
        texto = json.dumps(datos, ensure_ascii=False, separators=(",", ":"))
    else:
        texto = json.dumps(datos, ensure_ascii=False, indent=2)
    tmp = ruta.with_name(ruta.name + ".tmp")
    tmp.write_text(texto + "\n", encoding="utf-8")
    tmp.replace(ruta)  # escritura atómica: nunca queda un archivo a medias


def huella(ruta: Path) -> str:
    h = hashlib.sha1()
    with ruta.open("rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def slug(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    t = re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")
    return t[:60].strip("-") or "ruta"


def _r(v: float | None) -> int | None:
    return None if v is None else int(round(v))


def _r5(v: float | None) -> float | None:
    return None if v is None else round(v, 5)


# ---------------------------------------------------- clasificar y nombrar

def clasificar(act: Actividad, cfg: Config) -> str | None:
    tipo = act.tipo_original.lower()
    fichas = set(re.split(r"[/\s]+", tipo)) | {tipo}
    textos = f"{act.perfil} {act.nombre}".lower()
    for t in TIPOS:
        for palabra in cfg["clasificacion"].get(t, []):
            p = palabra.lower()
            if p in fichas or re.search(rf"\b{re.escape(p)}\b", textos):
                return t
    return None


def limpiar_nombre(nombre: str, sufijos: list[str]) -> str:
    nombre = nombre.strip()
    for s in sorted(sufijos, key=len, reverse=True):
        if nombre.lower().endswith(" " + s.lower()):
            return nombre[: -len(s)].strip()
    return nombre


# ------------------------------------------------------- construir ruta

def construir_ruta(act: Actividad, tipo: str, cfg: Config) -> dict:
    pts = act.puntos
    buenos = geo.filtrar_saltos([p.lat for p in pts], [p.lon for p in pts], [p.t for p in pts],
                                float(cfg["calculo"]["velocidad_max_gps_ms"]))
    pts = [pts[i] for i in buenos]
    if len(pts) < 2:
        raise Descartada("el GPS no tiene puntos válidos")
    lats = [p.lat for p in pts]
    lons = [p.lon for p in pts]
    eles = [p.ele for p in pts]
    tiempos = [p.t for p in pts]
    fcs = [p.fc for p in pts]
    dev = act.totales_dispositivo
    calc = cfg["calculo"]
    simp = cfg["simplificacion"]

    acum = geo.distancias_acumuladas(lats, lons)
    acum_gps = acum  # distancias reales entre puntos: para decidir si nos movíamos
    if dev.get("distancia_m") and acum[-1] > 0:
        # Ajusta las distancias al total del reloj para que el perfil cuadre.
        factor = dev["distancia_m"] / acum[-1]
        acum = [d * factor for d in acum]
    distancia = acum[-1]

    sube, baja = metricas.desnivel(eles, calc["umbral_desnivel_m"])
    sube = dev.get("desnivel_pos_m", sube)
    baja = dev.get("desnivel_neg_m", baja)
    validas = [e for e in eles if e is not None]
    alt_max = dev.get("alt_max_m", max(validas) if validas else None)
    alt_min = dev.get("alt_min_m", min(validas) if validas else None)

    inicio = tiempos[0] or act.fecha_archivo
    if inicio is None:
        raise Descartada("la ruta no tiene fecha")
    fin = next((t for t in reversed(tiempos) if t), None)
    duracion = (fin - tiempos[0]).total_seconds() if tiempos[0] and fin else None
    movimiento = metricas.tiempo_movimiento(
        tiempos, acum_gps, eles, calc["velocidad_min_movimiento_ms"], calc["velocidad_min_vertical_ms"])
    fc_validas = [f for f in fcs if f]
    fc_med = dev.get("fc_media") or metricas.fc_media(tiempos, fcs)
    fc_max = dev.get("fc_max") or (max(fc_validas) if fc_validas else None)

    local = inicio.astimezone(ZoneInfo(cfg.zona_horaria))
    nombre = limpiar_nombre(act.nombre, cfg["nombres"]["quitar_sufijos"]) or act.nombre
    resumen = {
        "nombre": nombre,
        "nombre_original": act.nombre,
        "tipo": tipo,
        "tipo_original": act.tipo_original,
        "origen": act.origen,
        "fecha": local.date().isoformat(),
        "anio": local.year,
        "inicio": local.isoformat(timespec="seconds"),
        "distancia_km": round(distancia / 1000, 2),
        "desnivel_pos_m": _r(sube),
        "desnivel_neg_m": _r(baja),
        "duracion_s": _r(duracion),
        "movimiento_s": _r(movimiento),
        "ritmo_s_km": _r(movimiento / (distancia / 1000)) if movimiento and distancia > 0 else None,
        "alt_max_m": _r(alt_max),
        "alt_min_m": _r(alt_min),
        "fc_media": _r(fc_med),
        "fc_max": _r(fc_max),
    }

    # Trazado simplificado: [lon, lat, ele, distancia_m]
    indices = geo.simplificar(geo.proyectar(lats, lons), simp["tolerancia_ruta_m"])
    coords = [[round(lons[i], 6), round(lats[i], 6),
               None if eles[i] is None else round(eles[i], 1), round(acum[i], 1)]
              for i in indices]

    # Perfil remuestreado a distancia fija: [distancia_m, ele, lon, lat]
    perfil: list[list[float]] = []
    con_ele = [i for i, e in enumerate(eles) if e is not None]
    if len(con_ele) >= 2:
        paso = max(10.0, distancia / simp["max_puntos_perfil"])
        filas = geo.remuestrear(
            [acum[i] for i in con_ele],
            [[eles[i] for i in con_ele], [lons[i] for i in con_ele], [lats[i] for i in con_ele]],
            paso)
        perfil = [[round(d, 1), round(e, 1), round(lo, 6), round(la, 6)] for d, e, lo, la in filas]

    return {"resumen": resumen, "coords": coords, "perfil": perfil}


# ------------------------------------------------------------- procesar

def _retirar(cfg: Config, archivos: dict, clave: str) -> None:
    entrada = archivos.pop(clave, None)
    if entrada and entrada.get("ruta_id"):
        (cfg.dir_procesadas / f"{entrada['ruta_id']}.json").unlink(missing_ok=True)


def _buscar_duplicado(archivos: dict, inicio: str, margen_s: float, excluir: str):
    t = datetime.fromisoformat(inicio)
    for clave, e in archivos.items():
        if clave == excluir or e.get("estado") != "ok":
            continue
        if abs((datetime.fromisoformat(e["inicio"]) - t).total_seconds()) <= margen_s:
            return clave, e
    return None


def _id_unico(archivos: dict, base: str) -> str:
    usados = {e.get("ruta_id") for e in archivos.values()}
    rid, n = base, 2
    while rid in usados:
        rid, n = f"{base}-{n}", n + 1
    return rid


def procesar(cfg: Config, todo: bool = False) -> Informe:
    inf = Informe()
    estado = leer_json(cfg.archivo_estado, {})
    if todo or estado.get("version") != VERSION_PROCESADO:
        estado = {}
        for f in cfg.dir_procesadas.glob("*.json"):
            f.unlink()
    estado["version"] = VERSION_PROCESADO
    archivos: dict = estado.setdefault("archivos", {})
    notas = leer_json(cfg.archivo_notas, {})
    incluir = {n.lower() for n in notas.get("incluir_archivos", [])}

    cfg.dir_raw.mkdir(parents=True, exist_ok=True)
    # Los FIT primero: si la misma salida llega como FIT y GPX, gana el FIT.
    encontrados = sorted(
        (p for p in cfg.dir_raw.rglob("*") if p.is_file() and p.suffix.lower() in EXTENSIONES),
        key=lambda p: (p.suffix.lower() != ".fit", str(p).lower()))

    from .garmin_export import metadatos_de  # import aquí: garmin_export usa este módulo

    vistos: set[str] = set()
    cache_meta: dict = {}
    for ruta in encontrados:
        clave = ruta.relative_to(cfg.dir_raw).as_posix()
        vistos.add(clave)
        forzado = ruta.name.lower() in incluir
        # Título y tipo de Garmin (FIT importados del export); si cambian, se reprocesa.
        meta = metadatos_de(ruta, cache_meta) if ruta.suffix.lower() == ".fit" else None
        firma = huella(ruta) + ("+incluir" if forzado else "")
        if meta:
            firma += "+" + hashlib.sha1(json.dumps(meta, sort_keys=True).encode()).hexdigest()[:12]
        previo = archivos.get(clave)
        if previo and previo.get("firma") == firma:
            inf.sin_cambios += 1
            continue
        if previo:
            _retirar(cfg, archivos, clave)

        try:
            act = leer(ruta)
            if meta:
                act.nombre = meta.get("nombre") or act.nombre
                act.tipo_original = f"{act.tipo_original} {meta.get('tipo_garmin', '')}".strip()
            tipo = clasificar(act, cfg)
            if tipo is None:
                if act.origen == "gpx" or forzado:
                    tipo = "otro"
                else:
                    raise Descartada(f"actividad de tipo '{act.tipo_original or '?'}'")
            datos = construir_ruta(act, tipo, cfg)
        except Descartada as e:
            archivos[clave] = {"firma": firma, "estado": "descartado", "motivo": str(e)}
            inf.descartadas.append((clave, str(e)))
            continue
        except Exception as e:  # noqa: BLE001 - se informa y se reintenta la próxima vez
            inf.errores.append((clave, f"{type(e).__name__}: {e}"))
            continue

        res = datos["resumen"]
        margen = float(cfg["calculo"]["duplicado_margen_s"])
        dup = _buscar_duplicado(archivos, res["inicio"], margen, excluir=clave)
        if dup:
            clave_dup, entrada_dup = dup
            if act.origen == "fit" and entrada_dup.get("origen") == "gpx":
                _retirar(cfg, archivos, clave_dup)
                archivos[clave_dup] = {"firma": entrada_dup["firma"], "estado": "duplicado",
                                       "motivo": f"misma salida que {clave}"}
                inf.duplicadas.append((clave_dup, f"sustituido por {clave}"))
            else:
                archivos[clave] = {"firma": firma, "estado": "duplicado",
                                   "motivo": f"misma salida que {clave_dup}"}
                inf.duplicadas.append((clave, f"misma salida que {clave_dup}"))
                continue

        rid = _id_unico(archivos, f"{res['fecha']}-{slug(res['nombre'])}")
        datos["resumen"] = {"id": rid, **res}
        escribir_json(cfg.dir_procesadas / f"{rid}.json", datos, compacto=True)
        archivos[clave] = {"firma": firma, "estado": "ok", "ruta_id": rid,
                           "origen": act.origen, "inicio": res["inicio"]}
        inf.nuevas.append(datos["resumen"])

    # Archivos que ya no están en data/raw: su ruta desaparece.
    for clave in [c for c in archivos if c not in vistos]:
        if archivos[clave].get("ruta_id"):
            inf.eliminadas.append(archivos[clave]["ruta_id"])
        _retirar(cfg, archivos, clave)

    escribir_json(cfg.archivo_estado, estado)
    return inf


# ------------------------------------------------------------ regenerar

def _recortar(coords: list, perfil: list, inicio_m: float, fin_m: float):
    if inicio_m <= 0 and fin_m <= 0:
        return coords, perfil
    total = coords[-1][3]
    lo, hi = inicio_m, total - fin_m
    coords = [c for c in coords if lo <= c[3] <= hi]
    perfil = [p if lo <= p[0] <= hi else [p[0], p[1], None, None] for p in perfil]
    return coords, perfil


def regenerar(cfg: Config, clave: str | None = None) -> dict:
    """Reconstruye docs/data. Con `clave`, todo se publica cifrado."""
    notas = leer_json(cfg.archivo_notas, {}).get("rutas", {})
    priv = cfg["privacidad"]
    simp = cfg["simplificacion"]
    salida = cfg.dir_web_datos
    dir_rutas = salida / "rutas"

    cifrador = None
    if clave:
        from .cripto import preparar_cifrador  # solo hace falta 'cryptography' si se cifra
        cifrador = preparar_cifrador(clave, leer_json(salida / "cripto.json", None))

    # Se borra todo lo publicado antes: así nunca conviven datos en claro y cifrados.
    dir_rutas.mkdir(parents=True, exist_ok=True)
    for f in dir_rutas.iterdir():
        if f.is_file():
            f.unlink()
    for nombre in ("rutas.json", "todas.json", "todas.geojson", "cripto.json"):
        (salida / nombre).unlink(missing_ok=True)

    def publicar(nombre: str, datos, compacto: bool = True) -> None:
        if cifrador:
            escribir_json(salida / nombre, cifrador.cifrar_json(datos), compacto=True)
        else:
            escribir_json(salida / nombre, datos, compacto=compacto)

    resumenes: list[dict] = []
    generales: list[dict] = []
    ocultas: list[str] = []
    for f in sorted(cfg.dir_procesadas.glob("*.json")):
        datos = leer_json(f, None)
        res = dict(datos["resumen"])
        nota = notas.get(res["id"], {})
        if nota.get("ocultar"):
            ocultas.append(res["id"])
            continue
        for campo in ("nombre", "descripcion", "tipo"):
            if nota.get(campo):
                res[campo] = nota[campo]
        for campo in CAMPOS_PRIVADOS + (() if priv.get("mostrar_fc", True) else CAMPOS_FC):
            res.pop(campo, None)

        coords, perfil = _recortar(datos["coords"], datos["perfil"],
                                   priv["recorte_inicio_m"], priv["recorte_fin_m"])
        if len(coords) < 2:
            ocultas.append(res["id"])
            continue
        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        res["bbox"] = [round(min(lons), 5), round(min(lats), 5), round(max(lons), 5), round(max(lats), 5)]
        res["punto_inicio"] = [round(lons[0], 5), round(lats[0], 5)]

        con_ele = all(c[2] is not None for c in coords)
        linea = [[round(c[0], 5), round(c[1], 5)] + ([round(c[2])] if con_ele else []) for c in coords]
        perfil_pub = [[round(p[0] / 1000, 3), round(p[1]), _r5(p[2]), _r5(p[3])] for p in perfil]
        res["archivo"] = (f"rutas/{cifrador.nombre(res['id'])}.json" if cifrador
                          else f"rutas/{res['id']}.geojson")
        publicar(res["archivo"], {
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": linea},
            "properties": {**res, "perfil": perfil_pub},
        })

        idx = geo.simplificar(geo.proyectar(lats, lons), simp["tolerancia_mapa_general_m"])
        generales.append({
            "type": "Feature",
            "geometry": {"type": "LineString",
                         "coordinates": [[round(lons[i], 4), round(lats[i], 4)] for i in idx]},
            "properties": {k: res[k] for k in ("id", "nombre", "tipo", "fecha", "anio")},
        })
        resumenes.append(res)

    resumenes.sort(key=lambda r: r["inicio"], reverse=True)
    publicar("rutas.json", {"rutas": resumenes}, compacto=False)
    publicar("todas.json", {"type": "FeatureCollection", "features": generales})
    if cifrador:
        escribir_json(salida / "cripto.json", cifrador.cabecera())
    return {"publicadas": len(resumenes), "ocultas": ocultas, "cifrado": bool(cifrador)}
