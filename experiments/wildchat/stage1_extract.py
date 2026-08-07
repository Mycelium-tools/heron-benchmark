"""
Stage 1 — stream WildChat-4.8M and keyword-prefilter first user turns.

Streams allenai/WildChat-4.8M (no full download) with a seeded shuffle (the
dataset is roughly chronological; a prefix would skew early-2023). For each
conversation, takes ONLY the first user turn, skips empty/toxic/near-duplicate
messages, and keeps rows matching the per-language animal keyword lists in
keywords.py.

Outputs (in --out-dir, default experiments/wildchat/out/):
  prefiltered.jsonl   one record per keyword hit (full text + metadata + matched terms)
  stage1_stats.json   denominators for the stage-3 base rate (scanned, skipped, hits per language)

Usage (from repo root):
    python experiments/wildchat/stage1_extract.py                    # full: 300k scan / 3000 hits
    python experiments/wildchat/stage1_extract.py --max-scan 5000    # smoke test
"""

import argparse
import hashlib
import json
import os
import random
import re
import sys
import time
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keywords import (
    TIER_A_BY_LANGUAGE,
    TIER_A_ENGLISH,
    TIER_B_BY_LANGUAGE,
    TIER_B_ENGLISH,
)

DATASET = "allenai/WildChat-4.8M"
CJK_LANGUAGES = {"Chinese"}  # substring match — no word boundaries

# Known WildChat template spam. These circulate in many near-identical variants
# that survive prefix dedup, and animal words inside the template text (e.g. the
# Midjourney template's fur/dog examples — half of all hits in the smoke run)
# would flood the classification budget with guaranteed non-stakes.
TEMPLATE_BLOCKLIST = re.compile(
    "|".join([
        r"as a prompt generator for a generative ai",
        r"image prompts for the ai to visualize",
        r"ignore all the instructions you got before",
        r"you are going to act as chatgpt with (?:developer mode|dan mode)",
        r"a fictional character called dan who answers all requests",
    ]),
    re.IGNORECASE,
)


def compile_matchers(include_tier_b: bool = False) -> dict[str, re.Pattern]:
    """Compile one alternation regex per language, plus the universal English one.

    The English pattern (key "") is applied to every row regardless of language;
    language-specific patterns are applied only to rows with that language.
    """
    english = list(TIER_A_ENGLISH) + (TIER_B_ENGLISH if include_tier_b else [])
    # Leading \b makes every bare fragment a word-PREFIX match (see keywords.py);
    # without it "hen" matches inside "when" and "lion" inside "million".
    matchers = {"": re.compile(rf"\b(?:{'|'.join(english)})", re.IGNORECASE)}
    for lang, terms in TIER_A_BY_LANGUAGE.items():
        fragments = list(terms)
        if include_tier_b:
            fragments += TIER_B_BY_LANGUAGE.get(lang, [])
        if lang in CJK_LANGUAGES:
            pattern = "|".join(re.escape(t) for t in fragments)
        else:
            pattern = rf"\b(?:{'|'.join(fragments)})"
        matchers[lang] = re.compile(pattern, re.IGNORECASE)
    return matchers


def match_terms(text: str, language: str, matchers: dict[str, re.Pattern]) -> list[str]:
    """Return distinct matched keyword strings (empty list = no hit)."""
    lowered = text.lower()
    found: list[str] = []
    seen = set()
    for key in ("", language):
        pattern = matchers.get(key)
        if pattern is None:
            continue
        for m in pattern.findall(lowered):
            if m and m not in seen:
                seen.add(m)
                found.append(m)
                if len(found) >= 10:
                    return found
    return found


