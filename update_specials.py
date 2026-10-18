#!/usr/bin/env python3
"""Chef Momo weekly-deals updater.

Writes specials/<store-slug>.json + specials/index.json (served from GitHub Pages next to the app).
Real data only: every file must come from a store's public weekly ad, with valid ISO dates and a source URL.
Stores without an adapter are simply skipped (the app then shows "No deals found yet for this store").

Usage
  python3 update_specials.py list                         # show known store slugs + adapters
  python3 update_specials.py fetch [SLUG ...]             # run adapters (all stores with one if no slug given)
  python3 update_specials.py import SLUG FILE --from 2026-10-12 --to 2026-10-18 --source URL [--name N --city C]
                                                          # FILE: .json list of {name,price,sec?,kw?} or .csv name,price[,sec][,kw;kw]
  python3 update_specials.py seed-js                      # seed Super King from src/specials.js (curated keywords)
  python3 update_specials.py index                        # rebuild specials/index.json only
  add --push to any command to copy specials/ into the deploy repo, commit and push
  (repo: --repo PATH, default /workspace/meal-planner-deploy)
"""
import argparse, csv, datetime as dt, html as H, json, pathlib, re, shutil, subprocess, sys, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / 'specials'
SECS = set('PMDBFG')
UA = 'Mozilla/5.0 (ChefMomo deals updater; +https://klettjamie-ai.github.io/meal-planner/)'

def slugify(s): return re.sub(r'[^a-z0-9]+', '-', s.lower().replace('&', ' and ')).strip('-')

# slug -> name, city, weekly-ad URL, adapter. Chain slugs (no city) hold chain-wide ads; the app also looks up "<chain>-<city|zip>".
STORES = {
  'superking-culvercity': dict(name='Super King Markets', city='Culver City, CA', ad='https://www.superkingmarkets.com/weekly-ad', adapter='superking'),
  'heb-austin':           dict(name='H-E-B', city='Austin, TX', ad='https://www.heb.com/weekly-ad/deals', adapter='heb'),
  'centralmarket-austin': dict(name='Central Market', city='Austin, TX', ad='https://www.centralmarket.com'),
  'wholefoods-austin':    dict(name='Whole Foods Market', city='Austin, TX', ad='https://www.wholefoodsmarket.com/sales-flyer'),
  'ralphs':      dict(name='Ralphs', city='', ad='https://www.ralphs.com/weeklyad'),
  'vons':        dict(name='Vons', city='', ad='https://www.vons.com/weeklyad'),
  'traderjoes':  dict(name="Trader Joe's", city='', ad='https://www.traderjoes.com/home/products/category/new-products'),
  'sprouts':     dict(name='Sprouts Farmers Market', city='', ad='https://shop.sprouts.com/weekly-ad'),
  'target':      dict(name='Target', city='', ad='https://www.target.com/weekly-ad'),
  'walmart':     dict(name='Walmart', city='', ad='https://www.walmart.com/shop/deals'),
  'costco':      dict(name='Costco', city='', ad='https://www.costco.com/online-offers.html'),
  'aldi':        dict(name='ALDI', city='', ad='https://www.aldi.us/weekly-specials/our-weekly-ads/'),
  'smartfinal':  dict(name='Smart & Final', city='', ad='https://www.smartandfinal.com/weekly-ad'),
}

