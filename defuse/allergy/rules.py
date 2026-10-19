"""Questions, definitions, the menu and the protocol engine (ALLERGY_PROTOCOL.md sections 1, 3 and 4).

Every system's answers, and the answer key, go through exactly this code. The model never looks up a recipe, combines
messages or decides whether a dish is safe: that happens here."""

MINUTES = 60                         # simulated minutes of service
POLLS = list(range(20, MINUTES + 1, 5))   # pass checks: every dish on the ticket, every 5 minutes from minute 20
CLARIFY_DELAY = 2
CLARIFY_BUDGET = 4

SEND, HOLD, ASK = 'send', 'hold', 'ask'
DECISION_NAME = {SEND: 'send', HOLD: 'hold (unsafe)', ASK: 'ask first (not known to be safe)'}

ALLERGENS = ['PEANUT', 'TREE_NUT', 'MILK', 'EGG', 'WHEAT', 'SOY', 'SESAME', 'FISH', 'SHELLFISH']
QUESTION_NAMES = ALLERGENS + ['FRYER', 'CORRECTION']
FACTUAL = ALLERGENS + ['FRYER']
NAME = {'PEANUT': 'peanuts', 'TREE_NUT': 'tree nuts', 'MILK': 'milk', 'EGG': 'eggs', 'WHEAT': 'wheat', 'SOY': 'soy',
        'SESAME': 'sesame', 'FISH': 'fish', 'SHELLFISH': 'crustacean shellfish'}

# Definitions shown to every system, from 21 U.S.C. 321(qq) and FDA's January 2025 guidance (Edition 5).
DEFINITIONS = (
    'Definitions (US FDA, 2025). Peanuts are legumes, not tree nuts. Tree nuts: almond, Brazil nut, cashew, hazelnut '
    '(filbert), macadamia, pecan, pine nut, pistachio, walnut (including black walnut and heartnut); coconut and '
    'chestnut are not tree nuts. Milk: milk from cows, goats, sheep or other ruminants and foods made from it (butter, '
    'cheese, cream, yogurt, ghee, whey, casein); lactose intolerance means avoiding milk; coconut milk and oat milk '
    'are not milk (almond milk is a tree nut, soy milk is soy). Eggs: eggs of chickens, ducks, geese, quail or other '
    'fowl, and mayonnaise, aioli and meringue. Wheat: includes spelt, durum, semolina, farro, einkorn, khorasan and '
    'triticale; "gluten-free" or celiac disease means avoiding wheat. Soy: soybeans, tofu, edamame, miso, tempeh, soy '
    'sauce, soy milk. Sesame: sesame seeds, sesame oil, tahini. Fish: fin fish such as salmon, tuna, cod and anchovies, '
    'and fish sauce. Crustacean shellfish: shrimp, prawns, crab, lobster, crayfish; a "shellfish" allergy means these.')


def instructions_header(target):
    return ('Restaurant allergy check during dinner service (research simulation). Answer only from what this message '
            f'says, about the food for {target}: everyone eating that order. Parts of a message about other tables or '
            'orders, or about people not eating this order, do not count. If a speaker misspeaks and corrects '
            'themselves in the same sentence, the item they settle on counts.\n'
            'For each allergen: avoid = someone eating this order must avoid it (an allergy, an intolerance or a request '
            'for none); ok = the message says it is fine for everyone eating this order; unclear = it may be meant, but '
            'the message does not make clear whether it must be avoided (for example "nuts" without saying which kind); '
            'not_mentioned = nothing said about it for this order.\n' + DEFINITIONS)


ALLERGEN_OPTIONS = [('not_mentioned', 'nothing said for this order'), ('avoid', 'must be avoided'),
                    ('ok', 'said to be fine'), ('unclear', 'may be meant; unclear')]


def questions():
    """The 11 questions. The same for every message; the target and the meaning of each answer are in the header."""
    out = [(a, f'{NAME[a].capitalize()}: what does this message say for this order?', ALLERGEN_OPTIONS) for a in ALLERGENS]
    out.append(('FRYER', 'The oil the fries are cooked in tonight (kitchen-wide): what does this message say is fried in it?', [
        ('not_mentioned', 'nothing about the fries oil'),
        ('fresh', 'fresh oil or a dedicated fryer: nothing else in it'),
        ('wheat', 'breaded or battered wheat items, e.g. chicken tenders'),
        ('shellfish', 'shrimp or other crustacean shellfish'),
        ('fish', 'fish'),
        ('unclear', 'mentioned, but what else is in it is unclear')]))
    out.append(('CORRECTION', 'Does this message explicitly correct or withdraw something said earlier about this '
                              'order\'s allergies (e.g. "correction", "scratch that", "ignore my earlier note")?', [
        ('no', 'no'), ('yes', 'yes, explicitly'), ('unclear', 'unclear')]))
    return out


