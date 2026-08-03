import importlib.util
import sys
from pathlib import Path

import pytest

SCORER_PATH = Path(__file__).with_name("pairwise_scorer.py")
SPEC = importlib.util.spec_from_file_location("pairwise_scorer", SCORER_PATH)
assert SPEC and SPEC.loader
PAIRWISE_SCORER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PAIRWISE_SCORER
SPEC.loader.exec_module(PAIRWISE_SCORER)

PAIRWISE_JUDGE_PROMPT = PAIRWISE_SCORER.PAIRWISE_JUDGE_PROMPT
build_pairwise_prompt = PAIRWISE_SCORER.build_pairwise_prompt
normalize_preference = PAIRWISE_SCORER.normalize_preference
parse_pairwise_judgment = PAIRWISE_SCORER.parse_pairwise_judgment
parse_preference = PAIRWISE_SCORER.parse_preference


@pytest.mark.parametrize("preference", ["A", "B", "TIE"])
def test_parse_preference(preference):
    assert parse_preference(f"REASONING: Test.\n\nPREFERENCE: {preference}") == preference


def test_parse_preference_rejects_other_output():
    assert parse_preference("PREFERENCE: RESPONSE A") == "UNPARSEABLE"


def test_parse_pairwise_judgment_requires_reasoning():
    parsed = parse_pairwise_judgment("PREFERENCE: A")

    assert parsed.preference == "A"
    assert parsed.format_valid is False


def test_normalize_preference():
    assert normalize_preference("A", "sol", "opus") == "sol"
    assert normalize_preference("B", "sol", "opus") == "opus"
    assert normalize_preference("TIE", "sol", "opus") == "TIE"


def test_normalize_preference_rejects_invalid_value():
    with pytest.raises(ValueError, match="Cannot normalize"):
        normalize_preference("UNPARSEABLE", "sol", "opus")


def test_build_prompt_replaces_only_evaluation_placeholders():
    prompt = build_pairwise_prompt("user request", "answer a", "answer b")

    assert "user request" in prompt
    assert "answer a" in prompt
    assert "answer b" in prompt
    assert "{user_request}" not in prompt
    assert "{response_a}" not in prompt
    assert "{response_b}" not in prompt
    assert prompt.startswith(PAIRWISE_JUDGE_PROMPT.split("CALIBRATION EXAMPLES")[0])


def test_pairwise_prompt_has_no_scalar_output_cues():
    assert PAIRWISE_JUDGE_PROMPT.count("--- EXAMPLE") == 4
    assert "CLASSIFICATION:" not in PAIRWISE_JUDGE_PROMPT
    assert "SCORE:" not in PAIRWISE_JUDGE_PROMPT
    assert "0.9-1.0" not in PAIRWISE_JUDGE_PROMPT
