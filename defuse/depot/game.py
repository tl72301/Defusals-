"""Sorting Depot: one package at a time, four bins, five short rounds. Deterministic from a seed."""
import hashlib
import json
import random
from pathlib import Path

BANK = Path(__file__).resolve().parent / 'bank'
CONTENT_BINS = {'cold': 'Cold', 'hazardous': 'Hazardous', 'fragile': 'Fragile', 'other': 'Everything else'}
CONTENT_MEANING = {'cold': 'food or medicine that must be kept refrigerated or frozen',
                   'hazardous': 'flammable, explosive, toxic, corrosive, pressurized, or a lithium battery',
                   'fragile': 'glass, ceramic, porcelain, crystal or anything else that breaks easily',
                   'other': 'sturdy, safe items that need no refrigeration'}
CONTINENT_BINS = {'europe': 'Europe', 'asia': 'Asia', 'americas': 'Americas', 'africa_oceania': 'Africa & Oceania'}
BIN_NAMES = {**CONTENT_BINS, **CONTINENT_BINS}
PER_ROUND = 20
SWITCH_AT = 10          # round 4 changes its rule after this many packages
RECENT = 6              # round 5 shows this many recent packages
DEADLINES = {'realtime': 1.5, 'paused': 10.0}   # seconds per package: the belt in realtime; effectively no limit when paused
PRECEDENCE = ('If more than one bin could apply, use the first that fits in this order: Hazardous, Cold, Fragile, '
              'Everything else.')
ROUNDS = [
    ('know', 'Know it', 'Sort each package by what is inside.'),
    ('read', 'Read it', 'Labels may be misspelled, abbreviated or in another language. Sort by what is inside.'),
    ('list', 'Check the list', 'Packages going to a destination on the manifest go to the bin the manifest names, '
                               'whatever is inside. Sort all other packages by what is inside.'),
    ('switch', 'New rule', 'Sort each package by what is inside. Partway through the round the rule changes; '
                           'always follow the rule shown now.'),
    ('remember', 'Read the recent list', 'Sort each package by what is inside. A smudged label that says "same bin as the '
                             'last package from <city>" goes wherever that package went: look it up in the recent list.'),
]
SWITCH_RULE = 'New rule: sort each package by the continent of its destination, whatever is inside.'
INSTRUCTIONS = 'Which bin does this package go into?'


def bank_dir(bank='v1'):
    if bank not in ('v1', 'v2'):
        raise ValueError('bank must be v1 (development) or v2 (test)')
    return BANK if bank == 'v1' else BANK / 'v2'


def load_bank(bank='v1'):
    folder = bank_dir(bank)
    contents = json.loads((folder / 'contents.json').read_text())
    messy = json.loads((folder / 'messy.json').read_text())
    cities = json.loads((BANK / 'cities.json').read_text())   # one shared gazetteer
    return contents, messy, cities


def heldout(item_id):
    """A fixed 20% of items, reported separately (never used to design the baselines)."""
    return int(hashlib.sha256(item_id.encode()).hexdigest(), 16) % 5 == 0


def explanation(pkg):
    name = BIN_NAMES[pkg['bin']]
    if pkg['rule'] == 'manifest':
        return f'The manifest sends packages for {pkg["destination"]} to {name}.'
    if pkg['rule'] == 'continent':
        return f'{pkg["destination"]} is in {name}.'
    if pkg['rule'] == 'memory':
        return f'The last package from {pkg["ref_city"]} went to {name}.'
    if pkg.get('meaning'):
        return f'"{pkg["label"]}" means {pkg["meaning"]}: {name}.'
    return f'{pkg["label"][0].upper() + pkg["label"][1:]}: {pkg["why"]}, so {name}.'


