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
    from defuse.allergy import charts, render                 # the chart, the video card and a truth-mode frame draw
    charts.cancel(tmp_path, tmp_path / 'cancel.png', 'cancel_dev')
    assert (tmp_path / 'cancel.png').stat().st_size > 10000
    assert render.cancel_card(tmp_path / 'cancel_dev-report.json').size == (render.W, render.H)
    sc = next(s for s in bank.load('cancel_dev') if s['arm'] == 'staff_wrong_correction')
    run = json.loads((tmp_path / 'cancel_dev' / 'oracle.json').read_text())['results']
    run = next(r for r in run if r['scenario'] == sc['id'])
    assert render.system_state(sc, run, 60, 'anyone')[0] != render.system_state(sc, run, 60, 'guest_only')[0]
    assert render.frame(sc, [(lab, run, rule) for rule, lab in render.RULE_LABELS], None, 60, [[0, 0]] * 3, True).size == (render.W, render.H)


def test_cancel_run_offline(stub, tmp_path, monkeypatch):
    from defuse.allergy import cancel_run, bank
    from defuse.budget import Budget
    load = bank.load
    monkeypatch.setattr(bank, 'load', lambda split: load(split)[:2])      # two orders per split keeps this quick
    monkeypatch.chdir(tmp_path)
    Budget().approve(4.00, attempt_requests=20000, confirm=True)
    monkeypatch.setattr(cancel_run, 'ROOT', tmp_path / 'data' / 'allergy')
    monkeypatch.setattr(cancel_run, 'ENDPOINT', stub['url'])
    cancel_run.main()
    for tag in ('', '-r2'):
        assert (tmp_path / 'data' / 'allergy' / 'cancel_test' / f'decisions{tag}.json').exists()
    from defuse.allergy import cancel_report                  # §9.6 (f): the stub answers the same way twice
    rep = cancel_report.repeat(tmp_path / 'data' / 'allergy', 'cancel_test')
    assert rep['decisions']['answers_changed']['k'] == 0 and rep['decisions']['messages_changed']['n'] == sum(
        len(sc['messages']) for sc in bank.load('cancel_test'))


def test_confirm_rule():
    """§10: a staff "fine" asks the guest; only the guest's answer to that question can lift the allergy."""
    def run(*msgs, rule='confirm', t=99):
        ms, ans = [], {}
        for i, (src, a, extra) in enumerate(msgs):
            ms.append({'id': f'm{i}', 'minute': i, 'source': src, **extra}); ans[f'm{i}'] = a
        log = {}
        return rules.restrictions(ms, ans, [], t, rule, log)['MILK'], log['asked']
    note = ('SERVER', blank(MILK='avoid'), {})
    fine = ('MANAGER', blank(MILK='ok', CORRECTION='yes'), {})
    casual = ('KITCHEN', blank(MILK='ok'), {})
    yes = ('GUEST', blank(MILK='avoid'), {'reply_to': 'm1', 'about': 'MILK'})
    no = ('GUEST', blank(MILK='ok'), {'reply_to': 'm1', 'about': 'MILK'})
    unsure = ('GUEST', blank(MILK='unclear'), {'reply_to': 'm1', 'about': 'MILK'})
    assert run(note, fine, no) == ('none', [('m1', 'MILK')])        # asked; the guest says nobody needs to avoid it
    assert run(note, casual, no) == ('none', [('m1', 'MILK')])      # a casual "fine" asks too: no correction needed
    assert run(note, fine, yes)[0] == 'avoid'
    assert run(note, fine, unsure)[0] == 'avoid'
    assert run(note, fine, no, t=1)[0] == 'avoid'                  # still waiting for the answer
    assert run(note, ('MANAGER', blank(), {}), no) == ('avoid', [])  # never asked, so the answer never came
    for rule in ('anyone', 'guest_only', 'same_sender'):            # the answer exists only under confirm
        assert run(note, casual, no, rule=rule) == ('avoid', [])
    assert run(note, fine, no, rule='anyone')[0] == 'none' and run(note, fine, no, rule='guest_only')[0] == 'avoid'
    assert run(('SERVER', blank(), {}), fine, no) == ('none', [])   # nothing to avoid: no question
    assert run(note, ('GUEST', blank(MILK='ok', CORRECTION='yes'), {}))[0] == 'none'   # the guest's own take-back
    assert run(note, ('MANAGER', blank(MILK='ok', CORRECTION='yes'), {}), ('GUEST', blank(MILK='ok'), {}))[0] == 'avoid'
    ms = [{'id': 'a', 'minute': 0, 'source': 'HOST'}, {'id': 'b', 'minute': 1, 'source': 'KITCHEN'}]   # a question with
    log = {}                                                                                              # no planned answer
    assert rules.restrictions(ms, {'a': blank(EGG='unclear'), 'b': blank(EGG='ok')}, [], 9, 'confirm', log)['EGG'] == 'unclear'
    assert log['asked'] == [('b', 'EGG')]


