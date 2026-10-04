"""Loading and validation of the quiz data.

Layout of ``data/``:

- ``questions/questions.csv``       id, axis, subaxis, multiplier, short (language-neutral)
- ``questions/text_<lang>.csv``     id, text (one file per language)
- ``i18n/ui_<lang>.json``           interface strings (one file per language)
- ``landscapes/landscapes.csv``     ordered list of landscape ids
- ``landscapes/<id>/parties.csv``   code, color, url (language-neutral)
- ``landscapes/<id>/positions.csv`` id + one column per party code, values in -2..2
- ``landscapes/<id>/text_<lang>.json`` landscape strings and party details
- ``landscapes/<id>/hemicycle.csv`` code, seats, in seating order left to right
  (optional; codes that are not parties, e.g. ``NI``, are shown as unaffiliated)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

AXES = ("economic", "social", "political")
FALLBACK_LANGUAGE = "en"  # landscape texts missing a key or a party fall back to English
ANSWER_VALUES = (-2, -1, 0, 1, 2)


class DataError(ValueError):
    """Raised when a data file is missing or inconsistent."""


@dataclass(frozen=True)
class Party:
    code: str
    color: str
    url: str
    details: dict


@dataclass(frozen=True)
class Landscape:
    id: str
    text: dict
    parties: tuple[Party, ...]
    positions: pd.DataFrame  # index: question id, columns: party codes
    hemicycle: tuple[tuple[str, int], ...] = ()  # (code, seats), left to right

    @property
    def party_codes(self) -> list[str]:
        return [p.code for p in self.parties]


def available_languages(data_dir: Path = DATA_DIR) -> list[str]:
    """Languages that have both UI strings and question texts."""
    ui = {p.stem.removeprefix("ui_") for p in (data_dir / "i18n").glob("ui_*.json")}
    questions = {p.stem.removeprefix("text_") for p in (data_dir / "questions").glob("text_*.csv")}
    return sorted(ui & questions)


def load_ui(lang: str, data_dir: Path = DATA_DIR) -> dict:
    return _read_json(data_dir / "i18n" / f"ui_{lang}.json")


def load_questions(lang: str, data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """Question metadata joined with the texts for ``lang``, indexed by id, in file order."""
    meta = pd.read_csv(data_dir / "questions" / "questions.csv", dtype={"id": str})
    _require_columns(meta, ["id", "axis", "subaxis", "multiplier", "short"], "questions.csv")
    if meta["id"].duplicated().any():
        raise DataError(f"questions.csv: duplicate ids {meta.loc[meta['id'].duplicated(), 'id'].tolist()}")
    bad_axes = set(meta["axis"]) - set(AXES)
    if bad_axes:
        raise DataError(f"questions.csv: unknown axes {sorted(bad_axes)}")
    parents = meta.groupby("subaxis")["axis"].nunique()
    if (parents > 1).any():
        raise DataError(f"questions.csv: sub-axes spanning several axes {parents[parents > 1].index.tolist()}")
    if not meta["multiplier"].isin([1, -1]).all():
        raise DataError("questions.csv: 'multiplier' must be 1 or -1")
    if not meta["short"].isin([0, 1]).all():
        raise DataError("questions.csv: 'short' must be 0 or 1")

    text_file = data_dir / "questions" / f"text_{lang}.csv"
    texts = pd.read_csv(text_file, dtype={"id": str})
    _require_columns(texts, ["id", "text"], text_file.name)
    _require_same_ids(meta["id"], texts["id"], text_file.name)

    questions = meta.merge(texts, on="id", how="left", validate="one_to_one")
    return questions.set_index("id")


def subaxes(questions: pd.DataFrame) -> list[tuple[str, str]]:
    """(sub-axis, parent axis) pairs, grouped by axis in AXES order, then in file order."""
    pairs = list(dict.fromkeys(zip(questions["subaxis"], questions["axis"])))
    return sorted(pairs, key=lambda pair: AXES.index(pair[1]))


def list_landscapes(data_dir: Path = DATA_DIR) -> list[str]:
    return pd.read_csv(data_dir / "landscapes" / "landscapes.csv", dtype=str)["id"].tolist()


def load_landscape(landscape_id: str, lang: str, data_dir: Path = DATA_DIR) -> Landscape:
    folder = data_dir / "landscapes" / landscape_id
    question_ids = pd.read_csv(data_dir / "questions" / "questions.csv", dtype={"id": str})["id"]

    parties_df = pd.read_csv(folder / "parties.csv", dtype=str, keep_default_na=False)  # url may be blank
    _require_columns(parties_df, ["code", "color", "url"], f"{landscape_id}/parties.csv")
    codes = parties_df["code"].tolist()

    positions = pd.read_csv(folder / "positions.csv", dtype={"id": str})
    _require_columns(positions, ["id", *codes], f"{landscape_id}/positions.csv")
    _require_same_ids(question_ids, positions["id"], f"{landscape_id}/positions.csv")
    positions = positions.set_index("id")[codes]
    if not positions.isin(ANSWER_VALUES).all().all():
        raise DataError(f"{landscape_id}/positions.csv: values must be integers in -2..2")

    text = load_landscape_text(landscape_id, lang, data_dir)
    details = text.get("parties", {})
    missing = [c for c in codes if c not in details]
    if missing:
        raise DataError(f"{landscape_id}/text_{FALLBACK_LANGUAGE}.json: no details for {missing}")

    parties = tuple(
        Party(code=row.code, color=row.color, url=row.url, details=details[row.code])
        for row in parties_df.itertuples(index=False)
    )
    return Landscape(
        id=landscape_id,
        text=text,
        parties=parties,
        positions=positions.astype(int),
        hemicycle=_load_hemicycle(folder / "hemicycle.csv", landscape_id),
    )


def load_landscape_text(landscape_id: str, lang: str, data_dir: Path = DATA_DIR) -> dict:
    """Landscape strings in ``lang``, with English filling any missing key or party field."""
    folder = data_dir / "landscapes" / landscape_id
    text = _read_json(folder / f"text_{FALLBACK_LANGUAGE}.json")
    overlay_path = folder / f"text_{lang}.json"
    if lang == FALLBACK_LANGUAGE or not overlay_path.exists():
        return text
    overlay = _read_json(overlay_path)
    merged = {**text, **{k: v for k, v in overlay.items() if k != "parties"}}
    merged["parties"] = {
        code: {**details, **overlay.get("parties", {}).get(code, {})} for code, details in text["parties"].items()
    }
    return merged


def _load_hemicycle(path: Path, landscape_id: str) -> tuple[tuple[str, int], ...]:
    if not path.exists():
        return ()
    seats = pd.read_csv(path, dtype={"code": str}, keep_default_na=False)  # a code like "NA" is text
    _require_columns(seats, ["code", "seats"], f"{landscape_id}/hemicycle.csv")
    if seats["code"].duplicated().any() or not (seats["seats"] > 0).all():
        raise DataError(f"{landscape_id}/hemicycle.csv: codes must be unique and seats positive")
    return tuple((row.code, int(row.seats)) for row in seats.itertuples(index=False))


def _read_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _require_columns(df: pd.DataFrame, columns: list[str], name: str) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise DataError(f"{name}: missing columns {missing}")


def _require_same_ids(expected: pd.Series, actual: pd.Series, name: str) -> None:
    if actual.duplicated().any():
        raise DataError(f"{name}: duplicate ids {actual[actual.duplicated()].tolist()}")
    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    if missing or extra:
        raise DataError(f"{name}: missing ids {missing}, unknown ids {extra}")
