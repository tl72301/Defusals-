"""Scenario bank: build plans, export blind authoring and review packets, merge texts, apply review exclusions.

Authors see only headers and spec lines. Reviewers see only headers, texts and the questions. Neither sees answers."""
import json
from pathlib import Path
from defuse.launch import sim, rules

BANK = Path(__file__).resolve().parent / 'bank'
SPLITS = {'dev': list(range(1001, 1009)), 'test': list(range(2001, 2025)),
          'hard_dev': list(range(3101, 3105)), 'hard_test': list(range(3001, 3017))}
HARD = {'hard_dev', 'hard_test'}


def header(sc, rep):
    return f'[{rules.clock(sc["start"], rep["minute"])}] {sim.SOURCES[rep["source"]]}'


def build():
    BANK.mkdir(exist_ok=True)
    for split, seeds in SPLITS.items():
        (BANK / f'{split}.json').write_text(json.dumps([sim.scenario(s, split, split in HARD) for s in seeds], indent=1))


def load(split):
    data = json.loads((BANK / f'{split}.json').read_text())
    texts = BANK / f'{split}_texts.json'
    if texts.exists():
        t = json.loads(texts.read_text())
        for sc in data:
            for r in sc['reports']:
                r['text'] = t.get(r['id'])
    excluded = BANK / 'excluded.json'
    ex = json.loads(excluded.read_text()) if excluded.exists() else {}
    gone, dropped = set(ex.get('scenarios', [])), set(ex.get('reports', []))
    for sc in data:
        sc['reports'] = [r for r in sc['reports'] if r['id'] not in dropped]
    return [sc for sc in data if sc['id'] not in gone]


def authoring_packet(split, seeds, path):
    data = {sc['id']: sc for sc in json.loads((BANK / f'{split}.json').read_text())}
    packet = []
    for seed in seeds:
        sc = data[f'L{seed}']
        packet.append({'scenario': sc['id'], 'reports': [
            {'id': r['id'], 'header': header(sc, r), 'must_convey': sim.resolve_spec(sc, r)} for r in sc['reports']]})
    Path(path).write_text(json.dumps(packet, indent=1, ensure_ascii=False))


def review_packet(split, ids, path):
    """Headers, texts and the 9 questions (with clock times filled in) for the given report ids."""
    out = []
    for sc in load(split):
        for r in sc['reports']:
            if r['id'] in ids:
                out.append({'id': r['id'], 'header': header(sc, r), 'text': r['text'],
                            'questions': [{'name': n, 'instructions': i, 'options': [{'value': v, 'description': d} for v, d in o]}
                                          for n, i, o in rules.questions(sc['start'], r['minute'])]})
    Path(path).write_text(json.dumps(out, indent=1, ensure_ascii=False))


def merge_texts(split, files):
    texts = {}
    for f in files:
        for item in json.loads(Path(f).read_text()):
            texts[item['id']] = item['text']
    (BANK / f'{split}_texts.json').write_text(json.dumps(texts, indent=1, ensure_ascii=False))
    return texts


def compare_review(split, review_files):
    """Reviewer answers vs answer keys. Returns per-report disagreements."""
    answers = {}
    for f in review_files:
        for item in json.loads(Path(f).read_text()):
            answers[item['id']] = item['answers']
    out = []
    for sc in json.loads((BANK / f'{split}.json').read_text()):
        for r in sc['reports']:
            got = answers.get(r['id'])
            if got is None:
                out.append({'scenario': sc['id'], 'id': r['id'], 'missing': True})
                continue
            diff = {q: (r['answers'][q], got.get(q)) for q in rules.QUESTION_NAMES if got.get(q) != r['answers'][q]}
            if diff:
                out.append({'scenario': sc['id'], 'id': r['id'], 'diff': diff})
    return out
