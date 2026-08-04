"""Rescore the saved 20-seed prototype responses with the current HERON judge.

The original response logs remain unchanged. Rescored logs are written to a
separate directory so the before/after judge change is auditable.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import subprocess

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = REPO_ROOT / "logs" / "prototype_20_seed_2026-08-04"
DEFAULT_OUTPUT = REPO_ROOT / "logs" / "prototype_20_seed_2026-08-04_rescored"
SCORER = "src/heron/scorer.py@heron_scorer"


def rescore(log_path: Path, output_dir: Path) -> Path:
    output_path = output_dir / f"{log_path.stem}-rescored.eval"
    if output_path.exists() and output_path.stat().st_size > 0:
        return output_path
    inspect = Path(os.sys.executable).with_name("inspect")
    subprocess.run(
        [
            str(inspect),
            "score",
            str(log_path),
            "--scorer",
            SCORER,
            "--action",
            "overwrite",
            "--output-file",
            str(output_path),
            "--stream",
            "4",
            "--display",
            "plain",
        ],
        cwd=REPO_ROOT,
        check=True,
        env=os.environ.copy(),
    )
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    load_dotenv(REPO_ROOT / ".env")
    source_logs = sorted(args.source.glob("*.eval"))
    if len(source_logs) != 3:
        raise RuntimeError(f"Expected 3 target-model logs, found {len(source_logs)}")

    args.output.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=3) as executor:
        outputs = list(executor.map(lambda path: rescore(path, args.output), source_logs))

    print("Rescored logs:")
    for output in outputs:
        print(output.relative_to(REPO_ROOT))


if __name__ == "__main__":
    main()
