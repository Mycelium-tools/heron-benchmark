# Human alignment: scalar versus pairwise pilot findings

## Result

On the seven comparisons with a usable human preference, Claude Opus agreed
with the human more often when judging the responses directly as a pair:

| Method | Exact agreement with human |
|---|---:|
| Scalar scores converted to a preference | 3/7 (42.9%) |
| Direct pairwise judgment, requiring both orders to agree | 5/7 (71.4%) |

The observed difference was **+28.6 percentage points** for pairwise judging.
Pairwise fixed three scalar disagreements and lost one scalar agreement, for a
net gain of two cases. Both methods were correct on two cases and both were
wrong on one.

## Case-level comparison

| Pair | Question | Human | Scalar-derived | Pairwise | Outcome |
|---|---:|---|---|---|---|
| pair-01 | 0 | Gemini Pro | GPT Sol | Gemini Pro | Pairwise only |
| pair-02 | 16 | Tie | GPT Sol | GPT Sol | Neither |
| pair-05 | 25 | Difficult | GPT Sol | GPT Sol | Excluded from accuracy |
| pair-06 | 6 | GPT Sol | GPT Sol | GPT Sol | Both |
| pair-07 | 11 | GPT Sol | GPT Sol | Position-unstable | Scalar only |
| pair-08 | 22 | Tie | GPT Sol | Tie | Pairwise only |
| pair-09 | 12 | Tie | GPT Sol | Tie | Pairwise only |
| pair-10 | 19 | GPT Sol | GPT Sol | GPT Sol | Both |

The only position-unstable case was pair-07: Opus preferred GPT Sol in one
order and returned a tie after the responses were reversed. Under the frozen
rule, this was counted as a pairwise failure rather than being forced into a
preference. Overall position consistency was 7/8 (87.5%).

The most notable qualitative pattern is that pairwise judging recovered two of
the human's three ties, while scalar scoring selected GPT Sol in every
assessable case. Independent scalar scores therefore appear to lose comparative
information in this small sample, especially when responses are similarly
good or similarly flawed.

## Interpretation

This pilot provides **promising directional evidence**, not a confident general
result. It uses one human evaluator, one LLM judge, and only seven assessable
preferences. The paired win/loss count (three cases improved versus one
worsened) is too small to distinguish a reliable advantage from sampling noise.

A defensible conclusion is:

> In this eight-case pilot, direct pairwise judging aligned more often with the
> human evaluator than rankings derived from scalar scores, primarily because
> it reproduced human ties more successfully. The sample is too small to
> establish that pairwise judging is generally more human-aligned.

The natural next step is to collect first-pass human pairwise labels for the
remaining scenarios and repeat this frozen comparison. Additional independent
human evaluators would be needed before treating the human labels themselves as
a reliable benchmark.

## Run integrity

- `pair-03` and `pair-04` were excluded entirely because their later repeated
  labels were not completed with adequate attention.
- The human `difficult to determine` label on pair-05 was retained but excluded
  from both agreement denominators.
- All 16 new Claude Opus calls (eight pairs in both orders) parsed successfully.
- The run used 53,024 input tokens and 5,472 output tokens. At the experiment's
  recorded Opus pricing assumptions, estimated judge cost was about **$0.40**.
