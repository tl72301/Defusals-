"""Where allergies hide, and whose they are (ALLERGY_PROTOCOL.md §11). Plans for the third October 19 test.

144 short allergy notes ("clauses": 9 allergens x 4 subjects x 4 ways of saying it), each written once by blind authors
who see only what the note must say, never where it goes. Code then places every clause in seven places, once as this
order's allergy and once as another table's:

    ticket                 Server, ticket note for <table>    the clause alone (the table is only in the header)
    ticket_named           Server, ticket note for <table>    "<table>: clause"
    host                   Host stand                         "<table>: clause"
    host_reservation       Host stand                         "Reservation note for <table>: clause"
    manager                Manager on duty                    "<table>: clause"
    manager_reservation    Manager on duty                    "Reservation note for <table>: clause"
    kitchen                Kitchen chat                       "<table>: clause"

Each order (a dine-in table) has two messages: A, its own allergy (allergen X), and B, another table's allergy
(allergen Y, a different allergen, with at least one of the order's dishes containing Y but not X). Because the same
words appear in every place, places can be compared clause by clause. The plan, not the text, defines the answer key:
A is X = avoid; B is nothing for this order. Authors and reviewers stay blind (§5)."""
import json
import random
import re
from pathlib import Path
from defuse.allergy import rules, lexicon
from defuse.allergy.rules import ALLERGENS, MENU
from defuse.allergy.sim import Builder, blank

PLACES = ['ticket', 'ticket_named', 'host', 'host_reservation', 'manager', 'manager_reservation', 'kitchen']
SOURCE = {'ticket': 'SERVER', 'ticket_named': 'SERVER', 'host': 'HOST', 'host_reservation': 'HOST',
          'manager': 'MANAGER', 'manager_reservation': 'MANAGER', 'kitchen': 'KITCHEN'}
SUBJECTS = ['the kid', 'the guest', 'one of the guests', 'someone in the party']
FORMS = ['is allergic to {w}', "can't have any {w}", 'must avoid {w}', 'has {a} {w} allergy']
SINGULAR = {'peanuts': 'peanut', 'tree nuts': 'tree nut', 'eggs': 'egg'}
SPECIAL = {'lactose', 'celiac'}                  # need their own phrasing ("lactose intolerant"), so not used here
TEST_SEEDS = list(range(4001, 4001 + 144 * len(PLACES)))
DEV_SEEDS = list(range(3901, 3901 + len(PLACES)))
DEV_CLAUSES = [('TREE_NUT', 'the guest', 0, 'cashews'), ('FISH', 'someone in the party', 2, 'fish'),
               ('EGG', 'the kid', 3, 'eggs'), ('SESAME', 'one of the guests', 1, 'tahini')]
GUIDE = ('Write one short note, the way restaurant staff jot an allergy down during dinner service, that says exactly '
         'what "must_convey" says and nothing else. Keep the subject (e.g. "the kid") and use the food word given, '
         'exactly as written. You may phrase the allergy your own way (e.g. "needs to avoid" for "must avoid") and add '
         'a few words such as "please flag it" or "be careful", but add no other food, person, symptom or severity. '
         'Start with a lowercase letter and end with a full stop. Do NOT name or number any table, order, ticket, room, '
         'time, staff role or place, and do not say "this table", "this order", "here", "tonight" or similar: code puts '
         'each note in several places, with or without a prefix such as "Table 7: " in front, so it must read '
         'naturally both on its own and after such a prefix.')


def phrase(form, word):
    w = SINGULAR.get(word, word) if '{a}' in form else word
    return form.format(w=w, a='an' if w[0] in 'aeiou' else 'a'), w


def valid_pair(x, y):
    """Another table's allergen y fits an order with allergen x when some dish has y but not x (fries oil: wheat)."""
    oil = rules.FRYER_DEFAULT
    return x != y and any(y in rules.dish_allergens(d, oil) and x not in rules.dish_allergens(d, oil) for d in MENU)


