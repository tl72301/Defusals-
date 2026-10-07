"""Deterministic task lists for every ladder rung. A task is one package: the prompt the model sees, four options,
and the answer. Everything is generated from a fixed seed so every player gets the same tasks."""
import hashlib
import json
import random
from pathlib import Path
from defuse.depot.game import CONTENT_BINS, CONTENT_MEANING, PRECEDENCE, load_bank, BANK

HERE = Path(__file__).resolve().parent / 'bank'
NAMES = dict(CONTENT_BINS)
BINS_LINE = ('Bins: ' + '; '.join(f'{CONTENT_BINS[b]} = {CONTENT_MEANING[b]}' for b in CONTENT_BINS) + '. ' + PRECEDENCE)
CONTINENT_NAME = {'europe': 'Europe', 'asia': 'Asia', 'americas': 'the Americas', 'africa_oceania': 'Africa or Oceania'}
PER_RUNG = 40


def rng(*parts):
    return random.Random(int(hashlib.sha256(':'.join(map(str, parts)).encode()).hexdigest()[:16], 16))


def test_items():
    """The v2 test bank (in play items only): English contents and messy labels with known bins."""
    contents, messy, cities = load_bank('v2')
    return contents, messy, cities


def contents_prompt(label, header, extra=()):
    return '\n'.join([header, 'Rule: Sort each package by what is inside.', BINS_LINE, *extra, f'Package: "{label}".'])


def task(ladder, rung, label, answer, prompt, **meta):
    return {'id': f'{ladder}{rung}-{hashlib.sha256((prompt + answer).encode()).hexdigest()[:10]}', 'ladder': ladder,
            'rung': rung, 'label': label, 'answer': answer, 'prompt': prompt,
            'options': [{'id': b, 'description': n} for b, n in CONTENT_BINS.items()], **meta}


# ---- Ladder A: speed and throughput (v2 items) ----
DEADLINES = [1.5, 1.0, 0.75, 0.5]
BATCH_SIZES = [1, 10, 50, 200]


def ladder_a_items(n):
    contents, messy, _ = test_items()
    pool = contents + messy
    rng('A', 'items').shuffle(pool)
    return pool[:n]


def ladder_a_deadline_tasks():
    out = []
    for rung, deadline in enumerate(DEADLINES, 1):
        for item in ladder_a_items(60):
            header = f'Sorting depot gauntlet: speed, rung {rung} ({deadline} s).'
            out.append(task('A', rung, item['label'], item['bin'], contents_prompt(item['label'], header), deadline=deadline))
    return out


# ---- Ladder B: rule load (v2 contents items, natural-language rules) ----
B_RUNGS = [(1, 0), (5, 0), (10, 0), (20, 0), (10, 4)]   # (destination overrides, exceptions)
OVERRIDE_TEMPLATES = [
    'Anything bound for {city} goes in {bin}.',
    'Send packages addressed to {city} to {bin}.',
    '{city}-bound packages go to the {bin} bin.',
    'For deliveries to {city}, use {bin}.',
    'Route every shipment for {city} to {bin}.',
]
EXCEPTION_TEMPLATES = [
    'Exception: packages that would go to {kind} by their contents and are going anywhere in {region} go to {bin} instead.',
    'Exception: if a package belongs in {kind} by what is inside and is headed to {region}, put it in {bin}.',
]


