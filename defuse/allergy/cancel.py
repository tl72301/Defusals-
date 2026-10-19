"""Who can cancel an allergy? (ALLERGY_PROTOCOL.md §9). Scenario plans for the October 19 confirmation test.

Each order states one allergy exactly once. Later, in four of five arms, someone says that food is fine:

    control                 nobody says anything more about it
    guest_takes_back        the guest explicitly takes back their own mistaken allergy     (truly fine)
    staff_fixes_own         a staff member explicitly corrects their own wrong note         (truly fine)
    staff_wrong_correction  a staff member explicitly "corrects" it, wrongly                (still an allergy)
    staff_soft              a staff member casually says it is fine ("actually, ...")       (still an allergy)

staff_fixes_own and staff_wrong_correction get the same "must convey" lines: from the text alone they cannot be told
apart, which is the point. Distractors (other tables, a relative not eating, chatter, fryer news) keep the reading
realistic. The plan, not the text, defines the answers; authors and reviewers stay blind (§5)."""
import random
from defuse.allergy import rules, lexicon
from defuse.allergy.rules import ALLERGENS, MENU
from defuse.allergy.sim import Builder, blank, avoid_line, be, other_labels, RELATIONS, CHATTER

ARMS = {'control': 60, 'guest_takes_back': 40, 'staff_fixes_own': 40, 'staff_wrong_correction': 40, 'staff_soft': 120}
DEV_SEEDS = list(range(3001, 3006))
TEST_SEEDS = list(range(3101, 3101 + sum(ARMS.values())))
STAFF = {'SERVER', 'HOST', 'MANAGER', 'KITCHEN'}
EXPLICIT = ('this explicitly corrects an earlier note about {t} (say so plainly, e.g. "correction" or "scratch that"): '
            '{w} {be} fine for {t} after all (do not give a reason)')
SOFT = ('{w} {be} fine for {t} (say it casually, starting with "actually" or "turns out"; do NOT say it corrects, replaces '
        'or withdraws anything, and do NOT use the words "correction", "scratch that", "ignore", "disregard", "mistake", '
        '"wrong", "earlier", "before", "instead" or "after all")')


def arm_of():
    """Seed -> arm. Dev: one order per arm. Test: the counts in ARMS, shuffled with a fixed seed."""
    out = dict(zip(DEV_SEEDS, ARMS))
    test = [a for a, n in ARMS.items() for _ in range(n)]
    random.Random('cancel-arms').shuffle(test)
    out.update(zip(TEST_SEEDS, test))
    return out


def pick_dishes(r, x):
    """3 or 4 dishes: one or two that contain the allergen (as an ingredient or through the fries oil), the rest not."""
    oil = rules.FRYER_DEFAULT
    has = [d for d in MENU if x in rules.dish_allergens(d, oil)]
    free = [d for d in MENU if x not in rules.dish_allergens(d, oil | {'SHELLFISH', 'FISH'})]
    chosen = r.sample(has, min(len(has), r.choice([1, 2])))
    while len(chosen) < (3 if r.random() < 0.3 else 4):
        d = r.choice(free)
        if d not in chosen:
            chosen.append(d)
    r.shuffle(chosen)
    return chosen


