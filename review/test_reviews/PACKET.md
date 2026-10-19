# Test-split reviews to confirm

**Do the blind integrality packet first** (`review/integrality_blind/`): 5 of these problems are in it, and this packet shows their labels.

All 62 test-split hand reviews are Claude's and unconfirmed. They're ordered least sure first. For each, mark `confirmed` or `disputed` (with a word on why) in `marks.csv`. A confirmed review stays as it is; a disputed one gets discussed before any test run.

## 1. `431521997`: degenerate-text (sureness: low)

**Why I'm not sure:** do-nothing only because 'must be large than' is modeled as >=; read strictly over integers the optimum is 36 (3 mango, 2 lychee). The rule labels it continuous only because it matched 'units of lychee' juice, though bubble teas are counted.

> A bubble tea shop sells mango and lychee bubble tea. Each mango bubble tea requires 4 units of mango juice and 8 units of tea. Each lychee bubble tea requires 6 units of lychee juice and 6 units of tea. The shop has available 2000 units of mango juice and 3000 units of lychee juice. At least 40% of the bubble teas made must be lychee flavored. However, mango bubble tea sells better and thus the number of mango bubble teas made must be large than the number of lychee bubble teas made. How many of each bubble tea flavor should be made to minimize the total amount of tea needed?

```
min 8*[mango bubble tea] + 6*[lychee bubble tea]
  c0_linear: 4*[mango bubble tea] <= 2000
  c1_linear: 6*[lychee bubble tea] <= 3000
  c2_ratio: 0.6*[lychee bubble tea] - 0.4*[mango bubble tea] >= 0
  c3_xy: 1*[mango bubble tea] - 1*[lychee bubble tea] >= 0
  every variable >= 0
```

**LP:** 0 (lychee bubble tea = 0, mango bubble tea = 0)  
**IP:** 0 (lychee bubble tea = 0, mango bubble tea = 0)

- Integrality label: **continuous** (rule: says 'units of lychee')
- Note (unlisted-variable): c0_linear: ['lychee bubble tea'] not listed, so coefficient 0 (the official converter: 1)
- Note (unlisted-variable): c1_linear: ['mango bubble tea'] not listed, so coefficient 0 (the official converter: 1)
- Note (strict-wording): c3_xy: text says 'large than' (strict); modeled as >=
- **My review (degenerate-text):** nothing has to be made, so making nothing (objective 0) is optimal as written; each unlisted coefficient really is 0: the resource is used by one product only

## 2. `1151835649`: degenerate-text (sureness: low)

**Why I'm not sure:** do-nothing only because 'must be larger than' is modeled as >=; the strict reading gives 26 (2 brownies, 3 lemon squares).

> A bakery makes fiber supplemented brownies and lemon squares. Each brownie requires 5 units of chocolate mix and 4 units of fiber. Each lemon square requires 7 units of lemon mix and 6 units of fiber. Lemon squares sell much faster and thus the number of lemon squares made must be larger than the number of brownies made. However, to please all customers, at least 40% of the items made must be brownies. If the bakery has 2500 units of chocolate mix and 3300 units of lemon mix, how many of each should be made to minimize the total amount of fiber needed?

```
min 4*[brownies] + 6*[lemon squares]
  c0_xy: 1*[lemon squares] - 1*[brownies] >= 0
  c1_ratio: 0.6*[brownies] - 0.4*[lemon squares] >= 0
  c2_linear: 5*[brownies] <= 2500
  c3_linear: 7*[lemon squares] <= 3300
  every variable >= 0
```

**LP:** 0 (brownies = 0, lemon squares = 0)  
**IP:** 0 (brownies = 0, lemon squares = 0)  
**IP, strict reading:** 26 (brownies = 2, lemon squares = 3) (c0_xy: >= 0 became >= 1)

- Integrality label: **integer** (rule: counts whole things)
- Note (strict-wording): c0_xy: text says 'larger than' (strict); modeled as >=
- Note (unlisted-variable): c2_linear: ['lemon squares'] not listed, so coefficient 0 (the official converter: 1)
- Note (unlisted-variable): c3_linear: ['brownies'] not listed, so coefficient 0 (the official converter: 1)
- **My review (degenerate-text):** nothing has to be made, so making nothing (objective 0) is optimal as written; each unlisted coefficient really is 0: the resource is used by one product only

## 3. `1605420061`: degenerate-text (sureness: low)

**Why I'm not sure:** do-nothing only because 'must exceed' is modeled as >=; read strictly over integers the optimum is 20 (1 chocolate, 2 peanut butter). The rule labels it continuous only because it matched 'units of chocolate' spread, though crepes are counted.

> A crepe store sells chocolate and peanut butter crepes. A chocolate crepe requires 3 units of chocolate spread and 6 units of crepe mix. A peanut butter crepe requires 4 units of peanut butter spread and 7 units of crepe mix. Recently, the peanut butter crepe has been more popular and therefore the number of peanut butter crepes made must exceed the number of chocolate crepes made. However at least 25% of the crepes made should be chocolate. The store has available 400 units of chocolate spread and 450 units of peanut butter spread. How many of each should the store make to minimize the total amount of crepe mix needed?

```
min 6*[chocolate crepe] + 7*[peanut butter crepes]
  c0_xy: 1*[peanut butter crepes] - 1*[chocolate crepe] >= 0
  c1_ratio: -0.25*[peanut butter crepes] + 0.75*[chocolate crepe] >= 0
  c2_linear: 3*[chocolate crepe] <= 400
  c3_linear: 4*[peanut butter crepes] <= 450
  every variable >= 0
```

**LP:** 0 (peanut butter crepes = 0, chocolate crepe = 0)  
**IP:** 0 (peanut butter crepes = 0, chocolate crepe = 0)

- Integrality label: **continuous** (rule: says 'units of chocolate')
- Note (strict-wording): c0_xy: text says 'must exceed' (strict); modeled as >=
- Note (unlisted-variable): c2_linear: ['peanut butter crepes'] not listed, so coefficient 0 (the official converter: 1)
- Note (unlisted-variable): c3_linear: ['chocolate crepe'] not listed, so coefficient 0 (the official converter: 1)
- **My review (degenerate-text):** nothing has to be made, so making nothing (objective 0) is optimal as written; each unlisted coefficient really is 0: the resource is used by one product only

## 4. `-1540907330`: degenerate-text (sureness: low)

**Why I'm not sure:** do-nothing only because 'must be larger than' is modeled as >=; read strictly over integers the optimum is 17 (2 goat, 1 chicken). The rule labels it continuous only because it matched 'units of chicken' meat, though bowls are counted.

> An Indian restaurant makes goat and chicken curry. Each bowl of goat curry requires 3 units of goat meat and 6 units of the curry base. Each bowl of chicken curry requires 5 units of chicken meat and 5 units of the curry base. The restaurant has available 1500 units of goat meat and 2000 units of chicken meat. At least 25% of the bowls made must be chicken curry. Since goat curry is more popular, the number of goat curry bowls must be larger than the number of chicken curry bowls. How many of each type of curry bowl should be made to minimize the total amount of curry base used?

```
min 6*[goat] + 5*[chicken]
  c0_linear: 3*[goat] <= 1500
  c1_linear: 5*[chicken] <= 2000
  c2_ratio: -0.25*[goat] + 0.75*[chicken] >= 0
  c3_xy: 1*[goat] - 1*[chicken] >= 0
  every variable >= 0
```

**LP:** 0 (goat = 0, chicken = 0)  
**IP:** 0 (goat = 0, chicken = 0)

- Integrality label: **continuous** (rule: says 'units of chicken')
- Note (unlisted-variable): c0_linear: ['chicken'] not listed, so coefficient 0 (the official converter: 1)
- Note (unlisted-variable): c1_linear: ['goat'] not listed, so coefficient 0 (the official converter: 1)
- Note (strict-wording): c3_xy: text says 'must be larger than' (strict); modeled as >=
- **My review (degenerate-text):** nothing has to be made, so making nothing (objective 0) is optimal as written; each unlisted coefficient really is 0: the resource is used by one product only

## 5. `1268238141`: degenerate-text (sureness: low)

**Why I'm not sure:** do-nothing only because 'must be larger than' is modeled as >=; the strict reading gives 14 (2 peach, 1 cherry).

> A candy company is making peach flavored candy and cherry flavored candy. Each pack of peach flavored candy requires 3 units of peach flavoring and 5 units of special syrup. Each pack of cherry flavored candy requires 5 units of cherry flavoring and 4 units of special syrup. The company has available 3000 units of peach flavoring and 4000 units of cherry flavoring. Peach candy is much more popular and thus the number of peach candy packs must be larger than the number of cherry candy packs. In addition, at least 30% of the pack must be cherry flavored. How many of each should be made to minimize the total amount of special syrup used?

```
min 5*[peach flavored candy] + 4*[cherry flavored candy]
  c0_linear: 3*[peach flavored candy] <= 3000
  c1_linear: 5*[cherry flavored candy] <= 4000
  c2_xy: 1*[peach flavored candy] - 1*[cherry flavored candy] >= 0
  c3_ratio: -0.3*[peach flavored candy] + 0.7*[cherry flavored candy] >= 0
  every variable >= 0
```

**LP:** 0 (peach flavored candy = 0, cherry flavored candy = 0)  
**IP:** 0 (peach flavored candy = 0, cherry flavored candy = 0)  
**IP, strict reading:** 14 (peach flavored candy = 2, cherry flavored candy = 1) (c2_xy: >= 0 became >= 1)

- Integrality label: **integer** (rule: counts whole things)
- Note (unlisted-variable): c0_linear: ['cherry flavored candy'] not listed, so coefficient 0 (the official converter: 1)
- Note (unlisted-variable): c1_linear: ['peach flavored candy'] not listed, so coefficient 0 (the official converter: 1)
- Note (strict-wording): c2_xy: text says 'larger than' (strict); modeled as >=
- **My review (degenerate-text):** nothing has to be made, so making nothing (objective 0) is optimal as written; each unlisted coefficient really is 0: the resource is used by one product only

