"use client";

import { useMemo, useState } from "react";

export type EvaluationRow = {
  sampleId: number;
  prompt: string;
  model: string;
  modelLabel: string;
  response: string;
  score: number;
  classification: string;
  judge: string;
  judgeLabel: string;
  judgeExplanation: string;
  judgeResponse: string;
  judgeFormatValid: boolean;
};

type Scenario = {
  id: number;
  prompt: string;
  rows: EvaluationRow[];
};

function readableClassification(value: string) {
  return value.toLowerCase().replace(/(^|\s)\S/g, (letter) => letter.toUpperCase());
}

function classificationTone(value: string) {
  if (value === "PROPORTIONATE") return "proportionate";
  if (value.includes("OVER")) return "over";
  return "under";
}

function score100(score: number) {
  return Math.round(score * 100);
}

export default function ExplorerClient({ rows }: { rows: EvaluationRow[] }) {
  const scenarios = useMemo<Scenario[]>(() => {
    const grouped = new Map<number, Scenario>();
    for (const row of rows) {
      const scenario = grouped.get(row.sampleId) ?? { id: row.sampleId, prompt: row.prompt, rows: [] };
      scenario.rows.push(row);
      grouped.set(row.sampleId, scenario);
    }
    return [...grouped.values()].sort((a, b) => a.id - b.id);
  }, [rows]);

  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState(scenarios[0]?.id ?? 0);
  const [selectedModel, setSelectedModel] = useState(scenarios[0]?.rows[0]?.model ?? "");

  const filtered = scenarios.filter((scenario) =>
    scenario.prompt.toLowerCase().includes(query.trim().toLowerCase()),
  );
  const selectedScenario = scenarios.find((scenario) => scenario.id === selectedId) ?? scenarios[0];
  const selectedRow = selectedScenario.rows.find((row) => row.model === selectedModel) ?? selectedScenario.rows[0];

  function selectScenario(scenario: Scenario) {
    setSelectedId(scenario.id);
    setSelectedModel(scenario.rows[0].model);
  }

  function moveScenario(offset: number) {
    const index = scenarios.findIndex((scenario) => scenario.id === selectedScenario.id);
    const next = scenarios[Math.min(Math.max(index + offset, 0), scenarios.length - 1)];
    selectScenario(next);
  }

  return (
    <section className="explorer-shell">
      <aside className="scenario-sidebar" aria-label="Scenarios">
        <label htmlFor="scenario-search">Search scenarios</label>
        <input
          id="scenario-search"
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Try ‘glue traps’ or ‘skincare’"
        />
        <div className="scenario-count">{filtered.length} of {scenarios.length} scenarios</div>
        <div className="scenario-list">
          {filtered.map((scenario) => (
            <button
              className={scenario.id === selectedScenario.id ? "active" : ""}
              key={scenario.id}
              type="button"
              onClick={() => selectScenario(scenario)}
            >
              <span>Seed {String(scenario.id).padStart(2, "0")}</span>
              <strong>{scenario.prompt}</strong>
              <small>
                {scenario.rows.map((row) => (
                  <i className={classificationTone(row.classification)} key={row.model}>{score100(row.score)}</i>
                ))}
              </small>
            </button>
          ))}
          {filtered.length === 0 && <p className="empty-search">No scenario matches that search.</p>}
        </div>
      </aside>

      <div className="evaluation-panel">
        <div className="evaluation-prompt">
          <div className="evaluation-kicker">
            <span>Seed {String(selectedScenario.id).padStart(2, "0")}</span>
            <div>
              <button type="button" onClick={() => moveScenario(-1)} disabled={selectedScenario.id === scenarios[0].id} aria-label="Previous scenario">←</button>
              <button type="button" onClick={() => moveScenario(1)} disabled={selectedScenario.id === scenarios.at(-1)?.id} aria-label="Next scenario">→</button>
            </div>
          </div>
          <h2>{selectedScenario.prompt}</h2>
        </div>

        <div className="model-tabs" role="tablist" aria-label="Model responses">
          {selectedScenario.rows.map((row) => (
            <button
              aria-selected={row.model === selectedRow.model}
              className={row.model === selectedRow.model ? "active" : ""}
              key={row.model}
              onClick={() => setSelectedModel(row.model)}
              role="tab"
              type="button"
            >
              <span>{row.modelLabel}</span>
              <b>{score100(row.score)}</b>
              <small className={classificationTone(row.classification)}>{readableClassification(row.classification)}</small>
            </button>
          ))}
        </div>

        <div className="evaluation-detail">
          <article className="full-response">
            <header><span>Model response</span><strong>{selectedRow.modelLabel}</strong></header>
            <div>{selectedRow.response}</div>
          </article>

          <aside className="judge-evaluation">
            <div className="judge-score">
              <p><span>HERON score</span><b>{score100(selectedRow.score)}</b></p>
              <p><span>Classification</span><strong className={classificationTone(selectedRow.classification)}>{readableClassification(selectedRow.classification)}</strong></p>
            </div>
            <div className="judge-rationale">
              <span>Judge rationale</span>
              <h3>{selectedRow.judgeLabel}</h3>
              <p>{selectedRow.judgeExplanation}</p>
            </div>
            <details>
              <summary>View raw judge output</summary>
              <pre>{selectedRow.judgeResponse}</pre>
            </details>
          </aside>
        </div>
      </div>
    </section>
  );
}
