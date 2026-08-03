# Pairwise LLM judge consistency: findings

## Result

Direct pairwise evaluation did **not** improve judge consistency across both
model families.

| Judge track | Scalar agreement | Pairwise agreement | Cheap judge order consistency | Strong judge order consistency |
|---|---:|---:|---:|---:|
| Gemini Flash vs Pro | 24/30 (80.0%) | 33/60 (55.0%) | 21/30 (70.0%) | 26/30 (86.7%) |
| GPT Luna vs Sol | 20/30 (66.7%) | 40/60 (66.7%) | 23/30 (76.7%) | 26/30 (86.7%) |

The predeclared decision rule required pairwise agreement to improve in both
tracks and every judge to be at least 90% position-consistent. Neither condition
was met.

## Position mattered

Reversing the two responses changed Gemini inter-judge agreement from 46.7% to
63.3%, and OpenAI agreement from 56.7% to 76.7%. Only 20 of 30 scenarios in each
track had position-consistent judgments from both judges.

Most Gemini order changes moved between a tie and a winner, although Flash
changed directly from one winner to the other once. Luna directly reversed its
winner four times. The order swaps were therefore necessary: a single ordering
would have produced a materially different conclusion.

## Pairwise judgments were more decisive, but not more consistent

Scalar-derived preferences produced many ties because response scores often
differed by no more than 0.15:

- Gemini track: Flash 96.7% ties and Pro 76.7% ties
- OpenAI track: Luna 46.7% ties and Sol 46.7% ties

Direct pairwise tie rates were lower:

- Gemini track: Flash 66.7% and Pro 53.3%
- OpenAI track: Luna 11.7% and Sol 13.3%

Pairwise evaluation therefore extracted more preferences, especially from the
OpenAI judges, but those additional preferences were sensitive to judge and
response order. Higher decisiveness should not be mistaken for higher
reliability.

## Run integrity and cost

The full run produced 240 valid pairwise outputs: 120 Gemini calls and 120
OpenAI calls, with both response orders for all 30 scenarios. It made no
Anthropic or Bedrock calls. All frozen-input and output hashes verified.

Estimated total cost was **$2.57**:

- Gemini Flash: $0.26
- Gemini Pro: $0.77
- GPT Luna: $0.21
- GPT Sol: $1.32

## Conclusion

For these judges and responses, replacing scalar scoring with direct pairwise
comparison does not solve inter-judge inconsistency. It removes some scalar
ties, but introduces meaningful order sensitivity and does not improve
agreement across judge families.

This experiment measures consistency, not correctness. It does not establish
whether the scalar or pairwise decisions better reflect human judgment.
