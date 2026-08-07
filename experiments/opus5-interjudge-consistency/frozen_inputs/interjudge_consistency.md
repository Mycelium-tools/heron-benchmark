# Opus 5 Inter-Judge Consistency Experiment

## Goal

Run Opus 5 on the full HERON dataset, then test whether smaller judge models
give the same score to its answer on each scenario. If the judges generally
agree, HERON may be able to use a cheaper judge without losing reliability.

## Fixed inputs

- Use the full HERON dataset.
- Generate one frozen corpus of Opus 5 conversations using the supplied Bedrock
  Converse endpoint and model ID:
  `us.anthropic.claude-opus-5`.
- Judge the exact same Opus conversation and reference answer with every judge.
  Do not regenerate Opus responses between judges.
- Freeze the dataset revision, response corpus, scorer prompt, score parser, and
  inference settings.
- Do not alter the current HERON judge prompt for this experiment.

## Judges and staged design

### Stage 1: Gemini judges

Score every frozen Opus conversation with:

1. `gemini-3.6-flash`
2. `gemini-3.1-pro-preview`

### Stage 2: conditional OpenAI judges

If the Gemini judges disagree enough to make their scores unreliable, score the
same conversations with:

3. `gpt-5.6-luna`
4. `gpt-5.6-sol`

When Stage 2 is triggered, run both OpenAI judges on the full frozen corpus.

## What to compare

Create one row per scenario containing:

- question ID;
- Opus 5 response;
- score and explanation from each judge;
- absolute score difference between the two Gemini judges; and
- question metadata useful for reviewing disagreements.

Sort or filter the table so the largest disagreements are easy to inspect.
Also report these simple summary numbers:

- number and percentage of scenarios with the same score;
- number and percentage within 0.15;
- number and percentage differing by more than 0.15; and
- average absolute score difference.

## Proposed trigger for Stage 2

Run Luna and Sol if the Gemini judges differ by more than 0.15 on more than 10%
of scenarios. Regardless of the overall rate, include Luna and Sol for every
individual scenario where the Gemini difference is greater than 0.15.

This is a proposed practical definition of “high enough variation” and should
be confirmed before the run.

## Interpretation

If Gemini Flash and Gemini Pro usually give the same or very similar
per-scenario scores, the cheaper model is a plausible replacement judge. If
they disagree frequently, Luna and Sol show whether the scenario itself draws
mixed judgments or whether one Gemini judge is the outlier.

Agreement alone cannot prove which score is objectively correct. Any claim
about judge quality, rather than judge consistency, would require manual review
of the disagreement cases.

## Deliverables

- Frozen full-dataset Opus 5 response corpus
- Raw judge outputs
- One scenario-by-scenario comparison table
- Short agreement summary and disagreement list
- Judge cost comparison
