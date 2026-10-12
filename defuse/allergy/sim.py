"""Scenario generator: the hidden truth (who must avoid what, and what is in the fries oil when), the ticket, message
plans (what each message must say, how, and with which trap), the answer key derived from each plan, templated
clarification answers, and the true dish decisions used for diagnostics only.

Messages' free text is written later by separate author agents from the plans' "spec" lines. The plan, not the text,
defines the correct answers; blind reviewers check that the text conveys exactly the plan (ALLERGY_PROTOCOL.md §5)."""
import random
from defuse.allergy import rules, lexicon
from defuse.allergy.rules import ALLERGENS, NAME, MENU, MINUTES, clock

PROFILES = ['nut', 'dairy', 'gluten', 'seafood', 'multi', 'none']
RELATIONS = ['sister', 'brother', 'friend', 'cousin', 'roommate', 'coworker', 'aunt', 'neighbor']
CHATTER = ['routine kitchen chatter with no allergy or fryer information: firing two burgers for {other}',
           'routine kitchen chatter with no allergy or fryer information: {other} is waiting on their desserts',
           'routine kitchen chatter with no allergy or fryer information: we are out of the mango sorbet tonight',
           'routine kitchen chatter with no allergy or fryer information: the grill station is backed up about five minutes',
           'routine kitchen chatter with no allergy or fryer information: plates for {other} are up at the pass',
           'routine kitchen chatter with no allergy or fryer information: someone restock the to-go boxes']


def blank():
    a = {x: 'not_mentioned' for x in ALLERGENS}
    a['FRYER'] = 'not_mentioned'
    a['CORRECTION'] = 'no'
    return a


def plural(word):
    return word.endswith('s') or word in ('dairy', 'milk', 'gluten', 'wheat', 'soy', 'sesame', 'fish', 'shellfish',
                                          'shrimp', 'lactose', 'ghee', 'whey', 'butter', 'cream', 'feta', 'mayo',
                                          'aioli', 'meringue', 'celiac', 'spelt', 'semolina', 'durum', 'farro', 'tofu',
                                          'edamame', 'miso', 'soy sauce', 'tempeh', 'tahini', 'sesame oil', 'salmon',
                                          'cod', 'tuna', 'fish sauce', 'crab', 'lobster', 'goat cheese', 'peanut butter',
                                          'peanut sauce', 'crayfish')


def be(word):
    return 'are' if word.endswith('s') and word not in ('lactose',) else 'is'


def avoid_line(subj, word, r):
    if word == 'lactose':
        return f'{subj} is lactose intolerant (say "lactose intolerant")'
    if word == 'celiac':
        return f'{subj} has celiac disease (use the word "celiac")'
    if word == 'gluten':
        return f'{subj} needs everything gluten-free (use the word "gluten")'
    form = r.choice(['is allergic to {w}', "can't have any {w}", 'must avoid {w}', 'has a {w} allergy'])
    if form == 'has a {w} allergy' and word.endswith('s') and word not in ('peanuts', 'tree nuts'):
        form = 'is allergic to {w}'
    return f'{subj} {form.format(w=word)} (use the word "{word}")'


def ok_line(subj_for, word):
    return f'{word} {be(word)} fine for {subj_for} (use the word "{word}"; say it plainly)'


class Builder:
    def __init__(self, seed, r, target, delivery, hard):
        self.seed, self.r, self.target, self.delivery, self.hard = seed, r, target, delivery, hard
        self.messages = []

    def word(self, allergen, plain_only=False):
        d = lexicon.WORDS[allergen]
        if self.hard and not plain_only and self.r.random() < 0.65:
            return self.r.choice(d['hard'])
        return self.r.choice(d['plain'])

    def subject(self):
        if self.delivery:
            return self.r.choice(['the customer', 'someone eating this order', 'one person on this order'])
        t = self.target
        return self.r.choice([f'the guest at {t}', f'one of the guests at {t}', f'someone at {t}', f'the kid at {t}'])

    def add(self, minute, source, label, answers, spec, tags, true=None):
        self.messages.append({'minute': minute, 'source': source, 'label': label, 'answers': answers, 'spec': spec,
                              'tags': sorted(set(tags)), 'true': true or {}})

    def label(self, source, about=None):
        about = about or self.target
        if source == 'SERVER':
            return f'Server, ticket note for {about}'
        if source == 'APP':
            return f'Delivery app, order note for {about}'
        if source == 'GUEST':
            return f'Customer, app chat for {about}' if self.delivery else f'Guest at {about}, text to the restaurant'
        return {'KITCHEN': 'Kitchen chat', 'HOST': 'Host stand', 'MANAGER': 'Manager on duty'}[source]


