# Cross-Family Judge Selection Experiment

## Goal

Choose an inexpensive main judge and backup judge for each evaluated model
family.

The central rule is:

> A model must never judge a response produced by a model from its own family.

The experiment measures which inexpensive judge best matches stronger judges
from the two other model families. It measures consistency with those judges,
not objective correctness.

## Dataset

- Use the revised 30-scenario HERON dataset.
- Confirm that all 30 questions are unique before the run.
- Freeze the dataset revision and hash.
- Do not change the HERON judge prompt or score parser.
- The current reference-answer fields are empty. Keep them identical for every
  judge and record this limitation.

## Frozen response corpus

Generate one response for every scenario from one strong model in each family:

| Family | Response model | Reasoning |
|---|---|---|
| OpenAI | GPT-5.6 Sol | `none` |
| Google | Gemini 3.1 Pro Preview | `low` |
| Anthropic | Claude Opus 5 | `low` |

This produces 90 frozen responses: 30 scenarios × 3 response models.

Generate each response once. All judges must score the exact same frozen
response. Do not regenerate responses between judges.

Freeze and record all model IDs, provider endpoints, prompts, output limits,
reasoning settings, and response hashes.

## Judges

### Inexpensive candidates

| Family | Candidate judge | Reasoning |
|---|---|---|
| Google | Gemini 3.6 Flash | `minimal` |
| Anthropic | Claude Sonnet 5 | `low` |
| OpenAI | GPT-5.6 Luna | `none` |

### Strong reference judges

| Family | Reference judge | Reasoning |
|---|---|---|
| Google | Gemini 3.1 Pro Preview | `medium` |
| Anthropic | Claude Opus 5 | `medium` |
| OpenAI | GPT-5.6 Sol | `medium` |

The reference judges use more reasoning because they replace human
adjudication. Candidate judges use their lowest supported reasoning level
because that is the intended production configuration.

## Judge routing

Every response is scored by the two inexpensive candidates and two strong
reference judges from the other families:

| Response family | Inexpensive candidates | Strong references | Excluded family |
|---|---|---|---|
| OpenAI | Gemini Flash, Claude Sonnet | Gemini Pro, Claude Opus | OpenAI |
| Google | Claude Sonnet, GPT Luna | Claude Opus, GPT Sol | Google |
| Anthropic | Gemini Flash, GPT Luna | Gemini Pro, GPT Sol | Anthropic |

No same-family judgment is allowed.

Judges must not be told which model produced a response. Randomize the order of
responses separately for each judge.

The primary run contains 360 judgments:

- 90 frozen responses;
- 4 eligible judges per response; and
- 0 same-family judgments.

## Reference score

Each response has two eligible strong reference scores.

1. If the two reference scores differ by no more than 0.15, call the response
   **reference-resolved**.
2. For a reference-resolved response, use the mean of the two reference scores
   as the provisional reference.
3. If the reference scores differ by more than 0.15, call the response
   **reference-ambiguous**.
4. Do not treat a candidate as right or wrong on a reference-ambiguous
   response. Report these responses separately.

The percentage of reference-resolved responses is an important result. Low
reference coverage means the rubric does not support reliable automatic
judging.

## Stability check

Before looking at scores, use a fixed random seed to select 18 frozen
responses—6 from each response family.

Run the same four eligible judges a second time on those responses. This adds
72 judgments.

Use these repeats to measure whether each judge gives a similar score when
shown the same response again.

## Metrics

For each inexpensive candidate, report:

- number of eligible responses;
- reference-resolution rate;
- mean absolute difference from the provisional reference;
- percentage within 0.15 of the reference;
- percentage differing by more than 0.30;
- mean signed difference from the reference;
- repeat-run percentage within 0.15;
- results separated by response family;
- 95% confidence intervals from a paired bootstrap clustered by scenario;
- token usage, cost, and latency; and
- a sorted list of the largest disagreements.

Pearson correlation may be reported as a secondary measure, but it is not an
agreement metric and must not be used to choose the winner by itself.

## Selection rule

An inexpensive candidate qualifies for a response family if:

- at least 85% of its scores are within 0.15 of the provisional reference;
- no more than 5% differ from the reference by more than 0.30;
- its absolute mean signed difference is no greater than 0.05; and
- at least 90% of its repeated scores are within 0.15 of the first score.

For each response family:

1. The least expensive qualifying candidate is the **main judge**.
2. The other qualifying candidate is the **backup judge**.
3. Do not force a winner if neither candidate qualifies or confidence
   intervals are too wide.

The expected output is a routing table, not one universal judge:

| Evaluated family | Possible main and backup |
|---|---|
| OpenAI | Gemini Flash and Claude Sonnet |
| Google | Claude Sonnet and GPT Luna |
| Anthropic | Gemini Flash and GPT Luna |

## Production escalation rule

1. Run the main judge.
2. Run the backup judge.
3. If their scores differ by no more than 0.15, use their mean.
4. If they differ by more than 0.15, run the two eligible strong reference
   judges.
5. If the strong reference judges also differ by more than 0.15, return
   **ambiguous** instead of manufacturing a definitive score.

## Interpretation

This experiment can establish which inexpensive judges most closely reproduce
cross-family strong-judge consensus, how stable they are, and how much they
cost.

Without human judgments or populated reference answers, it cannot establish
which score is objectively correct. Claims must therefore use language such as
"best match to cross-family reference consensus," not "best judge" or "most
accurate judge."

## Deliverables

- Frozen 90-response corpus
- Raw outputs from all primary and repeated judgments
- Scenario-by-scenario comparison table
- Results split by response family
- Reference-ambiguous disagreement list
- Stability analysis
- Cost and latency comparison
- Final main/backup routing table
- Interactive blinded qualitative-review interface
- Reproducibility manifest containing all revisions, settings, and hashes