## 6. `1384123609`: degenerate-text (sureness: low)

**Why I'm not sure:** 'must perform two types of experiments' may mean at least one of each (then the optimum is 5, one of each), not a degenerate text.

> A researcher must perform two types of experiments, in-vivo and ex-vivo. In-vivo experiments requires 30 minutes to prepare and 60 minutes to execute. Ex-vivo experiments require 45 minutes to prepare and 30 minutes to execute. In addition, in-vivo experiments gives the researcher 2 units of radiation while ex-vivo experiments give the researcher 3 unites of radiation. At most 400 minutes can be used for preparation and 500 minutes for execution of the experiment. How many of each experiment should be scheduled by the researcher to minimize the total radiation received by the researcher?

```
min 2*[in-vivo] + 3*[ex-vivo]
  c0_linear: 30*[in-vivo] + 45*[ex-vivo] <= 400
  c1_linear: 60*[in-vivo] + 30*[ex-vivo] <= 500
  every variable >= 0
```

**LP:** 0 (in-vivo = 0, ex-vivo = 0)  
**IP:** 0 (in-vivo = 0, ex-vivo = 0)

- Integrality label: **integer** (rule: counts whole things)
- **My review (degenerate-text):** 'must perform' suggests at least one of each, but no number is given; as written the optimum is to do nothing

## 7. `-685300642`: degenerate-text (sureness: low)

**Why I'm not sure:** do-nothing only because 'more orange sorbet' is modeled as >=; the strict reading gives 10 (1 matcha, 2 sorbet).

> A dessert shop is popular for their only two desserts - matcha ice cream and orange sorbet. Two units of flavouring and four units of ice cream is required to make one order of matcha ice cream. Four units of flavouring and three units of water is required to make an order of orange sorbet. The dessert shop has recently been getting more orders online for orange sorbet and therefore, there should be more orange sorbet made than matcha ice cream. However, at least fifteen percent of desserts made must be matcha ice cream. The dessert shop has available 600 units of ice cream and 550 units of water. How many of each dessert should the shop make to minimize the total amount of flavouring needed?

```
min 2*[matcha ice cream] + 4*[orange sorbet]
  c0_xy: 1*[orange sorbet] - 1*[matcha ice cream] >= 0
  c1_ratio: 0.85*[matcha ice cream] - 0.15*[orange sorbet] >= 0
  c2_linear: 4*[matcha ice cream] <= 600
  c3_linear: 3*[orange sorbet] <= 550
  every variable >= 0
```

**LP:** 0 (matcha ice cream = 0, orange sorbet = 0)  
**IP:** 0 (matcha ice cream = 0, orange sorbet = 0)  
**IP, strict reading:** 10 (matcha ice cream = 1, orange sorbet = 2) (c0_xy: >= 0 became >= 1)

- Integrality label: **integer** (rule: counts whole things)
- Note (strict-wording): c0_xy: text says 'more' (strict); modeled as >=
- Note (unlisted-variable): c2_linear: ['orange sorbet'] not listed, so coefficient 0 (the official converter: 1)
- Note (unlisted-variable): c3_linear: ['matcha ice cream'] not listed, so coefficient 0 (the official converter: 1)
- **My review (degenerate-text):** nothing has to be made, so making nothing (objective 0) is optimal as written; each unlisted coefficient really is 0: the resource is used by one product only

## 8. `2078392466`: degenerate-text (sureness: low)

**Why I'm not sure:** do-nothing only because 'must be larger than' is modeled as >=; read strictly over integers the optimum is 11 (2 wine, 1 kombucha). Labeled continuous by the rule ('unit of kombucha'); whether 'units of wine' are whole is your call.

> A brewery can ferment their product into either wine or kombucha. Each unit of wine requires 3 units of fruit and 8 units of water. Each unit of kombucha requires 5 units of fruit and 7 units of tea. The company has available 7000 units of water and 9000 units of tea. Wine sells for more, therefore the number of wine must be larger than the number of kombucha. Additionally, at least 20% of their products made must be kombucha. How many of each should the brewery make to minimize the total units of fruit required?

```
min 3*[wine] + 5*[kombucha]
  c0_linear: 8*[wine] <= 7000
  c1_linear: 7*[kombucha] <= 9000
  c2_xy: 1*[wine] - 1*[kombucha] >= 0
  c3_ratio: -0.2*[wine] + 0.8*[kombucha] >= 0
  every variable >= 0
```

**LP:** 0 (wine = 0, kombucha = 0)  
**IP:** 0 (wine = 0, kombucha = 0)

- Integrality label: **continuous** (rule: says 'unit of kombucha')
- Note (unlisted-variable): c0_linear: ['kombucha'] not listed, so coefficient 0 (the official converter: 1)
- Note (unlisted-variable): c1_linear: ['wine'] not listed, so coefficient 0 (the official converter: 1)
- Note (strict-wording): c2_xy: text says 'larger than' (strict); modeled as >=
- **My review (degenerate-text):** nothing has to be made, so making nothing (objective 0) is optimal as written; each unlisted coefficient really is 0: the resource is used by one product only

## 9. `1703643437`: orlm-error (sureness: medium)

**Why I'm not sure:** the ORLM-error verdict is sure (A=10, B=2 is feasible), but the text says 'Formulate a LP' while the label is integer (pills): IP 50, LP 47.78. Which one is the answer is your call.

> Sleep inducing medicine and anti-inflammatory medicine is found in two pills, pill A and pill B. One pill A contains 3 units of sleep inducing medicine and 5 units of anti-inflammatory medicine. One pill B contains 6 units of sleep-inducing medicine and 1 unit of anti-inflammatory medicine. The cost per pill for pill A is $4 and the cost per pill for pill B is $5. A patient must consume these two pills to get at least 40 units of sleep-inducing medicine and 50 units of anti-inflammatory medicine. Formulate a LP to minimize the cost for the patient.

```
min 4*[pill A] + 5*[pill B.]
  c0_linear: 3*[pill A] + 6*[pill B.] >= 40
  c1_linear: 5*[pill A] + 1*[pill B.] >= 50
  every variable >= 0
```

**LP:** 47.7778 (pill A = 9.62963, pill B. = 1.85185)  
**IP:** 50 (pill A = 10, pill B. = 2)

- Integrality label: **integer** (claude)
- **My review (orlm-error):** ORLM found no solution, but A=10, B=2 is feasible (cost 50)

## 10. `-1765797791`: ambiguous-text (sureness: medium)

**Why I'm not sure:** 'must eat three times as many apple as carrot': the annotation reads >= (54); the plain wording may be = (50, ORLM's answer). Ambiguous problems need a scoring rule (docs/PREREGISTRATION.md).

> A parent feeds their baby two flavors of baby food, apple and carrot, in order to meet the babies fat and folate requirements. Each serving of apple flavored baby food contains 2 units of fat and 5 units of folate. Each serving of carrot flavored baby food contains 4 units of fat and 3 units of folate. The baby does not like the carrot flavor, and therefore he must eat three times as many apple flavored baby food as carrot flavored baby food. However, he must eat at least 2 servings of carrot flavored baby food. If the baby can consume at most 100 units of folate, how many servings of each should he eat to maximize his fat intake?

```
max 2*[apple] + 4*[carrot]
  c0_xby: 1*[apple] - 3*[carrot] >= 0
  c1_lowerbound: 1*[carrot] >= 2
  c2_linear: 5*[apple] + 3*[carrot] <= 100
  every variable >= 0
```

**LP:** 55.5556 (apple = 16.6667, carrot = 5.55556)  
**IP:** 54 (apple = 17, carrot = 5)

- Integrality label: **integer** (claude)
- **My review (ambiguous-text):** 'three times as many apple as carrot': >= (annotation, 54) or = (ORLM, 50)

## 11. `-1832353699`: orlm-error (sureness: medium)

**Why I'm not sure:** our answer reads 'at most 33%' literally (0.33); I didn't re-derive ORLM's number in this pass, so 'ORLM reads it as 1/3' is the earlier explanation, not rechecked.

> A zookeeper feeds a gorilla with bananas and mangoes. Each banana contains 80 calories, 20 grams of potassium, and 10 grams of sugar. Each mango contains 100 calories, 15 grams of potassium, and 8 grams of sugar.  The gorilla must consume at least 4000 calories and 150 grams of potassium. Since the gorilla prefers bananas, at most 33% of the fruits he eats can be mangoes. If excess sugar makes the gorilla aggressive, how many of each fruit should he consume to minimize his sugar intake?

```
min 10*[bananas] + 8*[mangoes]
  c0_linear: 80*[bananas] + 100*[mangoes] >= 4000
  c1_linear: 20*[bananas] + 15*[mangoes] >= 150
  c2_ratio: -0.33*[bananas] + 0.67*[mangoes] <= 0
  every variable >= 0
```

**LP:** 431.409 (bananas = 30.9469, mangoes = 15.2425)  
**IP:** 440 (bananas = 32, mangoes = 15)

- Integrality label: **integer** (claude)
- **My review (orlm-error):** ORLM reads 'at most 33%' as 1/3

## 12. `615752596`: orlm-error (sureness: medium)

**Why I'm not sure:** the ORLM-error verdict is sure, but the answer depends on the reading: 80 as annotated, 76 with 'larger than' read strictly. Both are accepted now.

> A university research lab can make two types of diabetes medicine, medicine A and medicine B. Per dose, medicine A takes 30 units of imported material and 50 units of mRNA to make. Per dose, medicine B takes 40 units of imported material and 30 units of mRNA to take. The lab has available at most 300 units of imported material and 400 units of mRNA. The lab can make at most 5 doses of medicine A and the number of doses of medicine B must be larger than the number of dosed of medicine A. If one dose of medicine A can treat 12 people and one dose of medicine B can treat 8 people, how many doses of each should be made to maximize the number of people that can be treated?

