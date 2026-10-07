"""Frozen baselines for the Depot Gauntlet. Committed before any Gauntlet item was written (see FROZEN_BEFORE).

Every code player reads only the prompt text, plus the shared city gazetteer:
- keyword, dictionary: the frozen Sorting Depot programs (defuse/depot/baselines.py), unchanged.
- classifier: a trained multilingual model. Each label is embedded with paraphrase-multilingual-MiniLM-L12-v2
  and a logistic regression picks the bin. It was trained on the v1 development bank only (labels and bins);
  its regularization was chosen by 5-fold cross-validation on v1. The weights are stored in
  bank/classifier.json, so the trained model is fixed in git.
- random: uniform over the four bins (seeded by the prompt).

All code players get the same perfect rule parser for Ladder B (rules), written against the exact rule
templates in tasks.py: a code player's only possible errors there are about what is inside a package."""
import hashlib
import json
import random
import re
from pathlib import Path
from defuse.depot import baselines as depot
from defuse.depot.game import BANK, CONTENT_BINS, load_bank

FROZEN_BEFORE = 'gauntlet/bank'          # no knowledge.json or transliterated.json existed when this was committed
MODEL = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
WEIGHTS = Path(__file__).resolve().parent / 'bank' / 'classifier.json'
NAME_TO_BIN = {v: k for k, v in CONTENT_BINS.items()}
BIN_NAME = '|'.join(re.escape(v) for v in CONTENT_BINS.values())
REGION = {'Europe': 'europe', 'Asia': 'asia', 'the Americas': 'americas', 'Africa or Oceania': 'africa_oceania'}
CITY = {c: k for k, v in json.loads((BANK / 'cities.json').read_text()).items() for c in v}

OVERRIDE = [rf'^- Anything bound for (.+) goes in ({BIN_NAME})\.$', rf'^- Send packages addressed to (.+) to ({BIN_NAME})\.$',
            rf'^- (.+)-bound packages go to the ({BIN_NAME}) bin\.$', rf'^- For deliveries to (.+), use ({BIN_NAME})\.$',
            rf'^- Route every shipment for (.+) to ({BIN_NAME})\.$']
EXCEPTION = [rf'^- Exception: packages that would go to ({BIN_NAME}) by their contents and are going anywhere in (.+) go to ({BIN_NAME}) instead\.$',
             rf'^- Exception: if a package belongs in ({BIN_NAME}) by what is inside and is headed to (.+), put it in ({BIN_NAME})\.$']


def label(prompt):
    return re.search(r'Package: "(.*)"', prompt.splitlines()[-1]).group(1)


def parse_rules(prompt):
    overrides, exceptions = {}, []
    for line in prompt.splitlines():
        for pat in OVERRIDE:
            m = re.match(pat, line)
            if m:
                overrides[m.group(1)] = NAME_TO_BIN[m.group(2)]
        for pat in EXCEPTION:
            m = re.match(pat, line)
            if m:
                exceptions.append((NAME_TO_BIN[m.group(1)], REGION[m.group(2)], NAME_TO_BIN[m.group(3)]))
    return overrides, exceptions


def with_rules(contents):
    """Wrap a contents sorter with the perfect rule parser: exceptions, then destination rules, then contents."""
    def play(prompt):
        guess = contents(prompt)
        dest = re.search(r', going to (.+)\.$', prompt.splitlines()[-1])
        if not dest:
            return guess
        city = dest.group(1)
        overrides, exceptions = parse_rules(prompt)
        for kind, region, target in exceptions:
            if guess == kind and CITY.get(city) == region:
                return target
        return overrides.get(city, guess)
    play.__name__ = contents.__name__
    return play


_model = None


def embed(texts):
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL, device='cpu')
    return _model.encode(list(texts), batch_size=64, normalize_embeddings=True)


def training_set():
    contents, messy, _ = load_bank('v1')
    items = contents + messy
    return [i['label'] for i in items], [i['bin'] for i in items]


def train():
    """Fit on v1 only. Picks C by 5-fold cross-validation on v1, refits on all of v1, writes bank/classifier.json."""
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import StratifiedKFold, cross_val_score
    texts, bins = training_set()
    X, y = embed(texts), np.array(bins)
    folds = StratifiedKFold(5, shuffle=True, random_state=0)
    cv = {c: float(cross_val_score(LogisticRegression(C=c, max_iter=5000), X, y, cv=folds).mean())
          for c in (0.1, 0.3, 1, 3, 10, 30, 100)}
    best = max(cv, key=cv.get)
    fit = LogisticRegression(C=best, max_iter=5000).fit(X, y)
    WEIGHTS.write_text(json.dumps({
        'model': MODEL, 'trained_on': 'bank v1 (development) contents and messy labels', 'examples': len(texts),
        'training_sha256': hashlib.sha256(json.dumps([texts, bins]).encode()).hexdigest(),
        'cross_validation_accuracy_by_C': cv, 'C': best, 'classes': fit.classes_.tolist(),
        'coef': np.round(fit.coef_, 6).tolist(), 'intercept': np.round(fit.intercept_, 6).tolist()}, indent=1) + '\n')
    return best, cv


_weights = None


def classify(labels):
    import numpy as np
    global _weights
    if _weights is None:
        w = json.loads(WEIGHTS.read_text())
        _weights = (np.array(w['coef']), np.array(w['intercept']), w['classes'])
    coef, intercept, classes = _weights
    scores = embed(labels) @ coef.T + intercept
    return [classes[i] for i in scores.argmax(1)]


def classifier_contents(prompt):
    return classify([label(prompt)])[0]


def random_contents(prompt):
    return random.Random(prompt).choice(list(CONTENT_BINS))


def keyword_contents(prompt):
    return depot.keyword(prompt)


def dictionary_contents(prompt):
    return depot.dictionary(prompt)


classifier_contents.__name__, random_contents.__name__ = 'classifier', 'random'
keyword_contents.__name__, dictionary_contents.__name__ = 'keyword', 'dictionary'
CONTROLLERS = {f.__name__: with_rules(f) for f in (keyword_contents, dictionary_contents, classifier_contents, random_contents)}


def play_all(name, prompts):
    """Answer many prompts at once (the classifier embeds in one batch)."""
    if name != 'classifier':
        return [CONTROLLERS[name](p) for p in prompts]
    guesses = iter(classify([label(p) for p in prompts]))
    cache = {p: next(guesses) for p in prompts}
    contents = lambda p: cache[p]
    contents.__name__ = 'classifier'
    return [with_rules(contents)(p) for p in prompts]


if __name__ == '__main__':
    print(train())
