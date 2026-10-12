from defuse.launch import rules, sim, parser
from defuse.launch.rules import MET, VIOLATED, INSUFFICIENT

START = (14, 0)


def rep(rid, minute, source='LWO'):
    return {'id': rid, 'minute': minute, 'source': source}


def ans(**kw):
    a = sim.blank_answers()
    a.update(kw)
    return a


def full(minute, **kw):
    """A report that gives every item a safe value."""
    base = dict(WIND='le25', TEMP_LOW='lt90', TEMP_HIGH='lt90', PRECIP='no', LIGHTNING='clear30', FIELDMILL='lt1000',
                SOLAR='0-2')
    base.update(kw)
    return ans(**base)


def test_all_clear_then_freshness_expires():
    reps = [rep('a', 40)]
    a = {'a': full(40)}
    assert rules.state(reps, a, [], 40) == MET
    assert rules.state(reps, a, [], 51) == MET          # current: oldest obs 36, fresh until 51
    assert rules.state(reps, a, [], 52) == INSUFFICIENT


def test_wind_limit_conflict_and_unclear():
    reps = [rep('a', 40), rep('b', 41, 'TOWER')]
    assert rules.rule_status(reps, {'a': full(40), 'b': ans(WIND='30-31')}, [], 42)['WIND'] == INSUFFICIENT   # conflict
    assert rules.rule_status(reps, {'a': full(40, WIND='32-35'), 'b': ans(WIND='30-31')}, [], 42)['WIND'] == VIOLATED
    assert rules.rule_status(reps, {'a': full(40), 'b': ans(WIND='unclear')}, [], 42)['WIND'] == INSUFFICIENT


def test_correction_replaces_same_source_only():
    reps = [rep('a', 40, 'TOWER'), rep('b', 43, 'TOWER')]
    a = {'a': full(40, WIND='30-31'), 'b': ans(WIND='28-29', CORRECTION='yes')}
    assert rules.rule_status(reps, a, [], 42)['WIND'] == VIOLATED
    assert rules.rule_status(reps, a, [], 44)['WIND'] == MET


def test_stale_relay_is_not_current_and_clarification_overrides():
    reps = [rep('a', 40), rep('b', 45, 'TOWER')]
    a = {'a': full(40), 'b': ans(WIND='30-31', OBS_TIME='current')}
    assert rules.rule_status(reps, a, [], 46)['WIND'] == INSUFFICIENT          # conflict with the roll-up
    over = [(48, 'b', 'OBS_TIME', '15-29')]                                   # say-again: it was 20 minutes old
    assert rules.rule_status(reps, a, over, 47)['WIND'] == INSUFFICIENT       # answer not arrived yet
    assert rules.rule_status(reps, a, over, 48)['WIND'] == MET


def test_lightning_wait_uses_latest_possible_strike_time():
    reps = [rep('a', 40), rep('b', 50)]
    a = {'a': full(40, LIGHTNING='10-19'), 'b': full(50)}
    # strike at the latest 40 - 10 = 30, so wait until 60
    assert rules.rule_status(reps, a, [], 59)['LIGHTNING'] == VIOLATED
    assert rules.rule_status(reps, a, [], 60)['LIGHTNING'] == MET


def test_fieldmill_hold_fifteen_minutes():
    reps = [rep('a', 40), rep('b', 50), rep('c', 60)]
    a = {'a': full(40, FIELDMILL='1500-1999'), 'b': full(50), 'c': full(60)}
    assert rules.rule_status(reps, a, [], 54)['FIELDMILL'] == VIOLATED
    assert rules.rule_status(reps, a, [], 55)['FIELDMILL'] == MET


def test_heat_needs_thirty_consecutive_minutes_at_both_levels():
    reps = [rep(f'r{m}', m) for m in range(0, 81, 10)]
    hot = {f'r{m}': full(m, TEMP_LOW='94.6-96', TEMP_HIGH='94.6-96') for m in range(0, 81, 10)}
    assert rules.rule_status(reps, hot, [], 40)['HEAT'] == VIOLATED
    hot['r30'] = full(30, TEMP_LOW='94.6-96', TEMP_HIGH='90-94.5')           # the streak breaks at 30
    assert rules.rule_status(reps, hot, [], 50)['HEAT'] == MET
    assert rules.rule_status(reps, hot, [], 61)['HEAT'] == MET              # 26..61 still includes minute 30..40 readings
    assert rules.rule_status(reps, hot, [], 75)['HEAT'] == VIOLATED


def test_generated_answer_keys_are_valid_and_clarifications_answer_in_options():
    for seed in range(1001, 1013):
        sc = sim.scenario(seed, 'dev')
        for r in sc['reports']:
            opts = {q: {v for v, _ in o} for q, _, o in rules.questions(sc['start'], r['minute'])}
            assert set(r['answers']) == set(rules.QUESTION_NAMES)
            assert all(r['answers'][q] in opts[q] for q in r['answers'])
            assert r['spec'], r
            for q in rules.QUESTION_NAMES:
                text, a = sim.clarification(sc, r, q)
                assert a in opts[q] and text.startswith('Say-again')
        for t in rules.POLLS:
            assert sim.true_state(sc['weather'], sc['strikes'], t)[0] in (MET, VIOLATED)


def test_parser_on_handwritten_examples():
    p = lambda s, minute=20: parser.parse(s, minute, START)
    assert p('Tower: peak two-niner knots at one-three-two-point-five.')['WIND'] == '28-29'
    assert p('Winds 24G31KT at the 132.5 ft level.')['WIND'] == '30-31'
    assert p('54-foot wind 33 kt.')['WIND'] == 'not_mentioned'
    assert p('Mills reading -1,620 V/m within 5.')['FIELDMILL'] == '1500-1999'
    assert p('Last strike inside ten was 12 minutes ago.')['LIGHTNING'] == '10-19'
    assert p('Space weather: S4 severe radiation storm.')['SOLAR'] == '4'
    assert p('G4 geomagnetic storm watch.')['SOLAR'] == 'not_mentioned'
    assert p('Correction to my last: peak 27 knots.')['CORRECTION'] == 'yes'
    assert p('Relaying tower ob taken at 1402Z: peak 22 kt.')['OBS_TIME'] == '15-29'
