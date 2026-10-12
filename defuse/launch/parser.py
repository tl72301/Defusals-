"""Frozen regular-expression baseline. Written and committed before any report text existed (LAUNCH_PROTOCOL.md §6).
It reads the header (report minute, scenario start) and the text, and answers the same 9 questions."""
import re

DIGIT = {'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'tree': '3', 'four': '4', 'fower': '4', 'five': '5',
         'fife': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9', 'niner': '9'}
SPOKEN = re.compile(r'\b(' + '|'.join(DIGIT) + r')(?:[ -](' + '|'.join(DIGIT) + r'))+\b')


def normalize(text):
    t = text.lower().replace('°', ' deg ').replace('−', '-')
    t = SPOKEN.sub(lambda m: ''.join(DIGIT[w] for w in re.split(r'[ -]', m.group(0))), t)
    return t


def clock_minute(start, hhmm):
    """Simulated minute for a Zulu clock string, given the scenario start (hour, minute)."""
    h, m = int(hhmm[:2]), int(hhmm[2:4])
    base = start[0] * 60 + start[1]
    d = (h * 60 + m - base) % 1440
    return d - 1440 if d > 720 else d


CLOCK = re.compile(r'\b([01]\d|2[0-3])([0-5]\d)\s?z\b|\b([01]\d|2[0-3])([0-5]\d)\s?(?:zulu|utc)\b')


def clocks(t):
    return [(m.group(1) or m.group(3)) + (m.group(2) or m.group(4)) for m in CLOCK.finditer(t)]


def obs_time(t, minute, start):
    m = re.search(r'(?:taken|observed|measured|valid|as of|from the|reading at|ob at|observation at)[^.]{0,20}?'
                  r'\b(([01]\d|2[0-3])[0-5]\d)\s?(?:z|zulu|utc)?\b', t)
    if not m:
        m2 = re.search(r'(\d+)\s*(?:min|minutes?)\s*(?:old|ago)', t)
        if m2 and re.search(r'(relay|passing|taken|observ|reading)', t):
            age = int(m2.group(1))
        else:
            return 'current'
    else:
        age = minute - clock_minute(start, m.group(1))
    return 'current' if age <= 4 else '5-14' if age <= 14 else '15-29' if age <= 29 else '30+'


def sentences(t):
    return [s for s in re.split(r'(?<=[.;!?])\s+|\n', t) if s.strip()]


def wind(t):
    hits = []
    for s in sentences(t):
        if not re.search(r'wind|gust|kt\b|knots?|\dg\d', s):
            continue
        if re.search(r'\b54\b|54-?f(oo)?t|upper[- ]level', s) and not re.search(r'132', s):
            continue
        rng = re.search(r'(\d{1,2})\s*(?:to|-|–)\s*(\d{1,2})\s*(?:kt|knots)', s)
        if rng and _wbin(int(rng.group(1))) != _wbin(int(rng.group(2))):
            return 'unclear'
        metar = re.search(r'\b(\d{2})g(\d{2})\s*kt', s)
        if metar:
            hits.append(int(metar.group(2))); continue
        gust = re.search(r'gust(?:s|ing)?\s*(?:to\s*)?(\d{1,2})', s)
        if gust:
            hits.append(int(gust.group(1))); continue
        peak = re.search(r'peak[^0-9]{0,25}(\d{1,2})', s) or re.search(r'(\d{1,2})\s*(?:kt|knots)', s)
        if peak:
            hits.append(int(peak.group(1)))
    return _wbin(max(hits)) if hits else 'not_mentioned'


def _wbin(k):
    return 'le25' if k <= 25 else '26-27' if k <= 27 else '28-29' if k <= 29 else '30-31' if k <= 31 else '32-35' if k <= 35 else 'ge36'


def _tbin(f):
    return 'lt90' if f < 90 else '90-94.5' if f <= 94.5 else '94.6-96' if f <= 96 else 'gt96'


def temps(t):
    out = {'TEMP_LOW': 'not_mentioned', 'TEMP_HIGH': 'not_mentioned'}
    for s in sentences(t):
        if not re.search(r'temp|deg|\bf\b|fahrenheit', s):
            continue
        if re.search(r'ground', s) and not re.search(r'132|257', s):
            continue
        for level, key in (('132', 'TEMP_LOW'), ('257', 'TEMP_HIGH')):
            m = re.search(level + r'[^0-9]{0,40}?(\d{2,3}(?:\.\d)?)\s*(?:deg|f\b|fahrenheit)', s) or \
                re.search(r'(\d{2,3}(?:\.\d)?)\s*(?:deg|f\b|fahrenheit)[^0-9]{0,30}' + level, s)
            if m:
                out[key] = _tbin(float(m.group(1)))
        rng = re.search(r'(\d{2}(?:\.\d)?)\s*(?:to|-|–)\s*(\d{2}(?:\.\d)?)\s*(?:deg|f\b)', s)
        if rng and _tbin(float(rng.group(1))) != _tbin(float(rng.group(2))):
            for level, key in (('132', 'TEMP_LOW'), ('257', 'TEMP_HIGH')):
                if level in s:
                    out[key] = 'unclear'
    return out


def precip(t):
    if re.search(r'\bno (?:precip\w*|rain|showers?)\b|\bdry\b|precip\w*[^.]{0,15}\b(?:none|negative)\b', t):
        return 'no'
    if re.search(r'\b(?:rain|shower\w*|precip\w*|drizzle)\b', t):
        return 'yes'
    return 'not_mentioned'


def lightning(t, minute, start):
    if not re.search(r'lightning|strike|stroke|flash', t):
        return 'not_mentioned'
    if re.search(r'no (?:lightning|strikes?|activity)[^.]{0,40}(?:inside|within) (?:10|ten)', t) or \
            re.search(r'(?:inside|within) (?:10|ten)[^.]{0,30}(?:clear|nothing|no )', t):
        return 'clear30'
    ago = re.search(r'(\d{1,2})\s*(?:min|minutes?)\s*ago', t)
    at = re.search(r'(?:strike|stroke|flash|lightning)[^.]{0,60}?\bat\s*(([01]\d|2[0-3])[0-5]\d)\s?z?', t)
    dist = re.search(r'(\d{1,2}(?:\.\d)?)\s*(?:nm|nmi|nautical)', t)
    if dist and float(dist.group(1)) > 10 and not re.search(r'inside|within', t):
        return 'beyond10'
    age = int(ago.group(1)) if ago else (minute - clock_minute(start, at.group(1)) if at else None)
    if age is None:
        return 'unclear'
    return 'lt10' if age < 10 else '10-19' if age < 20 else '20-29' if age < 30 else 'clear30'


def fieldmill(t):
    if not re.search(r'mill|v/m|field', t):
        return 'not_mentioned'
    vals = [abs(float(x.replace(',', ''))) for x in re.findall(r'([-+]?\d[\d,]*)\s*v/m', t)]
    vals += [abs(float(x)) * 1000 for x in re.findall(r'([-+]?\d+(?:\.\d+)?)\s*kv/m', t)]
    if not vals:
        return 'lt1000' if re.search(r'mills? (?:are |is )?(?:quiet|calm|low|benign)', t) else 'unclear'
    v = max(vals)
    return 'lt1000' if v < 1000 else '1000-1499' if v < 1500 else '1500-1999' if v < 2000 else 'ge2000'


def solar(t):
    levels = [int(x) for x in re.findall(r'\b[sr]([0-5])\b', t)]
    if not levels:
        if re.search(r'no (?:solar|radiation storm|radio blackout)', t):
            return '0-2'
        return 'not_mentioned'
    v = max(levels)
    return '0-2' if v <= 2 else str(v)


def correction(t):
    return 'yes' if re.search(r'\bcorrect(?:ion|ing)\b|\bamend|\bdisregard|\bcorrected\b', t) else 'no'


def parse(text, minute, start):
    t = normalize(text)
    out = {'OBS_TIME': obs_time(t, minute, start), 'WIND': wind(t), **temps(t), 'PRECIP': precip(t),
           'LIGHTNING': lightning(t, minute, start), 'FIELDMILL': fieldmill(t), 'SOLAR': solar(t),
           'CORRECTION': correction(t)}
    return out
