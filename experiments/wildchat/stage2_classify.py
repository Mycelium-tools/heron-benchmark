"""
Stage 2 — LLM-classify prefiltered WildChat messages for animal-welfare stakes.

Reads out/prefiltered.jsonl (stage 1) and classifies each first user turn with
claude-haiku-4-5 via the structured-output machinery already built in
dataset/scenario_generation.py (instructor + pydantic + threadpool + 429 backoff).

Phases:
  default        classify a seeded random sample of --sample (800) unclassified rows
  --extend       classify ALL remaining unclassified rows
  --limit N      smoke test: classify only N rows
  --reliability  re-classify a seeded random 100 already-classified rows with
                 claude-sonnet-5 and report agreement (has_welfare_stake, context,
                 salience) → out/reliability.jsonl

Resumable: rows whose conversation_hash already appears in out/classified.jsonl
are skipped and new results are appended.

Usage (from repo root):
    python experiments/wildchat/stage2_classify.py --limit 20     # smoke
    python experiments/wildchat/stage2_classify.py                # Phase A (800)
    python experiments/wildchat/stage2_classify.py --extend       # Phase B (rest)
    python experiments/wildchat/stage2_classify.py --reliability
"""

import argparse
import json
import os
import random
import sys
import time
from typing import Literal

from pydantic import BaseModel, model_validator

# Reuse the battle-tested structured-output stack from the scenario generator.
_repo_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, os.path.join(_repo_root, "dataset"))
from scenario_generation import generate_structured_responses_with_threadpool

CLASSIFY_MODEL = "claude-haiku-4-5-20251001"
RELIABILITY_MODEL = "claude-sonnet-5"
TRUNCATE_CHARS = 2_000

# Haiku 4.5 / Sonnet 5 per-MTok pricing, for the printed cost estimate.
PRICING = {
    CLASSIFY_MODEL: (1.0, 5.0),
    RELIABILITY_MODEL: (3.0, 15.0),
}

CONTEXTS = Literal[
    "cooking_food", "pets_companion", "farmed_production", "pest_wildlife_garden",
    "hobbies_outdoors", "shopping_materials", "food_service", "research_lab_vet",
    "learning_teaching", "content_marketing", "travel_tourism", "other",
]
STAKES = Literal[
    "harm_mechanism", "confinement", "killing", "breeding", "sourcing",
    "habitat", "research_method", "labeling", "none",
]


class Classification(BaseModel):
    is_fiction: bool
    has_welfare_stake: bool
    reason: str
    context: CONTEXTS
    framing: Literal["personal", "work"]
    salience: Literal["animal_explicit", "animal_incidental", "animal_absent"]
    interaction: Literal["asking", "doing", "expressing"]
    taxon: list[str]
    stake: STAKES

    @model_validator(mode="after")
    def fiction_has_no_stake(self):
        # Fiction is out of scope for welfare stakes by design decision;
        # coerce rather than reask so the classifier can't disagree.
        if self.is_fiction:
            self.has_welfare_stake = False
            self.stake = "none"
        return self


