"""Scenario generator: hidden weather, report plans (what each report must say, how, and with which trap), the answer
key derived from each plan, templated clarification answers, and the true state used for diagnostics only.

Reports' free text is written later by a separate author agent from the plans' "spec" lines. The plan, not the text,
defines the correct answers; a blind reviewer checks that the text conveys exactly the plan (LAUNCH_PROTOCOL.md §5)."""
import json
import random
from pathlib import Path
from defuse.launch.rules import (WINDOW, LIGHTNING_WAIT, FIELDMILL_WAIT, HEAT_MINUTES, MET, VIOLATED, clock)

MINUTES = WINDOW[1]
SOURCES = {'LWO': 'Launch Weather Officer', 'TOWER': 'Pad weather tower operator', 'LIGHTNING': 'Lightning officer',
           'RADAR': 'Radar and pad observer', 'SPACEWX': 'Space weather desk'}
PROFILES = ['gusty', 'storm', 'heat', 'solar', 'quiet', 'mixed']
TRAPS = ['vague', 'stale_stated', 'stale_unstated', 'correction', 'irrelevant_level', 'near_threshold', 'format',
         'clock_time']


# ---------- answer bins from true values ----------
def wind_bin(k):
    return 'le25' if k <= 25 else '26-27' if k <= 27 else '28-29' if k <= 29 else '30-31' if k <= 31 else '32-35' if k <= 35 else 'ge36'


def temp_bin(f):
    return 'lt90' if f < 90 else '90-94.5' if f <= 94.5 else '94.6-96' if f <= 96 else 'gt96'


def mill_bin(v):
    a = abs(v)
    return 'lt1000' if a < 1000 else '1000-1499' if a < 1500 else '1500-1999' if a < 2000 else 'ge2000'


def solar_bin(level):
    return '0-2' if level <= 2 else str(level)


def age_bin(age):
    return 'current' if age <= 4 else '5-14' if age <= 14 else '15-29' if age <= 29 else '30+'


def lightning_bin(age):
    return 'lt10' if age < 10 else '10-19' if age < 20 else '20-29' if age < 30 else 'clear30'


# ---------- hidden weather ----------
def weather(r, profile):
    w = {'wind': [], 'temp_low': [], 'temp_high': [], 'precip': [], 'mill': [], 'solar': []}
    base, drift = r.uniform(13, 21), 0.0
    gust_on = sorted(r.sample(range(10, 75), 2)) if profile in ('gusty', 'mixed') else None
    hot = profile == 'heat'
    t0 = r.uniform(91.5, 93.5) if hot else r.uniform(80, 88)
    heat_peak = (r.randint(5, 25), r.randint(50, 75))
    storm = profile in ('storm', 'mixed')
    storm_mid = r.randint(15, 45)
    shower = (storm_mid - r.randint(3, 8), storm_mid + r.randint(4, 12)) if storm and r.random() < 0.8 else None
    solar_event = sorted(r.sample(range(15, 75), 2)) if profile == 'solar' else None
    quiet_solar = r.choice([0, 0, 1, 2]) if profile != 'solar' else r.choice([1, 2])
    for m in range(MINUTES + 1):
        drift = max(-4, min(4, drift + r.uniform(-0.8, 0.8)))
        k = base + drift
        if gust_on and gust_on[0] <= m <= gust_on[1]:
            k = r.uniform(27, 34)
        w['wind'].append(int(round(k)))
        if hot:
            rise = 2.6 if heat_peak[0] <= m <= heat_peak[1] else 0.0
            lo = t0 + rise + r.uniform(-0.25, 0.25)
            w['temp_low'].append(round(lo, 1))
            w['temp_high'].append(round(lo - r.uniform(0.0, 0.6), 1))
        else:
            lo = t0 + r.uniform(-0.4, 0.4)
            w['temp_low'].append(round(lo, 1))
            w['temp_high'].append(round(lo - r.uniform(0.5, 1.5), 1))
        w['precip'].append(bool(shower and shower[0] <= m <= shower[1]))
        near = storm and abs(m - storm_mid) <= 10
        mag = r.uniform(1500, 2600) if near and r.random() < 0.7 else r.uniform(80, 900)
        w['mill'].append(int(round(mag * (-1 if r.random() < 0.35 else 1), -1)))
        w['solar'].append(4 if solar_event and solar_event[0] <= m <= solar_event[1] else quiet_solar)
    strikes = []
    if storm:
        for m in range(max(0, storm_mid - 12), min(MINUTES, storm_mid + 12)):
            if r.random() < 0.18:
                strikes.append([m, round(r.uniform(4, 16), 1)])
    if profile == 'mixed':                                  # distant activity only
        strikes = [[m, max(d, 12.5)] for m, d in strikes]
    return w, strikes


