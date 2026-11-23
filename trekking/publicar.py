"""Publicar: procesar lo nuevo, regenerar la web, comprobar y subir a GitHub."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from datetime import date

from .config import Config

RUTAS_GIT_WINDOWS = (r"C:\Program Files\Git\cmd\git.exe",)


class ErrorPublicar(Exception):
    pass


def buscar_git() -> str:
    git = shutil.which("git") or next((p for p in RUTAS_GIT_WINDOWS if os.path.exists(p)), None)
    if not git:
        raise ErrorPublicar("No encuentro Git. Instálalo con: winget install -e --id Git.Git")
    return git


def _git(cfg: Config, *args: str, comprobar: bool = True) -> str:
    r = subprocess.run([buscar_git(), *args], cwd=cfg.raiz, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if comprobar and r.returncode != 0:
        raise ErrorPublicar(f"git {' '.join(args)} falló:\n{r.stderr.strip() or r.stdout.strip()}")
    return r.stdout.strip()


def url_web(cfg: Config) -> str | None:
    remoto = _git(cfg, "remote", "get-url", "origin", comprobar=False)
    m = re.search(r"github\.com[:/]([^/]+)/([^/.]+)", remoto)
    return f"https://{m.group(1).lower()}.github.io/{m.group(2)}/" if m else None


def _prohibido(archivo: str, cifrado: bool) -> bool:
    """Archivos que nunca deben llegar a GitHub."""
    if archivo.startswith(("data/raw/", "data/entrada/", "data/procesadas/")):
        return True
    if archivo in (".env", "data/estado.json"):
        return True
    # Con contraseña, en docs/data solo puede haber sobres cifrados (.json)
    return cifrado and archivo.startswith("docs/data/") and not archivo.endswith(".json")


def subir(cfg: Config, nuevas: int, cifrado: bool, mensaje: str | None = None) -> str:
    """Hace commit y push de los cambios. Devuelve un texto con lo ocurrido."""
    _git(cfg, "add", "-A")
    preparados = [l for l in _git(cfg, "diff", "--cached", "--name-only").splitlines() if l]
    peligrosos = [a for a in preparados if _prohibido(a, cifrado)]
    if peligrosos:
        _git(cfg, "reset", "-q")
        raise ErrorPublicar("Se iban a subir archivos privados; no se ha publicado nada:\n  "
                            + "\n  ".join(peligrosos))
    if not preparados:
        return "No hay cambios que publicar."

    # El mensaje no incluye nombres de rutas: el historial de git es público.
    if not mensaje:
        mensaje = f"Rutas actualizadas el {date.today():%d/%m/%Y}"
        if nuevas:
            mensaje += f" ({nuevas} {'nueva' if nuevas == 1 else 'nuevas'})"
    _git(cfg, "commit", "-q", "-m", mensaje)

    if not _git(cfg, "remote", comprobar=False):
        return "Guardado en git, pero el proyecto aún no está conectado a GitHub (falta 'origin')."
    _git(cfg, "push", "-q", "-u", "origin", "HEAD")
    web = url_web(cfg)
    return "Publicado en GitHub." + (f" La web se actualiza en 1-2 minutos: {web}" if web else "")