```
max 12*[medicine A] + 8*[medicine B.]
  c0_linear: 30*[medicine A] + 40*[medicine B.] <= 300
  c1_linear: 50*[medicine A] + 30*[medicine B.] <= 400
  c2_upperbound: 1*[medicine A] <= 5
  c3_xy: 1*[medicine B.] - 1*[medicine A] >= 0
  every variable >= 0
```

**LP:** 85.7143 (medicine A = 4.28571, medicine B. = 4.28571)  
**IP:** 80 (medicine A = 4, medicine B. = 4)  
**IP, strict reading:** 76 (medicine A = 3, medicine B. = 5) (c3_xy: >= 0 became >= 1)

- Integrality label: **integer** (claude)
- Note (strict-wording): c3_xy: text says 'larger than' (strict); modeled as >=
- **My review (orlm-error):** ORLM found no solution, but A = B = 4 is feasible (80 people); with the strict 'larger than' the integer answer is 76

## 13. `-1715698555`: ambiguous-text (sureness: medium)

**Why I'm not sure:** 'must be three times the number of large bins': >= as annotated (1240) or = (1215 over integers).

> A recycling company collects recycling from neighborhoods using small and large bins. A small bin requires 2 workers while a large bin requires 5 workers. A small bin can hold 25 units of recycling material and a large bin can hold 60 units of recycling material. The company has available 100 workers. Because most people don't recycle, the number of small bins must be three times the number of large bins. In addition, there must be at least 10 small bins and 4 large bins. How many of each bin type should be used to maximize the total amount of recycling material that can be collected?

```
max 25*[small] + 60*[large bins]
  c0_linear: 2*[small] + 5*[large bins] <= 100
  c1_xby: 1*[small] - 3*[large bins] >= 0
  c2_lowerbound: 1*[small] >= 10
  c3_lowerbound: 1*[large bins] >= 4
  every variable >= 0
```

**LP:** 1240 (small = 40, large bins = 4)  
**IP:** 1240 (small = 40, large bins = 4)

- Integrality label: **integer** (rule: counts whole things)
- **My review (ambiguous-text):** 'must be three times the number of large bins': >= (annotation, 1240) or = (1215 as integers); ORLM found no solution

## 14. `-169306566`: ambiguous-text (sureness: medium)

**Why I'm not sure:** '2 times more protein bars than smoothies': >= as annotated (56) or = (32, ORLM's answer). Also noted as strict wording; read strictly the answer stays 56.

> A woman on a diet needs to eat two types of meal preps, a smoothie and a protein bar. Each smoothie contains 2 units of protein and 300 calories. Each protein bar contains 7 units of protein and 250 calories. The woman must eat 2 times more protein bars than smoothies. If the woman can consume at most 2000 calories, how many of each should she eat or drink to maximize her protein intake?

```
max 2*[smoothie] + 7*[protein bar]
  c0_linear: 300*[smoothie] + 250*[protein bar] <= 2000
  c1_xby: 1*[protein bar] - 2*[smoothie] >= 0
  every variable >= 0
```

**LP:** 56 (smoothie = 0, protein bar = 8)  
**IP:** 56 (smoothie = 0, protein bar = 8)  
**IP, strict reading:** 56 (smoothie = 0, protein bar = 8) (c1_xby: >= 0 became >= 1)

- Integrality label: **integer** (rule: counts whole things)
- Note (strict-wording): c1_xby: text says 'more' (strict); modeled as >=
- **My review (ambiguous-text):** '2 times more protein bars than smoothies': >= (annotation, 56) or = (ORLM, 32)

## 15. `-1243268146`: orlm-error (sureness: medium)

**Why I'm not sure:** the ORLM-error verdict is sure, but the answer depends on the reading: 3200 as annotated, 3220 with 'more' read strictly. Both are accepted now.

> A biotechnology company has 35,000 units of antibiotics available which is important to the process of making a first-dose and second-dose of vaccines. The first-dose vaccine requires 30 units of antibiotics and 20 mg of gelatine whereas the second-dose vaccine requires 65 units of antibiotics and 60 mg of gelatine. Since the first-dose vaccine is required before the second-dose vaccine, there must be more first-dose than second-dose vaccines manufactured. However, at least 40 second-dose vaccines must be made. How many of each vaccine should be made to minimize the amount of gelatine used?

```
min 20*[first-dose] + 60*[second-dose]
  c0_linear: 30*[first-dose] + 65*[second-dose] <= 35000
  c1_xy: 1*[first-dose] - 1*[second-dose] >= 0
  c2_lowerbound: 1*[second-dose] >= 40
  every variable >= 0
```

**LP:** 3200 (first-dose = 40, second-dose = 40)  
**IP:** 3200 (first-dose = 40, second-dose = 40)  
**IP, strict reading:** 3220 (first-dose = 41, second-dose = 40) (c1_xy: >= 0 became >= 1)

- Integrality label: **integer** (rule: counts whole things)
- Note (strict-wording): c1_xy: text says 'more' (strict); modeled as >=
- **My review (orlm-error):** ORLM found no solution, but 40 + 40 doses work (3200); with the strict 'more' the integer answer is 3220

## 16. `2005236115`: orlm-error (sureness: high)

> Mr. Roberts want to invest in the telecom and healthcare industries. He has $100000 to invest. He has decided that the amount invested in telecom be at least three times as much as the amount invested in healthcare. But the money invested in telecom must be at most $70000. If investments in telecom earn 3% and investments in healthcare earn 1%, how much should Mr. Roberts invest in each to maximize profit?

```
max 0.03*[telecom] + 0.01*[healthcare]
  c0_sum: 1*[telecom] + 1*[healthcare] <= 100000
  c1_xby: 1*[telecom] - 3*[healthcare] >= 0
  c2_upperbound: 1*[telecom] <= 70000
  every variable >= 0
```

**LP:** 2333.33 (telecom = 70000, healthcare = 23333.3)  
**IP:** 2333.33 (telecom = 70000, healthcare = 23333)

- Integrality label: **continuous** (claude)
- **My review (orlm-error):** ORLM's 2400 breaks telecom >= 3x healthcare

## 17. `-725478241`: text-has-no-optimum (sureness: high)

> A cleaning company located in Edmonton wants to get the best exposure possible for promoting their new dishwashing detergent without exceeding their $250,000 advertising budget. To do so, the company decides to spend their money on two forms of advertising: (1) radio ads and (2) social media ads. Each radio ad costs $5,000; each social media ad costs $9,150. The expected exposure, based on industry ratings, is 60,500 viewers for each radio ad. Additionally, the expected exposure for each social media ad is 50,000 viewers. The company decides that at least 15 but no more than 40 radio ads should be ordered, and that at least 35 social media ads should be contracted. How many ads of each type should be run to obtain maximum exposure while staying within the budget?

```
max 60500*[radio ads] + 50000*[social media ads]
  c0_linear: 5000*[radio ads] + 9150*[social media ads] <= 250000
  c1_lowerbound: 1*[radio ads] >= 15
  c2_upperbound: 1*[radio ads] <= 40
  c3_lowerbound: 1*[social media ads] >= 35
  every variable >= 0
```

**LP:** infeasible  
**IP:** infeasible

- Integrality label: **integer** (rule: counts whole things)
- **My review (text-has-no-optimum):** the minimum ad orders cost $395,250, over the $250,000 budget
- Excluded from scoring anyway: the ads problem: used to design and debug the infeasibility feedback (the conflicting-constraints finder), and in the live self-correction test, during milestone 5.

## 18. `-1036797903`: ok (sureness: high)

> A grocery store wants to liquidate its stock of 10 apples, 20 bananas, and 80 grapes. Given past experience, the store knows that they can propose a banana-haters package with 6 apples and 30 grapes and that this package will bring a profit of six euros. Similarly, they can prepare a combo package with 5 apples, 6 bananas, and 20 grapes, yielding a profit of seven euros. They know they can sell any quantity of these two packages within the availability of its stock. What quantity of each package, banana-haters packages and combo packages, should the store prepare to maximize net profit?

```
max 6*[banana-haters package] + 7*[combo package]
  c0_linear: 6*[banana-haters package] + 5*[combo package] <= 10
  c1_linear: 6*[combo package] <= 20
  c2_linear: 30*[banana-haters package] + 20*[combo package] <= 80
  every variable >= 0
```

**LP:** 14 (banana-haters package = 0, combo package = 2)  
**IP:** 14 (banana-haters package = 0, combo package = 2)

- Integrality label: **integer** (rule: counts whole things)
- Note (unlisted-variable): c1_linear: ['banana-haters package'] not listed, so coefficient 0 (the official converter: 1)
- **My review (ok):** the banana constraint omits the banana-haters package, which really has no bananas (coefficient 0)

## 19. `-451843339`: text-has-no-optimum (sureness: high)

> A nutritionist is making a special vitamin mix using two drinks: A and B. The vitamin mix must contain at least 150 units of Vitamin A, at least 300 units of vitamin D, and at most 400 units of vitamin E. A cup of drink A contains 8 units of Vitamin A, 6 units of Vitamin D, 10 units of Vitamin E, and 4 units of Vitamin K. A cup of drink B contains 15 units of Vitamin A, 2 units of Vitamin D, 20 units of Vitamin E, and 12 units of Vitamin K. How many cups of each drink should be used to make the vitamin mix in order to minimize the amount of Vitamin K?

```
min 12*[B.] + 4*[A]
  c0_linear: 8*[A] + 15*[B.] >= 150
  c1_linear: 6*[A] + 2*[B.] >= 300
  c2_linear: 10*[A] + 20*[B.] <= 400
  every variable >= 0
```

**LP:** infeasible  
**IP:** infeasible

- Integrality label: **integer** (rule: counts whole things)
- **My review (text-has-no-optimum):** the vitamin E cap allows at most 40 cups of A, giving at most 240 units of vitamin D, below the 300 required

## 20. `207812519`: ok (sureness: high)

