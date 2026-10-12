"""Questions, options and the protocol engine (LAUNCH_PROTOCOL.md sections 3 and 4).

Every system's answers, and the answer key, go through exactly this code. The model never compares a value with a
limit, adds times or applies a waiting period: those happen here."""

WINDOW = (40, 80)                 # simulated minutes; the launch window
POLLS = list(range(WINDOW[0], WINDOW[1] + 1, 5))
FRESH = 15                        # minutes a reading stays usable after its (oldest possible) observation time
FRESH_SOLAR = 60
LIGHTNING_WAIT = 30
FIELDMILL_WAIT = 15
HEAT_MINUTES = 30
CLARIFY_DELAY = 2
CLARIFY_BUDGET = 4

MET, VIOLATED, INSUFFICIENT = 'met', 'violated', 'insufficient'
RULES = ('WIND', 'HEAT', 'PRECIP', 'LIGHTNING', 'FIELDMILL', 'SOLAR')
STATE_NAME = {MET: 'modeled criteria met', VIOLATED: 'constraint violated', INSUFFICIENT: 'evidence insufficient'}

# Observation-time bins: (oldest age, newest age) in minutes before the report time. None = expired on arrival.
OBS_AGE = {'current': (4, 0), '5-14': (14, 5), '15-29': (29, 15), '30+': None}
LIGHTNING_LATEST = {'lt10': 0, '10-19': 10, '20-29': 20}      # newest possible age of the strike, minutes


def clock(start, minute):
    """Zulu clock string for a simulated minute, e.g. start=(14, 20), minute=7 -> '1427Z'."""
    total = start[0] * 60 + start[1] + minute
    return f'{total // 60 % 24:02d}{total % 60:02d}Z'


def questions(start, report_minute):
    """The 9 questions for a report made at report_minute. Clock times in the options are computed here."""
    c = lambda m: clock(start, report_minute - m)
    rt = clock(start, report_minute)
    return [
        ('OBS_TIME', 'When were the weather observations in this report made? Use the time stated in the text; if no '
                     'time is stated, the observations are current.', [
            ('current', f'current: at the report time {rt} or up to 4 minutes before ({c(4)} to {rt}), or no time stated'),
            ('5-14', f'5 to 14 minutes before the report time ({c(14)} to {c(5)})'),
            ('15-29', f'15 to 29 minutes before the report time ({c(29)} to {c(15)})'),
            ('30+', f'30 or more minutes before the report time ({c(30)} or earlier)')]),
        ('WIND', 'What peak wind does this report give for the 132.5-foot level of the pad weather tower? Other heights '
                 'or upper-level winds do not count. Peak means the highest value, including gusts.', [
            ('not_mentioned', 'not mentioned for the 132.5-foot level'),
            ('le25', '25 knots or less'), ('26-27', '26 to 27 knots'), ('28-29', '28 to 29 knots'),
            ('30-31', '30 to 31 knots'), ('32-35', '32 to 35 knots'), ('ge36', '36 knots or more'),
            ('unclear', 'mentioned, but the value is unclear or given only as a range spanning these options')]),
        ('TEMP_LOW', 'What temperature does this report give at the 132.5-foot level?', TEMP_OPTIONS),
        ('TEMP_HIGH', 'What temperature does this report give at the 257.5-foot level?', TEMP_OPTIONS),
        ('PRECIP', 'What does this report say about precipitation at the pad or along the flight path?', [
            ('not_mentioned', 'not mentioned'),
            ('yes', 'precipitation is occurring at the pad or along the flight path'),
            ('no', 'no precipitation at the pad or along the flight path'),
            ('unclear', 'mentioned, but unclear')]),
        ('LIGHTNING', 'When was the most recent lightning within 10 nautical miles of the flight path, according to this '
                      'report?', [
            ('not_mentioned', 'lightning not mentioned'),
            ('lt10', f'less than 10 minutes before the report time (after {c(10)})'),
            ('10-19', f'10 to 19 minutes before the report time ({c(19)} to {c(10)})'),
            ('20-29', f'20 to 29 minutes before the report time ({c(29)} to {c(20)})'),
            ('clear30', f'no lightning within 10 nautical miles in the 30 minutes before the report ({c(30)} to {rt})'),
            ('beyond10', 'lightning mentioned only beyond 10 nautical miles; nothing said about within 10'),
            ('unclear', 'mentioned, but the time or distance is unclear')]),
        ('FIELDMILL', 'What is the largest field mill reading (electric field magnitude, ignoring the sign) within 5 '
                      'nautical miles of the pad, according to this report?', [
            ('not_mentioned', 'not mentioned'), ('lt1000', 'below 1,000 V/m'), ('1000-1499', '1,000 to 1,499 V/m'),
            ('1500-1999', '1,500 to 1,999 V/m'), ('ge2000', '2,000 V/m or more'), ('unclear', 'mentioned, but unclear')]),
        ('SOLAR', 'What is the highest NOAA solar radiation storm (S) or radio blackout (R) level in this report? '
                  'Geomagnetic storm (G) levels do not count.', [
            ('not_mentioned', 'no S or R level mentioned'), ('0-2', 'level 0 to 2 (none, minor or moderate)'),
            ('3', 'level 3 (strong)'), ('4', 'level 4 (severe)'), ('5', 'level 5 (extreme)'),
            ('unclear', 'mentioned, but unclear')]),
        ('CORRECTION', 'Does this report correct an earlier report?', [
            ('no', 'no'), ('yes', "yes: its values replace that source's earlier values for the same items"),
            ('unclear', 'unclear')]),
    ]


