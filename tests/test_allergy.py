"""Allergy Pass: protocol engine, lexicon, generator invariants and an offline run of every system."""
import pytest
from defuse.allergy import rules, sim, lexicon, parser, runner
from defuse.allergy.models import names_to_answers


def blank(**kw):
    a = sim.blank()
    a.update(kw)
    return a


def status_after(*answers):
    msgs = [{'id': f'm{i}', 'minute': i} for i in range(len(answers))]
    return rules.restrictions(msgs, {f'm{i}': a for i, a in enumerate(answers)}, [], 99)


def test_avoid_sticks_unless_explicitly_corrected():
    assert status_after(blank(MILK='avoid'), blank(MILK='ok'))['MILK'] == 'avoid'
    assert status_after(blank(MILK='avoid'), blank(MILK='ok', CORRECTION='yes'))['MILK'] == 'none'
    assert status_after(blank(MILK='avoid'), blank(MILK='ok', CORRECTION='unclear'))['MILK'] == 'avoid'


def test_unclear_is_cleared_by_ok_but_never_weakens_avoid():
    assert status_after(blank(PEANUT='unclear'))['PEANUT'] == 'unclear'
    assert status_after(blank(PEANUT='unclear'), blank(PEANUT='ok'))['PEANUT'] == 'none'
    assert status_after(blank(PEANUT='avoid'), blank(PEANUT='unclear'))['PEANUT'] == 'avoid'


def test_fryer_starts_with_wheat_accumulates_and_resets():
    msgs = [{'id': 'a', 'minute': 1}, {'id': 'b', 'minute': 2}, {'id': 'c', 'minute': 3}, {'id': 'd', 'minute': 4}]
    ans = {'a': blank(FRYER='shellfish'), 'b': blank(FRYER='unclear'), 'c': blank(FRYER='fresh'), 'd': blank(FRYER='fish')}
    assert rules.fryer(msgs, ans, [], 0) == ({'WHEAT'}, False)
    assert rules.fryer(msgs, ans, [], 1) == ({'WHEAT', 'SHELLFISH'}, False)
    assert rules.fryer(msgs, ans, [], 2)[1] is True
    assert rules.fryer(msgs, ans, [], 3) == (set(), False)
    assert rules.fryer(msgs, ans, [], 4) == ({'FISH'}, False)


def test_dish_decisions():
    none = {a: 'none' for a in rules.ALLERGENS}
    assert rules.decide('House fries', {**none, 'WHEAT': 'avoid'}, {'WHEAT'}, False) == rules.HOLD   # via the oil
    assert rules.decide('House fries', {**none, 'WHEAT': 'avoid'}, set(), False) == rules.SEND
    assert rules.decide('Pesto pasta', {**none, 'TREE_NUT': 'unclear'}, set(), False) == rules.ASK
    assert rules.decide('House fries', {**none, 'SOY': 'avoid'}, set(), True) == rules.ASK            # oil unknown
    assert rules.decide('House fries', none, set(), True) == rules.SEND                              # no restrictions
    assert rules.decide('Vegetable curry with coconut milk', {**none, 'MILK': 'avoid'}, set(), False) == rules.SEND


@pytest.mark.parametrize('food,cats', [('coconut milk', set()), ('almond milk', {'TREE_NUT'}), ('peanuts', {'PEANUT'}),
                                       ('celiac', {'WHEAT'}), ('ghee', {'MILK'}), ('tahini', {'SESAME'}),
                                       ('butternut squash', set()), ('duck eggs', {'EGG'}), ('prawns', {'SHELLFISH'})])
def test_lexicon(food, cats):
    assert lexicon.categories(food)[0] == cats


def test_names_mapping_resolves_nuts_with_peanuts_fine():
    a = names_to_answers({'foods': [{'food': 'nuts', 'status': 'avoid'}, {'food': 'peanuts', 'status': 'ok'}],
                          'fryer_status': 'shared', 'fryer_shared_with': 'the fried shrimp', 'correction': 'no'})
    assert a['TREE_NUT'] == 'avoid' and a['PEANUT'] == 'ok' and a['FRYER'] == 'shellfish'
    a = names_to_answers({'foods': [{'food': 'nuts', 'status': 'avoid'}], 'fryer_status': 'not_mentioned',
                          'fryer_shared_with': None, 'correction': 'no'})
    assert a['TREE_NUT'] == a['PEANUT'] == 'unclear'


def test_generator_invariants():
    for seed in list(range(2001, 2061)) + list(range(2101, 2161)):
        sc = sim.scenario(seed, 'x', seed > 2100)
        ids = [m['id'] for m in sc['messages']]
        assert len(ids) == len(set(ids)) and all(m['spec'] for m in sc['messages'])
        msgs = [{'id': m['id'], 'minute': m['minute']} for m in sc['messages']]
        key = {m['id']: m['answers'] for m in sc['messages']}
        for t in rules.POLLS:
            j = rules.decisions(sc['dishes'], msgs, key, [], t)[0]
            truth = sim.true_decisions(sc, t)
            assert not any(j[d] == rules.SEND and truth[d] != rules.SEND for d in sc['dishes']), (seed, t)


def test_every_system_runs_offline(stub, tmp_path):
    sc = sim.scenario(2003, 'test', True)
    for m in sc['messages']:
        m['text'] = ' '.join(m['spec'])
    ex = runner.make_extractors(tmp_path, endpoint=stub['url'])
    out = {s: runner.run_scenario(sc, s, ex) for s in runner.SYSTEMS}
    assert runner.score([out['oracle']])['wrong_decisions'] == 0
    for s, r in out.items():
        assert len(r['polls']) == len(rules.POLLS) and set(r['extractions']) == {m['id'] for m in sc['messages']}
    body = stub['requests'][0]
    assert len(body['questions']) == 11 and 'FDA' in body['input'][0]['content'][0]['text']


def test_parser_scope_and_slips():
    a = parser.parse('Guest at Table 12, text to the restaurant', "My sister can't have shrimp but she isn't eating with us.", 'Table 12')
    assert a['SHELLFISH'] == 'not_mentioned'
    a = parser.parse('Kitchen chat', 'Table 12 no dairy; Table 9 no eggs.', 'Table 12')
    assert a['MILK'] == 'avoid' and a['EGG'] == 'not_mentioned'


def test_saved_scenarios_compute_truth():
    from defuse.allergy import bank
    for split in bank.SPLITS:
        for sc in bank.load(split):
            for t in rules.POLLS:
                sim.true_decisions(sc, t)
