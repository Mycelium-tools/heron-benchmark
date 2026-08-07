# Five-scenario smoke test

## Technical result

The pairwise experiment ran successfully on the first five scenarios.

- 10 frozen response pairs
- 20 reused scalar-preference rows
- 40 new pairwise judgments
- 10 valid outputs from each judge
- 20 Gemini calls, 20 OpenAI calls, and 0 Anthropic calls
- Every output matched the required reasoning and preference format
- Every response pair was evaluated in both orders and normalized correctly
- All frozen-input and result hashes verified
- Estimated API cost: $0.41

The runner is resumable and the same code can run all 30 scenarios.

## Early results

| Track | Scalar agreement | Pairwise agreement | Cheap judge order consistency | Strong judge order consistency |
|---|---:|---:|---:|---:|
| Gemini judges | 4/5 (80%) | 7/10 (70%) | 4/5 (80%) | 4/5 (80%) |
| OpenAI judges | 2/5 (40%) | 6/10 (60%) | 2/5 (40%) | 4/5 (80%) |

Pairwise agreement was lower than scalar agreement in the Gemini track and
higher in the OpenAI track. Neither track met the predeclared 90% position-
consistency requirement. Luna changed its normalized preference in three of
five scenarios; each of the other judges changed once.

Tie behavior also differed between formats. Scalar-derived ties were very
common in this five-scenario subset, while direct pairwise judgments produced
fewer ties. This confirms that the experiment is measuring a real change in
task format rather than merely reproducing the scalar decisions.

## Interpretation

The smoke test validates the implementation but does not support an early
substantive conclusion from five scenarios. Most importantly, it shows that the
order swaps are necessary: without them, the apparent OpenAI inter-judge
agreement would have been either 40% or 80%, depending only on which response
order was used.

The full run is technically ready. Its purpose would be to determine whether
the mixed agreement and position-sensitivity patterns persist across all 30
scenarios.
