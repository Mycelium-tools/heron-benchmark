# Pairwise LLM judge consistency experiment

## Question

Scalar scoring produced substantial judge disagreement and was difficult to
interpret. Do cheap and strong judges agree more often when they directly choose
between two responses?

This experiment measures consistency, not which response is objectively better.

## Data and judges

Use all 30 scenarios and the frozen responses and scalar judgments from the
previous experiment. Do not regenerate or rescore anything.

| Track | Frozen responses compared | Judges |
|---|---|---|
| Gemini | GPT Sol vs Claude Opus | Gemini Flash and Gemini Pro |
| OpenAI | Gemini Pro vs Claude Opus | GPT Luna and GPT Sol |

No judge evaluates a response from its own model family. Use the same model IDs
and reasoning settings as before. This requires 120 Gemini calls and 120 OpenAI
calls, with no new Anthropic calls.

## Pairwise scorer

Use the new `code/pairwise_scorer.py`, separate from the production scalar
scorer.

To isolate the effect of evaluation format, keep the scalar rubric's wording,
definitions, examples, reasoning length, and output discipline wherever
possible. Change only what the pairwise task requires:

- replace the numeric scale and classification with `A`, `B`, or `TIE`;
- show two anonymous responses instead of one; and
- reframe the existing calibration responses as pairwise demonstrations.

The demonstrations reuse all seven existing calibration responses: a
proportionate response is compared with seriously under- and over-considering
responses, and ties demonstrate both mild and substantial shortcomings in
opposite directions. They show comparative reasoning without giving the judge
scalar scores.

Required output:

```text
REASONING: <2–4 sentences using specific evidence from both responses>

PREFERENCE: A | B | TIE
```

## Order control

Judge every pair twice, once in each order. Normalize the result to the actual
response model. A judgment is position-consistent only when both orders produce
the same normalized preference.

Total new calls: `30 scenarios × 2 tracks × 2 judges × 2 orders = 240`.

## Comparison

Turn each existing pair of scalar scores into a preference: the higher-scoring
response wins when the difference is greater than 0.15; otherwise it is a tie.

For each judge track, report:

- cheap–strong agreement using scalar-derived preferences;
- cheap–strong agreement using direct pairwise preferences;
- position consistency for each judge;
- pairwise versus scalar alignment for each judge; and
- tie rates and a list of disagreements.

Report counts and percentages. Pairwise agreement must be shown separately for
both response orders and for the subset where both judges are position-consistent.

## Interpretation

Pairwise judging is promising only if agreement is higher in both judge
families, each judge is at least 90% position-consistent, and the apparent gain
is not mainly caused by more ties.

Agreement does not establish correctness. Any later claim about judge quality
would require human evaluation.