TEMP_OPTIONS = [('not_mentioned', 'not mentioned for this level'), ('lt90', 'below 90.0°F'),
                ('90-94.5', '90.0 to 94.5°F'), ('94.6-96', '94.6 to 96.0°F'), ('gt96', 'above 96.0°F'),
                ('unclear', 'mentioned, but unclear')]
QUESTION_NAMES = ['OBS_TIME', 'WIND', 'TEMP_LOW', 'TEMP_HIGH', 'PRECIP', 'LIGHTNING', 'FIELDMILL', 'SOLAR', 'CORRECTION']
INSTRUCTIONS_HEADER = ('Weather report during a modeled launch countdown (research simulation). Answer only from what '
                       'this report says.')

# Which answers violate (True) or satisfy (False) a limit. Anything else is "no reading" or "unclear".
LIMIT = {
    'WIND': {'le25': False, '26-27': False, '28-29': False, '30-31': True, '32-35': True, 'ge36': True},
    'TEMP_LOW': {'lt90': False, '90-94.5': False, '94.6-96': True, 'gt96': True},
    'TEMP_HIGH': {'lt90': False, '90-94.5': False, '94.6-96': True, 'gt96': True},
    'PRECIP': {'yes': True, 'no': False},
    'FIELDMILL': {'lt1000': False, '1000-1499': False, '1500-1999': True, 'ge2000': True},
    'SOLAR': {'0-2': False, '3': False, '4': True, '5': True},
}
ITEMS = ['WIND', 'TEMP_LOW', 'TEMP_HIGH', 'PRECIP', 'LIGHTNING', 'FIELDMILL', 'SOLAR']
SILENT = {'not_mentioned', 'beyond10'}     # answers that give no reading for the rule