# ad-name pattern -> recipe-ingredient keywords the app matches on (lowercase substrings of ingredient names)
KW = [
  (r'persian cucumber', ['persian cucumber']), (r'strawberr', ['strawberr']), (r'papaya', ['papaya']), (r'\bpears?\b', ['pear']),
  (r'tangerine|satsuma', ['tangerine', 'satsuma']), (r'sweet lemon', ['sweet lemon']), (r'dragon fruit', ['dragon fruit']), (r'peach', ['peach']),
  (r'anaheim', ['anaheim']), (r'\bgarlic\b', ['garlic']), (r'mushroom', ['mushroom']), (r'salad', ['salad greens']), (r'avocado(?! oil)', ['avocado']),
  (r'\blimes?\b', ['lime']), (r'\blemons?\b', ['lemon']), (r'tomato(?!.*paste)', ['tomato']), (r'\bonions?\b', ['onion']), (r'cabbage', ['cabbage']),
  (r'sirloin', ['sirloin']), (r'salmon', ['salmon']), (r'beef shank', ['beef shank']), (r'chicken breast', ['chicken breast']), (r'chicken thigh', ['chicken thigh']),
  (r'stew meat|chuck', ['stew meat', 'chuck']), (r'chicken wing', ['chicken wing']), (r'pork leg|picnic', ['pork leg']), (r'short rib|flanken', ['flanken']),
  (r'lamb shank', ['lamb shank']), (r'tilapia', ['tilapia']), (r'shrimp', ['shrimp']), (r'ground turkey', ['ground turkey']), (r'ground beef', ['ground beef']),
  (r'kielbasa', ['kielbasa']), (r'sauerkraut', ['sauerkraut']),
  (r'mozzarella', ['mozzarella']), (r'pepper jack', ['pepper jack']), (r'monterey jack', ['monterey jack']), (r'greek yogurt', ['greek yogurt']), (r'protein yogurt|20 ?g protein', ['protein yogurt']),
  (r'plain yogurt', ['plain yogurt']), (r'queso fresco', ['queso fresco']), (r'crema', ['crema']), (r'\bfeta\b', ['feta']), (r'halebi', ['halebi']), (r'string cheese', ['string cheese']),
  (r'turkey bacon', ['turkey bacon']), (r'almond (breeze|milk)', ['almond milk']), (r'prosciutto', ['prosciutto']), (r'\beggs?\b', ['eggs']),
  (r'okra', ['okra']), (r'fava', ['fava']), (r'molokhia', ['molokhia']), (r'corn tortilla', ['corn tortilla']), (r'flour tortilla|riquisima flour', ['flour tortilla']),
  (r'ciabatta', ['ciabatta']), (r'fillo|phyllo', ['fillo']), (r'\brice\b(?! vinegar)', ['white rice']), (r'olive oil', ['olive oil']), (r'avocado oil', ['avocado oil']),
  (r'\bhoney\b', ['honey']), (r'grape leaves', ['grape leaves']), (r'pepper paste|tomato paste', ['tomato paste', 'pepper paste']), (r'tahini', ['tahini']),
  (r'\bpasta\b|spaghetti', ['pasta']), (r'cashew', ['cashew']), (r'pumpkin seed', ['pumpkin seeds']), (r'pistachio', ['pistachio']), (r'walnut', ['walnut']),
  (r'buckwheat|kasha', ['buckwheat']), (r'barley', ['barley']), (r'rye bread', ['rye bread']), (r'farmer.?s cheese|twar', ['farmer']),
]
SKIP = re.compile(r'vodka|beer|wine|tequila|whisk|\bcrv\b|charcoal|water\b|seltzer|soda|chips|detergent|paper|tissue|diaper', re.I)
SEC_OF = [(r'produce|fruit|veg', 'P'), (r'meat|seafood|butcher|fish', 'M'), (r'dairy|deli|cheese|egg', 'D'), (r'bakery|bread|tortilla', 'B'), (r'frozen', 'F')]

def kw_for(name):
    n = name.lower(); out = []
    for pat, kws in KW:
        if re.search(pat, n): out += [k for k in kws if k not in out]
    return out

def guess_sec(name, cat=''):
    for pat, s in SEC_OF:
        if re.search(pat, cat, re.I): return s
    n = name.lower()
    if re.search(r'beef|chicken|pork|lamb|salmon|tilapia|shrimp|fish|turkey(?! bacon)|kielbasa', n): return 'M'
    if re.search(r'cheese|yogurt|milk|egg|crema|queso|bacon|prosciutto|feta|halebi', n): return 'D'
    if re.search(r'tortilla|bread|ciabatta|bun|pita|lavash', n): return 'B'
    if re.search(r'frozen', n): return 'F'
    if re.search(r'lb$|cucumber|berr|papaya|pear|peach|lemon|lime|chili|garlic|mushroom|salad|tomato|onion|avocado(?! oil)|fruit|tangerine', n): return 'P'
    return 'G'

def http_get(url):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=30) as r: return r.read().decode('utf-8', 'ignore')

def us_date(s):  # 10/12/26 -> 2026-10-12
    m, d, y = [int(x) for x in s.split('/')]; y += 2000 if y < 100 else 0
    return dt.date(y, m, d).isoformat()

