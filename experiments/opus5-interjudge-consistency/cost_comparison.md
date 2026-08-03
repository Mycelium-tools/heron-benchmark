# Judge Cost Comparison

Costs below are estimates at standard paid API list prices on July 28, 2026.
They exclude free-tier credits, taxes, negotiated discounts, and the small
validation calls made while configuring the experiment.

## Observed experiment cost

| Model | Scope | Input tokens | Visible output | Thinking/reasoning | Estimated cost | Cost/scenario |
|---|---:|---:|---:|---:|---:|---:|
| Gemini 3.6 Flash | 30 | 97,167 | 6,518 | 0 | $0.1946 | $0.00649 |
| Gemini 3.1 Pro Preview | 30 | 97,167 | 5,331 | 11,252 | $0.3933 | $0.01311 |
| GPT-5.6 Luna | 30 | 93,395 | 5,718 | 0 | $0.1510 | $0.00503 |
| GPT-5.6 Sol | 30 | 93,395 | 5,949 | 0 | $0.7621 | $0.02540 |

Gemini output pricing includes thinking tokens. OpenAI input cost includes the
reported 93,305 cache-write tokens for each model at the published 1.25x cache-write
multiplier. No cache reads were reported.

On this corpus, Gemini Flash cost about 50.5% less than Gemini Pro
($0.1946 vs. $0.3933), making Pro about 2.02x as expensive. Luna was the
least-expensive judge in this run at $0.1510, while Sol was the most expensive
at $0.7621. All four cost totals are observed across the same 30 scenarios.

## Rates used

| Model | Standard input / 1M | Standard output / 1M |
|---|---:|---:|
| Gemini 3.6 Flash | $1.50 | $7.50 |
| Gemini 3.1 Pro Preview | $2.00 | $12.00 |
| GPT-5.6 Luna | $1.00 | $6.00 |
| GPT-5.6 Sol | $5.00 | $30.00 |

Sources:

- [Google Gemini Developer API pricing](https://ai.google.dev/gemini-api/docs/pricing)
- [OpenAI GPT-5.6 Luna model pricing](https://developers.openai.com/api/docs/models/gpt-5.6-luna)
- [OpenAI GPT-5.6 Sol pricing announcement](https://openai.com/index/previewing-gpt-5-6-sol/)

## Target-generation cost (not a judge)

The validated low-effort Opus corpus used 1,908 input and 48,281 output tokens.
At the published Claude Opus 5 rates of $5/1M input and $25/1M output, that is
an estimated $1.2166 ($0.04055/scenario). This target cost is separate from the
judge comparison.

Source: [Anthropic Claude Opus 5 pricing](https://platform.claude.com/docs/en/about-claude/models/whats-new-opus-5).
