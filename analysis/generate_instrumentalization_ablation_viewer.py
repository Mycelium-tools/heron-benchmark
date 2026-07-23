"""Generate a standalone HTML viewer for the instrumentalization ablation transcripts."""

from __future__ import annotations

import json
from pathlib import Path

from markdown_it import MarkdownIt

from generate_instrumentalization_ablation_report import (
    BASELINE_CODING,
    PAIR_CODING,
    PHASE1_DIR,
    PHASE2_DIR,
    RERUN_DIR,
    load_rows,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "analysis/instrumentalization_ablation_viewer.html"

DOMAINS = {
    100: "Restaurant sourcing",
    101: "Home cooking",
    102: "Restaurant menu · veal",
    103: "Restaurant menu · foie gras",
    104: "Live seafood",
    105: "Pest control · pigeons",
    106: "Fishing / food · crabs",
    107: "Cosmetics",
    108: "Entertainment",
    109: "Education",
    110: "Pet trade",
    111: "Garden pests",
    112: "Farming / hatchery",
    113: "Live export",
}

md = MarkdownIt("commonmark", {"html": False, "linkify": False, "typographer": True})


def render_markdown(value: str) -> str:
    return md.render(value or "")


def transcript(row: dict[str, str], label: str) -> dict[str, object]:
    return {
        "label": label,
        "id": int(row["sample_id"]),
        "prompt": row["input"],
        "score": float(row["moral_consideration"]),
        "completionHtml": render_markdown(row["output_completion"]),
        "completionText": row["output_completion"],
        "judge": row["score_explanation"],
    }


def build_data() -> dict[str, object]:
    phase1 = load_rows(PHASE1_DIR)
    phase2 = load_rows(PHASE2_DIR)
    rerun = load_rows(RERUN_DIR)
    pairs = []

    for base_id, coding in PAIR_CODING.items():
        variants = [transcript(phase2[base_id + 100], "Ablated")]
        if base_id == 110:
            variants.append(transcript(rerun[210], "Cost-neutral rerun"))
        pairs.append(
            {
                "key": f"pair-{base_id}",
                "kind": "pair",
                "baseId": base_id,
                "domain": DOMAINS[base_id],
                "outcome": coding["outcome"],
                "cover": coding["cover"],
                "edit": coding["edit"],
                "note": coding["note"],
                "baseline": transcript(phase1[base_id], "Baseline"),
                "variants": variants,
            }
        )

    excluded = []
    for base_id in sorted(set(phase1) - set(PAIR_CODING)):
        coding, eligibility = BASELINE_CODING[base_id]
        excluded.append(
            {
                "key": f"baseline-{base_id}",
                "kind": "baseline",
                "baseId": base_id,
                "domain": DOMAINS[base_id],
                "outcome": "baseline only",
                "cover": coding,
                "edit": eligibility,
                "note": (
                    "This item did not advance to Phase 2 because the baseline was a floor case."
                    if "floor" in eligibility
                    else "This item used an ethical label without an instrumental cover to remove."
                ),
                "baseline": transcript(phase1[base_id], "Baseline"),
                "variants": [],
            }
        )

    return {
        "pairs": pairs,
        "excluded": excluded,
        "summary": {"dropped": 5, "degraded": 2, "retained": 1, "inconclusive": 1},
    }


def main() -> None:
    payload = json.dumps(build_data(), ensure_ascii=False).replace("</", "<\\/")
    document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <title>Instrumentalization Ablation · Transcript Reader</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f5f2eb;
      --surface: #fffdf8;
      --surface-2: #eee9df;
      --ink: #20201d;
      --muted: #6b6961;
      --line: #d8d2c6;
      --strong-line: #aaa398;
      --accent: #1f5c55;
      --accent-soft: #dbeae5;
      --accent-ink: #123f3a;
      --drop: #a64439;
      --drop-soft: #f4dfda;
      --degrade: #8c6419;
      --degrade-soft: #f2e7c8;
      --retain: #2f6942;
      --retain-soft: #dbeadf;
      --unclear: #66558d;
      --unclear-soft: #e6e0f0;
      --shadow: 0 16px 40px rgba(49, 45, 37, .08);
      --transcript-size: 16px;
      --header-height: 72px;
    }}
    [data-theme="dark"] {{
      color-scheme: dark;
      --bg: #171817;
      --surface: #20221f;
      --surface-2: #292c28;
      --ink: #ecebe5;
      --muted: #aaa9a1;
      --line: #3b3e39;
      --strong-line: #64675f;
      --accent: #87c5b8;
      --accent-soft: #263f3a;
      --accent-ink: #c9eee5;
      --drop: #ef9c90;
      --drop-soft: #4a2a27;
      --degrade: #e8c776;
      --degrade-soft: #493d21;
      --retain: #9bd0a8;
      --retain-soft: #294334;
      --unclear: #c2b1e2;
      --unclear-soft: #3b324d;
      --shadow: 0 18px 42px rgba(0, 0, 0, .24);
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.5;
    }}
    button, input, select {{ font: inherit; }}
    button {{ color: inherit; }}
    .app-header {{
      position: sticky;
      top: 0;
      z-index: 20;
      min-height: var(--header-height);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 24px;
      padding: 12px 24px;
      background: color-mix(in srgb, var(--bg) 90%, transparent);
      backdrop-filter: blur(18px);
      border-bottom: 1px solid var(--line);
    }}
    .brand {{ min-width: 0; }}
    .eyebrow {{
      color: var(--accent);
      font-size: 11px;
      font-weight: 700;
      letter-spacing: .12em;
      text-transform: uppercase;
    }}
    h1 {{ margin: 2px 0 0; font-size: clamp(19px, 2vw, 26px); line-height: 1.15; letter-spacing: -.02em; }}
    .header-actions, .reader-actions, .pager, .variant-tabs {{ display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }}
    .icon-button, .seg-button, .pager button, .variant-tab {{
      border: 1px solid var(--line);
      background: var(--surface);
      border-radius: 9px;
      padding: 7px 10px;
      cursor: pointer;
      transition: border-color .15s ease, background .15s ease, transform .15s ease;
    }}
    .icon-button:hover, .seg-button:hover, .pager button:hover, .variant-tab:hover {{ border-color: var(--strong-line); }}
    .icon-button:active, .seg-button:active, .pager button:active, .variant-tab:active {{ transform: translateY(1px); }}
    .seg-button[aria-pressed="true"], .variant-tab[aria-selected="true"] {{
      color: var(--accent-ink);
      border-color: var(--accent);
      background: var(--accent-soft);
    }}
    .workspace {{ display: grid; grid-template-columns: 292px minmax(0, 1fr); min-height: calc(100vh - var(--header-height)); }}
    .sidebar {{
      position: sticky;
      top: var(--header-height);
      height: calc(100vh - var(--header-height));
      overflow: auto;
      padding: 18px 14px 32px;
      border-right: 1px solid var(--line);
      background: var(--bg);
    }}
    .search-wrap {{ position: relative; margin-bottom: 16px; }}
    .search-wrap input {{
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: var(--surface);
      color: var(--ink);
      padding: 9px 11px;
      outline: none;
    }}
    .search-wrap input:focus {{ border-color: var(--accent); box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 20%, transparent); }}
    .nav-heading {{ margin: 18px 7px 7px; color: var(--muted); font-size: 11px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; }}
    .nav-list {{ display: grid; gap: 4px; }}
    .nav-item {{
      width: 100%;
      display: grid;
      grid-template-columns: 38px minmax(0, 1fr) auto;
      align-items: center;
      gap: 8px;
      border: 1px solid transparent;
      border-radius: 10px;
      padding: 9px 8px;
      background: transparent;
      color: var(--ink);
      text-align: left;
      cursor: pointer;
    }}
    .nav-item:hover {{ background: var(--surface-2); }}
    .nav-item[aria-current="true"] {{ background: var(--surface); border-color: var(--strong-line); box-shadow: 0 5px 16px rgba(0,0,0,.05); }}
    .nav-id {{ color: var(--muted); font-variant-numeric: tabular-nums; font-size: 12px; }}
    .nav-domain {{ overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; font-weight: 650; }}
    .dot {{ width: 9px; height: 9px; border-radius: 50%; background: var(--strong-line); }}
    .dot.dropped {{ background: var(--drop); }}
    .dot.degraded {{ background: var(--degrade); }}
    .dot.retained {{ background: var(--retain); }}
    .dot.inconclusive {{ background: var(--unclear); }}
    .reader {{ width: min(1480px, 100%); margin: 0 auto; padding: 28px clamp(18px, 3vw, 44px) 72px; }}
    .study-strip {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) repeat(4, auto);
      gap: 16px;
      align-items: center;
      padding-bottom: 22px;
      margin-bottom: 26px;
      border-bottom: 1px solid var(--line);
    }}
    .study-copy strong {{ display: block; font-family: Georgia, "Times New Roman", serif; font-size: 19px; font-weight: 600; }}
    .study-copy span {{ color: var(--muted); font-size: 13px; }}
    .mini-stat {{ min-width: 64px; text-align: right; }}
    .mini-stat b {{ display: block; font-size: 18px; font-variant-numeric: tabular-nums; }}
    .mini-stat span {{ color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .08em; }}
    .pair-topline {{ display: flex; align-items: flex-start; justify-content: space-between; gap: 22px; margin-bottom: 18px; }}
    .pair-title h2 {{ margin: 3px 0 4px; font-family: Georgia, "Times New Roman", serif; font-size: clamp(27px, 3vw, 40px); line-height: 1.12; font-weight: 600; letter-spacing: -.025em; }}
    .pair-title p {{ margin: 0; color: var(--muted); }}
    .badge {{ display: inline-flex; align-items: center; border-radius: 999px; padding: 4px 9px; font-size: 12px; font-weight: 700; text-transform: capitalize; }}
    .badge.dropped {{ color: var(--drop); background: var(--drop-soft); }}
    .badge.degraded {{ color: var(--degrade); background: var(--degrade-soft); }}
    .badge.retained {{ color: var(--retain); background: var(--retain-soft); }}
    .badge.inconclusive {{ color: var(--unclear); background: var(--unclear-soft); }}
    .badge.baseline {{ color: var(--muted); background: var(--surface-2); }}
    .meta-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; margin: 0 0 20px; }}
    .meta-item {{ padding: 12px 14px; border-top: 2px solid var(--line); }}
    .meta-item dt {{ color: var(--muted); font-size: 11px; font-weight: 700; letter-spacing: .09em; text-transform: uppercase; }}
    .meta-item dd {{ margin: 5px 0 0; font-size: 13px; }}
    .reader-toolbar {{
      position: sticky;
      top: var(--header-height);
      z-index: 10;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 14px;
      margin: 0 -6px 18px;
      padding: 10px 6px;
      background: color-mix(in srgb, var(--bg) 92%, transparent);
      backdrop-filter: blur(14px);
      border-bottom: 1px solid var(--line);
    }}
    .score-line {{ color: var(--muted); font-size: 13px; }}
    .score-line b {{ color: var(--ink); font-variant-numeric: tabular-nums; }}
    .comparison {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; align-items: start; }}
    .comparison.stacked {{ grid-template-columns: 1fr; }}
    .transcript {{ min-width: 0; border: 1px solid var(--line); background: var(--surface); box-shadow: var(--shadow); }}
    .transcript-head {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 12px 16px;
      border-bottom: 1px solid var(--line);
      background: var(--surface-2);
    }}
    .transcript-label {{ font-weight: 750; }}
    .score {{ font-variant-numeric: tabular-nums; color: var(--muted); font-size: 12px; }}
    .prompt {{ padding: 16px 20px; border-bottom: 1px solid var(--line); background: color-mix(in srgb, var(--accent-soft) 52%, var(--surface)); }}
    .prompt-label, .judge-label {{ display: block; margin-bottom: 6px; color: var(--muted); font-size: 10px; font-weight: 750; letter-spacing: .1em; text-transform: uppercase; }}
    .prompt p {{ margin: 0; font-size: 14px; font-weight: 620; }}
    .completion {{ padding: 24px clamp(20px, 3vw, 34px); font-family: Georgia, "Times New Roman", serif; font-size: var(--transcript-size); line-height: 1.72; }}
    .completion h1, .completion h2, .completion h3, .completion h4 {{ margin: 1.5em 0 .55em; font-family: Inter, ui-sans-serif, sans-serif; line-height: 1.25; letter-spacing: -.01em; }}
    .completion h1 {{ font-size: 1.45em; }}
    .completion h2 {{ font-size: 1.28em; }}
    .completion h3, .completion h4 {{ font-size: 1.08em; }}
    .completion p {{ margin: 0 0 1em; }}
    .completion ul, .completion ol {{ padding-left: 1.45em; }}
    .completion li {{ margin: .35em 0; }}
    .completion hr {{ border: 0; border-top: 1px solid var(--line); margin: 1.8em 0; }}
    .completion strong {{ font-weight: 700; }}
    .judge {{ padding: 16px 20px; border-top: 1px solid var(--line); color: var(--muted); font-size: 13px; background: var(--surface-2); }}
    .judge p {{ margin: 0; }}
    .empty-state {{ padding: 80px 20px; text-align: center; color: var(--muted); }}
    .pager {{ justify-content: space-between; margin-top: 24px; }}
    .pager button:disabled {{ opacity: .4; cursor: default; }}
    .kbd-help {{ margin-top: 16px; color: var(--muted); font-size: 11px; text-align: center; }}
    kbd {{ padding: 1px 5px; border: 1px solid var(--line); border-bottom-color: var(--strong-line); border-radius: 4px; background: var(--surface); font-family: inherit; }}
    .sr-only {{ position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0; }}
    @media (max-width: 1040px) {{
      .workspace {{ grid-template-columns: 240px minmax(0, 1fr); }}
      .sidebar {{ padding-inline: 10px; }}
      .study-strip {{ grid-template-columns: minmax(0, 1fr) repeat(2, auto); }}
      .mini-stat:nth-of-type(3), .mini-stat:nth-of-type(4) {{ display: none; }}
      .comparison {{ grid-template-columns: 1fr; }}
      #layoutControls {{ display: none; }}
    }}
    @media (max-width: 760px) {{
      :root {{ --header-height: auto; }}
      .app-header {{ position: static; padding: 13px 15px; }}
      .header-actions .layout-label, .header-actions .font-label {{ display: none; }}
      .workspace {{ display: block; }}
      .sidebar {{ position: static; width: 100%; height: auto; max-height: 310px; border-right: 0; border-bottom: 1px solid var(--line); }}
      .nav-list {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .reader {{ padding: 22px 14px 54px; }}
      .study-strip {{ grid-template-columns: 1fr repeat(2, auto); gap: 10px; }}
      .pair-topline {{ display: block; }}
      .pair-topline .badge {{ margin-top: 12px; }}
      .meta-grid {{ grid-template-columns: 1fr; gap: 0; }}
      .reader-toolbar {{ position: static; }}
      .completion {{ padding-inline: 20px; }}
    }}
    @media (max-width: 470px) {{
      .brand .eyebrow {{ display: none; }}
      .app-header {{ align-items: flex-start; }}
      .header-actions {{ justify-content: flex-end; }}
      .nav-list {{ grid-template-columns: 1fr; }}
      .study-strip {{ grid-template-columns: 1fr 1fr; }}
      .study-copy {{ grid-column: 1 / -1; }}
      .mini-stat {{ text-align: left; }}
    }}
    @media print {{
      .app-header, .sidebar, .reader-toolbar, .pager, .kbd-help {{ display: none !important; }}
      .workspace {{ display: block; }}
      .reader {{ width: 100%; max-width: none; padding: 0; }}
      .comparison {{ grid-template-columns: 1fr 1fr; }}
      .transcript {{ box-shadow: none; break-inside: avoid; }}
    }}
  </style>
</head>
<body>
  <header class="app-header">
    <div class="brand">
      <div class="eyebrow">HERON experiment · July 2026</div>
      <h1>Instrumentalization Ablation</h1>
    </div>
    <div class="header-actions" aria-label="Viewer settings">
      <span class="font-label sr-only">Transcript text size</span>
      <button class="icon-button" id="fontDown" type="button" aria-label="Decrease transcript text size">A−</button>
      <button class="icon-button" id="fontUp" type="button" aria-label="Increase transcript text size">A+</button>
      <button class="icon-button" id="themeToggle" type="button" aria-label="Toggle dark mode">◐</button>
    </div>
  </header>

  <div class="workspace">
    <aside class="sidebar" aria-label="Transcript navigation">
      <label class="search-wrap">
        <span class="sr-only">Filter transcripts</span>
        <input id="search" type="search" placeholder="Filter by ID, topic, outcome…" autocomplete="off">
      </label>
      <div id="nav"></div>
      <div class="kbd-help"><kbd>J</kbd>/<kbd>K</kbd> next or previous · <kbd>/</kbd> search</div>
    </aside>

    <main class="reader" id="reader" tabindex="-1">
      <section class="study-strip" aria-label="Study summary">
        <div class="study-copy">
          <strong>7 of 8 interpretable pairs dropped or degraded</strong>
          <span>Gemini 3.1 Pro Preview · judged by GPT-5.6 Terra · one epoch</span>
        </div>
        <div class="mini-stat"><b>5</b><span>Dropped</span></div>
        <div class="mini-stat"><b>2</b><span>Degraded</span></div>
        <div class="mini-stat"><b>1</b><span>Retained</span></div>
        <div class="mini-stat"><b>1</b><span>Inconclusive</span></div>
      </section>
      <div id="content"></div>
    </main>
  </div>

  <script id="experimentData" type="application/json">{payload}</script>
  <script>
    (() => {{
      const data = JSON.parse(document.getElementById('experimentData').textContent);
      const items = [...data.pairs, ...data.excluded];
      const nav = document.getElementById('nav');
      const content = document.getElementById('content');
      const search = document.getElementById('search');
      const root = document.documentElement;
      let activeKey = location.hash.slice(1) || items[0].key;
      let layout = localStorage.getItem('heron-layout') || 'split';
      let fontSize = Number(localStorage.getItem('heron-font-size') || 16);
      let activeVariant = 0;

      const escapeHtml = (value) => String(value ?? '')
        .replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;').replaceAll("'", '&#039;');

      const outcomeClass = (outcome) => {{
        if (outcome.startsWith('dropped')) return 'dropped';
        if (outcome.startsWith('degraded')) return 'degraded';
        if (outcome.startsWith('retained')) return 'retained';
        if (outcome.startsWith('inconclusive')) return 'inconclusive';
        return 'baseline';
      }};

      const formatScore = (score) => Number(score).toFixed(2);

      function renderNav(filter = '') {{
        const query = filter.trim().toLowerCase();
        const groups = [
          ['Paired comparisons', data.pairs],
          ['Baseline only', data.excluded],
        ];
        nav.innerHTML = groups.map(([title, group]) => {{
          const visible = group.filter((item) =>
            [item.baseId, item.domain, item.outcome, item.cover].join(' ').toLowerCase().includes(query)
          );
          if (!visible.length) return '';
          return `<div class="nav-heading">${{title}}</div><div class="nav-list">${{visible.map((item) => `
            <button class="nav-item" type="button" data-key="${{item.key}}" aria-current="${{item.key === activeKey}}">
              <span class="nav-id">${{item.kind === 'pair' ? `${{item.baseId}}↔${{item.baseId + 100}}` : item.baseId}}</span>
              <span class="nav-domain">${{escapeHtml(item.domain)}}</span>
              <span class="dot ${{outcomeClass(item.outcome)}}" aria-label="${{escapeHtml(item.outcome)}}"></span>
            </button>`).join('')}}</div>`;
        }}).join('') || '<div class="empty-state">No transcripts match.</div>';
        nav.querySelectorAll('[data-key]').forEach((button) => button.addEventListener('click', () => selectItem(button.dataset.key)));
      }}

      function transcriptPanel(row) {{
        return `<article class="transcript">
          <header class="transcript-head">
            <span class="transcript-label">${{escapeHtml(row.label)}} · ID ${{row.id}}</span>
            <span class="score">Judge score <strong>${{formatScore(row.score)}}</strong></span>
          </header>
          <section class="prompt">
            <span class="prompt-label">User prompt</span>
            <p>${{escapeHtml(row.prompt)}}</p>
          </section>
          <section class="completion">${{row.completionHtml}}</section>
          <footer class="judge">
            <span class="judge-label">Judge explanation</span>
            <p>${{escapeHtml(row.judge)}}</p>
          </footer>
        </article>`;
      }}

      function renderContent() {{
        const item = items.find((candidate) => candidate.key === activeKey) || items[0];
        activeKey = item.key;
        const variant = item.variants[activeVariant] || item.variants[0];
        const itemIndex = items.findIndex((candidate) => candidate.key === item.key);
        const outcome = outcomeClass(item.outcome);
        const pairId = item.kind === 'pair' ? `${{item.baseId}} ↔ ${{item.baseId + 100}}` : `ID ${{item.baseId}}`;
        const scoreLine = variant
          ? `<span class="score-line"><b>${{formatScore(item.baseline.score)}}</b> baseline → <b>${{formatScore(variant.score)}}</b> ${{escapeHtml(variant.label.toLowerCase())}} (${{variant.score - item.baseline.score >= 0 ? '+' : ''}}${{(variant.score - item.baseline.score).toFixed(2)}})</span>`
          : `<span class="score-line">Baseline judge score <b>${{formatScore(item.baseline.score)}}</b></span>`;
        const variantTabs = item.variants.length > 1 ? `<div class="variant-tabs" role="tablist" aria-label="Ablation versions">${{item.variants.map((row, index) => `
          <button class="variant-tab" type="button" role="tab" aria-selected="${{index === activeVariant}}" data-variant="${{index}}">${{escapeHtml(row.label)}}</button>`).join('')}}</div>` : '';

        content.innerHTML = `
          <section class="pair-topline">
            <div class="pair-title">
              <div class="eyebrow">${{escapeHtml(pairId)}}</div>
              <h2>${{escapeHtml(item.domain)}}</h2>
              <p>${{escapeHtml(item.note)}}</p>
            </div>
            <span class="badge ${{outcome}}">${{escapeHtml(item.outcome)}}</span>
          </section>
          <dl class="meta-grid">
            <div class="meta-item"><dt>Observed cover</dt><dd>${{escapeHtml(item.cover)}}</dd></div>
            <div class="meta-item"><dt>Ablation edit</dt><dd>${{escapeHtml(item.edit)}}</dd></div>
            <div class="meta-item"><dt>Reading note</dt><dd>${{item.kind === 'pair' ? 'Compare what happens to welfare language after the cover is removed.' : 'Baseline context only; no paired ablation was run.'}}</dd></div>
          </dl>
          <div class="reader-toolbar">
            <div>${{scoreLine}}</div>
            <div class="reader-actions">
              ${{variantTabs}}
              <div id="layoutControls" aria-label="Transcript layout">
                <button class="seg-button" type="button" data-layout="split" aria-pressed="${{layout === 'split'}}">Side by side</button>
                <button class="seg-button" type="button" data-layout="stacked" aria-pressed="${{layout === 'stacked'}}">Stacked</button>
              </div>
            </div>
          </div>
          <section class="comparison ${{layout === 'stacked' ? 'stacked' : ''}}" aria-label="Transcript comparison">
            ${{transcriptPanel(item.baseline)}}
            ${{variant ? transcriptPanel(variant) : ''}}
          </section>
          <nav class="pager" aria-label="Previous and next transcript">
            <button type="button" id="prevItem" ${{itemIndex === 0 ? 'disabled' : ''}}>← Previous</button>
            <button type="button" id="nextItem" ${{itemIndex === items.length - 1 ? 'disabled' : ''}}>Next →</button>
          </nav>`;

        content.querySelectorAll('[data-layout]').forEach((button) => button.addEventListener('click', () => {{
          layout = button.dataset.layout;
          localStorage.setItem('heron-layout', layout);
          renderContent();
        }}));
        content.querySelectorAll('[data-variant]').forEach((button) => button.addEventListener('click', () => {{
          activeVariant = Number(button.dataset.variant);
          renderContent();
        }}));
        document.getElementById('prevItem').addEventListener('click', () => selectItem(items[itemIndex - 1]?.key));
        document.getElementById('nextItem').addEventListener('click', () => selectItem(items[itemIndex + 1]?.key));
        renderNav(search.value);
      }}

      function selectItem(key) {{
        if (!key || key === activeKey) return;
        activeKey = key;
        activeVariant = 0;
        history.replaceState(null, '', `#${{key}}`);
        renderContent();
        document.getElementById('reader').focus({{ preventScroll: true }});
        window.scrollTo({{ top: 0, behavior: 'smooth' }});
      }}

      function applyFontSize() {{
        fontSize = Math.max(13, Math.min(21, fontSize));
        root.style.setProperty('--transcript-size', `${{fontSize}}px`);
        localStorage.setItem('heron-font-size', String(fontSize));
      }}

      function applyTheme(theme) {{
        root.dataset.theme = theme;
        localStorage.setItem('heron-theme', theme);
        document.getElementById('themeToggle').setAttribute('aria-label', theme === 'dark' ? 'Use light mode' : 'Use dark mode');
      }}

      const storedTheme = localStorage.getItem('heron-theme');
      applyTheme(storedTheme || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'));
      applyFontSize();
      renderNav();
      renderContent();

      search.addEventListener('input', () => renderNav(search.value));
      document.getElementById('fontDown').addEventListener('click', () => {{ fontSize -= 1; applyFontSize(); }});
      document.getElementById('fontUp').addEventListener('click', () => {{ fontSize += 1; applyFontSize(); }});
      document.getElementById('themeToggle').addEventListener('click', () => applyTheme(root.dataset.theme === 'dark' ? 'light' : 'dark'));
      window.addEventListener('hashchange', () => {{
        const key = location.hash.slice(1);
        if (items.some((item) => item.key === key)) selectItem(key);
      }});
      document.addEventListener('keydown', (event) => {{
        if (event.target.matches('input, textarea, select')) return;
        const index = items.findIndex((item) => item.key === activeKey);
        if (event.key.toLowerCase() === 'j' && items[index + 1]) selectItem(items[index + 1].key);
        if (event.key.toLowerCase() === 'k' && items[index - 1]) selectItem(items[index - 1].key);
        if (event.key === '/') {{ event.preventDefault(); search.focus(); }}
      }});
    }})();
  </script>
</body>
</html>
"""
    OUTPUT.write_text(document, encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)} ({OUTPUT.stat().st_size / 1024:.1f} KiB)")


if __name__ == "__main__":
    main()
