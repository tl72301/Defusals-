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
    from defuse.allergy.report import summarize
    for r in out.values():
        v = summarize([r], {})
        assert v['unnecessary_holds'] + v['unnecessary_asks'] == v['unjustified_holds']


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


def test_exploratory_replay_matches_runner(stub, tmp_path):
    from defuse.allergy import exploratory
    runner.run('test', runner.SYSTEMS, tmp_path, endpoint=stub['url'], limit=2)
    scs, runs = exploratory.load_all(tmp_path)
    assert set(scs) == {'A2001', 'A2002'}
    for s, by in runs.items():
        for sid, r in by.items():
            got = exploratory.replay(scs[sid], {m: e['answers'] for m, e in r['extractions'].items()},
                                     exploratory.overrides(r), r['key'], exploratory.overrides(r, 'correct'))
            assert got == [(p['S'][d], p['J'][d], p['T'][d]) for p in r['polls'] for d in scs[sid]['dishes']]
    single = exploratory.single_mention(scs, runs)
    assert single['oracle']['false_clears'] == 0 and single['oracle']['missed_sole_mention'] == 0
    h = exploratory.hybrid(scs, runs, 0.0, 'options')     # nothing below 0: Decisions alone
    assert h['messages_sent_on'] == 0 and h['false_clears'] == runner.score(list(runs['decisions'].values()))['false_clears']


def test_cancel_rules():
    def status(*msgs, rule):
        ms = [{'id': f'm{i}', 'minute': i, 'source': src} for i, (src, _) in enumerate(msgs)]
        return rules.restrictions(ms, {f'm{i}': a for i, (_, a) in enumerate(msgs)}, [], 99, rule)['MILK']
    guest_avoid, fix = ('GUEST', blank(MILK='avoid')), blank(MILK='ok', CORRECTION='yes')
    for rule, server_fix, guest_fix in (('anyone', 'none', 'none'), ('guest_only', 'avoid', 'none'),
                                        ('same_sender', 'avoid', 'none')):
        assert status(guest_avoid, ('SERVER', fix), rule=rule) == server_fix
        assert status(guest_avoid, ('GUEST', fix), rule=rule) == guest_fix
    assert status(('SERVER', blank(MILK='avoid')), ('SERVER', fix), rule='same_sender') == 'none'
    assert status(('SERVER', blank(MILK='unclear')), ('KITCHEN', blank(MILK='ok')), rule='guest_only') == 'unclear'
    assert status(('SERVER', blank(MILK='unclear')), ('KITCHEN', blank(MILK='ok')), rule='anyone') == 'none'


def test_cancel_plans():
    from collections import Counter
    from defuse.allergy import cancel
    arm = cancel.arm_of()
    assert Counter(arm[s] for s in cancel.TEST_SEEDS) == Counter(cancel.ARMS)
    for seed in cancel.DEV_SEEDS + cancel.TEST_SEEDS:
        sc = cancel.scenario(seed, 'x', arm[seed])
        x = sc['allergen']
        assert sum('mention' in m['tags'] for m in sc['messages']) == 1
        assert [m['id'] for m in sc['messages'] if m['answers'][x] == 'avoid'] == \
               [m['id'] for m in sc['messages'] if 'mention' in m['tags']]
        assert any(x in rules.dish_allergens(d, rules.FRYER_DEFAULT) for d in sc['dishes'])
        assert (x in sc['restricted']) == (sc['arm'] in ('control', 'staff_wrong_correction', 'staff_soft'))
        lift = [m for m in sc['messages'] if 'lift' in m['tags']]
        assert len(lift) == (sc['arm'] != 'control')
        if sc['arm'] == 'staff_fixes_own':
            assert lift[0]['source'] == sc['mention_source']


def test_cancel_report_offline(stub, tmp_path):
    import json
    from defuse.allergy import cancel, cancel_report, bank
    arm = cancel.arm_of()
    scs = [cancel.scenario(s, 'cancel_dev', arm[s]) for s in cancel.DEV_SEEDS]
    for sc in scs:
        for m in sc['messages']:
            m['text'] = ' '.join(m['spec'])
    ex = runner.make_extractors(tmp_path, endpoint=stub['url'])
    (tmp_path / 'cancel_dev').mkdir()
    for s in runner.SYSTEMS:
        res = [runner.run_scenario(sc, s, ex) for sc in scs]
        (tmp_path / 'cancel_dev' / f'{s}.json').write_text(json.dumps({'results': res}))
    out = cancel_report.analyse(tmp_path, 'cancel_dev')
    oracle = out['readers']['oracle']['rules']
    assert oracle['anyone']['by_arm']['staff_wrong_correction']['unsafe'] == 1
    assert oracle['guest_only']['all']['unsafe'] == 0
    assert oracle['guest_only']['by_arm']['staff_fixes_own']['needless'] == 1
    assert 'hybrid' in out['readers'] and set(out['tests']) == {'reading_changes_outcome', 'rules_by_arm_descriptive', 'mention_missed', 'soft_read_as_correction', 'hybrid'}
