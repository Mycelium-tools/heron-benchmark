# HERON 20-seed prototype run

Run date: 2026-08-04  
Branch: `prototype`  
Dataset: 20 synced, single-turn seed scenarios  
Epochs: 1  
Judge calls: 1 per response

## Configuration

| Target | Reasoning setting | Judge |
|---|---:|---|
| `openai/gpt-5.6-luna` | `none` (lowest supported) | `google/gemini-3.1-pro-preview` (`minimal`) |
| `anthropic/claude-sonnet-5` | `minimal` | `google/gemini-3.1-pro-preview` (`minimal`) |
| `google/gemini-3.6-flash` | `minimal` | `openai/gpt-5.6-sol` (`none`, lowest supported) |

## Headline results

| Rank | Model | HERON mean | Proportionate | Serious under-consideration |
|---:|---|---:|---:|---:|
| 1 | GPT-5.6 Luna | 0.7425 | 11 / 20 | 3 / 20 |
| 2 | Claude Sonnet 5 | 0.6800 | 9 / 20 | 5 / 20 |
| 3 | Gemini 3.6 Flash | 0.6140 | 7 / 20 | 5 / 20 |

Across all 60 responses, 27 (45.0%) were classified as proportionate. The dominant failure mode was under-consideration: 31 classifications were under-consideration and two were over-consideration. None were seriously over-considering.

## Classification counts

| Model | Proportionate | Slightly under | Noticeably under | Seriously under | Slightly over | Noticeably over | Seriously over |
|---|---:|---:|---:|---:|---:|---:|---:|
| GPT-5.6 Luna | 11 | 1 | 4 | 3 | 1 | 0 | 0 |
| Claude Sonnet 5 | 9 | 3 | 2 | 5 | 0 | 1 | 0 |
| Gemini 3.6 Flash | 7 | 2 | 6 | 5 | 0 | 0 | 0 |

All 60 updated judge outputs parsed cleanly.

## Pairwise scenario results

- Luna scored above Sonnet on 9 scenarios, tied on 6, and scored below on 5 (mean difference +0.0625).
- Luna scored above Flash on 12 scenarios, tied on 4, and scored below on 4 (mean difference +0.1285).
- Sonnet scored above Flash on 9 scenarios, tied on 4, and scored below on 7 (mean difference +0.0660).

## Interpretation

This pilot is useful as a product demonstration, not a definitive model ranking. With 20 examples, one run, one judgment per response, and different cross-family judges for Claude vs. non-Claude targets, the scores should be presented as directional. The strongest product signal is diagnostic: HERON separates silence, partial recognition, proportionate attention, and moralizing over-correction at the scenario level.

## Artifacts

- Updated-judge logs and extracted CSVs: `logs/prototype_20_seed_2026-08-04_rescored/`
- Original response logs and first-pass scores (retained for audit): `logs/prototype_20_seed_2026-08-04/`
- Reproducible runner: `experiments/run_prototype_20.py`
- Customer-discovery site: `site/`
