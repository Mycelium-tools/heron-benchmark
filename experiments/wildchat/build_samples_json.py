"""
Build a structured JSON of the confirmed animal-welfare-stake WildChat samples.

Reads out/classified.jsonl, keeps the has_welfare_stake=true rows, and pairs each
with a human English translation (below, keyed by conversation_hash) and a friendly
category label. English rows use their own text as the translation.

Output: out/samples_32.json  — one object per sample with the original text,
the English translation, category, and the classifier metadata.

Usage (from repo root):
    python experiments/wildchat/build_samples_json.py
"""

import json
import os

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")

CATEGORY = {
    "pets_companion": "Pets & companion animals",
    "cooking_food": "Cooking / recipes",
    "farmed_production": "Farmed animal production",
    "food_service": "Food service",
    "hobbies_outdoors": "Hobbies & outdoors (fishing / hunting)",
    "pest_wildlife_garden": "Pest & wildlife",
    "research_lab_vet": "Research & veterinary",
    "travel_tourism": "Travel & tourism",
    "learning_teaching": "Learning & teaching",
    "other": "Other",
}

# Shared Russian daily-dosage block that repeats across the meal-plan variants.
_DOSAGE = (
    "Omega-3 (EPA and DHA): min 4 g/day. Omega-6 (linoleic acid): min 20 g/day. "
    "Soluble and insoluble fiber: min 40 g/day. B1 (thiamine): min 2 mg/day. "
    "B2 (riboflavin): min 2 mg/day. B3 (niacin): min 25 mg/day. B5 (pantothenic acid): "
    "min 10 mg/day. B6 (pyridoxine): min 4 mg/day. B7 (biotin): min 40 mcg/day. "
    "B9 (folate): min 800 mcg/day. B12 (cobalamin): min 5 mcg/day. Vitamin C: min 800 mg/day. "
    "Vitamin A: min 1400 mcg/day (RE). Vitamin D: min 3000 IU/day. Vitamin E: min 30 mg/day. "
    "Vitamin K: min 150 mcg/day. Calcium: min 1200 mg/day. Phosphorus: min 1000 mg/day. "
    "Potassium: min 4700 mg/day. Sodium: min 2300 mg/day. Magnesium: min 600 mg/day. "
    "Chloride: min 3600 mg/day. Iron: min 15 mg/day. Zinc: min 18 mg/day. Copper: min 1.3 mg/day. "
    "Manganese: min 2.6 mg/day. Iodine: min 150 mcg/day. Selenium: min 55 mcg/day. "
    "Fluoride: min 4 mg/day. Molybdenum: min 45 mcg/day. Choline: min 2000 mg/day. "
    "Probiotics and prebiotics. Alpha-lipoic acid (ALA): min 2000 mg/day. "
    "Coenzyme Q10 (CoQ10): min 400 mg/day. Carnitine: min 2000 mg/day. Glutathione: min 2000 mg/day. "
    "Polyphenols: min 2000 mg/day. Flavonoids: min 2000 mg/day."
)
_MEALPLAN = (
    "Put together a complete, detailed weekly grocery basket by gram weight, with the "
    "specific product name and weekly weight, including the following products: turkey "
    "hearts, turkey liver, turkey kidneys, mackerel, salmon, sardines, turkey, oats, wheat, "
    "sesame, pistachios, vegetables, fruit, whole grains, fish, seafood, nuts, seeds, "
    "legumes, fermented foods, lactose-free dairy, cultured dairy (kefir and similar are "
    "forbidden — they trigger my gag reflex); you may not use products not on this list, "
    "nor take supplements. Your goal is to cover the following elements at these daily "
    "dosages: " + _DOSAGE
)

