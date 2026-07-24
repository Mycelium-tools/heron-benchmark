"""
Render a paired-judge .eval log as a self-contained qualitative review page.

Usage:
    python analysis/render_paired_judgments.py path/to/run.eval
    python analysis/render_paired_judgments.py path/to/run.eval --output review.html
"""

import argparse
import json
from pathlib import Path

from inspect_ai.log import read_eval_log

OLD_KEY = "heron_old_prompt_scorer"
NEW_KEY = "heron_proportionality_scorer"


def score_data(sample, key: str) -> dict:
    score = sample.scores.get(key) if sample.scores else None
    if not score:
        return {}
    return {
        "score": score.value,
        "explanation": score.explanation or "",
        "judge_model": score.metadata.get("judge_model", ""),
        "prompt_version": score.metadata.get("prompt_version", ""),
        "judge_response": score.metadata.get("judge_response", ""),
        "classification": score.metadata.get("classification", ""),
        "format_valid": score.metadata.get("format_valid"),
    }


def sample_data(sample) -> dict:
    old = score_data(sample, OLD_KEY)
    new = score_data(sample, NEW_KEY)
    old_value = old.get("score")
    new_value = new.get("score")
    delta = (
        round(new_value - old_value, 3)
        if isinstance(old_value, (int, float)) and isinstance(new_value, (int, float))
        else None
    )
    return {
        "id": str(sample.id),
        "question": sample.input
        if isinstance(sample.input, str)
        else str(sample.input),
        "response": sample.output.completion if sample.output else "",
        "old": old,
        "new": new,
        "delta": delta,
    }


def render_html(log_path: Path) -> str:
    log = read_eval_log(str(log_path))
    if not log.samples:
        raise ValueError(f"No samples found in {log_path}")

    rows = [sample_data(sample) for sample in log.samples]
    missing = [row["id"] for row in rows if not row["old"] or not row["new"]]
    if missing:
        raise ValueError(
            "This is not a complete paired-judge log. Missing old or new scores "
            f"for sample IDs: {missing}"
        )

    payload = json.dumps(
        {
            "log": str(log_path),
            "model": log.eval.model,
            "created": str(log.eval.created),
            "samples": rows,
        },
        ensure_ascii=False,
    ).replace("</", "<\\/")

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>HERON paired-judge review</title>
<style>
:root {{
  color-scheme: light;
  --ink: #19231f;
  --muted: #66736d;
  --paper: #f4f1e8;
  --card: #fffdf7;
  --line: #d8d3c5;
  --old: #355e73;
  --new: #7a4e2d;
  --accent: #1f6b55;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  background: var(--paper);
  color: var(--ink);
  font: 16px/1.5 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}}
header {{
  position: sticky;
  top: 0;
  z-index: 2;
  padding: 18px max(24px, calc((100vw - 1200px) / 2));
  background: rgba(244, 241, 232, .96);
  border-bottom: 1px solid var(--line);
  backdrop-filter: blur(8px);
}}
h1 {{ margin: 0 0 4px; font: 700 24px/1.2 Georgia, serif; }}
.meta, .subtle {{ color: var(--muted); font-size: 14px; }}
.toolbar {{ display: flex; gap: 10px; flex-wrap: wrap; margin-top: 14px; }}
button, select, input, textarea {{
  font: inherit;
  border: 1px solid var(--line);
  border-radius: 7px;
  background: white;
  color: var(--ink);
}}
button {{ cursor: pointer; padding: 8px 12px; }}
button.primary {{ background: var(--accent); color: white; border-color: var(--accent); }}
select, input {{ padding: 7px 9px; }}
main {{ max-width: 1200px; margin: 24px auto 80px; padding: 0 24px; }}
.sample {{
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 12px;
  margin: 0 0 22px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(38, 43, 39, .04);
}}
.sample-head {{
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 18px;
  border-bottom: 1px solid var(--line);
}}
.content {{ padding: 18px; }}
h2, h3 {{ margin: 0 0 10px; }}
h2 {{ font-size: 17px; }}
h3 {{ font-size: 14px; text-transform: uppercase; letter-spacing: .04em; }}
.text {{
  white-space: pre-wrap;
  background: white;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 14px;
  margin-bottom: 18px;
}}
.human {{
  display: grid;
  grid-template-columns: 1fr 140px;
  gap: 10px;
  padding: 14px;
  border: 1px dashed #9da99f;
  border-radius: 8px;
  margin-bottom: 16px;
}}
.human textarea {{ grid-column: 1 / -1; min-height: 76px; padding: 9px; resize: vertical; }}
.judges {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }}
.judge {{ border: 1px solid var(--line); border-top-width: 5px; border-radius: 8px; padding: 14px; }}
.judge.old {{ border-top-color: var(--old); }}
.judge.new {{ border-top-color: var(--new); }}
.score {{ font-size: 25px; font-weight: 750; }}
.badge {{
  display: inline-block;
  margin-left: 8px;
  padding: 3px 7px;
  border-radius: 999px;
  background: #eee9dc;
  font-size: 12px;
  vertical-align: middle;
}}
.raw {{ margin-top: 12px; }}
.raw pre {{ white-space: pre-wrap; font: 13px/1.45 ui-monospace, monospace; }}
.hidden {{ display: none; }}
@media (max-width: 780px) {{
  .judges, .human {{ grid-template-columns: 1fr; }}
  .human textarea {{ grid-column: 1; }}
}}
</style>
</head>
<body>
<header>
  <h1>HERON paired-judge review</h1>
  <div class="meta" id="run-meta"></div>
  <div class="toolbar">
    <select id="classification-filter">
      <option value="">All new classifications</option>
    </select>
    <button id="reveal-all">Reveal all judgments</button>
    <button id="hide-all">Hide all judgments</button>
    <button class="primary" id="export">Export human annotations</button>
  </div>
