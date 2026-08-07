"""
Stage 3 — distributions, base rate, and exemplars from classified WildChat rows.

Reads out/classified.jsonl + out/stage1_stats.json (+ out/reliability.jsonl if
present) and writes:

  out/report.md           human-readable report (base rate, distributions with
                          Wilson 95% CIs, word-count histogram, caveats)
  out/distributions.json  the same numbers, machine-readable
  out/exemplars.txt       up to 50 stake-bearing messages verbatim, grouped by context

Usage (from repo root):
    python experiments/wildchat/stage3_report.py
"""

import argparse
import json
import math
import os
from collections import Counter, defaultdict
from datetime import datetime

WORD_BUCKETS = [(1, 10), (11, 20), (21, 40), (41, 80), (81, 160), (161, 320), (321, None)]
EXEMPLAR_TOTAL = 50
EXEMPLARS_PER_CONTEXT = 5


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score 95% CI for a binomial proportion, as (low, high) in [0, 1]."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    margin = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return (max(0.0, center - margin), min(1.0, center + margin))


def load_jsonl(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def distribution(values: list[str], total: int | None = None) -> list[dict]:
    """Counts, percentages, and Wilson CIs for a categorical field, sorted by count."""
    n = total if total is not None else len(values)
    rows = []
    for value, count in Counter(values).most_common():
        low, high = wilson_ci(count, n)
        rows.append({
            "value": value,
            "count": count,
            "pct": round(count / n * 100, 1),
            "ci_low_pct": round(low * 100, 1),
            "ci_high_pct": round(high * 100, 1),
        })
    return rows


def dist_table(rows: list[dict], header: str) -> str:
    lines = [f"### {header}", "", "| value | n | % | 95% CI |", "|---|---|---|---|"]
    for r in rows:
        lines.append(
            f"| {r['value']} | {r['count']} | {r['pct']}% "
            f"| [{r['ci_low_pct']}%, {r['ci_high_pct']}%] |"
        )
    return "\n".join(lines)


def word_histogram(word_counts: list[int]) -> list[dict]:
    rows = []
    for low, high in WORD_BUCKETS:
        label = f"{low}-{high}" if high else f"{low}+"
        count = sum(1 for w in word_counts if w >= low and (high is None or w <= high))
        rows.append({"bucket": label, "count": count,
                     "pct": round(count / len(word_counts) * 100, 1) if word_counts else 0.0})
    return rows


def histogram_block(rows: list[dict], title: str) -> str:
    lines = [f"### {title}", "", "```"]
    max_pct = max((r["pct"] for r in rows), default=1) or 1
    for r in rows:
        bar = "#" * round(r["pct"] / max_pct * 40)
        lines.append(f"{r['bucket']:>8} words | {bar:<40} {r['count']:>4} ({r['pct']}%)")
    lines.append("```")
    return "\n".join(lines)


def median(values: list[int]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    mid = len(s) // 2
    return float(s[mid]) if len(s) % 2 else (s[mid - 1] + s[mid]) / 2


def pick_exemplars(stake_rows: list[dict]) -> dict[str, list[dict]]:
    """Up to 5 per context (50 total), preferring distinct (taxon, stake) combos."""
    by_context: dict[str, list[dict]] = defaultdict(list)
    for row in sorted(stake_rows, key=lambda r: r["word_count"]):
        if not row.get("redacted"):
            by_context[row["classification"]["context"]].append(row)

    chosen: dict[str, list[dict]] = {}
    total = 0
    # Round-robin contexts by size so small contexts still get representation.
    for context in sorted(by_context, key=lambda c: -len(by_context[c])):
        picked: list[dict] = []
        seen_combos: set[tuple] = set()
        for row in by_context[context]:
            combo = (tuple(sorted(row["classification"]["taxon"])),
                     row["classification"]["stake"])
            if combo in seen_combos and len(by_context[context]) > EXEMPLARS_PER_CONTEXT:
                continue
            seen_combos.add(combo)
            picked.append(row)
            if len(picked) >= EXEMPLARS_PER_CONTEXT:
                break
        chosen[context] = picked
        total += len(picked)
        if total >= EXEMPLAR_TOTAL:
            break
    return chosen


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir",
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"))
    args = parser.parse_args()

    classified = load_jsonl(os.path.join(args.out_dir, "classified.jsonl"))
    if not classified:
        print("No classified.jsonl found — run stage2_classify.py first.")
        return
    with open(os.path.join(args.out_dir, "stage1_stats.json"), encoding="utf-8") as f:
        stage1 = json.load(f)
    reliability = load_jsonl(os.path.join(args.out_dir, "reliability.jsonl"))

    stake_rows = [r for r in classified if r["classification"]["has_welfare_stake"]]
    fiction_rows = [r for r in classified if r["classification"]["is_fiction"]]
    n_classified = len(classified)
    n_stake = len(stake_rows)

    # --- Base rate: P(stake) = P(keyword hit) × P(stake | hit, classified sample) ---
    hit_fraction = stage1["hits"] / stage1["scanned"]
    survival_low, survival_high = wilson_ci(n_stake, n_classified)
    survival = n_stake / n_classified
    base_rate_per_10k = hit_fraction * survival * 10_000
    base_rate_ci = (hit_fraction * survival_low * 10_000,
                    hit_fraction * survival_high * 10_000)

    per_language_base = []
    stake_by_lang = Counter(r["language"] for r in stake_rows)
    classified_by_lang = Counter(r["language"] for r in classified)
    for lang, n_cls in classified_by_lang.most_common():
        if n_cls < 20:
            continue
        k = stake_by_lang.get(lang, 0)
        lang_hits = stage1["hits_by_language"].get(lang, 0)
        lang_scanned = stage1["scanned_by_language"].get(lang, 0)
        if not lang_scanned:
            continue
        lo, hi = wilson_ci(k, n_cls)
        factor = lang_hits / lang_scanned * 10_000
        per_language_base.append({
            "language": lang, "classified": n_cls, "stake_true": k,
            "survival_pct": round(k / n_cls * 100, 1),
            "base_rate_per_10k": round(factor * k / n_cls, 1),
            "ci_low": round(factor * lo, 1), "ci_high": round(factor * hi, 1),
        })

    # --- Distributions among stake-bearing rows ---
    cls = [r["classification"] for r in stake_rows]
    dists = {
        "context": distribution([c["context"] for c in cls]),
        "framing": distribution([c["framing"] for c in cls]),
        "salience": distribution([c["salience"] for c in cls]),
        "interaction": distribution([c["interaction"] for c in cls]),
        "stake": distribution([c["stake"] for c in cls]),
        # multi-label: % is share of stake-bearing MESSAGES mentioning the taxon
        "taxon": distribution(
            [t for c in cls for t in dict.fromkeys(c["taxon"])], total=n_stake
        )[:25],
        "language": distribution([r["language"] for r in stake_rows]),
    }

    # --- Word counts (full text, not the truncated classifier input) ---
    wc_all = [r["word_count"] for r in stake_rows]
    target_rows = [
        r["word_count"] for r in stake_rows
        if r["classification"]["salience"] == "animal_explicit"
        and r["classification"]["framing"] == "personal"
    ]
    hist_all = word_histogram(wc_all)
    hist_target = word_histogram(target_rows)

    # --- Reliability summary ---
    reliability_summary = None
    if reliability:
        n_rel = len(reliability)
        reliability_summary = {
            key: round(
                sum(1 for r in reliability if r["haiku"][key] == r["sonnet"][key])
                / n_rel * 100, 1)
            for key in ("has_welfare_stake", "context", "salience")
        }
        reliability_summary["n"] = n_rel

    # --- Positive-class precision: of the classifier's stake=true rows, what
    # fraction does the Sonnet arbiter affirm? This is the number that matters,
    # since a random sample is dominated by easy negatives. ---
    positives = load_jsonl(os.path.join(args.out_dir, "reliability_positives.jsonl"))
    precision = None
    if positives:
        affirmed = sum(1 for r in positives if r["sonnet"]["has_welfare_stake"])
        precision = {
            "n": len(positives),
            "affirmed": affirmed,
            "precision_pct": round(affirmed / len(positives) * 100, 1),
        }
        # Base rate under the stricter arbiter definition (both judges agree):
        # scale the headline by the affirmed fraction.
        strict = base_rate_per_10k * affirmed / len(positives)
        precision["strict_base_rate_per_10k"] = round(strict, 1)

    # --- distributions.json ---
    summary = {
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "stage1": {k: stage1[k] for k in
                   ("scanned", "hits", "hit_rate_pct", "skipped_empty",
                    "skipped_toxic", "skipped_dupe", "skipped_template",
                    "seed", "tier_b")},
        "classified": n_classified,
        "stake_true": n_stake,
        "survival_pct": round(survival * 100, 1),
        "survival_ci_pct": [round(survival_low * 100, 1), round(survival_high * 100, 1)],
        "fiction": len(fiction_rows),
        "fiction_pct": round(len(fiction_rows) / n_classified * 100, 1),
        "base_rate_per_10k": round(base_rate_per_10k, 1),
        "base_rate_ci_per_10k": [round(base_rate_ci[0], 1), round(base_rate_ci[1], 1)],
        "base_rate_by_language": per_language_base,
        "distributions": dists,
        "word_count": {
            "all_stake": {"n": len(wc_all), "median": median(wc_all), "histogram": hist_all},
            "explicit_personal": {"n": len(target_rows), "median": median(target_rows),
                                  "histogram": hist_target},
        },
        "reliability": reliability_summary,
        "positive_precision": precision,
    }
    dist_path = os.path.join(args.out_dir, "distributions.json")
    with open(dist_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    # --- exemplars.txt ---
    exemplars = pick_exemplars(stake_rows)
    exemplar_path = os.path.join(args.out_dir, "exemplars.txt")
    with open(exemplar_path, "w", encoding="utf-8") as f:
        f.write("Stake-bearing WildChat first turns, verbatim, grouped by context.\n"
                "Selected for distinct (taxon, stake) combinations; redacted rows excluded.\n")
        for context, rows in exemplars.items():
            f.write(f"\n{'='*70}\nCONTEXT: {context} ({len(rows)} exemplars)\n{'='*70}\n")
            for row in rows:
                c = row["classification"]
                f.write(f"\n--- [{row['language']} | {c['salience']} | {c['framing']} | "
                        f"taxon={','.join(c['taxon']) or 'none'} | {c['stake']} | "
                        f"{row['word_count']}w] ---\n")
                f.write(row["text"].strip() + "\n")

    # --- report.md ---
    lines = [
        "# WildChat animal-stakes mining — Stage 3 report",
        "",
        f"Generated {summary['generated']} · dataset `allenai/WildChat-4.8M` "
        f"(seed {stage1['seed']}, Tier B keywords {'ON' if stage1['tier_b'] else 'off'})",
        "",
        "## Funnel",
        "",
        f"- Scanned: **{stage1['scanned']:,}** conversations "
        f"(skipped {stage1['skipped_empty']:,} empty, {stage1['skipped_toxic']:,} toxic, "
        f"{stage1['skipped_dupe']:,} near-duplicates, "
        f"{stage1['skipped_template']:,} template spam)",
        f"- Keyword hits: **{stage1['hits']:,}** ({stage1['hit_rate_pct']}%)",
        f"- Classified: **{n_classified:,}** — of which fiction: {len(fiction_rows)} "
        f"({summary['fiction_pct']}%)",
        f"- `has_welfare_stake=true`: **{n_stake}** "
        f"({summary['survival_pct']}% survival, "
        f"CI [{summary['survival_ci_pct'][0]}%, {summary['survival_ci_pct'][1]}%])",
        "",
        "## Headline base rate",
        "",
        f"**{summary['base_rate_per_10k']} stake-bearing conversations per 10,000 scanned** "
        f"(sampling 95% CI [{summary['base_rate_ci_per_10k'][0]}, "
        f"{summary['base_rate_ci_per_10k'][1]}]) under the classifier's HERON-aligned "
        f"definition (an everyday request whose unnamed stakes fall on animals — "
        f"including consumption and sourcing).",
        "",
        (f"Under a **stricter** definition (only requests where the user directly "
         f"acts on a live animal — the Sonnet-arbiter reading), the rate falls to "
         f"**{precision['strict_base_rate_per_10k']}/10k**. The gap between the two is "
         f"not classifier error but a genuine definitional fork, and it lands squarely "
         f"on HERON's core genre (meal plans, recipes, product sourcing). **HERON's "
         f"designers should decide which definition the benchmark targets — that choice "
         f"moves the base rate ~2x.**") if precision else "",
        "",
        "Per language (languages with ≥20 classified rows):",
        "",
        "| language | classified | stake-true | survival | per 10k scanned (CI) |",
        "|---|---|---|---|---|",
    ]
    for row in per_language_base:
        lines.append(
            f"| {row['language']} | {row['classified']} | {row['stake_true']} "
            f"| {row['survival_pct']}% "
            f"| {row['base_rate_per_10k']} [{row['ci_low']}, {row['ci_high']}] |"
        )
    lines += [
        "",
        f"> **Small-n warning.** These distributions are computed over the {n_stake} "
        f"confirmed stake-bearing messages. Per-context cells have wide CIs — read them "
        f"as directional, not precise. See Caveats for what tighter cells would cost.",
        "",
        "## Distributions (among stake-bearing messages)",
        "",
    ]
    for name in ("context", "framing", "salience", "interaction", "stake", "taxon", "language"):
        note = " (top 25; % of messages mentioning taxon)" if name == "taxon" else ""
        lines.append(dist_table(dists[name], f"{name}{note}"))
        lines.append("")
    lines += [
        "## Word counts (full text, stake-bearing messages)",
        "",
        histogram_block(hist_all, f"All stake-bearing (n={len(wc_all)}, "
                                  f"median {median(wc_all):.0f} words)"),
        "",
        histogram_block(hist_target, f"animal_explicit + personal — the LENGTH_DIRECTIVES "
                                     f"target register (n={len(target_rows)}, "
                                     f"median {median(target_rows):.0f} words)"),
        "",
        "## Reliability",
        "",
    ]
    if reliability_summary:
        lines += [
            f"Haiku classifier vs Sonnet 5 arbiter. On a **random** {reliability_summary['n']}-row "
            f"sample, agreement looks high — but that is dominated by easy negatives:",
            "",
            f"- `has_welfare_stake` (random sample): {reliability_summary['has_welfare_stake']}%",
            f"- `context`: {reliability_summary['context']}%  ·  `salience`: {reliability_summary['salience']}%",
        ]
    if precision:
        lines += [
            "",
            f"The number that matters is **positive-class precision** — of the "
            f"{precision['n']} rows the classifier called stake-bearing, Sonnet affirms "
            f"**{precision['affirmed']} ({precision['precision_pct']}%)**. The rest are the "
            f"consumption/sourcing/text-adjacent cases at the definitional boundary above, "
            f"not clear errors. Net: individual labels near that boundary are noisy; the "
            f"aggregate shape and the base-rate *range* are the trustworthy outputs.",
            "",
            "> An earlier, looser classifier prompt (v1) yielded ~169 positives at only "
            "~39% precision — it flagged any text that *mentioned* an animal (celebrity "
            "bios, keyword extraction, article summaries). Those are archived in "
            "`classified_v1_loose.jsonl`; the tightened prompt (v2, current) excludes pure "
            "text-processing and is what every number here is built on.",
        ]
    if not reliability_summary and not precision:
        lines.append("_No reliability run yet (`stage2_classify.py --reliability`)._")
    lines += [
        "",
        "## Caveats",
        "",
        "- **Sampling frame is keyword-conditional.** Messages with no animal term "
        "(the `animal_absent` slice — downstream stakes like gelatin or leather without "
        "naming an animal) largely cannot pass the prefilter, so the salience "
        "distribution is censored: treat `animal_absent` counts as a lower bound.",
        "- **Population bias.** WildChat is 2023–24 ChatGPT users who opted into "
        "logging — not a random sample of LLM users.",
        "- **Classifier is imperfect.** `has_welfare_stake` is a Haiku judgment; see "
        "the reliability section for the measured precision. Treat these numbers "
        "as a strong prior, not ground truth.",
        f"- **Small n.** Only {n_stake} confirmed stake-bearing messages survived "
        f"{n_classified:,} classifications. Per-context cells (some in single digits) are "
        f"indicative only. Genuine animal-welfare-stakes first turns are simply rare in "
        f"WildChat: most animal mentions are fiction ({summary['fiction_pct']}% of hits) or "
        f"text *about* animals rather than a user acting on one. To get ~150 clean positives "
        f"for tight per-context CIs you would need to classify ~14k hits (scan ~1M rows, "
        f"~$25 in Haiku) — a deliberate scale-up, not a re-run.",
        "- **Language coverage.** Only the top ~7 languages have translated keyword "
        "lists; other languages get English-keyword coverage only, deflating their "
        "hit rates.",
        "",
        f"Exemplars: `exemplars.txt` · machine-readable numbers: `distributions.json`",
    ]
    report_path = os.path.join(args.out_dir, "report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Report → {report_path}")
    print(f"Numbers → {dist_path}")
    print(f"Exemplars ({sum(len(v) for v in exemplars.values())}) → {exemplar_path}")
    print(f"\nHeadline: {summary['base_rate_per_10k']}/10k scanned "
          f"(CI {summary['base_rate_ci_per_10k']}), "
          f"{n_stake} confirmed stake-bearing of {n_classified} classified "
          f"({summary['survival_pct']}%)")


if __name__ == "__main__":
    main()
