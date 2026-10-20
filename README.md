# Chef Momo: weekly meal planner

Open `index.html` in a browser. It's a single self-contained file that works offline, and all data is saved in localStorage (`fitplan.meals.v1`).
Source is in `src/` (recipes.js, specials.js, logic.js, ui.js, body.html, style.css). Run `python3 build.py` to rebuild index.html.
Tests: `node test.js` (logic: 234 plan combos) and `.venv-pw/bin/python e2e.py` (browser flow).

Features
- Daily targets (kcal / protein / fat %), with an "Import from FitPlan" button that reads FitPlan's `fitplan.v1` data from the same browser and origin.
- Cooking-skill quiz (11 questions) → Beginner / Intermediate / Advanced. You can retake it or override the level manually. Plans use recipes at or below your level, plus an optional ⭐ stretch recipe (one level up, Sunday dinner, with tips).
- Per-week cuisine picker: 13 cuisines, or ✨ Recommend. Recommend skips the previous 2 weeks' cuisines and explains its pick: protein/fat fit, recipes at your level, specials used, and store strengths.
- Multi-week: week selector with ‹ › arrows, saved history tab, delete.
- 140 recipes, each tagged with cuisine, meal type, difficulty, active/total time, techniques and equipment.
- Stores: search/type any store + city/ZIP (presets: Super King Culver City, H-E-B / Central Market / Whole Foods Austin, Ralphs, Vons, Trader Joe's, Sprouts, Target, Walmart, Costco, ALDI, Smart & Final). Pick several: the planner uses the best sale price per item across them and the grocery list groups by store.
- Specials panel preloaded from the Super King weekly ad (valid 10/12/26–10/18/26). Edit/add/clear, set validity dates.
  Specials only apply when the shopping day falls inside the valid window.
- Grocery list by section with sale prices and checkboxes; prep guide with cook schedule, beginner tips, stretch tips, food safety and full recipe cards.


## Weekly deals (`specials/`)

The app is static, so it never scrapes stores itself. On load it fetches `specials/index.json` and then `specials/<store-slug>.json`
for each selected store from this same GitHub Pages site (cached by the service worker for offline use). Each store card shows
"Deals updated <date>" or "No deals found yet for this store". Your own edits in Settings → Deals override the published file.

**Store slugs.** Fixed-location presets: `superking-culvercity`, `heb-austin`, `centralmarket-austin`, `wholefoods-austin`.
Chains: `ralphs`, `vons`, `traderjoes`, `sprouts`, `target`, `walmart`, `costco`, `aldi`, `smartfinal`. A chain picked with a
city/ZIP looks up `<chain>-<city-or-zip>` first (e.g. `ralphs-90230`, `vons-culver-city-ca`), then the chain-wide file.
Typed-in stores use `slugify(name)-slugify(city)` (lowercase, non-alphanumerics → `-`, `&` → `and`).

**`specials/index.json`**
```json
{ "version": 1, "updated": "2026-10-18T04:57:31Z",
  "stores": { "superking-culvercity": { "name": "Super King Markets", "city": "Culver City, CA", "validFrom": "2026-10-12",
              "validTo": "2026-10-18", "items": 58, "updated": "2026-10-18T04:57:31Z",
              "source": "https://www.superkingmarkets.com/weekly-ad", "file": "superking-culvercity.json" } } }
```
**`specials/<slug>.json`**
```json
{ "store": "superking-culvercity", "name": "Super King Markets", "city": "Culver City, CA",
  "validFrom": "2026-10-12", "validTo": "2026-10-18",            // ISO dates from the ad, validFrom ≤ validTo, ≤ 45 days
  "source": "https://www.superkingmarkets.com/weekly-ad",          // public ad URL (required)
  "fetched": "2026-10-17", "updated": "2026-10-18T04:57:31Z",
  "items": [ { "name": "Salmon Fillet", "price": "$7.99 lb", "sec": "M", "kw": ["salmon"] } ] }
```
`price` is the ad text (`$4.99 lb`, `69¢ lb`, `2 for $3`, `$2.99 (must buy 2)`); `sec` is P/M/D/B/F/G; `kw` are lowercase
substrings matched against recipe ingredient names (empty = listed but never matched).

**Updater: `update_specials.py`** (real data only; invalid data is refused and the previous file is kept)
```
python3 update_specials.py list                        # slugs + which have adapters
python3 update_specials.py fetch [slug ...] --push     # run store adapters (Super King parses its public text ad list)
python3 update_specials.py import ralphs-90230 ad.csv --from 2026-10-15 --to 2026-10-21 --source https://www.ralphs.com/weeklyad --push
python3 update_specials.py seed-js                     # seed Super King from src/specials.js
```
A weekly job (e.g. cron / GitHub Action, Wednesdays) runs `fetch --push`; it rewrites `index.json` and commits to the Pages repo.
To support a new store, add an `adapter_<name>(slug, meta)` that returns `{validFrom, validTo, source, items}` from its public ad.

### H-E-B (heb-austin)
`update_specials.py fetch heb-austin` runs `adapter_heb`, but heb.com is behind Imperva/Incapsula bot protection (scripted requests get 403 or a challenge page), and the ad is zone-specific per store. The adapter fails cleanly and publishes nothing rather than guess. To publish real Austin deals, export the ad with an Austin store selected to CSV (`name,price,sec,kw`) and run
`python3 update_specials.py import heb-austin heb.csv --from 2026-10-21 --to 2026-10-27 --source https://www.heb.com/weekly-ad/deals --push`.

## Veggies preference
Normal / More veggies / Lots of veggies (wizard cuisine step + Settings). Every recipe has `veg` (servings per portion; 1 serving ≈ ½ cup chopped or 1 cup leafy ≈ 80 g, from `vegG()` rules in recipes.js). More/Lots: `vegBoost()` scales veg ingredients in mains ×1.5/×2 (breakfasts with veg half as much) and trims rice/noodles/potato/grains (≤35%) so calories stay flat; the planner also favors veg-heavy recipes and adds a cuisine-fitting side (11 `vs*` recipes, meal `v`) on days under 7/10 servings. Variety: each veg ingredient has a key + family (leafy, cruciferous, red/orange, alliums, squash, pods, mushrooms, roots; `vegKey()`); More/Lots fold 1/2 new cuisine-matched vegetables into each main (`ADDINS`, rotating per recipe, allergen-free, skips disliked items) and pick sides that add new vegetables, each side ≤2×/week. Targets: Normal 6+, More 10+, Lots 14+ different veggies/week. Plan shows "🌈 X different veggies this week" + family icons. Plan shows "🥦 N servings veggies" per day. Grocery, Prep batch amounts (🥦 marks boosted items, "(trimmed)" starches) and cost all follow. Tests: `node test-veg.js`.

## Units
Displayed amounts never use cups/tbsp/tsp/bunches. Liquids show as volume (ml/L or fl oz/qt/gal) and solids (spices, salt, herbs, grains, chopped veg) as weight (g/kg or oz/lb), converted with a density table (`measure()` / `unitText()` in src/logic.js). Countable items keep their count, and eggs and tortillas also show a weight. Grocery amounts round up. `node test-units.js` checks 84 plans in both unit systems.

## Pregnancy & postpartum
When sex is female, the profile has an optional stage: Not pregnant, Pregnant (trimester 1, 2 or 3, plus pre-pregnancy weight), or Postpartum (breastfeeding yes/no, weeks since birth). You can change it in Settings.
- **Calories:** pregnancy adds +0 / +340 / +452 kcal by trimester, with no loss goal and a minimum of 1,800 kcal. A gain range is shown based on pre-pregnancy BMI (IOM/ACOG). Breastfeeding adds +330 kcal (+400 after 6 months), with a minimum of 1,800 kcal. Postpartum loss is capped at 1 lb/wk and starts only after about 8 weeks if breastfeeding (6 weeks otherwise).
- **Protein:** at least 71 g, or 1.1 g/kg in pregnancy and 1.3 g/kg while breastfeeding.
- **Food safety:** `stagePool()` in logic.js applies CDC/FDA pregnancy food-safety rules. It removes raw or undercooked dishes, cold cured meats, high-mercury fish and liver. It rewrites cooking steps where needed (eggs cooked firm, meats to safe temperatures, cooked sprouts). It switches cheese to pasteurized, replaces queso fresco with pasteurized feta, and swaps out alcohol.
- **Fish:** `ensureFish()` keeps pregnancy weeks at 2–3 servings (8–12 oz) of low-mercury fish.
- **Plan view:** shows a badge, per-day nutrient chips and a "Why" section with sources and a disclaimer.
- **Postpartum plans** favor warming soups, iron, oats and one-hand snacks.

`node test-preg.js` runs the checks above.

## Find stores near me
The store picker in the wizard and in Settings can search by street address, or use the browser's location. It geocodes with OpenStreetMap Nominatim, then queries Overpass for shop=supermarket|grocery|greengrocer within about 5 mi, widening to 10 and then 20 mi if fewer than 5 stores are found.
- Searches only run when you press Search (nothing is sent per keystroke). OSM requests are at least 1.1 s apart, and results are cached.
- Known chains are mapped to existing store keys so deals attach (Super King Culver City, H-E-B, Central Market and Whole Foods in Austin, Ralphs, Vons, Trader Joe's, Sprouts and others).
- The address is kept only in localStorage.
- `node test-near.js` uses a mocked network; `e2e_near.py` uses mocked routes, or the real APIs when given a URL.

## Mise en place
Each recipe group folds into a "✅ … — all N ready" row once all its items are checked, and opens again when tapped. When everything is checked, the whole section folds to "✅ All ingredients ready" and the timeline scrolls into view. Unchecking an item opens it again. The fold state is saved with the checkboxes, and "Clear checks" resets everything. Covered by `e2e_mise.py`.

## Poland / Warsaw
- Store search geocodes US and Polish addresses (diacritics fine, e.g. "Marszałkowska 104, Warszawa") and also finds `shop=convenience` (Żabka; max 10 per search so supermarkets aren't crowded out) and `shop=discount`.
- Polish chain presets/brand mapping: Biedronka, Lidl, Żabka, Carrefour, Auchan, Kaufland, Dino, Netto, Stokrotka, ALDI, Frisco (online) → slugs `biedronka-pl`, `lidl-pl`, … (city appended, e.g. `biedronka-pl-warszawa`).
- Currency: if your main store is Polish, costs show in zł. Regular prices are US estimates converted at a fixed **1 USD = 3.90 zł** (NBP mid-rate 19 Oct 2026, rounded) and labeled as estimates; leaflet sale prices are real zł.
- Deals: Lidl gazetka 19–21.10.2026 (official leaflet data) and Biedronka 19–21.10.2026 (via gazetkowo.pl summary), with source and dates. Newer leaflets can be published as `specials/<slug>.json` (same format, `"currency":"PLN"`, prices like `"4,99 zł/kg"`).