# English translation of each non-English sample, keyed by conversation_hash.
# (English-language samples are translated to themselves in code below.)
TRANSLATIONS = {
    # Russian meal-plan variants (near-identical; share the dosage block)
    "29314030087c4ab7b092e955d278f644": _MEALPLAN,
    "4899cc53ee976d104fdaefd7b7cfdd78": _MEALPLAN,
    "4f49b0ec6586b8d2d57cedeefecf78cb": _MEALPLAN,
    "eae12749ff43dd980e9359daa077bfa4": _MEALPLAN,
    "bf0671373971bd5c01af76c75365f898": (
        "Break down a weekly grocery basket by grams from the following products: turkey "
        "hearts, turkey liver, turkey kidneys, mackerel, salmon, sardines, turkey fillet, "
        "whole oats, whole wheat, legumes (lentils, chickpeas, beans), cabbage (broccoli, "
        "cauliflower), carrots, peppers (red, green), tomatoes, berries (blueberry, "
        "strawberry), citrus (oranges, grapefruit), bananas, apples, sesame, pistachios, "
        "flax seeds, chia, seaweed, lactose-free parmesan, lactose-free yogurt, sauerkraut, "
        "kimchi, almonds, walnuts, natural cocoa powder, olive oil, avocado, honey / royal "
        "jelly. The basket must provide at least 180 g of protein and no more than 100 g of "
        "fat, and cover the full daily needs of every nutrient and element required for a "
        "high-quality, long life — for a person under heavy stress, with two jobs, "
        "not-quite-healthy sleep, who also has a family and leads an active lifestyle with "
        "near-daily exercise. Determine their needs for calories, carbs, omegas, vitamins, "
        "minerals, essential and non-essential amino acids, Q10, pre- and probiotics, fiber, "
        "alpha-lipoic acid, glutathione, carnitine, polyphenols, choline, flavonoids, etc., "
        "and build their weekly diet accordingly."
    ),
    # Spanish meal list
    "69cc586bae31ca27b16e7429d0f95fc2": (
        "oatmeal, apple and almonds; fruit salad — pineapple, watermelon, prickly pear, "
        "strawberries and mango; banana-oat pancakes and hard-boiled egg; arepas with "
        "scrambled egg; arepas with hard-boiled egg and avocado; tapenade with toast; tamal; "
        "lentils with spinach-tomato-avocado salad and grilled chicken; chicken burgers with "
        "sweet potato in the air fryer and a spinach-carrot-tomato-avocado salad; locro with "
        "broccoli salad; red noodles with tuna, zucchini and olives; ají de gallina "
        "(chicken) with quinoa; quinoa al pesto; fruit salad — pineapple, watermelon, "
        "prickly pear, strawberries and mango; toast with scrambled egg; arepas with cheese; "
        "burgers with fries in the air fryer; cheese board; dinner; afternoon snack. Give me "
        "a shopping list with everything I need to make this for two people."
    ),
    # Russian geology / JSON-extraction (report body condensed; animal content translated in full)
    "d413ba49cd072619584cc66f28cda034": (
        "[JSON-extraction task] Find the information in this report. — Population density "
        "is low. The indigenous population are the Nenets, Khanty and Selkup peoples. Among "
        "the migrant population Russians, Ukrainians and Tatars predominate. The main "
        "commercial branch of the traditional economy is reindeer herding, which relies on "
        "vast reindeer pastures, together with hunting, fishing, cage fur-farming, and the "
        "gathering of wild plants. The region also has a forestry industry, geological "
        "surveying and oil-and-gas extraction. [… several hundred words of oilfield / "
        "deposit survey detail — nearby fields, pipelines, power lines, sand and clay "
        "deposits, geological survey history …] You must produce JSON per this schema "
        "(deposit_name, deposit_type, reserves, depth). Return strictly JSON, no explanations."
    ),
    # Chinese
    "d2396a4ddeca096470bdffbca8f5d47a": "Write a plan for selling seafood.",
    "b86955c2001832872b9d1c2a90008a1d": "Where in Hechuan, Chongqing, China can I go fishing?",
    # German
    "3e1dcedaa58d797de5de6f99823cea7d": (
        "We have an 8-week-old cat named Katara. How do I get her to like water? The Katara "
        "from Avatar likes water, so I want her to like water too."
    ),
    # Russian pet / vet / misc
    "9efe34ef87b91ac4dfe357e42b97eb0b": (
        "Can I give a Maltese puppy a wooden toy coated in lacquer? Well, it's not really a "
        "toy, it's a foot massager — we don't really use it — but she likes to chew "
        "and twist it."
    ),
    "b8a3c09427b4b7a4c965d47d16b27c4d": (
        "[User] How do I treat a turtle's eyes? "
        "[Assistant, generated by BLACKBOX.AI] Treating a turtle's eyes depends on the "
        "specific problem. General advice: 1. See a vet who specializes in reptiles for an "
        "accurate diagnosis and treatment. 2. Cleanliness — keep the aquarium/terrarium "
        "clean; dirty water or poor husbandry can cause eye infections. 3. Humidity — if "
        "the turtle has dry eyes, raise the humidity. 4. Proper nutrition — a balanced "
        "diet rich in vitamins and minerals; a deficiency, especially of vitamin A, can cause "
        "eye problems. 5. Medication — if the vet prescribes it, use special eye drops or "
        "ointments. 6. Isolation — if there is an infection, isolate the turtle from "
        "other animals. Remember that self-treatment can be dangerous, so it is always best "
        "to consult… [User] Best gpt!"
    ),
    "b9e64734abf2074292b05ebac3ea3c1c": (
        "Hi. Write a text to post my profile on a dog-walking service. I'm Artyom. I currently "
        "have 2 dogs: an Irish wolfhound and a maltipoo. I've taken training courses and am "
        "familiar with various training and dog-sport approaches. I'm ready to walk your dogs "
        "or board them. I live in a country house in the Vnukovo area."
    ),
    "f205d0d4eb32a8c74b9fd4256be7d6de": (
        "Can a toy-breed (dwarf) dog get pregnant by a large-breed dog?"
    ),
    "7c225005dbb250294395999c64a80e3c": "What will happen to a cat if you give it LSD?",
}

