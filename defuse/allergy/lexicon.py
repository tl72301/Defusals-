"""Food words: the vocabulary the scenario plans use, and the frozen mapping from a food name to the FDA category.

The mapping follows the definitions in rules.DEFINITIONS. The raw-names system (ALLERGY_PROTOCOL.md §6) uses it to turn
the food names the model wrote into categories; the plans draw every allergen word from the same lists."""
import re

# Words a plan may use for each allergen. 'plain' for the original style, 'hard' adds derived or specific names.
WORDS = {
    'PEANUT': {'plain': ['peanuts'], 'hard': ['peanut butter', 'peanut sauce', 'groundnuts']},
    'TREE_NUT': {'plain': ['tree nuts'], 'hard': ['almonds', 'cashews', 'pistachios', 'walnuts', 'pecans', 'hazelnuts',
                                                   'macadamia nuts', 'pine nuts', 'Brazil nuts']},
    'MILK': {'plain': ['dairy', 'milk'], 'hard': ['lactose', 'ghee', 'whey', 'goat cheese', 'butter', 'cream', 'feta']},
    'EGG': {'plain': ['eggs'], 'hard': ['mayo', 'aioli', 'duck eggs', 'quail eggs', 'meringue']},
    'WHEAT': {'plain': ['wheat', 'gluten'], 'hard': ['celiac', 'spelt', 'semolina', 'durum', 'farro']},
    'SOY': {'plain': ['soy'], 'hard': ['tofu', 'edamame', 'miso', 'soy sauce', 'tempeh']},
    'SESAME': {'plain': ['sesame'], 'hard': ['tahini', 'sesame oil', 'sesame seeds']},
    'FISH': {'plain': ['fish'], 'hard': ['salmon', 'anchovies', 'cod', 'tuna', 'fish sauce']},
    'SHELLFISH': {'plain': ['shellfish', 'shrimp'], 'hard': ['prawns', 'crab', 'lobster', 'crayfish']},
}
AMBIGUOUS = {'nuts': ('PEANUT', 'TREE_NUT'), 'nut': ('PEANUT', 'TREE_NUT'), 'seafood': ('FISH', 'SHELLFISH')}

# Phrases checked before their parts ("coconut milk" before "milk").
NOT_ALLERGENS = ['coconut milk', 'oat milk', 'coconut', 'chestnuts', 'chestnut', 'rice milk', 'nutmeg', 'butternut squash',
                 'cocoa butter', 'shea butter', 'peanut-free', 'nut-free']
EXTRA = {
    'PEANUT': ['peanut', 'groundnut', 'peanut oil', 'peanut flour'],
    'TREE_NUT': ['tree nut', 'almond', 'almond milk', 'almond flour', 'cashew', 'pistachio', 'walnut', 'black walnut',
                 'heartnut', 'pecan', 'hazelnut', 'filbert', 'filberts', 'macadamia', 'macadamia nut', 'pine nut',
                 'pignoli', 'Brazil nut'],
    'MILK': ['lactose intolerance', 'lactose intolerant', 'cheese', 'yogurt', 'yoghurt', 'casein', 'buttermilk',
             'sheep milk', "sheep's milk", 'goat milk', "goat's milk", 'parmesan', 'mozzarella', 'cheddar'],
    'EGG': ['egg', 'mayonnaise', 'duck egg', 'quail egg', 'egg yolk', 'egg whites', 'egg white'],
    'WHEAT': ['coeliac', 'celiac disease', 'gluten-free', 'wheat flour', 'triticale', 'einkorn', 'khorasan',
              'kamut'],
    'SOY': ['soya', 'soybean', 'soybeans', 'soy milk', 'tamari', 'shoyu'],
    'SESAME': ['sesame seed', 'benne seeds'],
    'FISH': ['anchovy', 'trout', 'halibut', 'tilapia', 'bass', 'haddock', 'sardines', 'mackerel'],
    'SHELLFISH': ['prawn', 'crabs', 'lobsters', 'crawfish', 'langoustine', 'langoustines', 'crustaceans', 'crustacean',
                  'crustacean shellfish'],
}
# Fryer items: what shares the fries oil (rules.FRYER_ADDS categories only).
FRYER_ITEMS = {'wheat': ['the breaded chicken tenders', 'the battered onion rings', 'the breaded pickles'],
               'shellfish': ['the shrimp', 'the fried shrimp', 'the shrimp for the tacos'],
               'fish': ['the cod', 'the fish', 'the catfish']}
FRYER_WORDS = {'WHEAT': ['breaded', 'battered', 'tenders', 'onion rings', 'breading', 'batter', 'wheat'],
               'SHELLFISH': ['shrimp', 'prawns', 'prawn', 'crab', 'lobster', 'crayfish', 'shellfish'],
               'FISH': ['fish', 'cod', 'catfish', 'salmon', 'tilapia', 'haddock']}


def _table():
    out = {}
    for cat, d in WORDS.items():
        for w in d['plain'] + d['hard'] + EXTRA.get(cat, []):
            out[w.lower()] = (cat,)
    for w, cats in AMBIGUOUS.items():
        out[w] = cats
    for w in NOT_ALLERGENS:
        out[w.lower()] = ()
    return out


LEXICON = _table()
_PHRASES = sorted(LEXICON, key=len, reverse=True)


def categories(text):
    """Categories named in a food phrase. Returns (set of categories, ambiguous: bool). Longest phrases match first,
    on word boundaries; an ambiguous word ("nuts", "seafood") matches only if nothing more specific does."""
    s = ' ' + re.sub(r'\s+', ' ', str(text).lower()).strip() + ' '
    found, ambiguous = set(), False
    taken = [False] * len(s)
    for p in _PHRASES:
        for m in re.finditer(r'(?<![a-z])' + re.escape(p) + r'(?![a-z])', s):
            if any(taken[m.start():m.end()]):
                continue
            for i in range(m.start(), m.end()):
                taken[i] = True
            cats = LEXICON[p]
            if p in AMBIGUOUS:
                ambiguous = True
            found |= set(cats)
    return found, ambiguous


def fryer_category(text):
    """The single fryer category named in a description of what shares the oil, or None if none or several."""
    s = str(text or '').lower()
    hits = {cat for cat, words in FRYER_WORDS.items() if any(re.search(r'(?<![a-z])' + re.escape(w) + r'(?![a-z])', s) for w in words)}
    return hits.pop() if len(hits) == 1 else None
