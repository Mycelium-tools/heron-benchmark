# HERON judge experiments: overall finding

We tested whether HERON could use cheaper judges and whether pairwise judging
works better than scalar scoring.

## What we found

1. **Cheap judges are promising, but not yet validated.** Gemini Flash tracked
   Gemini Pro reasonably well when scoring frozen Opus responses. In the broader
   cross-family test, however, no cheap judge passed every reliability rule.

2. **Model agreement is not ground truth.** Even strong judges often disagreed
   on individual scenarios. Similar benchmark averages hid meaningful
   scenario-level differences, and same-family agreement may partly reflect
   shared model calibration.

3. **Pairwise judging did not improve agreement between LLM judges.** Gemini
   agreement fell from 80.0% with scalar-derived preferences to 55.0% pairwise;
   OpenAI agreement stayed at 66.7%. Pairwise decisions were also sensitive to
   which response appeared first.

4. **Pairwise judging was easier for the human evaluator.** Most comparisons
   felt easy, although long responses, repeated cases, and ambiguous ties made
   the task tiring. The repeat-label check was therefore not reliable.

5. **Pairwise judging may match human preferences better.** In the small clean
   pilot, Claude Opus matched the human on 5/7 direct pairwise decisions (71.4%)
   versus 3/7 preferences derived from scalar scores (42.9%). Pairwise mainly
   helped by recovering human ties. Seven usable labels are too few for a firm
   conclusion.

## Bottom line

The experiments do not yet justify replacing a strong judge with a cheap one,
and pairwise judging does not make LLM judges more consistent with each other.
The most useful signal so far is that pairwise evaluation may better capture
human comparative preferences.

The next useful step is human pairwise labeling across the full unique
30-scenario dataset, followed by the same frozen scalar-versus-pairwise
comparison. Until then, disagreement cases should remain visible rather than
being treated as objective scores.
