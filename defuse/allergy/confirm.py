"""Just ask the guest? (ALLERGY_PROTOCOL.md §10). Scenario plans for the second October 19 test.

Each order's allergy is written down once, by staff. Later a staff member says that food is fine:

    explicit_right   explicitly corrects the note, and is right: nobody eating the order needs to avoid it
    explicit_wrong   explicitly "corrects" it, wrongly: someone eating the order is allergic
    casual_right     says casually that it is fine ("actually, ..."), and is right
    casual_wrong     says casually that it is fine, wrongly

The right and wrong arms get identical "must convey" lines for the note and the staff message, so from those texts
nobody can tell them apart. Under the new rule (`confirm`, in rules.py) a staff "fine" makes code ask the guest a fixed
question; every order carries the guest's planned answer, which code delivers only when its reader's own readings
asked the question. The answers come in five styles, each written once meaning "no, nobody does" and once meaning
"yes, someone does". The plan, not the text, defines the answer key; authors and reviewers stay blind (§5)."""
import random
from defuse.allergy import cancel, lexicon
from defuse.allergy.rules import ALLERGENS
from defuse.allergy.sim import Builder, blank, avoid_line, be, other_labels, RELATIONS

ARMS = {'explicit_right': 60, 'explicit_wrong': 60, 'casual_right': 60, 'casual_wrong': 60}
DEV_SEEDS = list(range(3401, 3405))
TEST_SEEDS = list(range(3501, 3501 + sum(ARMS.values())))
STYLES = ['plain', 'short', 'indirect', 'scope', 'polarity']
DEV_STYLES = ['short', 'polarity', 'scope', 'indirect']
STAFF = ['SERVER', 'HOST', 'MANAGER', 'KITCHEN']
QUESTION = 'Does anyone eating this order need to avoid {w}?'

# What the guest's answer must convey. 'no': nobody eating the order needs to avoid it (key ok); 'yes': someone does
# (key avoid). Every style is meant to be clear to a careful reader who sees the question in the header.
REPLY = {
    'no': {
        'plain': 'answers the question with a clear no: nobody eating this order needs to avoid {w} (use the word "{w}")',
        'short': 'a very short answer, two to five words, meaning "no, nobody here does" (do NOT name any food or '
                 'allergen: it only makes sense together with the question in the header)',
        'indirect': 'answers without the words "yes", "no" or "allergic": says they eat {w} all the time with no '
                    'problem, so nobody eating this order needs to avoid it (use the word "{w}")',
        'scope': 'says nobody eating this order needs to avoid {w}: the only one with a {w} allergy is their {rel}, '
                 'who is not here tonight and is not eating anything from this order (mention the {rel}; use the word '
                 '"{w}")',
        'polarity': 'starts with "yeah, no" (or "yeah no") and means: no, nobody eating this order needs to avoid {w} '
                    '(use the word "{w}")'},
    'yes': {
        'plain': 'answers the question with a clear yes: someone eating this order is allergic to {w} (use the word '
                 '"{w}")',
        'short': 'a very short answer, two to five words, meaning "yes, I do" (do NOT name any food or allergen: it '
                 'only makes sense together with the question in the header)',
        'indirect': 'answers without the words "yes", "no" or "allergic": says {w} makes them seriously ill (for '
                    'example an EpiPen, hives or a hospital visit), so it must be kept off their food (use the word '
                    '"{w}")',
        'scope': 'says it is not them but their {rel}, who is here eating from this order tonight, who is allergic to '
                 '{w} (mention the {rel}; use the word "{w}")',
        'polarity': 'starts with the word "No" but means yes: asks for no {w} because someone eating this order is '
                    'allergic (for example "No {w} please, ...") (use the word "{w}")'},
}


