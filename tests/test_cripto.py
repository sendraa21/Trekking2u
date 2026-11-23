import json
from datetime import datetime, timezone

import pytest

from trekking.cripto import (Cifrador, ClaveIncorrecta, guardar_clave, leer_clave,
                             preparar_cifrador)
from trekking.procesar import procesar, regenerar
from trekking.publicar import _prohibido

from test_procesar import gpx, proyecto

CLAVE = "prueba-de-test-123"


def test_ida_y_vuelta_y_determinista():
    c = Cifrador.desde_clave(CLAVE, iteraciones=1000)
    sobre = c.cifrar(b"hola")
    assert c.descifrar(sobre) == b"hola"
    assert c.cifrar(b"hola") == sobre            # mismo contenido, mismo cifrado
    assert c.cifrar(b"adios")["iv"] != sobre["iv"]


def test_contrasena_incorrecta():
    c = Cifrador.desde_clave(CLAVE, iteraciones=1000)
    otro = Cifrador.desde_clave("otra-contrasena", c.sal, 1000)
    with pytest.raises(ClaveIncorrecta):
        otro.descifrar(c.cifrar(b"secreto"))


def test_reutiliza_sal_si_no_cambia_la_contrasena():
    c = Cifrador.desde_clave(CLAVE, iteraciones=1000)
    cab = c.cabecera()
    assert preparar_cifrador(CLAVE, cab).sal == c.sal
    assert preparar_cifrador("nueva-contrasena-1", cab).sal != c.sal


def test_clave_en_env(tmp_path):
    cfg = proyecto(tmp_path)
    (tmp_path / ".env").write_text("OTRA=1\n", encoding="utf-8")
    assert leer_clave(cfg) is None
    guardar_clave(cfg, "con=igual y espacios")
    assert leer_clave(cfg) == "con=igual y espacios"
    guardar_clave(cfg, None)
    assert leer_clave(cfg) is None
    assert (tmp_path / ".env").read_text(encoding="utf-8") == "OTRA=1\n"


def test_regenerar_cifrado_no_deja_nada_legible(tmp_path):
    cfg = proyecto(tmp_path)
    (cfg.dir_raw / "a.gpx").write_text(gpx("Collado Navegar"), encoding="utf-8")
    procesar(cfg)
    regenerar(cfg)  # primero en claro...
    assert (cfg.dir_web_datos / "rutas" / "2025-06-14-collado.geojson").exists()

    res = regenerar(cfg, CLAVE)  # ...y luego cifrado: lo anterior desaparece
    assert res["cifrado"]
    publicados = [p for p in cfg.dir_web_datos.rglob("*") if p.is_file()]
    for p in publicados:
        texto = p.read_text(encoding="utf-8")
        assert "Collado" not in texto and "navegacion" not in texto
        assert "collado" not in p.name and "2026" not in p.name
    cab = json.loads((cfg.dir_web_datos / "cripto.json").read_text(encoding="utf-8"))
    c = preparar_cifrador(CLAVE, cab)
    rutas = json.loads(c.descifrar(json.loads((cfg.dir_web_datos / "rutas.json").read_text())))["rutas"]
    assert rutas[0]["nombre"] == "Collado"
    ficha = json.loads(c.descifrar(json.loads((cfg.dir_web_datos / rutas[0]["archivo"]).read_text())))
    assert ficha["geometry"]["type"] == "LineString"

    # Sin cambios, regenerar otra vez produce exactamente los mismos archivos
    antes = {p.name: p.read_bytes() for p in publicados}
    regenerar(cfg, CLAVE)
    despues = {p.name: p.read_bytes() for p in cfg.dir_web_datos.rglob("*") if p.is_file()}
    assert antes == despues


@pytest.mark.parametrize("archivo,cifrado,esperado", [
    ("data/raw/a.gpx", False, True),
    ("data/procesadas/x.json", True, True),
    (".env", False, True),
    ("data/estado.json", False, True),
    ("docs/data/rutas/2025-06-14-x.geojson", True, True),
    ("docs/data/rutas/2025-06-14-x.geojson", False, False),
    ("docs/data/rutas/abc.json", True, False),
    ("data/notas.json", True, False),
    ("docs/index.html", True, False),
])
def test_archivos_prohibidos_al_publicar(archivo, cifrado, esperado):
    assert _prohibido(archivo, cifrado) is esperado
