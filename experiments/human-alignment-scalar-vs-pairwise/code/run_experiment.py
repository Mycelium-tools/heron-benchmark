"""Compare Claude Opus scalar-derived and direct pairwise preferences to a human."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from anthropic import AsyncAnthropic
from dotenv import load_dotenv

EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = EXPERIMENT_DIR.parents[1]
HUMAN_DIR = REPO_ROOT / "experiments" / "pairwise-human-feasibility" / "results"
CROSS_RESULTS = REPO_ROOT / "experiments" / "cross-family-judge-selection" / "results"
PAIRWISE_SCORER = (
    REPO_ROOT / "experiments" / "pairwise-llm-judge-consistency" / "code" / "pairwise_scorer.py"
)
DEFAULT_HUMAN_RESULTS = Path(
    "/Users/chadbrouze/Downloads/heron-pairwise-human-results-2026-07-31.json"
)
DEFAULT_RESULTS = EXPERIMENT_DIR / "results"
EXCLUDED_CANONICAL_PAIRS = {"pair-03", "pair-04"}
MODEL = "claude-opus-5"
MODEL_LABEL = "Claude Opus 5"
MAX_TOKENS = 1200


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise RuntimeError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


scorer = load_module(PAIRWISE_SCORER, "human_alignment_pairwise_scorer")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def append_jsonl(path: Path, value: Any) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def iso_now() -> str:
    return datetime.now(UTC).isoformat()


def human_normalized(preference: str, key: dict[str, Any]) -> str:
    if preference == "a":
        return key["a_model"]
    if preference == "b":
        return key["b_model"]
    if preference == "equal":
        return "TIE"
    if preference == "difficult":
        return "DIFFICULT"
    raise ValueError(preference)


def scalar_preference(openai_score: float, google_score: float) -> str:
    if openai_score > google_score:
        return "gpt-5.6-sol"
    if google_score > openai_score:
        return "gemini-3.1-pro-preview"
    return "TIE"


def prepare_cases(human_path: Path) -> list[dict[str, Any]]:
    human = read_json(human_path)
    answer_key = read_json(HUMAN_DIR / "answer_key.json")["pair_key"]
    corpus = read_jsonl(CROSS_RESULTS / "corpus.jsonl")
    judgments = read_jsonl(CROSS_RESULTS / "primary_judgments.jsonl")
    corpus_by_key = {row["key"]: row for row in corpus if row.get("status") == "ok"}
    opus_scores = {
        (row["target_family"], str(row["question_id"])): row
        for row in judgments
        if row.get("status") == "ok" and row.get("judge_key") == "opus"
    }

    cases = []
    for response in human["responses"]:
        pair_id = response["pair_id"]
        if pair_id.startswith("check-") or pair_id in EXCLUDED_CANONICAL_PAIRS:
            continue
        key = answer_key[pair_id]
        qid = str(key["question_id"])
        openai = corpus_by_key[f"openai:{qid}"]
        google = corpus_by_key[f"google:{qid}"]
        openai_scalar = opus_scores[("openai", qid)]
        google_scalar = opus_scores[("google", qid)]
        cases.append(
            {
                "pair_id": pair_id,
                "question_id": qid,
                "question": openai["question"],
                "human_display_preference": response["preference"],
                "human_preference": human_normalized(response["preference"], key),
                "human_confidence": response["confidence"],
                "human_difficulty": response["difficulty"],
                "human_notes": response.get("notes", ""),
                "responses": {
                    "gpt-5.6-sol": openai["response"],
                    "gemini-3.1-pro-preview": google["response"],
                },
                "scalar": {
                    "gpt-5.6-sol": {
                        "score": openai_scalar["score"],
                        "reasoning": openai_scalar["reasoning"],
                    },
                    "gemini-3.1-pro-preview": {
                        "score": google_scalar["score"],
                        "reasoning": google_scalar["reasoning"],
                    },
                    "preference": scalar_preference(openai_scalar["score"], google_scalar["score"]),
                },
            }
        )
    if len(cases) != 8:
        raise RuntimeError(f"Expected 8 cases after exclusions, found {len(cases)}")
    return cases


async def run_calls(cases: list[dict[str, Any]], output: Path) -> None:
    existing = {row["key"] for row in read_jsonl(output)} if output.exists() else set()
    client = AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"], timeout=300.0, max_retries=3)
    for case in cases:
        for order in ("forward", "reverse"):
            key = f'{case["pair_id"]}:{order}'
            if key in existing:
                continue
            if order == "forward":
                a_model, b_model = "gpt-5.6-sol", "gemini-3.1-pro-preview"
            else:
                a_model, b_model = "gemini-3.1-pro-preview", "gpt-5.6-sol"
            prompt = scorer.build_pairwise_prompt(
                case["question"], case["responses"][a_model], case["responses"][b_model]
            )
            started = time.monotonic()
            message = await client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}],
                thinking={"type": "adaptive"},
                output_config={"effort": "low"},
            )
            text = "\n".join(block.text for block in message.content if block.type == "text").strip()
            parsed = scorer.parse_pairwise_judgment(text)
            if not parsed.format_valid:
                raise RuntimeError(f"Unparseable response for {key}: {text}")
            append_jsonl(
                output,
                {
                    "key": key,
                    "pair_id": case["pair_id"],
                    "question_id": case["question_id"],
                    "order": order,
                    "judge_model": MODEL,
                    "judge_effort": "low",
                    "response_a_model": a_model,
                    "response_b_model": b_model,
                    "preference": parsed.preference,
                    "normalized_preference": scorer.normalize_preference(parsed.preference, a_model, b_model),
                    "reasoning": parsed.reasoning,
                    "response_text": text,
                    "format_valid": parsed.format_valid,
                    "usage": message.usage.model_dump(exclude_none=True),
                    "latency_seconds": round(time.monotonic() - started, 3),
                    "completed_at": iso_now(),
                },
            )
            print(f"completed {key}", flush=True)


def analyze(cases: list[dict[str, Any]], judgments_path: Path) -> dict[str, Any]:
    judgments = {(row["pair_id"], row["order"]): row for row in read_jsonl(judgments_path)}
    rows = []
    for case in cases:
        forward = judgments[(case["pair_id"], "forward")]
        reverse = judgments[(case["pair_id"], "reverse")]
        stable = forward["normalized_preference"] == reverse["normalized_preference"]
        pairwise_preference = forward["normalized_preference"] if stable else "POSITION_UNSTABLE"
        assessable = case["human_preference"] != "DIFFICULT"
        rows.append(
            {
                **case,
                "pairwise": {
                    "forward": forward,
                    "reverse": reverse,
                    "position_stable": stable,
                    "preference": pairwise_preference,
                },
                "assessable": assessable,
                "scalar_agrees_with_human": assessable and case["scalar"]["preference"] == case["human_preference"],
                "pairwise_agrees_with_human": assessable and pairwise_preference == case["human_preference"],
            }
        )
    assessable_rows = [row for row in rows if row["assessable"]]
    scalar_correct = sum(row["scalar_agrees_with_human"] for row in assessable_rows)
    pairwise_correct = sum(row["pairwise_agrees_with_human"] for row in assessable_rows)
    unstable = sum(not row["pairwise"]["position_stable"] for row in rows)
    return {
        "experiment_id": "human-alignment-scalar-vs-pairwise-v1",
        "generated_at": iso_now(),
        "included_cases": len(rows),
        "assessable_human_preferences": len(assessable_rows),
        "excluded_repeat_cases": sorted(EXCLUDED_CANONICAL_PAIRS),
        "unassessable_difficult_cases": len(rows) - len(assessable_rows),
        "scalar_agreement": {"count": scalar_correct, "total": len(assessable_rows), "percentage": 100 * scalar_correct / len(assessable_rows)},
        "pairwise_agreement": {"count": pairwise_correct, "total": len(assessable_rows), "percentage": 100 * pairwise_correct / len(assessable_rows)},
        "pairwise_position_instability": {"count": unstable, "total": len(rows), "percentage": 100 * unstable / len(rows)},
        "paired_outcomes": {
            "both_correct": sum(row["scalar_agrees_with_human"] and row["pairwise_agrees_with_human"] for row in assessable_rows),
            "scalar_only_correct": sum(row["scalar_agrees_with_human"] and not row["pairwise_agrees_with_human"] for row in assessable_rows),
            "pairwise_only_correct": sum(not row["scalar_agrees_with_human"] and row["pairwise_agrees_with_human"] for row in assessable_rows),
            "neither_correct": sum(not row["scalar_agrees_with_human"] and not row["pairwise_agrees_with_human"] for row in assessable_rows),
        },
        "cases": rows,
    }


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--human-results", type=Path, default=DEFAULT_HUMAN_RESULTS)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS)
    args = parser.parse_args()
    load_dotenv(REPO_ROOT / ".env")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY is required")
    args.results_dir.mkdir(parents=True, exist_ok=True)
    cases = prepare_cases(args.human_results)
    frozen = args.results_dir / "frozen_inputs"
    frozen.mkdir(parents=True, exist_ok=True)
    write_json(frozen / "cases.json", cases)
    shutil.copy2(EXPERIMENT_DIR / "experiment_spec.md", frozen / "experiment_spec.md")
    shutil.copy2(PAIRWISE_SCORER, frozen / "pairwise_scorer.py")
    judgments_path = args.results_dir / "pairwise_judgments.jsonl"
    await run_calls(cases, judgments_path)
    analysis = analyze(cases, judgments_path)
    write_json(args.results_dir / "analysis.json", analysis)
    write_json(
        args.results_dir / "manifest.json",
        {
            "experiment_id": analysis["experiment_id"],
            "created_at": iso_now(),
            "judge_model": MODEL,
            "judge_effort": "low",
            "new_api_calls": 2 * len(cases),
            "hashes": {
                "human_results": sha256(args.human_results),
                "answer_key": sha256(HUMAN_DIR / "answer_key.json"),
                "source_corpus": sha256(CROSS_RESULTS / "corpus.jsonl"),
                "source_scalar_judgments": sha256(CROSS_RESULTS / "primary_judgments.jsonl"),
                "pairwise_scorer": sha256(PAIRWISE_SCORER),
            },
        },
    )
    print(json.dumps({k: analysis[k] for k in ("scalar_agreement", "pairwise_agreement", "pairwise_position_instability", "paired_outcomes")}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