def other_labels(r, target, delivery, n):
    out = set()
    while len(out) < n:
        out.add(f'order #{r.randint(4100, 4899)}' if delivery and r.random() < 0.5 else f'Table {r.randint(3, 28)}')
        out.discard(target.replace('delivery ', ''))
        out.discard(target)
    return sorted(out)


def pick_dishes(r, restricted, profile):
    dishes = list(MENU)
    oil = rules.FRYER_DEFAULT
    conflict = [d for d in dishes if rules.dish_allergens(d, oil) & set(restricted)]
    safe = [d for d in dishes if not rules.dish_allergens(d, oil) & set(restricted)]
    n = 3 if r.random() < 0.3 else 4
    chosen = []
    if restricted and conflict:
        chosen += r.sample(conflict, min(len(conflict), r.choice([1, 2])))
    fries = [d for d in dishes if MENU[d][1] and d not in chosen]
    if r.random() < 0.75 and not any(MENU[d][1] for d in chosen):
        chosen.append(r.choice(fries))
    pool = [d for d in (safe if restricted else dishes) if d not in chosen]
    while len(chosen) < n and pool:
        d = r.choice(pool); pool.remove(d); chosen.append(d)
    return chosen


def scenario(seed, split, hard=False):
    r = random.Random(f'allergy:{seed}')
    profile = PROFILES[seed % len(PROFILES)]
    delivery = r.random() < 0.3
    target = f'delivery order #{r.randint(4100, 4899)}' if delivery else f'Table {r.randint(3, 28)}'
    start = (r.randint(17, 19), r.choice([0, 10, 20, 30, 40, 50]))
    others = other_labels(r, target, delivery, 4)
    b = Builder(seed, r, target, delivery, hard)

    base = {'nut': r.choice([['TREE_NUT'], ['PEANUT'], ['PEANUT', 'TREE_NUT']]),
            'dairy': ['MILK'] + (['EGG'] if r.random() < 0.3 else []),
            'gluten': ['WHEAT'],
            'seafood': r.choice([['SHELLFISH'], ['FISH'], ['SHELLFISH', 'FISH']]),
            'multi': r.sample(['MILK', 'EGG', 'SOY', 'SESAME', 'PEANUT', 'TREE_NUT', 'FISH'], 2),
            'none': []}[profile]
    restricted = {a: 0 for a in base}                  # allergen -> minute from which it truly applies
    late = None
    if profile == 'multi' or (profile not in ('none',) and r.random() < 0.25):
        options = [a for a in ['SESAME', 'SOY', 'EGG', 'MILK', 'SHELLFISH', 'WHEAT'] if a not in restricted]
        late = (r.choice(options), r.randint(15, 40))
        restricted[late[0]] = late[1]
    dishes = pick_dishes(r, list(restricted), profile)

    # Fryer truth: the fries oil starts with the breaded tenders (menu default); kitchen events change it.
    fryer_events = []
    if r.random() < (0.8 if profile in ('seafood', 'gluten') else 0.45):
        m1 = r.randint(8, 32)
        kind = r.choice(['shellfish', 'fish', 'fresh']) if profile != 'gluten' else r.choice(['fresh', 'fresh', 'shellfish'])
        fryer_events.append((m1, kind))
        if r.random() < 0.4:
            fryer_events.append((r.randint(m1 + 8, 52), 'fresh' if kind != 'fresh' else r.choice(['shellfish', 'fish', 'wheat'])))

    traps = ['correction', 'false_assurance', 'scope', 'other_table_same', 'fryer_unclear']
    if profile in ('nut', 'seafood'):
        traps.append('vague')
    if hard and base:
        traps.append('self_correct')
    if not base:
        traps = [t for t in traps if t not in ('false_assurance', 'other_table_same')]
    chosen_traps = r.sample(traps, min(len(traps), 3 if hard else 2))
    if profile in ('nut', 'seafood') and 'vague' not in chosen_traps and r.random() < 0.5:
        chosen_traps[0] = 'vague'

    # 1. The order (minute 0) states the base restrictions.
    src = 'APP' if delivery else 'SERVER'
    ans, spec, tags, true = blank(), [], ['order'], {}
    spec.append(f'{target} has just placed their order (do not name the dishes)')
    vague_cat = None
    if 'vague' in chosen_traps:
        vague_cat = ('nuts', ('PEANUT', 'TREE_NUT')) if profile == 'nut' else ('seafood', ('FISH', 'SHELLFISH'))
    for a in base:
        if vague_cat and a in vague_cat[1]:
            continue
        w = b.word(a)
        ans[a] = 'avoid'; true[a] = 'avoid'
        spec.append(avoid_line(b.subject(), w, r)); tags.append('hard_word' if w not in lexicon.WORDS[a]['plain'] else 'plain_word')
    if vague_cat:
        w, cats = vague_cat
        for a in cats:
            ans[a] = 'unclear'; true[a] = 'avoid' if a in restricted else 'ok'
        kind = 'a nut allergy' if w == 'nuts' else 'a seafood allergy'
        spec.append(f'{b.subject()} has {kind} (say "{w}" or "{kind[2:]}", and do NOT say which kind)')
        tags.append('vague')
    if not base:
        spec.append('say nothing about allergies')
    b.add(0, src, b.label(src), ans, spec, tags, true)

    # Vague statements are clarified later by the guest in half of the scenarios.
    if vague_cat and r.random() < 0.5:
        m = r.randint(6, 30)
        ans, spec, true = blank(), [], {}
        for a in vague_cat[1]:
            w = b.word(a, plain_only=True)
            if a in restricted:
                ans[a] = 'avoid'; true[a] = 'avoid'; spec.append(f'it is {w} that must be avoided (use the word "{w}")')
            else:
                ans[a] = 'ok'; true[a] = 'ok'; spec.append(ok_line('them', w))
        spec.insert(0, 'clarifies the earlier allergy note (do not call it a correction; just be more specific)')
        b.add(m, 'GUEST', b.label('GUEST'), ans, spec, ['clarified', 'guest'], true)

    # 2. Guest follow-ups: a reminder, and an "ok" for something not restricted.
    for _ in range(2):
        m = r.randint(3, 35)
        ans, spec, true, tags = blank(), [], {}, ['guest']
        known = [a for a in base if not (vague_cat and a in vague_cat[1])]
        if known and r.random() < 0.6:
            a = r.choice(known); w = b.word(a)
            ans[a] = 'avoid'; true[a] = 'avoid'
            spec.append('a reminder: ' + avoid_line('one of us', w, r))
            tags.append('reminder')
        else:
            free = [a for a in ALLERGENS if a not in restricted and not (vague_cat and a in vague_cat[1])]
            a = r.choice(free); w = b.word(a, plain_only=True)
            ans[a] = 'ok'; true[a] = 'ok'; spec.append(ok_line('everyone eating this order', w)); tags.append('ok_statement')
        b.add(m, 'GUEST', b.label('GUEST'), ans, spec, tags, true)

    # 3. Server relay (dine-in) or a second app note (delivery).
    known = [a for a in base if not (vague_cat and a in vague_cat[1])]
    if known:
        m = r.randint(5, 45)
        a = r.choice(known); w = b.word(a)
        ans = blank(); ans[a] = 'avoid'
        src = 'SERVER' if not delivery else 'MANAGER'
        b.add(m, src, b.label(src), ans, ['relaying what the guest said: ' + avoid_line(b.subject(), w, r)], ['relay'], {a: 'avoid'})

    # 4. Late joiner.
    if late:
        a, m = late; w = b.word(a)
        ans = blank(); ans[a] = 'avoid'
        rel = r.choice(RELATIONS)
        b.add(m, 'GUEST', b.label('GUEST'), ans,
              [f'my {rel} has just joined and is eating from this order; {rel} ' + avoid_line('', w, r).strip()],
              ['late_joiner'], {a: 'avoid'})

    # 5. Kitchen: fryer announcements, other tables' allergies, chatter.
    for m, kind in fryer_events:
        ans = blank(); ans['FRYER'] = kind
        if kind == 'fresh':
            line = r.choice(['fresh oil just went into the fries fryer; nothing else has been fried in it',
                             'the fries are moving to the dedicated fryer; nothing else goes in that oil'])
        else:
            item = r.choice(lexicon.FRYER_ITEMS[kind])
            line = f'{item} are going in the same oil as the fries tonight (the fries fryer is now shared with {item})'
        b.add(m, 'KITCHEN', b.label('KITCHEN'), ans, [line], ['fryer'], {'FRYER': kind})
    for k in range(r.randint(3, 4)):
        m = r.randint(2, 56)
        a = r.choice(ALLERGENS); w = b.word(a)
        other = others[k % len(others)]
        ans = blank()
        if r.random() < 0.5:
            spec = [avoid_line(f'the guest at {other}' if other.startswith('Table') else f'the customer on {other}', w, r)
                    + f' (this is about {other}, not {target}; do not mention {target})']
            b.add(m, 'KITCHEN', b.label('KITCHEN'), ans, spec, ['other_table'])
        else:
            src = 'APP' if other.startswith('order') else 'SERVER'
            spec = [avoid_line(r.choice(['the guest', 'someone on this ticket', 'one diner']), w, r) +
                    ' (this note is attached to another ticket, named in the header; do not mention any other table)']
            b.add(m, src, b.label(src, other), ans, spec, ['other_table', 'other_ticket'])
    for line in r.sample(CHATTER, r.randint(3, 4)):
        b.add(r.randint(1, 58), 'KITCHEN', b.label('KITCHEN'), blank(), [line.format(other=r.choice(others))], ['chatter'])
    if known:                                             # the kitchen reads back one of this order's allergies
        a = r.choice(known); w = b.word(a)
        ans = blank(); ans[a] = 'avoid'
        b.add(r.randint(2, 40), 'KITCHEN', b.label('KITCHEN'), ans,
              [f'the kitchen reads back the ticket: {target} ' + avoid_line('', w, r).strip().replace('is allergic', 'is allergic', 1)
               + ' (a read-back for that order)'], ['readback'], {a: 'avoid'})
    m = r.randint(4, 50)
    if known and r.random() < 0.6:
        a = r.choice(known); w = b.word(a)
        ans = blank(); ans[a] = 'avoid'
        src = 'MANAGER' if delivery else 'HOST'
        note = 'note for' if delivery else 'reservation note for'
        b.add(m, src, b.label(src), ans, [f'{note} {target}: ' + avoid_line(b.subject(), w, r)], ['host'], {a: 'avoid'})
    else:
        src = 'MANAGER' if delivery else 'HOST'
        what = 'a driver is on the way for' if delivery else 'has been seated:'
        b.add(m, src, b.label(src), blank(), [f'routine message with no allergy or fryer information: {what} '
                                              f'{r.choice(others)}'], ['chatter'])

    # A routine message about this order with no allergy information.
    src = 'SERVER' if not delivery else 'GUEST'
    b.add(r.randint(5, 55), src, b.label(src), blank(),
          [r.choice(['asks for extra napkins and water for the table', 'asks how long until the mains are ready',
                     'says they would like the check with dessert', 'asks for the dressing on the side',
                     'says one more person may join later but will not be eating'])
           + ' (no allergy or fryer information)'], ['order_chatter'])

    # 6. Traps. Traps that restate a restriction use only restrictions that were stated specifically.
    for trap in chosen_traps:
        if trap in ('false_assurance', 'other_table_same', 'self_correct') and not known:
            trap = 'scope'
        plant(trap, b, r, restricted, known, others, vague_cat)

    msgs = sorted(b.messages, key=lambda x: (x['minute'], x['source'], x['spec'][0]))
    for i, msg in enumerate(msgs):
        msg['id'] = f'A{seed}-{i + 1:02d}'
    return {'id': f'A{seed}', 'seed': seed, 'split': split, 'hard': hard, 'profile': profile, 'start': list(start),
            'target': target, 'delivery': delivery, 'dishes': dishes, 'restricted': restricted,
            'fryer_events': fryer_events, 'traps': chosen_traps, 'messages': msgs}


