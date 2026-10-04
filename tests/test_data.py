import json

import pandas as pd
import pytest

from votimeter.data import (
    AXES,
    DATA_DIR,
    available_languages,
    list_landscapes,
    load_landscape,
    load_questions,
    load_ui,
)

LANGUAGES = available_languages()
COMPLETE_LANGUAGES = {"en", "pt", "fr", "de", "it", "es"}  # party profiles fully translated
LANDSCAPES = list_landscapes()


def test_expected_languages_and_landscapes():
    assert {"en", "pt", "fr", "de", "it", "es"} <= set(LANGUAGES)
    eu27 = {"at", "be", "bg", "hr", "cy", "cz", "dk", "ee", "fi", "fr", "de", "gr", "hu", "ie",
            "it", "lv", "lt", "lu", "mt", "nl", "pl", "pt", "ro", "sk", "si", "es", "se"}
    assert eu27 | {"eu", "uk"} <= set(LANDSCAPES)


@pytest.mark.parametrize("lang", LANGUAGES)
def test_questions_load_with_text(lang):
    questions = load_questions(lang)
    assert len(questions) == 60
    assert questions["text"].str.strip().ne("").all()
    assert set(questions["axis"]) == set(AXES)
    assert questions.groupby("axis").size().eq(20).all()


def test_question_ids_are_prefixed_by_axis():
    questions = load_questions("en")
    prefixes = {"economic": "ECO", "social": "SOC", "political": "POL"}
    for qid, axis in questions["axis"].items():
        assert qid.startswith(prefixes[axis])


@pytest.mark.parametrize("lang", LANGUAGES)
def test_ui_strings_have_same_keys(lang):
    reference = set(load_ui("en"))
    assert set(load_ui(lang)) == reference


def test_every_subaxis_has_pole_labels():
    ui = load_ui("en")
    for subaxis in load_questions("en")["subaxis"].unique():
        assert ui[f"sub_{subaxis}_low"] and ui[f"sub_{subaxis}_high"]


@pytest.mark.parametrize("landscape_id", LANDSCAPES)
@pytest.mark.parametrize("lang", LANGUAGES)
def test_landscapes_load(landscape_id, lang):
    landscape = load_landscape(landscape_id, lang)
    assert landscape.parties
    assert list(landscape.positions.columns) == landscape.party_codes
    assert len(landscape.positions) == 60
    for party in landscape.parties:
        assert party.details["name"]
        assert party.details["description"]


@pytest.mark.parametrize("landscape_id", LANDSCAPES)
def test_landscape_text_keys_match_across_languages(landscape_id):
    """Every language has a text file per landscape. The six original languages are complete;
    the others may leave out keys or party details, which then fall back to English."""
    folder = DATA_DIR / "landscapes" / landscape_id
    reference = json.loads((folder / "text_en.json").read_text(encoding="utf-8"))
    meta_keys = set(reference) - {"parties"}
    for lang in LANGUAGES:
        text = json.loads((folder / f"text_{lang}.json").read_text(encoding="utf-8"))
        assert set(text) <= set(reference), (lang, set(text) - set(reference))
        assert meta_keys <= set(text), (lang, meta_keys - set(text))  # landscape names and notes are always translated
        for code, details in text.get("parties", {}).items():
            assert code in reference["parties"], (lang, code)
            assert set(details) <= set(reference["parties"][code]), (lang, code)
        if lang in COMPLETE_LANGUAGES:
            assert set(text["parties"]) == set(reference["parties"]), lang


def test_portugal_positions_preserved_from_original_order():
    positions = pd.read_csv(DATA_DIR / "landscapes" / "pt" / "positions.csv")
    assert positions.columns[0] == "id"
    assert positions.loc[0, "id"] == "ECO01"
    assert positions.loc[0, "Chega"] == 2


def test_volt_has_the_same_positions_everywhere():
    """Volt shares one programme across countries (see scripts/sync_volt.py)."""
    columns = {
        landscape_id: load_landscape(landscape_id, "en").positions["Volt"]
        for landscape_id in LANDSCAPES
        if "Volt" in load_landscape(landscape_id, "en").party_codes
    }
    countries = set(LANDSCAPES) - {"eu"}
    assert countries <= set(columns), f"Volt missing in {sorted(countries - set(columns))}"
    reference = columns["pt"]
    for landscape_id, column in columns.items():
        assert column.equals(reference), f"Volt differs in {landscape_id}: run scripts/sync_volt.py"


@pytest.mark.parametrize("landscape_id", LANDSCAPES)
def test_no_two_parties_in_a_landscape_have_identical_answers(landscape_id):
    positions = load_landscape(landscape_id, "en").positions
    duplicated = positions.T.duplicated(keep=False)
    assert not duplicated.any(), f"identical answers: {positions.columns[duplicated].tolist()}"
