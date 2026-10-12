"""Keyword parser baseline, written and committed before any message text existed (ALLERGY_PROTOCOL.md §6).

Splits a message into clauses, drops clauses about other tables or about people not eating, finds food words with the
shared lexicon and decides avoid / ok / unclear from nearby words. Free, fast and brittle by design: it shows how much
of the task plain keyword matching can do."""
import re
from defuse.allergy import lexicon
from defuse.allergy.rules import ALLERGENS

OK = re.compile(r"\b(fine|ok|okay|no problem|can have|can eat|is good|are good|all good|no issue|not an issue)\b")
AVOID = re.compile(r"(allerg|can't|cannot|can not|\bno\b|avoid|intoleran|-free|\bfree\b|celiac|coeliac|must not|"
                   r"don't|do not|without|keep .* away|anaphyla)")
CORRECTION = re.compile(r"\b(correction|scratch that|ignore (my|the|that) (earlier|last|previous)|disregard|"
                        r"correcting|i was wrong|update to (my|the) earlier|cancel (my|the) earlier)\b")
SELF_FIX = re.compile(r"[,\s-]*\b(uh|um)?[,\s]*\b(sorry|i mean|make that|i meant|no wait)\b[,:]?(\s*i mean)?\s*", re.I)
FRYER = re.compile(r"\b(fryer|fry oil|fries oil|frying oil|the oil|same oil|fried in)\b")
FRESH = re.compile(r"\b(fresh oil|new oil|dedicated|nothing else|clean oil|changed the oil|oil change)\b")
LABEL = re.compile(r"\b(table \d+|order #?\d+)\b")


def blank():
    a = {x: 'not_mentioned' for x in ALLERGENS}
    a['FRYER'] = 'not_mentioned'
    a['CORRECTION'] = 'no'
    return a


def fix_slips(sentence):
    """'allergic to sesame, sorry, I mean soy' -> 'allergic to soy': drop the food word said just before the fix."""
    while True:
        m = SELF_FIX.search(sentence)
        if not m:
            return sentence
        before = sentence[:m.start()]
        words = before.split()
        cut = len(before)
        for k in range(1, min(4, len(words)) + 1):
            tail = ' '.join(words[-k:])
            if lexicon.categories(tail)[0] or lexicon.categories(tail)[1]:
                cut = len(before) - len(tail)
                break
        sentence = sentence[:cut].rstrip() + ' ' + sentence[m.end():]


def parse(header, text, target):
    a = blank()
    tgt = target.lower().replace('delivery ', '')
    head = header.lower()
    head_label = LABEL.search(head)
    if head_label and head_label.group(1) not in tgt and tgt not in head_label.group(1):
        return a                                           # a note on another table's ticket
    t = text.lower()
    if CORRECTION.search(t):
        a['CORRECTION'] = 'yes'
    seen = {}
    clauses = []
    for sentence in re.split(r'[.;!?]', t):
        if re.search(r"not eating|isn't eating|is not eating|won't be eating|not joining|not with us", sentence):
            continue
        clauses += re.split(r',|\bbut\b|\bwhile\b|\band in\b|\bthough\b', fix_slips(sentence))
    for clause in clauses:
        labels = LABEL.findall(clause)
        if labels and not any(x in tgt or tgt in x for x in labels):
            continue
        if FRYER.search(clause):
            if FRESH.search(clause):
                a['FRYER'] = 'fresh'
            else:
                cat = lexicon.fryer_category(clause)
                a['FRYER'] = {'WHEAT': 'wheat', 'SHELLFISH': 'shellfish', 'FISH': 'fish'}.get(cat, 'unclear')
            continue
        cats, ambiguous = lexicon.categories(clause)
        if not cats:
            continue
        polarity = 'ok' if OK.search(clause) else 'avoid' if AVOID.search(clause) else 'unclear'
        for c in cats:
            v = 'unclear' if ambiguous and polarity == 'avoid' else polarity
            prev = seen.get(c)
            seen[c] = v if prev is None else ('avoid' if 'avoid' in (prev, v) else 'unclear' if 'unclear' in (prev, v) else v)
    if seen.get('PEANUT') == 'ok' and seen.get('TREE_NUT') == 'unclear':
        seen['TREE_NUT'] = 'avoid'
    if seen.get('TREE_NUT') == 'ok' and seen.get('PEANUT') == 'unclear':
        seen['PEANUT'] = 'avoid'
    a.update(seen)
    return a
