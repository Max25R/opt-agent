# Why is each answer wrong?

You are labeling the failures of a system that turns optimization word problems into linear or integer programs and solves them. Below are 20 problems it answered wrongly. Each shows the problem text, the system's answer, the answers accepted as right, the reference model (the dataset's annotation, with whole-number or fractional variables as the problem's label says), and the system's own model. Rows marked `baseline` are answers the system gave directly, with no model.

For each failure, choose exactly one category from the table: the one for its main error, the one whose fix alone would give an accepted answer, if there is one. Mention any other errors in the note. Judge against the problem text: the reference is usually right, but it can be wrong or be one of several readings.

Reply with CSV only, and no other text: the header `number,key,category,note`, then one row per failure, with its number and key exactly as given, a category name from the table, and a one-sentence note in double quotes.

| category | meaning |
|---|---|
| `objective` | optimizes the wrong quantity, or in the wrong direction |
| `constraint-scope` | a limit applied to the wrong set of things: one combined limit read as one per item, or the reverse |
| `missing-constraint` | leaves out a requirement the text states (also when a revision deleted it) |
| `invented-constraint` | adds a requirement the text doesn't state |
| `coefficient` | a wrong number: misread, attached to the wrong variable, or converted between units wrongly |
| `direction` | a constraint points the wrong way (at least vs at most), and no accepted reading allows it |
| `integrality` | whole numbers vs fractions differ from the label |
| `rounding` | the right answer, rounded too far to match at 1e-6 |
| `calculation` | no misreading found that gives this answer: a slip in the arithmetic or in finding the best choice |
| `reference` | the system's reading is one the text supports but no accepted reading allows, or the reference is wrong |
| `other` | none of these; say what in the note |

## 1. `1344881875`: baseline (key `640f2a95687b`)

> A farmer has 140 hectares available to grow tomatoes and potatoes. She prefers to plant more tomatoes than potatoes, but the soil and weather conditions allow her to grow at most twice the amount of tomatoes to that of potatoes. In addition, she must grow at least 20 hectares of tomatoes and at least 30 hectares of potatoes to meet community demands. If the profit per hectare of tomatoes is $350 and the profit per hectare of potatoes is $600, how many hectares of each crop should she plant to maximize profit? What is this profit?

**Answered:** optimal 59500  
**Accepted:** optimal 79000 (annotated)  
**As annotated:** LP optimal 79000, IP optimal 79000; label integer

Reference (the annotation, with its label):
```
max 350*[tomatoes] + 600*[potatoes]
  c0_sum: 1*[tomatoes] + 1*[potatoes] <= 140
  c1_xby: 1*[tomatoes] - 2*[potatoes] <= 0
  c2_lowerbound: 1*[tomatoes] >= 20
  c3_lowerbound: 1*[potatoes] >= 30
  tomatoes: integer, in [0, inf]
  potatoes: integer, in [0, inf]
```

No model: the baseline answers directly.

## 2. `1344881875`: single-shot, self-correction (key `427f5774b4f4`)

> A farmer has 140 hectares available to grow tomatoes and potatoes. She prefers to plant more tomatoes than potatoes, but the soil and weather conditions allow her to grow at most twice the amount of tomatoes to that of potatoes. In addition, she must grow at least 20 hectares of tomatoes and at least 30 hectares of potatoes to meet community demands. If the profit per hectare of tomatoes is $350 and the profit per hectare of potatoes is $600, how many hectares of each crop should she plant to maximize profit? What is this profit?

**Answered:** optimal 66500  
**Accepted:** optimal 79000 (annotated)  
**As annotated:** LP optimal 79000, IP optimal 79000; label integer

Reference (the annotation, with its label):
```
max 350*[tomatoes] + 600*[potatoes]
  c0_sum: 1*[tomatoes] + 1*[potatoes] <= 140
  c1_xby: 1*[tomatoes] - 2*[potatoes] <= 0
  c2_lowerbound: 1*[tomatoes] >= 20
  c3_lowerbound: 1*[potatoes] >= 30
  tomatoes: integer, in [0, inf]
  potatoes: integer, in [0, inf]
```