class Depot:
    def __init__(self, seed, rounds=None, bank='v1'):
        self.seed, self.bank = seed, bank
        r = random.Random(f'depot:{seed}')
        contents, messy, cities = load_bank(bank)
        self.city_continent = {c: k for k, v in cities.items() for c in v}
        all_cities = sorted(self.city_continent)
        pool = contents[:]; r.shuffle(pool)
        take = iter(pool)
        by_bin = {b: [i for i in pool if i['bin'] == b] for b in CONTENT_BINS}
        used = set()

        def fresh(item=None):
            if item is None:
                item = next(i for i in take if i['id'] not in used)
            used.add(item['id'])
            return item

        def content_pkg(item, rnd, **extra):
            return {'round': rnd, 'rule': 'contents', 'label': item['label'], 'bin': item['bin'], 'why': item.get('why'),
                    'meaning': item.get('meaning'), 'item_id': item['id'], 'heldout': heldout(item['id']), **extra}

        self.manifest = {}
        packages = []
        # 1. Know it
        packages += [content_pkg(fresh(), 'know') for _ in range(PER_ROUND)]
        # 2. Read it
        packages += [content_pkg(m, 'read') for m in r.sample(messy, PER_ROUND)]
        # 3. Check the list: 4 manifest destinations; 8 packages go there, with contents that point elsewhere.
        manifest_cities = r.sample(all_cities, 4)
        self.manifest = {c: r.choice(list(CONTENT_BINS)) for c in manifest_cities}
        others = [c for c in all_cities if c not in self.manifest]
        listed = []
        for k in range(PER_ROUND):
            if k < 8:
                city = manifest_cities[k % 4]
                item = next(i for i in by_bin[r.choice([b for b in CONTENT_BINS if b != self.manifest[city]])] if i['id'] not in used)
                pkg = content_pkg(fresh(item), 'list', destination=city)
                pkg.update(rule='manifest', bin=self.manifest[city])
            else:
                pkg = content_pkg(fresh(), 'list', destination=r.choice(others))
            listed.append(pkg)
        r.shuffle(listed); packages += listed
        # 4. New rule: by contents, then by destination continent.
        for k in range(PER_ROUND):
            city = r.choice(all_cities)
            pkg = content_pkg(fresh(), 'switch', destination=city)
            if k >= SWITCH_AT:
                pkg.update(rule='continent', bin=self.city_continent[city])
            packages.append(pkg)
        # 5. Remember: origins; 8 smudged labels refer to a recent package with a unique origin in the window.
        remember = []
        smudged = set(r.sample(range(4, PER_ROUND), 8))
        for k in range(PER_ROUND):
            origin = r.choice(all_cities)
            window = remember[-RECENT:]
            unique = [p for p in window if sum(q['origin'] == p['origin'] for q in window) == 1]
            if k in smudged and unique:
                ref = r.choice(unique)
                pkg = {'round': 'remember', 'rule': 'memory', 'label': f'smudged label: same bin as the last package from {ref["origin"]}',
                       'bin': ref['bin'], 'ref_city': ref['origin'], 'origin': origin, 'item_id': None, 'heldout': False,
                       'why': None, 'meaning': None}
            else:
                pkg = content_pkg(fresh(), 'remember', origin=origin)
            remember.append(pkg)
        packages += remember
        keep = set(rounds or [x[0] for x in ROUNDS])
        self.packages = [p for p in packages if p['round'] in keep]
        for i, p in enumerate(self.packages):
            p['index'] = i
            p['number'] = sum(q['round'] == p['round'] for q in self.packages[:i]) + 1
            p['explanation'] = explanation(p)

    def round_info(self, pkg):
        n = [x[0] for x in ROUNDS].index(pkg['round'])
        return n + 1, ROUNDS[n][1], ROUNDS[n][2]

    def bins(self, pkg):
        return CONTINENT_BINS if pkg['rule'] == 'continent' else CONTENT_BINS

    def recent(self, pkg):
        if pkg['round'] != 'remember':
            return []
        before = [p for p in self.packages if p['round'] == 'remember' and p['index'] < pkg['index']]
        return before[-RECENT:]

    def prompt(self, pkg):
        """The only thing the model sees: plain text."""
        n, title, rule = self.round_info(pkg)
        lines = [f'Sorting depot, round {n} of 5: {title}.', f'Rule: {rule}']
        if pkg['rule'] == 'continent' or (pkg['round'] == 'switch' and pkg['number'] > SWITCH_AT):
            lines.append(SWITCH_RULE)
        bins = self.bins(pkg)
        if bins is CONTENT_BINS:
            lines.append('Bins: ' + '; '.join(f'{CONTENT_BINS[b]} = {CONTENT_MEANING[b]}' for b in CONTENT_BINS)
                         + '. ' + PRECEDENCE)
        else:
            lines.append('Bins: ' + ', '.join(CONTINENT_BINS.values()) + '.')
        if pkg['round'] == 'list':
            lines.append('Manifest: ' + '; '.join(f'packages for {c} go to {CONTENT_BINS[b]}' for c, b in self.manifest.items()) + '.')
        recent = self.recent(pkg)
        if recent:
            lines.append('Recent packages, oldest first: ' + '; '.join(
                f'"{p["label"]}" from {p["origin"]} went to {BIN_NAMES[p["bin"]]}' for p in recent) + '.')
        where = (f', going to {pkg["destination"]}' if pkg.get('destination') else '') + \
                (f', from {pkg["origin"]}' if pkg.get('origin') else '')
        lines.append(f'Package {pkg["number"]} of {PER_ROUND}: "{pkg["label"]}"{where}.')
        return '\n'.join(lines)

    def options(self, pkg):
        return [{'id': b, 'description': name} for b, name in self.bins(pkg).items()]
