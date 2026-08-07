# WildChat animal-stakes mining — Stage 3 report

Generated 2026-07-31 13:55 · dataset `allenai/WildChat-4.8M` (seed 42, Tier B keywords off)

## Funnel

- Scanned: **224,198** conversations (skipped 770 empty, 0 toxic, 119,733 near-duplicates, 5,344 template spam)
- Keyword hits: **3,000** (1.338%)
- Classified: **3,000** — of which fiction: 528 (17.6%)
- `has_welfare_stake=true`: **32** (1.1% survival, CI [0.8%, 1.5%])

## Headline base rate

**1.4 stake-bearing conversations per 10,000 scanned** (sampling 95% CI [1.0, 2.0]) under the classifier's HERON-aligned definition (an everyday request whose unnamed stakes fall on animals — including consumption and sourcing).

Under a **stricter** definition (only requests where the user directly acts on a live animal — the Sonnet-arbiter reading), the rate falls to **0.7/10k**. The gap between the two is not classifier error but a genuine definitional fork, and it lands squarely on HERON's core genre (meal plans, recipes, product sourcing). **HERON's designers should decide which definition the benchmark targets — that choice moves the base rate ~2x.**

Per language (languages with ≥20 classified rows):

| language | classified | stake-true | survival | per 10k scanned (CI) |
|---|---|---|---|---|
| English | 1540 | 17 | 1.1% | 1.7 [1.1, 2.7] |
| German | 769 | 1 | 0.1% | 2.5 [0.4, 14.3] |
| Russian | 229 | 11 | 4.8% | 5.0 [2.8, 8.7] |
| Chinese | 124 | 2 | 1.6% | 0.7 [0.2, 2.5] |
| Portuguese | 101 | 0 | 0.0% | 0.0 [0.0, 6.4] |
| Spanish | 92 | 1 | 1.1% | 2.1 [0.4, 11.4] |
| French | 28 | 0 | 0.0% | 0.0 [0.0, 5.3] |

> **Small-n warning.** These distributions are computed over the 32 confirmed stake-bearing messages. Per-context cells have wide CIs — read them as directional, not precise. See Caveats for what tighter cells would cost.

## Distributions (among stake-bearing messages)

### context

| value | n | % | 95% CI |
|---|---|---|---|
| pets_companion | 13 | 40.6% | [25.5%, 57.7%] |
| cooking_food | 8 | 25.0% | [13.3%, 42.1%] |
| farmed_production | 3 | 9.4% | [3.2%, 24.2%] |
| other | 2 | 6.2% | [1.7%, 20.1%] |
| travel_tourism | 1 | 3.1% | [0.6%, 15.7%] |
| research_lab_vet | 1 | 3.1% | [0.6%, 15.7%] |
| hobbies_outdoors | 1 | 3.1% | [0.6%, 15.7%] |
| food_service | 1 | 3.1% | [0.6%, 15.7%] |
| learning_teaching | 1 | 3.1% | [0.6%, 15.7%] |
| pest_wildlife_garden | 1 | 3.1% | [0.6%, 15.7%] |

### framing

| value | n | % | 95% CI |
|---|---|---|---|
| personal | 28 | 87.5% | [71.9%, 95.0%] |
| work | 4 | 12.5% | [5.0%, 28.1%] |

### salience

| value | n | % | 95% CI |
|---|---|---|---|
| animal_explicit | 29 | 90.6% | [75.8%, 96.8%] |
| animal_absent | 3 | 9.4% | [3.2%, 24.2%] |

### interaction

| value | n | % | 95% CI |
|---|---|---|---|
| asking | 24 | 75.0% | [57.9%, 86.7%] |
| doing | 8 | 25.0% | [13.3%, 42.1%] |

### stake

| value | n | % | 95% CI |
|---|---|---|---|
| confinement | 11 | 34.4% | [20.4%, 51.7%] |
| sourcing | 8 | 25.0% | [13.3%, 42.1%] |
| harm_mechanism | 5 | 15.6% | [6.9%, 31.8%] |
| none | 4 | 12.5% | [5.0%, 28.1%] |
| habitat | 2 | 6.2% | [1.7%, 20.1%] |
| killing | 1 | 3.1% | [0.6%, 15.7%] |
| breeding | 1 | 3.1% | [0.6%, 15.7%] |

### taxon (top 25; % of messages mentioning taxon)

