from datetime import datetime, timezone

from trekking.garmin_export import _emparejar


def test_empareja_por_hora_de_inicio():
    base = datetime(2025, 6, 14, 6, 0, tzinfo=timezone.utc).timestamp()
    acts = [(base, {"name": "A"}), (base + 86400, {"name": "B"})]
    assert _emparejar(datetime(2025, 6, 14, 6, 0, 5, tzinfo=timezone.utc), acts)["name"] == "A"
    assert _emparejar(datetime(2025, 6, 15, 5, 58, tzinfo=timezone.utc), acts)["name"] == "B"
    assert _emparejar(datetime(2025, 6, 14, 12, 0, tzinfo=timezone.utc), acts) is None
    assert _emparejar(None, acts) is None