The system's model:
```
max 350*[tomato_hectares] + 600*[potato_hectares]
  land: 1*[tomato_hectares] + 1*[potato_hectares] <= 140
  tomatoes_more_than_potatoes: 1*[tomato_hectares] - 1*[potato_hectares] >= 0
  tomato_at_most_twice_potato: 1*[tomato_hectares] - 2*[potato_hectares] <= 0
  min_tomato: 1*[tomato_hectares] >= 20
  min_potato: 1*[potato_hectares] >= 30
  tomato_hectares: continuous, in [0, inf]
  potato_hectares: continuous, in [0, inf]
```

## 3. `431521997`: baseline (key `a1ccef523f8d`)

> A bubble tea shop sells mango and lychee bubble tea. Each mango bubble tea requires 4 units of mango juice and 8 units of tea. Each lychee bubble tea requires 6 units of lychee juice and 6 units of tea. The shop has available 2000 units of mango juice and 3000 units of lychee juice. At least 40% of the bubble teas made must be lychee flavored. However, mango bubble tea sells better and thus the number of mango bubble teas made must be large than the number of lychee bubble teas made. How many of each bubble tea flavor should be made to minimize the total amount of tea needed?

**Answered:** optimal 36  
**Accepted:** optimal 0 (annotated)  
**As annotated:** LP optimal 0, IP optimal 0; label continuous

- The same answer as row 4's model.

Reference (the annotation, with its label):
```
min 8*[mango bubble tea] + 6*[lychee bubble tea]
  c0_linear: 4*[mango bubble tea] <= 2000
  c1_linear: 6*[lychee bubble tea] <= 3000
  c2_ratio: 0.6*[lychee bubble tea] - 0.4*[mango bubble tea] >= 0
  c3_xy: 1*[mango bubble tea] - 1*[lychee bubble tea] >= 0
  lychee bubble tea: continuous, in [0, inf]
  mango bubble tea: continuous, in [0, inf]
```

No model: the baseline answers directly.

Review (degenerate-text): nothing has to be made, so making nothing (objective 0) is optimal as written; each unlisted coefficient really is 0: the resource is used by one product only

## 4. `431521997`: single-shot, self-correction (key `e19b1271eb6a`)

> A bubble tea shop sells mango and lychee bubble tea. Each mango bubble tea requires 4 units of mango juice and 8 units of tea. Each lychee bubble tea requires 6 units of lychee juice and 6 units of tea. The shop has available 2000 units of mango juice and 3000 units of lychee juice. At least 40% of the bubble teas made must be lychee flavored. However, mango bubble tea sells better and thus the number of mango bubble teas made must be large than the number of lychee bubble teas made. How many of each bubble tea flavor should be made to minimize the total amount of tea needed?

**Answered:** optimal 36  
**Accepted:** optimal 0 (annotated)  
**As annotated:** LP optimal 0, IP optimal 0; label continuous

Reference (the annotation, with its label):
```
min 8*[mango bubble tea] + 6*[lychee bubble tea]
  c0_linear: 4*[mango bubble tea] <= 2000
  c1_linear: 6*[lychee bubble tea] <= 3000
  c2_ratio: 0.6*[lychee bubble tea] - 0.4*[mango bubble tea] >= 0
  c3_xy: 1*[mango bubble tea] - 1*[lychee bubble tea] >= 0
  lychee bubble tea: continuous, in [0, inf]
  mango bubble tea: continuous, in [0, inf]
```

The system's model:
```
min 8*[mango bubble teas made] + 6*[lychee bubble teas made]
  mango juice available: 4*[mango bubble teas made] <= 2000
  lychee juice available: 6*[lychee bubble teas made] >= 0
  lychee at least 40 percent of total: -0.4*[mango bubble teas made] + 0.6*[lychee bubble teas made] >= 0
  mango more than lychee: 1*[mango bubble teas made] - 1*[lychee bubble teas made] >= 1
  mango bubble teas made: integer, in [0, inf]
  lychee bubble teas made: integer, in [0, inf]
```

