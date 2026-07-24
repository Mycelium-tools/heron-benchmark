"""
Paired old-vs-proportionality judge experiment.

The target model generates each answer once. Two Terra judges then score the
same frozen one-turn conversation using the old and new prompts.

Usage:
    inspect eval src/heron/paired_eval.py@heron_paired_test5 \
        --model google/gemini-3.1-pro-preview
    inspect eval src/heron/paired_eval.py@heron_paired_full \
        --model google/gemini-3.1-pro-preview
"""

from inspect_ai import Task, task
from inspect_ai.dataset import MemoryDataset

from heron.eval import load_samples
from heron.scorer import (
    heron_old_prompt_scorer,
    heron_proportionality_scorer,
)
from heron.solver import static_two_turn_conversation

EXPECTED_SAMPLE_COUNT = 24


def load_paired_experiment_samples():
    """Load and strictly validate the frozen one-turn experiment dataset."""
    samples = load_samples()

    problems = []
    if len(samples) != EXPECTED_SAMPLE_COUNT:
        problems.append(
            f"expected {EXPECTED_SAMPLE_COUNT} questions, found {len(samples)}"
        )

    invalid_ids = [
        sample.id
        for sample in samples
        if not sample.id or sample.id.strip().lower() in {"none", "nan", "null"}
    ]
    if invalid_ids:
        problems.append(f"missing or invalid IDs: {invalid_ids}")

    ids = [sample.id for sample in samples]
    duplicate_ids = sorted({sample_id for sample_id in ids if ids.count(sample_id) > 1})
    if duplicate_ids:
        problems.append(f"duplicate IDs: {duplicate_ids}")

    blank_questions = [
        sample.id
        for sample in samples
        if not isinstance(sample.input, str) or not sample.input.strip()
    ]
    if blank_questions:
        problems.append(f"blank questions at IDs: {blank_questions}")

    two_turn_ids = [
        sample.id for sample in samples if (sample.metadata.get("turn2") or "").strip()
    ]
    if two_turn_ids:
        problems.append(f"non-empty turn2 values at IDs: {two_turn_ids}")

    if problems:
        details = "\n- ".join(problems)
        raise ValueError(
            "Paired experiment dataset validation failed:\n"
            f"- {details}\n"
            "Sync/regenerate the question dataset before running the experiment."
        )

    return samples


def paired_task(samples, dataset_name: str) -> Task:
    return Task(
        dataset=MemoryDataset(samples=samples, name=dataset_name),
        solver=[static_two_turn_conversation()],
        scorer=[
            heron_old_prompt_scorer(),
            heron_proportionality_scorer(),
        ],
    )


@task
def heron_paired_test5():
    samples = load_paired_experiment_samples()[:5]
    return paired_task(samples, "heron_paired_test5")


@task
def heron_paired_full():
    samples = load_paired_experiment_samples()
    return paired_task(samples, "heron_paired_full")
