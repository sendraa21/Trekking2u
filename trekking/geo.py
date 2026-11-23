"""Utilidades geográficas: distancias, simplificación y remuestreo."""
from __future__ import annotations

import math

RADIO_TIERRA_M = 6_371_008.8


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia en metros entre dos puntos (lat/lon en grados)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * RADIO_TIERRA_M * math.asin(min(1.0, math.sqrt(a)))


def distancias_acumuladas(lats: list[float], lons: list[float]) -> list[float]:
    acum = [0.0]
    for i in range(1, len(lats)):
        acum.append(acum[-1] + haversine(lats[i - 1], lons[i - 1], lats[i], lons[i]))
    return acum


def filtrar_saltos(lats: list[float], lons: list[float], tiempos: list,
                   v_max: float, max_seguidos: int = 30) -> list[int]:
    """Índices de los puntos buenos, sin los saltos imposibles del GPS.

    Un punto se descarta si, para llegar a él desde el último punto bueno, habría
    que ir a más de `v_max` m/s. Si se descartan muchos seguidos, se asume que el
    GPS se ha recolocado de verdad: se acepta el punto y se sigue desde ahí.
    """
    n = len(lats)
    if n < 2 or tiempos[0] is None:
        return list(range(n))
    buenos, seguidos = [0], 0
    for i in range(1, n):
        j = buenos[-1]
        if tiempos[i] is None or tiempos[j] is None:
            buenos.append(i)
            continue
        dt = max((tiempos[i] - tiempos[j]).total_seconds(), 1.0)
        if haversine(lats[j], lons[j], lats[i], lons[i]) / dt <= v_max or seguidos >= max_seguidos:
            buenos.append(i)
            seguidos = 0
        else:
            seguidos += 1
    return buenos


def proyectar(lats: list[float], lons: list[float]) -> list[tuple[float, float]]:
    """Proyección plana local en metros (suficiente para una ruta)."""
    k = math.cos(math.radians(sum(lats) / len(lats)))
    return [(math.radians(lo) * RADIO_TIERRA_M * k, math.radians(la) * RADIO_TIERRA_M)
            for la, lo in zip(lats, lons)]


def simplificar(xy: list[tuple[float, float]], tolerancia: float) -> list[int]:
    """Douglas-Peucker iterativo. Devuelve los índices de los puntos a conservar."""
    n = len(xy)
    if n < 3:
        return list(range(n))
    conservar = [False] * n
    conservar[0] = conservar[-1] = True
    tol2 = tolerancia * tolerancia
    pila = [(0, n - 1)]
    while pila:
        a, b = pila.pop()
        ax, ay = xy[a]
        dx, dy = xy[b][0] - ax, xy[b][1] - ay
        largo2 = dx * dx + dy * dy
        peor, idx = -1.0, -1
        for i in range(a + 1, b):
            px, py = xy[i][0] - ax, xy[i][1] - ay
            if largo2 == 0:
                d2 = px * px + py * py
            else:
                t = max(0.0, min(1.0, (px * dx + py * dy) / largo2))
                ex, ey = px - t * dx, py - t * dy
                d2 = ex * ex + ey * ey
            if d2 > peor:
                peor, idx = d2, i
        if peor > tol2:
            conservar[idx] = True
            pila.append((a, idx))
            pila.append((idx, b))
    return [i for i, c in enumerate(conservar) if c]


def remuestrear(acum: list[float], series: list[list[float]], paso: float) -> list[list[float]]:
    """Interpola las series cada `paso` metros. Devuelve filas [d, v1, v2, ...]."""
    if len(acum) < 2 or acum[-1] <= 0:
        return []
    total = acum[-1]
    objetivos = [i * paso for i in range(int(total // paso) + 1)]
    if objetivos[-1] < total:
        objetivos.append(total)
    filas, j = [], 0
    for d in objetivos:
        while j < len(acum) - 2 and acum[j + 1] < d:
            j += 1
        d0, d1 = acum[j], acum[j + 1]
        f = 0.0 if d1 == d0 else min(1.0, max(0.0, (d - d0) / (d1 - d0)))
        filas.append([d] + [s[j] + (s[j + 1] - s[j]) * f for s in series])
    return filas
