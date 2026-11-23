"""Cifrado de los datos publicados con una contraseña compartida.

Los datos de docs/data se suben a un repositorio público; cifrados, solo
quien conoce la contraseña puede leerlos (la web los descifra en el navegador
con Web Crypto). El formato es compatible con el navegador:

- docs/data/cripto.json  {"v", "kdf", "iteraciones", "sal", "prueba"}
- cada archivo cifrado es un "sobre"  {"v": 1, "iv": base64, "datos": base64}
- clave: PBKDF2-HMAC-SHA256(contraseña, sal, iteraciones) -> 64 bytes
    [0:32]  clave AES-256-GCM (la única que necesita el navegador)
    [32:64] clave HMAC, para el IV y para los nombres de archivo
- IV = HMAC(k_mac, "iv" + contenido)[:12]: el mismo contenido produce el mismo
  cifrado, así git no ve cambios cuando nada ha cambiado.
- nombre de archivo = HMAC(k_mac, "nombre" + id): no revela lugares ni fechas.

La contraseña se guarda solo en tu PC, en el archivo .env (ignorado por git).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .config import Config

ITERACIONES = 310_000
PRUEBA = b"trekking2u"
VARIABLE = "TREKKING_CLAVE"
LONGITUD_MINIMA = 10


def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


def _de64(s: str) -> bytes:
    return base64.b64decode(s)


class ClaveIncorrecta(Exception):
    pass


@dataclass(frozen=True)
class Cifrador:
    k_aes: bytes
    k_mac: bytes
    sal: bytes
    iteraciones: int

    @classmethod
    def desde_clave(cls, clave: str, sal: bytes | None = None,
                    iteraciones: int = ITERACIONES) -> "Cifrador":
        sal = sal or os.urandom(16)
        bits = hashlib.pbkdf2_hmac("sha256", clave.encode("utf-8"), sal, iteraciones, dklen=64)
        return cls(k_aes=bits[:32], k_mac=bits[32:], sal=sal, iteraciones=iteraciones)

    def cifrar(self, contenido: bytes) -> dict:
        iv = hmac.new(self.k_mac, b"iv" + contenido, "sha256").digest()[:12]
        return {"v": 1, "iv": _b64(iv), "datos": _b64(AESGCM(self.k_aes).encrypt(iv, contenido, None))}

    def descifrar(self, sobre: dict) -> bytes:
        try:
            return AESGCM(self.k_aes).decrypt(_de64(sobre["iv"]), _de64(sobre["datos"]), None)
        except Exception as e:  # InvalidTag
            raise ClaveIncorrecta("contraseña incorrecta o datos dañados") from e

    def cifrar_json(self, datos) -> dict:
        return self.cifrar(json.dumps(datos, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))

    def nombre(self, rid: str) -> str:
        return hmac.new(self.k_mac, b"nombre" + rid.encode("utf-8"), "sha256").hexdigest()[:20]

    def cabecera(self) -> dict:
        return {
            "v": 1,
            "kdf": "PBKDF2-SHA256",
            "iteraciones": self.iteraciones,
            "sal": _b64(self.sal),
            "prueba": self.cifrar(PRUEBA),
        }


def preparar_cifrador(clave: str, cabecera_anterior: dict | None) -> Cifrador:
    """Reutiliza la sal anterior si la contraseña no ha cambiado (menos cambios en git)."""
    if cabecera_anterior:
        try:
            c = Cifrador.desde_clave(clave, _de64(cabecera_anterior["sal"]),
                                     int(cabecera_anterior["iteraciones"]))
            if c.descifrar(cabecera_anterior["prueba"]) == PRUEBA:
                return c
        except (KeyError, ValueError, ClaveIncorrecta):
            pass
    return Cifrador.desde_clave(clave)


# ------------------------------------------------------ contraseña en .env

def _archivo_env(cfg: Config) -> Path:
    return cfg.raiz / ".env"


def leer_clave(cfg: Config) -> str | None:
    if os.environ.get(VARIABLE):
        return os.environ[VARIABLE]
    env = _archivo_env(cfg)
    if not env.exists():
        return None
    for linea in env.read_text(encoding="utf-8").splitlines():
        if linea.strip().startswith(f"{VARIABLE}="):
            valor = linea.split("=", 1)[1].strip()
            return valor or None
    return None


def guardar_clave(cfg: Config, clave: str | None) -> None:
    """Guarda (o borra, con None) la contraseña en .env conservando el resto de líneas."""
    env = _archivo_env(cfg)
    lineas = env.read_text(encoding="utf-8").splitlines() if env.exists() else []
    lineas = [l for l in lineas if not l.strip().startswith(f"{VARIABLE}=")]
    if clave:
        lineas.append(f"{VARIABLE}={clave}")
    env.write_text("\n".join(lineas) + ("\n" if lineas else ""), encoding="utf-8")
