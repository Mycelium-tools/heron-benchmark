"""
Per-language keyword tiers for the WildChat animal prefilter.

Terms are regex fragments, combined into one compiled alternation per language.
Language-specific lists are applied ONLY to rows whose `language` field matches —
this is what prevents cross-language collisions (French "chat" = cat but collides
with English "chat"; "python"/"mouse"/"bug" are programming words in English).

Tiers:
  TIER_A — unambiguous animal terms, always on.
  TIER_B — ambiguous terms, OFF by default. Promote one at a time only after
           eyeballing its hit quality in a stage-1 sample run.

Conventions:
  - Space-delimited languages: fragments are wrapped as \\b(?:...) at compile
    time, so a bare fragment like "veterinar" is a word-PREFIX match
    (veterinarian, veterinary, ...). Add a trailing \\b inside the fragment for
    exact-word matches where the prefix would collide (e.g. rats?\\b vs "rate").
  - Chinese: plain substring match (no word boundaries in CJK). Multi-character
    terms only — single characters like 马 (horse) collide with 马上 ("at once").

Language names match the WildChat `language` field values (full English names).
"""

# Applied to EVERY row regardless of language (English mixes into all languages).
TIER_A_ENGLISH = [
    # generic
    r"animals?\b", r"veterinar", r"taxiderm", r"euthan", r"zoos?\b", r"wildlife",
    r"kennel", r"neuter", r"spay\b|spayed|spaying", r"leash",
    # pets / companion
    r"dogs?\b", r"pupp(?:y|ies)", r"kitten", r"hamster", r"rabbits?\b",
    r"bunn(?:y|ies)", r"parrot", r"budgie", r"gecko", r"iguana", r"ferret",
    r"goldfish", r"tortoise", r"turtles?\b", r"guinea pig",
    # farmed / production
    r"livestock", r"poultry", r"chickens?\b", r"hens?\b", r"rooster",
    r"cattle", r"cows?\b", r"calf\b|calves\b", r"\bpigs?\b", r"piglet",
    r"sheep\b", r"goats?\b", r"lambs?\b", r"slaughter", r"abattoir",
    r"feedlot", r"broiler", r"dairy farm", r"ducks?\b",
    r"barn\b|barns\b",
    # seafood / fishing
    r"lobster", r"shrimps?\b", r"prawns?\b", r"crabs?\b", r"salmon", r"tilapia",
    r"oyster", r"octopus", r"squids?\b", r"tunas?\b", r"sardine", r"eels?\b",
    r"fishing", r"fisher(?:y|ies|man|men)", r"aquacult", r"seafood", r"aquarium",
    r"bait\b",
    # pest / wildlife encounters
    r"rodent", r"cockroach", r"\brats?\b", r"\bmice\b", r"mousetrap",
    r"glue traps?\b", r"raccoon", r"squirrel", r"pigeon", r"possum|opossum",
    r"deer\b", r"coyote", r"snakes?\b", r"infestation",
    # wild animals
    r"elephant", r"giraffe", r"rhino", r"whales?\b", r"dolphin", r"sharks?\b",
    r"tigers?\b", r"lions?\b", r"wolf\b|wolves\b",
    r"monkeys?\b", r"gorilla", r"chimpanzee",
    # insects & inverts
    r"\bbees?\b", r"beekeep", r"apiar", r"wasps?\b", r"mosquito",
    r"\bants?\b", r"silkworm", r"mealworm", r"locust", r"snails?\b",
    # horses
    r"horses?\b", r"equine", r"pony\b|ponies\b", r"foals?\b",
    # animal products
    r"leather", r"\bfur\b", r"\bwool\b", r"gelatin", r"foie gras", r"ivory",
    r"free[- ]range", r"cage[- ]free", r"grass[- ]fed",
]

