"""Run the pairwise-versus-scalar judge-consistency experiment.

The runner reuses the frozen corpus and scalar judgments from the preceding
experiment. It makes pairwise calls only to Google and OpenAI, is resumable, and
runs both response orders for every judge and scenario.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import time
from collections import Counter
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types as google_types
from openai import AsyncOpenAI

EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = EXPERIMENT_DIR.parents[1]
SOURCE_RESULTS = (
    REPO_ROOT
    / "experiments"
    / "cross-family-judge-selection"
    / "results"
)
SOURCE_CORPUS = SOURCE_RESULTS / "corpus.jsonl"
SOURCE_SCALARS = SOURCE_RESULTS / "primary_judgments.jsonl"
SCORER_PATH = Path(__file__).with_name("pairwise_scorer.py")
SPEC_PATH = EXPERIMENT_DIR / "experiment_spec.md"
DEFAULT_RESULTS = EXPERIMENT_DIR / "results" / "full"
SCALAR_TIE_THRESHOLD = 0.15
MAX_TOKENS = 4096
CONCURRENCY = 6
MAX_ATTEMPTS = 5

JUDGES = {
    "flash": {
        "label": "Gemini 3.6 Flash",
        "family": "google",
        "provider": "google",
        "model": "gemini-3.6-flash",
        "reasoning": "minimal",
    },
    "pro": {
        "label": "Gemini 3.1 Pro Preview",
        "family": "google",
        "provider": "google",
        "model": "gemini-3.1-pro-preview",
        "reasoning": "medium",
    },
    "luna": {
        "label": "GPT-5.6 Luna",
        "family": "openai",
        "provider": "openai",
        "model": "gpt-5.6-luna",
        "reasoning": "none",
    },
    "sol": {
        "label": "GPT-5.6 Sol",
        "family": "openai",
        "provider": "openai",
        "model": "gpt-5.6-sol",
        "reasoning": "medium",
    },
}

TRACKS = {
    "gemini": {
        "response_families": ("openai", "anthropic"),
        "response_labels": ("GPT-5.6 Sol", "Claude Opus 5"),
        "judges": ("flash", "pro"),
    },
    "openai": {
        "response_families": ("google", "anthropic"),
        "response_labels": ("Gemini 3.1 Pro Preview", "Claude Opus 5"),
        "judges": ("luna", "sol"),
    },
}

PRICES = {
    "gemini-3.6-flash": {"input": 1.50, "output": 7.50},
    "gemini-3.1-pro-preview": {"input": 2.00, "output": 12.00},
    "gpt-5.6-luna": {"input": 1.00, "output": 6.00},
    "gpt-5.6-sol": {"input": 5.00, "output": 30.00},
}


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise RuntimeError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


pairwise_scorer = load_module(SCORER_PATH, "pairwise_experiment_scorer")


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def append_jsonl(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def sanitize_raw(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: sanitize_raw(item)
            for key, item in value.items()
            if key not in {"thought_signature", "thoughtSignature"}
        }
    if isinstance(value, list):
        return [sanitize_raw(item) for item in value]
    return value


def google_usage(response: Any) -> dict[str, Any]:
    usage = getattr(response, "usage_metadata", None)
    if usage is None:
        return {}
    raw = usage.model_dump(exclude_none=True)
    return {
        "input_tokens": raw.get("prompt_token_count", 0),
        "output_tokens": raw.get("candidates_token_count", 0),
        "reasoning_tokens": raw.get("thoughts_token_count", 0),
        "raw": raw,
    }


def openai_usage(response: Any) -> dict[str, Any]:
    return response.usage.model_dump(exclude_none=True) if response.usage else {}


async def with_retries(
    label: str, call: Callable[[], Awaitable[dict[str, Any]]]
) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return await call()
        except Exception as error:  # noqa: BLE001
            last_error = error
            status = getattr(error, "status_code", None)
            if status is None:
                status = getattr(getattr(error, "response", None), "status_code", None)
            if status not in {None, 408, 409, 429, 500, 502, 503, 504}:
                break
            if attempt == MAX_ATTEMPTS:
                break
            delay = 2**attempt
            print(f"{label}: retrying in {delay}s", flush=True)
            await asyncio.sleep(delay)
    assert last_error is not None
    raise last_error


class Providers:
    """Google and OpenAI only; Anthropic calls are impossible in this runner."""

    def __init__(self) -> None:
        google_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get(
            "GEMINI_API_KEY"
        )
        openai_key = os.environ.get("OPENAI_API_KEY")
        if not google_key or not openai_key:
            raise RuntimeError("GOOGLE_API_KEY and OPENAI_API_KEY are required")
        self.google = genai.Client(api_key=google_key)
        self.openai = AsyncOpenAI(
            api_key=openai_key,
            timeout=300.0,
            max_retries=0,
        )

    async def call(
        self, judge: dict[str, str], prompt: str
    ) -> dict[str, Any]:
        if judge["provider"] == "google":
            response = await self.google.aio.models.generate_content(
                model=judge["model"],
                contents=prompt,
                config=google_types.GenerateContentConfig(
                    max_output_tokens=MAX_TOKENS,
                    thinking_config=google_types.ThinkingConfig(
                        thinking_level=judge["reasoning"]
                    ),
                ),
            )
            raw = response.model_dump(mode="json", exclude_none=True)
            candidates = raw.get("candidates", [])
            finish = candidates[0].get("finish_reason") if candidates else None
            if finish != "STOP":
                raise RuntimeError(f"Gemini returned finish_reason={finish}")
            return {
                "text": (response.text or "").strip(),
                "usage": google_usage(response),
                "raw": sanitize_raw(raw),
            }
        if judge["provider"] == "openai":
            response = await self.openai.responses.create(
                model=judge["model"],
                input=prompt,
                max_output_tokens=MAX_TOKENS,
                reasoning={"effort": judge["reasoning"]},
            )
            if response.status != "completed":
                raise RuntimeError(f"OpenAI returned status={response.status}")
            return {
                "text": (response.output_text or "").strip(),
                "usage": openai_usage(response),
                "raw": sanitize_raw(response.model_dump(mode="json", exclude_none=True)),
            }
        raise RuntimeError(f"Forbidden provider: {judge['provider']}")


def scalar_preference(
    score_1: float, score_2: float, label_1: str, label_2: str
) -> str:
    if abs(score_1 - score_2) <= SCALAR_TIE_THRESHOLD + 1e-12:
        return "TIE"
    return label_1 if score_1 > score_2 else label_2


def load_frozen_inputs(limit: int) -> tuple[list[dict], list[dict]]:
    corpus = read_jsonl(SOURCE_CORPUS)
    scalars = read_jsonl(SOURCE_SCALARS)
    if len(corpus) != 90 or len(scalars) != 360:
        raise RuntimeError("Source experiment is incomplete")
    if not all(row.get("format_valid") for row in scalars):
        raise RuntimeError("Source scalar judgments contain malformed output")

    question_ids = sorted(
        {row["question_id"] for row in corpus}, key=lambda value: int(value)
    )[:limit]
    corpus_by_key = {row["key"]: row for row in corpus}
    scalar_by_key = {row["key"]: row for row in scalars}
    pairs = []
    baseline = []

    for track_key, track in TRACKS.items():
        family_1, family_2 = track["response_families"]
        label_1, label_2 = track["response_labels"]
        for question_id in question_ids:
            response_1 = corpus_by_key[f"{family_1}:{question_id}"]
            response_2 = corpus_by_key[f"{family_2}:{question_id}"]
            if response_1["question"] != response_2["question"]:
                raise RuntimeError("Question mismatch in frozen response pair")
            pair_key = f"{track_key}:{question_id}"
            pairs.append(
                {
                    "pair_key": pair_key,
                    "track": track_key,
                    "question_id": question_id,
                    "question": response_1["question"],
                    "response_1_family": family_1,
                    "response_1_label": label_1,
                    "response_1_model": response_1["target_model"],
                    "response_1": response_1["response"],
                    "response_1_sha256": response_1["conversation_sha256"],
                    "response_2_family": family_2,
                    "response_2_label": label_2,
                    "response_2_model": response_2["target_model"],
                    "response_2": response_2["response"],
                    "response_2_sha256": response_2["conversation_sha256"],
                }
            )
            for judge_key in track["judges"]:
                judge = JUDGES[judge_key]
                if judge["family"] in {family_1, family_2}:
                    raise RuntimeError("Same-family judge detected")
                scalar_1 = scalar_by_key[f"{family_1}:{question_id}:{judge_key}"]
                scalar_2 = scalar_by_key[f"{family_2}:{question_id}:{judge_key}"]
                baseline.append(
                    {
                        "key": f"{pair_key}:{judge_key}",
                        "pair_key": pair_key,
                        "track": track_key,
                        "question_id": question_id,
                        "judge_key": judge_key,
                        "judge_model": judge["model"],
                        "response_1_score": scalar_1["score"],
                        "response_2_score": scalar_2["score"],
                        "scalar_preference": scalar_preference(
                            scalar_1["score"], scalar_2["score"], label_1, label_2
                        ),
                        "source_judgment_keys": [scalar_1["key"], scalar_2["key"]],
                    }
                )
    return pairs, baseline


def settings(limit: int) -> dict[str, Any]:
    return {
        "scenario_limit": limit,
        "tracks": TRACKS,
        "judges": JUDGES,
        "max_tokens": MAX_TOKENS,
        "concurrency": CONCURRENCY,
        "scalar_tie_threshold": SCALAR_TIE_THRESHOLD,
        "orders": ["forward", "reverse"],
        "sampling_parameters": "temperature, top_p, and top_k omitted",
        "allowed_providers": ["google", "openai"],
    }


def prepare_results(
    results_dir: Path, pairs: list[dict], baseline: list[dict], limit: int
) -> None:
    manifest_path = results_dir / "manifest.json"
    hashes = {
        "source_corpus": sha256_file(SOURCE_CORPUS),
        "source_scalars": sha256_file(SOURCE_SCALARS),
        "pairwise_scorer": sha256_file(SCORER_PATH),
        "experiment_spec": sha256_file(SPEC_PATH),
        "settings": sha256_text(json.dumps(settings(limit), sort_keys=True)),
    }
    if manifest_path.exists():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        if existing["hashes"] != hashes:
            raise RuntimeError("Refusing to resume because frozen inputs changed")
        return

    results_dir.mkdir(parents=True, exist_ok=False)
    frozen = results_dir / "frozen_inputs"
    frozen.mkdir()
    shutil.copy2(SCORER_PATH, frozen / "pairwise_scorer.py")
    shutil.copy2(SPEC_PATH, frozen / "experiment_spec.md")
    write_json(frozen / "response_pairs.json", pairs)
    write_json(frozen / "scalar_baseline.json", baseline)
    write_json(
        manifest_path,
        {
            "experiment": "Pairwise LLM Judge Consistency",
            "status": "initialized",
            "created_at": utc_now(),
            "scenario_count": limit,
            "expected_pairwise_calls": limit * 2 * 2 * 2,
            "hashes": hashes,
            "settings": settings(limit),
        },
    )


async def run_pairwise(
    providers: Providers, pairs: list[dict], results_dir: Path
) -> list[dict]:
    path = results_dir / "pairwise_judgments.jsonl"
    completed = {
        row["key"] for row in read_jsonl(path) if row.get("status") == "ok"
    }
    tasks = []
    for pair in pairs:
        for judge_key in TRACKS[pair["track"]]["judges"]:
            for order in ("forward", "reverse"):
                key = f"{pair['pair_key']}:{judge_key}:{order}"
                if key not in completed:
                    tasks.append((pair, judge_key, order))

    semaphore = asyncio.Semaphore(CONCURRENCY)
    write_lock = asyncio.Lock()
    expected = len(pairs) * 4

    async def judge_one(pair: dict, judge_key: str, order: str) -> None:
        judge = JUDGES[judge_key]
        if judge["provider"] not in {"google", "openai"}:
            raise RuntimeError("Anthropic provider route detected")
        if order == "forward":
            label_a, label_b = pair["response_1_label"], pair["response_2_label"]
            response_a, response_b = pair["response_1"], pair["response_2"]
        else:
            label_a, label_b = pair["response_2_label"], pair["response_1_label"]
            response_a, response_b = pair["response_2"], pair["response_1"]
        prompt = pairwise_scorer.build_pairwise_prompt(
            pair["question"], response_a, response_b
        )
        key = f"{pair['pair_key']}:{judge_key}:{order}"
        started = time.perf_counter()

        async def call_and_validate() -> dict[str, Any]:
            result = await providers.call(judge, prompt)
            parsed = pairwise_scorer.parse_pairwise_judgment(result["text"])
            if not parsed.format_valid:
                raise RuntimeError(f"Malformed pairwise output from {judge_key}")
            result["parsed"] = parsed
            return result

        async with semaphore:
            result = await with_retries(key, call_and_validate)
        normalized = pairwise_scorer.normalize_preference(
            result["parsed"].preference, label_a, label_b
        )
        row = {
            "status": "ok",
            "key": key,
            "pair_key": pair["pair_key"],
            "track": pair["track"],
            "question_id": pair["question_id"],
            "judge_key": judge_key,
            "judge_label": judge["label"],
            "judge_family": judge["family"],
            "judge_model": judge["model"],
            "judge_reasoning": judge["reasoning"],
            "order": order,
            "response_a_label": label_a,
            "response_b_label": label_b,
            "preference": result["parsed"].preference,
            "normalized_preference": normalized,
            "reasoning": result["parsed"].reasoning,
            "format_valid": result["parsed"].format_valid,
            "response_text": result["text"],
            "prompt_sha256": sha256_text(prompt),
            "usage": result["usage"],
            "latency_seconds": round(time.perf_counter() - started, 3),
            "completed_at": utc_now(),
            "raw_provider_response": result["raw"],
        }
        async with write_lock:
            append_jsonl(path, row)
            completed.add(key)
            print(f"Pairwise {len(completed)}/{expected} ({key})", flush=True)

    await asyncio.gather(*(judge_one(*task) for task in tasks))
    rows = read_jsonl(path)
    if len(rows) != expected or not all(row["format_valid"] for row in rows):
        raise RuntimeError("Pairwise run is incomplete")
    return rows


def rate(numerator: int, denominator: int) -> dict[str, Any]:
    return {
        "count": numerator,
        "total": denominator,
        "percentage": 100 * numerator / denominator if denominator else None,
    }


def estimate_costs(judgments: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for model, price in PRICES.items():
        model_rows = [row for row in judgments if row["judge_model"] == model]
        input_tokens = sum(
            row["usage"].get("input_tokens", 0) for row in model_rows
        )
        output_tokens = sum(
            row["usage"].get("output_tokens", 0) for row in model_rows
        )
        reasoning_tokens = sum(
            row["usage"].get("reasoning_tokens", 0) for row in model_rows
        )
        cached_tokens = sum(
            row["usage"]
            .get("input_tokens_details", {})
            .get("cached_tokens", 0)
            for row in model_rows
        )
        cache_write_tokens = sum(
            row["usage"]
            .get("input_tokens_details", {})
            .get("cache_write_tokens", 0)
            for row in model_rows
        )
        if model.startswith("gpt-"):
            regular_tokens = input_tokens - cached_tokens - cache_write_tokens
            input_cost = (
                regular_tokens * price["input"]
                + cached_tokens * price["input"] * 0.10
                + cache_write_tokens * price["input"] * 1.25
            ) / 1_000_000
        else:
            input_cost = input_tokens * price["input"] / 1_000_000
        billed_output = output_tokens + (
            reasoning_tokens if model.startswith("gemini-") else 0
        )
        output_cost = billed_output * price["output"] / 1_000_000
        rows.append(
            {
                "model": model,
                "calls": len(model_rows),
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "reasoning_tokens": reasoning_tokens,
                "cached_tokens": cached_tokens,
                "cache_write_tokens": cache_write_tokens,
                "estimated_cost_usd": input_cost + output_cost,
            }
        )
    return {
        "by_model": rows,
        "total_estimated_cost_usd": sum(
            row["estimated_cost_usd"] for row in rows
        ),
    }


def analyze(
    pairs: list[dict], baseline: list[dict], judgments: list[dict], results_dir: Path
) -> dict[str, Any]:
    scalar = {row["key"]: row for row in baseline}
    pairwise = {row["key"]: row for row in judgments}
    comparison = []
    track_summary = {}

    for track_key, track in TRACKS.items():
        track_pairs = [row for row in pairs if row["track"] == track_key]
        cheap, strong = track["judges"]
        scalar_agreement = 0
        order_agreement = Counter()
        position_consistency = Counter()
        scalar_alignment = Counter()
        stable_both = 0
        stable_agreement = 0
        scalar_ties = Counter()
        pairwise_ties = Counter()

        for pair in track_pairs:
            scalar_rows = {
                judge: scalar[f"{pair['pair_key']}:{judge}"] for judge in track["judges"]
            }
            judgments_by_judge = {
                judge: {
                    order: pairwise[f"{pair['pair_key']}:{judge}:{order}"]
                    for order in ("forward", "reverse")
                }
                for judge in track["judges"]
            }
            scalar_match = (
                scalar_rows[cheap]["scalar_preference"]
                == scalar_rows[strong]["scalar_preference"]
            )
            scalar_agreement += scalar_match
            for order in ("forward", "reverse"):
                order_agreement[order] += (
                    judgments_by_judge[cheap][order]["normalized_preference"]
                    == judgments_by_judge[strong][order]["normalized_preference"]
                )
            stable = {}
            for judge in track["judges"]:
                forward = judgments_by_judge[judge]["forward"]["normalized_preference"]
                reverse = judgments_by_judge[judge]["reverse"]["normalized_preference"]
                stable[judge] = forward == reverse
                position_consistency[judge] += stable[judge]
                scalar_alignment[judge] += (
                    stable[judge]
                    and forward == scalar_rows[judge]["scalar_preference"]
                )
                scalar_ties[judge] += scalar_rows[judge]["scalar_preference"] == "TIE"
                pairwise_ties[judge] += sum(
                    judgments_by_judge[judge][order]["normalized_preference"] == "TIE"
                    for order in ("forward", "reverse")
                )
            both_stable = all(stable.values())
            stable_both += both_stable
            stable_agreement += (
                both_stable
                and judgments_by_judge[cheap]["forward"]["normalized_preference"]
                == judgments_by_judge[strong]["forward"]["normalized_preference"]
            )
            comparison.append(
                {
                    **pair,
                    "scalar": scalar_rows,
                    "pairwise": judgments_by_judge,
                    "scalar_interjudge_agreement": scalar_match,
                    "both_judges_position_consistent": both_stable,
                }
            )

        count = len(track_pairs)
        pairwise_agreement_total = order_agreement["forward"] + order_agreement["reverse"]
        track_summary[track_key] = {
            "scenario_count": count,
            "judges": list(track["judges"]),
            "scalar_interjudge_agreement": rate(scalar_agreement, count),
            "pairwise_interjudge_agreement": {
                "forward": rate(order_agreement["forward"], count),
                "reverse": rate(order_agreement["reverse"], count),
                "all_orders": rate(pairwise_agreement_total, count * 2),
                "position_stable_subset": rate(stable_agreement, stable_both),
            },
            "position_consistency": {
                judge: rate(position_consistency[judge], count)
                for judge in track["judges"]
            },
            "scalar_pairwise_alignment_on_stable_cases": {
                judge: rate(scalar_alignment[judge], position_consistency[judge])
                for judge in track["judges"]
            },
            "scalar_tie_rate": {
                judge: rate(scalar_ties[judge], count) for judge in track["judges"]
            },
            "pairwise_tie_rate": {
                judge: rate(pairwise_ties[judge], count * 2)
                for judge in track["judges"]
            },
        }

    summary = {
        "generated_at": utc_now(),
        "pairwise_call_count": len(judgments),
        "provider_call_counts": dict(Counter(row["judge_family"] for row in judgments)),
        "anthropic_call_count": 0,
        "costs": estimate_costs(judgments),
        "tracks": track_summary,
    }
    write_json(results_dir / "analysis.json", summary)
    write_json(results_dir / "cost_summary.json", summary["costs"])
    write_json(results_dir / "scenario_comparison.json", comparison)

    csv_rows = []
    for row in comparison:
        track = TRACKS[row["track"]]
        for judge in track["judges"]:
            csv_rows.append(
                {
                    "track": row["track"],
                    "question_id": row["question_id"],
                    "judge": judge,
                    "scalar_preference": row["scalar"][judge]["scalar_preference"],
                    "pairwise_forward": row["pairwise"][judge]["forward"]["normalized_preference"],
                    "pairwise_reverse": row["pairwise"][judge]["reverse"]["normalized_preference"],
                    "position_consistent": (
                        row["pairwise"][judge]["forward"]["normalized_preference"]
                        == row["pairwise"][judge]["reverse"]["normalized_preference"]
                    ),
                }
            )
    with (results_dir / "comparison.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(csv_rows[0]))
        writer.writeheader()
        writer.writerows(csv_rows)
    return summary


def finalize(results_dir: Path, summary: dict[str, Any]) -> None:
    path = results_dir / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["status"] = "complete"
    manifest["completed_at"] = utc_now()
    manifest["summary"] = summary
    manifest["artifacts"] = {
        str(artifact.relative_to(results_dir)): {
            "sha256": sha256_file(artifact),
            "bytes": artifact.stat().st_size,
        }
        for artifact in sorted(results_dir.rglob("*"))
        if artifact.is_file() and artifact != path
    }
    write_json(path, manifest)


async def run(limit: int, results_dir: Path, dry_run: bool) -> None:
    pairs, baseline = load_frozen_inputs(limit)
    expected = limit * 2 * 2 * 2
    plan = {
        "scenarios": limit,
        "response_pairs": len(pairs),
        "scalar_baseline_rows": len(baseline),
        "pairwise_calls": expected,
        "provider_calls": {"google": expected // 2, "openai": expected // 2},
        "anthropic_calls": 0,
    }
    print(json.dumps(plan, indent=2), flush=True)
    if dry_run:
        return

    prepare_results(results_dir, pairs, baseline, limit)
    load_dotenv(REPO_ROOT / ".env")
    providers = Providers()
    judgments = await run_pairwise(providers, pairs, results_dir)
    summary = analyze(pairs, baseline, judgments, results_dir)
    finalize(results_dir, summary)
    print(json.dumps(summary, indent=2), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=30, choices=range(1, 31))
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(args.limit, args.results_dir.resolve(), args.dry_run))


if __name__ == "__main__":
    main()