</header>
<main id="samples"></main>
<script>
const DATA = {payload};
const storageKey = "heron-review:" + DATA.log;
let annotations = JSON.parse(localStorage.getItem(storageKey) || "{{}}");
const classes = [
  "SERIOUSLY UNDER", "NOTICEABLY UNDER", "SLIGHTLY UNDER", "PROPORTIONATE",
  "SLIGHTLY OVER", "NOTICEABLY OVER", "SERIOUSLY OVER"
];
const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({{
  "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
}}[c]));
document.getElementById("run-meta").textContent =
  `${{DATA.model}} · ${{DATA.samples.length}} samples · ${{DATA.created}}`;
const filter = document.getElementById("classification-filter");
classes.forEach(value => filter.insertAdjacentHTML(
  "beforeend", `<option value="${{value}}">${{value}}</option>`
));
function annotation(id) {{
  return annotations[id] || {{ classification: "", score: "", notes: "" }};
}}
function save(id, field, value) {{
  annotations[id] = {{...annotation(id), [field]: value}};
  localStorage.setItem(storageKey, JSON.stringify(annotations));
}}
function judgePanel(kind, data) {{
  const title = kind === "old" ? "Old consideration prompt" : "New proportionality prompt";
  const badge = data.classification ? `<span class="badge">${{esc(data.classification)}}</span>` : "";
  return `<section class="judge ${{kind}}">
    <h3>${{title}}</h3>
    <div><span class="score">${{Number(data.score).toFixed(2)}}</span>${{badge}}</div>
    <p>${{esc(data.explanation)}}</p>
    <div class="subtle">${{esc(data.judge_model)}} · ${{esc(data.prompt_version)}} ·
      format ${{data.format_valid ? "valid" : "invalid"}}</div>
    <details class="raw"><summary>Raw judge response</summary>
      <pre>${{esc(data.judge_response)}}</pre>
    </details>
  </section>`;
}}
function render() {{
  const selected = filter.value;
  const visible = DATA.samples.filter(row => !selected || row.new.classification === selected);
  document.getElementById("samples").innerHTML = visible.map(row => {{
    const a = annotation(row.id);
    const options = ['<option value="">Human classification…</option>']
      .concat(classes.map(c => `<option ${{a.classification === c ? "selected" : ""}}>${{c}}</option>`))
      .join("");
    const delta = row.delta === null ? "n/a" : `${{row.delta >= 0 ? "+" : ""}}${{row.delta.toFixed(2)}}`;
    return `<article class="sample" data-id="${{esc(row.id)}}">
      <div class="sample-head"><strong>Sample ${{esc(row.id)}}</strong>
        <span class="subtle">new − old: ${{delta}}</span></div>
      <div class="content">
        <h2>User request</h2><div class="text">${{esc(row.question)}}</div>
        <h2>Model response</h2><div class="text">${{esc(row.response)}}</div>
        <h2>Your judgment</h2>
        <div class="human">
          <select data-field="classification">${{options}}</select>
          <input data-field="score" type="number" min="0" max="1" step=".05"
            value="${{esc(a.score)}}" placeholder="Human score">
          <textarea data-field="notes" placeholder="Reasoning or notes…">${{esc(a.notes)}}</textarea>
        </div>
        <button class="reveal">Reveal judgments</button>
        <div class="judges hidden">${{judgePanel("old", row.old)}}${{judgePanel("new", row.new)}}</div>
      </div>
    </article>`;
  }}).join("");
  document.querySelectorAll("[data-field]").forEach(input => {{
    input.addEventListener("change", event => {{
      const article = event.target.closest(".sample");
      save(article.dataset.id, event.target.dataset.field, event.target.value);
    }});
  }});
  document.querySelectorAll(".reveal").forEach(button => button.addEventListener("click", event => {{
    const judges = event.target.nextElementSibling;
    judges.classList.toggle("hidden");
    event.target.textContent = judges.classList.contains("hidden") ? "Reveal judgments" : "Hide judgments";
  }}));
}}
filter.addEventListener("change", render);
document.getElementById("reveal-all").onclick = () =>
  document.querySelectorAll(".judges").forEach(node => node.classList.remove("hidden"));
document.getElementById("hide-all").onclick = () =>
  document.querySelectorAll(".judges").forEach(node => node.classList.add("hidden"));
document.getElementById("export").onclick = () => {{
  const blob = new Blob([JSON.stringify({{
    log: DATA.log, model: DATA.model, annotations
  }}, null, 2)], {{type: "application/json"}});
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "heron-human-annotations.json";
  link.click();
  URL.revokeObjectURL(link.href);
}};
render();
</script>
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("eval_log", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    output = args.output or args.eval_log.with_name(
        f"{args.eval_log.stem}_paired_review.html"
    )
    output.write_text(render_html(args.eval_log), encoding="utf-8")
    print(f"Wrote paired review: {output}")


if __name__ == "__main__":
    main()
