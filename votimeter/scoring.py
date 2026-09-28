"""Affinity and compass calculations. Answers are keyed by question id."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from votimeter.data import AXES

MAX_DISTANCE_PER_QUESTION = 4  # answers range from -2 to 2


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
    scores = {}
    for axis in AXES:
        axis_ids = questions.index[questions["axis"] == axis]
        values = answered.reindex(axis_ids).dropna()
        if values.empty:
            scores[axis] = 0.0
            continue
        weighted = (values * questions.loc[values.index, "multiplier"]).sum()
        scores[axis] = max(-1.0, min(1.0, weighted / (len(values) * 2.0)))
    return scores
