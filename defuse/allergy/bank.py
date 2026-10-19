"""Scenario bank: build plans, export blind authoring and review packets, merge texts, apply review exclusions.

Authors see only headers and spec lines. Reviewers see only headers, texts and the questions. Neither sees answers."""
import json
from pathlib import Path
from defuse.allergy import sim, rules, cancel, confirm

BANK = Path(__file__).resolve().parent / 'bank'
SPLITS = {'dev': [1001, 1002], 'hard_dev': [1101, 1102],
          'test': list(range(2001, 2061)), 'hard_test': list(range(2101, 2161)),
          'cancel_dev': cancel.DEV_SEEDS, 'cancel_test': cancel.TEST_SEEDS,       # §9: who can cancel an allergy
          'confirm_dev': confirm.DEV_SEEDS, 'confirm_test': confirm.TEST_SEEDS}   # §10: just ask the guest?
HARD = {'hard_dev', 'hard_test'}
CANCEL = {'cancel_dev', 'cancel_test'}
CONFIRM = {'confirm_dev', 'confirm_test'}


def header(sc, msg):
    return f'[{rules.clock(sc["start"], msg["minute"])}] {msg["label"]}'


def build(splits=None):
    BANK.mkdir(exist_ok=True)
    for split, seeds in SPLITS.items():
        if splits and split not in splits:
            continue
        if split in CANCEL:
            arm = cancel.arm_of()
            plans = [cancel.scenario(s, split, arm[s]) for s in seeds]
        elif split in CONFIRM:
            arm = confirm.arm_of()
            plans = [confirm.scenario(s, split, *arm[s]) for s in seeds]
        else:
            plans = [sim.scenario(s, split, split in HARD) for s in seeds]
        (BANK / f'{split}.json').write_text(json.dumps(plans, indent=1))


def load(split):
    data = json.loads((BANK / f'{split}.json').read_text())
    texts = BANK / f'{split}_texts.json'
    if texts.exists():
        t = json.loads(texts.read_text())
        for sc in data:
            for m in sc['messages']:
                m['text'] = t.get(m['id'])
    excluded = BANK / 'excluded.json'
    ex = json.loads(excluded.read_text()) if excluded.exists() else {}
    dropped = set(ex.get('messages', []))
    data = [sc for sc in data if sc['id'] not in set(ex.get('scenarios', []))]      # §9.4: whole orders
    for sc in data:
        sc['messages'] = [m for m in sc['messages'] if m['id'] not in dropped]
    return data


def authoring_packet(split, seeds, path, replies=None):
    """replies (§10.4): None writes every message; False leaves out the guests' answers; True writes only those, one
    per item, so their authors never see the rest of the order."""
    data = {sc['seed']: sc for sc in json.loads((BANK / f'{split}.json').read_text())}
    packet = []
    for seed in seeds:
        sc = data[seed]
        msgs = [{'id': m['id'], 'header': header(sc, m), 'must_convey': sim.resolve_spec(sc, m)} for m in sc['messages']
                if replies is None or ('reply_to' in m) == replies]
        if msgs:
            packet.append({'scenario': sc['id'], 'order': sc['target'], 'messages': msgs})
    Path(path).write_text(json.dumps(packet, indent=1, ensure_ascii=False))
    return sum(len(x['messages']) for x in packet)


def review_packet(split, seeds, path):
    """Compact: the questions once, then each message's order, header and text."""
    guide = {'how_to_answer': 'Answer all 11 questions for every message with exactly one allowed value, judging ONLY '
                              'from the header and the text, about the food for the order named in "order".',
             'definitions': rules.DEFINITIONS,
             'questions': [{'name': n, 'instructions': i, 'options': [{'value': v, 'meaning': d} for v, d in o]}
                           for n, i, o in rules.questions()]}
    items = []
    by_seed = {sc['seed']: sc for sc in load(split)}
    for seed in seeds:
        sc = by_seed[seed]
        for m in sc['messages']:
            items.append({'id': m['id'], 'order': sc['target'], 'header': header(sc, m), 'text': m['text']})
    Path(path).write_text(json.dumps({'guide': guide, 'messages': items}, indent=1, ensure_ascii=False))
    return len(items)


def merge_texts(split, files):
    texts = {}
    for f in files:
        for item in json.loads(Path(f).read_text()):
            texts[item['id']] = item['text']
    (BANK / f'{split}_texts.json').write_text(json.dumps(texts, indent=1, ensure_ascii=False))
    return texts


def compare_review(split, review_files):
    answers = {}
    for f in review_files:
        for item in json.loads(Path(f).read_text()):
            answers[item['id']] = item['answers']
    out = []
    for sc in json.loads((BANK / f'{split}.json').read_text()):
        for m in sc['messages']:
            got = answers.get(m['id'])
            if got is None:
                out.append({'scenario': sc['id'], 'id': m['id'], 'missing': True})
                continue
            diff = {q: (m['answers'][q], got.get(q)) for q in rules.QUESTION_NAMES if got.get(q) != m['answers'][q]}
            if diff:
                out.append({'scenario': sc['id'], 'id': m['id'], 'diff': diff})
    return out
