// Seasoning audit: every savory recipe has salt (with an amount) + ≥2 seasonings; mains also have aromatics + an acid/fresh finish.
const {RAW,tagIngredient}=require('./src/recipes.js');const L=require('./src/logic.js');
const assert=(c,m)=>{if(!c){console.error('FAIL',m);process.exitCode=1}};
const SEAS=/marjoram|caraway|chives?\b|horseradish|juniper|cumin|coriander|paprika|chili|chile|chipotle|oregano|basil|thyme|rosemary|parsley|cilantro|mint|dill|bay lea|cinnamon|cardamom|turmeric|garam|masala|curry|za.atar|sumac|baharat|7-spice|shawarma|pepper|five-spice|star anise|gochu|fajita|taco seasoning|taj[íi]n|allspice|nutmeg|fennel|mustard|aleppo|herbs|vanilla|sriracha|doubanjiang|seasoning|galangal|jalape|serrano|poblano|adobo|kimchi|miso|soy sauce|fish sauce|oyster sauce|hoisin|teriyaki|tamarind|pesto|salsa|tahini|bbq|mirin|tonkatsu|yakisoba|roux|nam prik|lemongrass|ginger|garlic/i;
const AROM=/garlic|onion|shallot|ginger|scallion|leek|lemongrass|chive/i, ACID=/lemon|lime|vinegar|sumac|tamarind|yogurt|salsa|pickle|kimchi|cilantro|parsley|mint|basil|dill|scallion|taj[íi]n|pomegranate|sriracha|labneh|herbs|hot sauce|tomatillo/i;
const SWEET=new Set(['it1','md1','la2','vn8','us1','mx8']);
let sav=0,sw=0,ex=0,maxD=0;
for(const r of RAW){
  assert(r.flavor&&r.flavor.length>40,'flavor tip '+r.id);
  if(r.nocook){ex++;continue}
  const salt=r.ing.find(i=>/\bsalt\b/i.test(i.n));
  if(r.sweet){sw++;assert(salt&&salt.q>0,'pinch salt '+r.id);assert(r.ing.some(i=>/cinnamon|vanilla|taj/i.test(i.n)),'sweet spice '+r.id);continue}
  sav++;
  assert(salt&&salt.q>0&&salt.u==='tsp','salt amount '+r.id);
  const seas=new Set(r.ing.filter(i=>SEAS.test(i.n)&&!/\bsalt\b/i.test(i.n)).map(i=>i.n.toLowerCase()));
  assert(seas.size>=2,'≥2 seasonings '+r.id+' '+[...seas]);
  if(r.meal==='m'){assert(seas.size>=3,'mains ≥3 '+r.id);assert(r.ing.some(i=>AROM.test(i.n)),'aromatic '+r.id);assert(r.ing.some(i=>ACID.test(i.n)),'acid/finish '+r.id);assert(/salt/i.test(r.steps),'salt in steps '+r.id)}
  assert(/season|salt/i.test(r.flavor),'meal-prep note '+r.id);
}
// allergen tags still match ingredients (new ingredients re-tagged)
for(const r of RAW){const t=new Set();r.ing.forEach(i=>tagIngredient(i.n).a.forEach(a=>t.add(a)));for(const a of t)assert(r.allergens.includes(a),'allergen '+r.id+' '+a)}
// macros: kcal still consistent with p/c/f
RAW.forEach(r=>{const e=r.p*4+r.c*4+r.f*9;assert(Math.abs(e-r.kcal)/r.kcal<=0.12,'macro '+r.id)});
// pantry section exists and holds the spices
assert(L.SECTIONS.S&&/probably have/.test(L.SECTIONS.S),'pantry section');
assert(RAW.every(r=>r.ing.filter(i=>/kosher salt|ground cumin|black pepper/.test(i.n)).every(i=>i.sec==='S')),'spices in pantry');
console.log(`seasoning OK: ${sav} savory, ${sw} sweet, ${ex} grab-and-go exempt`);
