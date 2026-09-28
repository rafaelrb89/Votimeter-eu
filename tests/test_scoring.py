import pandas as pd
import pytest

from votimeter.data import load_questions
from votimeter.scoring import affinity, compass_scores


@pytest.fixture
def questions():
    return pd.DataFrame(
        {"axis": ["economic", "economic", "social", "political"], "multiplier": [1, -1, 1, -1]},
        index=["ECO01", "ECO02", "SOC01", "POL01"],
    )


def test_affinity_identical_answers_is_full_agreement():
    positions = pd.DataFrame({"A": [2, -1], "B": [-2, 1]}, index=["Q1", "Q2"])
    result = affinity({"Q1": 2, "Q2": -1}, positions)
    assert result["A"] == 1.0
    assert result["B"] == pytest.approx(1 - (4 + 2) / 8)
    assert list(result.index) == ["A", "B"]


def test_affinity_only_uses_answered_questions():
    positions = pd.DataFrame({"A": [2, -2]}, index=["Q1", "Q2"])
    assert affinity({"Q1": 2}, positions)["A"] == 1.0


def test_affinity_empty():
    assert affinity({}, pd.DataFrame({"A": [0]}, index=["Q1"])).empty


def test_compass_uses_axis_column_and_multiplier(questions):
    scores = compass_scores({"ECO01": 2, "ECO02": -2, "SOC01": -1, "POL01": 2}, questions)
    assert scores == {"economic": 1.0, "social": -0.5, "political": -1.0}


def test_compass_unanswered_axis_is_zero(questions):
    assert compass_scores({"ECO01": 1}, questions) == {"economic": 0.5, "social": 0.0, "political": 0.0}


def test_compass_ignores_nan(questions):
    series = pd.Series({"ECO01": 2, "ECO02": None, "SOC01": None, "POL01": None})
    assert compass_scores(series, questions)["economic"] == 1.0


def test_compass_matches_original_positional_logic():
    """With the original file order, the axis column reproduces the old 20/20/20 slicing."""
    original = pd.read_csv("data/landscapes/pt/positions.csv").set_index("id")
    questions = load_questions("pt")
    for party in original.columns:
        answers = original[party]
        expected = {}
        for axis, block in zip(("economic", "social", "political"), (slice(0, 20), slice(20, 40), slice(40, 60))):
            values = answers.iloc[block]
            mult = questions["multiplier"].iloc[block]
            expected[axis] = max(-1.0, min(1.0, (values * mult).sum() / (len(values) * 2.0)))
        assert compass_scores(answers, questions) == pytest.approx(expected)
