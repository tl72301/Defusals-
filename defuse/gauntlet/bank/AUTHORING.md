# Held-out gauntlet bank: authoring note

Written by a separate agent that was blind to the baselines. It did not read the
repository, its git history or any existing baseline or bank files. Every item was
written from general knowledge. Date: 2026-10-07.

## Bins and precedence
cold (refrigerated or frozen food/medicine), hazardous (flammable, explosive, toxic,
corrosive, pressurized, lithium battery), fragile (glass, ceramic, porcelain, crystal,
anything easily broken), other (everything else). When more than one bin applies, the
first one in this order wins: hazardous, cold, fragile, other.

## knowledge.json (200 items, 40 per rung)
- **everyday** (k-e-): common household items in natural wording.
- **specialist** (k-s-): trade or domain knowledge: bare UN numbers, chemical names,
  biologic product types, regional foods by their native names, lab ware, industrial parts.
- **expert** (k-x-): obscure knowledge: reagents given by formula or abbreviation,
  pyrophoric metals, museum objects, cold-chain blood and cell products, niche cuisine,
  glass-ceramics.
- **misleading** (k-m-): the words on the surface point to the wrong bin, but the
  answer is clear once you understand the item.
- **compound** (k-c-): more than one bin seems to apply. Precedence picks the answer, or
  a closer look rules out the decoy bins. Each `why` names the bins involved.

In rungs 2-4, labels never contain the words cold, hazardous, fragile, refrigerated,
frozen, flammable, glass or other (checked by script).

Balance per rung:
- everyday: cold 10 | hazardous 10 | fragile 10 | other 10
- specialist: cold 10 | hazardous 10 | fragile 10 | other 10
- expert: cold 10 | hazardous 10 | fragile 10 | other 10
- misleading: cold 10 | hazardous 10 | fragile 10 | other 10
- compound: cold 10 | hazardous 10 | fragile 10 | other 10

## transliterated.json (40 items, d4-000..d4-039)
Messy foreign-language labels: romaji, romanized Russian, Hindi, Greek and Korean,
Arabic chat alphabet with digits, mixed-script labels (Latin, Cyrillic and CJK),
Cyrillic or Greek homoglyphs, and code-switched slips. 15 languages are used: Japanese,
Russian, Hindi, Arabic, Spanish, Korean, Greek, Vietnamese, German, Turkish, Mandarin,
Italian, Portuguese, Tagalog and Swahili. Each item has a `meaning` field with an
English gloss and a `form` field that describes the trick.

Balance: cold 10 | hazardous 10 | fragile 10 | other 10

## Validation
A script checked the counts, unique ids, unique labels (case-insensitive, across both
files), the bin values, label length (2-10 words), the banned words, and the per-rung
balance (8-12 per bin).