def clauses(split='where_test'):
    """The clause plans. Test: per allergen, the 16 subject x form pairs; the "has a ... allergy" form always takes a
    plain word (category name), and 4 of the other 12 take plain words too, so half the clauses use a plain word and
    half a harder one. Words are drawn from lexicon.WORDS by a fixed shuffle."""
    out = []
    if split == 'where_dev':
        for i, (x, subj, f, word) in enumerate(DEV_CLAUSES):
            text, w = phrase(FORMS[f], word)
            out.append({'id': f'D{i + 1}', 'allergen': x, 'subject': subj, 'form': FORMS[f], 'word': w,
                        'word_type': 'plain' if word in lexicon.WORDS[x]['plain'] else 'hard',
                        'must_convey': f'{subj} {text} (use the words "{subj}" and "{w}")'})
        return out
    for x in ALLERGENS:
        r = random.Random(f'where-clauses:{x}')
        plain = list(lexicon.WORDS[x]['plain'])
        hard = [w for w in lexicon.WORDS[x]['hard'] if w not in SPECIAL]
        others = [(s, f) for f in range(3) for s in SUBJECTS]
        r.shuffle(others)
        plain_pairs = set(others[:4]) | {(s, 3) for s in SUBJECTS}
        r.shuffle(hard)
        hard_words = (hard * 8)[:8]
        for f in range(4):
            for s in SUBJECTS:
                if (s, f) in plain_pairs:
                    word, kind = plain[(SUBJECTS.index(s) + f) % len(plain)], 'plain'
                else:
                    word, kind = hard_words.pop(), 'hard'
                text, w = phrase(FORMS[f], word)
                out.append({'allergen': x, 'subject': s, 'form': FORMS[f], 'word': w, 'word_type': kind,
                            'must_convey': f'{s} {text} (use the words "{s}" and "{w}")'})
    for i, c in enumerate(out):
        c['id'] = f'C{i + 1:03d}'
    return out


def pairing(cs):
    """B clause for each A clause: a perfect matching (every clause used once as B) in which every pair is valid,
    found by augmenting paths over a fixed shuffle."""
    r = random.Random('where-pairs')
    adj = []
    for a in cs:
        nbrs = [j for j, b in enumerate(cs) if valid_pair(a['allergen'], b['allergen'])]
        r.shuffle(nbrs)
        adj.append(nbrs)
    match = {}                                     # B index -> A index

    def augment(i, seen):
        for j in adj[i]:
            if j in seen:
                continue
            seen.add(j)
            if j not in match or augment(match[j], seen):
                match[j] = i
                return True
        return False
    for i in range(len(cs)):
        if not augment(i, set()):
            raise ValueError('no valid pairing')
    return {i: j for j, i in match.items()}


def cells(split):
    """seed -> (A clause, A place, B clause, B place). Test: every clause in every place once as A; its B clause is
    the matched one, placed (A place + an offset fixed per clause) mod 7, so every clause is also in every place once
    as B. Dev: 7 orders, one per A place, cycling the 4 dev clauses."""
    cs = clauses(split)
    if split == 'where_dev':
        return {s: (cs[i % 4]['id'], PLACES[i], cs[(i + 1) % 4]['id'], PLACES[(i + 3) % 7])
                for i, s in enumerate(DEV_SEEDS)}
    pair = pairing(cs)
    offs = [i % len(PLACES) for i in range(len(cs))]
    random.Random('where-offsets').shuffle(offs)
    todo = [(i, p) for i in range(len(cs)) for p in range(len(PLACES))]
    random.Random('where-orders').shuffle(todo)
    return {s: (cs[i]['id'], PLACES[p], cs[pair[i]]['id'], PLACES[(p + offs[i]) % len(PLACES)])
            for s, (i, p) in zip(TEST_SEEDS, todo)}


def pick_dishes(r, x, y):
    """1 or 2 dishes with x, 1 with y but not x, and the rest (to 3 or 4 dishes) with neither."""
    oil = rules.FRYER_DEFAULT
    has = {d: rules.dish_allergens(d, oil) for d in MENU}
    with_x = [d for d in MENU if x in has[d]]
    y_only = [d for d in MENU if y in has[d] and x not in has[d]]
    neither = [d for d in MENU if x not in has[d] and y not in has[d]]
    n = r.choice([3, 4])
    chosen = r.sample(with_x, min(len(with_x), r.choice([1, 2]))) + [r.choice(y_only)]
    return chosen + r.sample(neither, n - len(chosen))


BANNED = re.compile(r"\b(tables?|tickets?|orders?|tonight|here|reservations?|res|host|manager|kitchen|server|chef|"
                    r"booking|booked)\b", re.I)


