import os
import urllib.parse
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from votimeter.data import ANSWER_VALUES, available_languages, list_landscapes, load_landscape, load_questions, load_ui, subaxes
from votimeter.scoring import affinity, compass_scores, subaxis_scores

# -------------------------------------------------------------------------
# Page Configuration
# -------------------------------------------------------------------------
st.set_page_config(page_title="Votimeter", page_icon="⚛️", layout="wide")

APP_URL = os.environ.get("VOTIMETER_APP_URL", "https://YOUR_APP_DEPLOYED_URL_HERE")
CONTACT_EMAIL = "ribeirobarbosarafael@gmail.com"
DEFAULT_LANGUAGE = "en"
DEFAULT_LANDSCAPE = "eu"

st.markdown(f"<style>{(Path(__file__).parent / 'assets' / 'style.css').read_text()}</style>", unsafe_allow_html=True)

# -------------------------------------------------------------------------
# Language & landscape selection (persisted in the URL: ?lang=en&landscape=eu)
# -------------------------------------------------------------------------
# English first, then the other languages by their own name.
LANGUAGES = sorted(available_languages(), key=lambda code: (code != DEFAULT_LANGUAGE, load_ui(code)["language_name"]))
LANDSCAPES = list_landscapes()


def _initial_choice(param, options, default):
    value = st.query_params.get(param, default)
    return value if value in options else default


if "lang" not in st.session_state:
    st.session_state.lang = _initial_choice("lang", LANGUAGES, DEFAULT_LANGUAGE)
if "landscape" not in st.session_state:
    st.session_state.landscape = _initial_choice("landscape", LANDSCAPES, DEFAULT_LANDSCAPE)


@st.cache_data
def get_ui(lang):
    return load_ui(lang)


@st.cache_data
def get_questions(lang):
    return load_questions(lang)


@st.cache_data
def get_landscape(landscape_id, lang):
    return load_landscape(landscape_id, lang)


@st.cache_data
def landscape_names(lang):
    return {lid: load_landscape(lid, lang).text["short_name"] for lid in LANDSCAPES}


with st.sidebar:
    st.selectbox("🌐 " + get_ui(st.session_state.lang)["language_label"], LANGUAGES, key="lang", format_func=lambda code: get_ui(code)["language_name"])
    t = get_ui(st.session_state.lang)
    names = landscape_names(st.session_state.lang)
    st.selectbox(t["landscape_label"], LANDSCAPES, key="landscape", format_func=names.get)
st.query_params["lang"] = st.session_state.lang
st.query_params["landscape"] = st.session_state.landscape

questions = get_questions(st.session_state.lang)
landscape = get_landscape(st.session_state.landscape, st.session_state.lang)
lt = landscape.text  # landscape-specific strings

all_ids = questions.index.tolist()
short_ids = questions.index[questions["short"] == 1].tolist()
SUBAXES = subaxes(questions)
can_run_short_test = bool(short_ids)

if "mode" not in st.session_state:
    st.session_state.mode = "intro"
if "idx" not in st.session_state:
    st.session_state.idx = -1
if "answers" not in st.session_state:
    st.session_state.answers = {}  # question id -> answer value
if "sequence" not in st.session_state:
    st.session_state.sequence = []  # question ids in the order they are asked


# -------------------------------------------------------------------------
# Helper Functions
# -------------------------------------------------------------------------
def start_test(sequence, mode):
    st.session_state.mode = mode
    st.session_state.sequence = sequence
    st.session_state.idx = 0
    st.session_state.answers = {}
    st.rerun()


def restart():
    st.session_state.mode = "intro"
    st.session_state.idx = -1
    st.session_state.answers = {}
    st.session_state.sequence = []
    st.rerun()


