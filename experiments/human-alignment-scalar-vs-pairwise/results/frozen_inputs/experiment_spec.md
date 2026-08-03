# Human alignment: scalar versus pairwise pilot

## Question

Does a strong LLM reproduce a human's pairwise preference more often when it
compares two responses directly than when its independent scalar scores are
converted into a preference?

## Frozen inputs

- Use the eight first-pass human comparisons that were not later repeated.
- Exclude `pair-03` and `pair-04` entirely because their order-swapped human
  relabels were not read carefully enough to be reliable.
- The responses are the frozen GPT-5.6 Sol and Gemini 3.1 Pro Preview corpus.
- The human's first-pass label is the common reference for both methods.
- `difficult to determine` is not a preference and is excluded from agreement
  denominators, but retained in the case table.

## Judge

Use Claude Opus 5 as the single strong third-family judge. Reuse its frozen
scalar scores from the cross-family judge-selection experiment. Make new
pairwise calls through the Anthropic API with the frozen pairwise prompt, low
effort, and no sampling parameters specified.

Run every pairwise judgment twice, reversing response order. A direct pairwise
preference is stable only when both orders select the same underlying response
or both return a tie. An order-unstable result counts as a failure to reproduce
the human preference; it is never forced into a winner.

## Comparison

- Scalar-derived preference: higher Opus score wins; identical scores are a tie.
- Pairwise preference: the stable result across both response orders.
- Agreement: exact match with the human label, including ties.

Report agreement counts and percentages, position instability, and a case table
showing the human label, scalar scores and preference, both pairwise judgments,
and whether each method agreed. This eight-case study is an exploratory pilot,
not a statistically conclusive estimate of judge accuracy.