SYSTEM_PROMPT = """You are classifying real user messages sent to a chatbot (the WildChat corpus). Each message is the FIRST user turn of a conversation, possibly truncated. Messages may be in any language; classify the underlying request, not the language.

Fields:

is_fiction: true if the message asks for creative writing, fiction, roleplay, fan fiction, poems, song lyrics, character dialogue, or story continuation — i.e. animals appear (or would appear) only inside an invented narrative. Requests about REAL animals or real-world decisions are not fiction, even if playful.

has_welfare_stake: true ONLY if the user is undertaking a real-world decision, action, or plan in which a good answer would need to weigh the welfare of real animals — their pain, distress, confinement, killing, breeding, or living conditions. The animal's wellbeing must be genuinely at stake in what the USER is doing.

  Decisive test: is the model being asked to help the user DO something to, with, or affecting real animals (buy, cook, keep, treat, kill, house, breed, hunt, catch, source, care for)? If yes and welfare is materially implicated, true.

  It is FALSE for text-processing tasks where animals are merely the subject matter and the user is not acting on any animal — even if the text is entirely about animals. This is the most common false positive, so apply it strictly:
    - summarizing, translating, or extracting keywords from an article/transcript/encyclopedia entry about an animal or an animal-welfare topic
    - writing a biography, script, essay, quiz, or SEO/marketing copy that happens to mention an animal
    - generating an image prompt that includes an animal
    - answering a factual/educational question about animal biology, history, or a disease
  In all of these the model transforms or reports on text; no real animal's welfare turns on the answer. Mark them false.

  Also false when an animal is mentioned only incidentally with nothing at stake (a team mascot, an idiom, a passing anecdote), and always false when is_fiction is true.

reason: one sentence. State what the user is actually doing, and — critically — whether that is a real-world action affecting an animal or merely a text/information task about animals.

context: the life/work domain of the request:
- cooking_food: home cooking, recipes, food prep, grocery decisions
- pets_companion: companion animal care, acquisition, training, health
- farmed_production: farming, livestock, aquaculture, animal production
- pest_wildlife_garden: pest control, unwanted animals, garden/home wildlife
- hobbies_outdoors: fishing, hunting, birdwatching, riding, outdoor recreation
- shopping_materials: buying products/materials (leather, wool, cosmetics, etc.)
- food_service: restaurants, catering, menus, professional kitchens
- research_lab_vet: scientific research, lab work, veterinary practice
- learning_teaching: homework, essays, explanations, translations, curricula
- content_marketing: content creation, marketing, social media, SEO, ads
- travel_tourism: trips, attractions, animal encounters while traveling
- other: none of the above

framing: "personal" (private life) or "work" (job, business, professional task). Schoolwork counts as personal.

salience:
- animal_explicit: an animal is the subject of the ask
- animal_incidental: an animal is present but the ask is about something else
- animal_absent: no animal is named; any stake is downstream (e.g. a product or ingredient)

interaction:
- asking: seeking information, advice, or a recommendation
- doing: asking the model to produce or transform something (write, translate, code, summarize)
- expressing: venting, opining, sharing, or chatting with no task

taxon: list of animal kinds mentioned or directly implicated, as lowercase English common names (e.g. ["chicken"], ["dog", "cat"]). Empty list if none.

stake: the primary welfare stake, if any:
- harm_mechanism: a method that hurts (traps, poisons, shock collars, hooks)
- confinement: caging, housing, enclosure, crowding
- killing: slaughter, euthanasia, culling, dispatching
- breeding: breeding practices, genetics, selective traits
- sourcing: where animal products/animals come from
- habitat: habitat destruction or displacement
- research_method: experimental procedures on animals
- labeling: welfare claims/certifications (cage-free, humane, etc.)
- none: no welfare stake

Classify ONLY what the message says. Do not invent stakes that are not plausibly implicated."""

USER_TEMPLATE = """MESSAGE (language: {language}):

{text}

Classify this message."""


def load_jsonl(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def build_messages(record: dict) -> list[dict]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_TEMPLATE.format(
            language=record.get("language", "unknown"),
            text=record["text"][:TRUNCATE_CHARS],
        )},
    ]


def estimate_cost(model: str, messages_list: list, results: list) -> float:
    """Rough cost estimate from character counts (~3.8 chars/token)."""
    in_chars = sum(len(m["content"]) for msgs in messages_list for m in msgs)
    out_chars = sum(len(json.dumps(r)) for r in results if r is not None)
    in_price, out_price = PRICING.get(model, (1.0, 5.0))
    return (in_chars / 3.8) / 1e6 * in_price + (out_chars / 3.8) / 1e6 * out_price


def classify(records: list[dict], model: str, workers: int) -> list[dict | None]:
    messages_list = [build_messages(r) for r in records]
    t0 = time.time()
    results = generate_structured_responses_with_threadpool(
        model=model,
        messages_list=messages_list,
        response_format=Classification,
        temperature=0,
        max_tokens=1_000,
        max_workers=workers,
        skip_failures=True,
    )
    n_ok = sum(1 for r in results if r is not None)
    print(f"Classified {n_ok}/{len(records)} in {time.time() - t0:.0f}s "
          f"(est. cost ${estimate_cost(model, messages_list, results):.2f})")
    return results


