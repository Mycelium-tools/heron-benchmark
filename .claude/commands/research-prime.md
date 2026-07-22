# Research Context Prime
> Load full HERON project context before doing any work.

## Read these first (in parallel)
- `CLAUDE.md` — project overview, schema, dimensions, workflows, conventions
- `README.md` — what HERON is + the canonical silkworm example
- `pyproject.toml` — deps and package layout
- `src/heron/eval.py` — tasks, dataset loading, log routing, MODELS
- `src/heron/solver.py` — 1–2 turn static conversation
- `src/heron/scorer.py` — dimensions, judge, reference-anchored scoring
- `dataset/heron_questions.csv` — current question set

## Structure
```bash
find . -type f \( -name "*.py" -o -name "*.md" -o -name "*.csv" -o -name "*.toml" \) \
  -not -path "*/.venv/*" -not -path "*/__pycache__/*" | sort
```

## Key conventions
1. **Never edit `samples.json` directly** — it's generated. Edit the Google Sheet (or `dataset/heron_questions.csv`) then run the sync.
2. **Flag scorer-prompt changes before making them** — they affect all eval results.
3. Reference answers are the grading key — every accuracy question should have one.
4. Keep changes minimal; read existing code before changing it.