Review (degenerate-text): nothing has to be made, so making nothing (objective 0) is optimal as written; each unlisted coefficient really is 0: the resource is used by one product only

## 5. `-2012603375`: single-shot, self-correction (key `67fbee25f880`)

> In order to make carbon dioxide, wood is burned using two processes, with a catalyst and without a catalyst. The process with a catalyst requires 10 units of wood and 20 units of oxygen to make 15 units of carbon dioxide. The process without a catalyst requires 15 units of wood and 12 units of oxygen to make 18 units of carbon dioxide. There are 300 units of wood and 300 units of oxygen available. How many of each process should be used to maximize the amount of carbon dioxide produced?

**Answered:** optimal 375.000006  
**Accepted:** optimal 369 (annotated)  
**As annotated:** LP optimal 375.000006, IP optimal 369; label integer

- Correct if integrality weren't graded (the lenient score, 3f).

Reference (the annotation, with its label):
```
max 15*[with a catalyst] + 18*[without a catalyst]
  c0_linear: 10*[with a catalyst] + 15*[without a catalyst] <= 300
  c1_linear: 20*[with a catalyst] + 12*[without a catalyst] <= 300
  with a catalyst: integer, in [0, inf]
  without a catalyst: integer, in [0, inf]
```

The system's model:
```
max 15*[catalyst process runs] + 18*[non-catalyst process runs]
  wood: 10*[catalyst process runs] + 15*[non-catalyst process runs] <= 300
  oxygen: 20*[catalyst process runs] + 12*[non-catalyst process runs] <= 300
  catalyst process runs: continuous, in [0, inf]
  non-catalyst process runs: continuous, in [0, inf]
```

## 6. `1605420061`: baseline (key `e4dd618af202`)

> A crepe store sells chocolate and peanut butter crepes. A chocolate crepe requires 3 units of chocolate spread and 6 units of crepe mix. A peanut butter crepe requires 4 units of peanut butter spread and 7 units of crepe mix. Recently, the peanut butter crepe has been more popular and therefore the number of peanut butter crepes made must exceed the number of chocolate crepes made. However at least 25% of the crepes made should be chocolate. The store has available 400 units of chocolate spread and 450 units of peanut butter spread. How many of each should the store make to minimize the total amount of crepe mix needed?

**Answered:** optimal 20  
**Accepted:** optimal 0 (annotated)  
**As annotated:** LP optimal 0, IP optimal 0; label continuous

- The same answer as row 7's model.

Reference (the annotation, with its label):
```
min 6*[chocolate crepe] + 7*[peanut butter crepes]
  c0_xy: 1*[peanut butter crepes] - 1*[chocolate crepe] >= 0
  c1_ratio: -0.25*[peanut butter crepes] + 0.75*[chocolate crepe] >= 0
  c2_linear: 3*[chocolate crepe] <= 400
  c3_linear: 4*[peanut butter crepes] <= 450
  peanut butter crepes: continuous, in [0, inf]
  chocolate crepe: continuous, in [0, inf]
```

No model: the baseline answers directly.

Review (degenerate-text): nothing has to be made, so making nothing (objective 0) is optimal as written; each unlisted coefficient really is 0: the resource is used by one product only

## 7. `1605420061`: single-shot, self-correction (key `253358322749`)

> A crepe store sells chocolate and peanut butter crepes. A chocolate crepe requires 3 units of chocolate spread and 6 units of crepe mix. A peanut butter crepe requires 4 units of peanut butter spread and 7 units of crepe mix. Recently, the peanut butter crepe has been more popular and therefore the number of peanut butter crepes made must exceed the number of chocolate crepes made. However at least 25% of the crepes made should be chocolate. The store has available 400 units of chocolate spread and 450 units of peanut butter spread. How many of each should the store make to minimize the total amount of crepe mix needed?

**Answered:** optimal 20  
**Accepted:** optimal 0 (annotated)  
**As annotated:** LP optimal 0, IP optimal 0; label continuous

