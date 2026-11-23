"""Cálculo de métricas de una ruta."""
from __future__ import annotations

from datetime import datetime


def desnivel(eles: list[float | None], umbral: float) -> tuple[float, float]:
    """Desnivel positivo y negativo con histéresis.

    Solo cuenta un cambio cuando supera `umbral` metros respecto al último
    punto de referencia; así el ruido del GPS/barómetro no infla el total.
    """
    sube = baja = 0.0
    ref = None
    for e in eles:
        if e is None:
            continue
        if ref is None:
            ref = e
            continue
        d = e - ref
        if d >= umbral:
            sube += d
            ref = e
        elif d <= -umbral:
            baja -= d
            ref = e
    return sube, baja


def tiempo_movimiento(tiempos: list[datetime | None], acum: list[float],
                      eles: list[float | None], v_min: float, v_min_vertical: float) -> float | None:
    """Segundos en los que avanzamos (en horizontal o subiendo/bajando)."""
    if not tiempos or tiempos[0] is None:
        return None
    total = 0.0
    for i in range(1, len(tiempos)):
        t0, t1 = tiempos[i - 1], tiempos[i]
        if t0 is None or t1 is None:
            continue
        dt = (t1 - t0).total_seconds()
        if dt <= 0:
            continue
        v = (acum[i] - acum[i - 1]) / dt
        e0, e1 = eles[i - 1], eles[i]
        vz = abs(e1 - e0) / dt if e0 is not None and e1 is not None else 0.0
        if v >= v_min or vz >= v_min_vertical:
            total += dt
    return total


def fc_media(tiempos: list[datetime | None], fcs: list[int | None]) -> float | None:
    """Media de FC ponderada por tiempo (los relojes no graban a intervalos fijos)."""
    suma = peso = 0.0
    for i in range(len(fcs) - 1):
        f, t0, t1 = fcs[i], tiempos[i], tiempos[i + 1]
        if f is None or t0 is None or t1 is None:
            continue
        dt = (t1 - t0).total_seconds()
        if dt > 0:
            suma += f * dt
            peso += dt
    if peso:
        return suma / peso
    validas = [f for f in fcs if f is not None]
    return sum(validas) / len(validas) if validas else None
