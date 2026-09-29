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
    up_to_date = current == builder.render()  # plain bool: pytest would otherwise diff two ~1 MB strings
    assert up_to_date, "web/data.json is stale: run `python scripts/build_web_data.py`"


def test_hemicycle_totals():
    from votimeter.data import load_landscape

    expected = {"eu": 720, "pt": 230, "fr": 577, "uk": 650, "de": 630, "nl": 150, "it": 400, "es": 350,
        "at": 183, "be": 150, "bg": 240, "hr": 151, "cy": 56, "cz": 200, "dk": 179, "ee": 101, "fi": 200, "gr": 300,
        "hu": 199, "ie": 174, "lv": 100, "lt": 141, "lu": 60, "mt": 79, "pl": 460, "ro": 331, "sk": 150, "si": 90, "se": 349}
    for landscape_id, total in expected.items():
        assert sum(seats for _, seats in load_landscape(landscape_id, "en").hemicycle) == total, landscape_id


def test_hemicycle_codes_are_parties_or_other():
    """Catches codes pandas would silently turn into NaN (e.g. a party called "NA")."""
    from votimeter.data import list_landscapes, load_landscape

    for landscape_id in list_landscapes():
        landscape = load_landscape(landscape_id, "en")
        for code, _ in landscape.hemicycle:
            assert isinstance(code, str), (landscape_id, code)
            assert code in landscape.party_codes or code.startswith(("Other", "NI")), (landscape_id, code)