def true_state(w, strikes, t):
    """Rules applied to exact hidden values (diagnostics only; never the scoring reference)."""
    status = {
        'WIND': w['wind'][t] > 29,
        'HEAT': all(w['temp_low'][m] > 94.5 and w['temp_high'][m] > 94.5 for m in range(max(0, t - HEAT_MINUTES), t + 1)) and t >= HEAT_MINUTES,
        'PRECIP': w['precip'][t],
        'LIGHTNING': any(d <= 10 and t - LIGHTNING_WAIT < m <= t for m, d in strikes),
        'FIELDMILL': any(abs(w['mill'][m]) >= 1500 for m in range(max(0, t - FIELDMILL_WAIT + 1), t + 1)),
        'SOLAR': w['solar'][t] >= 4,
    }
    return VIOLATED if any(status.values()) else MET, status


def last_strike_within(strikes, m):
    within = [s for s, d in strikes if d <= 10 and s <= m]
    return max(within) if within else None


# ---------- report plans ----------
def item_facts(w, strikes, m, items, r, style, used=None):
    """Plan entries (answer + spec line) for the items a report mentions, observed at minute m. Styles actually
    applied are added to `used`."""
    used = set() if used is None else used
    facts = {}
    for item in items:
        if item == 'WIND':
            k = w['wind'][m]
            if style.get('format') and r.random() < 0.5:
                sustained = max(8, k - r.randint(4, 9))
                spec = f'peak wind at the 132.5-ft level: sustained {sustained} kt gusting {k} kt, written METAR-style (e.g. {sustained:02d}G{k:02d}KT)'
                used.add('format')
            elif style.get('format'):
                used.add('format')
                spec = f'peak wind at the 132.5-ft level {k} kt, with the number spoken digit by digit in radio style (e.g. "two-niner" for 29)'
            else:
                spec = f'peak wind at the 132.5-ft level {k} kt'
            facts['WIND'] = (wind_bin(k), spec)
        elif item in ('TEMP_LOW', 'TEMP_HIGH'):
            f = w['temp_low' if item == 'TEMP_LOW' else 'temp_high'][m]
            level = '132.5-ft' if item == 'TEMP_LOW' else '257.5-ft'
            facts[item] = (temp_bin(f), f'temperature at the {level} level {f:.1f} °F')
        elif item == 'PRECIP':
            facts['PRECIP'] = ('yes' if w['precip'][m] else 'no',
                               'precipitation (rain shower) at the pad or along the flight path' if w['precip'][m]
                               else 'no precipitation at the pad or along the flight path')
        elif item == 'LIGHTNING':
            last = last_strike_within(strikes, m)
            if last is None or m - last >= 30:
                far = [s for s, d in strikes if d > 10 and m - 30 < s <= m]
                spec = 'no lightning within 10 nautical miles of the flight path in the last 30 minutes'
                if last is not None:
                    spec += f' (the last strike within 10 nmi was at {{clock:{last}}}, {m - last} minutes ago)'
                elif far and r.random() < 0.5:
                    spec += ' (there is lightning farther out, beyond 10 nmi)'
                facts['LIGHTNING'] = ('clear30', spec)
            else:
                dist = next(d for s, d in strikes if s == last and d <= 10)
                when = f'at {{clock:{last}}}' if style.get('clock_time') else f'{m - last} minutes ago'
                if style.get('clock_time'):
                    used.add('clock_time')
                facts['LIGHTNING'] = (lightning_bin(m - last), f'most recent lightning strike within 10 nautical miles of the flight path was {when}, {dist} nmi from the flight path')
        elif item == 'FIELDMILL':
            v = w['mill'][m]
            spec = f'largest field mill reading within 5 nmi of the pad {v:+d} V/m'
            if style.get('format') and abs(v) >= 1000 and r.random() < 0.5:
                spec = f'largest field mill reading within 5 nmi of the pad {v / 1000:+.2f} kV/m (write it in kV/m)'
                used.add('format')
            facts['FIELDMILL'] = (mill_bin(v), spec)
        elif item == 'SOLAR':
            level = w['solar'][m]
            scale = r.choice(['S', 'R'])
            names = {0: 'none', 1: 'minor', 2: 'moderate', 3: 'strong', 4: 'severe', 5: 'extreme'}
            spec = (f'NOAA {scale}{level} ({names[level]}) {"solar radiation storm" if scale == "S" else "radio blackout"} conditions'
                    if level else 'no solar radiation storm or radio blackout in progress (NOAA S0/R0)')
            facts['SOLAR'] = (solar_bin(level), spec)
    return facts


