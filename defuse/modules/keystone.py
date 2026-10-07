"""Dependent integer chains, with an oracle trace kept out of model input."""
import math

RULES = {
    'DIGIT_TIDE': 'Add the sum of all serial digits to x.',
    'LAMP_FOLD': 'If any indicator is lit, replace x with 2*x+1; otherwise replace x with x+7.',
    'CELL_TAX': 'Subtract battery count times (port count + 1) from x.',
    'KEY_FEED': 'Add the number on the key at position 1+(x modulo 4) to x.',
    'PRIME_TURN': 'If the key at position 1+(x modulo 4) has a prime number, add 1 to x; otherwise add 3.',
    'PORT_WEAVE': 'Replace x with 3*x + port count.',
    'NOVA_MIRROR': 'If NOVA is lit, replace x with 99-x; otherwise add 11 to x.',
    'ODD_ANCHOR': 'If x is odd, add battery count + 2; otherwise add the final serial digit + 1.',
    'HIGH_KEY': 'Add the largest key number minus the smallest key number to x.',
    'RAY_SWITCH': 'If RAY is lit, replace x with 5*x+2; otherwise replace x with 2*x+5.',
    'DIGIT_FLIP': 'Reverse the three decimal digits of x, including leading zeros, and interpret the result as an integer.',
    'VOWEL_LIFT': 'If the serial contains A, E, I, O or U, add 13 to x; otherwise subtract 9.',
    'FIBER_FORK': 'If a fiber port is present, replace x with 2*x+3; otherwise replace x with x+6.',
    'KEY_GAP': 'Add the absolute difference between key 1 and key 4 to x.',
    'QUARTER_ECHO': 'Replace x with floor(x/4) + 3*(x modulo 4) + 1.',
    'LAMP_COUNT': 'Add 7 times the number of lit indicators, then subtract the number of unlit indicators.',
}


def is_prime(value):
    return value >= 2 and all(value % d for d in range(2, math.isqrt(value)+1))


def apply_step(rule, x, keys, edge):
    digits = [int(c) for c in edge['serial'] if c.isdigit()]
    lights = edge['indicators']
    ports, batteries = edge['ports'], edge['batteries']
    if rule == 'DIGIT_TIDE': value = x + sum(digits)
    elif rule == 'LAMP_FOLD': value = 2*x+1 if any(lights.values()) else x+7
    elif rule == 'CELL_TAX': value = x-batteries*(len(ports)+1)
    elif rule == 'KEY_FEED': value = x+keys[x % 4]
    elif rule == 'PRIME_TURN': value = x+(1 if is_prime(keys[x % 4]) else 3)
    elif rule == 'PORT_WEAVE': value = 3*x+len(ports)
    elif rule == 'NOVA_MIRROR': value = 99-x if lights['NOVA'] else x+11
    elif rule == 'ODD_ANCHOR': value = x+batteries+2 if x % 2 else x+digits[-1]+1
    elif rule == 'HIGH_KEY': value = x+max(keys)-min(keys)
    elif rule == 'RAY_SWITCH': value = 5*x+2 if lights['RAY'] else 2*x+5
    elif rule == 'DIGIT_FLIP': value = int(f'{x:03d}'[::-1])
    elif rule == 'VOWEL_LIFT': value = x+13 if any(c in 'AEIOU' for c in edge['serial']) else x-9
    elif rule == 'FIBER_FORK': value = 2*x+3 if 'fiber' in ports else x+6
    elif rule == 'KEY_GAP': value = x+abs(keys[0]-keys[3])
    elif rule == 'QUARTER_ECHO': value = x//4+3*(x % 4)+1
    elif rule == 'LAMP_COUNT': value = x+7*sum(lights.values())-sum(not v for v in lights.values())
    else: raise ValueError('Unknown Keystone rule')
    return value % 1000


def trace(state, edge):
    if len(state['steps']) != state['depth']:
        raise ValueError('Keystone depth must equal its number of dependent steps')
    value, steps = 0, []
    for index, rule in enumerate(state['steps'], 1):
        after = apply_step(rule, value, state['keys'], edge)
        steps.append({'step':index, 'rule':rule, 'input':value, 'output':after})
        value = after
    return {'initial_value':0, 'steps':steps, 'final_value':value, 'key_position':1+value % 4}


def make_state(rng, depth, stage=1, history=None):
    if depth not in range(1,6): raise ValueError('Keystone depth must be 1..5')
    return {'stage':stage, 'depth':depth, 'keys':rng.sample(range(100),4),
            'steps':rng.sample(list(RULES),depth), 'history':history or []}


def manual_section():
    return ('Keystone — four numbered keys in positions 1 to 4. Start the accumulator x at 0. '
            'Execute the listed rule IDs in order, exactly once each. After EACH rule, normalize x modulo 1000 '
            '(use the remainder 0..999, even after subtraction). Each rule reads the previous normalized x. '
            'After exactly depth rule applications, press key position 1+(x modulo 4). This final decoding is not another rule step. '
            'Key numbers are facts used by some rules; the action chooses a position. A prime is an integer at least 2 '
            'whose only positive divisors are 1 and itself. Port count counts the listed ports. '
            'A wrong press adds a strike and repeats the same stage. A standard module has three stages with strictly increasing depths. '
            'The isolated sweep uses one stage and one choice per seed/depth. No intermediate work is shown by the module.\n\n' +
            '\n'.join(f'{name}: {description}' for name,description in RULES.items()))