> A teddy bear company produces three different colored bears: black, white, and brown. These bears are made in two different factories. Running factory 1 for 1 hour costs $300 and produces 5 black teddy bears, 6 white teddy bears, and 3 brown ones. Running factory 2 for 1 hour costs $600 and produces 10 black teddy bears and 10 white teddy bears. (but no brown ones). To meet children's demand, at least 20 black teddy bears, 5 white teddy bears, and 15 brown teddy bears must be made daily. Given this information, develop a linear programming problem assuming the teddy bear company wants to minimize the cost of production.

```
min 300*[factory 1] + 600*[factory 2]
  c0_linear: 5*[factory 1] + 10*[factory 2] >= 20
  c1_linear: 6*[factory 1] + 10*[factory 2] >= 5
  c2_linear: 3*[factory 1] >= 15
  every variable >= 0
```

**LP:** 1500 (factory 1 = 5, factory 2 = 0)  
**IP:** 1500 (factory 1 = 5, factory 2 = 0)

- Integrality label: **integer** (rule: counts whole things)
- Note (unlisted-variable): c2_linear: ['factory 2'] not listed, so coefficient 0 (the official converter: 1)
- **My review (ok):** the brown-bear constraint omits factory 2, which makes 'no brown ones' (coefficient 0)

## 21. `-847055511`: text-has-no-optimum (sureness: high)

> A high rise building is buying two types of furnaces, a new model and an old model. A new model furnace can heat 10 apartments and consumes 200 kWh per day. An old model can heat 15 apartments and consumes 250 kWh per day. Since the old model is harder to find, at most 35% of the furnaces can be the old model and at least 5 new model furnaces should be used. If the high rise needs to heat at least 200 apartments and has 3500 kWh of electricity available, how many of each furnace should be purchase to minimize the total number of furnaces?

```
min 1*[new model] + 1*[old model]
  c0_ratio: -0.35*[new model] + 0.65*[old model] <= 0
  c1_lowerbound: 1*[new model] >= 5
  c2_linear: 10*[new model] + 15*[old model] >= 200
  c3_linear: 200*[new model] + 250*[old model] <= 3500
  every variable >= 0
```

**LP:** infeasible  
**IP:** infeasible

- Integrality label: **integer** (rule: counts whole things)
- **My review (text-has-no-optimum):** with old models capped at 35%, 3500 kWh heats at most ~189 apartments, below the 200 needed

## 22. `-1979635456`: degenerate-text (sureness: high)

> A bakery makes almond and pistachio croissants. An almond croissant requires 5 units of butter and 8 units of flour. A pistachio croissant requires 3 units of butter and 6 units of flour. The bakery has available 600 units of butter and 800 units of flour. Since the almond croissant is more popular, at least 3 times as many almond croissants should be made as pistachio croissants. If making an almond croissant takes 12 minutes and making a pistachio croissant takes 10 minutes, how many of each should be made to minimize the total production time?

```
min 12*[almond] + 10*[pistachio]
  c0_linear: 5*[almond] + 3*[pistachio] <= 600
  c1_linear: 8*[almond] + 6*[pistachio] <= 800
  c2_xby: 1*[almond] - 3*[pistachio] >= 0
  every variable >= 0
```

**LP:** 0 (almond = 0, pistachio = 0)  
**IP:** 0 (almond = 0, pistachio = 0)

- Integrality label: **integer** (rule: counts whole things)
- **My review (degenerate-text):** nothing has to be made, so making nothing (objective 0) is optimal as written

## 23. `-1766223663`: text-has-no-optimum (sureness: high)

> A cough syrup company sells cough syrup in kids and adult size bottles. A kids size bottle can hold 100 ml of cough syrup while an adult size bottle can hold 300 ml of cough syrup. Since there is no difference in concentration of medical ingredients between the two bottles, at least 3 times as many adult size bottle must be made as kids size bottles. However, at least 50 kids size bottles must be made. If the company has 25000 ml of cough syrup available, how many bottles of each should be made to maximize the total number of bottles?

```
max 1*[kids] + 1*[adult size]
  c0_xby: 1*[adult size] - 3*[kids] >= 0
  c1_lowerbound: 1*[kids] >= 50
  c2_linear: 100*[kids] + 300*[adult size] <= 25000
  every variable >= 0
```

**LP:** infeasible  
**IP:** infeasible

- Integrality label: **integer** (rule: counts whole things)
- **My review (text-has-no-optimum):** the minimums need 50,000 ml of syrup; only 25,000 ml is available

## 24. `-1584110645`: degenerate-text (sureness: high)

> A grilled cheese shop sells a light and heavy grilled cheese sandwich. A light grilled cheese sandwich requires 2 slices of bread and 3 slices of cheese. A heavy grilled cheese sandwich requires 3 slices of bread and 5 slices of cheese. Since most people who come to the store love grilled cheese, the store must make at least 3 times as many heavy grilled cheese sandwiches as light grilled cheese sandwiches. The store has available 300 slices of bread and 500 slices of cheese. If a light grilled cheese sandwich takes 10 minutes to make and a heavy grilled cheese sandwich takes 15 minutes to make, how many of each should they make to minimize the total production time?

```
min 10*[light] + 15*[heavy]
  c0_xby: 1*[heavy] - 3*[light] >= 0
  c1_linear: 2*[light] + 3*[heavy] <= 300
  c2_linear: 3*[light] + 5*[heavy] <= 500
  every variable >= 0
```

**LP:** 0 (light = 0, heavy = 0)  
**IP:** 0 (light = 0, heavy = 0)

- Integrality label: **integer** (rule: counts whole things)
- **My review (degenerate-text):** nothing has to be made, so making nothing (objective 0) is optimal as written

## 25. `-468779640`: text-has-no-optimum (sureness: high)

> A banana company sells their bananas in small and large crates. A small crate can hold 20 bananas while a large crate can hole 50 bananas. Since large crates are more manageable, the number of large crates must be at least twice the number of small crates. However, at least 5 small crates should be used. If the company has available 500 bananas, how many of each crate should the company use to maximize the total number of crates produced?

```
max 1*[small] + 1*[large]
  c0_xby: 1*[large] - 2*[small] >= 0
  c1_lowerbound: 1*[small] >= 5
  c2_linear: 20*[small] + 50*[large] <= 500
  every variable >= 0
```

**LP:** infeasible  
**IP:** infeasible

- Integrality label: **integer** (rule: counts whole things)
- **My review (text-has-no-optimum):** the minimums need 600 bananas; only 500 are available

## 26. `-2027758451`: orlm-error (sureness: high)

> A mall buys two types of hand sanitizer machines, a motion activated one and a manual one. The motion activated one can deliver 50 drops per minute and consumes 30 kWh. The manual one can deliver 75 drops per minute and consumes 20 kWh. Since the motion activated one is more hygienic, at most 40% of the machines can be manual. In addition, at least 3 should be motion activated. If the mall must be able to deliver at least 1000 drops per minute and can use at most 500 kWh per minute, how many of each machine should they buy to minimize the total number of machines?

```
min 1*[motion activated] + 1*[manual]
  c0_ratio: -0.4*[motion activated] + 0.6*[manual] <= 0
  c1_lowerbound: 1*[motion activated] >= 3
  c2_linear: 50*[motion activated] + 75*[manual] >= 1000
  c3_linear: 30*[motion activated] + 20*[manual] <= 500
  every variable >= 0
```

**LP:** 16.6667 (motion activated = 10, manual = 6.66667)  
**IP:** 17 (motion activated = 11, manual = 6)

- Integrality label: **integer** (claude)
- **My review (orlm-error):** 11 motion + 6 manual = 17 machines is feasible; ORLM says 18

## 27. `498603121`: degenerate-text (sureness: high)

> A coffee shop sells mochas and regular coffees. Each mocha requires 3 units of coffee powder and 6 units of milk. Each regular coffee requires 6 units of coffee powder and 2 units of milk. The shop has available 400 units of coffee powder and 500 units of milk. Making a mocha takes 5 minutes and making a regular coffee takes 3 minutes. Since mochas are more popular among people, the shop must make at least 3 times as many mochas as regular coffees. How many of each should they make to minimize the total production time?

```
min 5*[mochas] + 3*[regular coffees]
  c0_linear: 3*[mochas] + 6*[regular coffees] <= 400
  c1_linear: 6*[mochas] + 2*[regular coffees] <= 500
  c2_xby: 1*[mochas] - 3*[regular coffees] >= 0
  every variable >= 0
```

**LP:** 0 (mochas = 0, regular coffees = 0)  
**IP:** 0 (mochas = 0, regular coffees = 0)

- Integrality label: **integer** (rule: counts whole things)
- **My review (degenerate-text):** nothing has to be made, so making nothing (objective 0) is optimal as written

## 28. `1165597365`: text-has-no-optimum (sureness: high)

> A butcher shop is buying meat slicers for their shop, a manual and automatic slicer. The manual slicer can cut 5 slices per minute while the automatic slicer can cut 8 slices per minute. In addition, to make sure all the parts operate smoothly, the manual slicer requires 3 units of grease per minute while the automatic slicer requires 6 units of grease per minute. Since the automatic slicer does not need someone to operate it, the number of manual slicers must be less than the number of automatic slicers. In addition, the butcher shop needs to be able to cut at least 50 slices per minute but can use at most 35 units of grease per minute. How many of each slicer should the butcher shop buy to minimize the total number of slicers in the shop?

```
min 1*[manual] + 1*[automatic]
  c0_xy: 1*[manual] - 1*[automatic] <= 0
  c1_linear: 5*[manual] + 8*[automatic] >= 50
  c2_linear: 3*[manual] + 6*[automatic] <= 35
  every variable >= 0
```

**LP:** 7.5 (manual = 3.33333, automatic = 4.16667)  
**IP:** infeasible  
**IP, strict reading:** infeasible (c0_xy: <= 0 became <= -1)

- Integrality label: **integer** (claude)
- Note (strict-wording): c0_xy: text says 'less than' (strict); modeled as <=
- **My review (text-has-no-optimum):** no whole number of slicers satisfies the grease limit (checked every case); the LP relaxation's optimum is 7.5

## 29. `-1603650758`: text-has-no-optimum (sureness: high)

