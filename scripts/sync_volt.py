"""Copy Volt's positions from the reference landscape to every landscape that lists Volt.

Volt runs on one pan-European programme, so it has the same answers in every
country. Edit Volt's column in data/landscapes/pt/positions.csv, then run:

    python scripts/sync_volt.py
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent / "data" / "landscapes"
REFERENCE = "pt"
PARTY = "Volt"


def main() -> None:
    reference = pd.read_csv(ROOT / REFERENCE / "positions.csv", dtype={"id": str}).set_index("id")[PARTY]
    for folder in sorted(p for p in ROOT.iterdir() if p.is_dir()):
        codes = pd.read_csv(folder / "parties.csv", dtype=str)["code"].tolist()
        if PARTY not in codes:
            continue
        positions = pd.read_csv(folder / "positions.csv", dtype={"id": str}).set_index("id")
        positions[PARTY] = reference.reindex(positions.index)
        positions[codes].to_csv(folder / "positions.csv")
        print(f"{folder.name}: synced")


if __name__ == "__main__":
    main()