def ladder_b_tasks():
    contents, _, cities = test_items()
    city_cont = {c: k for k, v in cities.items() for c in v}
    all_cities = sorted(city_cont)
    out = []
    for rung, (n_over, n_exc) in enumerate(B_RUNGS, 1):
        r = rng('B', rung)
        over_cities = r.sample(all_cities, n_over)
        overrides = {c: r.choice(list(CONTENT_BINS)) for c in over_cities}
        pairs = r.sample([(k, g) for k in CONTENT_BINS for g in CONTINENT_NAME], n_exc)   # distinct, so never contradictory
        exceptions = [(k, g, r.choice([b for b in CONTENT_BINS if b != k])) for k, g in pairs]
        rules = [r.choice(OVERRIDE_TEMPLATES).format(city=c, bin=NAMES[b]) for c, b in overrides.items()]
        rules += [r.choice(EXCEPTION_TEMPLATES).format(kind=NAMES[k], region=CONTINENT_NAME[g], bin=NAMES[t]) for k, g, t in exceptions]
        order = ('Order of rules: exceptions first, then the destination list, then what is inside.' if exceptions
                 else 'Destination rules override what is inside.')
        pool = contents[:]; r.shuffle(pool)
        others = [c for c in all_cities if c not in overrides]
        for k in range(PER_RUNG):
            item = pool[k]
            if k % 2 == 0 and over_cities:                         # half the packages go to a listed destination
                city = over_cities[k // 2 % len(over_cities)]
            elif exceptions and k % 4 == 1:                         # a quarter test the exceptions
                kind, region, _ = exceptions[k // 4 % len(exceptions)]
                item = next((i for i in pool[PER_RUNG:] if i['bin'] == kind and i['id'] not in {t['meta_id'] for t in out}), item)
                city = r.choice([c for c in others if city_cont[c] == region] or others)
            else:
                city = r.choice(others)
            answer, decided_by = resolve(item['bin'], city, city_cont[city], overrides, exceptions)
            header = f'Sorting depot gauntlet: rule load, rung {rung} ({n_over} destination rules, {n_exc} exceptions).'
            prompt = '\n'.join([header, 'Rules:', *[f'- {x}' for x in rules], order, BINS_LINE,
                                f'Package: "{item["label"]}", going to {city}.'])
            out.append(task('B', rung, item['label'], answer, prompt, destination=city, meta_id=item['id'], contents_bin=item['bin'], decided_by=decided_by,
                            rules={'overrides': overrides, 'exceptions': exceptions}))
    return out


def resolve(contents_bin, city, continent, overrides, exceptions):
    for kind, region, target in exceptions:
        if contents_bin == kind and continent == region:
            return target, 'exception'
    if city in overrides:
        return overrides[city], 'destination rule'
    return contents_bin, 'contents'


# ---- Ladder C: knowledge depth (separately written bank) ----
C_RUNGS = ['everyday', 'specialist', 'expert', 'misleading', 'compound']


def ladder_c_tasks():
    data = json.loads((HERE / 'knowledge.json').read_text())
    excluded = set(json.loads((HERE / 'excluded.json').read_text())['ids']) if (HERE / 'excluded.json').exists() else set()
    out = []
    for rung, name in enumerate(C_RUNGS, 1):
        for item in [i for i in data if i['rung'] == name and i['id'] not in excluded]:
            header = f'Sorting depot gauntlet: knowledge, rung {rung}.'
            out.append(task('C', rung, item['label'], item['bin'], contents_prompt(item['label'], header), item_id=item['id']))
    return out


# ---- Ladder D: messy input (programmatic noise on v2 English labels, plus a written transliteration rung) ----
D_RUNGS = ['light typos', 'heavy typos', 'scanner (OCR) errors', 'transliteration and mixed scripts', 'extreme']
OCR = {'rn': 'm', 'm': 'rn', 'l': '1', 'i': 'l', 'o': '0', 'e': 'c', 'a': 'o', 'h': 'b', 's': '5', 'cl': 'd', 'g': 'q', 'b': '6'}
LEET = {'a': '4', 'e': '3', 'i': '1', 'o': '0', 's': '$', 't': '7'}


def typo(word, r, edits):
    w = list(word)
    for _ in range(edits):
        if len(w) < 3:
            break
        i = r.randrange(1, len(w) - 1)
        op = r.choice(['drop', 'swap', 'double', 'replace'])
        if op == 'drop':
            del w[i]
        elif op == 'swap' and i + 1 < len(w):
            w[i], w[i + 1] = w[i + 1], w[i]
        elif op == 'double':
            w.insert(i, w[i])
        else:
            w[i] = r.choice('aeioubcdfghklmnprstvwy')
    return ''.join(w)


def ocr(text, r, rate):
    out, i = '', 0
    while i < len(text):
        two = text[i:i + 2]
        if two in OCR and r.random() < rate:
            out += OCR[two]; i += 2; continue
        ch = text[i]
        out += OCR[ch] if ch in OCR and r.random() < rate else ('' if ch == ' ' and r.random() < rate / 2 else ch)
        i += 1
    return out


def noisy(label, level, r):
    words = label.split()
    if level == 1:
        k = r.randrange(len(words)); words[k] = typo(words[k], r, 1); return ' '.join(words)
    if level == 2:
        return ' '.join(typo(w, r, 2) if len(w) > 3 else w for w in words)
    if level == 3:
        return ocr(label, r, 0.35)
    # extreme: OCR, leetspeak, upper case and truncation
    text = ocr(label, r, 0.3)
    text = ''.join(LEET.get(c, c) if r.random() < 0.4 else c for c in text).upper()
    return text[:max(6, int(len(text) * 0.75))] + '…'


def ladder_d_tasks():
    contents, _, _ = test_items()
    out = []
    written = json.loads((HERE / 'transliterated.json').read_text()) if (HERE / 'transliterated.json').exists() else []
    excluded = set(json.loads((HERE / 'excluded.json').read_text())['ids']) if (HERE / 'excluded.json').exists() else set()
    for rung, name in enumerate(D_RUNGS, 1):
        if rung == 4:
            items = [(i['label'], i['bin'], i['id']) for i in written if i['id'] not in excluded]
        else:
            r = rng('D', rung)
            pool = contents[:]; r.shuffle(pool)
            level = {1: 1, 2: 2, 3: 3, 5: 4}[rung]
            items = [(noisy(i['label'], level, r), i['bin'], i['id']) for i in pool[:PER_RUNG]]
        for label, answer, source in items:
            header = f'Sorting depot gauntlet: messy input, rung {rung}.'
            out.append(task('D', rung, label, answer, contents_prompt(label, header), source_id=source))
    return out


RUNG_NAMES = {'A': [f'{d} s deadline' for d in DEADLINES], 'B': [f'{o} rules' + (f' + {e} exceptions' if e else '') for o, e in B_RUNGS],
              'C': C_RUNGS, 'D': D_RUNGS}
LADDERS = {'A': ladder_a_deadline_tasks, 'B': ladder_b_tasks, 'C': ladder_c_tasks, 'D': ladder_d_tasks}