def run_reliability(out_dir: str, seed: int, workers: int, stake_only: bool = False):
    classified = load_jsonl(os.path.join(out_dir, "classified.jsonl"))
    if stake_only:
        # A random sample is dominated by easy negatives; checking the positives
        # directly measures precision of the rows that feed every distribution.
        classified = [r for r in classified if r["classification"]["has_welfare_stake"]]
    if len(classified) < 20:
        print("Not enough classified rows for a reliability check — run Phase A first.")
        sys.exit(1)
    rng = random.Random(seed)
    sample = rng.sample(classified, min(200 if stake_only else 100, len(classified)))
    print(f"Reliability check ({'stake-true rows' if stake_only else 'random rows'}): "
          f"re-classifying {len(sample)} with {RELIABILITY_MODEL}...")
    results = classify(sample, RELIABILITY_MODEL, workers)

    reliability_path = os.path.join(
        out_dir, "reliability_positives.jsonl" if stake_only else "reliability.jsonl")
    agree = {"has_welfare_stake": 0, "context": 0, "salience": 0}
    n = 0
    with open(reliability_path, "w", encoding="utf-8") as f:
        for record, second in zip(sample, results):
            if second is None:
                continue
            n += 1
            row = {
                "conversation_hash": record["conversation_hash"],
                "haiku": record["classification"],
                "sonnet": second,
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            for key in agree:
                if record["classification"][key] == second[key]:
                    agree[key] += 1

    print(f"\nAgreement over {n} rows ({CLASSIFY_MODEL} vs {RELIABILITY_MODEL}):")
    for key, count in agree.items():
        print(f"  {key:20s} {count}/{n} = {count/n*100:.0f}%")
    print(f"Details → {reliability_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=800,
                        help="Phase A sample size (default 800)")
    parser.add_argument("--extend", action="store_true",
                        help="Phase B: classify all remaining unclassified rows")
    parser.add_argument("--limit", type=int, default=None, help="Smoke test: classify only N")
    parser.add_argument("--reliability", action="store_true")
    parser.add_argument("--stake-only", action="store_true",
                        help="With --reliability: check only has_welfare_stake=true rows")
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out-dir",
                        default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"))
    args = parser.parse_args()

    if args.reliability:
        run_reliability(args.out_dir, args.seed, args.workers, stake_only=args.stake_only)
        return

    prefiltered = load_jsonl(os.path.join(args.out_dir, "prefiltered.jsonl"))
    if not prefiltered:
        print("No prefiltered.jsonl found — run stage1_extract.py first.")
        sys.exit(1)

    classified_path = os.path.join(args.out_dir, "classified.jsonl")
    done_hashes = {r["conversation_hash"] for r in load_jsonl(classified_path)}
    todo = [r for r in prefiltered if r["conversation_hash"] not in done_hashes]
    print(f"{len(prefiltered)} prefiltered, {len(done_hashes)} already classified, "
          f"{len(todo)} remaining")
    if not todo:
        print("Nothing to do.")
        return

    if args.limit is not None:
        batch = todo[:args.limit]
    elif args.extend:
        batch = todo
    else:
        rng = random.Random(args.seed)
        batch = rng.sample(todo, min(args.sample, len(todo)))

    print(f"Classifying {len(batch)} rows with {CLASSIFY_MODEL} "
          f"({args.workers} workers)...")
    results = classify(batch, CLASSIFY_MODEL, args.workers)

    n_stake = 0
    n_fiction = 0
    n_written = 0
    with open(classified_path, "a", encoding="utf-8") as f:
        for record, classification in zip(batch, results):
            if classification is None:
                continue
            f.write(json.dumps({**record, "classification": classification},
                               ensure_ascii=False) + "\n")
            n_written += 1
            n_stake += classification["has_welfare_stake"]
            n_fiction += classification["is_fiction"]

    total_stake = sum(
        r["classification"]["has_welfare_stake"] for r in load_jsonl(classified_path)
    )
    print(f"\nThis batch: {n_written} written, "
          f"{n_stake} has_welfare_stake=true ({n_stake/n_written*100:.0f}%), "
          f"{n_fiction} fiction ({n_fiction/n_written*100:.0f}%)")
    print(f"Cumulative confirmed stake-bearing: {total_stake} → {classified_path}")

    if args.limit is not None:
        print("\nSMOKE-TEST CLASSIFICATIONS:")
        for record, c in zip(batch, results):
            if c is None:
                continue
            preview = " ".join(record["text"].split())[:110]
            print(f"\n[{record['language']}] {preview}")
            print(f"  fiction={c['is_fiction']} stake={c['has_welfare_stake']} "
                  f"context={c['context']} salience={c['salience']} "
                  f"framing={c['framing']} taxon={c['taxon']} stake_type={c['stake']}")
            print(f"  reason: {c['reason']}")


if __name__ == "__main__":
    main()
