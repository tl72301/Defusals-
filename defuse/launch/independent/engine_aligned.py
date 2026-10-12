"""Independent implementation of the LAUNCH_PROTOCOL.md rule engine (sections 3 and 4).

Standard library only. Public API:

    rule_status(reports, answers, overrides, t) -> {'WIND','HEAT','PRECIP','LIGHTNING','FIELDMILL','SOLAR': status}
    state(reports, answers, overrides, t)       -> overall status

Statuses are 'met' | 'violated' | 'insufficient'.
"""

MET = 'met'
VIOLATED = 'violated'
INSUFFICIENT = 'insufficient'

QUESTIONS = ('OBS_TIME', 'WIND', 'TEMP_LOW', 'TEMP_HIGH', 'PRECIP', 'LIGHTNING',
             'FIELDMILL', 'SOLAR', 'CORRECTION')
ITEMS = ('WIND', 'TEMP_LOW', 'TEMP_HIGH', 'PRECIP', 'LIGHTNING', 'FIELDMILL', 'SOLAR')

# OBS_TIME bin -> (oldest age, newest age) in minutes before the report time. '30+' is expired.
OBS_AGES = {
    'current': (4, 0),
    '5-14': (14, 5),
    '15-29': (29, 15),
}
EXPIRED_BIN = '30+'

FRESH_WINDOW = 15
SOLAR_FRESH_WINDOW = 60
LIGHTNING_WAIT = 30
FIELDMILL_WAIT = 15
HEAT_STREAK = 30

UNCLEAR = 'unclear'

# Answers that give no reading for the item at all.
NO_READING = {
    item: frozenset(['not_mentioned']) for item in ITEMS
}
NO_READING['LIGHTNING'] = frozenset(['not_mentioned', 'beyond10'])

# Limit-style items: (values that show a violation, values that show none).
LIMIT_SETS = {
    'WIND': (frozenset(['30-31', '32-35', 'ge36']), frozenset(['le25', '26-27', '28-29'])),
    'TEMP_LOW': (frozenset(['94.6-96', 'gt96']), frozenset(['lt90', '90-94.5'])),
    'TEMP_HIGH': (frozenset(['94.6-96', 'gt96']), frozenset(['lt90', '90-94.5'])),
    'PRECIP': (frozenset(['yes']), frozenset(['no'])),
    'SOLAR': (frozenset(['4', '5']), frozenset(['0-2', '3'])),
}

# LIGHTNING: bin -> minutes before the report time of the latest possible strike.
LIGHTNING_LATEST_OFFSET = {'lt10': 0, '10-19': 10, '20-29': 20}
LIGHTNING_DEFINITE = frozenset(['lt10', '10-19', '20-29', 'clear30'])

FIELDMILL_HIGH = frozenset(['1500-1999', 'ge2000'])
FIELDMILL_DEFINITE = frozenset(['lt1000', '1000-1499', '1500-1999', 'ge2000'])


class _Reading(object):
    __slots__ = ('key', 'minute', 'source', 'item', 'value', 'oldest_obs', 'newest_obs',
                 'expired', 'removed')

    def __init__(self, key, minute, source, item, value, oldest_obs, newest_obs, expired):
        self.key = key
        self.minute = minute
        self.source = source
        self.item = item
        self.value = value
        self.oldest_obs = oldest_obs
        self.newest_obs = newest_obs
        self.expired = expired
        self.removed = False


def _effective_answers(report, answers, overrides, t_overrides):
    """Answers for one report with every clarification that has arrived by t_overrides applied.

    Later arrivals win; equal arrivals are applied in list order (the last one wins)."""
    rid = report['id']
    eff = dict(answers.get(rid, {}))
    for q in QUESTIONS:
        eff.setdefault(q, 'not_mentioned' if q not in ('OBS_TIME', 'CORRECTION') else
                       ('current' if q == 'OBS_TIME' else 'no'))
    applicable = [(o[0], i, o) for i, o in enumerate(overrides)
                  if o[1] == rid and o[0] <= t_overrides]
    applicable.sort(key=lambda x: (x[0], x[1]))
    for _, _, (_, _, question, value) in applicable:
        eff[question] = value
    return eff


