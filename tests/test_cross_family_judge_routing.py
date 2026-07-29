import pytest

from heron.scorer import (
    JUDGE_AGREEMENT_THRESHOLD,
    JUDGE_ROUTES,
    aggregate_judge_scores,
    model_family,
    select_judges,
)


@pytest.mark.parametrize(
    ("model_name", "expected_family"),
    [
        ("openai/gpt-5.6-sol", "openai"),
        ("openai-api/gpt-5.6-luna", "openai"),
        ("google/gemini-3.1-pro-preview", "google"),
        ("bedrock/us.anthropic.claude-opus-5", "anthropic"),
        ("anthropic/claude-sonnet-5", "anthropic"),
    ],
)
def test_model_family(model_name, expected_family):
    assert model_family(model_name) == expected_family


@pytest.mark.parametrize(
    "target_model",
    [
        "openai/gpt-5.6-sol",
        "google/gemini-3.1-pro-preview",
        "bedrock/us.anthropic.claude-opus-5",
    ],
)
def test_routes_never_use_same_family(target_model):
    target_family = model_family(target_model)
    judges = select_judges(target_model)

    assert judges == JUDGE_ROUTES[target_family]
    assert len(judges) == 2
    assert all(model_family(judge) != target_family for judge in judges)
    assert len({model_family(judge) for judge in judges}) == 2


def test_unknown_model_family_fails_closed():
    with pytest.raises(ValueError, match="Unsupported model family"):
        select_judges("other/unknown-model")


def test_reference_pair_resolves_at_threshold():
    mean, resolved, difference = aggregate_judge_scores(
        0.5,
        0.5 + JUDGE_AGREEMENT_THRESHOLD,
    )

    assert mean == pytest.approx(0.575)
    assert resolved is True
    assert difference == pytest.approx(0.15)


def test_reference_pair_marks_larger_difference_ambiguous():
    mean, resolved, difference = aggregate_judge_scores(0.2, 0.8)

    assert mean == pytest.approx(0.5)
    assert resolved is False
    assert difference == pytest.approx(0.6)
