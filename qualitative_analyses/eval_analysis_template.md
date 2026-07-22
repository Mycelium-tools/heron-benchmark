# HERON Eval Analysis Report

> Template — copy to `eval_analysis_YYYY-MM-DD_<label>.md` and fill in.
> Metadata below comes from the `.eval` log header (`inspect view` or `read_eval_log`);
> per-sample rows can be generated with `python analysis/extract_eval_csvs.py --run-dir <dir>`.

**Date:**
**Log file:** `<file>.eval`
**Task function:** `heron_full()` / `heron_test5()`
**Model:**
**Judge:** (from scorer metadata — GPT for Claude targets, Claude otherwise)
**Scorer:** `heron_scorer` (Moral Sensitivity, 0.0–1.0)
**inspect_ai version:**
**Run duration:**
**Git commit:**

---

## Scenarios Evaluated

N samples from `samples.json`:

| ID | Scenario Summary | Score |
|----|-----------------|-------|
| 0 | | |
| 1 | | |

**Mean score:**
**Min:** (ID )
**Max:** (ID )

---

## Quantitative Summary

- Score distribution (how many in 0.0–0.3 / 0.4–0.5 / 0.6–0.7 / 0.8–1.0 bands)
- Any clustering by scenario domain (pest control, food business, labeling, hunting, …)

### Token Usage

| | Input | Output | Total |
|---|---|---|---|
| Target model | | | |

---

## Key Findings

### 1.

### 2.

### 3.

---

## Judge Calibration Analysis

For each sample where your own read disagrees with the judge, record it here —
these disagreements are what drive rubric revisions (see CLAUDE.md scoring section
for the July 2026 revision that came out of exactly this exercise).

| ID | Judge score | My score | Why |
|----|------------|----------|-----|
| | | | |

Failure-mode checklist per disagreement:
- Vocabulary-only response over-credited? (substance-over-vocabulary rule)
- Central accuracy-framed welfare pushback under-credited? (framing-rationale rule)
- Moralizing response over-credited? (proportionality cap)
- Passing branding mention over-credited? (central-vs-passing rule)

---

## Notable Individual Performances

### Best: ID — (score)

### Worst: ID — (score)

### Most Interesting: ID — (score)

---

## Discrepancies & Flags

(Anything odd: refusals, empty responses, judge parse failures, samples that
should be reworded or dropped from the question set.)

---

## Recommendations

1.