def _readings(reports, answers, overrides, t_reports, t_overrides):
    """All readings from reports with minute <= t_reports, with corrections applied."""
    existing = [r for r in reports if r['minute'] <= t_reports]
    existing.sort(key=lambda r: (r['minute'], r['id']))
    per_report = []
    readings = []
    for r in existing:
        eff = _effective_answers(r, answers, overrides, t_overrides)
        key = (r['minute'], r['id'])
        obs = eff.get('OBS_TIME')
        expired = obs not in OBS_AGES
        if expired:
            oldest_obs = newest_obs = None
        else:
            oldest_age, newest_age = OBS_AGES[obs]
            oldest_obs = r['minute'] - oldest_age
            newest_obs = r['minute'] - newest_age
        mentioned = []
        for item in ITEMS:
            value = eff.get(item, 'not_mentioned')
            if value in NO_READING[item]:
                continue
            mentioned.append(item)
            readings.append(_Reading(key, r['minute'], r['source'], item, value,
                                     oldest_obs, newest_obs, expired))
        per_report.append((key, r['source'], eff.get('CORRECTION') == 'yes', mentioned))

    # Corrections: remove the same source's readings from earlier reports for restated items.
    for key, source, is_correction, mentioned in per_report:
        if not is_correction or not mentioned:
            continue
        restated = set(mentioned)
        for rd in readings:
            if rd.source == source and rd.key < key and rd.item in restated:
                rd.removed = True
    return [rd for rd in readings if not rd.removed]


def _fresh(rd, t):
    if rd.expired:
        return False
    window = SOLAR_FRESH_WINDOW if rd.item == 'SOLAR' else FRESH_WINDOW
    return t <= rd.oldest_obs + window


def _latest_fresh_per_source(readings, item, t):
    latest = {}
    for rd in readings:
        if rd.item != item or not _fresh(rd, t):
            continue
        cur = latest.get(rd.source)
        if cur is None or rd.key > cur.key:
            latest[rd.source] = rd
    return [latest[s] for s in sorted(latest)]


def _limit_status(readings, item, t):
    viol, ok = LIMIT_SETS[item]
    values = [rd.value for rd in _latest_fresh_per_source(readings, item, t)]
    definite = [v for v in values if v != UNCLEAR and (v in viol or v in ok)]
    any_unclear = any(v not in viol and v not in ok for v in values)
    if definite and all(v in viol for v in definite):
        return VIOLATED
    if definite and all(v in ok for v in definite) and not any_unclear:
        return MET
    return INSUFFICIENT


def _heat_status(reports, answers, overrides, t):
    cache = {}

    full = _readings(reports, answers, overrides, t, t)          # ALIGNED: corrections known at t apply to the past

    def level_status(level, m):
        if m not in cache:
            cache[m] = [rd for rd in full if rd.minute <= m]
        return _limit_status(cache[m], level, m)

    levels = ('TEMP_LOW', 'TEMP_HIGH')
    if any(level_status(lv, t) == INSUFFICIENT for lv in levels):
        return INSUFFICIENT
    window = range(t - HEAT_STREAK, t + 1)                   # ALIGNED: minutes t-30..t
    statuses = [(level_status('TEMP_LOW', m), level_status('TEMP_HIGH', m)) for m in window]
    if any(lo == MET or hi == MET for lo, hi in statuses):
        return MET
    if all(lo == VIOLATED and hi == VIOLATED for lo, hi in statuses):
        return VIOLATED
    return INSUFFICIENT


def _lightning_status(readings, t):
    for rd in readings:
        if rd.item != 'LIGHTNING' or rd.expired:
            continue
        if rd.value in LIGHTNING_LATEST_OFFSET:
            latest_strike = rd.minute - LIGHTNING_LATEST_OFFSET[rd.value]
            if t < latest_strike + LIGHTNING_WAIT:
                return VIOLATED
    latest = _latest_fresh_per_source(readings, 'LIGHTNING', t)
    if any(rd.value == UNCLEAR for rd in latest):               # ALIGNED: unclear blocks met
        return INSUFFICIENT
    if any(rd.value in LIGHTNING_DEFINITE for rd in latest):
        return MET
    return INSUFFICIENT