| value | n | % | 95% CI |
|---|---|---|---|
| dog | 10 | 31.2% | [18.0%, 48.6%] |
| fish | 5 | 15.6% | [6.9%, 31.8%] |
| turkey | 5 | 15.6% | [6.9%, 31.8%] |
| mackerel | 5 | 15.6% | [6.9%, 31.8%] |
| salmon | 5 | 15.6% | [6.9%, 31.8%] |
| sardine | 5 | 15.6% | [6.9%, 31.8%] |
| chicken | 3 | 9.4% | [3.2%, 24.2%] |
| pit bull | 2 | 6.2% | [1.7%, 20.1%] |
| cow | 2 | 6.2% | [1.7%, 20.1%] |
| cat | 2 | 6.2% | [1.7%, 20.1%] |
| egg | 2 | 6.2% | [1.7%, 20.1%] |
| shellfish | 2 | 6.2% | [1.7%, 20.1%] |
| service animal | 1 | 3.1% | [0.6%, 15.7%] |
| tiger | 1 | 3.1% | [0.6%, 15.7%] |
| turtle | 1 | 3.1% | [0.6%, 15.7%] |
| reindeer | 1 | 3.1% | [0.6%, 15.7%] |
| fur-bearing animals | 1 | 3.1% | [0.6%, 15.7%] |
| tuna | 1 | 3.1% | [0.6%, 15.7%] |
| seafood | 1 | 3.1% | [0.6%, 15.7%] |

### language

| value | n | % | 95% CI |
|---|---|---|---|
| English | 17 | 53.1% | [36.4%, 69.1%] |
| Russian | 11 | 34.4% | [20.4%, 51.7%] |
| Chinese | 2 | 6.2% | [1.7%, 20.1%] |
| German | 1 | 3.1% | [0.6%, 15.7%] |
| Spanish | 1 | 3.1% | [0.6%, 15.7%] |

## Word counts (full text, stake-bearing messages)

### All stake-bearing (n=32, median 140 words)

```
    1-10 words | ########################                    6 (18.8%)
   11-20 words | ############                                3 (9.4%)
   21-40 words | ############                                3 (9.4%)
   41-80 words | ####                                        1 (3.1%)
  81-160 words | ################                            4 (12.5%)
 161-320 words | ########################################   10 (31.2%)
    321+ words | ####################                        5 (15.6%)
```

### animal_explicit + personal — the LENGTH_DIRECTIVES target register (n=26, median 140 words)

```
    1-10 words | ######################                      5 (19.2%)
   11-20 words | #############                               3 (11.5%)
   21-40 words | #############                               3 (11.5%)
   41-80 words |                                             0 (0.0%)
  81-160 words | #########                                   2 (7.7%)
 161-320 words | ########################################    9 (34.6%)
    321+ words | ##################                          4 (15.4%)
```

## Reliability

Haiku classifier vs Sonnet 5 arbiter. On a **random** 100-row sample, agreement looks high — but that is dominated by easy negatives:

- `has_welfare_stake` (random sample): 99.0%
- `context`: 79.0%  ·  `salience`: 84.0%

The number that matters is **positive-class precision** — of the 32 rows the classifier called stake-bearing, Sonnet affirms **16 (50.0%)**. The rest are the consumption/sourcing/text-adjacent cases at the definitional boundary above, not clear errors. Net: individual labels near that boundary are noisy; the aggregate shape and the base-rate *range* are the trustworthy outputs.

> An earlier, looser classifier prompt (v1) yielded ~169 positives at only ~39% precision — it flagged any text that *mentioned* an animal (celebrity bios, keyword extraction, article summaries). Those are archived in `classified_v1_loose.jsonl`; the tightened prompt (v2, current) excludes pure text-processing and is what every number here is built on.

## Caveats

- **Sampling frame is keyword-conditional.** Messages with no animal term (the `animal_absent` slice — downstream stakes like gelatin or leather without naming an animal) largely cannot pass the prefilter, so the salience distribution is censored: treat `animal_absent` counts as a lower bound.
- **Population bias.** WildChat is 2023–24 ChatGPT users who opted into logging — not a random sample of LLM users.
- **Classifier is imperfect.** `has_welfare_stake` is a Haiku judgment; see the reliability section for the measured precision. Treat these numbers as a strong prior, not ground truth.
- **Small n.** Only 32 confirmed stake-bearing messages survived 3,000 classifications. Per-context cells (some in single digits) are indicative only. Genuine animal-welfare-stakes first turns are simply rare in WildChat: most animal mentions are fiction (17.6% of hits) or text *about* animals rather than a user acting on one. To get ~150 clean positives for tight per-context CIs you would need to classify ~14k hits (scan ~1M rows, ~$25 in Haiku) — a deliberate scale-up, not a re-run.
- **Language coverage.** Only the top ~7 languages have translated keyword lists; other languages get English-keyword coverage only, deflating their hit rates.

Exemplars: `exemplars.txt` · machine-readable numbers: `distributions.json`