Reference (the annotation, with its label):
```
min 6*[chocolate crepe] + 7*[peanut butter crepes]
  c0_xy: 1*[peanut butter crepes] - 1*[chocolate crepe] >= 0
  c1_ratio: -0.25*[peanut butter crepes] + 0.75*[chocolate crepe] >= 0
  c2_linear: 3*[chocolate crepe] <= 400
  c3_linear: 4*[peanut butter crepes] <= 450
  peanut butter crepes: continuous, in [0, inf]
  chocolate crepe: continuous, in [0, inf]
```

The system's model:
```
min 6*[chocolate crepes made] + 7*[peanut butter crepes made]
  chocolate spread: 3*[chocolate crepes made] <= 400
  peanut butter spread: 4*[peanut butter crepes made] <= 450
  peanut butter exceeds chocolate: 1*[peanut butter crepes made] - 1*[chocolate crepes made] >= 1
  chocolate at least 25 percent of crepes: 3*[chocolate crepes made] - 1*[peanut butter crepes made] >= 0
  chocolate crepes made: integer, in [0, inf]
  peanut butter crepes made: integer, in [0, inf]
```

Review (degenerate-text): nothing has to be made, so making nothing (objective 0) is optimal as written; each unlisted coefficient really is 0: the resource is used by one product only

## 8. `-1540907330`: baseline (key `247f393b269e`)

> An Indian restaurant makes goat and chicken curry. Each bowl of goat curry requires 3 units of goat meat and 6 units of the curry base. Each bowl of chicken curry requires 5 units of chicken meat and 5 units of the curry base. The restaurant has available 1500 units of goat meat and 2000 units of chicken meat. At least 25% of the bowls made must be chicken curry. Since goat curry is more popular, the number of goat curry bowls must be larger than the number of chicken curry bowls. How many of each type of curry bowl should be made to minimize the total amount of curry base used?

**Answered:** optimal 17  
**Accepted:** optimal 0 (annotated)  
**As annotated:** LP optimal 0, IP optimal 0; label continuous

- The same answer as row 9's model.

Reference (the annotation, with its label):
```
min 6*[goat] + 5*[chicken]
  c0_linear: 3*[goat] <= 1500
  c1_linear: 5*[chicken] <= 2000
  c2_ratio: -0.25*[goat] + 0.75*[chicken] >= 0
  c3_xy: 1*[goat] - 1*[chicken] >= 0
  goat: continuous, in [0, inf]
  chicken: continuous, in [0, inf]
```

No model: the baseline answers directly.

Review (degenerate-text): nothing has to be made, so making nothing (objective 0) is optimal as written; each unlisted coefficient really is 0: the resource is used by one product only

## 9. `-1540907330`: single-shot, self-correction (key `f2fab7f6a053`)

> An Indian restaurant makes goat and chicken curry. Each bowl of goat curry requires 3 units of goat meat and 6 units of the curry base. Each bowl of chicken curry requires 5 units of chicken meat and 5 units of the curry base. The restaurant has available 1500 units of goat meat and 2000 units of chicken meat. At least 25% of the bowls made must be chicken curry. Since goat curry is more popular, the number of goat curry bowls must be larger than the number of chicken curry bowls. How many of each type of curry bowl should be made to minimize the total amount of curry base used?

**Answered:** optimal 17  
**Accepted:** optimal 0 (annotated)  
**As annotated:** LP optimal 0, IP optimal 0; label continuous

Reference (the annotation, with its label):
```
min 6*[goat] + 5*[chicken]
  c0_linear: 3*[goat] <= 1500
  c1_linear: 5*[chicken] <= 2000
  c2_ratio: -0.25*[goat] + 0.75*[chicken] >= 0
  c3_xy: 1*[goat] - 1*[chicken] >= 0
  goat: continuous, in [0, inf]
  chicken: continuous, in [0, inf]
```

