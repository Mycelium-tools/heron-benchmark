"""Re-score the 24 verify-run scenarios with Gemini 3.6 Flash and compare to Opus 4.8.

Uses the pipeline's own build_scoring_messages so Flash sees the exact same
rubric + 14 few-shot pairs + scenario JSON that Opus saw. Two independent
passes measure Flash's own repeat stability at temperature=0.
"""
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, "/Users/allenlu/Desktop/AIxAnimals/heron-benchmark/dataset")
from dotenv import load_dotenv
load_dotenv("/Users/allenlu/Desktop/AIxAnimals/heron-benchmark/.env")

import instructor
from google import genai
from google.genai import types as genai_types

import scenario_generation as sg

VERIFY_JSON = "/Users/allenlu/Desktop/AIxAnimals/heron-benchmark/dataset/scenarios/verify_080626_2142/verify_scored.json"
OUT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "flash_qc_comparison.json")
FLASH = "gemini-3.6-flash"

data = json.load(open(VERIFY_JSON))
rows = data["dataset"]
print(f"Loaded {len(rows)} scored scenarios from verify run")

client = instructor.from_genai(genai.Client())


def score_one(scenario_dict: dict) -> sg.QCResponse:
    msgs = sg.build_scoring_messages(scenario_dict, sg.RUBRIC, sg.SCORING_EXAMPLES)
    # Gemini uses role "model" for assistant turns
    msgs = [
        {**m, "role": "model"} if m["role"] == "assistant" else m
        for m in msgs
    ]
    resp = client.chat.completions.create(
        model=FLASH,
        messages=msgs,
        response_model=sg.QCResponse,
        max_retries=3,
        config=genai_types.GenerateContentConfig(temperature=0.0, max_output_tokens=2048),
    )
    return resp


def run_pass(label: str) -> list[sg.QCResponse]:
    with ThreadPoolExecutor(max_workers=3) as ex:
        results = list(ex.map(lambda r: score_one(r["scenario"]), rows))
    print(f"pass {label}: done ({len(results)} judgments)")
    return results


pass1 = run_pass("1")
pass2 = run_pass("2")

# --- comparison ---
records = []
for row, f1, f2 in zip(rows, pass1, pass2):
    records.append({
        "question": row["scenario"]["question"][:90],
        "cell": {k: row["scenario"][k] for k in
                 ("failure_direction", "warranted_consideration", "salience", "context")},
        "opus_score": row["response"]["score"],
        "flash_score": f1.score,
        "flash_score_rerun": f2.score,
        "opus_explanation": row["response"]["explanation"],
        "flash_explanation": f1.explanation,
    })

opus = [r["opus_score"] for r in records]
flash = [r["flash_score"] for r in records]
flash2 = [r["flash_score_rerun"] for r in records]
n = len(records)

exact = sum(o == f for o, f in zip(opus, flash))
within1 = sum(abs(o - f) <= 1 for o, f in zip(opus, flash))
mean_diff = sum(f - o for o, f in zip(opus, flash)) / n
mae = sum(abs(f - o) for o, f in zip(opus, flash)) / n
flips = [(r, r["opus_score"], r["flash_score"]) for r in records
         if (r["opus_score"] >= 7) != (r["flash_score"] >= 7)]
stable = sum(a == b for a, b in zip(flash, flash2))

print("\n================ COMPARISON: Opus 4.8 vs Gemini 3.6 Flash (n=24) ================")
print(f"exact agreement:        {exact}/{n} ({exact/n:.0%})")
print(f"within 1 point:         {within1}/{n} ({within1/n:.0%})")
print(f"mean signed diff (F-O): {mean_diff:+.2f}")
print(f"mean absolute diff:     {mae:.2f}")
print(f"pass/fail flips (>=7):  {len(flips)}")
print(f"flash repeat stability: {stable}/{n} exact ({stable/n:.0%})")
print(f"opus  mean {sum(opus)/n:.2f} | flash mean {sum(flash)/n:.2f}")

from collections import Counter
print(f"opus  dist: {dict(sorted(Counter(opus).items()))}")
print(f"flash dist: {dict(sorted(Counter(flash).items()))}")

print("\n--- per-scenario ---")
print(f"{'opus':>4} {'flsh':>4} {'rern':>4}  scenario")
for r in sorted(records, key=lambda r: abs(r["flash_score"] - r["opus_score"]), reverse=True):
    marker = " <-- FLIP" if (r["opus_score"] >= 7) != (r["flash_score"] >= 7) else ""
    print(f"{r['opus_score']:>4} {r['flash_score']:>4} {r['flash_score_rerun']:>4}  {r['question']}{marker}")

print("\n--- largest disagreements (|diff| >= 2): flash explanations ---")
for r in records:
    if abs(r["flash_score"] - r["opus_score"]) >= 2:
        print(f"\n[opus {r['opus_score']} vs flash {r['flash_score']}] {r['question']}")
        print(f"  cell: {r['cell']}")
        print(f"  flash: {r['flash_explanation'][:400]}")

json.dump(records, open(OUT_JSON, "w"), indent=2)
print(f"\nFull records saved to {OUT_JSON}")