# Language-specific Tier A extras (applied only when row language matches).
TIER_A_BY_LANGUAGE: dict[str, list[str]] = {
    "Chinese": [
        # substring match; multi-char terms only (see module docstring)
        "动物", "宠物", "兽医", "屠宰", "家禽", "牲畜", "养殖场", "水族馆",
        "钓鱼", "小狗", "狗狗", "小猫", "猫咪", "猪肉", "牛肉", "鸡肉", "羊肉",
        "奶牛", "绵羊", "山羊", "兔子", "乌龟", "仓鼠", "鹦鹉", "蜜蜂", "昆虫",
        "老鼠", "龙虾", "螃蟹", "海鲜", "皮革", "牧场", "斗鸡", "斗狗",
    ],
    "Russian": [
        r"животн",              # животное/животных (NOT живот = stomach)
        r"собак", r"щенк|щенок", r"кошк", r"котят|котёнок|котенок",
        r"ветеринар", r"скотовод", r"свинь|свинин",   # NOT "свине" (свинец = lead)
        r"куриц|курин|курятин",  # NOT "кур" prefix (курить = to smoke)
        r"птицефабрик", r"рыбалк|рыболов", r"аквариум", r"кролик",
        r"лошад", r"овц", r"охот(?!но)",  # NOT охотно = "willingly"
        r"зоопарк", r"питомц|питомец",
        r"хомяк", r"попугай", r"черепах", r"креветк", r"краб", r"лосос",
        r"убой", r"бойн", r"крыс",
    ],
    "Spanish": [
        r"animal(?:es)?\b", r"mascota", r"veterinari", r"perr[oa]s?\b",
        r"cachorr", r"gatit", r"gatos?\b", r"pollos?\b", r"gallin",
        r"ganado", r"matadero", r"cerdos?\b", r"vacas?\b", r"ovejas?\b",
        r"cabras?\b", r"caballos?\b", r"conejos?\b", r"\bpez\b|peces\b",
        r"pesca\b|pescar\b", r"acuario", r"langosta", r"camar[oó]n",
        r"abejas?\b", r"tortuga", r"loros?\b", r"cuero", r"apicult",
        r"zool[oó]gico", r"granja",
    ],
    "French": [
        # NOT "chat" — collides with the English loanword for online chat
        r"anima(?:l|ux)\b", r"v[eé]t[eé]rinaire", r"chiots?\b", r"chatons?\b",
        r"chiens?\b", r"poulets?\b", r"poules?\b", r"b[eé]tail", r"abattoir",
        r"[eé]levage", r"cochons?\b", r"porcs?\b", r"vaches?\b", r"moutons?\b",
        r"ch[eè]vres?\b", r"chev(?:al|aux)\b", r"lapins?\b", r"poissons?\b",
        r"aquarium", r"homard", r"crevette", r"abeille", r"tortue",
        r"perroquet", r"cuir\b", r"chasse\b", r"zoo\b",
    ],
    "Portuguese": [
        r"anima(?:l|is)\b", r"veterin[aá]ri", r"cachorr",   # cachorro = dog (BR)
        r"filhote", r"gatinh", r"gatos?\b", r"frango", r"galinha",
        r"gado\b", r"matadouro", r"porcos?\b", r"vacas?\b", r"ovelha",
        r"cabras?\b", r"cavalos?\b", r"coelho", r"peixes?\b", r"aqu[aá]rio",
        r"lagosta", r"camar[aã]o", r"abelha", r"tartaruga", r"papagaio",
        r"couro\b", r"ca[çc]a\b", r"zool[oó]gico",
    ],
    "German": [
        # "Tier" prefix is safe within German-language rows (Tierarzt, Haustier…)
        r"tier(?:e|arzt|ärzt|schutz|heim|halt)", r"haustier",
        r"\bhunde?n?\b",        # NOT bare "hund" prefix (hundert = hundred)
        r"welpen?\b", r"katzen?\b", r"k[aä]tzchen", r"h[uü]hner|huhn\b",
        r"gefl[uü]gel", r"vieh\b", r"schlachthof",  # NOT "schlacht" (= battle)
        r"schweine?\b", r"\bkuh\b|k[uü]he\b", r"\bschafe?\b", r"ziegen?\b",
        r"pferde?\b", r"kaninchen", r"fische?n?\b", r"aquarium", r"hummer\b",
        r"garnelen?\b", r"bienen?\b", r"schildkr[oö]te", r"papagei",
        r"leder\b", r"jagd\b", r"zoo\b",
    ],
}

# Ambiguous terms — OFF by default. Promote individually after checking hit
# quality (programming/idiom collisions noted per term).
TIER_B_ENGLISH = [
    r"\bcats?\b",      # unix cat, CAT scan, category abbreviations
    r"mouse\b",        # computer mouse
    r"\bbugs?\b",      # software bugs
    r"spiders?\b",     # web crawlers
    r"\bpets?\b",      # pet project, PET scan/plastic
    r"hunting",        # job hunting, house hunting
    r"cricket",        # the sport
    r"\bbats?\b",      # baseball
    r"grooming",       # personal grooming
    r"farms?\b",       # server farm, content farm
    r"\bfish\b",       # phishing adjacency is fine, but "fish" idioms abound
    r"birds?\b",       # Twitter-era idioms, "bird's eye view"
    r"bears?\b",       # "bear in mind", "can't bear" (verified noisy in smoke run)
    r"turkeys?\b",     # Turkey the country (verified noisy in smoke run)
    r"foxe?s?\b",      # 20th Century Fox, Fox as surname (verified noisy)
]

TIER_B_BY_LANGUAGE: dict[str, list[str]] = {
    "Russian": [r"мыш"],       # мышь = mouse (also computer mouse)
    "Spanish": [r"rat[oó]n"],  # computer mouse
    "French": [r"souris"],     # computer mouse
    "Portuguese": [r"\brato\b"],
    "German": [r"\bmaus\b"],
}