def show_intro():
    """Shows the intro page with test length choice."""
    st.title(t["app_title"])
    st.write(t["intro_welcome"].format(landscape_intro=lt["intro"]))
    st.write("")
    st.write(t["intro_method"])
    st.write("")
    st.write(t["intro_choice"].format(n_short=len(short_ids), n_full=len(all_ids)))
    st.caption(t["intro_subaxes_note"].format(n=len(SUBAXES)))
    st.caption(t["intro_landscape_hint"])
    st.write("---")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<div class='start-btn'>", unsafe_allow_html=True)
        if st.button(t["start_short"].format(n=len(short_ids)), key="start_short", disabled=not can_run_short_test):
            start_test(short_ids, "short")
        st.markdown("</div>", unsafe_allow_html=True)
        if not can_run_short_test:
            st.caption(t["option_unavailable"])
    with col2:
        st.markdown("<div class='start-btn'>", unsafe_allow_html=True)
        if st.button(t["start_full"].format(n=len(all_ids)), key="start_full"):
            start_test(all_ids, "full")
        st.markdown("</div>", unsafe_allow_html=True)
    st.write("---")
    st.markdown(f"**{lt['included_label']}:** " + " | ".join(f"[{p.code}]({p.url or p.details.get('wiki_url', '#')})" for p in landscape.parties))
    st.caption(lt["inclusion_note"])
    st.caption(t["statements_note"])
    st.caption("")
    st.caption(t["axis_economic_desc"])
    st.caption(t["axis_social_desc"])
    st.caption(t["axis_political_desc"])
    st.caption(t["subaxes_explainer"].format(n=len(SUBAXES)))
    for axis in ("economic", "social", "political"):
        poles = [f"{t[f'sub_{sid}_low']} – {t[f'sub_{sid}_high']}" for sid, parent in SUBAXES if parent == axis]
        st.caption(f"**{t['axis_' + axis]}:** " + " · ".join(poles))
    st.caption("")
    st.caption(t["positions_note"].format(contact=CONTACT_EMAIL))


def show_question():
    """Shows the current question, answer buttons, skip, and back buttons."""
    sequence = st.session_state.sequence
    current_idx = st.session_state.idx
    if not (0 <= current_idx < len(sequence)):
        restart()
        return
    qid = sequence[current_idx]
    st.header(t["question_header"].format(i=current_idx + 1, n=len(sequence)))
    st.subheader(questions.at[qid, "text"])
    st.write(t["question_prompt"])

    moved = None
    cols = st.columns(len(ANSWER_VALUES))
    for i, value in enumerate(ANSWER_VALUES):
        with cols[i]:
            if st.button(t[f"answer_{value}"], key=f"{qid}_opt_{value}"):
                st.session_state.answers[qid] = value
                moved = "forward"

    st.markdown("<div class='skip-btn-wrapper'>", unsafe_allow_html=True)
    if st.button(t["skip"], key=f"{qid}_skip", use_container_width=True, type="tertiary"):
        st.session_state.answers.pop(qid, None)
        moved = "forward"
    st.markdown("</div>", unsafe_allow_html=True)

    if current_idx > 0:
        st.markdown("<div class='recuar-btn-wrapper'>", unsafe_allow_html=True)
        if st.button(t["back"], key=f"{qid}_back", use_container_width=True, type="tertiary"):
            st.session_state.idx -= 1
            moved = "back"
        st.markdown("</div>", unsafe_allow_html=True)

    if moved == "forward":
        st.session_state.idx += 1
        if st.session_state.idx == len(sequence):
            st.session_state.mode = "midpoint" if st.session_state.mode == "short" else "results"
        st.rerun()
    elif moved == "back":
        st.rerun()


def show_midpoint_choice():
    """Displays screen after short test, asking user to continue or see results."""
    st.header(t["midpoint_header"].format(n=len(short_ids)))
    st.write(t["midpoint_text"])
    st.info(t["midpoint_subaxes_note"].format(n=len(SUBAXES)))
    st.write("---")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<div class='midpoint-btn'>", unsafe_allow_html=True)
        if st.button(t["see_results"].format(n=len(short_ids)), key="results_short"):
            st.session_state.mode = "results"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    with col2:
        st.markdown("<div class='midpoint-btn'>", unsafe_allow_html=True)
        if st.button(t["continue_test"].format(n=len(all_ids)), key="continue_full"):
            # Keep the short answers and ask the remaining questions in file order.
            st.session_state.sequence = short_ids + [q for q in all_ids if q not in short_ids]
            st.session_state.idx = len(short_ids)
            st.session_state.mode = "full"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


