# Defuse × Decisions — Original Manual

Three strikes or an expired countdown ends the attempt. All ordinary modules and any active Relief Watch demand must be cleared to win.

## Wires

Thread Array — numbered wires. Use the first matching rule, counting from 1.
If there are at least two amber wires AND the final serial digit is even, cut the last amber wire.
Otherwise, if there are no teal wires AND the serial contains a vowel (A E I O U), cut wire 2.
Otherwise, if the first and last wires have the same color, cut the middle wire, rounding its position up (ceil(n/2)).
Otherwise cut the last wire. A wrong cut adds a strike without removing the wire.

## Button

Pulse Seal — apply the first matching rule.
If the label is DRIFT and there are at least 3 batteries, press and release.
Otherwise, if the button is plum and the NOVA indicator is lit, press and release.
Otherwise hold. Holding reveals a strip: amber requires countdown digit 3, teal requires digit 6, white requires digit 0.
The display is floor(seconds remaining), written MM:SS. While held, release only when that digit is on the current display.
When the digit is absent, wait 0.2 seconds. Waiting while the digit is present, or releasing while absent, adds a strike.
A wrong operation leaves the held/released state unchanged. The display at arrival of the action determines the verdict.

## Glyph

Sigil Rack — find the single column containing all four names. Press the four glyphs in that column’s top-to-bottom order. Already pressed keys stay visible and pressing one again adds a strike.
reed-eye → split-moon → ladder-seed → crooked-sun → twin-rain → cup-star
loop-thorn → river-knot → fork-cloud → hollow-sail → triple-moss → bent-comet
stone-wing → coil-leaf → broken-crown → dotted-wave → branch-gate → amber-hook

## Echo

Tint Echo — colors are amber, teal, plum, white, numbered 0,1,2,3 in that order.
For each flash, add the CURRENT strike count and also add 1 if the serial contains a vowel; take the result modulo 4. Press that resulting color.
Replay all flashes of a stage in order. There are three stages of lengths 1,2,3. The displayed cursor identifies the next flash. A wrong answer leaves the cursor in place; recalculate with the new strike count.

## Recall

Ledger Keys — four positions, numbered 1 to 4, display distinct labels 1 to 4; the screen shows a digit 1 to 4. Five stages. Keep the visible history of successful presses.
Stage 1: press the position equal to the screen digit.
Stage 2: press the key with the same LABEL pressed in stage 1.
Stage 3: if the screen is even, press the same POSITION as stage 1; otherwise press the key labeled 4.
Stage 4: if the screen is at least 3, press the key with the LABEL from stage 2; otherwise press the POSITION from stage 3.
Stage 5: if there are at least 2 batteries, press the key with the LABEL from stage 4; otherwise press the POSITION from stage 2.
Incorrect presses add a strike and do not enter the history or advance the stage.

## Lexicon

Word Loom — exactly one manual word can be spelled using one letter from each dial. Words: MIST, LOAM, FERN, DUSK, COVE, BRIM, TIDE, GLOW.
Dials are handled left to right. At the current dial, cycle forward if its displayed letter differs from the matching word; otherwise lock that dial. Cycling past the target or locking a different letter adds a strike without progress. A cycle advances by one letter with wraparound. Each dial shows its complete circular letter list.

## Interrupt

Relief Watch — every 25 to 40 seconds of game time, the gauge demands a response within 10 seconds.
Vent (yes) if pressure is at least 60 AND either the RAY indicator is unlit or there is a fiber port. Otherwise do not vent (no).
An incorrect answer adds a strike and closes this demand. Missing the deadline adds one strike. It rearms until all ordinary modules are solved; it cannot be permanently solved earlier. Respond to an active demand before returning to ordinary modules.

## Labyrinth

Labyrinth — a 6×6 grid. Coordinates are (row,column), starting at (1,1) in the top left. Up reduces row; down increases row; left reduces column; right increases column. Identify the layout by its unordered pair of marker circles. Outer boundaries are walls. Each listed pair of adjacent cells has a wall between them; all other adjacent pairs are open. Move to the exit. Any open move is legal, including a detour; a wall bump adds a strike and leaves the dot in place. Shortest-path choices are measured separately from legality. The move history shows your prior attempts.