# ---------- the menu (code only; no system sees recipes) ----------
# dish: (allergens as an ingredient, served with fries)
MENU = {
    'House fries': ((), True),
    'Steak frites': (('MILK',), True),
    'Cheeseburger and fries': (('WHEAT', 'MILK', 'SESAME'), True),
    'Grilled chicken and fries': ((), True),
    'Fish and chips': (('FISH', 'WHEAT'), True),
    'Caesar salad': (('FISH', 'EGG', 'MILK', 'WHEAT'), False),
    'Garden salad with tahini dressing': (('SESAME',), False),
    'Grilled salmon with rice': (('FISH',), False),
    'Pesto pasta': (('WHEAT', 'MILK', 'TREE_NUT'), False),
    'Margherita pizza': (('WHEAT', 'MILK'), False),
    'Peanut noodles': (('PEANUT', 'WHEAT', 'SOY', 'SESAME'), False),
    'Tofu rice bowl': (('SOY', 'SESAME'), False),
    'Shrimp tacos': (('SHELLFISH', 'MILK'), False),
    'Lobster roll': (('SHELLFISH', 'WHEAT', 'EGG', 'MILK'), False),
    'Vegetable curry with coconut milk': ((), False),
    'Brownie sundae': (('WHEAT', 'EGG', 'MILK', 'TREE_NUT'), False),
    'Almond cake': (('TREE_NUT', 'EGG', 'MILK', 'WHEAT'), False),
    'Mango sorbet': ((), False),
    'Fruit plate': ((), False),
}
FRYER_DEFAULT = frozenset({'WHEAT'})        # the fries share oil with the breaded chicken tenders unless told otherwise
FRYER_ADDS = {'wheat': 'WHEAT', 'shellfish': 'SHELLFISH', 'fish': 'FISH'}


# ---------- protocol engine ----------
def effective_answers(messages, answers, overrides, t):
    """messages: [{'id','minute'}] in any order; answers: {id: {question: value}};
    overrides: [(arrival_minute, message_id, question, value)] from clarification answers."""
    eff = {}
    for m in messages:
        if m['minute'] <= t:
            eff[m['id']] = dict(answers[m['id']])
    for arrival, mid, q, v in overrides:
        if arrival <= t and mid in eff:
            eff[mid][q] = v
    order = sorted((m for m in messages if m['id'] in eff), key=lambda m: (m['minute'], m['id']))
    return [(m, eff[m['id']]) for m in order]


CUSTOMER = {'GUEST', 'APP'}           # the guest's own side: their texts and their delivery-app notes
RULES = {'anyone': 'any clear correction cancels an allergy (the October 12 rule)',
         'guest_only': 'anyone can add an allergy; only the guest can take one away',
         'same_sender': 'only the guest, or whoever first stated the allergy, can take it away'}


def restrictions(messages, answers, overrides, t, rule='anyone'):
    """Each allergen's status for the order at time t: 'avoid', 'unclear' or 'none'.

    Statements are applied in time order. 'avoid' always applies. 'unclear' applies unless the allergen is already to be
    avoided. 'ok' clears an 'unclear', but lifts an 'avoid' only in a message that explicitly corrects an earlier one
    (CORRECTION = yes): an unexplained reversal is not trusted.

    rule (ALLERGY_PROTOCOL.md §9) decides whose 'ok' counts at all, using the sender code knows from the message header:
    'anyone' (the original rule), 'guest_only' (only the guest's side) or 'same_sender' (the guest's side, or the sender
    who first stated that allergen). Messages need a 'source' for the last two."""
    status = {a: 'none' for a in ALLERGENS}
    first = {}
    for m, a in effective_answers(messages, answers, overrides, t):
        correction = a.get('CORRECTION') == 'yes'
        src = m.get('source')
        for x in ALLERGENS:
            v = a.get(x, 'not_mentioned')
            if v in ('avoid', 'unclear') and status[x] == 'none':
                first[x] = src
            if v == 'avoid':
                status[x] = 'avoid'
            elif v == 'unclear' and status[x] != 'avoid':
                status[x] = 'unclear'
            elif v == 'ok' and (status[x] != 'avoid' or correction):
                if rule == 'anyone' or src in CUSTOMER or (rule == 'same_sender' and src == first.get(x)):
                    status[x] = 'none'
    return status


def fryer(messages, answers, overrides, t):
    """(allergens in the fries oil, whether the oil's contents are unknown) at time t.

    Starts from the menu default. 'fresh' empties the oil and clears any doubt; each shared item is added; 'unclear'
    makes the contents unknown until the next 'fresh'."""
    contents, unknown = set(FRYER_DEFAULT), False
    for _, a in effective_answers(messages, answers, overrides, t):
        v = a.get('FRYER', 'not_mentioned')
        if v == 'fresh':
            contents, unknown = set(), False
        elif v in FRYER_ADDS:
            contents.add(FRYER_ADDS[v])
        elif v == 'unclear':
            unknown = True
    return contents, unknown


def dish_allergens(dish, oil):
    recipe, fries = MENU[dish]
    return set(recipe) | (set(oil) if fries else set())


def decide(dish, status, oil, oil_unknown):
    """send / hold / ask for one dish."""
    contents = dish_allergens(dish, oil)
    avoid = {a for a, s in status.items() if s == 'avoid'}
    unclear = {a for a, s in status.items() if s == 'unclear'}
    if contents & avoid:
        return HOLD
    if contents & unclear:
        return ASK
    if MENU[dish][1] and oil_unknown and (avoid or unclear):
        return ASK
    return SEND


def decisions(dishes, messages, answers, overrides, t, rule='anyone'):
    status = restrictions(messages, answers, overrides, t, rule)
    oil, unknown = fryer(messages, answers, overrides, t)
    return {d: decide(d, status, oil, unknown) for d in dishes}, status, sorted(oil), unknown


def clock(start, minute):
    """12-hour clock for a simulated minute, e.g. start=(18, 40), minute=25 -> '7:05 PM'."""
    total = start[0] * 60 + start[1] + minute
    h, m = total // 60 % 24, total % 60
    return f'{(h - 1) % 12 + 1}:{m:02d} {"AM" if h < 12 else "PM"}'
