from datetime import datetime, timedelta, timezone

import pytest

from trekking import geo, metricas


def test_haversine_un_grado_de_latitud():
    assert geo.haversine(40.0, -3.0, 41.0, -3.0) == pytest.approx(111_195, rel=1e-3)


def test_simplificar_linea_recta_deja_extremos():
    xy = [(float(i), 0.0) for i in range(100)]
    assert geo.simplificar(xy, 1.0) == [0, 99]


def test_simplificar_conserva_esquina():
    xy = [(float(i), 0.0) for i in range(50)] + [(49.0, float(i)) for i in range(1, 50)]
    assert 49 in geo.simplificar(xy, 1.0)


def test_semicirculos_cerca_del_meridiano_cero():
    from trekking.lectores import _grados
    # -0.00001° son unos -119 semicírculos; antes se confundían con grados
    assert _grados(-119) == pytest.approx(-0.00001, abs=1e-7)
    assert _grados(42 * 2**31 / 180) == pytest.approx(42.0)
    assert _grados(90) == pytest.approx(90 * 180 / 2**31)


def test_filtrar_saltos_quita_picos_y_acepta_recolocaciones():
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    tiempos = [t0 + timedelta(seconds=5 * i) for i in range(8)]
    lat0, paso = 42.6, 0.00004  # ~4,5 m cada 5 s
    lats = [lat0 + paso * i for i in range(8)]
    lons = [0.0] * 8
    lats[3] += 0.002  # pico de ~220 m
    assert geo.filtrar_saltos(lats, lons, tiempos, v_max=8) == [0, 1, 2, 4, 5, 6, 7]
    # Si el GPS se queda "lejos" muchos puntos seguidos, se acepta la nueva posición
    lats2 = [lat0, lat0] + [lat0 + 0.01] * 6
    # (descarta 2, 3 y 4; al cuarto seguido lo da por bueno)
    assert geo.filtrar_saltos(lats2, lons, tiempos, v_max=8, max_seguidos=3) == [0, 1, 5, 6, 7]


def test_remuestrear_interpola():
    filas = geo.remuestrear([0.0, 100.0], [[10.0, 20.0]], 25.0)
    assert [f[0] for f in filas] == [0, 25, 50, 75, 100]
    assert filas[2][1] == pytest.approx(15.0)


def test_desnivel_ignora_ruido():
    eles = [100, 101, 100, 101, 100, 110, 109, 110, 100]
    sube, baja = metricas.desnivel(eles, umbral=3)
    assert sube == pytest.approx(10)
    assert baja == pytest.approx(10)


def test_tiempo_movimiento_descarta_paradas():
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    tiempos = [t0 + timedelta(seconds=s) for s in (0, 10, 20, 620, 630)]
    acum = [0, 10, 20, 22, 32]          # 1 m/s, luego parada de 10 min con 2 m de deriva
    eles = [100] * 5
    mov = metricas.tiempo_movimiento(tiempos, acum, eles, v_min=0.3, v_min_vertical=0.05)
    assert mov == 30


def test_fc_media_ponderada_por_tiempo():
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    tiempos = [t0, t0 + timedelta(seconds=10), t0 + timedelta(seconds=40)]
    assert metricas.fc_media(tiempos, [100, 160, 150]) == pytest.approx(145)
