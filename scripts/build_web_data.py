"""Bundle data/ into web/data.json for the static website.

Run after editing anything in data/:

    python scripts/build_web_data.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from votimeter.data import (  # noqa: E402
    DATA_DIR,
    FALLBACK_LANGUAGE,
    available_languages,
    list_landscapes,
    load_landscape,
    load_questions,
    load_ui,
    subaxes,
)

OUTPUT = ROOT / "web" / "data.json"
DEFAULTS = {"lang": "en", "landscape": "eu"}


def build() -> dict:
    languages = available_languages()
    meta = load_questions(FALLBACK_LANGUAGE)
    question_ids = meta.index.tolist()

    bundle = {
        "defaults": DEFAULTS,
        "questions": [
            {"id": qid, "axis": row.axis, "subaxis": row.subaxis, "multiplier": int(row.multiplier), "short": bool(row.short)}
            for qid, row in meta.iterrows()
        ],
        "subaxes": [{"id": subaxis, "axis": axis} for subaxis, axis in subaxes(meta)],
        "languages": {},
        "landscapes": [],
    }
    for lang in languages:
        ui = load_ui(lang)
        bundle["languages"][lang] = {
            "name": ui["language_name"],
            "ui": ui,
            "questions": load_questions(lang)["text"].to_dict(),
        }
    for landscape_id in list_landscapes():
        landscape = load_landscape(landscape_id, FALLBACK_LANGUAGE)
        # English in full; other languages only as written, the site falls back to English per key.
        texts = {FALLBACK_LANGUAGE: landscape.text}
        for lang in languages:
            path = DATA_DIR / "landscapes" / landscape_id / f"text_{lang}.json"
            if lang != FALLBACK_LANGUAGE and path.exists():
                texts[lang] = json.loads(path.read_text(encoding="utf-8"))
        bundle["landscapes"].append({
            "id": landscape_id,
            "parties": [{"code": p.code, "color": p.color, "url": p.url} for p in landscape.parties],
            "positions": {code: landscape.positions.loc[question_ids, code].astype(int).tolist() for code in landscape.party_codes},
            "hemicycle": [list(seat) for seat in landscape.hemicycle],
            "text": texts,
        })
    return bundle


def render() -> str:
    return json.dumps(build(), ensure_ascii=False, separators=(",", ":")) + "\n"


if __name__ == "__main__":
    OUTPUT.write_text(render(), encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")
