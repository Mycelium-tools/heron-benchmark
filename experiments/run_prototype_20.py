"""Run the 20-seed HERON launch-page prototype evaluation.

This keeps the customer-discovery run separate from the benchmark defaults.
Each target receives one response per seed at minimal reasoning effort, and the
existing HERON scorer makes one judging call for every response.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC_DIR = _REPO_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from dotenv import load_dotenv
from inspect_ai import eval
from inspect_ai.model import GenerateConfig, get_model

from heron.eval import heron_full, load_samples


TARGET_SPECS = [
    ("anthropic/claude-sonnet-5", "minimal"),
    # Luna does not expose "minimal"; "none" is its lowest supported setting.
    ("openai/gpt-5.6-luna", "none"),
    ("google/gemini-3.6-flash", "minimal"),
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--log-dir",
        default="logs/prototype_20_seed_2026-08-04",
        help="Directory for Inspect .eval logs.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Optional smoke-test limit; omit to run all 20 synced seeds.",
    )
    args = parser.parse_args()

    load_dotenv()
    sample_count = len(load_samples())
    if sample_count != 20:
        raise RuntimeError(
            f"Expected the synced 20-seed set, but samples.json has {sample_count} rows."
        )

    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    models = [
        get_model(model, config=GenerateConfig(reasoning_effort=reasoning_effort))
        for model, reasoning_effort in TARGET_SPECS
    ]

    eval(
        heron_full(),
        model=models,
        log_dir=str(log_dir),
        limit=args.limit,
        epochs=1,
        max_tasks=3,
        max_samples=4,
        timeout=180,
        retry_on_error=2,
        fail_on_error=False,
        metadata={
            "release": "pilot-20",
            "target_reasoning_effort": {
                model: reasoning_effort
                for model, reasoning_effort in TARGET_SPECS
            },
            "judge_calls_per_response": 1,
        },
    )


if __name__ == "__main__":
    main()