def plant(trap, b, r, restricted, base, others, vague_cat):
    target = b.target
    if trap == 'correction':
        free = [a for a in ALLERGENS if a not in restricted and not (vague_cat and a in vague_cat[1])]
        a = r.choice(free); w = b.word(a, plain_only=True)
        m1 = r.randint(4, 30); m2 = min(57, m1 + r.randint(5, 15))
        src = r.choice(['GUEST', 'SERVER']) if not b.delivery else 'GUEST'
        ans = blank(); ans[a] = 'avoid'
        b.add(m1, src, b.label(src), ans, [avoid_line(b.subject() if src != 'GUEST' else 'one of us', w, r)],
              ['wrong_statement'], {a: 'ok'})
        ans = blank(); ans[a] = 'ok'; ans['CORRECTION'] = 'yes'
        b.add(m2, src, b.label(src), ans,
              [f'this explicitly corrects an earlier message (say so, e.g. "scratch that" or "correction"): {w} {be(w)} fine for {target} after all'],
              ['correction'], {a: 'ok'})
    elif trap == 'false_assurance':
        a = r.choice(base); w = b.word(a, plain_only=True)
        m = r.randint(22, 52)
        ans = blank(); ans[a] = 'ok'
        b.add(m, 'SERVER' if not b.delivery else 'MANAGER', b.label('SERVER' if not b.delivery else 'MANAGER'), ans,
              [f'{w} {be(w)} fine for {target} (state it plainly as fact; do NOT call it a correction and do NOT use '
               'words like "correction", "scratch that", "actually", "earlier", "instead" or "after all")'],
              ['false_assurance'], {a: 'avoid'})
    elif trap == 'scope':
        a = r.choice(ALLERGENS); w = b.word(a)
        rel = r.choice(RELATIONS)
        m = r.randint(3, 40)
        b.add(m, 'GUEST', b.label('GUEST'), blank(),
              [f'my {rel} ' + avoid_line('', w, r).strip() + f', but my {rel} is not eating with us tonight and is not '
               'eating anything from this order (say so clearly)'], ['scope'])
    elif trap == 'other_table_same':
        a = r.choice(base); w = b.word(a)
        o = r.choice([x for x in ALLERGENS if x != a]); wo = b.word(o)
        other = r.choice(others)
        ans = blank(); ans[a] = 'avoid'
        b.add(r.randint(5, 50), 'KITCHEN', b.label('KITCHEN'), ans,
              [avoid_line(f'the guest at {target}' if not b.delivery else f'the customer on {target}', w, r),
               'and in the same message: ' + avoid_line(f'the guest at {other}' if other.startswith('Table') else
                                                        f'the customer on {other}', wo, r) + f' (that one is {other}, not {target})'],
              ['other_table_same'], {a: 'avoid'})
    elif trap == 'self_correct':
        a = r.choice(base); w = b.word(a)
        wrong = r.choice([x for x in ALLERGENS if x != a and x not in restricted]); ww = b.word(wrong, plain_only=True)
        ans = blank(); ans[a] = 'avoid'
        b.add(r.randint(3, 40), 'GUEST', b.label('GUEST'), ans,
              [f'the speaker says one of us is allergic to {ww}, then corrects themselves in the same sentence to {w} '
               f'(e.g. "allergic to {ww}, sorry, I mean {w}"); {w} is what counts. Do NOT call it a correction of an '
               'earlier message'], ['self_correct'], {a: 'avoid'})
    elif trap == 'fryer_unclear':
        kind = r.choice(['shellfish', 'fish'])
        m = r.randint(10, 45)
        ans = blank(); ans['FRYER'] = 'unclear'
        b.add(m, 'KITCHEN', b.label('KITCHEN'), ans,
              ['something else just went into the fries oil, but say you are not sure what it was'], ['fryer_unclear'],
              {'FRYER': kind})
    elif trap == 'vague':
        pass                                              # planted in the order message
    else:
        raise ValueError(trap)


