import json
from datetime import datetime, timedelta, timezone

from trekking.config import cargar_config
from trekking.lectores import leer_gpx
from trekking.procesar import procesar, regenerar


def gpx(nombre="Prueba Navegar", tipo="other", inicio=datetime(2025, 6, 14, 6, 0, tzinfo=timezone.utc), n=60):
    pts = []
    for i in range(n):
        t = (inicio + timedelta(seconds=10 * i)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        pts.append(
            f'<trkpt lat="{42.5 + i * 0.0001:.6f}" lon="{0.35 + (i % 7) * 0.00005:.6f}">'
            f"<ele>{1000 + i * 2}</ele><time>{t}</time>"
            f"<extensions><ns3:TrackPointExtension><ns3:hr>{120 + i % 5}</ns3:hr>"
            f"</ns3:TrackPointExtension></extensions></trkpt>")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<gpx version="1.1" creator="test" xmlns="http://www.topografix.com/GPX/1/1" '
        'xmlns:ns3="http://www.garmin.com/xmlschemas/TrackPointExtension/v1">'
        f"<trk><name>{nombre}</name><type>{tipo}</type><trkseg>{''.join(pts)}</trkseg></trk></gpx>")


def proyecto(tmp_path, toml=""):
    (tmp_path / "data" / "raw").mkdir(parents=True)
    base = '[nombres]\nquitar_sufijos = ["Navegar", "Senderismo"]\n'
    (tmp_path / "trekking.toml").write_text(base + toml, encoding="utf-8")
    return cargar_config(tmp_path)


def test_leer_gpx_garmin(tmp_path):
    f = tmp_path / "a.gpx"
    f.write_text(gpx(), encoding="utf-8")
    act = leer_gpx(f)
    assert act.nombre == "Prueba Navegar"
    assert act.tipo_original == "other"
    assert len(act.puntos) == 60
    assert act.puntos[0].fc == 120
    assert act.puntos[0].ele == 1000
    assert act.puntos[0].t.tzinfo is not None


def test_procesado_completo_e_incremental(tmp_path):
    cfg = proyecto(tmp_path)
    (cfg.dir_raw / "a.gpx").write_text(gpx("Collado Navegar"), encoding="utf-8")
    (cfg.dir_raw / "b.gpx").write_text(
        gpx("Pinar Senderismo", "hiking", datetime(2025, 11, 2, 7, 30, tzinfo=timezone.utc)),
        encoding="utf-8")

    inf = procesar(cfg)
    assert len(inf.nuevas) == 2 and not inf.errores
    por_nombre = {r["nombre"]: r for r in inf.nuevas}
    assert por_nombre["Collado"]["tipo"] == "navegacion"
    assert por_nombre["Collado"]["id"] == "2025-06-14-collado"
    assert por_nombre["Collado"]["fecha"] == "2025-06-14"
    assert por_nombre["Collado"]["inicio"].endswith("+02:00")  # hora de Madrid en verano
    assert por_nombre["Pinar"]["tipo"] == "senderismo"
    # Sube 118 m en escalones de 2 m: el umbral de 3 m cuenta 116 (el último escalón no llega)
    assert por_nombre["Collado"]["desnivel_pos_m"] == 116

    # Segunda pasada: nada nuevo
    inf2 = procesar(cfg)
    assert inf2.nuevas == [] and inf2.sin_cambios == 2

    regenerar(cfg)
    rutas = json.loads((cfg.dir_web_datos / "rutas.json").read_text(encoding="utf-8"))["rutas"]
    assert [r["nombre"] for r in rutas] == ["Pinar", "Collado"]  # más reciente primero
    assert "nombre_original" not in rutas[0]
    assert rutas[1]["archivo"] == "rutas/2025-06-14-collado.geojson"
    ficha = json.loads((cfg.dir_web_datos / rutas[1]["archivo"]).read_text(encoding="utf-8"))
    assert ficha["geometry"]["type"] == "LineString"
    assert len(ficha["properties"]["perfil"]) > 2
    assert not (cfg.dir_web_datos / "cripto.json").exists()
    todas = json.loads((cfg.dir_web_datos / "todas.json").read_text(encoding="utf-8"))
    assert len(todas["features"]) == 2


def test_duplicados_y_borrados(tmp_path):
    cfg = proyecto(tmp_path)
    (cfg.dir_raw / "a.gpx").write_text(gpx(), encoding="utf-8")
    (cfg.dir_raw / "copia.gpx").write_text(gpx(n=61), encoding="utf-8")  # misma hora de inicio
    inf = procesar(cfg)
    assert len(inf.nuevas) == 1 and len(inf.duplicadas) == 1

    (cfg.dir_raw / "a.gpx").unlink()
    (cfg.dir_raw / "copia.gpx").unlink()
    inf = procesar(cfg)
    assert inf.eliminadas == ["2025-06-14-prueba"]
    assert list(cfg.dir_procesadas.glob("*.json")) == []


def test_notas_y_privacidad(tmp_path):
    cfg = proyecto(tmp_path, "[privacidad]\nrecorte_inicio_m = 50\nrecorte_fin_m = 50\nmostrar_fc = false\n")
    (cfg.dir_raw / "a.gpx").write_text(gpx(), encoding="utf-8")
    (cfg.dir_raw / "b.gpx").write_text(
        gpx("Otra", inicio=datetime(2026, 8, 1, 6, 0, tzinfo=timezone.utc)), encoding="utf-8")
    procesar(cfg)
    cfg.archivo_notas.write_text(json.dumps({"rutas": {
        "2025-06-14-prueba": {"nombre": "Mirador del Pinar", "descripcion": "¡Qué día!"},
        "2026-08-01-otra": {"ocultar": True},
    }}), encoding="utf-8")
    res = regenerar(cfg)
    assert res["publicadas"] == 1 and res["ocultas"] == ["2026-08-01-otra"]
    ficha = json.loads((cfg.dir_web_datos / "rutas" / "2025-06-14-prueba.geojson").read_text(encoding="utf-8"))
    props = ficha["properties"]
    assert props["nombre"] == "Mirador del Pinar" and props["descripcion"] == "¡Qué día!"
    assert "fc_media" not in props
    # El primer punto publicado está a más de 50 m del inicio real
    assert ficha["geometry"]["coordinates"][0][1] > 42.5 + 0.0004
    assert props["perfil"][0][2] is None  # sin coordenadas en la zona recortada
    assert not (cfg.dir_web_datos / "rutas" / "2026-08-01-otra.geojson").exists()