def show_subaxes(answers):
    """One row per sub-axis, grouped by main axis: your score and the parties' for reference."""
    st.write(t["subaxes_caption"])
    labels = {sid: f"{t[f'sub_{sid}_low']} – {t[f'sub_{sid}_high']}" for sid, _ in SUBAXES}
    you = subaxis_scores(answers, questions)
    rows = [{"who": t["you"], "subaxis": labels[sid], "score": score, "you": True} for sid, score in you.items() if score is not None]
    for code in landscape.party_codes:
        party = subaxis_scores(landscape.positions[code], questions)
        rows += [{"who": code, "subaxis": labels[sid], "score": party[sid], "you": False} for sid in you if you[sid] is not None]
    for sid, score in you.items():
        if score is None:
            st.caption(f"{labels[sid]}: {t['subaxis_insufficient']}")
    if not rows:
        return
    df = pd.DataFrame(rows)
    colors = {p.code: p.color for p in landscape.parties} | {t["you"]: "#E3B23C"}
    domain = list(colors)
    order = [labels[sid] for sid, _ in SUBAXES]
    base = alt.Chart(df).encode(
        x=alt.X("score:Q", scale=alt.Scale(domain=[-1, 1]), axis=alt.Axis(title=None, format=".1f", grid=False)),
        y=alt.Y("subaxis:N", sort=order, title=None, axis=alt.Axis(labelLimit=320)),
        color=alt.Color("who:N", scale=alt.Scale(domain=domain, range=[colors[c] for c in domain]), legend=None),
        tooltip=["who", "subaxis", alt.Tooltip("score:Q", format="+.2f")],
    )
    parties = base.transform_filter(~alt.datum.you).mark_circle(size=70, opacity=0.55)
    marker = base.transform_filter(alt.datum.you).mark_point(shape="triangle-up", size=220, filled=True, opacity=1)
    zero = alt.Chart(pd.DataFrame({"zero": [0]})).mark_rule(strokeDash=[3, 3], color="grey", size=0.5).encode(x="zero:Q")
    st.altair_chart((zero + parties + marker).properties(background="transparent", height=36 * len(order)), use_container_width=True)