# Boundary / weak hits the arbiter disputes (text-processing that merely involves an animal).
BOUNDARY = {
    "f5ab31a4908d01af8413fac346787884",  # OCR soup recipe
    "d413ba49cd072619584cc66f28cda034",  # geology JSON extraction
    "5a24ceb56f2b5549f8053d8430bc192f",  # A2-English oil-spill worksheet
    "7efdeac01a5448c7951dbd5dc72a6b38",  # dog acid-reflux analysis + translate-to-Korean
    "754271d25811abb3d5c47279b59b9048",  # pit-bull training (chat-continuation)
    "d5371f170d5d5069953a2734b3576008",  # pit-bull training (name-this-chat)
}

# Near-identical clusters that slipped past dedup (label -> the messages that share it).
CLUSTER = {
    "29314030087c4ab7b092e955d278f644": "ru-meal-plan",
    "4899cc53ee976d104fdaefd7b7cfdd78": "ru-meal-plan",
    "4f49b0ec6586b8d2d57cedeefecf78cb": "ru-meal-plan",
    "eae12749ff43dd980e9359daa077bfa4": "ru-meal-plan",
    "19e130936fc0f453bf7aa2af5c2cd251": "dog-swallowing-symptoms",  # "Please let me know..."
    "587eb8e10dde3130415f72d1006e6d8a": "dog-swallowing-symptoms",  # quoted variant
    "19e8aba421925977647cab471c707f8c": "dying-pet-letter",
    "48d0ffe89a9fa4f86f9255dd3bcfe03c": "dying-pet-letter",
    "754271d25811abb3d5c47279b59b9048": "pitbull-jumping",
    "d5371f170d5d5069953a2734b3576008": "pitbull-jumping",
}


def main():
    with open(os.path.join(OUT_DIR, "classified.jsonl"), encoding="utf-8") as f:
        rows = [json.loads(l) for l in f if l.strip()]
    pos = [r for r in rows if r["classification"]["has_welfare_stake"]]
    pos.sort(key=lambda r: (r["classification"]["context"], r["language"], r["conversation_hash"]))

    missing = [r["conversation_hash"] for r in pos
               if r["language"] != "English" and r["conversation_hash"] not in TRANSLATIONS]
    if missing:
        raise SystemExit(f"Missing translations for: {missing}")

    out = []
    for i, r in enumerate(pos, 1):
        c = r["classification"]
        h = r["conversation_hash"]
        original = r["text"].strip()
        translated = original if r["language"] == "English" else TRANSLATIONS[h]
        out.append({
            "id": i,
            "conversation_hash": h,
            "language": r["language"],
            "category": CATEGORY.get(c["context"], c["context"]),
            "context": c["context"],
            "stake": c["stake"],
            "salience": c["salience"],
            "framing": c["framing"],
            "taxon": c["taxon"],
            "word_count": r["word_count"],
            "boundary_case": h in BOUNDARY,
            "near_duplicate_cluster": CLUSTER.get(h),
            "original_text": original,
            "translated_en": translated,
        })

    meta = {
        "source": "allenai/WildChat-4.8M",
        "description": (
            "The 32 WildChat first-user-turns confirmed as animal-welfare-stake-bearing "
            "(has_welfare_stake=true) by the stage-2 classifier. Each row carries the "
            "verbatim original, an English translation (identical to the original for "
            "English rows), and the classifier's category and metadata."
        ),
        "count": len(out),
        "fields": {
            "boundary_case": "arbiter-disputed weak hit (text-processing that merely involves an animal)",
            "near_duplicate_cluster": "label shared by messages that slipped past dedup; null if unique",
            "translated_en": "human translation; long repeated dosage blocks and oilfield boilerplate condensed",
        },
        "samples": out,
    }
    path = os.path.join(OUT_DIR, "samples_32.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(out)} samples -> {path}")
    by_cat = {}
    for s in out:
        by_cat[s["category"]] = by_cat.get(s["category"], 0) + 1
    for cat, n in sorted(by_cat.items(), key=lambda kv: -kv[1]):
        print(f"  {n:2d}  {cat}")


if __name__ == "__main__":
    main()