def blank_answers():
    return {'OBS_TIME': 'current', 'WIND': 'not_mentioned', 'TEMP_LOW': 'not_mentioned', 'TEMP_HIGH': 'not_mentioned',
            'PRECIP': 'not_mentioned', 'LIGHTNING': 'not_mentioned', 'FIELDMILL': 'not_mentioned',
            'SOLAR': 'not_mentioned', 'CORRECTION': 'no'}


def make_report(rid, minute, source, facts, obs_minute, time_stated, tags, extra_spec=(), correction=False):
    answers = blank_answers()
    spec = []
    for q, (ans, line) in facts.items():
        answers[q] = ans
        spec.append(line)
    if time_stated and obs_minute != minute:
        answers['OBS_TIME'] = age_bin(minute - obs_minute)
        spec.insert(0, f'these observations were taken at {{clock:{obs_minute}}} (say so explicitly)')
    elif obs_minute != minute:
        spec.insert(0, 'do NOT say when these observations were taken; give them as if current')
    if correction:
        answers['CORRECTION'] = 'yes'
        spec.insert(0, 'this is a correction of this source\'s earlier report; say so')
    spec += list(extra_spec)
    return {'id': rid, 'minute': minute, 'source': source, 'obs_minute': obs_minute, 'answers': answers,
            'spec': spec, 'tags': sorted(set(tags)), 'true_obs': {q: facts[q][0] for q in facts}}


def scenario(seed, split):
    r = random.Random(f'launch:{seed}')
    profile = PROFILES[seed % len(PROFILES)]
    w, strikes = weather(r, profile)
    start = (r.randint(12, 19), r.choice([0, 10, 20, 30, 40, 50]))
    reports, n = [], 0

    def rid():
        nonlocal n
        n += 1
        return f'L{seed}-{n:02d}'

    focus = {'gusty': ['WIND'], 'storm': ['LIGHTNING', 'FIELDMILL', 'PRECIP'], 'heat': ['TEMP_LOW', 'TEMP_HIGH'],
             'solar': ['SOLAR'], 'quiet': ['WIND', 'TEMP_LOW'], 'mixed': ['WIND', 'LIGHTNING', 'SOLAR']}[profile]
    # Roll-ups every 10 minutes from the Launch Weather Officer.
    for m in range(0, MINUTES + 1, 10):
        items = [i for i in ['WIND', 'TEMP', 'PRECIP', 'LIGHTNING', 'FIELDMILL']
                 if i in focus or (i == 'TEMP' and {'TEMP_LOW', 'TEMP_HIGH'} & set(focus)) or r.random() < 0.93]
        items = [x for i in items for x in (['TEMP_LOW', 'TEMP_HIGH'] if i == 'TEMP' else [i])]
        if m in (0, 40) or 'SOLAR' in focus:
            items.append('SOLAR')
        style = {'format': r.random() < 0.3, 'clock_time': r.random() < 0.4}
        used = set()
        facts = item_facts(w, strikes, m, items, r, style, used)
        tags = ['rollup'] + sorted(used)
        reports.append(make_report(rid(), m, 'LWO', facts, m, False, tags))
    # Interim reports from the specialist desks, focused on the profile.
    desk = {'WIND': 'TOWER', 'TEMP_LOW': 'TOWER', 'TEMP_HIGH': 'TOWER', 'PRECIP': 'RADAR', 'LIGHTNING': 'LIGHTNING',
            'FIELDMILL': 'LIGHTNING', 'SOLAR': 'SPACEWX'}
    for m in sorted(r.sample([x for x in range(3, MINUTES) if x % 10], 5)):
        item = r.choice(focus)
        items = [i for i in desk if desk[i] == desk[item] and (i == item or r.random() < 0.6)]
        style = {'format': r.random() < 0.5, 'clock_time': r.random() < 0.5}
        used = set()
        facts = item_facts(w, strikes, m, items, r, style, used)
        tags = ['interim'] + sorted(used)
        if any(i in ('WIND', 'TEMP_LOW', 'TEMP_HIGH') and abs(_margin(w, i, m)) <= 1.0 for i in items) or \
                ('FIELDMILL' in items and 1300 <= abs(w['mill'][m]) <= 1700):
            tags.append('near_threshold')
        reports.append(make_report(rid(), m, desk[item], facts, m, False, tags))
    traps = r.sample(['vague', 'stale_stated', 'stale_unstated', 'correction', 'irrelevant_level'], 3)
    for trap in traps:
        reports += plant(trap, r, w, strikes, focus, desk, rid)
    reports.sort(key=lambda x: (x['minute'], x['id']))
    for i, rep in enumerate(reports):                       # stable ids in time order
        rep['id'] = f'L{seed}-{i + 1:02d}'
    return {'id': f'L{seed}', 'seed': seed, 'split': split, 'profile': profile, 'start': list(start),
            'weather': w, 'strikes': strikes, 'traps': traps, 'reports': reports}


