"""Línea de órdenes de Trekking2u.

    .venv\\Scripts\\python -m trekking publicar          # TODO: procesar + regenerar + subir a GitHub
    .venv\\Scripts\\python -m trekking procesar          # rutas nuevas + regenerar web (sin subir)
    .venv\\Scripts\\python -m trekking procesar --todo   # reprocesar todo desde cero
    .venv\\Scripts\\python -m trekking regenerar         # solo regenerar docs/data (tras editar notas.json)
    .venv\\Scripts\\python -m trekking servir            # ver la web en local
    .venv\\Scripts\\python -m trekking clave             # poner o cambiar la contraseña de la web
"""
from __future__ import annotations

import argparse
import sys

from .config import Config, cargar_config
from .procesar import Informe, procesar, regenerar


def _hm(segundos: int | None) -> str:
    if not segundos:
        return "-"
    h, m = divmod(round(segundos / 60), 60)
    return f"{h}h{m:02d}"


def _mostrar(inf: Informe) -> None:
    if inf.nuevas:
        print(f"Rutas nuevas: {len(inf.nuevas)}")
        for r in sorted(inf.nuevas, key=lambda r: r["inicio"]):
            print(f"  + {r['fecha']}  {r['nombre']:<24} {r['tipo']:<11}"
                  f" {r['distancia_km']:>6.2f} km  +{r['desnivel_pos_m'] or 0} m"
                  f"  {_hm(r['movimiento_s'])} en movimiento")
    for clave, motivo in inf.duplicadas:
        print(f"  = {clave}: {motivo}")
    for clave, motivo in inf.descartadas:
        print(f"  - {clave}: descartado ({motivo})")
    for rid in inf.eliminadas:
        print(f"  x {rid}: su archivo ya no está en data/raw, se quita")
    for clave, error in inf.errores:
        print(f"  ! {clave}: ERROR {error}")
    if inf.sin_cambios:
        print(f"Sin cambios: {inf.sin_cambios} archivo(s) ya procesados")
    if not (inf.nuevas or inf.duplicadas or inf.descartadas or inf.eliminadas or inf.errores):
        print("No hay rutas nuevas.")


def _clave_web(cfg: Config) -> str | None:
    from .cripto import leer_clave
    clave = leer_clave(cfg)
    if not clave and cfg["privacidad"].get("requiere_contrasena"):
        raise SystemExit(
            "Falta la contraseña de la web (trekking.toml pide publicar con contraseña).\n"
            "Ponla con:  .venv\\Scripts\\python -m trekking clave")
    return clave


def _regenerar(cfg: Config) -> dict:
    res = regenerar(cfg, _clave_web(cfg))
    print(f"Web: {res['publicadas']} ruta(s)"
          + (f", {len(res['ocultas'])} oculta(s)" if res["ocultas"] else "")
          + (" - datos cifrados con contraseña" if res["cifrado"] else " - datos SIN cifrar"))
    return res


def _orden_clave(cfg: Config, quitar: bool) -> int:
    from getpass import getpass
    from .cripto import LONGITUD_MINIMA, guardar_clave

    if quitar:
        guardar_clave(cfg, None)
        print("Contraseña borrada de este PC.")
        if cfg["privacidad"].get("requiere_contrasena"):
            print("Ojo: trekking.toml sigue pidiendo contraseña; no se podrá publicar sin ella.")
        return 0
    print("La contraseña protege los datos de la web. Compártela solo con quien queráis.")
    print(f"Usa al menos {LONGITUD_MINIMA} caracteres; mejor varias palabras (p. ej. 'pino-lago-nube-2026').")
    nueva = getpass("Nueva contraseña (no se ve al escribir): ")
    if len(nueva) < LONGITUD_MINIMA:
        print(f"Demasiado corta: mínimo {LONGITUD_MINIMA} caracteres. No se ha cambiado nada.")
        return 1
    if nueva != nueva.strip():
        print("No puede empezar ni acabar con espacios. No se ha cambiado nada.")
        return 1
    if getpass("Repítela: ") != nueva:
        print("No coinciden. No se ha cambiado nada.")
        return 1
    guardar_clave(cfg, nueva)
    print("Guardada en el archivo .env (solo en este PC; nunca se sube a GitHub).")
    _regenerar(cfg)
    print("Para que la web use la nueva contraseña, publica:  publicar.bat")
    return 0


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(prog="trekking", description="Procesa y publica nuestras rutas.")
    ordenes = parser.add_subparsers(dest="orden", required=True)
    p = ordenes.add_parser("publicar", help="procesa lo nuevo, regenera la web y la sube a GitHub")
    p.add_argument("-m", "--mensaje", help="mensaje del commit (opcional)")
    p = ordenes.add_parser("procesar", help="procesa las rutas nuevas y regenera la web (sin subir)")
    p.add_argument("--todo", action="store_true", help="ignora lo ya procesado y empieza de cero")
    ordenes.add_parser("regenerar", help="solo regenera docs/data (tras editar notas.json)")
    s = ordenes.add_parser("servir", help="abre la web en local para verla antes de publicar")
    s.add_argument("--puerto", type=int, default=8000)
    s.add_argument("--sin-navegador", action="store_true")
    c = ordenes.add_parser("clave", help="pone o cambia la contraseña de la web")
    c.add_argument("--quitar", action="store_true", help="borra la contraseña de este PC")
    args = parser.parse_args(argv)

    cfg = cargar_config()
    if args.orden == "servir":
        from .servir import servir
        servir(cfg.raiz / "docs", args.puerto, abrir=not args.sin_navegador)
        return 0
    if args.orden == "clave":
        return _orden_clave(cfg, args.quitar)

    inf = None
    if args.orden in ("procesar", "publicar"):
        _clave_web(cfg)  # falla pronto si falta la contraseña
        inf = procesar(cfg, todo=getattr(args, "todo", False))
        _mostrar(inf)
    res = _regenerar(cfg)

    if args.orden == "publicar":
        from .publicar import ErrorPublicar, subir
        try:
            print(subir(cfg, len(inf.nuevas), res["cifrado"], args.mensaje))
        except ErrorPublicar as e:
            print(f"ERROR: {e}")
            return 1
    return 1 if inf and inf.errores else 0


if __name__ == "__main__":
    sys.exit(main())