def check_clause(c, text):
    """What is wrong with an author's clause (§11.4), or [] if nothing: the subject and food word are there; no digits,
    no table, order, place, role or time words; no other allergen; one short sentence ending in a full stop."""
    low = text.lower()
    out = []
    if c['subject'] not in low:
        out.append(f'subject "{c["subject"]}" missing')
    if not re.search(r'(?<![a-z])' + re.escape(c['word'].lower()) + r'(?![a-z])', low):
        out.append(f'food word "{c["word"]}" missing')
    if re.search(r'\d', text):
        out.append('has a digit')
    if BANNED.search(text):
        out.append(f'names a table, order, place, role or time ("{BANNED.search(text).group(0)}")')
    cats, ambiguous = lexicon.categories(text)
    if cats - {c['allergen']} or ambiguous:
        out.append(f'names another allergen {sorted(cats - {c["allergen"]})}')
    if not text.rstrip().endswith('.') or len(text) > 140 or text.count('.') > 2:
        out.append('not one short sentence ending in a full stop')
    return out


def compose(place, table, clause):
    """The message text code builds from a clause written by an author."""
    if place == 'ticket':
        return clause[0].upper() + clause[1:]
    lead = clause[0].lower() + clause[1:]
    if place.endswith('_reservation'):
        return f'Reservation note for {table}: {lead}'
    return f'{table}: {lead}'


def scenario(seed, split, a_clause, a_place, b_clause, b_place):
    r = random.Random(f'where:{seed}')
    target = f'Table {r.randint(3, 28)}'
    other = f'Table {r.choice([n for n in range(3, 29) if f"Table {n}" != target])}'
    start = (r.randint(17, 19), r.choice([0, 10, 20, 30, 40, 50]))
    by_id = {c['id']: c for c in clauses(split)}
    ca, cb = by_id[a_clause], by_id[b_clause]
    x, y = ca['allergen'], cb['allergen']
    b = Builder(seed, r, target, False, hard=ca['word_type'] == 'hard')
    for role, c, place, table in (('A', ca, a_place, target), ('B', cb, b_place, other)):
        ans = blank()
        if role == 'A':
            ans[x] = 'avoid'
        src = SOURCE[place]
        label = b.label(src, table) if src == 'SERVER' else b.label(src)
        b.add(r.randint(1, 15), src, label, ans, [f'{role} ({place}, {table}): {c["must_convey"]}'],
              [role, place, c['word_type']], {x: 'avoid'} if role == 'A' else {})
        b.messages[-1].update(clause=c['id'], place=place, table=table, role=role)
    msgs = sorted(b.messages, key=lambda m: (m['minute'], m['role']))
    for i, m in enumerate(msgs):
        m['id'] = f'W{seed}-{i + 1:02d}'
    a_minute = next(m['minute'] for m in msgs if m['role'] == 'A')
    return {'id': f'W{seed}', 'seed': seed, 'split': split, 'hard': b.hard, 'profile': a_place, 'start': list(start),
            'target': target, 'other': other, 'delivery': False, 'dishes': pick_dishes(r, x, y), 'allergen': x,
            'other_allergen': y, 'a_clause': a_clause, 'a_place': a_place, 'b_clause': b_clause, 'b_place': b_place,
            'restricted': {x: a_minute}, 'fryer_events': [], 'traps': [a_place, f'other:{b_place}'], 'messages': msgs}


def plans(split):
    return [scenario(s, split, *cell) for s, cell in sorted(cells(split).items())]


def authoring_packet(split, path):
    """What clause authors see: the guide and, per clause, its id and must_convey line. Nothing about places, tables
    or orders."""
    items = [{'id': c['id'], 'must_convey': c['must_convey']} for c in clauses(split)]
    Path(path).write_text(json.dumps({'guide': GUIDE, 'clauses': items}, indent=1, ensure_ascii=False))
    return len(items)


def compose_texts(split, files, bank_dir):
    """Merge authors' clause files ([{id, text}]) and write every message's composed text to {split}_texts.json."""
    texts = {}
    for f in files:
        for item in json.loads(Path(f).read_text()):
            texts[item['id']] = item['text'].strip()
    ids = {c['id'] for c in clauses(split)}
    if set(texts) != ids:
        raise ValueError(f'clauses missing {sorted(ids - set(texts))[:5]} or unknown {sorted(set(texts) - ids)[:5]}')
    bad = {c['id']: check_clause(c, texts[c['id']]) for c in clauses(split) if check_clause(c, texts[c['id']])}
    if bad:
        raise ValueError(f'clauses that fail the check (§11.4): {bad}')
    (Path(bank_dir) / f'{split}_clauses.json').write_text(json.dumps(texts, indent=1, ensure_ascii=False))
    out = {m['id']: compose(m['place'], m['table'], texts[m['clause']])
           for sc in json.loads((Path(bank_dir) / f'{split}.json').read_text()) for m in sc['messages']}
    (Path(bank_dir) / f'{split}_texts.json').write_text(json.dumps(out, indent=1, ensure_ascii=False))
    return out