> A chemical plant can buy two types of generators, generator A and generator B, which use two different processes to generate hydrogen. Generator A uses an electrolysis process and produces 40 cubic meters of hydrogen as well as 300 units of pollutants every day. Generator B uses a fermentation process to produce 30 cubic meters of hydrogen per day while outputting 200 units of pollutants. The chemical plant must make a minimum of 1000 cubic meters of hydrogen per day but due to environmental restrictions they can produce at most 3000 units of pollutant. How many of each type of generator should they buy to minimize the number of generators needed?

```
min 1*[generator A] + 1*[generator B]
  c0_linear: 40*[generator A] + 30*[generator B] >= 1000
  c1_linear: 300*[generator A] + 200*[generator B] <= 3000
  every variable >= 0
```

**LP:** infeasible  
**IP:** infeasible

- Integrality label: **integer** (rule: counts whole things)
- **My review (text-has-no-optimum):** the pollution cap limits hydrogen to 450 m3/day, below the 1000 required

## 30. `492091808`: degenerate-text (sureness: high)

> A small chocolate shop makes milk chocolate and dark chocolate bars. Milk chocolate bars require 4 units of cocoa and 7 units of milk. Dark chocolate bars require 6 units of cocoa and 3 units of milk. The shop has 2000 units of cocoa and 1750 units of milk available. In addition since milk chocolate sells better, at least 2 times as many milk chocolate bars need to be made as dark chocolate bars.  If making a milk chocolate bar takes 15 minutes and making a dark chocolate bar takes 12 mins, how many of each should the make to minimize total production time?

```
min 15*[milk chocolate] + 12*[dark chocolate bars]
  c0_linear: 4*[milk chocolate] + 6*[dark chocolate bars] <= 2000
  c1_linear: 7*[milk chocolate] + 3*[dark chocolate bars] <= 1750
  c2_xby: 1*[milk chocolate] - 2*[dark chocolate bars] >= 0
  every variable >= 0
```

**LP:** 0 (milk chocolate = 0, dark chocolate bars = 0)  
**IP:** 0 (milk chocolate = 0, dark chocolate bars = 0)

- Integrality label: **integer** (rule: counts whole things)
- **My review (degenerate-text):** nothing has to be made, so making nothing (objective 0) is optimal as written

## 31. `-272035411`: annotation-error (sureness: high)

> A patient in the hospital can take two pills, Pill 1 and Pill 2. Per pill, pill 1 provides 0.2 units of pain medication and 0.3 units of anxiety medication. Per pill, pill 2 provides 0.6 units of pain medication and 0.2 units of anxiety medication. In addition, pill 1 causes 0.3 units of discharge while pill 2 causes 0.1 units of discharge. At most 6 units of pain medication can be provided and at least 3 units of anxiety medication must be provided. How many pills of each should the patient be given to minimize the total amount of discharge?

```
min 0.3*[Pill 1] + 0.1*[Pill 2]
  c0_linear: 0.2*[Pill 1] + 0.6*[Pill 2] <= 6
  c1_linear: 0.3*[Pill 1] >= 3
  every variable >= 0
```

**LP:** 3 (Pill 1 = 10, Pill 2 = 0)  
**IP:** 3 (Pill 1 = 10, Pill 2 = 0)

- Integrality label: **integer** (rule: counts whole things)
- Note (unlisted-variable): c1_linear: ['Pill 2'] not listed, so coefficient 0 (the official converter: 1)
- **My review (annotation-error):** the anxiety constraint omits pill 2's 0.2 units; the text's integer answer is 2.3, matching ORLM
- The error changes the answer.

## 32. `1637604355`: orlm-error (sureness: high)

> A patient with a sore throat can drink two syrups, syrup 1 and syrup 2 for treatment. Per serving, syrup 1 delivers 0.5 units of medicine to the throat and 0.4 units of medicine to the lungs. Per serving, syrup 2 delivers 0.2 units of medicine to the throat and 0.5 units of medicine to the lungs. Furthermore, syrup 1 contains 0.5 units of sugar while syrup 2 contains 0.3 units of sugar per serving. The patient can get at most 5 units of medicine for the throat and at least 4 units of medicine to the lungs. How many servings of each should the patient take to minimize his sugar intake?

```
min 0.5*[syrup 1] + 0.3*[syrup 2]
  c0_linear: 0.5*[syrup 1] + 0.2*[syrup 2] <= 5
  c1_linear: 0.4*[syrup 1] + 0.5*[syrup 2] >= 4
  every variable >= 0
```

**LP:** 2.4 (syrup 1 = 0, syrup 2 = 8)  
**IP:** 2.4 (syrup 1 = 0, syrup 2 = 8)

- Integrality label: **integer** (rule: counts whole things)
- **My review (orlm-error):** 8 servings of syrup 2 give 2.4 units of sugar; ORLM says 4

## 33. `1402521519`: orlm-error (sureness: high)

> A lab has 20000 mg of mRNA anti-viral available to make children's and adult vaccines. Each children's vaccine contains 50 mg of mRNA and 50 mg of fever suppressant. Each adult vaccine contains 75 mg of mRNA and 75 mg of fever suppressant. Since adult vaccines are more essential, at least 70% of vaccines should be adult vaccines. However, at least 50 children's vaccines should be made. How many of each vaccine should be made to minimize the amount of fever suppressant used?

```
min 50*[children's] + 75*[adult vaccines]
  c0_linear: 50*[children's] + 75*[adult vaccines] <= 20000
  c1_ratio: -0.7*[children's] + 0.3*[adult vaccines] >= 0
  c2_lowerbound: 1*[children's] >= 50
  every variable >= 0
```