Layout 1: circles (1,1) and (6,1). Walls: (1,1)–(2,1); (1,2)–(2,2); (1,3)–(2,3); (1,4)–(1,5); (1,5)–(2,5); (2,3)–(2,4); (2,4)–(2,5); (2,6)–(3,6); (3,1)–(4,1); (3,1)–(3,2); (3,2)–(3,3); (3,3)–(4,3); (3,3)–(3,4); (3,4)–(3,5); (4,2)–(5,2); (4,2)–(4,3); (4,4)–(5,4); (4,4)–(4,5); (4,5)–(4,6); (5,2)–(6,2); (5,3)–(6,3); (5,3)–(5,4); (5,4)–(6,4); (5,5)–(6,5); (5,5)–(5,6).

Layout 2: circles (1,2) and (6,6). Walls: (1,1)–(1,2); (1,2)–(2,2); (1,4)–(2,4); (1,5)–(2,5); (2,1)–(3,1); (2,2)–(2,3); (2,3)–(3,3); (2,4)–(2,5); (2,5)–(2,6); (3,1)–(3,2); (3,2)–(4,2); (3,3)–(3,4); (3,4)–(3,5); (3,5)–(3,6); (4,2)–(5,2); (4,3)–(5,3); (4,3)–(4,4); (4,4)–(4,5); (4,5)–(4,6); (5,1)–(5,2); (5,2)–(6,2); (5,3)–(6,3); (5,4)–(5,5); (5,5)–(5,6); (6,4)–(6,5).

Layout 3: circles (1,3) and (6,5). Walls: (1,1)–(1,2); (1,4)–(2,4); (1,4)–(1,5); (2,1)–(2,2); (2,2)–(3,2); (2,2)–(2,3); (2,4)–(3,4); (2,5)–(3,5); (2,5)–(2,6); (3,1)–(4,1); (3,2)–(3,3); (3,3)–(4,3); (3,4)–(4,4); (3,5)–(4,5); (3,5)–(3,6); (4,1)–(4,2); (4,2)–(5,2); (4,3)–(4,4); (4,5)–(4,6); (5,1)–(5,2); (5,3)–(6,3); (5,3)–(5,4); (5,4)–(5,5); (5,5)–(6,5); (6,4)–(6,5).

Layout 4: circles (1,4) and (6,4). Walls: (1,1)–(2,1); (1,2)–(1,3); (1,3)–(2,3); (1,4)–(2,4); (1,6)–(2,6); (2,2)–(3,2); (2,2)–(2,3); (2,4)–(2,5); (2,5)–(3,5); (3,1)–(3,2); (3,3)–(4,3); (3,3)–(3,4); (3,4)–(3,5); (3,6)–(4,6); (4,1)–(4,2); (4,2)–(4,3); (4,4)–(5,4); (4,4)–(4,5); (4,5)–(5,5); (5,1)–(6,1); (5,2)–(6,2); (5,2)–(5,3); (5,3)–(6,3); (5,4)–(6,4); (5,5)–(6,5).

Layout 5: circles (1,5) and (6,3). Walls: (1,1)–(1,2); (1,3)–(2,3); (1,4)–(1,5); (1,6)–(2,6); (2,1)–(2,2); (2,2)–(2,3); (2,3)–(2,4); (2,4)–(2,5); (2,5)–(3,5); (3,1)–(3,2); (3,2)–(3,3); (3,3)–(4,3); (3,4)–(4,4); (3,5)–(3,6); (4,1)–(4,2); (4,3)–(4,4); (4,5)–(5,5); (4,5)–(4,6); (5,1)–(5,2); (5,2)–(6,2); (5,2)–(5,3); (5,3)–(5,4); (5,4)–(5,5); (6,3)–(6,4); (6,5)–(6,6).

Layout 6: circles (1,6) and (6,2). Walls: (1,1)–(1,2); (1,2)–(2,2); (1,4)–(2,4); (1,5)–(2,5); (2,1)–(3,1); (2,2)–(3,2); (2,3)–(3,3); (2,3)–(2,4); (2,4)–(3,4); (2,5)–(2,6); (3,3)–(3,4); (3,5)–(4,5); (3,5)–(3,6); (4,1)–(4,2); (4,2)–(4,3); (4,3)–(5,3); (4,4)–(4,5); (4,6)–(5,6); (5,1)–(5,2); (5,2)–(5,3); (5,3)–(6,3); (5,4)–(6,4); (5,4)–(5,5); (5,5)–(6,5); (6,1)–(6,2).