# ---------- adapters: return dict(validFrom, validTo, source, items=[{name, price, sec, kw}]) from the store's PUBLIC ad ----------
def adapter_superking(slug, meta):
    url = meta['ad']; h = http_get(url)
    m = re.search(r'Prices valid (\d{1,2}/\d{1,2}/\d{2,4}) through (\d{1,2}/\d{1,2}/\d{2,4})', h)
    if not m: raise RuntimeError('validity dates not found on ad page')
    items, cat = [], ''
    for part in re.split(r'(<h3>.*?</h3>)', h[h.find('skwa-textlist'):]):
        if part.startswith('<h3>'): cat = H.unescape(re.sub(r'<[^>]+>', '', part)); continue
        for nm, pr in re.findall(r'skwa-tl-name">(.*?)</span>\s*<span class="skwa-tl-price">(.*?)</span>', part, re.S):
            nm, pr = H.unescape(nm).strip(), H.unescape(pr).strip()
            if SKIP.search(nm + ' ' + pr): continue
            kw = kw_for(nm)
            if kw: items.append(dict(name=nm, price=pr, sec=guess_sec(nm, cat), kw=kw))
    return dict(validFrom=us_date(m.group(1)), validTo=us_date(m.group(2)), source=url, items=items)

def adapter_heb(slug, meta):
    """H-E-B's weekly ad is store-specific (zone picked by your H-E-B store) and heb.com sits behind Imperva/Incapsula bot
    protection: scripted requests get a ~200-byte challenge page or 'errorCode 15'. We don't try to get around that.
    If the page ever comes back with real content, parse it; otherwise fail cleanly and keep the previous file.
    Fallback: export the Austin-store ad by hand (My H-E-B app / heb.com with your store selected) to CSV and run
      update_specials.py import heb-austin heb.csv --from YYYY-MM-DD --to YYYY-MM-DD --source https://www.heb.com/weekly-ad/deals"""
    h = http_get(meta['ad'])
    if 'Incapsula' in h or '"errorCode"' in h or len(h) < 2000:
        raise RuntimeError('heb.com blocked automated access (Incapsula bot protection). Import a CSV from the Austin-store ad instead (see adapter_heb docstring).')
    m = re.search(r'Prices good (?:\w+, )?(\w+ \d{1,2})(?:, (\d{4}))? (?:thru|through) (?:\w+, )?(\w+ \d{1,2}), (\d{4})', h)
    if not m: raise RuntimeError('page loaded but validity dates not found; refusing to guess')
    y = m.group(4); f = dt.datetime.strptime(f"{m.group(1)} {m.group(2) or y}", '%B %d %Y').date(); t = dt.datetime.strptime(f"{m.group(3)} {y}", '%B %d %Y').date()
    items = []
    for nm, pr in re.findall(r'"name":"([^"]{3,120})".{0,400}?"(?:salePrice|price)":"?(\$?[\d.]+[^",]{0,20})', h, re.S):
        if SKIP.search(nm): continue
        kw = kw_for(nm)
        if kw: items.append(dict(name=H.unescape(nm), price=pr if pr.startswith('$') else '$' + pr, sec=guess_sec(nm), kw=kw))
    return dict(validFrom=f.isoformat(), validTo=t.isoformat(), source=meta['ad'], items=items)

ADAPTERS = {'superking': adapter_superking, 'heb': adapter_heb}

# ---------- validation + writing ----------
PRICE_RX = re.compile(r'(\$\d|\d+¢|\d+ for \$|free)', re.I)
def validate(slug, d):
    errs = []
    try:
        f, t = dt.date.fromisoformat(d['validFrom']), dt.date.fromisoformat(d['validTo'])
        if f > t: errs.append('validFrom after validTo')
        if (t - f).days > 45: errs.append('validity window > 45 days')
    except Exception as e: errs.append(f'bad dates: {e}')
    if not re.match(r'^https?://', d.get('source') or ''): errs.append('source must be an http(s) URL')
    if not d.get('items'): errs.append('no items')
    for i, it in enumerate(d.get('items', [])):
        if not it.get('name') or not PRICE_RX.search(it.get('price', '')): errs.append(f'item {i}: needs name and a real price ({it})')
        if it.get('sec') not in SECS: errs.append(f'item {i}: sec must be one of {sorted(SECS)}')
        if not isinstance(it.get('kw'), list) or not all(isinstance(k, str) and k and k == k.lower() for k in it['kw']): errs.append(f'item {i}: kw must be a list of lowercase strings (empty = shown but never matched)')
    if errs: raise SystemExit(f'[{slug}] invalid, nothing written:\n  ' + '\n  '.join(errs[:20]))