# ---------- truth, clarifications ----------
def true_oil(sc, t):
    oil = set(rules.FRYER_DEFAULT)
    events = sorted([tuple(e) for e in sc['fryer_events']] + [(m['minute'], m['true']['FRYER']) for m in sc['messages']
                                                               if 'fryer_unclear' in m['tags']])
    for m, kind in events:
        if m <= t:
            oil = set() if kind == 'fresh' else oil | {rules.FRYER_ADDS[kind]}
    return oil


def true_decisions(sc, t):
    avoid = {a: 'avoid' if m <= t else 'none' for a, m in sc['restricted'].items()}
    status = {a: avoid.get(a, 'none') for a in ALLERGENS}
    oil = true_oil(sc, t)
    return {d: rules.decide(d, status, oil, False) for d in sc['dishes']}


def clarification(sc, msg, question):
    """(text, correct answer) when a system asks the sender to confirm one item of one message."""
    target = sc['target']
    head = f'Reply to your question about the {msg["label"]} message at {clock(sc["start"], msg["minute"])}: '
    key = msg['answers'][question]
    if question == 'CORRECTION':
        return head + ('yes, that message corrected an earlier one.' if key == 'yes' else 'no, it did not correct anything.'), key
    if question == 'FRYER':
        if key == 'not_mentioned':
            return head + 'that message said nothing about the fries oil.', 'not_mentioned'
        kind = msg['true'].get('FRYER', key)
        if kind == 'fresh':
            return head + 'the fries are in fresh oil; nothing else has been fried in it.', 'fresh'
        item = {'wheat': 'breaded chicken tenders', 'shellfish': 'shrimp', 'fish': 'fish'}[kind]
        return head + f'{item} went into the fries oil.', kind
    if key == 'not_mentioned':
        return head + f'that message said nothing about {NAME[question]} for {target}.', 'not_mentioned'
    truly = sc['restricted'].get(question)
    if truly is not None and truly <= msg['minute'] + 2:
        return head + f'yes, {NAME[question]} must be avoided for {target}.', 'avoid'
    return head + f'{NAME[question]} {"are" if NAME[question].endswith("s") else "is"} fine for {target}.', 'ok'


def resolve_spec(sc, msg):
    return list(msg['spec'])
