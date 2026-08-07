# WildChat mining — empirical priors for HERON scenario design

Mines real user messages from [`allenai/WildChat-4.8M`](https://huggingface.co/datasets/allenai/WildChat-4.8M)
(ungated, ODC-BY) to replace judgment calls in HERON's scenario design with measured
distributions: which contexts animal-stake conversations occur in, personal-vs-work
framing, salience (explicit / incidental / absent), plus an exemplar pool of real user
phrasing and an empirical word-count target for `LENGTH_DIRECTIVES`.

## Pipeline

Three stages; each writes files to `out/` and the next stage reads them, so you can
inspect between stages. Run everything from the repo root.

```bash
# Stage 1 — stream + keyword prefilter (smoke test first, then full)
python experiments/wildchat/stage1_extract.py --max-scan 5000     # smoke
python experiments/wildchat/stage1_extract.py                     # 300k scan / 3000 hits

# Stage 2 — LLM classification (Haiku 4.5)
python experiments/wildchat/stage2_classify.py --limit 20         # smoke
python experiments/wildchat/stage2_classify.py                    # Phase A: 800 sample
python experiments/wildchat/stage2_classify.py --extend           # Phase B: all remaining
python experiments/wildchat/stage2_classify.py --reliability      # 100 rows vs Sonnet 5

# Stage 3 — report
python experiments/wildchat/stage3_report.py
```

## Outputs (`out/`)

| File | What |
|---|---|
| `report.md` | Primary deliverable: base rate per 10k, distributions with Wilson CIs, word-count histograms, caveats |
| `distributions.json` | Same numbers, machine-readable |
| `exemplars.txt` | Up to 50 stake-bearing messages verbatim, grouped by context |
| `prefiltered.jsonl` | Stage-1 keyword hits (gitignored) |
| `classified.jsonl` | Stage-2 classifications, resumable/appendable (gitignored) |
| `stage1_stats.json` | Scan denominators for the base rate |
| `reliability.jsonl` | Haiku-vs-Sonnet double annotations (gitignored) |

## Design decisions

- **First user turn only** — that's what a HERON scenario models.
- **Multilingual**: all languages kept. Keyword lists are per-language and applied
  conditionally on the row's `language` field (prevents collisions like French
  "chat" or English "python"/"mouse"). Top ~7 languages have translated lists;
  others get English-only coverage (reported as a scope limit).
- **Fiction excluded**: creative-writing/roleplay requests are flagged
  (`is_fiction`) and forced to `has_welfare_stake=false` — tracked, not analyzed.
- **Streaming shuffle** (seed 42) — the dataset is roughly chronological.
- **Dedup** on normalized first-turn text (WildChat has heavy repeat-prompt spam).
- **Truncation**: classifier sees the first 2,000 chars; word-count stats use full text.
- Keyword tiers live in `keywords.py`: Tier A (unambiguous, on) / Tier B
  (ambiguous — `mouse`, `bug`, `cat`… — off by default, promote after eyeballing
  hits with `--tier-b`).
- Stage 2 reuses `generate_structured_responses_with_threadpool` from
  `dataset/scenario_generation.py` (instructor + pydantic + retry stack).

## Caveats when reading results

The salience distribution is censored by the keyword sampling frame
(`animal_absent` messages mostly can't match a keyword); WildChat is 2023–24
ChatGPT opt-in users, not a random LLM-user sample; and `has_welfare_stake` is a
classifier judgment — see the reliability section of the report. Strong prior,
not ground truth.