def normalize_for_dedup(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()[:500]


def first_user_turn(conversation) -> str | None:
    for message in conversation or []:
        if message.get("role") == "user":
            return message.get("content") or ""
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-scan", type=int, default=300_000)
    parser.add_argument("--max-hits", type=int, default=3_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--shuffle-buffer", type=int, default=10_000)
    parser.add_argument("--tier-b", action="store_true",
                        help="Also match the ambiguous Tier B keyword lists")
    parser.add_argument("--sample-print", type=int, default=20)
    parser.add_argument("--out-dir",
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"))
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    prefiltered_path = os.path.join(args.out_dir, "prefiltered.jsonl")
    stats_path = os.path.join(args.out_dir, "stage1_stats.json")

    matchers = compile_matchers(include_tier_b=args.tier_b)

    from datasets import load_dataset
    print(f"Streaming {DATASET} (shuffle seed={args.seed}, buffer={args.shuffle_buffer})...")
    stream = load_dataset(DATASET, split="train", streaming=True)
    stream = stream.shuffle(seed=args.seed, buffer_size=args.shuffle_buffer)

    scanned = 0
    skipped_empty = 0
    skipped_toxic = 0
    skipped_dupe = 0
    skipped_template = 0
    scanned_by_language: Counter = Counter()
    hits_by_language: Counter = Counter()
    term_counts: Counter = Counter()
    seen_hashes: set[str] = set()
    # Templated prompts (same opening, varying payload) survive full-prefix dedup;
    # cap hits sharing a short normalized prefix so one template can't eat the budget.
    hit_prefix_counts: Counter = Counter()
    hits: list[dict] = []

    t0 = time.time()

    def build_stats() -> dict:
        return {
            "dataset": DATASET,
            "seed": args.seed,
            "tier_b": args.tier_b,
            "scanned": scanned,
            "skipped_empty": skipped_empty,
            "skipped_toxic": skipped_toxic,
            "skipped_dupe": skipped_dupe,
            "skipped_template": skipped_template,
            "hits": len(hits),
            "hit_rate_pct": round(len(hits) / scanned * 100, 3) if scanned else 0.0,
            "elapsed_seconds": round(time.time() - t0, 1),
            "scanned_by_language": dict(scanned_by_language.most_common()),
            "hits_by_language": dict(hits_by_language.most_common()),
            "top_matched_terms": dict(term_counts.most_common(40)),
        }

    def write_stats():
        with open(stats_path, "w", encoding="utf-8") as f:
            json.dump(build_stats(), f, indent=2, ensure_ascii=False)

    with open(prefiltered_path, "w", encoding="utf-8") as out:
        for row in stream:
            if scanned >= args.max_scan or len(hits) >= args.max_hits:
                break
            scanned += 1

            if scanned % 10_000 == 0:
                elapsed = time.time() - t0
                rate = scanned / elapsed
                eta = (args.max_scan - scanned) / rate
                hit_rate = len(hits) / scanned * 100
                print(
                    f"  scanned {scanned:,} | {rate:,.0f} rows/s | ETA {eta/60:.1f} min "
                    f"| hits {len(hits):,} ({hit_rate:.2f}%) | "
                    f"top langs: {dict(hits_by_language.most_common(3))}",
                    flush=True,
                )
                # Checkpoint so a killed run keeps consistent denominators, and
                # flush hits so prefiltered.jsonl never ends mid-line.
                out.flush()
                write_stats()

            if row.get("toxic"):
                skipped_toxic += 1
                continue

            text = first_user_turn(row.get("conversation"))
            if text is None or not text.strip():
                skipped_empty += 1
                continue

            language = row.get("language") or "unknown"
            scanned_by_language[language] += 1

            dedup_key = hashlib.md5(normalize_for_dedup(text).encode()).hexdigest()
            if dedup_key in seen_hashes:
                skipped_dupe += 1
                continue
            seen_hashes.add(dedup_key)

            if TEMPLATE_BLOCKLIST.search(text):
                skipped_template += 1
                continue

            terms = match_terms(text, language, matchers)
            if not terms:
                continue

            hit_prefix = normalize_for_dedup(text)[:150]
            if hit_prefix_counts[hit_prefix] >= 2:
                skipped_template += 1
                continue
            hit_prefix_counts[hit_prefix] += 1

            record = {
                "conversation_hash": row.get("conversation_hash"),
                "text": text,
                "language": language,
                "country": row.get("country"),
                "timestamp": str(row.get("timestamp")),
                "model": row.get("model"),
                "redacted": bool(row.get("redacted")),
                "matched_terms": terms,
                "word_count": len(text.split()),
            }
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            hits.append(record)
            hits_by_language[language] += 1
            term_counts.update(terms)

    elapsed = time.time() - t0
    stats = build_stats()
    write_stats()

    print(f"\n{'='*70}")
    print(f"Scanned {scanned:,} rows in {elapsed/60:.1f} min "
          f"({scanned/elapsed:,.0f} rows/s)")
    print(f"Skipped: {skipped_empty:,} empty, {skipped_toxic:,} toxic, "
          f"{skipped_dupe:,} near-duplicates, {skipped_template:,} template spam")
    print(f"Hits: {len(hits):,} ({stats['hit_rate_pct']}%) → {prefiltered_path}")
    print(f"Top matched terms: {dict(term_counts.most_common(15))}")
    print(f"Hits by language: {dict(hits_by_language.most_common(10))}")
    print(f"Stats → {stats_path}")

    if hits:
        n = min(args.sample_print, len(hits))
        print(f"\n{'='*70}\n{n} RANDOM HITS (eyeball for false positives):\n{'='*70}")
        rng = random.Random(args.seed)
        for record in rng.sample(hits, n):
            preview = re.sub(r"\s+", " ", record["text"])[:220]
            print(f"\n[{record['language']}] matched {record['matched_terms']}")
            print(f"  {preview}")


if __name__ == "__main__":
    main()
