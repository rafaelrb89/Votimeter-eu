/* Votimeter — static front end. Reads data.json (built from data/ by scripts/build_web_data.py). */
(function () {
  "use strict";

  const STORAGE_KEY = "votimeter:v1";
  const VALUES = [-2, -1, 0, 1, 2];
  const AXES = ["economic", "social", "political"];
  const AXIS_PREFIX = { economic: "ECO", social: "SOC", political: "POL" };
  const AXIS_ENDS = { economic: ["web_left", "web_right"], social: ["web_conservative", "web_progressive"], political: ["web_authoritarian", "web_liberal"] };
  const UNAFFILIATED_COLOR = "#9AA1B5";
  const SVG_NS = "http://www.w3.org/2000/svg";

  let DATA = null;
  let state = {
    lang: "en",
    landscape: "eu",
    mode: "intro", // intro | quiz | midpoint | results
    kind: "full", // short | full
    sequence: [],
    idx: 0,
    answers: {},
  };
  let resumable = false;

  const view = document.getElementById("view");
  const footer = document.getElementById("footer");

  // ------------------------------------------------------------------ utils
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const md = (s) => esc(s).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").replace(/\n/g, "<br>");
  const fill = (s, vars) => String(s).replace(/\{(\w+)\}/g, (m, k) => (vars && k in vars ? vars[k] : m));
  const t = (key, vars) => fill(DATA.languages[state.lang].ui[key] ?? key, vars);
  const pct = (x) => `${Math.round(x * 100)}%`;
  const signed = (x) => (x > 0 ? "+" : x < 0 ? "−" : "") + Math.abs(x).toFixed(2);
  const landscape = () => DATA.landscapes.find((l) => l.id === state.landscape);
  // Landscape texts: the chosen language where written, English otherwise.
  const textOf = (l, key) => ((l.text[state.lang] || {})[key] ?? l.text.en[key]);
  const lt = (key, vars) => fill(textOf(landscape(), key) ?? key, vars);
  const partyInfo = (code) => ({ ...(landscape().text.en.parties[code] || {}), ...(((landscape().text[state.lang] || {}).parties || {})[code] || {}) });
  const partyColor = (code) => (landscape().parties.find((p) => p.code === code) || {}).color || UNAFFILIATED_COLOR;
  const questionText = (id) => DATA.languages[state.lang].questions[id];
  const allIds = () => DATA.questions.map((q) => q.id);
  const shortIds = () => DATA.questions.filter((q) => q.short).map((q) => q.id);
  const qIndex = {};

  function stripLabel(desc) {
    // "**Economic Axis**: Measures ..." -> "Measures ..."
    const i = desc.indexOf(":");
    return i >= 0 ? desc.slice(i + 1).trim() : desc;
  }

  function svg(tag, attrs, parent) {
    const el = document.createElementNS(SVG_NS, tag);
    for (const [k, v] of Object.entries(attrs || {})) el.setAttribute(k, v);
    if (parent) parent.appendChild(el);
    return el;
  }

  // ---------------------------------------------------------------- storage
  function save() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (e) { /* storage unavailable: nothing to do */ }
  }

  function restore() {
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
      if (saved && typeof saved === "object") return saved;
    } catch (e) { /* ignore */ }
    return null;
  }

  function readUrl() {
    try {
      const params = new URLSearchParams(location.search);
      return { lang: params.get("lang"), landscape: params.get("landscape") };
    } catch (e) {
      return {};
    }
  }

  function writeUrl() {
    try {
      const url = new URL(location.href);
      url.searchParams.set("lang", state.lang);
      url.searchParams.set("landscape", state.landscape);
      history.replaceState(null, "", url);
    } catch (e) { /* sandboxed: ignore */ }
  }

  // ---------------------------------------------------------------- scoring
  function affinity(answers) {
    const ids = Object.keys(answers);
    if (!ids.length) return [];
    const L = landscape();
    return L.parties
      .map((p) => {
        const pos = L.positions[p.code];
        const dist = ids.reduce((sum, id) => sum + Math.abs(pos[qIndex[id]] - answers[id]), 0);
        return { code: p.code, score: Math.min(1, Math.max(0, 1 - dist / (4 * ids.length))) };
      })
      .sort((a, b) => b.score - a.score);
  }

  function compass(valueOf) {
    const scores = {};
    for (const axis of AXES) {
      let sum = 0;
      let n = 0;
      for (const q of DATA.questions) {
        if (q.axis !== axis) continue;
        const v = valueOf(q.id);
        if (v === undefined || v === null) continue;
        sum += v * q.multiplier;
        n += 1;
      }
      scores[axis] = n ? Math.max(-1, Math.min(1, sum / (2 * n))) : 0;
    }
    return scores;
  }
  const MAX_SKIPPED_PER_SUBAXIS = 2; // beyond this a sub-axis score is not shown
  function subaxisScores(valueOf) {
    const scores = {};
    for (const sub of DATA.subaxes) {
      const qs = DATA.questions.filter((q) => q.subaxis === sub.id);
      let sum = 0;
      let n = 0;
      for (const q of qs) {
        const v = valueOf(q.id);
        if (v === undefined || v === null) continue;
        sum += v * q.multiplier;
        n += 1;
      }
      scores[sub.id] = n && n >= qs.length - MAX_SKIPPED_PER_SUBAXIS ? Math.max(-1, Math.min(1, sum / (2 * n))) : null;
    }
    return scores;
  }
  const isFullTest = () => state.kind === "full" && state.sequence.length === allIds().length;
  const userCompass = () => compass((id) => state.answers[id]);
  const partyCompass = (code) => compass((id) => landscape().positions[code][qIndex[id]]);

  // -------------------------------------------------------------- hemicycle
  function seatLayout(total) {
    const rows = Math.max(4, Math.round(Math.sqrt(total / 5.2)));
    const r0 = 0.38;
    const radii = Array.from({ length: rows }, (_, i) => r0 + ((1 - r0) * i) / (rows - 1));
    const rsum = radii.reduce((a, b) => a + b, 0);
    const counts = radii.map((r) => Math.round((total * r) / rsum));
    counts[rows - 1] += total - counts.reduce((a, b) => a + b, 0);
    const seats = [];
    radii.forEach((r, i) => {
      const n = counts[i];
      for (let j = 0; j < n; j++) {
        const a = n === 1 ? Math.PI / 2 : Math.PI - (Math.PI * j) / (n - 1);
        seats.push({ x: r * Math.cos(a), y: -r * Math.sin(a), a, r });
      }
    });
    seats.sort((p, q) => q.a - p.a || p.r - q.r);
    const size = Math.min(((1 - r0) / (rows - 1)) * 0.42, (Math.PI * r0) / Math.max(1, counts[0] - 1) * 0.42);
    return { seats, size };
  }

  function drawHemicycle(container, options) {
    const L = landscape();
    const total = L.hemicycle.reduce((s, [, n]) => s + n, 0);
    if (!total) return null;
    const { seats, size } = seatLayout(total);
    const root = svg("svg", { viewBox: `${-1 - size} ${-1 - size} ${2 + 2 * size} ${1 + 2 * size + 0.02}`, role: "img", "aria-label": lt("hemicycle_note") });
    let k = 0;
    const byParty = {};
    for (const [code, n] of L.hemicycle) {
      byParty[code] = [];
      for (let i = 0; i < n; i++, k++) {
        const s = seats[k];
        const dimmed = options && options.focus && options.focus !== code;
        const c = svg("circle", { cx: s.x.toFixed(4), cy: s.y.toFixed(4), r: size.toFixed(4), class: "seat" }, root);
        c.style.fill = dimmed ? "var(--dim-seat)" : partyColor(code);
        if (!(options && options.static)) c.style.animation = `rise .5s ease-out ${(k / total) * 0.5}s both`;
        byParty[code].push(s);
      }
    }
    if (options && options.focus && byParty[options.focus] && byParty[options.focus].length) {
      const own = byParty[options.focus];
      const outer = own.filter((s) => s.r === Math.max(...own.map((q) => q.r)));
      const seat = outer[Math.floor(outer.length / 2)];
      svg("circle", { cx: seat.x, cy: seat.y, r: size * 2.4, fill: "none", stroke: "var(--gold)", "stroke-width": size * 0.9 }, root);
      svg("circle", { cx: seat.x, cy: seat.y, r: size * 1.15, fill: "var(--gold)", stroke: "var(--ink)", "stroke-width": size * 0.25 }, root);
    }
    container.appendChild(root);
    return root;
  }

  function legendHtml(focus) {
    const isParty = (code) => landscape().parties.some((p) => p.code === code);
    const rows = landscape().hemicycle.filter(([code]) => isParty(code));
    const other = landscape().hemicycle.filter(([code]) => !isParty(code)).reduce((sum, [, n]) => sum + n, 0);
    const item = (label, n, color) => `<li><span class="swatch" style="background:${color}"></span>${esc(label)} <span class="num">${n}</span></li>`;
    return `<ul class="legend">${rows
      .map(([code, n]) => item(code, n, focus && focus !== code ? "var(--dim-seat)" : partyColor(code)))
      .join("")}${other ? item(lt("unaffiliated_label"), other, focus ? "var(--dim-seat)" : UNAFFILIATED_COLOR) : ""}</ul>`;
  }

  // ------------------------------------------------------------------ chrome
  function renderSwitches() {
    const langSelect = document.getElementById("lang-select");
    langSelect.setAttribute("aria-label", t("language_label"));
    langSelect.innerHTML = Object.entries(DATA.languages)
      .sort(([ca, a], [cb, b]) => (cb === DATA.defaults.lang) - (ca === DATA.defaults.lang) || a.name.localeCompare(b.name))
      .map(([code, l]) => `<option value="${code}" lang="${code}"${code === state.lang ? " selected" : ""}>${esc(l.name)}</option>`)
      .join("");
    const select = document.getElementById("landscape-select");
    select.setAttribute("aria-label", t("landscape_label"));
    const option = (l) => `<option value="${l.id}"${l.id === state.landscape ? " selected" : ""}>${esc(textOf(l, "short_name"))}</option>`;
    const countries = DATA.landscapes.filter((l) => l.id !== "eu")
      .sort((a, b) => textOf(a, "short_name").localeCompare(textOf(b, "short_name"), state.lang));
    select.innerHTML = DATA.landscapes.filter((l) => l.id === "eu").map(option).join("")
      + `<optgroup label="${esc(t("web_countries"))}">${countries.map(option).join("")}</optgroup>`;
    document.documentElement.lang = state.lang;
  }

  function renderFooter() {
    footer.innerHTML = `
      <h2>${esc(t("web_about"))}</h2>
      <p class="small">${md(lt("inclusion_note"))}</p>
      <p class="small">${md(t("positions_note", { contact: "ribeirobarbosarafael@gmail.com" }))}</p>
      <p class="small">${md(t("affinity_note"))}</p>
      <p class="small">${md(t("details_disclaimer"))}</p>`;
  }

  function render() {
    if (state.mode !== "intro") state._last = state.mode; // screen to offer when the visitor returns
    renderSwitches();
    renderFooter();
    view.innerHTML = "";
    ({ intro: renderIntro, quiz: renderQuiz, midpoint: renderMidpoint, results: renderResults }[state.mode] || renderIntro)();
    save();
    writeUrl();
  }

  // ------------------------------------------------------------------- intro
  function renderIntro() {
    const nShort = shortIds().length;
    const nAll = allIds().length;
    const answered = Object.keys(state.answers).length;
    const hero = document.createElement("section");
    hero.className = "hero";
    hero.innerHTML = `
      <div class="hero-copy">
        <p class="eyebrow">${esc(lt("name"))}</p>
        <h1 class="hero-title">${esc(t("web_tagline"))}</h1>
        <p class="hero-lede">${esc(t("web_lede", { n: nAll }))}</p>
        <div class="btn-row">
          ${nShort ? `<button class="btn btn-primary" data-action="start-short">${esc(t("start_short", { n: nShort }))}<small>${esc(t("web_duration_short"))}</small></button>` : ""}
          <button class="btn" data-action="start-full">${esc(t("start_full", { n: nAll }))}<small>${esc(t("web_duration_full"))}</small></button>
        </div>
        <p class="note">${esc(t("intro_subaxes_note", { n: DATA.subaxes.length }))}</p>
        ${resumable && answered ? `<button class="btn btn-quiet resume" data-action="resume">↻ ${esc(t("web_resume", { n: answered }))}</button>` : ""}
      </div>
      <figure class="chamber" style="margin:0"></figure>`;
    view.appendChild(hero);
    const fig = hero.querySelector(".chamber");
    drawHemicycle(fig, {});
    fig.insertAdjacentHTML("beforeend", `${legendHtml()}<figcaption class="small">${esc(lt("hemicycle_note"))}</figcaption>`);

    const counts = {};
    DATA.questions.forEach((q) => (counts[q.axis] = (counts[q.axis] || 0) + 1));
    const ends = AXIS_ENDS;
    const axes = document.createElement("section");
    axes.className = "section";
    axes.innerHTML = `
      <div class="section-head">
        <h2 class="section-title">${esc(t("web_axes_title"))}</h2>
        <p class="prose">${esc(t("statements_note").replace(/[:：]\s*$/, "."))}</p>
        <p class="prose">${esc(t("subaxes_explainer", { n: DATA.subaxes.length }))}</p>
      </div>
      <div class="axes">
        ${AXES.map((axis) => `
          <article class="axis-card">
            <p class="eyebrow">${AXIS_PREFIX[axis]} · ${esc(t("web_axis_statements", { n: counts[axis] }))}</p>
            <h3>${esc(t("web_axis_" + axis))}</h3>
            <p>${esc(stripLabel(t("axis_" + axis + "_desc")))}</p>
            <div class="spectrum"><div class="spectrum-bar"></div>
              <div class="spectrum-ends"><span>${esc(t(ends[axis][0]))}</span><span>${esc(t(ends[axis][1]))}</span></div></div>
            <ul class="subaxis-list">
              ${DATA.subaxes.filter((sub) => sub.axis === axis).map((sub) => `
                <li><span>${esc(t("sub_" + sub.id + "_low"))}</span><span aria-hidden="true">↔</span><span>${esc(t("sub_" + sub.id + "_high"))}</span></li>`).join("")}
            </ul>
          </article>`).join("")}
      </div>`;
    view.appendChild(axes);
  }

  function startTest(kind) {
    state.kind = kind;
    state.sequence = kind === "short" ? shortIds() : allIds();
    state.idx = 0;
    state.answers = {};
    state.mode = "quiz";
    resumable = false;
    render();
    focusView();
  }

  // -------------------------------------------------------------------- quiz
  function renderQuiz() {
    const seq = state.sequence;
    if (!(state.idx >= 0 && state.idx < seq.length)) {
      state.mode = "intro";
      return renderIntro();
    }
    const id = seq[state.idx];
    const q = DATA.questions[qIndex[id]];
    const current = state.answers[id];
    const answered = seq.filter((x) => x in state.answers).length;
    const wrap = document.createElement("section");
    wrap.className = "quiz";
    wrap.innerHTML = `
      <div style="display:grid;gap:10px">
        <div class="progress" aria-hidden="true">
          ${seq.map((x, i) => `<span${x in state.answers ? ` data-v="${state.answers[x]}"` : ""}${i === state.idx ? ' class="is-current"' : ""}></span>`).join("")}
        </div>
        <div class="progress-meta">
          <p class="eyebrow">${esc(id.replace(/(\D+)(\d+)/, "$1 · $2"))} — ${esc(t("web_axis_" + q.axis))}</p>
          <p class="eyebrow">${esc(t("question_header", { i: state.idx + 1, n: seq.length }))} · ${esc(t("web_answered", { n: answered }))}</p>
        </div>
      </div>
      <h1 class="statement enter" tabindex="-1">${esc(questionText(id))}</h1>
      <div class="scale" role="group" aria-label="${esc(t("question_prompt"))}">
        ${VALUES.map((v, i) => `<button type="button" class="choice" data-answer="${v}" data-v="${v}" aria-pressed="${current === v}">${esc(t("answer_" + v))}<span class="key" aria-hidden="true">${i + 1}</span></button>`).join("")}
      </div>
      <div class="quiz-nav">
        <div class="btn-row">
          ${state.idx > 0 ? `<button type="button" class="btn btn-quiet" data-action="back">← ${esc(t("back"))}</button>` : ""}
          <button type="button" class="btn btn-quiet" data-action="skip">${esc(t("skip"))} →</button>
        </div>
        <p class="hint">${esc(t("web_keyboard_hint"))}</p>
      </div>`;
    view.appendChild(wrap);
  }

  function answer(value) {
    const id = state.sequence[state.idx];
    if (value === null) delete state.answers[id];
    else state.answers[id] = value;
    state.idx += 1;
    if (state.idx >= state.sequence.length) state.mode = state.kind === "short" ? "midpoint" : "results";
    render();
    focusView();
  }

  function back() {
    if (state.idx > 0) {
      state.idx -= 1;
      render();
      focusView();
    }
  }

  function focusView() {
    const target = view.querySelector(".statement") || view;
    try { target.focus({ preventScroll: true }); } catch (e) { /* ignore */ }
    window.scrollTo({ top: 0 });
  }

  // ---------------------------------------------------------------- midpoint
  function renderMidpoint() {
    const nShort = shortIds().length;
    const nAll = allIds().length;
    const wrap = document.createElement("section");
    wrap.className = "midpoint";
    wrap.innerHTML = `
      <p class="eyebrow">${esc(t("web_answered", { n: Object.keys(state.answers).length }))}</p>
      <h1 class="section-title">${esc(t("midpoint_header", { n: nShort }))}</h1>
      <p class="prose">${esc(t("midpoint_text"))}</p>
      <p class="note">${esc(t("midpoint_subaxes_note", { n: DATA.subaxes.length }))}</p>
      <div class="btn-row">
        <button class="btn btn-primary" data-action="see-results">${esc(t("see_results", { n: nShort }))}</button>
        <button class="btn" data-action="continue">${esc(t("continue_test", { n: nAll }))}</button>
      </div>`;
    view.appendChild(wrap);
  }

  function continueFull() {
    const short = shortIds();
    state.sequence = short.concat(allIds().filter((id) => !short.includes(id)));
    state.idx = short.length;
    state.kind = "full";
    state.mode = "quiz";
    render();
    focusView();
  }

  // ----------------------------------------------------------------- results
  function renderResults() {
    const answers = state.answers;
    const n = Object.keys(answers).length;
    if (!n) {
      view.innerHTML = `<section class="midpoint"><h1 class="section-title">${esc(t("no_answers"))}</h1><div class="btn-row"><button class="btn btn-primary" data-action="restart">${esc(t("restart"))}</button></div></section>`;
      return;
    }
    const ranking = affinity(answers);
    const top = ranking[0];
    const nShort = shortIds().length;
    const basis = state.kind === "short" && state.sequence.length === nShort && n === nShort
      ? t("results_short", { n })
      : n === allIds().length ? t("results_full", { n }) : t("results_partial", { n });

    // 1. Verdict + chamber
    const verdict = document.createElement("section");
    verdict.className = "verdict";
    verdict.innerHTML = `
      <div class="verdict-copy">
        <p class="eyebrow">${esc(t("web_your_seat"))} · ${esc(lt("short_name"))}</p>
        <h1 class="verdict-title">${fill(esc(t("web_you_sit_with", { party: "{party}" })), { party: `<span class="party"><span class="swatch" style="background:${partyColor(top.code)}"></span>${esc(top.code)}</span>` })}</h1>
        <p class="verdict-name">${esc(partyInfo(top.code).name || "")}</p>
        <p class="verdict-score"><strong>${pct(top.score)}</strong><span>${esc(t("web_match"))}</span></p>
        <p class="basis">${esc(basis)}</p>
      </div>
      <figure class="chamber" style="margin:0"></figure>`;
    view.appendChild(verdict);
    const fig = verdict.querySelector(".chamber");
    if (drawHemicycle(fig, { focus: top.code, static: true })) {
      fig.insertAdjacentHTML("beforeend", `${legendHtml(top.code)}<figcaption class="small">${esc(lt("hemicycle_note"))}</figcaption>`);
    }

    // 2. Ranking
    const rank = document.createElement("section");
    rank.className = "section";
    rank.innerHTML = `
      <div class="section-head"><h2 class="section-title">${esc(lt("results_title"))}</h2>
        <p class="prose">${esc(t("affinity_explainer"))}</p></div>
      <ol class="ranking">
        ${ranking.map((r, i) => `
          <li class="rank">
            <span class="rank-pos">${String(i + 1).padStart(2, "0")}</span>
            <span class="rank-name"><span class="swatch" style="background:${partyColor(r.code)}"></span><span>${esc(r.code)}</span></span>
            <span class="rank-track"><span class="rank-fill" style="display:block;width:${(r.score * 100).toFixed(1)}%;background:${partyColor(r.code)};animation-delay:${i * 40}ms"></span></span>
            <span class="rank-pct">${pct(r.score)}</span>
          </li>`).join("")}
      </ol>`;
    view.appendChild(rank);

    // 3. Compass, then the three dimensions; after the full test each one opens into its four sub-axes
    const you = userCompass();
    const parties = landscape().parties.map((p) => ({ code: p.code, color: p.color, ...partyCompass(p.code) }));
    const full = isFullTest();
    const subYou = full ? subaxisScores((id) => state.answers[id]) : {};
    const subParties = full
      ? landscape().parties.map((p) => ({ code: p.code, color: p.color, ...subaxisScores((id) => landscape().positions[p.code][qIndex[id]]) }))
      : [];
    const subLabel = (id) => `${t("sub_" + id + "_low")} – ${t("sub_" + id + "_high")}`;
    const comp = document.createElement("section");
    comp.className = "section";
    comp.innerHTML = `
      <div class="section-head"><h2 class="section-title">${esc(t("compass_title"))}</h2>
        <p class="prose">${esc(t("web_compass_caption"))}</p></div>
      <figure class="compass" style="margin:0"></figure>`;
    view.appendChild(comp);
    drawCompass(comp.querySelector(".compass"), you, parties);

    const dims = document.createElement("section");
    dims.className = "section";
    dims.innerHTML = `
      <div class="section-head"><h2 class="section-title">${esc(t("web_dimensions_title"))}</h2>
        <p class="prose">${esc(t("web_dimensions_intro", { name: t("subaxes_title") }))}</p></div>
      <div class="strips">
        ${AXES.map((a) => `
          <div class="strip">
            <div class="strip-head"><h3>${esc(t("web_axis_" + a))}</h3><span class="strip-score">${esc(t("you"))} ${signed(you[a])}</span></div>
            <p class="strip-desc">${esc(stripLabel(t("axis_" + a + "_desc")))}</p>
            <div class="strip-plot" data-axis="${a}"></div>
            <div class="spectrum-ends"><span>${esc(t(AXIS_ENDS[a][0]))}</span><span>${esc(t(AXIS_ENDS[a][1]))}</span></div>
            ${full ? `
            <button type="button" class="sub-toggle" data-action="toggle-sub" aria-expanded="false" aria-controls="sub-${a}">
              <span class="chev" aria-hidden="true">▸</span> ${esc(t("subaxes_title"))} <span class="sub-count">${DATA.subaxes.filter((sub) => sub.axis === a).length}</span>
            </button>
            <div class="sub-panel" id="sub-${a}" hidden>
              ${DATA.subaxes.filter((sub) => sub.axis === a).map((sub) => `
                <div class="strip strip-sub">
                  <div class="strip-head"><h4>${esc(subLabel(sub.id))}</h4>
                    <span class="strip-score">${subYou[sub.id] === null ? esc(t("subaxis_insufficient")) : `${esc(t("you"))} ${signed(subYou[sub.id])}`}</span></div>
                  <p class="strip-desc">${esc(t("sub_" + sub.id + "_desc"))}</p>
                  <div class="strip-plot" data-sub="${sub.id}"></div>
                  <div class="spectrum-ends"><span>${esc(t("sub_" + sub.id + "_low"))}</span><span>${esc(t("sub_" + sub.id + "_high"))}</span></div>
                </div>`).join("")}
            </div>` : ""}
          </div>`).join("")}
      </div>
      ${full
        ? `<p class="small sub-note">${esc(t("subaxes_caption"))}</p>`
        : `<div class="sub-locked"><h3>${esc(t("subaxes_title"))}</h3><p>${esc(t("subaxes_locked", { n: DATA.subaxes.length, m: allIds().length }))}</p>
            ${state.kind === "short" ? `<div class="btn-row"><button class="btn" data-action="continue">${esc(t("continue_test", { n: allIds().length }))}</button></div>` : ""}</div>`}`;
    view.appendChild(dims);
    dims.querySelectorAll(".strip-plot[data-axis]").forEach((el) => drawStrip(el, el.dataset.axis, you, parties, t("web_axis_" + el.dataset.axis)));
    dims.querySelectorAll(".strip-plot[data-sub]").forEach((el) => drawStrip(el, el.dataset.sub, subYou, subParties, subLabel(el.dataset.sub)));

    // 4. Group details
    const scoreOf = Object.fromEntries(ranking.map((r) => [r.code, r.score]));
    const groups = document.createElement("section");
    groups.className = "section";
    groups.innerHTML = `
      <div class="section-head"><h2 class="section-title">${esc(lt("details_title"))}</h2></div>
      <div class="groups">
        ${ranking.map((r) => {
          const d = partyInfo(r.code);
          const url = landscape().parties.find((p) => p.code === r.code).url;
          const facts = [
            [lt("leader_label"), d.leader], [t("founded_label"), d.founded], [t("spectrum_label"), d.spectrum],
            [t("ideologies_label"), d.ideologies], [t("priorities_label"), d.priorities],
          ].filter(([, v]) => v);
          return `
          <details class="group">
            <summary>
              <span class="swatch" style="background:${partyColor(r.code)}"></span>
              <span><span class="group-code">${esc(r.code)}</span><span class="group-full">${esc(d.name || "")}</span></span>
              <span class="group-pct">${pct(scoreOf[r.code])}</span>
            </summary>
            <div class="group-body">
              <p>${esc(d.description || "")}</p>
              <dl class="facts">${facts.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join("")}</dl>
              <div class="links">
                ${url ? `<a href="${esc(url)}" target="_blank" rel="noopener">${esc(t("official_site"))} ↗</a>` : ""}
                ${d.program_url ? `<a href="${esc(d.program_url)}" target="_blank" rel="noopener">${esc(t("program_link"))} ↗</a>` : ""}
                ${d.wiki_url ? `<a href="${esc(d.wiki_url)}" target="_blank" rel="noopener">${esc(t("wiki_link"))} ↗</a>` : ""}
              </div>
            </div>
          </details>`;
        }).join("")}
      </div>`;
    view.appendChild(groups);

    // 5. Share + restart
    const shareText = t("share_text", { party: top.code, affinity: pct(top.score) });
    const pageUrl = location.href.split("#")[0];
    const enc = encodeURIComponent;
    const share = document.createElement("section");
    share.className = "section";
    share.innerHTML = `
      <div class="share">
        <h2>${esc(t("share_title"))}</h2>
        <p class="share-text" id="share-text">${esc(shareText)} ${esc(pageUrl)}</p>
        <div class="btn-row">
          <button type="button" class="copy" data-action="copy">${esc(t("web_copy_result"))}</button>
          <a href="https://twitter.com/intent/tweet?text=${enc(shareText)}&url=${enc(pageUrl)}&hashtags=${enc(lt("hashtags"))}" target="_blank" rel="noopener">X</a>
          <a href="https://wa.me/?text=${enc(shareText + " " + pageUrl)}" target="_blank" rel="noopener">WhatsApp</a>
          <a href="https://www.facebook.com/sharer/sharer.php?u=${enc(pageUrl)}" target="_blank" rel="noopener">Facebook</a>
          <a href="mailto:?subject=${enc(t("share_email_subject"))}&body=${enc(shareText + " " + pageUrl)}">Email</a>
        </div>
        <p class="share-status" id="share-status" role="status"></p>
      </div>
      <div class="btn-row"><button class="btn" data-action="restart">↺ ${esc(t("restart"))}</button></div>`;
    view.appendChild(share);
  }

  function drawCompass(container, you, parties) {
    const W = 460, P = 34, S = W - 2 * P;
    const X = (v) => P + ((v + 1.1) / 2.2) * S;
    const Y = (v) => P + ((1.1 - v) / 2.2) * S;
    const root = svg("svg", { viewBox: `0 0 ${W} ${W}`, role: "img", "aria-label": t("compass_title") });
    svg("rect", { x: P, y: P, width: S, height: S, rx: 8, class: "compass-frame" }, root);
    svg("line", { x1: X(0), x2: X(0), y1: P, y2: P + S, class: "compass-grid" }, root);
    svg("line", { x1: P, x2: P + S, y1: Y(0), y2: Y(0), class: "compass-grid" }, root);
    const label = (txt, x, y, anchor, rotate) => {
      const el = svg("text", { x, y, "text-anchor": anchor, class: "compass-axis-label" }, root);
      if (rotate) el.setAttribute("transform", `rotate(-90 ${x} ${y})`);
      el.textContent = txt;
    };
    label(t("web_left"), P + 2, P + S + 22, "start");
    label(t("web_right"), P + S - 2, P + S + 22, "end");
    label(t("web_progressive"), P - 14, P + 4, "end", true);
    label(t("web_conservative"), P - 14, P + S - 4, "start", true);

    const placed = [];
    const overlaps = (b) => placed.some((o) => b.x < o.x + o.w && b.x + b.w > o.x && b.y < o.y + o.h && b.y + b.h > o.y);
    const addLabel = (txt, x, y, cls) => {
      const w = txt.length * 7.2 + 2, h = 14;
      const candidates = [[x + 9, y - h / 2], [x - 9 - w, y - h / 2], [x - w / 2, y - 10 - h], [x - w / 2, y + 10]];
      let box = null;
      for (const [bx, by] of candidates) {
        const b = { x: bx, y: by, w, h };
        if (!overlaps(b) && bx >= 0 && bx + w <= W) { box = b; break; }
      }
      box = box || { x: x + 9, y: y - h / 2, w, h };
      placed.push(box);
      const el = svg("text", { x: box.x, y: box.y + 11, class: cls }, root);
      el.textContent = txt;
    };
    for (const p of parties) placed.push({ x: X(p.economic) - 6, y: Y(p.social) - 6, w: 12, h: 12 });
    placed.push({ x: X(you.economic) - 9, y: Y(you.social) - 9, w: 18, h: 18 });

    for (const p of parties) {
      const c = svg("circle", { cx: X(p.economic), cy: Y(p.social), r: 6, class: "party-dot" }, root);
      c.style.fill = p.color;
      svg("title", {}, c).textContent = `${p.code}: ${signed(p.economic)}, ${signed(p.social)}`;
    }
    const yx = X(you.economic), yy = Y(you.social);
    svg("path", { d: `M${yx} ${yy - 10} L${yx + 9} ${yy + 6} L${yx - 9} ${yy + 6} Z`, class: "you-mark" }, root);
    addLabel(t("you"), yx + 3, yy, "you-label");
    for (const p of parties) addLabel(p.code, X(p.economic), Y(p.social), "dot-label");
    container.appendChild(root);
  }

  function drawStrip(container, axis, you, parties, label) {
    const W = 420, P = 14, mid = 58;
    const X = (v) => P + ((v + 1) / 2) * (W - 2 * P);
    // Label lanes above and below the line; each party takes the first lane where its label fits.
    const lanes = [mid - 12, mid + 24, mid - 28, mid + 40, mid - 44, mid + 56];
    const laneEnd = lanes.map(() => -Infinity);
    const labels = [...parties].sort((a, b) => a[axis] - b[axis]).map((p) => {
      const x = X(p[axis]), w = p.code.length * 7.8 + 10;
      let lane = lanes.findIndex((_, i) => x - w / 2 > laneEnd[i]);
      if (lane < 0) lane = 0;
      laneEnd[lane] = x + w / 2;
      return { p, x, y: lanes[lane] };
    });
    const top = Math.min(...labels.map((l) => l.y)) - 14;
    const bottom = Math.max(mid + 16, ...labels.map((l) => l.y + 6));
    const root = svg("svg", { viewBox: `0 ${top} ${W} ${bottom - top}`, role: "img", "aria-label": label });
    svg("line", { x1: P, x2: W - P, y1: mid, y2: mid, class: "strip-line" }, root);
    for (const { p, x, y } of labels) {
      if (Math.abs(y - mid) > 20) svg("line", { x1: x, x2: x, y1: mid, y2: y < mid ? y + 3 : y - 11, class: "strip-line", "stroke-width": 1 }, root);
      const c = svg("circle", { cx: x, cy: mid, r: 6, class: "party-dot" }, root);
      c.style.fill = p.color;
      svg("title", {}, c).textContent = `${p.code}: ${signed(p[axis])}`;
      const tx = svg("text", { x, y, "text-anchor": "middle", class: "dot-label" }, root);
      tx.textContent = p.code;
    }
    if (you[axis] !== null && you[axis] !== undefined) {
      const x = X(you[axis]);
      svg("line", { x1: x, x2: x, y1: top + 4, y2: bottom - 4, class: "you-rule" }, root);
      svg("path", { d: `M${x} ${mid - 9} L${x + 9} ${mid + 7} L${x - 9} ${mid + 7} Z`, class: "you-mark" }, root);
    }
    container.appendChild(root);
  }

  function copyResult() {
    const status = document.getElementById("share-status");
    const text = document.getElementById("share-text").textContent;
    const fallback = () => {
      const range = document.createRange();
      range.selectNodeContents(document.getElementById("share-text"));
      const sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
      status.textContent = t("web_copy_failed");
    };
    try {
      navigator.clipboard.writeText(text).then(() => (status.textContent = t("web_copied")), fallback);
    } catch (e) {
      fallback();
    }
  }

  function restart() {
    state.mode = "intro";
    state.answers = {};
    state.sequence = [];
    state.idx = 0;
    resumable = false;
    render();
    focusView();
  }

  // ------------------------------------------------------------------ events
  document.addEventListener("click", (e) => {
    const el = e.target.closest("button, a[data-action]");
    if (!el) return;
    if (el.dataset.landscape) { state.landscape = el.dataset.landscape; return render(); }
    if (el.dataset.answer !== undefined) return answer(Number(el.dataset.answer));
    const action = el.dataset.action;
    if (!action) return;
    if (el.tagName === "A") e.preventDefault();
    ({
      home: () => { state.mode = "intro"; resumable = Object.keys(state.answers).length > 0; render(); },
      "start-short": () => startTest("short"),
      "start-full": () => startTest("full"),
      resume: () => { resumable = false; state.mode = state.mode === "intro" ? state._last || "quiz" : state.mode; render(); focusView(); },
      skip: () => answer(null),
      back,
      "see-results": () => { state.mode = "results"; render(); focusView(); },
      continue: continueFull,
      "toggle-sub": () => {
        const open = el.getAttribute("aria-expanded") !== "true";
        el.setAttribute("aria-expanded", String(open));
        el.querySelector(".chev").textContent = open ? "▾" : "▸";
        document.getElementById(el.getAttribute("aria-controls")).hidden = !open;
      },
      copy: copyResult,
      restart,
    }[action] || (() => {}))();
  });

  document.addEventListener("change", (e) => {
    if (e.target.id === "landscape-select") { state.landscape = e.target.value; render(); }
    if (e.target.id === "lang-select") { state.lang = e.target.value; render(); }
  });

  document.addEventListener("keydown", (e) => {
    if (state.mode !== "quiz" || e.metaKey || e.ctrlKey || e.altKey) return;
    if (e.target.closest && e.target.closest("input, textarea, select")) return;
    if (/^[1-5]$/.test(e.key)) { e.preventDefault(); answer(VALUES[Number(e.key) - 1]); }
    else if (e.key === "s" || e.key === "S") { e.preventDefault(); answer(null); }
    else if (e.key === "ArrowLeft" || e.key === "Backspace") { e.preventDefault(); back(); }
  });

  // -------------------------------------------------------------------- boot
  function boot(data) {
    DATA = data;
    DATA.questions.forEach((q, i) => (qIndex[q.id] = i));
    const langs = Object.keys(DATA.languages);
    const lands = DATA.landscapes.map((l) => l.id);
    const saved = restore();
    const url = readUrl();
    const pick = (value, options, fallback) => (options.includes(value) ? value : fallback);
    state.lang = pick(url.lang, langs, pick(saved && saved.lang, langs, DATA.defaults.lang));
    state.landscape = pick(url.landscape, lands, pick(saved && saved.landscape, lands, DATA.defaults.landscape));
    if (saved && saved.answers && Array.isArray(saved.sequence)) {
      const known = new Set(allIds());
      state.answers = Object.fromEntries(Object.entries(saved.answers).filter(([id, v]) => known.has(id) && VALUES.includes(v)));
      state.sequence = saved.sequence.filter((id) => known.has(id));
      state.idx = Math.min(Number(saved.idx) || 0, state.sequence.length);
      state.kind = saved.kind === "short" ? "short" : "full";
      state._last = ["quiz", "midpoint", "results"].includes(saved.mode) ? saved.mode : saved._last;
      resumable = Object.keys(state.answers).length > 0 && !!state._last;
    }
    state.mode = "intro";
    render();
  }

  fetch("data.json")
    .then((r) => {
      if (!r.ok) throw new Error(`data.json: HTTP ${r.status}`);
      return r.json();
    })
    .then(boot)
    .catch((err) => {
      view.innerHTML = `<p class="loading">Could not load the quiz data (${esc(err.message)}). If you opened index.html directly from disk, serve the folder instead: <code>python -m http.server -d web</code>.</p>`;
    });
})();