The system's model:
```
min 6*[goat curry bowls] + 5*[chicken curry bowls]
  goat meat: 3*[goat curry bowls] <= 1500
  chicken meat: 5*[chicken curry bowls] <= 2000
  chicken share: -0.25*[goat curry bowls] + 0.75*[chicken curry bowls] >= 0
  goat popularity: 1*[goat curry bowls] - 1*[chicken curry bowls] >= 1
  goat curry bowls: integer, in [0, inf]
  chicken curry bowls: integer, in [0, inf]
```

Review (degenerate-text): nothing has to be made, so making nothing (objective 0) is optimal as written; each unlisted coefficient really is 0: the resource is used by one product only

## 10. `-38093970`: baseline (key `345e1e034ddd`)

> A drug company is making allergy pills and fever reducing pills in two factories, factory 1 and factory 2. Factory 1 produces 20 allergy pills and 15 fever reducing pills per hour. Factory 2 produces 10 allergy pills and 30 fever reducing pills per hour.  Factory 1 is much more efficient and only requires 20 units of a rare compound while factory 2 requires 30 units of a rare compound. The company only has available 1000 units of the rare compound. If the company must make at least 700 allergy pills and 600 fever reducing pills, how many hours should each factory be run to minimize the total time needed?

**Answered:** optimal 35  
**Accepted:** optimal 37 (annotated); optimal 36.6666663 (annotated)  
**As annotated:** LP optimal 36.6666663, IP optimal 37; label either

Reference (the annotation, with its label):
```
min 1*[factory 1] + 1*[factory 2]
  c0_linear: 20*[factory 1] + 30*[factory 2] <= 1000
  c1_linear: 20*[factory 1] + 10*[factory 2] >= 700
  c2_linear: 15*[factory 1] + 30*[factory 2] >= 600
  factory 1: integer, in [0, inf]
  factory 2: integer, in [0, inf]
```

No model: the baseline answers directly.

## 11. `-926961422`: baseline (key `3fd95540fd36`)

> A music company produces two types of digital keyboards, one is full-weighted and another is semi-weighted. Both keyboards are sold for $2800 and $2400 respectively. There are about 3500 oscillator chips available every day from which the full-weighted version requires 20 chips while the semi-weighted version requires 15 chips. The company has a total of 6 working hours a day. Both of these keyboards require a production time of 1.2 hours. What should be the manufacturing quantity for each of the keyboards to maximize the total revenue?

**Answered:** optimal 14000  
**Accepted:** optimal 559600 (annotated)  
**As annotated:** LP optimal 559999.992, IP optimal 559600; label integer

- The same answer as row 12's model.

Reference (the annotation, with its label):
```
max 2800*[full-weighted] + 2400*[semi-weighted]
  c0_linear: 20*[full-weighted] + 15*[semi-weighted] <= 3500
  c1_linear: 1.2*[full-weighted] + 1.2*[semi-weighted] >= 6
  full-weighted: integer, in [0, inf]
  semi-weighted: integer, in [0, inf]
```

No model: the baseline answers directly.

## 12. `-926961422`: single-shot, self-correction (key `7a8161cb4ddd`)

> A music company produces two types of digital keyboards, one is full-weighted and another is semi-weighted. Both keyboards are sold for $2800 and $2400 respectively. There are about 3500 oscillator chips available every day from which the full-weighted version requires 20 chips while the semi-weighted version requires 15 chips. The company has a total of 6 working hours a day. Both of these keyboards require a production time of 1.2 hours. What should be the manufacturing quantity for each of the keyboards to maximize the total revenue?

**Answered:** optimal 14000  
**Accepted:** optimal 559600 (annotated)  
**As annotated:** LP optimal 559999.992, IP optimal 559600; label integer

Reference (the annotation, with its label):
```
max 2800*[full-weighted] + 2400*[semi-weighted]
  c0_linear: 20*[full-weighted] + 15*[semi-weighted] <= 3500
  c1_linear: 1.2*[full-weighted] + 1.2*[semi-weighted] >= 6
  full-weighted: integer, in [0, inf]
  semi-weighted: integer, in [0, inf]
```

