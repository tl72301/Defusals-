import hashlib
import json
from collections import Counter
from defuse.gauntlet import tasks, baselines


def test_ladder_b_rule_parser_is_perfect_given_true_contents():
    for t in tasks.ladder_b_tasks():
        contents = lambda prompt, t=t: t['contents_bin']
        contents.__name__ = 'truth'
        assert baselines.with_rules(contents)(t['prompt']) == t['answer']
        overrides, exceptions = baselines.parse_rules(t['prompt'])
        assert overrides == t['rules']['overrides'] and exceptions == [tuple(e) for e in t['rules']['exceptions']]
    decided = Counter(t['decided_by'] for t in tasks.ladder_b_tasks() if t['rung'] == 5)
    assert decided['exception'] >= 8 and decided['destination rule'] >= 8


def test_tasks_are_deterministic_and_answers_are_bins():
    for name in 'ABD':
        first, again = tasks.LADDERS[name](), tasks.LADDERS[name]()
        assert [t['prompt'] for t in first] == [t['prompt'] for t in again]
        assert all(t['answer'] in {o['id'] for o in t['options']} for t in first)
        assert all(baselines.label(t['prompt']) == t['label'] for t in first)


def test_classifier_is_frozen_and_trained_on_the_development_bank_only():
    w = json.loads(baselines.WEIGHTS.read_text())
    texts, bins = baselines.training_set()
    assert w['training_sha256'] == hashlib.sha256(json.dumps([texts, bins]).encode()).hexdigest()
    assert w['examples'] == len(texts) and 'v1' in w['trained_on'] and len(w['coef']) == 4