def write_store(slug, d, meta=None):
    meta = meta or STORES.get(slug, {})
    doc = dict(store=slug, name=d.get('name') or meta.get('name', slug), city=d.get('city', meta.get('city', '')),
               validFrom=d['validFrom'], validTo=d['validTo'], source=d['source'],
               fetched=d.get('fetched') or dt.date.today().isoformat(), updated=dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
               items=[dict(name=it['name'], price=it['price'], sec=it['sec'], kw=it['kw']) for it in d['items']])
    validate(slug, doc); OUT.mkdir(exist_ok=True)
    (OUT / f'{slug}.json').write_text(json.dumps(doc, ensure_ascii=False, indent=1) + '\n')
    print(f'wrote specials/{slug}.json: {len(doc["items"])} items, valid {doc["validFrom"]}..{doc["validTo"]}')

def build_index():
    OUT.mkdir(exist_ok=True); stores = {}
    for p in sorted(OUT.glob('*.json')):
        if p.name == 'index.json': continue
        d = json.loads(p.read_text())
        stores[d['store']] = dict(name=d['name'], city=d.get('city', ''), validFrom=d['validFrom'], validTo=d['validTo'], items=len(d['items']), updated=d['updated'], source=d['source'], file=p.name)
    idx = dict(version=1, updated=dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), stores=stores)
    (OUT / 'index.json').write_text(json.dumps(idx, ensure_ascii=False, indent=1) + '\n'); print(f'index.json: {len(stores)} store(s)')

def push(repo):
    repo = pathlib.Path(repo); dst = repo / 'specials'; dst.mkdir(exist_ok=True)
    for p in OUT.glob('*.json'): shutil.copy(p, dst / p.name)
    for dd in [ROOT / 'dist' / 'specials']:
        dd.mkdir(parents=True, exist_ok=True); [shutil.copy(p, dd / p.name) for p in OUT.glob('*.json')]
    subprocess.run(['git', '-C', str(repo), 'add', 'specials'], check=True)
    if subprocess.run(['git', '-C', str(repo), 'diff', '--cached', '--quiet']).returncode == 0: print('no changes to push'); return
    subprocess.run(['git', '-C', str(repo), 'commit', '-qm', f'Weekly deals update {dt.date.today().isoformat()}'], check=True)
    subprocess.run(['git', '-C', str(repo), 'push', '-q', 'origin', 'HEAD'], check=True); print('pushed')

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['list', 'fetch', 'import', 'seed-js', 'index'])
    ap.add_argument('args', nargs='*'); ap.add_argument('--from', dest='vf'); ap.add_argument('--to', dest='vt'); ap.add_argument('--source')
    ap.add_argument('--name'); ap.add_argument('--city'); ap.add_argument('--push', action='store_true'); ap.add_argument('--repo', default='/workspace/meal-planner-deploy')
    a = ap.parse_args(); bad = 0
    if a.cmd == 'list':
        for s, m in STORES.items(): print(f'{s:24} {m["name"]:24} {m["city"] or "(chain-wide)":18} adapter={m.get("adapter") or "-"}')
        return
    if a.cmd == 'fetch':
        for slug in (a.args or [s for s, m in STORES.items() if m.get('adapter')]):
            m = STORES.get(slug) or sys.exit(f'unknown slug {slug}')
            if not m.get('adapter'): print(f'[{slug}] no adapter yet; skipped'); continue
            try: write_store(slug, ADAPTERS[m['adapter']](slug, m))
            except (Exception, SystemExit) as e: bad += 1; print(f'[{slug}] FAILED, kept previous file: {e}')
    elif a.cmd == 'import':
        slug, fn = a.args[0], pathlib.Path(a.args[1])
        if fn.suffix == '.json': items = json.loads(fn.read_text())
        else: items = [dict(name=r[0], price=r[1], sec=(r[2] if len(r) > 2 and r[2] else guess_sec(r[0])), kw=(r[3].split(';') if len(r) > 3 and r[3] else kw_for(r[0]))) for r in csv.reader(fn.open()) if r and r[0] != 'name']
        for it in items: it.setdefault('sec', guess_sec(it['name'])); it.setdefault('kw', kw_for(it['name']))
        items = [it for it in items if it['kw']]
        write_store(slug, dict(validFrom=a.vf, validTo=a.vt, source=a.source, items=items, name=a.name, city=a.city or ''), STORES.get(slug, {'name': a.name or slug, 'city': a.city or ''}))
    elif a.cmd == 'seed-js':
        js = subprocess.run(['node', '-e', "const {SK_SPECIALS}=require('./src/specials.js');console.log(JSON.stringify(SK_SPECIALS))"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
        d = json.loads(js); write_store('superking-culvercity', d)
    build_index()
    if a.push: push(a.repo)
    if bad: sys.exit(1)

if __name__ == '__main__': main()
