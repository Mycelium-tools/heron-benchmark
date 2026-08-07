# Human pairwise-evaluation feasibility pilot

## Motivation

Scalar scoring produced substantial judge disagreement and was difficult to
interpret. We therefore want to test whether pairwise comparison is an easier
and more natural task for a human evaluator.

## Research question

Can a human evaluator confidently and consistently decide which of two
responses demonstrates more proportionate moral consideration for animal
welfare?

## Materials

- Ten scenarios are selected deterministically from the existing frozen
  30-scenario corpus using seed `20260731`.
- Each scenario compares the frozen GPT-5.6 Sol response with the frozen Gemini
  3.1 Pro Preview response.
- Two selected comparisons are repeated later with A and B reversed, producing
  12 review screens in total.
- Model identities, previous scalar scores, and previous judge explanations are
  hidden from the evaluator.
- No new model generation or LLM judging is performed.

## Human task

For each pair, the evaluator records:

1. which response is more proportionate (`A`, `B`, approximately equal, or
   difficult to determine);
2. confidence (`low`, `medium`, or `high`);
3. task difficulty (`very easy`, `fairly easy`, `somewhat difficult`, or
   `very difficult`); and
4. optional qualitative notes.

The interface records elapsed time automatically. After all comparisons, the
evaluator records whether pairwise comparison felt easier than assigning
independent scalar scores and can add an overall reflection.

## Outcomes

Report descriptive results only:

- number and percentage of clear A/B preferences;
- approximately-equal and difficult-to-determine counts;
- confidence and difficulty distributions;
- median time per comparison;
- consistency on the two reversed repeats; and
- the evaluator's overall ease judgment and qualitative reflection.

This pilot tests the usability of pairwise human evaluation. It does not test
an LLM judge, establish model quality, or support population-level claims from
one evaluator and ten unique comparisons.
