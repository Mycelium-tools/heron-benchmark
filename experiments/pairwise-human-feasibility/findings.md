# Human pairwise-evaluation feasibility pilot: findings

## Motivation

Scalar scoring produced substantial judge disagreement and was difficult to
interpret. We therefore tested whether pairwise comparison was an easier and
more natural task for a human evaluator.

## Method

One evaluator reviewed ten unique, blinded comparisons between frozen GPT-5.6
Sol and Gemini 3.1 Pro Preview responses. Model names and previous judge scores
were hidden, response order was balanced, and two comparisons were repeated
later with A and B reversed. The evaluator recorded a preference, confidence,
difficulty, optional notes, and a final reflection.

## Results

| Outcome | Result |
|---|---:|
| Clear preference | 6/10 (60%) |
| Approximately equal | 3/10 (30%) |
| Difficult to determine | 1/10 (10%) |
| High confidence | 6/10 (60%) |
| Very easy | 7/10 (70%) |
| Somewhat or very difficult | 3/10 (30%) |
| Reversed-repeat consistency | 1/2 observed; not interpretable |
| Median time per unique comparison | 93.6 seconds |

The evaluator described pairwise comparison as **much easier** than assigning
independent scalar scores, although the task's overall clarity was rated
**mixed**. The ten unique comparisons took about 17.3 minutes in total; all 12
screens took about 18.8 minutes.

The reversed-repeat result is not a valid estimate of evaluator consistency.
The evaluator reported not carefully rereading the repeated responses because
doing so was too burdensome. The observed 1/2 result is retained for
transparency, but it reflects a failure of the repeat procedure—particularly
fatigue from long responses—rather than demonstrated instability in the
underlying judgment.

## Qualitative findings

The main burden was reading long responses. Differences in verbosity sometimes
influenced the evaluator's preference independently of the underlying welfare
judgment. Repeated long responses were sufficiently annoying that the evaluator
did not fully reread them, invalidating the planned consistency check.

The pilot also exposed two substantive limitations:

1. Pairwise comparison does not by itself distinguish “both good” from “both
   similarly poor.” Several ties occurred because neither response showed the
   consideration the evaluator thought was warranted.
2. One scenario was judged unsuitable because it was unclear that moral
   consideration was warranted at all. Pairwise review can therefore reveal
   dataset-validity problems as well as response differences.

As an exploratory secondary result, GPT-5.6 Sol was selected in five of the six
clear preferences and Gemini Pro in one. Five of the six clear choices were
also displayed in position B. With one evaluator, ten examples, unequal
response lengths, and an invalid repeat check, neither pattern should be
interpreted as a reliable model ranking or position effect.

## Conclusion

The pilot supports the narrow claim that pairwise evaluation **felt easier and
was usually easy to complete** for this evaluator. It does not test whether the
method is reliably reproducible because the repeat procedure was not completed
with sufficient attention. Separately, 40% of cases produced no clear winner.

Pairwise evaluation is promising enough to refine, but not yet ready to serve
as an LLM-judge validation method. A revised human interface should distinguish
“both proportionate,” “both flawed,” and “too close to call,” and the questionable
scenario should be reviewed before a larger run. If consistency is tested
again, it should use shorter responses or a much shorter session and should
explicitly confirm that repeats were fully reread. More human evaluators would
then be needed before testing LLM pairwise judges.
