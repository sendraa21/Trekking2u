"""Servidor local para ver la web antes de publicarla.

Windows a veces asocia .js con "text/plain" en el registro y el navegador
rechaza los módulos; aquí se fuerzan los tipos correctos.
"""
from __future__ import annotations

import functools
import http.server
import webbrowser
from pathlib import Path

TIPOS = {
    ".js": "text/javascript",
    ".mjs": "text/javascript",
    ".css": "text/css",
    ".json": "application/json",
    ".geojson": "application/geo+json",
    ".svg": "image/svg+xml",
    ".html": "text/html",
}


class _Manejador(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, **TIPOS}

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def servir(carpeta: Path, puerto: int = 8000, abrir: bool = True) -> None:
    manejador = functools.partial(_Manejador, directory=str(carpeta))
    with http.server.ThreadingHTTPServer(("127.0.0.1", puerto), manejador) as srv:
        url = f"http://127.0.0.1:{puerto}/"
        print(f"Web local en {url}  (Ctrl+C para parar)")
        if abrir:
            webbrowser.open(url)
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            pass
