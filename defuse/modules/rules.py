"""Auditable rule oracle; returns an action and the manual clause exercised."""
import math
from defuse.manual import GLYPH_COLUMNS, WORDS
from defuse.modules.labyrinth import shortest_action
from defuse.modules.keystone import trace

COLORS = ['amber', 'teal', 'plum', 'white']

def vowel(edge):
    return any(x in 'AEIOU' for x in edge['serial'])

def display(seconds):
    value = max(0, int(seconds))
    return f'{value//60:02d}:{value%60:02d}'

def correct(kind, state, edge, strikes, remaining):
    if kind == 'labyrinth': return 'move:'+shortest_action(state), 'labyrinth.shortest_path'
    if kind == 'keystone': return 'keystone:'+str(trace(state, edge)['key_position']), 'keystone.depth'+str(state['depth'])
    if kind == 'wires':
        w = state['wires']
        digit = int(next(c for c in reversed(edge['serial']) if c.isdigit()))
        if w.count('amber') >= 2 and digit % 2 == 0:
            return f'cut:{len(w)-1-w[::-1].index("amber")}', 'wires.amber_even'
        if 'teal' not in w and vowel(edge): return 'cut:1', 'wires.no_teal_vowel'
        if w[0] == w[-1]: return f'cut:{math.ceil(len(w)/2)-1}', 'wires.match_ends'
        return f'cut:{len(w)-1}', 'wires.last'
    if kind == 'button':
        if state['held']:
            digit = {'amber':'3', 'teal':'6', 'white':'0'}[state['strip']]
            return ('release', 'button.release_'+state['strip']) if digit in display(remaining) else ('wait', 'button.wait_'+state['strip'])
        if state['label'] == 'DRIFT' and edge['batteries'] >= 3: return 'tap', 'button.drift'
        if state['color'] == 'plum' and edge['indicators']['NOVA']: return 'tap', 'button.nova'
        return 'hold', 'button.hold'
    if kind == 'glyph':
        column = next(c for c in GLYPH_COLUMNS if set(state['glyphs']) <= set(c))
        ordered = [g for g in column if g in state['glyphs']]
        return 'glyph:'+ordered[len(state['pressed'])], f'glyph.column{GLYPH_COLUMNS.index(column)}'
    if kind == 'echo':
        flash = state['flashes'][state['cursor']]
        offset = strikes + int(vowel(edge))
        return 'color:'+COLORS[(COLORS.index(flash)+offset)%4], f'echo.vowel{int(vowel(edge))}.strikes{strikes}'
    if kind == 'recall':
        stage, h, screen, labels = state['stage'], state['history'], state['screen'], state['labels']
        if stage == 1: pos, rule = screen, 'stage1'
        elif stage == 2: pos, rule = labels.index(h[0]['label'])+1, 'stage2'
        elif stage == 3:
            pos, rule = (h[0]['position'], 'stage3_even') if screen%2==0 else (labels.index(4)+1, 'stage3_odd')
        elif stage == 4:
            pos, rule = (labels.index(h[1]['label'])+1, 'stage4_high') if screen>=3 else (h[2]['position'], 'stage4_low')
        else:
            pos, rule = (labels.index(h[3]['label'])+1, 'stage5_batteries') if edge['batteries']>=2 else (h[1]['position'], 'stage5_few')
        return f'key:{pos}', 'recall.'+rule
    if kind == 'lexicon':
        word = next(w for w in WORDS if all(w[i] in state['dials'][i] for i in range(4)))
        i = state['cursor']
        return ('lock', 'lexicon.lock') if state['dials'][i][state['indices'][i]] == word[i] else ('cycle', 'lexicon.cycle')
    if kind == 'interrupt':
        if state['pressure'] < 60: return 'no', 'interrupt.low'
        if not edge['indicators']['RAY']: return 'yes', 'interrupt.unlit'
        if 'fiber' in edge['ports']: return 'yes', 'interrupt.fiber'
        return 'no', 'interrupt.lit_no_fiber'
    raise ValueError('Unknown module: '+kind)
