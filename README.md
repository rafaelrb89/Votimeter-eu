# Votimeter EU

A quiz that places you on three political axes (economic, social, political) and measures your agreement with a set of parties. It is based on [paradigmapolitico2](https://github.com/rafaelrb89/paradigmapolitico2) (Votímetro).

- **Languages:** English, Português, Français, Deutsch, Italiano, Español
- **Party landscapes:** European Parliament groups (2024–2029 term), all 27 EU member states, and the United Kingdom

You can switch language and landscape at any time. Answers are stored by question ID, so switching keeps them. The selection is also saved in the URL (`?lang=pt&landscape=eu`), so you can share a link with a preset.

## Two front ends

| | Folder | What it is |
|---|---|---|
| **Website** | `web/` | Static HTML/CSS/JS. No server needed. Deployed to GitHub Pages. |
| **Streamlit app** | `Home.py` | The original app, now bilingual. |

Both read the same data in `data/`.

### Website

```bash
python scripts/build_web_data.py      # bundle data/ into web/data.json (after any data edit)
python -m http.server -d web 8000     # then open http://localhost:8000
```

`web/data.json` is generated. Rebuild it after editing anything in `data/`; the tests fail if it is stale.

**Publishing:** the `Deploy website` workflow publishes `web/` to GitHub Pages on every push to `main` that touches it. Enable it once under **Settings → Pages → Source: GitHub Actions**.

The website supports `?lang=pt&landscape=eu` in the URL. It remembers a visitor's answers in their browser, so they can resume an unfinished test. Keyboard: `1`–`5` answer, `S` skips, `←` goes back.

### Streamlit app

```bash
poetry install
poetry run python -m streamlit run Home.py   # run the app
poetry run pytest                            # validate data + scoring
```

The share buttons use `VOTIMETER_APP_URL` (environment variable) as the public URL of the app.

## Data layout

Everything the quiz shows comes from `data/`. The code has no hard-coded questions or parties.

```
data/
├── questions/
│   ├── questions.csv        # id, axis, multiplier, short   (language-neutral)
│   ├── text_en.csv          # id, text
│   └── text_pt.csv          # id, text
├── i18n/
│   ├── ui_en.json           # interface strings
│   └── ui_pt.json
└── landscapes/
    ├── landscapes.csv       # which landscapes exist, in sidebar order
    ├── eu/
    │   ├── parties.csv      # code, color, url               (language-neutral)
    │   ├── positions.csv    # id + one column per party code, values -2..2
    │   ├── text_en.json     # landscape strings + party details
    │   ├── text_pt.json
    │   └── hemicycle.csv    # code, seats, left to right (website chamber drawing)
    └── pt/  (same files)
```

- **Question IDs** have the form `ECO01`, `SOC01` or `POL01`. The `axis` column (`economic`, `social`, `political`) decides which compass axis a question counts towards. Question order no longer matters.
- **`multiplier`** is `1` when agreeing moves you right (economic), progressive (social) or liberal/globalist (political). It is `-1` when agreeing moves you the other way.
- **`short`** is `1` for questions included in the short test.
- **Positions** use the same scale as user answers: `-2` strongly disagree … `2` strongly agree.

### Adding a language

1. Add `data/i18n/ui_<lang>.json` with the same keys as `ui_en.json`.
2. Add `data/questions/text_<lang>.csv` with every question ID.
3. Add `text_<lang>.json` to every landscape folder.

A language shows up in the sidebar only when both its UI file and its question file exist. The tests check that the keys and IDs are complete.

### Adding a landscape

Create `data/landscapes/<id>/` with `parties.csv`, `positions.csv` and a `text_<lang>.json` for every language, then add `<id>` to `landscapes.csv`.

## About the positions

- **Portugal:** the positions are unchanged from the original app.
- **Volt** is listed in every country with **identical positions**, because it runs on one pan-European programme. The reference is Volt's column in `data/landscapes/pt/positions.csv`. After editing it, run `python scripts/sync_volt.py` to copy it to every country; a test fails if the copies differ. The European Parliament view stays by group, where Volt sits in Greens/EFA.
- **All countries except Portugal:** first estimates. Each party starts from the column of its European Parliament group, or of a sister party (Volt Nederland from Volt Portugal), and is then adjusted where it differs from that group. For example, the RN is more protectionist than PfE, the PCF is pro-nuclear, the FDP opposes common EU debt, BSW is left-wing on the economy but restrictive on migration, and M5S was scored from scratch. **All of these need the same review as the EU groups.**
- **Seat counts** (`hemicycle.csv`) are approximate, and seats not held by a listed party are shown in grey as "Other". Snapshots: France by parliamentary group, July 2024; UK, July 2024; Germany, February 2025; Netherlands, October 2025; Italy, September 2022; Spain, July 2023, with regional parties grouped as "Other". Other countries use the latest result available when this data was built. For Hungary, Slovenia, Cyprus, Sweden and Bulgaria, a newer election is not yet reflected; the chamber says so, and parties that are strong in polls, such as Tisza in Hungary, are included without seats.
- **Websites and links:** `url` in `parties.csv` may be blank when the official site was not confirmed. The site then omits the "Official website" link. Wikipedia links for the EU27 extension use Wikipedia search, so they never point to a wrong article.
- **European Parliament groups:** these positions are a first estimate. Each group started from its Portuguese member parties where it has them (EPP↔AD, S&D↔PS, Renew↔IL, Greens/EFA↔Livre/Volt, The Left↔BE/CDU, PfE↔Chega), then was adjusted to the group's overall line: its manifestos, its main national delegations and its voting record. ECR and ESN have no Portuguese members and were estimated directly. **Please review them before a public launch**, especially on points where groups are split internally, for example The Left on Ukraine, S&D and Greens on prostitution, and EPP on common EU debt.