**LP:** 11250 (children's = 50, adult vaccines = 116.667)  
**IP:** 11275 (children's = 50, adult vaccines = 117)

- Integrality label: **integer** (claude)
- **My review (orlm-error):** ORLM's 2500 breaks the 70%-adult constraint

## 34. `2041857060`: orlm-error (sureness: high)

> A doctor's office takes the  temperature of patients one by one either by using an electronic or regular thermometer. The electronic thermometer takes 3 minutes to make a reading while the regular thermometer takes 2 minutes to make a reading. Since the electronic thermometer is more accurate, at least twice as many patients should have their temperature checked by the electronic thermometer than the regular thermometer. Since the electronic thermometer has a cooldown time, at least 50 patients should have their temperature checked by a regular thermometer. If the office is open for 15000 minutes, maximize the number of patients whose temperature can be taken?

```
max 1*[electronic] + 1*[regular thermometer]
  c0_xby: 1*[electronic] - 2*[regular thermometer] >= 0
  c1_lowerbound: 1*[regular thermometer] >= 50
  c2_linear: 3*[electronic] + 2*[regular thermometer] <= 15000
  every variable >= 0
```

**LP:** 5625 (electronic = 3750, regular thermometer = 1875)  
**IP:** 5625 (electronic = 3750, regular thermometer = 1875)

- Integrality label: **integer** (rule: counts whole things)
- **My review (orlm-error):** ORLM's 7500 breaks electronic >= 2x regular

## 35. `-1819716628`: orlm-error (sureness: high)

> A patient in the hospital can take two different pain killers, pain killer 1 and pain killer 2. Per dose, pain killer 1 delivers 0.5 units of medicine to the legs and 0.8 units of medicine to the back. Per dose, pain killer 2 delivers 0.7 units of medicine to the legs and 0.4 units of medicine to the back. In, addition pain killer 1 deliver 0.3 units of sleeping medicine and pain killer 2 delivers 0.6 units of sleeping medicine. At most 8 units of sleep medicine should be delivered and at least 4 units of medicine should be delivered to the legs. How many doses of each should be taken to maximize the amount of medicine delivered to the back?

```
max 0.8*[pain killer 1] + 0.4*[pain killer 2]
  c0_linear: 0.3*[pain killer 1] + 0.6*[pain killer 2] <= 8
  c1_linear: 0.5*[pain killer 1] + 0.7*[pain killer 2] >= 4
  every variable >= 0
```

**LP:** 21.3333 (pain killer 1 = 26.6667, pain killer 2 = 0)  
**IP:** 20.8 (pain killer 1 = 26, pain killer 2 = 0)

- Integrality label: **integer** (claude)
- **My review (orlm-error):** ORLM's 6.4 isn't the maximum: 26 doses of pain killer 1 give 20.8

## 36. `-2028768463`: text-has-no-optimum (sureness: high)

> A pharmaceutical company has 800 units of painkiller medicine and makes daytime and nighttime painkiller. A daytime pill has 6 units of painkiller medicine and 2 units of sleep medicine. A nighttime pill has 5 units of painkiller medicine and 5 units of sleep medicine. Since some people don’t want the sleeping effect, at least 40% of the pills must be daytime pills. However at least 200 nighttime pills must be made. How many of each pill should be made to minimize the total amount of sleep medicine required?

```
min 2*[daytime] + 5*[nighttime painkiller]
  c0_linear: 6*[daytime] + 5*[nighttime painkiller] <= 800
  c1_ratio: 0.6*[daytime] - 0.4*[nighttime painkiller] >= 0
  c2_lowerbound: 1*[nighttime painkiller] >= 200
  every variable >= 0
```

**LP:** infeasible  
**IP:** infeasible

- Integrality label: **integer** (rule: counts whole things)
- **My review (text-has-no-optimum):** the minimums need 1800 units of painkiller; only 800 are available

## 37. `1694815390`: annotation-error (sureness: high)

> Both sulfate and ginger need to be added to a shampoo. One unit of sulfate takes 0.5 minutes to be effective while one unit of ginger takes 0.75 minutes to be effective. The shampoo must contain at least 100 units of sulfates and a total of 400 units of both ingredient. Since too much sulfate can damage the hair, there can be at most twice the amount of sulfate as ginger in the shampoo. How many units of each should be added to the shampoo to minimize the total amount of time it takes for the mixture to be effective? (Note: one must be added before the other)

```
min 0.5*[sulfate] + 0.75*[ginger]
  c0_lowerbound: 1*[sulfate] >= 100
  c1_sum: 1*[sulfate] + 1*[ginger] <= 400
  c2_xby: 1*[sulfate] - 2*[ginger] <= 0
  every variable >= 0
```

**LP:** 87.5 (sulfate = 100, ginger = 50)  
**IP:** 87.5 (sulfate = 100, ginger = 50)

- Integrality label: **continuous** (rule: asks how many units)
- **My review (annotation-error):** 'a total of 400 units' is annotated as <= 400 (the scheme has no equality); with = 400 the answer is 233.3
- The error changes the answer.

## 38. `-945818446`: text-has-no-optimum (sureness: high)

> A pharmaceutical company has two labs, lab 1 and lab 2, where they make heart and lung medication in pill form. At lab 1, they can produce 20 heart medication pills and 30 lung medication pills per hour. At lab 2, they can produce 30 heart medication pills and 40 lung medication pills per hour. Each session at lab 1 requires 3 hours of worker labor while each session at lab 2 requires 5 hours of worker labor. The company has 1500 worker hours available and must make at least 20000 heart medication pills and at least 30000 lung medication pills. How many hours at each lab should be run to minimize the total time needed?

```
min 1*[lab 1] + 1*[lab 2]
  c0_linear: 3*[lab 1] + 5*[lab 2] <= 1500
  c1_linear: 20*[lab 1] + 30*[lab 2] >= 20000
  c2_linear: 30*[lab 1] + 40*[lab 2] >= 30000
  every variable >= 0
```

**LP:** infeasible  
**IP:** infeasible

- Integrality label: **continuous** (rule: asks how many hours)
- **My review (text-has-no-optimum):** 1500 worker-hours give at most 10,000 heart pills, below the 20,000 required

## 39. `-1921036549`: annotation-error (sureness: high)

> Both chorine and water softener need to be added to a pool. One unit of chlorine takes 1 minute to be effective while one unit of water softener takes 2 minutes to be effective. Because too much chlorine can burn your eyes, there has to at most half as much chlorine as water softener in the pool. If there has to be at least 200 units of chlorine in the water and a total of 500 units of chemicals in the water, how many units of each should be added to minimize the total time it takes for the pool to be ready? (Note: chlorine must be added before water softener or vice versa).

```
min 1*[chorine] + 2*[water softener]
  c0_xby: 1*[chorine] - 0.5*[water softener] <= 0
  c1_lowerbound: 1*[chorine] >= 200
  every variable >= 0
```

**LP:** 1000 (chorine = 200, water softener = 400)  
**IP:** 1000 (chorine = 200, water softener = 400)

- Integrality label: **continuous** (rule: asks how many units)
- **My review (annotation-error):** 'a total of 500 units of chemicals' is missing; with it the text is infeasible (chlorine <= 166.7 but >= 200)
- The error changes the answer.

## 40. `1238353423`: text-has-no-optimum (sureness: high)

> A drug company is making pain killers and sleeping pills using two processes, process 1 and process 2. Process 1 produces 35 units of pain killers and 12 units of sleeping pills per hour. Process 2 produces 50 units of pain killers and 30 units of sleeping pills per hour. Process 1 requires 50 units of preliminary material while process 2 requires 60 units of preliminary material. The drug company has available 2000 units of preliminary material and must make at least 1200 units of pain killers and 1200 units of sleeping pills. How many of each process should be run to minimize the total time needed?

```
min 1*[process 1] + 1*[process 2]
  c0_linear: 50*[process 1] + 60*[process 2] <= 2000
  c1_linear: 35*[process 1] + 50*[process 2] >= 1200
  c2_linear: 12*[process 1] + 30*[process 2] >= 1200
  every variable >= 0
```

**LP:** infeasible  
**IP:** infeasible

- Integrality label: **integer** (rule: counts whole things)
- **My review (text-has-no-optimum):** 2000 units of material give at most 1000 sleeping pills, below the 1200 required

## 41. `-1598952138`: orlm-error (sureness: high)

> A car manufacturer ships their cars on large and small planes. A large plane can carry 30 cars while a small plane can carry 10 cars. Since large planes cause more pollution, the number of large planes must be less than the number of small planes. If the manufacturer wants to deliver at least 300 cars, find the minimum number of planes that can be used.

```
min 1*[large] + 1*[small]
  c0_xy: 1*[large] - 1*[small] <= 0
  c1_linear: 30*[large] + 10*[small] >= 300
  every variable >= 0
```

**LP:** 15 (large = 7.5, small = 7.5)  
**IP:** 16 (large = 8, small = 8)  
**IP, strict reading:** 16 (large = 7, small = 9) (c0_xy: <= 0 became <= -1)

- Integrality label: **integer** (claude)
- Note (strict-wording): c0_xy: text says 'less than' (strict); modeled as <=
- **My review (orlm-error):** ORLM found no solution, but 7 large + 9 small planes work (16)

## 42. `-634192638`: text-has-no-optimum (sureness: high)

> A chemical company is transporting their hydrogen using two different methods, high pressure tube trailers and liquefied hydrogen tankers. The first method is a high-pressure tube trailer which can transport 50 cubic meters each per trip at a cost of $500. The second method is using liquefied hydrogen tankers which can transport 30 cubic meters each per trip at a cost of $200. The company needs to transport at least 1000 cubic meters of hydrogen and they have budget of $3750 available. In addition, the number of transports done by the high pressure tube trailer method has to be less than the number of transports done by the liquefied hydrogen tanker method. How many of each transportation method should they use to minimize the total number of trips?

```
min 1*[high pressure tube] + 1*[liquefied hydrogen tankers]
  c0_linear: 50*[high pressure tube] + 30*[liquefied hydrogen tankers] >= 1000
  c1_linear: 500*[high pressure tube] + 200*[liquefied hydrogen tankers] <= 3750
  c2_xy: 1*[high pressure tube] - 1*[liquefied hydrogen tankers] <= 0
  every variable >= 0
```

**LP:** infeasible  
**IP:** infeasible  
**IP, strict reading:** infeasible (c2_xy: <= 0 became <= -1)

- Integrality label: **integer** (rule: counts whole things)
- Note (strict-wording): c2_xy: text says 'less than' (strict); modeled as <=
- **My review (text-has-no-optimum):** the budget limits volume to 562.5 m3, below the 1000 required

## 43. `941255519`: text-has-no-optimum (sureness: high)

> A snow removal company removes snow from neighborhoods using small trucks and large trucks. A small truck requires 2 people to shovel the snow and can carry 30 units of snow. A large truck require 4 people to shovel the snow and car carry 50 units of snow. The company has available 30 people. In addition, because some neighbourhood don’t allow big trucks, at least 10 trucks must be small. There must be at least 3 large trucks as well and the number of small trucks must be twice as much as the number of large trucks. How many of each truck should be used to maximize the total amount of snow that can be transported?

```
max 30*[small trucks] + 50*[large trucks]
  c0_linear: 2*[small trucks] + 4*[large trucks] <= 30
  c1_lowerbound: 1*[small trucks] >= 10
  c2_lowerbound: 1*[large trucks] >= 3
  c3_xby: 1*[small trucks] - 2*[large trucks] >= 0
  every variable >= 0
```

**LP:** infeasible  
**IP:** infeasible

- Integrality label: **integer** (rule: counts whole things)
- **My review (text-has-no-optimum):** the minimum trucks need 32 people; only 30 are available

## 44. `-1062928915`: annotation-error (sureness: high)

> A woman has $100000 to gamble on two sports bets: a basketball tournament, a horse race, and a soccer game. Based on simple analysis, the woman determines her chance of losing her money would be 50% for basketball tournament, 25% for horse race, and 10% for the soccer game. The payout for each dollar put on each bet will be $1.2 for basketball tournament, $0.5 for horse race, and $0.1 for the soccer game. Knowing herself, she limits her average chance of losing her money should be at most 30%. Could you help her determine how much to money to put on each sport bet to maximize her average payout?

```
max 1.2*[basketball tournament] + 0.5*[horse race] + 0.1*[soccer game]
  c0_sum: 1*[basketball tournament] + 1*[horse race] + 1*[soccer game] <= 100000
  c1_linear: 0.5*[basketball tournament] + 0.25*[horse race] + 0.1*[soccer game] <= 0.3
  every variable >= 0
```

**LP:** 0.72 (basketball tournament = 0.6, horse race = 0, soccer game = 0)  
**IP:** 0.5 (basketball tournament = 0, horse race = 1, soccer game = 0)

- Integrality label: **continuous** (claude)
- **My review (annotation-error):** 'average chance of losing at most 30%' is annotated as an absolute limit of 0.3; the text's answer is 65,000, matching ORLM
- The error changes the answer.

## 45. `-114149479`: annotation-error (sureness: high)

> A small bakery has 20000 grams of batter and 14000 grams of milk to make their crepe cakes, sponge cakes, and birthday cakes. A crepe cake needs 400 grams of batter and 200 grams of milk. A sponge cake requires 500 grams of batter and 300 grams of milk. A birthday cake requires 450 grams of batter and 350 grams of milk. If the profit per crepe cake is $12, the profit per sponge cake is $10, and the profit per birthday cake is $15, how many of each should the bakery make to maximize their profit?

```
max 12*[crepe cakes] + 10*[sponge cakes] + 15*[birthday cakes]
  c0_linear: 200*[crepe cakes] + 300*[sponge cakes] + 350*[birthday cakes] <= 20000
  every variable >= 0
```

**LP:** 1200 (crepe cakes = 100, sponge cakes = 0, birthday cakes = 0)  
**IP:** 1200 (crepe cakes = 100, sponge cakes = 0, birthday cakes = 0)

- Integrality label: **integer** (rule: counts whole things)
- **My review (annotation-error):** batter and milk are merged into one constraint (milk coefficients with batter's limit); the text's answer is 648, matching ORLM
- The error changes the answer.

## 46. `-1448607152`: text-has-no-optimum (sureness: high)

> A strata-management company is looking into purchasing two types of air conditioners, a low-power and a high-power model. A low-powered air conditioner can cool down 12 housing units and uses 150 units of electricity every day. A high-power model can cool down 17 housing units and uses 250 units of electricity every day. Since the low-powered model is not good for the aesthetics, the strata decided to limit the number of low-powered models to only 30% and at least 7 high-powered models must be used. If the apartment needs to condition at least 250 housing units and has 3400 units of electricity available, how many of each air conditioner should the strata company buy to minimize the total number of air conditioners?

```
min 1*[low-power] + 1*[high-power model]
  c0_lowerbound: 1*[high-power model] >= 7
  c1_linear: 12*[low-power] + 17*[high-power model] >= 250
  c2_linear: 250*[high-power model] + 150*[low-power] <= 3400
  c3_ratio: 0.7*[low-power] - 0.3*[high-power model] <= 0
  every variable >= 0
```

**LP:** infeasible  
**IP:** infeasible

- Integrality label: **integer** (rule: counts whole things)
- **My review (text-has-no-optimum):** with low-power units capped at 30%, electricity limits cooling to ~240 units, below the 250 required

## 47. `-1770860412`: text-has-no-optimum (sureness: high)

> A hospital hires ultrasound technicians and graduate researchers to image patients. An ultrasound technician works 8 hours per shift while a graduate researcher works 5 hours per shift. Ultrasound technicians are paid $300 per shift while graduate researchers are paid $100 per shift. However, due to regulations, there must be twice as many ultrasound technician shifts than graduate researcher shifts. Currently, the hospital needs 500 hours of ultrasound services to meet needs. If the hospital has a budget of $14000, how many of each worker certified to use the ultrasound should be scheduled to reduce the total number of workers?

```
min 1*[ultrasound technicians] + 1*[graduate researchers]
  c0_xby: 1*[ultrasound technicians] - 2*[graduate researchers] >= 0
  c1_linear: 300*[ultrasound technicians] + 100*[graduate researchers] <= 14000
  c2_linear: 8*[ultrasound technicians] + 5*[graduate researchers] >= 500
  every variable >= 0
```

**LP:** infeasible  
**IP:** infeasible

- Integrality label: **integer** (rule: counts whole things)
- Note (order-mapping-overridden): order_mapping maps 'graduate researcher' to 'ultrasound technicians', but it names 'graduate researchers'
- **My review (text-has-no-optimum):** order_mapping sends 'graduate researcher' to the technicians; resolved by name. With technician shifts >= 2x researcher shifts, the $14,000 budget covers at most 420 hours, below the 500 needed

## 48. `905906224`: degenerate-text (sureness: high)

> A restaurant has two combos available to their customers, an original and an experimental meal. The original meal typically generates 20 units of food waste and 45 units of wrapping waste and takes 10 minutes to cook. In comparison, the experimental meal generates 25 units of food waste and 35 units of wrapping waste and takes 15 minutes to cook. The restaurant can have at most 900 units of wrapping waste and can have at most 800 units of food waste as regulated by the government. How many of each combo should be pushed for by the waiting staff to minimize the cooking time?

```
min 15*[experimental meal] + 10*[original]
  c0_linear: 35*[experimental meal] + 45*[original] <= 900
  c1_linear: 20*[original] + 25*[experimental meal] <= 800
  every variable >= 0
```

**LP:** 0 (original = 0, experimental meal = 0)  
**IP:** 0 (original = 0, experimental meal = 0)

- Integrality label: **integer** (rule: counts whole things)
- **My review (degenerate-text):** nothing has to be made, so making nothing (objective 0) is optimal as written

## 49. `-1704758994`: text-has-no-optimum (sureness: high)

> A market owner wants to start a jam business. He can either sell one unit of jam to customers in a set of small packets or jugs. A set of small packets can hold 1000 ml of jam while a jug can hold 1250 ml of jam. Since a set of small packets are more expensive to make, at least three times as many jugs must be used than sets of small packets. On the other hand, at least 35 sets of small packets should be filled. If the market owner has 65000 ml of jam, how many sets of small packets or jugs should be selected to maximize the total number of units that he can sell to his customers?

```
max 1*[small packets] + 1*[jugs]
  c0_xby: 1*[jugs] - 3*[small packets] >= 0
  c1_lowerbound: 1*[small packets] >= 35
  c2_linear: 1000*[small packets] + 1250*[jugs] <= 65000
  every variable >= 0
```

**LP:** infeasible  
**IP:** infeasible

- Integrality label: **integer** (rule: counts whole things)
- Note (empty-objvar): objective 'total number of units' lists no variables; used their sum
- **My review (text-has-no-optimum):** the minimums need 166,250 ml of jam; only 65,000 ml is available

## 50. `1278831553`: text-has-no-optimum (sureness: high)

> A navy ship is stocking food onto their submarine and their staff can eat either a salad or fruit bowl for their fibre and vitamin intake. The nutritionist in charge of this voyage needs to ensure that their staff gets at least 90 units of vitamin and 110 units of fibre each. Each salad contains 7 units of vitamins and 12 units of fibre. Each fruit bowl contains 15 units of vitamin and 3 units of fibre. In addition, since fruit bowls take longer to prepare, at most 30% of their meals should be fruit bowls. If each salad contains 2 units of potassium and each fruit bowl contains 8 units of potassium, how many of each should they prepare for each staff to maximize their potassium intake?

```
max 2*[salad] + 8*[fruit bowl]
  c0_linear: 15*[fruit bowl] + 7*[salad] >= 90
  c1_linear: 12*[salad] + 3*[fruit bowl] >= 110
  c2_ratio: -0.3*[salad] + 0.7*[fruit bowl] <= 0
  every variable >= 0
```

**LP:** unbounded  
**IP:** unbounded

- Integrality label: **integer** (rule: counts whole things)
- **My review (text-has-no-optimum):** maximizes potassium subject only to minimum requirements, so it's unbounded

## 51. `1677678357`: text-has-no-optimum (sureness: high)

> A soda company sells soda in two types of containers: cans and glass bottles. A can holds 250 ml of soda whereas a bottle holds 1000 ml of soda. The soda company needs to bottle at least 1000000 ml of soda every day and due to the ability to sell soda cans as packs, there must be at least three times more cans than glass bottles. However, because of previous contracts with gas stations, there must be at least 100 glass bottles made. How many of each should be made to maximize the total number of units produced?

```
max 1*[cans] + 1*[glass bottles]
  c0_linear: 250*[cans] + 1000*[glass bottles] >= 1e+06
  c1_xby: 1*[cans] - 3*[glass bottles] >= 0
  c2_lowerbound: 1*[glass bottles] >= 100
  every variable >= 0
```

**LP:** unbounded  
**IP:** unbounded

- Integrality label: **integer** (rule: counts whole things)
- **My review (text-has-no-optimum):** maximizes units subject only to minimum requirements, so it's unbounded

## 52. `358766780`: annotation-error (sureness: high)

> A candle-making company can move their inventory of candles using freight and air. Freight can transport 5 tons per trip while using air can transport 3 tons per trip. Since freight take longer, the cost for each freight trip is $300 while the cost over air for each trip is $550. The company needs to transport at least 200 tons of candles and they have a budget of $20000. Additionally, due to some urgent orders, at least 30% of tons of candles must be transported through air. There must also be at least 5 trips through freight. How many of trip by each should be scheduled to minimize the total number of trips?

```
min 1*[freight] + 1*[air]
  c0_linear: 5*[freight] + 3*[air] >= 200
  c1_linear: 300*[freight] + 550*[air] <= 20000
  c2_ratio: -0.3*[freight] + 0.7*[air] >= 0
  c3_lowerbound: 1*[freight] >= 5
  every variable >= 0
```

**LP:** 45.4545 (freight = 31.8182, air = 13.6364)  
**IP:** 46 (freight = 32, air = 14)

- Integrality label: **integer** (claude)
- Note (duplicate-var): `vars` lists a variable twice (['freight', 'air', 'air']); kept one copy
- **My review (annotation-error):** 'at least 30% of tons by air' is annotated as 30% of trips; in tons the answer is 48, matching ORLM
- The error changes the answer.

## 53. `912269019`: text-has-no-optimum (sureness: high)

> Grain is transported from a farm to local grocery stores in either large bags or tiny bags. Large bags can hold 25 kg of grain and requires 4 units of energy to transport. Tiny bags can hold 6 kg of grain and requires 1.5 units of energy to transport. The distribution process has access to 110 units of energy. Because of popularity of buying in bulk, there must be twice as many large bags as tiny bags of rice. Additionally, there must be at least 20 tiny bags of rice. How many of each size of rice bags should be used to maximize the total amount of grain in weight?

```
max 25*[large bags] + 6*[tiny bags]
  c0_linear: 4*[large bags] + 1.5*[tiny bags] <= 110
  c1_xby: 1*[large bags] - 2*[tiny bags] >= 0
  c2_lowerbound: 1*[tiny bags] >= 20
  every variable >= 0
```

**LP:** infeasible  
**IP:** infeasible

- Integrality label: **integer** (rule: counts whole things)
- **My review (text-has-no-optimum):** the minimum bags need 190 units of energy; only 110 are available

## 54. `915960254`: ok (sureness: high)

> An autobody shop needs to purchase two types of car jacks, an automatic electric one, or a gas-powered one. The automatic electric one can process 5 cars every hour and uses 6 units of electricity whereas the gas-powered one can process 4 cars each hour using 7 units of gas. Since there is a limit to how many automatic electric ones there can be due to the limited number of power outlets, the shop must use less than 15 automatic electric ones. The shop can use at most 50 units of electricity and 80 units of gas. How many of each type of jack should the shop purchase to maximize the amount of cars processed every hour?

```
max 4*[gas-powered one] + 5*[automatic electric one]
  c0_upperbound: 1*[automatic electric one] <= 15
  c1_linear: 6*[automatic electric one] <= 50
  c2_linear: 7*[gas-powered one] <= 80
  every variable >= 0
```

**LP:** 87.381 (automatic electric one = 8.33333, gas-powered one = 11.4286)  
**IP:** 84 (automatic electric one = 8, gas-powered one = 11)  
**IP, strict reading:** 84 (automatic electric one = 8, gas-powered one = 11) (c0_upperbound: <= 15 became <= 14)

- Integrality label: **integer** (claude)
- Note (strict-wording): c0_upperbound: text says 'less than' (strict); modeled as <=
- Note (unlisted-variable): c1_linear: ['gas-powered one'] not listed, so coefficient 0 (the official converter: 1)
- Note (unlisted-variable): c2_linear: ['automatic electric one'] not listed, so coefficient 0 (the official converter: 1)
- **My review (ok):** electricity is used only by the electric jacks and gas only by the gas-powered ones (coefficients 0)

## 55. `1695786577`: ok (sureness: high)

> A railway company is planning the infrastructure for the city and is considering two types of transportation, trains and trams. Each train can transport 120 people per hour comfortably and each tram can transport 30 people per hour comfortably. Since trains take longer to build, the number of trams must be at least twice the number of trains. If the railway company wants to transport at least 600 people per hour, minimize the total number of transportation units required.

```
min 1*[trains] + 1*[trams]
  c0_linear: 30*[trams] + 120*[trains] >= 600
  c1_xby: 1*[trams] - 2*[trains] >= 0
  every variable >= 0
```

**LP:** 10 (trains = 3.33333, trams = 6.66667)  
**IP:** 11 (trains = 3, trams = 8)

- Integrality label: **integer** (claude)
- Note (order-mapping-overridden): order_mapping maps 'train' to 'trams', but it names 'trains'
- **My review (ok):** order_mapping sends 'train' to the trams; resolved by name. By hand: LP 10 (3.33 trains, 6.67 trams), IP 11 (3 trains, 8 trams)

## 56. `-440570570`: text-has-no-optimum (sureness: high)

> A taxi company will purchase vehicles to rent to their drivers. They are interested in purchasing either motorcycles or sedans. A motorcycle can transport 30 people, produces 4 units of pollution, and earns the taxi company $100 per shift. A sedan can transport 70 people, produces 15 units of pollution and earns the company $225 per shift. Because not every customer is comfortable with a motorcycle, at most 25% of vehicles can be motorcycles. Additionally, the company has committed to producing less than 200 units of pollution. The company needs to transport at least 1200 people every shift. How many of each type of vehicle should be used to maximize the total earnings for the taxi company per shift?

```
max 100*[motorcycles] + 225*[sedans]
  c0_ratio: 0.75*[motorcycles] - 0.25*[sedans] <= 0
  c1_linear: 4*[motorcycles] + 15*[sedans] <= 200
  c2_linear: 30*[motorcycles] + 70*[sedans] >= 1200
  every variable >= 0
```

**LP:** infeasible  
**IP:** infeasible  
**IP, strict reading:** infeasible (c1_linear: <= 200 became <= 199)

- Integrality label: **integer** (rule: counts whole things)
- Note (strict-wording): c1_linear: text says 'less than' (strict); modeled as <=
- **My review (text-has-no-optimum):** the pollution cap limits transport to ~980 people, below the 1200 required

## 57. `1197838065`: annotation-error (sureness: high)

> A drop-in clinic is performing a test either through the ear or blood. A blood test takes 30 minutes to perform while an ear test takes 5 minutes to perform. Since the blood test is more accurate, at least three times as many blood tests should be performed as ear tests. However, at least 12 ear tests must be administered. If the drop-in clinic operates for 7525 minutes, maximize the number of tests that can be performed.

```
max 1*[ear] + 1*[blood]
  c0_xby: 1*[blood] - 3*[ear] >= 0
  c1_lowerbound: 1*[ear] >= 12
  every variable >= 0
```

**LP:** unbounded  
**IP:** unbounded

- Integrality label: **integer** (rule: counts whole things)
- **My review (annotation-error):** the 7525-minute opening-hours limit is missing, so the annotated model is unbounded
- The error changes the answer.

## 58. `249236183`: text-has-no-optimum (sureness: high)

> A senior home has snacks of spinach and soybeans to increase their intake of iron. A cup of spinach contains 100 units of fibre and 5 mg of iron. A cup of soybeans contains 80 units of fibre and 12 mg of iron. Due to other nutritional requirements, the nurses decided that the number of cups of spinach must exceed the number of cups of soybeans. Furthermore, a cup of spinach contains 30 calories while a cup of soybeans contains 100 calories. If they schedule that the elderly need in total at least 12000 units of fibre and 300 mg of iron, how many cups of each should the nurses schedule to maximize the seniors’ total caloric intake?

```
max 30*[spinach] + 100*[soybeans]
  c0_linear: 100*[spinach] + 80*[soybeans] >= 12000
  c1_linear: 5*[spinach] + 12*[soybeans] >= 300
  c2_xy: 1*[spinach] - 1*[soybeans] >= 0
  every variable >= 0
```

**LP:** unbounded  
**IP:** unbounded  
**IP, strict reading:** unbounded (c2_xy: >= 0 became >= 1)

- Integrality label: **integer** (rule: counts whole things)
- Note (strict-wording): c2_xy: text says 'must exceed' (strict); modeled as >=
- **My review (text-has-no-optimum):** maximizes calories subject only to minimum requirements, so it's unbounded

## 59. `602019445`: text-has-no-optimum (sureness: high)

> A keyboard manufacturer makes mechanical and standard keyboards. Mechanical keyboards are becoming more popular and thus the manufacturer aims to have five times as many mechanical than standard keyboards. A mechanical keyboard costs five units of plastic and two units of solder whereas a standard keyboard costs two units of plastic and one unit of solder. There are still customers that prefer a less noisy alternative. Therefore, there must be at least 30 standard keyboards. If the company has available 1000 units of plastic and 250 units of solder, how many of each type should be manufactured to maximize the total number of keyboards?

```
max 1*[mechanical] + 1*[standard keyboards]
  c0_xby: 1*[mechanical] - 5*[standard keyboards] >= 0
  c1_lowerbound: 1*[standard keyboards] >= 30
  c2_linear: 5*[mechanical] + 2*[standard keyboards] <= 1000
  c3_linear: 2*[mechanical] + 1*[standard keyboards] <= 250
  every variable >= 0
```

**LP:** infeasible  
**IP:** infeasible

- Integrality label: **integer** (rule: counts whole things)
- **My review (text-has-no-optimum):** the minimums need 330 units of solder; only 250 are available

## 60. `1878130600`: annotation-error (sureness: high)

> A landscaper has 2500 square feet of grass land in a customer’s backyard where they need to cut grass using either a heavy-duty yard machine or a gas lawn mower. For each square foot of land, the heavy-duty yard machine requires 2 seconds while the gas lawn mower takes 5 seconds. Per square foot, the heavy-duty yard machine produces 12 units of pollution and requires 3 units of fuel. Conversely, the gas lawn mower generates 10 units of pollution for each square foot and requires 2 units of fuel. There are 450 units of fuel available and the landscaper can produce no more than 2000 units of pollution. For how many square feet should each machine be used to minimize the time required to cut this customer’s backyard?

```
min 5*[gas lawn mower] + 2*[heavy-duty yard machine]
  c0_linear: 2*[gas lawn mower] + 3*[heavy-duty yard machine] <= 450
  c1_linear: 12*[heavy-duty yard machine] + 10*[gas lawn mower] <= 2000
  c2_sum: 1*[heavy-duty yard machine] + 1*[gas lawn mower] <= 2500
  every variable >= 0
```

**LP:** 0 (heavy-duty yard machine = 0, gas lawn mower = 0)  
**IP:** 0 (heavy-duty yard machine = 0, gas lawn mower = 0)

- Integrality label: **continuous** (rule: asks how many square feet)
- **My review (annotation-error):** the 2500 sq ft that must be cut is annotated as an upper limit (<= 2500); read as a requirement the text is infeasible (fuel)
- The error changes the answer.

## 61. `2018818116`: degenerate-text (sureness: high)

> A park is designing their trails and can either create a wide trail or a narrow trail. A wide trail can take 50 visitors every day while the narrow trail expects 20 visitors every day. The wide trail will introduce 6 units of garbage and the narrow trail will introduce 3 units of garbage. There can be at most 3 wide trails and the park hopes to have at most 225 visitors every day. How many of each type of trail should the park construct to minimize the total amount of garbage produced.

```
min 6*[wide trail] + 3*[narrow trail]
  c0_linear: 50*[wide trail] + 20*[narrow trail] <= 225
  c1_upperbound: 1*[wide trail] <= 3
  every variable >= 0
```

**LP:** 0 (wide trail = 0, narrow trail = 0)  
**IP:** 0 (wide trail = 0, narrow trail = 0)

- Integrality label: **integer** (rule: counts whole things)
- **My review (degenerate-text):** nothing has to be made, so making nothing (objective 0) is optimal as written

## 62. `-527722703`: orlm-error (sureness: high)

> A hospital can transport their patients either using a type II ambulance or hospital van. The hospital needs to transport 320 patients every day. A type II ambulance is mounted on a truck-style chassis and can move 20 patients every shift and costs the hospital (including gas and salary) $820. A hospital van can move 15 patients and costs the hospital $550 every shift. The hospital can have at most 60% of shifts be hospital vans due to union limitations of the type II ambulance drivers. How many of shift using each type of vehicle should be scheduled to minimize the total cost to the hospital?

```
min 820*[type II ambulance] + 550*[hospital van]
  c0_linear: 20*[type II ambulance] + 15*[hospital van] >= 320
  c1_ratio: -0.6*[type II ambulance] + 0.4*[hospital van] <= 0
  every variable >= 0
```

**LP:** 12385.9 (type II ambulance = 7.52941, hospital van = 11.2941)  
**IP:** 12600 (type II ambulance = 10, hospital van = 8)

- Integrality label: **integer** (claude)
- **My review (orlm-error):** 10 ambulances + 8 vans cost $12,600, less than ORLM's $12,860
