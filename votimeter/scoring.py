"""Affinity and compass calculations. Answers are keyed by question id."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from votimeter.data import AXES, subaxes

MAX_DISTANCE_PER_QUESTION = 4  # answers range from -2 to 2
MAX_SKIPPED_PER_SUBAXIS = 2  # beyond this a sub-axis score is not shown


def affinity(answers: Mapping[str, int], positions: pd.DataFrame) -> pd.Series:
    """Share of agreement (0..1) with each party, sorted descending.

    One minus the sum of absolute differences over the answered questions,
    normalised by the maximum possible distance.
    """
    if not answers:
        return pd.Series(dtype=float)
    user = pd.Series(answers, dtype=float)
    party_answers = positions.loc[user.index]
    distances = party_answers.sub(user, axis=0).abs().sum()
    max_distance = MAX_DISTANCE_PER_QUESTION * len(user)
    return (1 - distances / max_distance).clip(0.0, 1.0).sort_values(ascending=False)


def compass_scores(answers: Mapping[str, int] | pd.Series, questions: pd.DataFrame) -> dict[str, float]:
    """Score (-1..1) on each axis, using each question's axis and multiplier.

    Unanswered questions are ignored; an axis with no answers scores 0.
    """
    answered = pd.Series(answers, dtype=float).dropna()
    return {axis: _score(answered, questions, questions.index[questions["axis"] == axis]) or 0.0 for axis in AXES}


def subaxis_scores(answers: Mapping[str, int] | pd.Series, questions: pd.DataFrame) -> dict[str, float | None]:
    """Score (-1..1) on each sub-axis, or None when more than MAX_SKIPPED_PER_SUBAXIS of its questions are unanswered."""
    answered = pd.Series(answers, dtype=float).dropna()
    scores = {}
    for subaxis, _ in subaxes(questions):
        ids = questions.index[questions["subaxis"] == subaxis]
        enough = answered.index.isin(ids).sum() >= len(ids) - MAX_SKIPPED_PER_SUBAXIS
        scores[subaxis] = _score(answered, questions, ids) if enough else None
    return scores


def _score(answered: pd.Series, questions: pd.DataFrame, ids: pd.Index) -> float | None:
    values = answered.reindex(ids).dropna()
    if values.empty:
        return None
    weighted = (values * questions.loc[values.index, "multiplier"]).sum()
    return max(-1.0, min(1.0, weighted / (len(values) * 2.0)))
