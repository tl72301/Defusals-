# v2 test item bank: authoring notes

## How it was built

- Written by hand as an independent test bank. The only existing files consulted were
  `bank/contents.json` and `bank/messy.json`, read to copy the JSON format and to avoid
  reusing their items or close variants of the same concept. No baseline code, baseline
  output, review notes or git history were consulted.
- Each item was checked against the four bin definitions shown to players and the
  precedence order Hazardous > Cold > Fragile > Everything else. Labels were qualified
  ("unopened", "raw", "empty", "solvent-based", "deli", "plastic jar of") where the answer
  could otherwise depend on brand, packaging, formulation or region.
- `contents.json`: 160 items (`t-c000` to `t-c159`), 40 per bin. In each bin at least 25
  labels contain none of the obvious category words (glass, frozen, fresh, battery,
  flammable, fragile, ceramic, porcelain, crystal, chilled, ice, refrigerated, toxic, acid,
  poison, spray, gas, fuel). Counts free of those words (substring match): cold 34,
  hazardous 28, fragile 27, other 34. The "other" bin includes some items whose label
  contains a misleading category word but which are sturdy and safe (ice skates, silicone
  ice cube trays, acid-free paper, empty spray bottle, fiberglass ladder, Frozen-themed
  lunchbox), and shelf-stable versions of foods that are often refrigerated (UHT milk,
  powdered milk, canned tuna, beef jerky).
- `messy.json`: 160 items (`t-m000` to `t-m159`), 40 per bin. Each bin has 20
  foreign-language labels and 20 messy English shipping-slip labels (misspellings,
  dropped vowels, run-together words, count and unit codes such as `8ct`, `1dz`, `12oz`,
  `x6`, `sz7`). No Spanish, French, German, Italian or Portuguese.
- Validated with a short script: both files parse, exactly 40 items per bin, ids unique
  and sequential, no label (case-insensitive) repeats another label in v2 or in the v1
  files.

## Languages in messy.json (80 foreign-language items)

| Language | Script | Items |
|---|---|---|
| Japanese | Kanji/kana | 9 |
| Chinese | Hanzi | 8 |
| Korean | Hangul | 8 |
| Hindi | Devanagari | 8 |
| Russian | Cyrillic | 7 |
| Arabic | Arabic | 6 |
| Turkish | Latin | 6 |
| Dutch | Latin | 6 |
| Greek | Greek | 5 |
| Polish | Latin | 5 |
| Swedish | Latin | 4 |
| Vietnamese | Latin | 4 |
| Indonesian | Latin | 4 |

The remaining 80 items are messy English.

## Items that rely on the precedence rule (contents.json)

| id | label | bin | why |
|---|---|---|---|
| t-c038 | crème brûlée in ceramic ramekins | cold | needs refrigeration; Cold before Fragile |
| t-c039 | trifle in a glass serving bowl | cold | needs refrigeration; Cold before Fragile |
| t-c064 | mercury thermometer | hazardous | toxic mercury in glass; Hazardous before Fragile |
| t-c065 | glass jar of white phosphorus | hazardous | ignites in air, toxic; Hazardous before Fragile |
| t-c068 | nail polish in a glass bottle | hazardous | flammable; Hazardous before Fragile |
| t-c069 | perfume in a crystal bottle | hazardous | alcohol-based, flammable; Hazardous before Fragile |
| t-c070 | glass ampoules of bromine | hazardous | toxic and corrosive; Hazardous before Fragile |
| t-c072 | glass bottle of nitric acid | hazardous | corrosive; Hazardous before Fragile |

No messy.json item depends on the precedence rule.