def _margin(w, item, m):
    if item == 'WIND':
        return w['wind'][m] - 29.5
    return w['temp_low' if item == 'TEMP_LOW' else 'temp_high'][m] - 94.55


def plant(trap, r, w, strikes, focus, desk, rid):
    m = r.randint(30, 74)                                   # traps land just before or inside the window
    allowed = ('WIND', 'TEMP_LOW', 'TEMP_HIGH', 'FIELDMILL', 'SOLAR') if trap == 'vague' else \
        ('WIND', 'TEMP_LOW', 'TEMP_HIGH', 'PRECIP', 'FIELDMILL', 'SOLAR')
    item = r.choice([i for i in focus if i in allowed] or ['WIND'])
    if trap == 'vague':
        true_facts = item_facts(w, strikes, m, [item], r, {})
        lo, hi = _vague_range(item, w, m)
        rep = make_report(rid(), m, desk[item], {item: ('unclear', f'{_item_name(item)} given only vaguely as "{lo} to {hi}" (a range; do not give a single value)')},
                          m, False, ['vague'])
        rep['true_obs'] = {item: true_facts[item][0]}
        return [rep]
    if trap in ('stale_stated', 'stale_unstated'):
        age = r.randint(16, 26)
        obs = max(0, m - age)
        facts = item_facts(w, strikes, obs, [item], r, {})
        rep = make_report(rid(), m, 'LWO', facts, obs, trap == 'stale_stated', [trap, 'relay'],
                          extra_spec=['phrase it as relaying another desk\'s reading'])
        return [rep]
    if trap == 'correction':
        facts = item_facts(w, strikes, m, [item], r, {})
        wrong = _wrong_value(item, w, m, r)
        first = make_report(rid(), m, desk[item], {item: wrong}, m, False, ['corrected_later'])
        first['true_obs'] = {item: facts[item][0]}
        fix_at = min(MINUTES, m + r.randint(2, 5))
        second = make_report(rid(), fix_at, desk[item], facts, m, True, ['correction'],
                             extra_spec=[f'it corrects the value given at {{clock:{m}}}'], correction=True)
        return [first, second]
    if trap == 'irrelevant_level':
        options = [
            ('WIND', f'wind at the 54-ft level {w["wind"][m] + r.randint(3, 8)} kt (a different height; say "54-foot")'),
            ('WIND', 'upper-level winds are within limits (do not give any tower wind)'),
            ('TEMP_LOW', f'ground-level temperature {w["temp_low"][m] + 2.4:.1f} °F (say "at ground level")'),
            ('SOLAR', f'a G{r.choice([3, 4])} geomagnetic storm watch (say "geomagnetic", G scale only; no S or R level)'),
        ]
        _, line = r.choice(options)
        return [make_report(rid(), m, 'LWO', {}, m, False, ['irrelevant_level'], extra_spec=[line])]
    return []


def _item_name(item):
    return {'WIND': 'peak wind at the 132.5-ft level (kt)', 'TEMP_LOW': 'temperature at the 132.5-ft level (°F)',
            'TEMP_HIGH': 'temperature at the 257.5-ft level (°F)', 'PRECIP': 'precipitation',
            'FIELDMILL': 'largest field mill reading within 5 nmi (V/m)', 'SOLAR': 'NOAA S/R level'}[item]


def _vague_range(item, w, m):
    if item == 'WIND':
        return 27, 32
    if item in ('TEMP_LOW', 'TEMP_HIGH'):
        return 93.5, 95.5
    if item == 'FIELDMILL':
        return 1200, 1800
    if item == 'SOLAR':
        return 'S3', 'S4'
    return 'light', 'none'


