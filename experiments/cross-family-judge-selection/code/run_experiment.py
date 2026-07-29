"""Run the HERON cross-family judge-selection experiment.

The runner is resumable. It freezes 90 target responses, applies only
cross-family judges, repeats a fixed subset for stability, and writes the
pre-registered analysis artifacts.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import importlib
import json
import os
import random
import re
import shutil
import statistics
import subprocess
import sys
import time
from collections import Counter
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from google import genai
from google.genai import types as google_types
from openai import AsyncOpenAI

REPO_ROOT = Path(__file__).resolve().parents[3]
EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_RESULTS_DIR = EXPERIMENT_DIR / "results"
DATASET_PATH = REPO_ROOT / "samples.json"
SCORER_PATH = REPO_ROOT / "src" / "heron" / "scorer.py"
SPEC_PATH = EXPERIMENT_DIR / "experiment_spec.md"

sys.path.insert(0, str(REPO_ROOT / "src"))
scorer_module = importlib.import_module("heron.scorer")
JUDGE_PROMPT_TEMPLATE = scorer_module.PROPORTIONALITY_JUDGE_PROMPT
parse_score_value = scorer_module.parse_score_value
parse_classification = scorer_module.parse_classification
classification_matches_score = scorer_module.classification_matches_score
extract_labeled_section = scorer_module._extract_labeled_section

BEDROCK_REGION = "us-east-1"
TARGET_MAX_TOKENS = 8192
JUDGE_MAX_TOKENS = 4096
TARGET_CONCURRENCY = 4
JUDGE_CONCURRENCY = 6
MAX_ATTEMPTS = 5
REFERENCE_THRESHOLD = 0.15
LARGE_DIFFERENCE_THRESHOLD = 0.30
REPEAT_SEED = 20260729
BOOTSTRAP_SEED = 20260730
BOOTSTRAP_SAMPLES = 5000

TARGETS = {
    "openai": {
        "label": "GPT-5.6 Sol",
        "provider": "openai",
        "model": "gpt-5.6-sol",
        "reasoning": "none",
    },
    "google": {
        "label": "Gemini 3.1 Pro Preview",
        "provider": "google",
        "model": "gemini-3.1-pro-preview",
        "reasoning": "low",
    },
    "anthropic": {
        "label": "Claude Opus 5",
        "provider": "bedrock",
        "model": "us.anthropic.claude-opus-5",
        "reasoning": "low",
    },
}

JUDGES = {
    "flash": {
        "label": "Gemini 3.6 Flash",
        "family": "google",
        "provider": "google",
        "model": "gemini-3.6-flash",
        "reasoning": "minimal",
        "role": "candidate",
    },
    "sonnet": {
        "label": "Claude Sonnet 5",
        "family": "anthropic",
        "provider": "bedrock",
        "model": "us.anthropic.claude-sonnet-5",
        "reasoning": "low",
        "role": "candidate",
    },
    "luna": {
        "label": "GPT-5.6 Luna",
        "family": "openai",
        "provider": "openai",
        "model": "gpt-5.6-luna",
        "reasoning": "none",
        "role": "candidate",
    },
    "pro": {
        "label": "Gemini 3.1 Pro Preview",
        "family": "google",
        "provider": "google",
        "model": "gemini-3.1-pro-preview",
        "reasoning": "medium",
        "role": "reference",
    },
    "opus": {
        "label": "Claude Opus 5",
        "family": "anthropic",
        "provider": "bedrock",
        "model": "us.anthropic.claude-opus-5",
        "reasoning": "medium",
        "role": "reference",
    },
    "sol": {
        "label": "GPT-5.6 Sol",
        "family": "openai",
        "provider": "openai",
        "model": "gpt-5.6-sol",
        "reasoning": "medium",
        "role": "reference",
    },
}

ROUTES = {
    "openai": {
        "candidates": ["flash", "sonnet"],
        "references": ["pro", "opus"],
    },
    "google": {
        "candidates": ["sonnet", "luna"],
        "references": ["opus", "sol"],
    },
    "anthropic": {
        "candidates": ["flash", "luna"],
        "references": ["pro", "sol"],
    },
}

PRICES = {
    "gemini-3.6-flash": {"input": 1.50, "output": 7.50},
    "gemini-3.1-pro-preview": {"input": 2.00, "output": 12.00},
    "gpt-5.6-luna": {"input": 1.00, "output": 6.00},
    "gpt-5.6-sol": {"input": 5.00, "output": 30.00},
    "us.anthropic.claude-sonnet-5": {"input": 2.00, "output": 10.00},
    "us.anthropic.claude-opus-5": {"input": 5.00, "output": 25.00},
}


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def sha256_json(value: Any) -> str:
    return sha256_bytes(canonical_json(value).encode())


def git_value(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


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
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as error:
            raise RuntimeError(f"Invalid JSONL at {path}:{number}") from error
    return rows


def completed_keys(path: Path) -> set[str]:
    return {
        str(row["key"])
        for row in read_jsonl(path)
        if row.get("status") == "ok"
    }


def load_questions() -> list[dict[str, Any]]:
    payload = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    questions = payload.get("all")
    if not isinstance(questions, list) or len(questions) != 30:
        raise RuntimeError("The experiment requires exactly 30 HERON scenarios")
    ids = [str(question["id"]) for question in questions]
    if len(ids) != len(set(ids)):
        raise RuntimeError("Duplicate scenario IDs found")
    normalized = [
        re.sub(r"\s+", " ", question["question"].strip().casefold())
        for question in questions
    ]
    duplicates = [text for text, count in Counter(normalized).items() if count > 1]
    if duplicates:
        raise RuntimeError("Duplicate scenario text found")
    if any((question.get("turn2") or "").strip() for question in questions):
        raise RuntimeError("This frozen experiment expects one-turn scenarios")
    return questions


def bedrock_api_key() -> str:
    for name in (
        "AWS_API_KEY",
        "CHAD_AWS_BEDROCK_KEY",
        "AWS_BEARER_TOKEN_BEDROCK",
    ):
        configured = os.environ.get(name, "").strip()
        if not configured:
            continue
        if configured.startswith("ABSK"):
            return configured
        if "=" in configured:
            embedded = configured.split("=", 1)[1].strip()
            if embedded.startswith("ABSK"):
                return embedded
    raise RuntimeError("No Bedrock API bearer key is configured")


def sanitize_raw(value: Any) -> Any:
    """Drop opaque thought signatures while preserving provider response data."""
    if isinstance(value, dict):
        return {
            key: sanitize_raw(item)
            for key, item in value.items()
            if key not in {"thought_signature", "thoughtSignature"}
        }
    if isinstance(value, list):
        return [sanitize_raw(item) for item in value]
    return value


async def with_retries(
    label: str,
    call: Callable[[], Awaitable[dict[str, Any]]],
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
            retryable = status is None or status in {
                408,
                409,
                429,
                500,
                502,
                503,
                504,
            }
            if not retryable or attempt == MAX_ATTEMPTS:
                break
            delay = 2**attempt
            print(
                f"{label}: attempt {attempt} failed; retrying in {delay}s",
                flush=True,
            )
            await asyncio.sleep(delay)
    assert last_error is not None
    raise last_error


def bedrock_text(response: dict[str, Any]) -> str:
    blocks = response["output"]["message"]["content"]
    return "\n".join(block["text"] for block in blocks if "text" in block).strip()


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


def bedrock_usage(response: dict[str, Any]) -> dict[str, Any]:
    usage = response.get("usage", {})
    return {
        "input_tokens": usage.get("inputTokens", 0),
        "output_tokens": usage.get("outputTokens", 0),
        "reasoning_tokens": 0,
        "raw": usage,
    }


def prompt_for_judge(question: str, response: str) -> str:
    return JUDGE_PROMPT_TEMPLATE.replace("{user_request}", question).replace(
        "{assistant_response}", response
    )


def parse_judgment(response_text: str) -> dict[str, Any]:
    reasoning = extract_labeled_section(
        response_text,
        "REASONING",
        ["CLASSIFICATION", "SCORE"],
    )
    classification = parse_classification(response_text)
    score = max(0.0, min(1.0, parse_score_value(response_text)))
    format_valid = (
        bool(reasoning)
        and classification != "UNPARSEABLE"
        and bool(re.search(r"(?im)^SCORE:", response_text))
        and classification_matches_score(classification, score)
    )
    return {
        "score": score,
        "reasoning": reasoning,
        "classification": classification,
        "format_valid": format_valid,
    }


class Providers:
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
        self.bedrock = httpx.AsyncClient(
            timeout=300.0,
            headers={
                "Authorization": f"Bearer {bedrock_api_key()}",
                "Content-Type": "application/json",
            },
        )

    async def close(self) -> None:
        await self.bedrock.aclose()

    async def bedrock_call(
        self,
        model: str,
        prompt: str,
        effort: str,
        max_tokens: int,
    ) -> dict[str, Any]:
        url = (
            f"https://bedrock-runtime.{BEDROCK_REGION}.amazonaws.com/"
            f"model/{model}/converse"
        )
        response = await self.bedrock.post(
            url,
            json={
                "messages": [
                    {"role": "user", "content": [{"text": prompt}]},
                ],
                "inferenceConfig": {"maxTokens": max_tokens},
                "additionalModelRequestFields": {
                    "thinking": {"type": "adaptive"},
                    "output_config": {"effort": effort},
                },
            },
        )
        response.raise_for_status()
        raw = response.json()
        if raw.get("stopReason") != "end_turn":
            raise RuntimeError(f"Bedrock returned stopReason={raw.get('stopReason')}")
        return {
            "text": bedrock_text(raw),
            "usage": bedrock_usage(raw),
            "raw": sanitize_raw(raw),
        }

    async def google_call(
        self,
        model: str,
        prompt: str,
        effort: str,
        max_tokens: int,
    ) -> dict[str, Any]:
        response = await self.google.aio.models.generate_content(
            model=model,
            contents=prompt,
            config=google_types.GenerateContentConfig(
                max_output_tokens=max_tokens,
                thinking_config=google_types.ThinkingConfig(thinking_level=effort),
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

    async def openai_call(
        self,
        model: str,
        prompt: str,
        effort: str,
        max_tokens: int,
    ) -> dict[str, Any]:
        response = await self.openai.responses.create(
            model=model,
            input=prompt,
            max_output_tokens=max_tokens,
            reasoning={"effort": effort},
        )
        if response.status != "completed":
            raise RuntimeError(f"OpenAI returned status={response.status}")
        return {
            "text": (response.output_text or "").strip(),
            "usage": openai_usage(response),
            "raw": sanitize_raw(response.model_dump(mode="json", exclude_none=True)),
        }

    async def call(
        self,
        provider: str,
        model: str,
        prompt: str,
        effort: str,
        max_tokens: int,
    ) -> dict[str, Any]:
        if provider == "bedrock":
            return await self.bedrock_call(model, prompt, effort, max_tokens)
        if provider == "google":
            return await self.google_call(model, prompt, effort, max_tokens)
        if provider == "openai":
            return await self.openai_call(model, prompt, effort, max_tokens)
        raise ValueError(f"Unknown provider: {provider}")


def settings() -> dict[str, Any]:
    return {
        "targets": TARGETS,
        "judges": JUDGES,
        "routes": ROUTES,
        "target_max_tokens": TARGET_MAX_TOKENS,
        "judge_max_tokens": JUDGE_MAX_TOKENS,
        "reference_threshold": REFERENCE_THRESHOLD,
        "large_difference_threshold": LARGE_DIFFERENCE_THRESHOLD,
        "repeat_seed": REPEAT_SEED,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "bootstrap_samples": BOOTSTRAP_SAMPLES,
        "sampling_parameters": (
            "temperature, top_p, and top_k omitted for every provider"
        ),
    }


def prepare_results(
    results_dir: Path,
    questions: list[dict[str, Any]],
) -> dict[str, Any]:
    manifest_path = results_dir / "manifest.json"
    current_settings = settings()
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected = {
            "dataset": sha256_file(DATASET_PATH),
            "scorer": sha256_file(SCORER_PATH),
            "spec": sha256_file(SPEC_PATH),
            "settings": sha256_json(current_settings),
        }
        for key, current_hash in expected.items():
            if manifest["hashes"][key] != current_hash:
                raise RuntimeError(f"Refusing to resume because {key} changed")
        return manifest

    results_dir.mkdir(parents=True, exist_ok=False)
    frozen = results_dir / "frozen_inputs"
    frozen.mkdir()
    shutil.copy2(DATASET_PATH, frozen / "samples.json")
    shutil.copy2(SCORER_PATH, frozen / "scorer.py")
    shutil.copy2(SPEC_PATH, frozen / "experiment_spec.md")
    manifest = {
        "experiment": "Cross-Family Judge Selection",
        "status": "initialized",
        "created_at": utc_now(),
        "git_commit": git_value("rev-parse", "HEAD"),
        "git_status_porcelain": git_value("status", "--porcelain"),
        "scenario_count": len(questions),
        "reference_answers_nonempty": sum(
            bool((question.get("reference_answer") or "").strip())
            for question in questions
        ),
        "hashes": {
            "dataset": sha256_file(DATASET_PATH),
            "scorer": sha256_file(SCORER_PATH),
            "spec": sha256_file(SPEC_PATH),
            "settings": sha256_json(current_settings),
        },
        "settings": current_settings,
        "artifacts": {},
    }
    write_json(manifest_path, manifest)
    return manifest


async def generate_corpus(
    providers: Providers,
    questions: list[dict[str, Any]],
    results_dir: Path,
) -> list[dict[str, Any]]:
    path = results_dir / "corpus.jsonl"
    done = completed_keys(path)
    pending = [
        (family, target, question)
        for family, target in TARGETS.items()
        for question in questions
        if f"{family}:{question['id']}" not in done
    ]
    semaphore = asyncio.Semaphore(TARGET_CONCURRENCY)
    write_lock = asyncio.Lock()

    async def generate_one(
        family: str,
        target: dict[str, str],
        question: dict[str, Any],
    ) -> None:
        key = f"{family}:{question['id']}"
        started = time.perf_counter()
        async with semaphore:
            result = await with_retries(
                f"target {key}",
                lambda: providers.call(
                    target["provider"],
                    target["model"],
                    question["question"],
                    target["reasoning"],
                    TARGET_MAX_TOKENS,
                ),
            )
        response = result["text"].strip()
        if not response:
            raise RuntimeError(f"Target {key} returned an empty response")
        row = {
            "status": "ok",
            "key": key,
            "question_id": str(question["id"]),
            "dataset_index": questions.index(question),
            "question": question["question"],
            "reference_answer": question.get("reference_answer", ""),
            "target_family": family,
            "target_label": target["label"],
            "target_model": target["model"],
            "target_reasoning": target["reasoning"],
            "response": response,
            "conversation_sha256": sha256_json(
                [
                    {"role": "user", "content": question["question"]},
                    {"role": "assistant", "content": response},
                ]
            ),
            "usage": result["usage"],
            "latency_seconds": round(time.perf_counter() - started, 3),
            "completed_at": utc_now(),
            "raw_provider_response": result["raw"],
        }
        async with write_lock:
            append_jsonl(path, row)
            print(
                f"Corpus {len(completed_keys(path))}/90 ({key})",
                flush=True,
            )

    await asyncio.gather(
        *(
            generate_one(family, target, question)
            for family, target, question in pending
        )
    )
    rows = read_jsonl(path)
    if len(completed_keys(path)) != 90:
        raise RuntimeError("Frozen target corpus is incomplete")
    return sorted(
        rows,
        key=lambda row: (row["dataset_index"], row["target_family"]),
    )


async def run_judgments(
    providers: Providers,
    corpus: list[dict[str, Any]],
    results_dir: Path,
    *,
    repeat: bool,
    selected_keys: set[str] | None = None,
) -> list[dict[str, Any]]:
    filename = "repeat_judgments.jsonl" if repeat else "primary_judgments.jsonl"
    path = results_dir / filename
    done = completed_keys(path)
    tasks = []
    for corpus_row in corpus:
        if selected_keys is not None and corpus_row["key"] not in selected_keys:
            continue
        route = ROUTES[corpus_row["target_family"]]
        for judge_key in [*route["candidates"], *route["references"]]:
            judgment_key = f"{corpus_row['key']}:{judge_key}"
            if judgment_key not in done:
                tasks.append((corpus_row, judge_key))

    semaphore = asyncio.Semaphore(JUDGE_CONCURRENCY)
    write_lock = asyncio.Lock()
    expected_total = (
        len(selected_keys) * 4 if selected_keys is not None else len(corpus) * 4
    )

    async def judge_one(
        corpus_row: dict[str, Any],
        judge_key: str,
    ) -> None:
        judge = JUDGES[judge_key]
        if judge["family"] == corpus_row["target_family"]:
            raise RuntimeError("Same-family judging route detected")
        key = f"{corpus_row['key']}:{judge_key}"
        prompt = prompt_for_judge(corpus_row["question"], corpus_row["response"])
        started = time.perf_counter()

        async def call_and_validate() -> dict[str, Any]:
            result = await providers.call(
                judge["provider"],
                judge["model"],
                prompt,
                judge["reasoning"],
                JUDGE_MAX_TOKENS,
            )
            parsed = parse_judgment(result["text"])
            if not parsed["format_valid"]:
                raise RuntimeError(f"Malformed judgment from {judge_key}")
            result["parsed"] = parsed
            return result

        async with semaphore:
            result = await with_retries(
                f"{'repeat' if repeat else 'judge'} {key}",
                call_and_validate,
            )
        row = {
            "status": "ok",
            "key": key,
            "corpus_key": corpus_row["key"],
            "question_id": corpus_row["question_id"],
            "target_family": corpus_row["target_family"],
            "target_model": corpus_row["target_model"],
            "conversation_sha256": corpus_row["conversation_sha256"],
            "judge_key": judge_key,
            "judge_label": judge["label"],
            "judge_family": judge["family"],
            "judge_model": judge["model"],
            "judge_role": judge["role"],
            "judge_reasoning": judge["reasoning"],
            "prompt_sha256": sha256_bytes(prompt.encode()),
            "response_text": result["text"],
            **result["parsed"],
            "usage": result["usage"],
            "latency_seconds": round(time.perf_counter() - started, 3),
            "completed_at": utc_now(),
            "raw_provider_response": result["raw"],
        }
        async with write_lock:
            append_jsonl(path, row)
            print(
                f"{'Repeats' if repeat else 'Judgments'} "
                f"{len(completed_keys(path))}/{expected_total} ({key})",
                flush=True,
            )

    await asyncio.gather(*(judge_one(row, judge) for row, judge in tasks))
    rows = read_jsonl(path)
    if len(completed_keys(path)) != expected_total:
        raise RuntimeError(f"{filename} is incomplete")
    if any(row["judge_family"] == row["target_family"] for row in rows):
        raise RuntimeError("Same-family judgment found in saved output")
    return rows


def select_repeat_keys(corpus: list[dict[str, Any]], results_dir: Path) -> set[str]:
    path = results_dir / "repeat_selection.json"
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        return set(payload["corpus_keys"])
    rng = random.Random(REPEAT_SEED)
    selected = []
    for family in TARGETS:
        keys = sorted(row["key"] for row in corpus if row["target_family"] == family)
        selected.extend(rng.sample(keys, 6))
    payload = {
        "seed": REPEAT_SEED,
        "selection_rule": "Six frozen responses sampled from each target family",
        "corpus_keys": sorted(selected),
    }
    write_json(path, payload)
    return set(selected)


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def bootstrap_ci(
    rows: list[dict[str, Any]],
    metric: Callable[[list[dict[str, Any]]], float],
) -> list[float]:
    clusters: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        clusters.setdefault(row["question_id"], []).append(row)
    keys = sorted(clusters)
    rng = random.Random(BOOTSTRAP_SEED)
    estimates = []
    for _ in range(BOOTSTRAP_SAMPLES):
        sampled = [rng.choice(keys) for _ in keys]
        sample_rows = [row for key in sampled for row in clusters[key]]
        estimates.append(metric(sample_rows))
    return [percentile(estimates, 0.025), percentile(estimates, 0.975)]


def candidate_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "resolved_count": 0,
            "mae": None,
            "within_0_15": None,
            "over_0_30": None,
            "signed_bias": None,
        }
    differences = [row["candidate_score"] - row["reference_score"] for row in rows]
    absolute = [abs(value) for value in differences]
    result = {
        "resolved_count": len(rows),
        "mae": statistics.mean(absolute),
        "within_0_15": sum(
            value <= REFERENCE_THRESHOLD + 1e-12 for value in absolute
        )
        / len(rows),
        "over_0_30": sum(
            value > LARGE_DIFFERENCE_THRESHOLD + 1e-12 for value in absolute
        )
        / len(rows),
        "signed_bias": statistics.mean(differences),
    }
    result["bootstrap_95_ci"] = {
        "mae": bootstrap_ci(
            rows,
            lambda sample: statistics.mean(
                abs(row["candidate_score"] - row["reference_score"])
                for row in sample
            ),
        ),
        "within_0_15": bootstrap_ci(
            rows,
            lambda sample: sum(
                abs(row["candidate_score"] - row["reference_score"])
                <= REFERENCE_THRESHOLD + 1e-12
                for row in sample
            )
            / len(sample),
        ),
        "signed_bias": bootstrap_ci(
            rows,
            lambda sample: statistics.mean(
                row["candidate_score"] - row["reference_score"]
                for row in sample
            ),
        ),
    }
    return result


def usage_tokens(row: dict[str, Any]) -> tuple[int, int, int, int]:
    usage = row.get("usage", {})
    input_tokens = int(usage.get("input_tokens", 0))
    output_tokens = int(usage.get("output_tokens", 0))
    reasoning_tokens = int(usage.get("reasoning_tokens", 0))
    details = usage.get("input_tokens_details", {})
    cache_write = int(details.get("cache_write_tokens", 0))
    cached = int(details.get("cached_tokens", 0))
    return input_tokens, output_tokens, reasoning_tokens, cache_write + cached


def estimate_cost(model: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    price = PRICES[model]
    input_tokens = output_tokens = reasoning_tokens = 0
    cache_write = cached = 0
    for row in rows:
        usage = row.get("usage", {})
        input_tokens += int(usage.get("input_tokens", 0))
        output_tokens += int(usage.get("output_tokens", 0))
        reasoning_tokens += int(usage.get("reasoning_tokens", 0))
        details = usage.get("input_tokens_details", {})
        cache_write += int(details.get("cache_write_tokens", 0))
        cached += int(details.get("cached_tokens", 0))
    if model.startswith("gpt-"):
        regular = input_tokens - cache_write - cached
        input_cost = (
            regular * price["input"]
            + cache_write * price["input"] * 1.25
            + cached * price["input"] * 0.10
        ) / 1_000_000
    else:
        input_cost = input_tokens * price["input"] / 1_000_000
    billed_output = output_tokens + (
        reasoning_tokens if model.startswith("gemini-") else 0
    )
    output_cost = billed_output * price["output"] / 1_000_000
    return {
        "model": model,
        "calls": len(rows),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "reasoning_tokens": reasoning_tokens,
        "cache_write_tokens": cache_write,
        "cached_tokens": cached,
        "estimated_cost_usd": input_cost + output_cost,
        "average_scheduled_elapsed_seconds": (
            statistics.mean(row["latency_seconds"] for row in rows) if rows else 0
        ),
    }


def analyze(
    corpus: list[dict[str, Any]],
    primary: list[dict[str, Any]],
    repeats: list[dict[str, Any]],
    results_dir: Path,
) -> dict[str, Any]:
    judgments = {row["key"]: row for row in primary}
    comparison_rows = []
    candidate_observations: dict[str, list[dict[str, Any]]] = {
        key: [] for key, value in JUDGES.items() if value["role"] == "candidate"
    }
    coverage: dict[str, dict[str, int]] = {
        family: {"total": 0, "resolved": 0, "ambiguous": 0} for family in TARGETS
    }

    for corpus_row in corpus:
        family = corpus_row["target_family"]
        route = ROUTES[family]
        scores = {
            judge: float(judgments[f"{corpus_row['key']}:{judge}"]["score"])
            for judge in [*route["candidates"], *route["references"]]
        }
        left, right = route["references"]
        reference_difference = abs(scores[left] - scores[right])
        resolved = reference_difference <= REFERENCE_THRESHOLD + 1e-12
        reference_score = statistics.mean([scores[left], scores[right]])
        coverage[family]["total"] += 1
        coverage[family]["resolved" if resolved else "ambiguous"] += 1
        row = {
            "corpus_key": corpus_row["key"],
            "question_id": corpus_row["question_id"],
            "question": corpus_row["question"],
            "target_family": family,
            "target_model": corpus_row["target_model"],
            "target_response": corpus_row["response"],
            "conversation_sha256": corpus_row["conversation_sha256"],
            "candidate_1": route["candidates"][0],
            "candidate_1_score": scores[route["candidates"][0]],
            "candidate_2": route["candidates"][1],
            "candidate_2_score": scores[route["candidates"][1]],
            "reference_1": left,
            "reference_1_score": scores[left],
            "reference_2": right,
            "reference_2_score": scores[right],
            "reference_difference": reference_difference,
            "reference_resolved": resolved,
            "reference_score": reference_score if resolved else "",
        }
        comparison_rows.append(row)
        if resolved:
            for candidate in route["candidates"]:
                candidate_observations[candidate].append(
                    {
                        "question_id": corpus_row["question_id"],
                        "target_family": family,
                        "candidate_score": scores[candidate],
                        "reference_score": reference_score,
                    }
                )

    comparison_rows.sort(
        key=lambda row: (-row["reference_difference"], row["corpus_key"])
    )
    comparison_path = results_dir / "scenario_comparison.csv"
    with comparison_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(comparison_rows[0]))
        writer.writeheader()
        writer.writerows(comparison_rows)

    stability: dict[str, dict[str, Any]] = {}
    for judge in JUDGES:
        differences = []
        for repeat in repeats:
            if repeat["judge_key"] != judge:
                continue
            first = judgments[repeat["key"]]
            differences.append(abs(float(first["score"]) - float(repeat["score"])))
        if differences:
            stability[judge] = {
                "repeat_count": len(differences),
                "same_score": sum(value == 0 for value in differences)
                / len(differences),
                "within_0_15": sum(
                    value <= REFERENCE_THRESHOLD + 1e-12 for value in differences
                )
                / len(differences),
                "mean_absolute_difference": statistics.mean(differences),
                "maximum_absolute_difference": max(differences),
            }

    candidate_summary = {}
    for candidate, observations in candidate_observations.items():
        by_family = {
            family: candidate_metrics(
                [row for row in observations if row["target_family"] == family]
            )
            for family in TARGETS
            if candidate in ROUTES[family]["candidates"]
        }
        candidate_summary[candidate] = {
            "label": JUDGES[candidate]["label"],
            "overall": candidate_metrics(observations),
            "by_target_family": by_family,
            "stability": stability[candidate],
        }

    all_call_rows = [
        *[
            {
                "model": row["target_model"],
                "usage": row["usage"],
                "latency_seconds": row["latency_seconds"],
            }
            for row in corpus
        ],
        *[
            {
                "model": row["judge_model"],
                "usage": row["usage"],
                "latency_seconds": row["latency_seconds"],
            }
            for row in [*primary, *repeats]
        ],
    ]
    cost_rows = []
    for model in sorted({row["model"] for row in all_call_rows}):
        cost_rows.append(
            estimate_cost(
                model,
                [row for row in all_call_rows if row["model"] == model],
            )
        )
    cost_path = results_dir / "cost_summary.csv"
    with cost_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(cost_rows[0]))
        writer.writeheader()
        writer.writerows(cost_rows)

    cost_by_candidate = {}
    for candidate in ("flash", "sonnet", "luna"):
        model = JUDGES[candidate]["model"]
        model_cost = next(row for row in cost_rows if row["model"] == model)
        candidate_calls = [
            row
            for row in [*primary, *repeats]
            if row["judge_key"] == candidate
        ]
        candidate_model_calls = [
            row
            for row in all_call_rows
            if row["model"] == model
        ]
        cost_by_candidate[candidate] = (
            model_cost["estimated_cost_usd"]
            * len(candidate_calls)
            / len(candidate_model_calls)
        )

    recommendation = {}
    for family, route in ROUTES.items():
        candidates = route["candidates"]
        evaluated = []
        for candidate in candidates:
            metrics = candidate_summary[candidate]["by_target_family"][family]
            stable = candidate_summary[candidate]["stability"]["within_0_15"]
            qualifies = (
                metrics["within_0_15"] is not None
                and metrics["within_0_15"] >= 0.85
                and metrics["over_0_30"] <= 0.05
                and abs(metrics["signed_bias"]) <= 0.05
                and stable >= 0.90
            )
            evaluated.append(
                {
                    "candidate": candidate,
                    "qualifies": qualifies,
                    "estimated_experiment_judge_cost_usd": cost_by_candidate[candidate],
                    "metrics": metrics,
                    "stability_within_0_15": stable,
                }
            )
        qualified = sorted(
            [row for row in evaluated if row["qualifies"]],
            key=lambda row: row["estimated_experiment_judge_cost_usd"],
        )
        recommendation[family] = {
            "main": qualified[0]["candidate"] if qualified else None,
            "backup": qualified[1]["candidate"] if len(qualified) > 1 else None,
            "status": (
                "main_and_backup_selected"
                if len(qualified) == 2
                else "main_only"
                if len(qualified) == 1
                else "inconclusive"
            ),
            "candidate_results": evaluated,
        }

    analysis = {
        "generated_at": utc_now(),
        "scenario_count": 30,
        "frozen_response_count": len(corpus),
        "primary_judgment_count": len(primary),
        "repeat_judgment_count": len(repeats),
        "same_family_judgment_count": sum(
            row["judge_family"] == row["target_family"]
            for row in [*primary, *repeats]
        ),
        "reference_coverage": {
            family: {
                **values,
                "resolution_rate": values["resolved"] / values["total"],
            }
            for family, values in coverage.items()
        },
        "candidate_summary": candidate_summary,
        "stability": stability,
        "routing_recommendation": recommendation,
        "costs": cost_rows,
    }
    write_json(results_dir / "analysis.json", analysis)
    write_json(results_dir / "routing_recommendation.json", recommendation)
    return analysis


def finalize_manifest(
    results_dir: Path,
    manifest: dict[str, Any],
    analysis: dict[str, Any],
) -> None:
    manifest["status"] = "complete"
    manifest["completed_at"] = utc_now()
    manifest["summary"] = {
        "frozen_response_count": analysis["frozen_response_count"],
        "primary_judgment_count": analysis["primary_judgment_count"],
        "repeat_judgment_count": analysis["repeat_judgment_count"],
        "same_family_judgment_count": analysis["same_family_judgment_count"],
        "routing_recommendation": analysis["routing_recommendation"],
    }
    manifest["artifacts"] = {
        str(path.relative_to(results_dir)): {
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
        }
        for path in sorted(results_dir.rglob("*"))
        if path.is_file() and path.name != "manifest.json"
    }
    write_json(results_dir / "manifest.json", manifest)


async def run(results_dir: Path) -> None:
    load_dotenv(REPO_ROOT / ".env")
    questions = load_questions()
    manifest = prepare_results(results_dir, questions)
    providers = Providers()
    try:
        corpus = await generate_corpus(providers, questions, results_dir)
        primary = await run_judgments(
            providers,
            corpus,
            results_dir,
            repeat=False,
        )
        selected = select_repeat_keys(corpus, results_dir)
        repeats = await run_judgments(
            providers,
            corpus,
            results_dir,
            repeat=True,
            selected_keys=selected,
        )
    finally:
        await providers.close()
    analysis = analyze(corpus, primary, repeats, results_dir)
    finalize_manifest(results_dir, manifest, analysis)
    print(
        "Experiment complete: "
        f"{len(corpus)} responses, {len(primary)} primary judgments, "
        f"{len(repeats)} repeat judgments.",
        flush=True,
    )


async def smoke_test_providers() -> None:
    load_dotenv(REPO_ROOT / ".env")
    providers = Providers()
    configurations = {
        (
            value["provider"],
            value["model"],
            value["reasoning"],
        )
        for value in [*TARGETS.values(), *JUDGES.values()]
    }
    try:
        for provider, model, effort in sorted(configurations):
            result = await providers.call(
                provider,
                model,
                "Respond with exactly: OK",
                effort,
                128,
            )
            if not result["text"].strip():
                raise RuntimeError(f"Smoke test returned empty output for {model}")
            print(f"Smoke test passed: {model} ({effort})", flush=True)
    finally:
        await providers.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", default=str(DEFAULT_RESULTS_DIR))
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    if args.smoke:
        asyncio.run(smoke_test_providers())
        return
    results_dir = Path(args.results_dir)
    if not results_dir.is_absolute():
        results_dir = REPO_ROOT / results_dir
    asyncio.run(run(results_dir))


if __name__ == "__main__":
    main()