def show_results():
    """Shows the results page: affinity chart, compass chart, party info, share buttons."""
    st.success(t["test_done"])
    answers = st.session_state.answers
    n_answered = len(answers)

    if not answers:
        st.warning(t["no_answers"])
        if st.button(t["restart"]):
            restart()
        return

    sequence = st.session_state.sequence
    if len(sequence) == len(short_ids) < len(all_ids) and n_answered == len(short_ids):
        st.info(t["results_short"].format(n=n_answered))
    elif n_answered == len(all_ids):
        st.info(t["results_full"].format(n=n_answered))
    else:
        st.info(t["results_partial"].format(n=n_answered))

    # --- 1. Affinity ---
    st.header(lt["results_title"])
    party_col, affinity_col = t["party_label"], t["affinity_label"]
    affinity_df = affinity(answers, landscape.positions).rename_axis(party_col).reset_index(name=affinity_col)
    colors = {p.code: p.color for p in landscape.parties}
    color_domain = affinity_df[party_col].tolist()
    affinity_chart = alt.Chart(affinity_df).mark_bar().encode(
        x=alt.X(affinity_col, axis=alt.Axis(format="%", title=t["affinity_axis"], grid=False)),
        y=alt.Y(party_col, sort="-x", title=party_col, axis=alt.Axis(labelLimit=200)),
        color=alt.Color(party_col, scale=alt.Scale(domain=color_domain, range=[colors[p] for p in color_domain]), legend=None),
        tooltip=[party_col, alt.Tooltip(affinity_col, format=".1%")],
    ).properties(background="transparent")
    st.altair_chart(affinity_chart, use_container_width=True)
    st.write(t["affinity_explainer"])
    st.caption(t["affinity_note"])
    st.write("---")

    # --- 2. Political Compass ---
    st.header(t["compass_title"])
    entity, econ, social, political = t["party_label"], t["axis_economic"], t["axis_social"], t["axis_political"]
    compass_rows = [{"id": "__you__", entity: t["you"], **compass_scores(answers, questions)}]
    for code in landscape.party_codes:
        compass_rows.append({"id": code, entity: code, **compass_scores(landscape.positions[code], questions)})
    compass_df = pd.DataFrame(compass_rows).rename(columns={"economic": econ, "social": social, "political": political})

    if not compass_df.empty:
        origin = pd.DataFrame({"zero": [0]})
        vline = alt.Chart(origin).mark_rule(strokeDash=[3, 3], color="grey", size=0.5).encode(x="zero:Q")
        hline = alt.Chart(origin).mark_rule(strokeDash=[3, 3], color="grey", size=0.5).encode(y="zero:Q")
        base = alt.Chart(compass_df).encode(
            x=alt.X(econ, scale=alt.Scale(domain=[-1.1, 1.1]), axis=alt.Axis(title=t["axis_economic_title"], grid=False, format=".1f")),
            y=alt.Y(social, scale=alt.Scale(domain=[-1.1, 1.1]), axis=alt.Axis(title=t["axis_social_title"], grid=False, format=".1f")),
        )
        color_scale = alt.Scale(domain=[-1, 0, 1], range=["#FF0000", "#808080", "#FFFF00"])
        points = base.mark_point(size=120, filled=True, opacity=0.9).encode(
            color=alt.Color(political, scale=color_scale, legend=alt.Legend(title=political, orient="top", titleOrient="left", gradientLength=200, format=".1f")),
            tooltip=[entity, alt.Tooltip(econ, format=".2f"), alt.Tooltip(social, format=".2f"), alt.Tooltip(political, format=".2f", title=t["axis_political_tooltip"])],
            shape=alt.condition(alt.datum.id == "__you__", alt.value("triangle"), alt.value("circle")),
        )
        text = base.mark_text(align="left", baseline="middle", dx=9, fontSize=12, fontWeight="bold").encode(text=entity, color=alt.value("#FFFFFF"))
        st.altair_chart((vline + hline + points + text).properties(background="transparent").interactive(), use_container_width=True)
        st.write(t["compass_explainer"])
        st.caption(t["compass_note"])
    else:
        st.warning(t["compass_error"])
    st.write("---")

    # --- 3. Detailed profile (full test only: the short test has 2 statements per sub-axis) ---
    st.header(t["subaxes_title"])
    if len(sequence) == len(all_ids):
        show_subaxes(answers)
    else:
        st.info(t["subaxes_locked"].format(n=len(SUBAXES), m=len(all_ids)))
    st.write("---")

    # --- 4. Party details ---
    st.subheader(lt["details_title"])
    st.caption(t["details_disclaimer"])
    na = t["not_available"]
    for party in sorted(landscape.parties, key=lambda p: p.code):
        d = party.details
        with st.expander(party.code):
            st.markdown(f"**{lt['entity_label']}:** {d.get('name', na)}")
            st.markdown(f"**{lt['leader_label']}:** {d.get('leader', na)}")
            st.markdown(f"**{t['founded_label']}:** {d.get('founded', na)}")
            st.markdown(f"**{t['spectrum_label']}:** {d.get('spectrum', na)}")
            st.markdown(f"**{t['ideologies_label']}:** {d.get('ideologies', na)}")
            st.markdown(f"**{t['priorities_label']}:** {d.get('priorities', na)}")
            st.markdown(f"**{t['description_label']}:** {d.get('description', na)}")
            st.markdown(f"**{t['links_label']}:**")
            if party.url:
                st.markdown(f"- [{t['official_site']}]({party.url})")
            if d.get("program_url"):
                st.markdown(f"- [{t['program_link']}]({d['program_url']})")
            if d.get("wiki_url"):
                st.markdown(f"- [{t['wiki_link']}]({d['wiki_url']})")

    # --- 5. Share ---
    st.write("---")
    st.subheader(t["share_title"])
    top_party = affinity_df.iloc[0][party_col] if not affinity_df.empty else t["none"]
    top_affinity = affinity_df.iloc[0][affinity_col] if not affinity_df.empty else 0
    share_text = t["share_text"].format(party=top_party, affinity=f"{top_affinity:.0%}")
    share_url = f"{APP_URL}?{urllib.parse.urlencode({'lang': st.session_state.lang, 'landscape': landscape.id})}"
    share_text_encoded = urllib.parse.quote_plus(f"{share_text} {share_url}")
    share_url_encoded = urllib.parse.quote_plus(share_url)
    links = {
        "facebook": ("Facebook", f"https://www.facebook.com/sharer/sharer.php?u={share_url_encoded}"),
        "x": ("X (Twitter)", f"https://twitter.com/intent/tweet?url={share_url_encoded}&text={urllib.parse.quote_plus(share_text)}&hashtags={lt['hashtags']}"),
        "whatsapp": ("WhatsApp", f"https://wa.me/?text={share_text_encoded}"),
        "email": ("Email", f"mailto:?subject={urllib.parse.quote_plus(t['share_email_subject'])}&body={share_text_encoded}"),
    }
    st.markdown("<div class='share-button-container'>", unsafe_allow_html=True)
    for cls, (label, url) in links.items():
        st.markdown(f'<a href="{url}" target="_blank" class="share-btn share-btn-{cls}">{label}</a>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.write("---")
    st.markdown("<div class='restart-btn-wrapper'>", unsafe_allow_html=True)
    if st.button(t["restart"], use_container_width=True, key="restart_test_results", type="tertiary"):
        restart()
    st.markdown("</div>", unsafe_allow_html=True)


# -------------------------------------------------------------------------
# Main Application Flow
# -------------------------------------------------------------------------
mode = st.session_state.mode
if mode == "intro":
    show_intro()
elif mode in ("short", "full"):
    show_question()
elif mode == "midpoint":
    show_midpoint_choice()
elif mode == "results":
    show_results()
else:
    st.error(t["invalid_state"])
    restart()
