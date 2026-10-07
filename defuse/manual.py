"""Original rules. These are also the exact sections sent to the controller."""
from pathlib import Path
from defuse.modules.labyrinth import manual_section as labyrinth_manual
from defuse.modules.keystone import manual_section as keystone_manual

GLYPH_COLUMNS = [
    ['reed-eye', 'split-moon', 'ladder-seed', 'crooked-sun', 'twin-rain', 'cup-star'],
    ['loop-thorn', 'river-knot', 'fork-cloud', 'hollow-sail', 'triple-moss', 'bent-comet'],
    ['stone-wing', 'coil-leaf', 'broken-crown', 'dotted-wave', 'branch-gate', 'amber-hook'],
]
WORDS = ['MIST', 'LOAM', 'FERN', 'DUSK', 'COVE', 'BRIM', 'TIDE', 'GLOW']
SECTIONS = {
'wires': '''Thread Array — numbered wires. Use the first matching rule, counting from 1.
If there are at least two amber wires AND the final serial digit is even, cut the last amber wire.
Otherwise, if there are no teal wires AND the serial contains a vowel (A E I O U), cut wire 2.
Otherwise, if the first and last wires have the same color, cut the middle wire, rounding its position up (ceil(n/2)).
Otherwise cut the last wire. A wrong cut adds a strike without removing the wire.''',
'button': '''Pulse Seal — apply the first matching rule.
If the label is DRIFT and there are at least 3 batteries, press and release.
Otherwise, if the button is plum and the NOVA indicator is lit, press and release.
Otherwise hold. Holding reveals a strip: amber requires countdown digit 3, teal requires digit 6, white requires digit 0.
The display is floor(seconds remaining), written MM:SS. While held, release only when that digit is on the current display.
When the digit is absent, wait 0.2 seconds. Waiting while the digit is present, or releasing while absent, adds a strike.
A wrong operation leaves the held/released state unchanged. The display at arrival of the action determines the verdict.''',
'glyph': 'Sigil Rack — find the single column containing all four names. Press the four glyphs in that column’s top-to-bottom order. Already pressed keys stay visible and pressing one again adds a strike.\n' + '\n'.join(' → '.join(c) for c in GLYPH_COLUMNS),
'echo': '''Tint Echo — colors are amber, teal, plum, white, numbered 0,1,2,3 in that order.
For each flash, add the CURRENT strike count and also add 1 if the serial contains a vowel; take the result modulo 4. Press that resulting color.
Replay all flashes of a stage in order. There are three stages of lengths 1,2,3. The displayed cursor identifies the next flash. A wrong answer leaves the cursor in place; recalculate with the new strike count.''',
'recall': '''Ledger Keys — four positions, numbered 1 to 4, display distinct labels 1 to 4; the screen shows a digit 1 to 4. Five stages. Keep the visible history of successful presses.
Stage 1: press the position equal to the screen digit.
Stage 2: press the key with the same LABEL pressed in stage 1.
Stage 3: if the screen is even, press the same POSITION as stage 1; otherwise press the key labeled 4.
Stage 4: if the screen is at least 3, press the key with the LABEL from stage 2; otherwise press the POSITION from stage 3.
Stage 5: if there are at least 2 batteries, press the key with the LABEL from stage 4; otherwise press the POSITION from stage 2.
Incorrect presses add a strike and do not enter the history or advance the stage.''',
'lexicon': 'Word Loom — exactly one manual word can be spelled using one letter from each dial. Words: ' + ', '.join(WORDS) + '''.
Dials are handled left to right. At the current dial, cycle forward if its displayed letter differs from the matching word; otherwise lock that dial. Cycling past the target or locking a different letter adds a strike without progress. A cycle advances by one letter with wraparound. Each dial shows its complete circular letter list.''',
'interrupt': '''Relief Watch — every 25 to 40 seconds of game time, the gauge demands a response within 10 seconds.
Vent (yes) if pressure is at least 60 AND either the RAY indicator is unlit or there is a fiber port. Otherwise do not vent (no).
An incorrect answer adds a strike and closes this demand. Missing the deadline adds one strike. It rearms until all ordinary modules are solved; it cannot be permanently solved earlier. Respond to an active demand before returning to ordinary modules.''',
}
SECTIONS['labyrinth'] = labyrinth_manual()
SECTIONS['keystone'] = keystone_manual()

def markdown():
    return '# Defuse × Decisions — Original Manual\n\nThree strikes or an expired countdown ends the attempt. All ordinary modules and any active Relief Watch demand must be cleared to win.\n\n' + '\n\n'.join('## ' + k.title() + '\n\n' + v for k,v in SECTIONS.items()) + '\n'

if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(); p.add_argument('--output', type=Path)
    a = p.parse_args()
    if a.output: a.output.write_text(markdown())
    else: print(markdown())