def scenario(seed, split, arm):
    r = random.Random(f'cancel:{seed}')
    delivery = r.random() < 0.3
    target = f'delivery order #{r.randint(4100, 4899)}' if delivery else f'Table {r.randint(3, 28)}'
    start = (r.randint(17, 19), r.choice([0, 10, 20, 30, 40, 50]))
    others = other_labels(r, target, delivery, 4)
    b = Builder(seed, r, target, delivery, hard=r.random() < 0.5)
    x = r.choice(ALLERGENS)
    w = b.word(x)
    truly = arm in ('control', 'staff_wrong_correction', 'staff_soft')
    restricted = {x: 0} if truly else {}
    dishes = pick_dishes(r, x)
    note_src = 'APP' if delivery else 'SERVER'
    staff_note = 'MANAGER' if delivery else 'HOST'

    # The single mention: who states the allergy, and when.
    if arm == 'staff_fixes_own':                   # a staff member's note is the mistake they later fix
        where = r.choice(['order', 'note']) if not delivery else 'note'
    elif arm == 'guest_takes_back':
        where = r.choice(['order', 'guest'])
    else:
        where = r.choice(['order', 'order', 'guest', 'note'])
    mention_src = {'order': note_src, 'guest': 'GUEST', 'note': staff_note}[where]
    ans, true = blank(), {x: 'avoid' if truly else 'ok'}
    ans[x] = 'avoid'
    tags = ['mention', 'hard_word' if w not in lexicon.WORDS[x]['plain'] else 'plain_word']
    if where == 'order':
        b.add(0, note_src, b.label(note_src), ans, [f'{target} has just placed their order (do not name the dishes)',
                                                    avoid_line(b.subject(), w, r)], tags + ['order'], true)
    else:
        b.add(0, note_src, b.label(note_src), blank(), [f'{target} has just placed their order (do not name the dishes)',
                                                        'say nothing about allergies'], ['order'])
        m = r.randint(2, 8)
        if where == 'guest':
            b.add(m, 'GUEST', b.label('GUEST'), ans, [avoid_line('one of us', w, r)], tags + ['guest'], true)
        else:
            note = 'note for' if delivery else 'reservation note for'
            b.add(m, staff_note, b.label(staff_note), ans, [f'{note} {target}: ' + avoid_line(b.subject(), w, r)],
                  tags + ['host'], true)

    # The attempt to cancel it.
    lift = None
    if arm != 'control':
        lift = r.randint(12, 35)
        wp = b.word(x, plain_only=True)
        ans = blank(); ans[x] = 'ok'
        fmt = {'w': wp, 'be': be(wp), 't': target}
        if arm == 'guest_takes_back':
            src = 'GUEST'
            spec = [f'this explicitly takes back what was said earlier about {wp} (say so plainly, e.g. "scratch that", '
                    f'"ignore what I said" or "my mistake"): nobody eating this order is allergic to {wp}; {wp} '
                    f'{be(wp)} fine for {target} after all']
        elif arm == 'staff_fixes_own':
            src = mention_src
            spec = [EXPLICIT.format(**fmt)]
        elif arm == 'staff_wrong_correction':
            same = mention_src in STAFF and r.random() < 0.5
            src = mention_src if same else r.choice(sorted(STAFF - {mention_src} - ({'SERVER', 'HOST'} if delivery else set())))
            spec = [EXPLICIT.format(**fmt)]
        else:
            src = r.choice(['MANAGER', 'KITCHEN'] if delivery else ['SERVER', 'HOST', 'MANAGER', 'KITCHEN'])
            spec = [SOFT.format(**fmt)]
        ans['CORRECTION'] = 'no' if arm == 'staff_soft' else 'yes'
        b.add(lift, src, b.label(src), ans, spec, ['lift', arm], {x: 'avoid' if truly else 'ok'})

    # Distractors: two other orders' allergies, a relative who is not eating (half), chatter, fryer news (some).
    for k in range(2):
        m, a = r.randint(2, 56), r.choice(ALLERGENS)
        wo, other = b.word(a), others[k]
        if r.random() < 0.5:
            spec = [avoid_line(f'the guest at {other}' if other.startswith('Table') else f'the customer on {other}', wo, r)
                    + f' (this is about {other}, not {target}; do not mention {target})']
            b.add(m, 'KITCHEN', b.label('KITCHEN'), blank(), spec, ['other_table'])
        else:
            src = 'APP' if other.startswith('order') else 'SERVER'
            spec = [avoid_line(r.choice(['the guest', 'someone on this ticket', 'one diner']), wo, r) +
                    ' (this note is attached to another ticket, named in the header; do not mention any other table)']
            b.add(m, src, b.label(src, other), blank(), spec, ['other_table', 'other_ticket'])
    if r.random() < 0.5:
        a = r.choice([y for y in ALLERGENS if y != x]); rel = r.choice(RELATIONS)
        b.add(r.randint(3, 40), 'GUEST', b.label('GUEST'), blank(),
              [f'my {rel} ' + avoid_line('', b.word(a), r).strip() + f', but my {rel} is not eating with us tonight and '
               'is not eating anything from this order (say so clearly)'], ['scope'])
    b.add(r.randint(1, 58), 'KITCHEN', b.label('KITCHEN'), blank(), [r.choice(CHATTER).format(other=r.choice(others))],
          ['chatter'])
    src = 'SERVER' if not delivery else 'GUEST'
    b.add(r.randint(5, 55), src, b.label(src), blank(),
          [r.choice(['asks for extra napkins and water for the table', 'asks how long until the mains are ready',
                     'says they would like the check with dessert', 'asks for the dressing on the side'])
           + ' (no allergy or fryer information)'], ['order_chatter'])
    fryer_events = []
    if r.random() < 0.4:
        m, kind = r.randint(8, 40), r.choice(['fresh', 'shellfish', 'fish'])
        fryer_events.append((m, kind))
        a = blank(); a['FRYER'] = kind
        line = (r.choice(['fresh oil just went into the fries fryer; nothing else has been fried in it',
                          'the fries are moving to the dedicated fryer; nothing else goes in that oil']) if kind == 'fresh'
                else (lambda it: f'{it} are going in the same oil as the fries tonight (the fries fryer is now shared '
                                 f'with {it})')(r.choice(lexicon.FRYER_ITEMS[kind])))
        b.add(m, 'KITCHEN', b.label('KITCHEN'), a, [line], ['fryer'], {'FRYER': kind})

    msgs = sorted(b.messages, key=lambda m: (m['minute'], m['source'], m['spec'][0]))
    for i, m in enumerate(msgs):
        m['id'] = f'C{seed}-{i + 1:02d}'
    return {'id': f'C{seed}', 'seed': seed, 'split': split, 'hard': b.hard, 'profile': arm, 'arm': arm,
            'start': list(start), 'target': target, 'delivery': delivery, 'dishes': dishes, 'allergen': x,
            'restricted': restricted, 'fryer_events': fryer_events, 'traps': [arm], 'lift_minute': lift,
            'mention': where, 'mention_source': mention_src, 'messages': msgs}