def readings(reports, answers, overrides, t):
    """Usable readings at time t. reports: [{'id','source','minute'}]; answers: {id: {question: value}};
    overrides: [(arrival_minute, report_id, question, value)] from clarification answers."""
    effective = {}
    for r in reports:
        if r['minute'] <= t:
            effective[r['id']] = dict(answers[r['id']])
    for arrival, rid, q, value in overrides:
        if arrival <= t and rid in effective:
            effective[rid][q] = value
    out = []
    for r in sorted((r for r in reports if r['id'] in effective), key=lambda r: (r['minute'], r['id'])):
        a = effective[r['id']]
        age = OBS_AGE.get(a.get('OBS_TIME', 'current'), (4, 0))
        if a.get('CORRECTION') == 'yes':                  # a correction removes the source's earlier readings
            mentioned = {q for q in ITEMS if a.get(q) not in SILENT}
            out = [x for x in out if not (x['source'] == r['source'] and x['item'] in mentioned)]
        for q in ITEMS:
            v = a.get(q, 'not_mentioned')
            if v in SILENT:
                continue
            out.append({'item': q, 'value': v, 'source': r['source'], 'report': r['id'], 'minute': r['minute'],
                        'obs_old': None if age is None else r['minute'] - age[0],
                        'obs_new': None if age is None else r['minute'] - age[1]})
    return out


def _fresh(x, t):
    if x['obs_old'] is None:
        return False
    return t <= x['obs_old'] + (FRESH_SOLAR if x['item'] == 'SOLAR' else FRESH)


def _latest_per_source(rs, item, t):
    latest = {}
    for x in rs:
        if x['item'] == item and _fresh(x, t):
            latest[x['source']] = x                     # rs is in report order, so the last one wins
    return list(latest.values())


def _limit_status(rs, item, t):
    """met / violated / insufficient for a simple limit, from each source's latest fresh reading."""
    latest = _latest_per_source(rs, item, t)
    definite = [LIMIT[item][x['value']] for x in latest if x['value'] in LIMIT[item]]
    unclear = any(x['value'] not in LIMIT[item] for x in latest)
    if not definite:
        return INSUFFICIENT
    if all(definite):
        return VIOLATED
    if not any(definite) and not unclear:
        return MET
    return INSUFFICIENT


def _heat(rs, t):
    def level(item, m):
        s = _limit_status([x for x in rs if x['minute'] <= m], item, m)
        return {MET: 'within', VIOLATED: 'exceed'}.get(s, 'unknown')
    if 'unknown' in (level('TEMP_LOW', t), level('TEMP_HIGH', t)):
        return INSUFFICIENT
    minutes = [(level('TEMP_LOW', m), level('TEMP_HIGH', m)) for m in range(t - HEAT_MINUTES, t + 1)]
    if any('within' in pair for pair in minutes):      # the 30-consecutive-minute streak is broken
        return MET
    if all(pair == ('exceed', 'exceed') for pair in minutes):
        return VIOLATED
    return INSUFFICIENT


def _lightning(rs, t):
    for x in rs:
        if x['item'] == 'LIGHTNING' and x['value'] in LIGHTNING_LATEST:
            if t < x['minute'] - LIGHTNING_LATEST[x['value']] + LIGHTNING_WAIT:
                return VIOLATED
    latest = _latest_per_source(rs, 'LIGHTNING', t)
    if not latest or any(x['value'] == 'unclear' for x in latest):
        return INSUFFICIENT
    return MET


def _fieldmill(rs, t):
    for x in rs:
        if x['item'] == 'FIELDMILL' and LIMIT['FIELDMILL'].get(x['value']) and x['obs_new'] is not None:
            if t < x['obs_new'] + FIELDMILL_WAIT:
                return VIOLATED
    s = _limit_status(rs, 'FIELDMILL', t)
    return MET if s == MET else INSUFFICIENT


def rule_status(reports, answers, overrides, t):
    rs = readings(reports, answers, overrides, t)
    return {'WIND': _limit_status(rs, 'WIND', t), 'HEAT': _heat(rs, t), 'PRECIP': _limit_status(rs, 'PRECIP', t),
            'LIGHTNING': _lightning(rs, t), 'FIELDMILL': _fieldmill(rs, t), 'SOLAR': _limit_status(rs, 'SOLAR', t)}


def overall(status):
    if VIOLATED in status.values():
        return VIOLATED
    if INSUFFICIENT in status.values():
        return INSUFFICIENT
    return MET


def state(reports, answers, overrides, t):
    return overall(rule_status(reports, answers, overrides, t))
