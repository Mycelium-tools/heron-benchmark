#!/usr/bin/env python3
"""Build a self-contained qualitative review interface from frozen results."""

from __future__ import annotations

import csv
import json
from pathlib import Path

EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
RESULTS_DIR = EXPERIMENT_DIR / "results"
OUTPUT_PATH = RESULTS_DIR / "qualitative_review.html"


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def compact_judgment(row: dict) -> dict:
    return {
        "judge_key": row["judge_key"],
        "judge_label": row["judge_label"],
        "judge_family": row["judge_family"],
        "judge_role": row["judge_role"],
        "judge_reasoning": row["judge_reasoning"],
        "score": row["score"],
        "classification": row["classification"],
        "reasoning": row["reasoning"],
        "format_valid": row["format_valid"],
    }


def build_payload() -> dict:
    with (RESULTS_DIR / "scenario_comparison.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        scenarios = list(csv.DictReader(handle))

    judgments: dict[str, list[dict]] = {}
    for row in read_jsonl(RESULTS_DIR / "primary_judgments.jsonl"):
        judgments.setdefault(row["corpus_key"], []).append(compact_judgment(row))

    for row in scenarios:
        for key in (
            "candidate_1_score",
            "candidate_2_score",
            "reference_1_score",
            "reference_2_score",
            "reference_difference",
            "reference_score",
        ):
            row[key] = float(row[key]) if row[key] else None
        row["reference_resolved"] = row["reference_resolved"].lower() == "true"
        row["judgments"] = sorted(
            judgments[row["corpus_key"]],
            key=lambda item: (item["judge_role"] != "reference", item["judge_label"]),
        )

    analysis = json.loads((RESULTS_DIR / "analysis.json").read_text(encoding="utf-8"))
    return {
        "generated_at": analysis["generated_at"],
        "reference_coverage": analysis["reference_coverage"],
        "candidate_summary": analysis["candidate_summary"],
        "scenarios": scenarios,
    }


def main() -> None:
    payload = json.dumps(build_payload(), ensure_ascii=False).replace("</", "<\\/")
    html = TEMPLATE.replace("__EXPERIMENT_DATA__", payload)
    OUTPUT_PATH.write_text(html, encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH} ({OUTPUT_PATH.stat().st_size:,} bytes)")


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>HERON · Cross-family judge review</title>
  <style>
    :root {
      color-scheme: light;
      --ink: #17221d;
      --muted: #637069;
      --paper: #f4f1e9;
      --panel: #fffdf7;
      --line: #d8d3c5;
      --green: #195c46;
      --green-soft: #dcebe2;
      --amber: #9a541d;
      --amber-soft: #f7e6ce;
      --red: #9b3434;
      --red-soft: #f4dddd;
      --blue: #355d75;
      --shadow: 0 16px 42px rgba(39, 48, 41, .08);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background:
        radial-gradient(circle at 8% 2%, rgba(87, 130, 105, .12), transparent 25rem),
        var(--paper);
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    button, input, select, textarea { font: inherit; }
    button, select, input {
      border: 1px solid var(--line);
      background: var(--panel);
      color: var(--ink);
      border-radius: 10px;
    }
    button { cursor: pointer; }
    button:hover { border-color: var(--green); }
    .shell { width: min(1500px, calc(100% - 36px)); margin: 0 auto; }
    header { padding: 46px 0 28px; }
    .eyebrow {
      color: var(--green);
      font-size: .76rem;
      font-weight: 800;
      letter-spacing: .14em;
      text-transform: uppercase;
    }
    h1 {
      max-width: 860px;
      margin: 9px 0 10px;
      font-family: Georgia, "Times New Roman", serif;
      font-size: clamp(2.15rem, 5vw, 4.6rem);
      font-weight: 500;
      letter-spacing: -.045em;
      line-height: .98;
    }
    header p { max-width: 760px; margin: 0; color: var(--muted); line-height: 1.6; }
    .summary {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin: 25px 0 18px;
    }
    .stat {
      min-height: 116px;
      padding: 18px;
      border: 1px solid var(--line);
      border-radius: 16px;
      background: rgba(255, 253, 247, .78);
      box-shadow: var(--shadow);
    }
    .stat strong { display: block; margin-top: 9px; font-family: Georgia, serif; font-size: 2rem; font-weight: 500; }
    .stat small { color: var(--muted); line-height: 1.35; }
    .decision {
      display: flex;
      gap: 14px;
      align-items: flex-start;
      margin-bottom: 24px;
      padding: 16px 18px;
      border: 1px solid #d7b689;
      border-radius: 14px;
      background: var(--amber-soft);
    }
    .decision b { color: var(--amber); }
    .decision p { margin: 2px 0 0; color: #614b3b; line-height: 1.45; }
    .controls {
      position: sticky;
      top: 0;
      z-index: 10;
      display: grid;
      grid-template-columns: minmax(220px, 1fr) repeat(3, auto);
      gap: 9px;
      padding: 12px 0;
      background: rgba(244, 241, 233, .94);
      backdrop-filter: blur(12px);
    }
    .controls input, .controls select, .controls button { min-height: 44px; padding: 0 12px; }
    .workspace {
      display: grid;
      grid-template-columns: minmax(300px, 410px) minmax(0, 1fr);
      gap: 16px;
      align-items: start;
      padding-bottom: 50px;
    }
    .list, .detail {
      border: 1px solid var(--line);
      border-radius: 16px;
      background: var(--panel);
      box-shadow: var(--shadow);
    }
    .list { overflow: hidden; }
    .list-head {
      display: flex;
      justify-content: space-between;
      padding: 13px 15px;
      border-bottom: 1px solid var(--line);
      color: var(--muted);
      font-size: .82rem;
    }
    #scenarioList { max-height: calc(100vh - 95px); overflow: auto; }
    .scenario {
      display: block;
      width: 100%;
      padding: 15px;
      border: 0;
      border-bottom: 1px solid #ece8df;
      border-radius: 0;
      text-align: left;
      background: transparent;
    }
    .scenario:hover, .scenario.active { background: #eef3ee; }
    .scenario.active { box-shadow: inset 3px 0 var(--green); }
    .row-top { display: flex; justify-content: space-between; gap: 8px; margin-bottom: 7px; }
    .id { color: var(--muted); font-size: .75rem; font-weight: 750; text-transform: uppercase; letter-spacing: .05em; }
    .question-preview { display: -webkit-box; overflow: hidden; -webkit-box-orient: vertical; -webkit-line-clamp: 2; line-height: 1.38; }
    .chips { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
    .chip, .score {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 4px 7px;
      border-radius: 999px;
      font-size: .72rem;
      font-weight: 750;
      background: #eceae3;
    }
    .chip.resolved { color: var(--green); background: var(--green-soft); }
    .chip.ambiguous { color: var(--red); background: var(--red-soft); }
    .score { color: var(--blue); background: #e1ebf0; }
    .detail { min-height: 70vh; padding: clamp(20px, 3vw, 36px); }
    .detail h2 { margin: 9px 0 0; font-family: Georgia, serif; font-size: clamp(1.45rem, 3vw, 2.25rem); font-weight: 500; line-height: 1.2; }
    .detail h3 { margin: 30px 0 10px; font-size: .78rem; letter-spacing: .1em; text-transform: uppercase; }
    .response {
      padding: 20px;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: #faf8f1;
      white-space: pre-wrap;
      line-height: 1.58;
    }
    .judge-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
    .judge-card { padding: 16px; border: 1px solid var(--line); border-radius: 12px; }
    .judge-card.reference { border-top: 3px solid var(--green); }
    .judge-card.candidate { border-top: 3px solid var(--blue); }
    .judge-title { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; }
    .judge-title strong { font-size: .92rem; }
    .judge-meta { margin-top: 3px; color: var(--muted); font-size: .72rem; }
    .judge-card p { margin: 13px 0 0; color: #3e4943; line-height: 1.5; font-size: .88rem; }
    .notes {
      width: 100%;
      min-height: 110px;
      padding: 13px;
      border: 1px solid var(--line);
      border-radius: 10px;
      resize: vertical;
      background: #fff;
      color: var(--ink);
      line-height: 1.5;
    }
    .note-status { margin-top: 6px; min-height: 1em; color: var(--muted); font-size: .74rem; }
    .empty { padding: 50px 20px; color: var(--muted); text-align: center; }
    @media (max-width: 900px) {
      .summary { grid-template-columns: repeat(2, 1fr); }
      .controls { grid-template-columns: 1fr 1fr; }
      .workspace { grid-template-columns: 1fr; }
      #scenarioList { max-height: 430px; }
    }
    @media (max-width: 620px) {
      .shell { width: min(100% - 22px, 1500px); }
      header { padding-top: 30px; }
      .summary, .judge-grid, .controls { grid-template-columns: 1fr; }
      .stat { min-height: auto; }
    }
  </style>
</head>
<body>
  <header class="shell">
    <div class="eyebrow">HERON · 30 unique scenarios</div>
    <h1>Cross-family judge review</h1>
    <p>Inspect the frozen model responses and all four cross-family judgments. Reference disagreements are sorted to the top so ambiguous cases are easy to review.</p>
    <section class="summary" id="summary"></section>
    <aside class="decision">
      <div aria-hidden="true">◆</div>
      <div><b>Experiment decision</b><p>No cheap candidate passed every reliability threshold. Production therefore uses two strong, cross-family references and excludes cases where they differ by more than 0.15.</p></div>
    </aside>
  </header>

  <main class="shell">
    <section class="controls" aria-label="Review controls">
      <input id="search" type="search" placeholder="Search question or response…" aria-label="Search">
      <select id="family" aria-label="Target family">
        <option value="all">All target families</option>
        <option value="openai">OpenAI targets</option>
        <option value="google">Google targets</option>
        <option value="anthropic">Anthropic targets</option>
      </select>
      <select id="resolution" aria-label="Reference status">
        <option value="all">All reference states</option>
        <option value="ambiguous">Ambiguous only</option>
        <option value="resolved">Resolved only</option>
      </select>
      <button id="exportNotes" type="button">Export review notes</button>
    </section>

    <section class="workspace">
      <aside class="list">
        <div class="list-head"><span>Scenarios</span><span id="count"></span></div>
        <div id="scenarioList"></div>
      </aside>
      <article class="detail" id="detail"><div class="empty">Choose a scenario to begin reviewing.</div></article>
    </section>
  </main>

  <script id="experiment-data" type="application/json">__EXPERIMENT_DATA__</script>
  <script>
    const data = JSON.parse(document.getElementById("experiment-data").textContent);
    const state = { selected: null, filtered: [] };
    const $ = (id) => document.getElementById(id);
    const pct = (value) => `${(value * 100).toFixed(1)}%`;
    const score = (value) => value == null ? "—" : Number(value).toFixed(2);
    const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, char => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
    })[char]);
    const notesKey = (key) => `heron-review-note:${key}`;

    function renderSummary() {
      const coverage = data.reference_coverage;
      const ambiguous = Object.values(coverage).reduce((sum, item) => sum + item.ambiguous, 0);
      $("summary").innerHTML = `
        <div class="stat"><small>Frozen responses</small><strong>${data.scenarios.length}</strong><small>3 target families × 30 scenarios</small></div>
        <div class="stat"><small>Primary judgments</small><strong>${data.scenarios.length * 4}</strong><small>Four eligible judges per response</small></div>
        <div class="stat"><small>Resolved references</small><strong>${data.scenarios.length - ambiguous}/90</strong><small>Strong judges within 0.15</small></div>
        <div class="stat"><small>Same-family judgments</small><strong>0</strong><small>Family separation enforced</small></div>`;
    }

    function applyFilters() {
      const query = $("search").value.trim().toLowerCase();
      const family = $("family").value;
      const resolution = $("resolution").value;
      state.filtered = data.scenarios
        .filter(row => family === "all" || row.target_family === family)
        .filter(row => resolution === "all" || (resolution === "resolved") === row.reference_resolved)
        .filter(row => !query || `${row.question} ${row.target_response}`.toLowerCase().includes(query))
        .sort((a, b) => b.reference_difference - a.reference_difference || Number(a.question_id) - Number(b.question_id));
      if (!state.filtered.some(row => row.corpus_key === state.selected)) {
        state.selected = state.filtered[0]?.corpus_key ?? null;
      }
      renderList();
      renderDetail();
    }

    function renderList() {
      $("count").textContent = `${state.filtered.length} shown`;
      $("scenarioList").innerHTML = state.filtered.length ? state.filtered.map(row => `
        <button class="scenario ${row.corpus_key === state.selected ? "active" : ""}" data-key="${escapeHtml(row.corpus_key)}">
          <div class="row-top"><span class="id">Q${escapeHtml(row.question_id)} · ${escapeHtml(row.target_family)}</span><span class="score">Δ ${score(row.reference_difference)}</span></div>
          <div class="question-preview">${escapeHtml(row.question)}</div>
          <div class="chips"><span class="chip ${row.reference_resolved ? "resolved" : "ambiguous"}">${row.reference_resolved ? "reference resolved" : "reference ambiguous"}</span></div>
        </button>`).join("") : `<div class="empty">No scenarios match these filters.</div>`;
      document.querySelectorAll(".scenario").forEach(button => button.addEventListener("click", () => {
        state.selected = button.dataset.key;
        renderList();
        renderDetail();
      }));
    }

    function renderDetail() {
      const row = data.scenarios.find(item => item.corpus_key === state.selected);
      if (!row) {
        $("detail").innerHTML = `<div class="empty">No scenario selected.</div>`;
        return;
      }
      const judges = row.judgments.map(judge => `
        <section class="judge-card ${escapeHtml(judge.judge_role)}">
          <div class="judge-title">
            <div><strong>${escapeHtml(judge.judge_label)}</strong><div class="judge-meta">${escapeHtml(judge.judge_role)} · ${escapeHtml(judge.judge_reasoning)} reasoning · ${escapeHtml(judge.classification)}</div></div>
            <span class="score">${score(judge.score)}</span>
          </div>
          <p>${escapeHtml(judge.reasoning)}</p>
        </section>`).join("");
      $("detail").innerHTML = `
        <div class="eyebrow">Question ${escapeHtml(row.question_id)} · ${escapeHtml(row.target_model)}</div>
        <h2>${escapeHtml(row.question)}</h2>
        <div class="chips">
          <span class="chip ${row.reference_resolved ? "resolved" : "ambiguous"}">${row.reference_resolved ? "reference resolved" : "reference ambiguous"}</span>
          <span class="score">reference Δ ${score(row.reference_difference)}</span>
          <span class="score">reference score ${score(row.reference_score)}</span>
        </div>
        <h3>Frozen target response</h3>
        <div class="response">${escapeHtml(row.target_response)}</div>
        <h3>Judge assessments</h3>
        <div class="judge-grid">${judges}</div>
        <h3>Your qualitative notes</h3>
        <textarea class="notes" id="notes" placeholder="Record whether the judgments are persuasive, what seems missed, and which judge—if any—looks like an outlier.">${escapeHtml(localStorage.getItem(notesKey(row.corpus_key)) || "")}</textarea>
        <div class="note-status" id="noteStatus">Notes save locally in this browser.</div>`;
      let timer;
      $("notes").addEventListener("input", event => {
        clearTimeout(timer);
        timer = setTimeout(() => {
          localStorage.setItem(notesKey(row.corpus_key), event.target.value);
          $("noteStatus").textContent = "Saved locally.";
        }, 250);
      });
    }

    function exportNotes() {
      const notes = data.scenarios.flatMap(row => {
        const note = localStorage.getItem(notesKey(row.corpus_key));
        return note ? [{
          corpus_key: row.corpus_key,
          question_id: row.question_id,
          target_family: row.target_family,
          reference_difference: row.reference_difference,
          note
        }] : [];
      });
      const blob = new Blob([JSON.stringify(notes, null, 2)], { type: "application/json" });
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = "heron-qualitative-review-notes.json";
      link.click();
      URL.revokeObjectURL(link.href);
    }

    ["search", "family", "resolution"].forEach(id => $(id).addEventListener(id === "search" ? "input" : "change", applyFilters));
    $("exportNotes").addEventListener("click", exportNotes);
    renderSummary();
    applyFilters();
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