def test_confirm_plans():
    from collections import Counter
    from defuse.allergy import confirm, bank, confirm_report
    arm = confirm.arm_of()
    assert Counter(arm[s][0] for s in confirm.TEST_SEEDS) == Counter(confirm.ARMS)
    assert set(Counter(arm[s] for s in confirm.TEST_SEEDS).values()) == {12}
    assert [arm[s][0] for s in confirm.DEV_SEEDS] == list(confirm.ARMS)
    for split in ('confirm_dev', 'confirm_test'):
        saved = bank.load(split)
        assert [sc['seed'] for sc in saved] == bank.SPLITS[split]
        for sc in saved:
            assert sc == json_round(confirm.scenario(sc['seed'], split, *arm[sc['seed']]) | {'messages': sc['messages']})
            x, msgs = sc['allergen'], sc['messages']
            mention, lift, reply = ([m for m in msgs if t in m['tags']] for t in ('mention', 'lift', 'reply'))
            assert len(mention) == len(lift) == len(reply) == 1
            mention, lift, reply = mention[0], lift[0], reply[0]
            assert mention['source'] in ('SERVER', 'HOST', 'MANAGER') and lift['source'] in confirm.STAFF
            assert [m['id'] for m in msgs if m['answers'][x] == 'avoid'] == [mention['id']] + \
                   ([reply['id']] if sc['arm'].endswith('wrong') else [])
            assert reply['reply_to'] == lift['id'] and reply['about'] == x and reply['minute'] - lift['minute'] in range(2, 7)
            assert reply['answers'][x] == ('ok' if sc['arm'].endswith('right') else 'avoid')
            assert (x in sc['restricted']) == sc['arm'].endswith('wrong')
            assert sc['question'] in reply['label'] and any(x in rules.dish_allergens(d, rules.FRYER_DEFAULT)
                                                             for d in sc['dishes'])
            o = {rule: confirm_report.order_outcome(sc, runner.run_scenario(sc, 'oracle', {}), rule) for rule in
                 confirm_report.RULES}
            assert not o['confirm']['unsafe'] and not o['confirm']['needless'] and o['confirm']['asked']
            assert o['guest_only']['needless'] == sc['arm'].endswith('right')
            assert o['anyone']['unsafe'] == (sc['arm'] == 'explicit_wrong')
            assert o['anyone']['needless'] == (sc['arm'] == 'casual_right')


def json_round(x):
    import json
    return json.loads(json.dumps(x))


def test_confirm_report_offline(stub, tmp_path):
    import json
    from defuse.allergy import confirm_report, bank
    scs = bank.load('confirm_dev')
    for sc in scs:
        for m in sc['messages']:
            m['text'] = ' '.join(m['spec'])
    ex = runner.make_extractors(tmp_path, endpoint=stub['url'])
    (tmp_path / 'confirm_dev').mkdir()
    for s in runner.SYSTEMS:
        res = [runner.run_scenario(sc, s, ex) for sc in scs]
        (tmp_path / 'confirm_dev' / f'{s}.json').write_text(json.dumps({'results': res}))
        reply = {m['id'] for sc in scs for m in sc['messages'] if 'reply' in m['tags']}
        assert not any(c['message'] in reply for r in res for c in r['clarifications'])      # never asked about a reply
    out = confirm_report.analyse(tmp_path, 'confirm_dev')
    oracle = out['readers']['oracle']['rules']
    assert oracle['confirm']['unsafe_of_wrong']['k'] == oracle['confirm']['needless_of_right']['k'] == 0
    assert oracle['guest_only']['needless_of_right']['k'] == 2 and oracle['anyone']['unsafe_of_wrong']['k'] == 1
    assert 'hybrid' in out['readers'] and set(out['tests']) == {'confirm_outcome_differs_from_key', 'reply_misread',
                                                                'confirm_keeps_gains', 'hybrid'}
    assert sum(out['readers']['decisions']['reply_readings'][k].get('not_mentioned', 0) for k in
               out['readers']['decisions']['reply_readings']) == 4           # the stub answers the first option


def test_confirm_run_offline(stub, tmp_path, monkeypatch):
    from defuse.allergy import confirm_run, confirm_report, bank
    from defuse.budget import Budget
    load = bank.load

    def two(split):                                       # two orders per split; the plan stands in for any missing text
        scs = load(split)[:2]
        for sc in scs:
            for m in sc['messages']:
                m['text'] = m.get('text') or ' '.join(m['spec'])
        return scs
    monkeypatch.setattr(bank, 'load', two)
    monkeypatch.chdir(tmp_path)
    Budget().approve(1.85, attempt_requests=12000, confirm=True)
    monkeypatch.setattr(confirm_run, 'ROOT', tmp_path / 'data' / 'allergy')
    monkeypatch.setattr(confirm_run, 'ENDPOINT', stub['url'])
    confirm_run.main()
    out = tmp_path / 'data' / 'allergy' / 'confirm_test'
    assert (out / 'decisions.json').exists() and (out / 'responses-names-r2.json').exists()
    assert not (out / 'decisions-r2.json').exists()                          # Decisions is not repeated (§10.5)
    rep = confirm_report.repeat(tmp_path / 'data' / 'allergy', 'confirm_test')
    assert set(rep) == set(confirm_run.REPEATED) and rep['responses-options']['answers_changed']['k'] == 0
    assert confirm_report.analyse(tmp_path / 'data' / 'allergy', 'confirm_test', '-r2')['readers']['decisions']