def _wrong_value(item, w, m, r):
    """What the source mistakenly said first: a value on the other side of the limit when possible."""
    if item == 'WIND':
        k = w['wind'][m]
        v = k - 10 if k > 29 else k + 10
        return wind_bin(v), f'peak wind at the 132.5-ft level {v} kt'
    if item in ('TEMP_LOW', 'TEMP_HIGH'):
        f = w['temp_low' if item == 'TEMP_LOW' else 'temp_high'][m]
        v = f - 4 if f > 94.5 else f + 3
        level = '132.5-ft' if item == 'TEMP_LOW' else '257.5-ft'
        return temp_bin(v), f'temperature at the {level} level {v:.1f} °F'
    if item == 'FIELDMILL':
        v = w['mill'][m]
        v2 = 600 if abs(v) >= 1500 else 1800
        return mill_bin(v2), f'largest field mill reading within 5 nmi of the pad {v2:+d} V/m'
    if item == 'SOLAR':
        level = w['solar'][m]
        v = 1 if level >= 4 else 4
        return solar_bin(v), f'NOAA S{v} solar radiation storm conditions'
    return ('yes', 'precipitation at the pad') if not w['precip'][m] else ('no', 'no precipitation at the pad')


# ---------- clarification answers (fixed templates) ----------
ITEM_PHRASE = {
    'WIND': lambda v: f'peak wind at the 132.5-foot level was {v} knots',
    'TEMP_LOW': lambda v: f'temperature at the 132.5-foot level was {v:.1f} degrees Fahrenheit',
    'TEMP_HIGH': lambda v: f'temperature at the 257.5-foot level was {v:.1f} degrees Fahrenheit',
    'FIELDMILL': lambda v: f'largest field mill reading within 5 nautical miles was {v:+d} volts per meter',
}


def clarification(sc, report, question):
    """(text, correct answer for the asked question). Restates only what this source observed for this item."""
    start, m, obs = sc['start'], report['minute'], report['obs_minute']
    head = f'Say-again response to your question about the {SOURCES[report["source"]]} report sent at {clock(start, m)}: '
    if question == 'OBS_TIME':
        return head + f'those observations were taken at {clock(start, obs)}.', age_bin(m - obs)
    if question == 'CORRECTION':
        ans = report['answers']['CORRECTION']
        return head + ('yes, that report was a correction.' if ans == 'yes' else 'no, that report was not a correction.'), ans
    mentioned = report['answers'][question] != 'not_mentioned' or question in report.get('true_obs', {})
    if not mentioned:
        return head + 'that report had no information on that item.', 'not_mentioned'
    w = sc['weather']
    if 'corrected_later' in report['tags']:                # the source restates what it said at the time
        return head + 'I say again, ' + report['spec'][0] + '.', report['answers'][question]
    if question in ITEM_PHRASE:
        key = {'WIND': 'wind', 'TEMP_LOW': 'temp_low', 'TEMP_HIGH': 'temp_high', 'FIELDMILL': 'mill'}[question]
        v = w[key][obs]
        ans = {'WIND': wind_bin, 'TEMP_LOW': temp_bin, 'TEMP_HIGH': temp_bin, 'FIELDMILL': mill_bin}[question](v)
        return head + ITEM_PHRASE[question](v) + '.', ans
    if question == 'PRECIP':
        p = w['precip'][obs]
        return head + ('precipitation was occurring at the pad.' if p else 'there was no precipitation at the pad or along the flight path.'), 'yes' if p else 'no'
    if question == 'SOLAR':
        level = w['solar'][obs]
        return head + (f'NOAA solar radiation storm level S{level}.' if level else 'no solar radiation storm or radio blackout, S0 and R0.'), solar_bin(level)
    if question == 'LIGHTNING':
        last = last_strike_within(sc['strikes'], obs)
        if last is None or m - last >= 30:
            return head + 'no lightning within 10 nautical miles of the flight path in the 30 minutes before that report.', 'clear30'
        return head + f'the most recent strike within 10 nautical miles of the flight path was at {clock(start, last)}.', lightning_bin(m - last)
    raise ValueError(question)


def resolve_spec(sc, report):
    """Spec lines with {clock:N} placeholders filled in."""
    import re
    return [re.sub(r'\{clock:(\d+)\}', lambda x: clock(sc['start'], int(x.group(1))), s) for s in report['spec']]


def build(seeds, split, out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    scenarios = [scenario(s, split) for s in seeds]
    (out / f'{split}_scenarios.json').write_text(json.dumps(scenarios, indent=1))
    return scenarios
