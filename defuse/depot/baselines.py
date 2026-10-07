"""Frozen code baselines for Sorting Depot. Both read only what the model reads (the prompt text), plus fixed
word lists and the shared city gazetteer. Neither may be edited after a test bank is created: see
FROZEN_BEFORE and tests/test_depot.py.

- keyword: the original substring matcher (bank/keyword_baseline.json), with the manifest bug fixed: it now
  applies the manifest only in the "Check the list" round.
- dictionary: the critical review's stronger baseline (REVIEW.md on branch review/critical, commit 676daa1),
  copied verbatim. Its vocabulary was written after reading the v1 bank, so on v1 it is post-hoc; on the v2
  test bank, written later by a separate author, it is a frozen competitor."""
import json
import re
import unicodedata
from defuse.depot.game import BANK, BIN_NAMES

FROZEN_BEFORE = 'bank/v2'   # these baselines were committed before this test bank existed

def norm(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', s.lower())
                   if not unicodedata.combining(c))

# Prefixes, not complete item labels. Written after reading the bank: NOT held out.
WORDS = {
 'hazardous': '''batter lith batteri pila powerbank gasoline gasol gasolen petrol
 propane propain butane fuel lighter match spray paint acetone bleach bleech drain
 poison weedkiller firework fireworx sparkler flare ammunition ammo lamp-oil
 alcohol chlorine oven extinguisher scuba oxygen camping kerosene kerosine
 turpentine mothball ant-killer acid muriatic ethanol charger bear pepper
 black-powder diesel gasolina allumette feuerwerk lejia javel bombola rattengift
 diluant fuego municion fluuid cleanr unkraut alcool caustica benzinkanister
 veleno fogos'''.split(),
 'fragile': '''glass glas glss ceramic porcelain porcelin crystal crystl mirror
 mirrer vase china snow-globe snowglobe lightbulb litebulb bulb aquarium
 terracotta teracotta decanter hourglass test-tube windowpane pottery
 magnifying terrarium murano copa vidrio assiette porcelaine miroir spiegel
 kristall bicchieri vetro lampada tazze ceramica espelho figurine weinglaser
 jarron champain fish-tank plats porzellan verre lustre cristal piatti
 porcellana taca glasvase vajilla bauble'''.split(),
 'cold': '''frozen froze frzn ice chilled refrigerat fresh milk cheese yogurt
 yoghrt butter cream meat fish seafood vaccine insulin peas salmon chicken
 chikn cheddar pizza popsicle popsicel oyster shrimp beef tofu pasta-egg kefir
 mozzarella blueberry gelato gelatto lobster scallop ham pork lamb dumpling
 waffle eggnog mousse juice hummus cottage crab tuna helado lait tiefgekuhlt
 frango salmone vacuna yaourt hackfleisch schlagsahne queso gamba manteiga
 glace carne huitre creme requeijao joghurt pescado lachs gamberi poulet'''.split()
}
CITY = {norm(city): k for k, cities in json.loads((BANK/'cities.json').read_text()).items()
        for city in cities}
NAMES = {name: key for key, name in BIN_NAMES.items()}

def stronger(prompt):
    line = prompt.splitlines()[-1]
    label = re.search(r': "(.*)"', line).group(1)
    dest = re.search(r', going to (.+)\.$', line)
    if 'New rule: sort each package by the continent' in prompt:
        return CITY.get(norm(dest.group(1)), 'europe')
    if dest:
        pairs = dict(re.findall(r'packages for (.*?) go to (Cold|Hazardous|Fragile|Everything else)', prompt))
        if dest.group(1) in pairs:
            return NAMES[pairs[dest.group(1)]]
    ref = re.search(r'same bin as the last package from (.+)$', label)
    if ref:
        pairs = re.findall(r'" from (.*?) went to (Cold|Hazardous|Fragile|Everything else)', prompt)
        return next(NAMES[b] for c, b in reversed(pairs) if c == ref.group(1))
    s = norm(label)
    # Prioritize explicit hazardous containers and fragile materials over contents.
    for b, words in WORDS.items():
        if any(re.search(r'\b' + re.escape(w).replace(r'\-', r'[- ]'), s) for w in words):
            return b
    return 'other'


def keyword(prompt):
    """The original keyword matcher, working from the prompt text alone."""
    vocab = json.loads((BANK / 'keyword_baseline.json').read_text())
    line = prompt.splitlines()[-1]
    label = re.search(r': "(.*)"', line).group(1)
    dest = re.search(r', going to (.+?)(?:, from .+)?\.$', line)
    if 'New rule: sort each package by the continent' in prompt:
        city = dest.group(1).lower() if dest else ''
        return next((k for k, v in vocab['cities'].items() if city in v), 'europe')
    if dest and 'Check the list' in prompt.splitlines()[0]:
        pairs = dict(re.findall(r'packages for (.*?) go to (Cold|Hazardous|Fragile|Everything else)', prompt))
        if dest.group(1) in pairs:
            return NAMES[pairs[dest.group(1)]]
    ref = re.search(r'same bin as the last package from (.+)$', label)
    if ref:
        pairs = re.findall(r'" from (.*?) went to (Cold|Hazardous|Fragile|Everything else)', prompt)
        hit = [b for c, b in pairs if c == ref.group(1)]
        if hit:
            return NAMES[hit[-1]]
    low = label.lower()
    for b in ('cold', 'hazardous', 'fragile'):
        if any(word in low for word in vocab[b]):
            return b
    return 'other'


dictionary = stronger
CONTROLLERS = {'keyword': keyword, 'dictionary': dictionary}