def _fieldmill_status(readings, t):
    for rd in readings:
        if rd.item != 'FIELDMILL' or rd.expired:
            continue
        if rd.value in FIELDMILL_HIGH and t < rd.newest_obs + FIELDMILL_WAIT:
            return VIOLATED
    latest = _latest_fresh_per_source(readings, 'FIELDMILL', t)
    if any(rd.value == UNCLEAR for rd in latest):               # ALIGNED: unclear blocks met
        return INSUFFICIENT
    if any(rd.value in FIELDMILL_DEFINITE for rd in latest):
        return MET
    return INSUFFICIENT


def rule_status(reports, answers, overrides, t):
    readings = _readings(reports, answers, overrides, t, t)
    return {
        'WIND': _limit_status(readings, 'WIND', t),
        'HEAT': _heat_status(reports, answers, overrides, t),
        'PRECIP': _limit_status(readings, 'PRECIP', t),
        'LIGHTNING': _lightning_status(readings, t),
        'FIELDMILL': _fieldmill_status(readings, t),
        'SOLAR': _limit_status(readings, 'SOLAR', t),
    }


def state(reports, answers, overrides, t):
    statuses = rule_status(reports, answers, overrides, t).values()
    if any(s == VIOLATED for s in statuses):
        return VIOLATED
    if any(s == INSUFFICIENT for s in statuses):
        return INSUFFICIENT
    return MET


# --------------------------------------------------------------------------------------------
# Hand examples
# --------------------------------------------------------------------------------------------

def _ans(**kw):
    a = {q: 'not_mentioned' for q in QUESTIONS}
    a['OBS_TIME'] = 'current'
    a['CORRECTION'] = 'no'
    a.update(kw)
    return a