def arm_of():
    """Seed -> (arm, reply style). Dev: one order per arm. Test: 60 per arm, shuffled with a fixed seed; within each
    arm, 12 orders per style, also shuffled with a fixed seed."""
    out = {s: (a, st) for s, a, st in zip(DEV_SEEDS, ARMS, DEV_STYLES)}
    test = [a for a, n in ARMS.items() for _ in range(n)]
    random.Random('confirm-arms').shuffle(test)
    styles = {}
    for a, n in ARMS.items():
        styles[a] = [st for st in STYLES for _ in range(n // len(STYLES))]
        random.Random(f'confirm-styles:{a}').shuffle(styles[a])
    for seed, a in zip(TEST_SEEDS, test):
        out[seed] = (a, styles[a].pop())
    return out


def reply_label(b, question):
    who = f'Customer, app chat for {b.target}' if b.delivery else f'Guest at {b.target}'
    return f'{who}, reply to the restaurant\'s question "{question}"'


def scenario(seed, split, arm, style):
    r = random.Random(f'confirm:{seed}')
    delivery = r.random() < 0.3
    target = f'delivery order #{r.randint(4100, 4899)}' if delivery else f'Table {r.randint(3, 28)}'
    start = (r.randint(17, 19), r.choice([0, 10, 20, 30, 40, 50]))
    others = other_labels(r, target, delivery, 4)
    b = Builder(seed, r, target, delivery, hard=r.random() < 0.5)
    x = r.choice(ALLERGENS)
    w = b.word(x)
    right = arm.endswith('_right')
    truth = {x: 'ok' if right else 'avoid'}
    dishes = cancel.pick_dishes(r, x)

    # The single mention, always by staff: the server's ticket note, a host's reservation note or a manager's note.
    where = 'manager' if delivery else r.choice(['order', 'order', 'host', 'manager'])
    mention_src = {'order': 'SERVER', 'host': 'HOST', 'manager': 'MANAGER'}[where]
    ans = blank(); ans[x] = 'avoid'
    tags = ['mention', where, 'hard_word' if w not in lexicon.WORDS[x]['plain'] else 'plain_word']
    if where == 'order':
        b.add(0, 'SERVER', b.label('SERVER'), ans, [f'{target} has just placed their order (do not name the dishes)',
                                                    avoid_line(b.subject(), w, r)], tags, truth)
    else:
        src0 = 'APP' if delivery else 'SERVER'
        b.add(0, src0, b.label(src0), blank(), [f'{target} has just placed their order (do not name the dishes)',
                                                'say nothing about allergies'], ['order'])
        note = 'note for' if delivery or where == 'manager' else 'reservation note for'
        b.add(r.randint(2, 8), mention_src, b.label(mention_src), ans,
              [f'{note} {target}: ' + avoid_line(b.subject(), w, r)], tags, truth)

    # The staff "fine": the same role that wrote the note half the time, otherwise another staff role.
    lift = r.randint(12, 35)
    wp = b.word(x, plain_only=True)
    roles = [s for s in STAFF if not (delivery and s in ('SERVER', 'HOST'))]
    src = mention_src if r.random() < 0.5 else r.choice([s for s in roles if s != mention_src])
    fmt = {'w': wp, 'be': be(wp), 't': target}
    ans = blank(); ans[x] = 'ok'
    ans['CORRECTION'] = 'yes' if arm.startswith('explicit') else 'no'
    spec = (cancel.EXPLICIT if arm.startswith('explicit') else cancel.SOFT).format(**fmt)
    b.add(lift, src, b.label(src), ans, [spec], ['lift', arm], truth)

    # The guest's answer to the code's question, delivered only if a reader's readings asked it.
    question = QUESTION.format(w=wp)
    reply_minute = lift + r.randint(2, 6)
    rel = r.choice(RELATIONS)
    ans = blank(); ans[x] = 'ok' if right else 'avoid'
    b.add(reply_minute, 'GUEST', reply_label(b, question), ans,
          [REPLY['no' if right else 'yes'][style].format(w=wp, rel=rel)], ['reply', style], truth)

    fryer_events = cancel.distractors(b, r, x, target, others, delivery)
    msgs = sorted(b.messages, key=lambda m: (m['minute'], m['source'], m['spec'][0]))
    for i, m in enumerate(msgs):
        m['id'] = f'Q{seed}-{i + 1:02d}'
    lift_id = next(m['id'] for m in msgs if 'lift' in m['tags'])
    reply = next(m for m in msgs if 'reply' in m['tags'])
    reply.update(reply_to=lift_id, about=x)
    return {'id': f'Q{seed}', 'seed': seed, 'split': split, 'hard': b.hard, 'profile': arm, 'arm': arm, 'style': style,
            'start': list(start), 'target': target, 'delivery': delivery, 'dishes': dishes, 'allergen': x,
            'restricted': {} if right else {x: 0}, 'fryer_events': fryer_events, 'traps': [arm, style],
            'lift_minute': lift, 'reply_minute': reply_minute, 'question': question, 'mention': where,
            'mention_source': mention_src, 'lift_source': src, 'messages': msgs}