The system's model:
```
max 2800*[full-weighted keyboards] + 2400*[semi-weighted keyboards]
  oscillator chips: 20*[full-weighted keyboards] + 15*[semi-weighted keyboards] <= 3500
  production hours: 1.2*[full-weighted keyboards] + 1.2*[semi-weighted keyboards] <= 6
  full-weighted keyboards: integer, in [0, inf]
  semi-weighted keyboards: integer, in [0, inf]
```

## 13. `181608358`: baseline (key `0490589d903d`)

> A concert organizer has to transport equipment using carts or trolleys. Carts can transport 5 kg/min of equipment and requires 2 workers. Trolleys can transport 7 kg/min of equipment and requires 4 workers. There must be at least 12 trolleys to be used. Additionally, only a maximum of 40% of the transportation can be using trolleys. The organizer has to deliver at a rate of 100 kg/min of equipment. How many of each transportation method should be used to minimize the total number of workers?

**Answered:** optimal 100  
**Accepted:** optimal 84 (annotated)  
**As annotated:** LP optimal 84, IP optimal 84; label integer

- The same answer as row 14's model.

Reference (the annotation, with its label):
```
min 2*[carts] + 4*[trolleys]
  c0_linear: 5*[carts] + 7*[trolleys] >= 100
  c1_lowerbound: 1*[trolleys] >= 12
  c2_ratio: -0.4*[carts] + 0.6*[trolleys] <= 0
  carts: integer, in [0, inf]
  trolleys: integer, in [0, inf]
```

No model: the baseline answers directly.

## 14. `181608358`: single-shot, self-correction (key `0b4989196d97`)

> A concert organizer has to transport equipment using carts or trolleys. Carts can transport 5 kg/min of equipment and requires 2 workers. Trolleys can transport 7 kg/min of equipment and requires 4 workers. There must be at least 12 trolleys to be used. Additionally, only a maximum of 40% of the transportation can be using trolleys. The organizer has to deliver at a rate of 100 kg/min of equipment. How many of each transportation method should be used to minimize the total number of workers?

**Answered:** optimal 100  
**Accepted:** optimal 84 (annotated)  
**As annotated:** LP optimal 84, IP optimal 84; label integer

Reference (the annotation, with its label):
```
min 2*[carts] + 4*[trolleys]
  c0_linear: 5*[carts] + 7*[trolleys] >= 100
  c1_lowerbound: 1*[trolleys] >= 12
  c2_ratio: -0.4*[carts] + 0.6*[trolleys] <= 0
  carts: integer, in [0, inf]
  trolleys: integer, in [0, inf]
```

The system's model:
```
min 2*[carts] + 4*[trolleys]
  delivery_rate: 5*[carts] + 7*[trolleys] >= 100
  min_trolleys: 1*[trolleys] >= 12
  trolley_share_max_40_percent: 4.2*[trolleys] - 2*[carts] <= 0
  carts: integer, in [0, inf]
  trolleys: integer, in [0, inf]
```

## 15. `-2138755435`: baseline (key `d6846668d636`)

> A dim sum restaurant can deliver their food by cart or by hand. Servers can deliver by cart and have 70 customer interactions and will have to refill food five times an hour. They can also deliver more food by hand, due to the increased mobility, and have 85 customer interactions while refilling food twenty times an hour. However, the customers get more options when delivering by cart, therefore at least 70% of delivery shifts must be by cart. There must be at least 3 servers delivering by hand for their direct customer service. If the restaurant wants to have 4000 customer interactions per hour, how many of each form of delivery should the dim sum restaurant schedule to minimize the total number of refills per hour?

**Answered:** optimal 425  
**Accepted:** optimal 95 (annotated)  
**As annotated:** LP optimal 95, IP optimal 95; label integer

- The same answer as row 16's model.

Reference (the annotation, with its label):
```
min 5*[cart] + 20*[hand]
  c0_ratio: 0.3*[cart] - 0.7*[hand] >= 0
  c1_lowerbound: 1*[hand] >= 3
  c2_linear: 70*[cart] + 85*[hand] <= 4000
  cart: integer, in [0, inf]
  hand: integer, in [0, inf]
```

