# Cross-family judge selection: findings

## Result

No cheap judge met all four pre-registered reliability requirements for any
target-model family. The experiment therefore does **not** support choosing a
cheap main-and-backup pair yet.

| Target family | Better cheap candidate | MAE | Within 0.15 | Over 0.30 | Bias | Repeat within 0.15 | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| OpenAI | Gemini Flash | 0.071 | 85.7% | 4.8% | +0.071 | 100.0% | Fails bias |
| Google | GPT Luna | 0.099 | 84.2% | 0.0% | -0.020 | 83.3% | Fails agreement and stability |
| Anthropic | GPT Luna | 0.137 | 68.8% | 18.8% | +0.112 | 83.3% | Fails three requirements |

Gemini Flash was perfectly stable in its 12 repeat judgments, but tended to
score higher than the strong-judge consensus. Luna came closest for Gemini
responses, missing the agreement threshold by one resolved scenario, but was
not stable enough in the repeat sample. Sonnet did not outperform Luna for
Gemini responses and did not qualify for OpenAI responses.

## Important limitation

The two strong reference judges themselves differed by more than 0.15 on 34 of
90 responses. Reference consensus was available for 70.0% of OpenAI responses,
63.3% of Google responses, and 53.3% of Anthropic responses. This is the
experiment's most important result: model-only agreement is often insufficient
to define a trustworthy answer, especially for Claude responses.

The study measures consistency with a model consensus, not objective judge
quality. There were no human labels and the dataset has no reference answers,
so ambiguous cases cannot establish which judge is correct.

## Production decision

HERON now uses two strong judges from families different from the evaluated
model:

- OpenAI response → Gemini Pro and Claude Opus
- Gemini response → Claude Opus and GPT Sol
- Claude response → Gemini Pro and GPT Sol

Their mean is used only when their scores are within 0.15. Larger disagreements
are marked ambiguous and excluded from the aggregate metric while retaining
both judgments for review. This preserves the cross-family rule and avoids
claiming evidence for a cheap judge that did not pass the stated standard.

The complete experiment cost about **$7.38**, including 90 target generations,
360 primary judgments, and 72 repeat judgments. The candidate-judge portions
cost about $0.20 for Luna, $0.25 for Flash, and $0.60 for Sonnet. Those savings
remain attractive, but a larger dataset with adjudicated human labels would be
needed to justify deploying them.

Use `results/qualitative_review.html` to inspect the largest reference
disagreements first and record qualitative notes.
