import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_builder():
    spec = importlib.util.spec_from_file_location("build_web_data", ROOT / "scripts" / "build_web_data.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_web_data_is_up_to_date():
    builder = _load_builder()
    current = (ROOT / "web" / "data.json").read_text(encoding="utf-8")
    assert current == builder.render(), "web/data.json is stale: run `python scripts/build_web_data.py`"


def test_hemicycle_totals():
    from votimeter.data import load_landscape

    assert sum(seats for _, seats in load_landscape("eu", "en").hemicycle) == 720
    assert sum(seats for _, seats in load_landscape("pt", "en").hemicycle) == 230