No model: the baseline answers directly.

## 16. `-2138755435`: single-shot, self-correction (key `3a8922d1e80d`)

> A dim sum restaurant can deliver their food by cart or by hand. Servers can deliver by cart and have 70 customer interactions and will have to refill food five times an hour. They can also deliver more food by hand, due to the increased mobility, and have 85 customer interactions while refilling food twenty times an hour. However, the customers get more options when delivering by cart, therefore at least 70% of delivery shifts must be by cart. There must be at least 3 servers delivering by hand for their direct customer service. If the restaurant wants to have 4000 customer interactions per hour, how many of each form of delivery should the dim sum restaurant schedule to minimize the total number of refills per hour?

**Answered:** optimal 425  
**Accepted:** optimal 95 (annotated)  
**As annotated:** LP optimal 95, IP optimal 95; label integer

Reference (the annotation, with its label):
```
min 5*[cart] + 20*[hand]
  c0_ratio: 0.3*[cart] - 0.7*[hand] >= 0
  c1_lowerbound: 1*[hand] >= 3
  c2_linear: 70*[cart] + 85*[hand] <= 4000
  cart: integer, in [0, inf]
  hand: integer, in [0, inf]
```

The system's model:
```
min 5*[cart_servers] + 20*[hand_servers]
  customer_interactions: 70*[cart_servers] + 85*[hand_servers] == 4000
  cart_share_at_least_70_percent: 0.3*[cart_servers] - 0.7*[hand_servers] >= 0
  min_hand_servers: 1*[hand_servers] >= 3
  cart_servers: integer, in [0, inf]
  hand_servers: integer, in [0, inf]
```

## 17. `-258335120`: single-shot, self-correction (key `9b88d1204a80`)

> Platinum in combination with palladium has been used as a catalyst in cars and it changes carbon monoxide, which is toxic, into carbon dioxide. An automotive company is comparing two different catalysts, a palladium-heavy catalyst and a platinum-heavy catalyst. The process with a palladium-heavy catalyst requires 15 units of platinum and 25 units of palladium and can perform the conversion to carbon dioxide at a rate of 5 units per second. A platinum-heavy catalyst requires 20 units of platinum and 14 units of palladium and converts to carbon dioxide at a rate of 4 units per second. There are 450 units of platinum and 390 units of palladium available. How many of each catalyst should be used to maximize the amount converted into carbon dioxide?

**Answered:** optimal 100.344829  
**Accepted:** optimal 98 (annotated)  
**As annotated:** LP optimal 100.344829, IP optimal 98; label integer

- Correct if integrality weren't graded (the lenient score, 3f).

Reference (the annotation, with its label):
```
max 5*[palladium-heavy catalyst] + 4*[platinum-heavy catalyst]
  c0_linear: 14*[platinum-heavy catalyst] + 25*[palladium-heavy catalyst] <= 390
  c1_linear: 15*[palladium-heavy catalyst] + 20*[platinum-heavy catalyst] <= 450
  palladium-heavy catalyst: integer, in [0, inf]
  platinum-heavy catalyst: integer, in [0, inf]
```

The system's model:
```
max 5*[palladium-heavy catalyst] + 4*[platinum-heavy catalyst]
  platinum available: 15*[palladium-heavy catalyst] + 20*[platinum-heavy catalyst] <= 450
  palladium available: 25*[palladium-heavy catalyst] + 14*[platinum-heavy catalyst] <= 390
  palladium-heavy catalyst: continuous, in [0, inf]
  platinum-heavy catalyst: continuous, in [0, inf]
```

## 18. `602019445`: baseline (key `9d9faf3cb66b`)

> A keyboard manufacturer makes mechanical and standard keyboards. Mechanical keyboards are becoming more popular and thus the manufacturer aims to have five times as many mechanical than standard keyboards. A mechanical keyboard costs five units of plastic and two units of solder whereas a standard keyboard costs two units of plastic and one unit of solder. There are still customers that prefer a less noisy alternative. Therefore, there must be at least 30 standard keyboards. If the company has available 1000 units of plastic and 250 units of solder, how many of each type should be manufactured to maximize the total number of keyboards?