Layout 7: circles (2,1) and (6,1). Walls: (1,1)–(2,1); (1,2)–(1,3); (1,3)–(2,3); (1,5)–(2,5); (1,6)–(2,6); (2,1)–(2,2); (2,2)–(3,2); (2,3)–(2,4); (2,4)–(3,4); (2,5)–(3,5); (3,2)–(3,3); (3,3)–(4,3); (3,4)–(4,4); (3,5)–(4,5); (4,1)–(4,2); (4,2)–(5,2); (4,2)–(4,3); (4,5)–(4,6); (5,2)–(5,3); (5,3)–(5,4); (5,4)–(5,5); (5,5)–(6,5); (5,5)–(5,6); (6,1)–(6,2); (6,3)–(6,4).

Layout 8: circles (2,2) and (6,6). Walls: (1,1)–(1,2); (1,3)–(1,4); (1,5)–(2,5); (2,1)–(2,2); (2,2)–(2,3); (2,3)–(2,4); (2,4)–(3,4); (2,5)–(2,6); (2,6)–(3,6); (3,1)–(3,2); (3,2)–(3,3); (3,3)–(4,3); (3,4)–(3,5); (4,1)–(4,2); (4,2)–(4,3); (4,4)–(5,4); (4,4)–(4,5); (4,5)–(5,5); (4,5)–(4,6); (5,1)–(5,2); (5,2)–(5,3); (5,3)–(6,3); (5,4)–(6,4); (5,5)–(5,6); (6,2)–(6,3).

Layout 9: circles (2,3) and (6,5). Walls: (1,1)–(2,1); (1,2)–(1,3); (1,4)–(2,4); (1,6)–(2,6); (2,1)–(2,2); (2,2)–(2,3); (2,3)–(3,3); (2,4)–(2,5); (2,5)–(3,5); (3,2)–(4,2); (3,2)–(3,3); (3,3)–(3,4); (3,4)–(3,5); (3,6)–(4,6); (4,1)–(4,2); (4,2)–(4,3); (4,4)–(5,4); (4,4)–(4,5); (4,5)–(5,5); (5,1)–(5,2); (5,2)–(6,2); (5,3)–(6,3); (5,3)–(5,4); (5,5)–(6,5); (6,4)–(6,5).

## Keystone

Keystone — four numbered keys in positions 1 to 4. Start the accumulator x at 0. Execute the listed rule IDs in order, exactly once each. After EACH rule, normalize x modulo 1000 (use the remainder 0..999, even after subtraction). Each rule reads the previous normalized x. After exactly depth rule applications, press key position 1+(x modulo 4). This final decoding is not another rule step. Key numbers are facts used by some rules; the action chooses a position. A prime is an integer at least 2 whose only positive divisors are 1 and itself. Port count counts the listed ports. A wrong press adds a strike and repeats the same stage. A standard module has three stages with strictly increasing depths. The isolated sweep uses one stage and one choice per seed/depth. No intermediate work is shown by the module.

DIGIT_TIDE: Add the sum of all serial digits to x.
LAMP_FOLD: If any indicator is lit, replace x with 2*x+1; otherwise replace x with x+7.
CELL_TAX: Subtract battery count times (port count + 1) from x.
KEY_FEED: Add the number on the key at position 1+(x modulo 4) to x.
PRIME_TURN: If the key at position 1+(x modulo 4) has a prime number, add 1 to x; otherwise add 3.
PORT_WEAVE: Replace x with 3*x + port count.
NOVA_MIRROR: If NOVA is lit, replace x with 99-x; otherwise add 11 to x.
ODD_ANCHOR: If x is odd, add battery count + 2; otherwise add the final serial digit + 1.
HIGH_KEY: Add the largest key number minus the smallest key number to x.
RAY_SWITCH: If RAY is lit, replace x with 5*x+2; otherwise replace x with 2*x+5.
DIGIT_FLIP: Reverse the three decimal digits of x, including leading zeros, and interpret the result as an integer.
VOWEL_LIFT: If the serial contains A, E, I, O or U, add 13 to x; otherwise subtract 9.
FIBER_FORK: If a fiber port is present, replace x with 2*x+3; otherwise replace x with x+6.
KEY_GAP: Add the absolute difference between key 1 and key 4 to x.
QUARTER_ECHO: Replace x with floor(x/4) + 3*(x modulo 4) + 1.
LAMP_COUNT: Add 7 times the number of lit indicators, then subtract the number of unlit indicators.
