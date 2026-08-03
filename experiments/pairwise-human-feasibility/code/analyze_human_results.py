#!/usr/bin/env python3
"""Compute descriptive pilot statistics from an exported human-results JSON."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path

EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
ANSWER_KEY = EXPERIMENT_DIR / "results" / "answer_key.json"


def normalized_choice(response: dict, key: dict) -> str:
    choice = response["preference"]
    if choice in {"equal", "difficult"}:
        return choice
    return key[f"{choice}_family"]


def pct(count: int, total: int) -> float:
    return round(100 * count / total, 1) if total else 0.0


def analyze(results_path: Path) -> dict:
    results = json.loads(results_path.read_text(encoding="utf-8"))
    answer_key = json.loads(ANSWER_KEY.read_text(encoding="utf-8"))["pair_key"]
    responses = [row for row in results["responses"] if row]
    unique = [row for row in responses if not answer_key[row["pair_id"]]["is_repeat"]]

    preferences = Counter(row["preference"] for row in unique)
    confidence = Counter(row["confidence"] for row in unique)
    difficulty = Counter(row["difficulty"] for row in unique)
    clear = preferences["a"] + preferences["b"]

    repeats = []
    response_by_pair = {row["pair_id"]: row for row in responses}
    for pair_id, key in answer_key.items():
        if not key["is_repeat"] or pair_id not in response_by_pair:
            continue
        original_id = key["canonical_pair_id"]
        if original_id not in response_by_pair:
            continue
        original = response_by_pair[original_id]
        repeated = response_by_pair[pair_id]
        original_choice = normalized_choice(original, answer_key[original_id])
        repeat_choice = normalized_choice(repeated, key)
        repeats.append(
            {
                "original_pair_id": original_id,
                "repeat_pair_id": pair_id,
                "original_choice": original_choice,
                "repeat_choice": repeat_choice,
                "consistent": original_choice == repeat_choice,
            }
        )

    elapsed = [row["elapsed_seconds"] for row in unique]
    return {
        "experiment_id": results["experiment_id"],
        "completed_at": results["completed_at"],
        "unique_comparisons_completed": len(unique),
        "clear_preferences": {"count": clear, "percentage": pct(clear, len(unique))},
        "approximately_equal": {
            "count": preferences["equal"],
            "percentage": pct(preferences["equal"], len(unique)),
        },
        "difficult_to_determine": {
            "count": preferences["difficult"],
            "percentage": pct(preferences["difficult"], len(unique)),
        },
        "preference_distribution": dict(preferences),
        "confidence_distribution": dict(confidence),
        "difficulty_distribution": dict(difficulty),
        "median_seconds_per_unique_comparison": (
            round(statistics.median(elapsed), 1) if elapsed else None
        ),
        "repeat_consistency": {
            "consistent": sum(row["consistent"] for row in repeats),
            "total": len(repeats),
            "details": repeats,
        },
        "final_reflection": results["reflection"],
        "notes": [
            {
                "pair_id": row["pair_id"],
                "question_id": row["question_id"],
                "note": row["notes"],
            }
            for row in unique
            if row["notes"]
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("results_json", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    summary = analyze(args.results_json)
    text = json.dumps(summary, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
