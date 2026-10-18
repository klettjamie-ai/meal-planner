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
Normal / More veggies / Lots of veggies (wizard cuisine step + Settings). Every recipe has `veg` (servings per portion; 1 serving ≈ ½ cup chopped or 1 cup leafy ≈ 80 g, from `vegG()` rules in recipes.js). More/Lots: `vegBoost()` scales veg ingredients in mains ×1.5/×2 (breakfasts with veg half as much) and trims rice/noodles/potato/grains (≤35%) so calories stay flat; the planner also favors veg-heavy recipes and adds a cuisine-fitting side (11 `vs*` recipes, meal `v`) on days under 7/10 servings. Plan shows "🥦 N servings veggies" per day. Grocery, Prep batch amounts (🥦 marks boosted items, "(trimmed)" starches) and cost all follow. Tests: `node test-veg.js`.
