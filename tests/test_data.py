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
LANDSCAPES = list_landscapes()


def test_expected_languages_and_landscapes():
    assert {"en", "pt", "fr", "de", "it", "es"} <= set(LANGUAGES)
    assert {"eu", "pt", "fr", "uk", "de", "nl", "it", "es"} <= set(LANDSCAPES)


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
    texts = {
        lang: json.loads((DATA_DIR / "landscapes" / landscape_id / f"text_{lang}.json").read_text(encoding="utf-8"))
        for lang in LANGUAGES
    }
    reference = texts["en"]
    for lang, text in texts.items():
        assert set(text) == set(reference), lang
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
    assert {"pt", "fr", "uk", "de", "nl", "it", "es"} <= set(columns)
    reference = columns["pt"]
    for landscape_id, column in columns.items():
        assert column.equals(reference), f"Volt differs in {landscape_id}: run scripts/sync_volt.py"