def _selftest():
    # 1. Single source wind reading, freshness edge (current: fresh through r+11).
    reps = [{'id': 'a', 'minute': 10, 'source': 'tower'}]
    ans = {'a': _ans(WIND='28-29')}
    assert rule_status(reps, ans, [], 9)['WIND'] == INSUFFICIENT  # report not yet exists
    assert rule_status(reps, ans, [], 10)['WIND'] == MET
    assert rule_status(reps, ans, [], 21)['WIND'] == MET
    assert rule_status(reps, ans, [], 22)['WIND'] == INSUFFICIENT
    # 5-14 bin: fresh through r+1. 15-29: never fresh.
    ans = {'a': _ans(WIND='30-31', OBS_TIME='5-14')}
    assert rule_status(reps, ans, [], 11)['WIND'] == VIOLATED
    assert rule_status(reps, ans, [], 12)['WIND'] == INSUFFICIENT
    ans = {'a': _ans(WIND='30-31', OBS_TIME='15-29')}
    assert rule_status(reps, ans, [], 10)['WIND'] == INSUFFICIENT

    # 2. Disagreement between sources -> insufficient; unclear does not block violation.
    reps = [{'id': 'a', 'minute': 10, 'source': 'tower'},
            {'id': 'b', 'minute': 12, 'source': 'lwo'}]
    ans = {'a': _ans(WIND='le25'), 'b': _ans(WIND='32-35')}
    assert rule_status(reps, ans, [], 12)['WIND'] == INSUFFICIENT
    ans = {'a': _ans(WIND='unclear'), 'b': _ans(WIND='32-35')}
    assert rule_status(reps, ans, [], 12)['WIND'] == VIOLATED
    ans = {'a': _ans(WIND='unclear'), 'b': _ans(WIND='le25')}
    assert rule_status(reps, ans, [], 12)['WIND'] == INSUFFICIENT
    # Clarification at minute 14 resolves 'unclear'.
    ov = [(14, 'a', 'WIND', '26-27')]
    assert rule_status(reps, ans, ov, 13)['WIND'] == INSUFFICIENT
    assert rule_status(reps, ans, ov, 14)['WIND'] == MET

    # 3. Same source: latest fresh reading wins; correction removes earlier readings.
    reps = [{'id': 'a', 'minute': 10, 'source': 'tower'},
            {'id': 'b', 'minute': 15, 'source': 'tower'}]
    ans = {'a': _ans(FIELDMILL='ge2000'), 'b': _ans(FIELDMILL='lt1000')}
    st = rule_status(reps, ans, [], 15)
    assert st['FIELDMILL'] == VIOLATED            # waiting from a until 25
    assert rule_status(reps, ans, [], 25)['FIELDMILL'] == MET
    ans['b']['CORRECTION'] = 'yes'
    assert rule_status(reps, ans, [], 15)['FIELDMILL'] == MET

    # 4. Lightning waiting uses the latest possible strike time, not freshness.
    reps = [{'id': 'L', 'minute': 20, 'source': 'lightning'}]
    ans = {'L': _ans(LIGHTNING='10-19')}
    assert rule_status(reps, ans, [], 39)['LIGHTNING'] == VIOLATED
    assert rule_status(reps, ans, [], 40)['LIGHTNING'] == INSUFFICIENT  # no longer fresh (> 31)
    ans = {'L': _ans(LIGHTNING='20-29')}
    assert rule_status(reps, ans, [], 29)['LIGHTNING'] == VIOLATED
    assert rule_status(reps, ans, [], 30)['LIGHTNING'] == MET  # fresh through 31
    assert rule_status(reps, ans, [], 32)['LIGHTNING'] == INSUFFICIENT
    ans = {'L': _ans(LIGHTNING='beyond10')}
    assert rule_status(reps, ans, [], 20)['LIGHTNING'] == INSUFFICIENT
    ans = {'L': _ans(LIGHTNING='clear30')}
    assert rule_status(reps, ans, [], 20)['LIGHTNING'] == MET

    # 5. Solar freshness 60 minutes.
    reps = [{'id': 's', 'minute': 0, 'source': 'swx'}]
    ans = {'s': _ans(SOLAR='3')}
    assert rule_status(reps, ans, [], 56)['SOLAR'] == MET
    assert rule_status(reps, ans, [], 57)['SOLAR'] == INSUFFICIENT

    # 6. HEAT: tower reports every 10 minutes, both levels.
    reps = [{'id': 't%02d' % m, 'minute': m, 'source': 'tower'} for m in range(0, 81, 10)]
    hot = {r['id']: _ans(TEMP_LOW='gt96', TEMP_HIGH='94.6-96') for r in reps}
    # Before 29 minutes of known exceedance -> insufficient; from t=29 onward violated.
    assert rule_status(reps, hot, [], 28)['HEAT'] == INSUFFICIENT
    assert rule_status(reps, hot, [], 29)['HEAT'] == VIOLATED
    assert rule_status(reps, hot, [], 60)['HEAT'] == VIOLATED
    # One cool reading at 40 at the low level -> met until it leaves the 30-minute window.
    mixed = dict(hot)
    mixed['t40'] = _ans(TEMP_LOW='90-94.5', TEMP_HIGH='gt96')
    assert rule_status(reps, mixed, [], 45)['HEAT'] == MET
    # t40 within window for m in [40, 49] (t50 replaces it as the latest fresh at 50).
    assert rule_status(reps, mixed, [], 78)['HEAT'] == MET    # window 49..78 includes 49
    assert rule_status(reps, mixed, [], 79)['HEAT'] == VIOLATED
    # Gap in reporting -> unknown minutes -> insufficient.
    gap = [r for r in reps if r['minute'] != 30]
    assert rule_status(gap, hot, [], 45)['HEAT'] == INSUFFICIENT
    # Missing current status for one level -> insufficient even if the other is cool.
    one = {r['id']: _ans(TEMP_LOW='lt90') for r in reps}
    assert rule_status(reps, one, [], 45)['HEAT'] == INSUFFICIENT

    # 7. Overall state.
    reps = [{'id': 'r', 'minute': 40, 'source': 'lwo'},
            {'id': 'h', 'minute': 20, 'source': 'tower'}]
    ans = {'h': _ans(TEMP_LOW='lt90', TEMP_HIGH='lt90'),
           'r': _ans(WIND='le25', TEMP_LOW='lt90', TEMP_HIGH='lt90', PRECIP='no',
                     LIGHTNING='clear30', FIELDMILL='lt1000', SOLAR='0-2')}
    assert state(reps, ans, [], 40) == MET, rule_status(reps, ans, [], 40)
    ans['r']['PRECIP'] = 'yes'
    assert state(reps, ans, [], 40) == VIOLATED
    ans['r']['PRECIP'] = 'unclear'
    assert state(reps, ans, [], 40) == INSUFFICIENT
    print('self-test ok')


if __name__ == '__main__':
    _selftest()
