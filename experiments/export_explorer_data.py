"""Export rescored prototype rows as compact JSON for the site explorer."""

from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "logs" / "prototype_20_seed_2026-08-04_rescored"
OUTPUT = ROOT / "site" / "app" / "explorer" / "evaluation-data.json"

MODEL_ORDER = {
    "openai/gpt-5.6-luna": 0,
    "anthropic/claude-sonnet-5": 1,
    "google/gemini-3.6-flash": 2,
}

MODEL_LABELS = {
    "openai/gpt-5.6-luna": "Luna",
    "anthropic/claude-sonnet-5": "Claude Sonnet",
    "google/gemini-3.6-flash": "Gemini Flash",
}

JUDGE_LABELS = {
    "google/gemini-3.1-pro-preview": "Gemini 3.1 Pro",
    "openai/gpt-5.6-sol": "GPT-5.6 Sol",
}


def main() -> None:
    rows: list[dict[str, object]] = []
    for path in sorted(SOURCE.glob("*.csv")):
        with path.open(newline="") as handle:
            for source in csv.DictReader(handle):
                model = source["model"]
                judge = source["judge_model"]
                rows.append(
                    {
                        "sampleId": int(source["sample_id"]),
                        "prompt": source["input"],
                        "model": model,
                        "modelLabel": MODEL_LABELS[model],
                        "response": source["output_completion"],
                        "score": float(source["moral_consideration"]),
                        "classification": source["proportionality_classification"],
                        "judge": judge,
                        "judgeLabel": JUDGE_LABELS[judge],
                        "judgeExplanation": source["score_explanation"],
                        "judgeResponse": source["judge_response"],
                        "judgeFormatValid": source["judge_format_valid"] == "True",
                    }
                )

    rows.sort(key=lambda row: (row["sampleId"], MODEL_ORDER[str(row["model"])]))
    if len(rows) != 60:
        raise RuntimeError(f"Expected 60 rescored rows, found {len(rows)}")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
    print(f"Wrote {len(rows)} rows to {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