**Answered:** optimal 132  
**Accepted:** infeasible (annotated); infeasible (equality)  
**As annotated:** LP infeasible, IP infeasible; label integer

Reference (the annotation, with its label):
```
max 1*[mechanical] + 1*[standard keyboards]
  c0_xby: 1*[mechanical] - 5*[standard keyboards] >= 0
  c1_lowerbound: 1*[standard keyboards] >= 30
  c2_linear: 5*[mechanical] + 2*[standard keyboards] <= 1000
  c3_linear: 2*[mechanical] + 1*[standard keyboards] <= 250
  mechanical: integer, in [0, inf]
  standard keyboards: integer, in [0, inf]
```

No model: the baseline answers directly.

Review (text-has-no-optimum): the minimums need 330 units of solder; only 250 are available

## 19. `2078392466`: baseline (key `e5d60d789150`)

> A brewery can ferment their product into either wine or kombucha. Each unit of wine requires 3 units of fruit and 8 units of water. Each unit of kombucha requires 5 units of fruit and 7 units of tea. The company has available 7000 units of water and 9000 units of tea. Wine sells for more, therefore the number of wine must be larger than the number of kombucha. Additionally, at least 20% of their products made must be kombucha. How many of each should the brewery make to minimize the total units of fruit required?

**Answered:** optimal 11  
**Accepted:** optimal 0 (annotated)  
**As annotated:** LP optimal 0, IP optimal 0; label continuous

- The same answer as row 20's model.

Reference (the annotation, with its label):
```
min 3*[wine] + 5*[kombucha]
  c0_linear: 8*[wine] <= 7000
  c1_linear: 7*[kombucha] <= 9000
  c2_xy: 1*[wine] - 1*[kombucha] >= 0
  c3_ratio: -0.2*[wine] + 0.8*[kombucha] >= 0
  wine: continuous, in [0, inf]
  kombucha: continuous, in [0, inf]
```

No model: the baseline answers directly.

Review (degenerate-text): nothing has to be made, so making nothing (objective 0) is optimal as written; each unlisted coefficient really is 0: the resource is used by one product only

## 20. `2078392466`: single-shot, self-correction (key `bea6fb2fa5c4`)

> A brewery can ferment their product into either wine or kombucha. Each unit of wine requires 3 units of fruit and 8 units of water. Each unit of kombucha requires 5 units of fruit and 7 units of tea. The company has available 7000 units of water and 9000 units of tea. Wine sells for more, therefore the number of wine must be larger than the number of kombucha. Additionally, at least 20% of their products made must be kombucha. How many of each should the brewery make to minimize the total units of fruit required?

**Answered:** optimal 11  
**Accepted:** optimal 0 (annotated)  
**As annotated:** LP optimal 0, IP optimal 0; label continuous

Reference (the annotation, with its label):
```
min 3*[wine] + 5*[kombucha]
  c0_linear: 8*[wine] <= 7000
  c1_linear: 7*[kombucha] <= 9000
  c2_xy: 1*[wine] - 1*[kombucha] >= 0
  c3_ratio: -0.2*[wine] + 0.8*[kombucha] >= 0
  wine: continuous, in [0, inf]
  kombucha: continuous, in [0, inf]
```

The system's model:
```
min 3*[wine units] + 5*[kombucha units]
  water: 8*[wine units] <= 7000
  tea: 7*[kombucha units] <= 9000
  wine_more_than_kombucha: 1*[wine units] - 1*[kombucha units] >= 1
  kombucha_at_least_20_percent: -0.2*[wine units] + 0.8*[kombucha units] >= 0
  wine units: integer, in [0, inf]
  kombucha units: integer, in [0, inf]
```

Review (degenerate-text): nothing has to be made, so making nothing (objective 0) is optimal as written; each unlisted coefficient really is 0: the resource is used by one product only
