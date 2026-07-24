# Paired old-vs-proportionality judge experiment

This experiment generates each Gemini answer once, then scores that same frozen
one-turn response with two prompts:

- `heron_old_prompt_scorer`: the existing moral-sensitivity prompt, frozen for
  this experiment.
- `heron_proportionality_scorer`: the new symmetric proportionality prompt.

Both scorers use `openai/gpt-5.6-terra` with temperature 0. The experiment
requires exactly 24 questions, unique non-empty IDs, and blank `turn2` values.

## 1. Sync and validate the current Google Sheet

The current published CSV URL is configured in `sync_questions_to_hf.py`. If
the published link changes again, it can be overridden without editing code by
adding it to `.env`:

```bash
GOOGLE_SHEETS_URL="https://docs.google.com/spreadsheets/d/e/.../pub?gid=...&single=true&output=csv"
```

Then sync, requiring all 24 rows:

```bash
python sync_questions_to_hf.py --expected-count 24
```

The sync now stops before uploading or regenerating `samples.json` if IDs or
questions are blank, IDs are duplicated, or the row count is not 24.

## 2. Run the five-question smoke test

```bash
inspect eval src/heron/paired_eval.py@heron_paired_test5 \
  --model google/gemini-3.1-pro-preview \
  --log-dir logs/paired_judge_smoke
```

Confirm that all five samples succeed and contain both score keys:

- `heron_old_prompt_scorer`
- `heron_proportionality_scorer`

The new scorer should also contain a valid `classification` and both scorers
should report `openai/gpt-5.6-terra` as `judge_model`.

Generate the side-by-side review page:

```bash
python analysis/render_paired_judgments.py \
  logs/paired_judge_smoke/YOUR_SMOKE_LOG.eval
```

The generated HTML shows the scenario and Gemini response first. Human
annotations can be entered before revealing the two judgments. Annotations are
saved in browser local storage and can be exported as JSON.

## 3. Run the full experiment

After the smoke test passes:

```bash
inspect eval src/heron/paired_eval.py@heron_paired_full \
  --model google/gemini-3.1-pro-preview \
  --log-dir logs/paired_judge_full
```

Then generate its review page:

```bash
python analysis/render_paired_judgments.py \
  logs/paired_judge_full/YOUR_FULL_LOG.eval
```

To produce a CSV containing both judgments:

```bash
python analysis/extract_eval_csvs.py \
  --run-dir logs/paired_judge_full
```
