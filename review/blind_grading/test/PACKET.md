# Blind grading: `test`

40 models of word problems, drawn at random (seed 20261030, `python -m opt_agent.blind_grading runs/test`). For each, decide whether the model says what the text says, and write `right`, `wrong` or `unsure` in the `grade` column of `grades.csv`, with a note if it helps. Then run `python -m opt_agent.report runs/test`.

- **right**: a correct model of the text, under any reading the text supports. Names, the order of terms, and equivalent forms (x <= 3y written as x - 3y <= 0) don't matter.
- **wrong**: some part doesn't say what the text says: the objective, a constraint, a number, a direction, or whole numbers vs fractions.
- **unsure**: you can't decide.

The reference is the dataset's annotation, with the problem's integrality label. It's usually right, but it can be wrong or be one of several readings: grade against the text.

Answers, scores, conditions and problem ids are left out on purpose. Until you're done, please don't open the run's files, its report, or `review/taxonomy/`, which lists the wrong answers.

## 1.

> A zookeeper feeds a gorilla with bananas and mangoes. Each banana contains 80 calories, 20 grams of potassium, and 10 grams of sugar. Each mango contains 100 calories, 15 grams of potassium, and 8 grams of sugar.  The gorilla must consume at least 4000 calories and 150 grams of potassium. Since the gorilla prefers bananas, at most 33% of the fruits he eats can be mangoes. If excess sugar makes the gorilla aggressive, how many of each fruit should he consume to minimize his sugar intake?

Reference:
```
min 10*[bananas] + 8*[mangoes]
  c0_linear: 80*[bananas] + 100*[mangoes] >= 4000
  c1_linear: 20*[bananas] + 15*[mangoes] >= 150
  c2_ratio: -0.33*[bananas] + 0.67*[mangoes] <= 0
  bananas: integer, in [0, inf]
  mangoes: integer, in [0, inf]
```

To grade:
```
min 10*[bananas] + 8*[mangoes]
  calories: 80*[bananas] + 100*[mangoes] >= 4000
  potassium: 20*[bananas] + 15*[mangoes] >= 150
  mango_share: -0.33*[bananas] + 0.67*[mangoes] <= 0
  bananas: integer, in [0, inf]
  mangoes: integer, in [0, inf]
```

## 2.

> A pharmaceutical company has 800 units of painkiller medicine and makes daytime and nighttime painkiller. A daytime pill has 6 units of painkiller medicine and 2 units of sleep medicine. A nighttime pill has 5 units of painkiller medicine and 5 units of sleep medicine. Since some people don’t want the sleeping effect, at least 40% of the pills must be daytime pills. However at least 200 nighttime pills must be made. How many of each pill should be made to minimize the total amount of sleep medicine required?

Reference:
```
min 2*[daytime] + 5*[nighttime painkiller]
  c0_linear: 6*[daytime] + 5*[nighttime painkiller] <= 800
  c1_ratio: 0.6*[daytime] - 0.4*[nighttime painkiller] >= 0
  c2_lowerbound: 1*[nighttime painkiller] >= 200
  daytime: integer, in [0, inf]
  nighttime painkiller: integer, in [0, inf]
```

To grade:
```
min 2*[daytime pills] + 5*[nighttime pills]
  painkiller medicine: 6*[daytime pills] + 5*[nighttime pills] <= 800
  daytime share at least 40%: 0.6*[daytime pills] - 0.4*[nighttime pills] >= 0
  minimum nighttime pills: 1*[nighttime pills] >= 200
  daytime pills: integer, in [0, inf]
  nighttime pills: integer, in [0, inf]
```

## 3.

> A factory provides rides for its employees in either taxis or company cars. Each taxi ride can take 2 employees while each company car ride can take 3 employees. Since buying and maintaining cars is expensive, at most 60% of the rides can be company car rides. However, there has to be at least 30 company car rides. If the company needs to transport at least 500 employees, how many rides of each should be done to minimize the total number of taxi rides.

Reference:
```
min 1*[taxis]
  c0_ratio: -0.6*[taxis] + 0.4*[company cars] <= 0
  c1_lowerbound: 1*[company cars] >= 30
  c2_linear: 2*[taxis] + 3*[company cars] >= 500
  taxis: integer, in [0, inf]
  company cars: integer, in [0, inf]
```

To grade:
```
min 1*[taxi rides]
  capacity: 2*[taxi rides] + 3*[company car rides] >= 500
  car_share_limit: 0.4*[company car rides] - 0.6*[taxi rides] <= 0
  min_car_rides: 1*[company car rides] >= 30
  taxi rides: integer, in [0, inf]
  company car rides: integer, in [0, inf]
```

## 4.

> Ayse produces a plant growth compound by mixing two types of fertilizer: C and Y. This growth compound must contain at least 5 units of nitrous oxide and 8 units of vitamin mix. Fertilizer C and Y cost $2 and $3 per kg respectively. Fertilizer C contains 1.5 units of nitrous oxide per kg and 3 units of vitamin mix per kg. Fertilizer Y contains 5 units of nitrous oxide per kg and 1 unit of vitamin mix per kg. Determine the minimum cost of Ayse's compound.

Reference:
```
min 2*[C] + 3*[Y.]
  c0_linear: 1.5*[C] + 5*[Y.] >= 5
  c1_linear: 3*[C] + 1*[Y.] >= 8
  C: continuous, in [0, inf]
  Y.: continuous, in [0, inf]
```

To grade:
```
min 2*[kilograms of fertilizer C] + 3*[kilograms of fertilizer Y]
  nitrous oxide minimum: 1.5*[kilograms of fertilizer C] + 5*[kilograms of fertilizer Y] >= 5
  vitamin mix minimum: 3*[kilograms of fertilizer C] + 1*[kilograms of fertilizer Y] >= 8
  kilograms of fertilizer C: continuous, in [0, inf]
  kilograms of fertilizer Y: continuous, in [0, inf]
```

## 5.

> A candy store mixes regular candy and sour candy to prepare two products, regular mix and sour surprise mix. Each kilogram of the regular mix contains 0.8 kg of regular candy and 0.2 kg of sour candy. The profit per kilogram of the regular mix is $3. Each kilogram of the sour surprise mix contains 0.1 kg of regular candy and 0.9 kg of sour candy. The profit per kilogram of the sour surprise mix is $5. The candy store has 80 kg of regular candy and 60 kg of sour candy available. How many kilograms of each type of candy mix should be created to maximize profits?

Reference:
```
max 3*[regular mix] + 5*[sour surprise mix]
  c0_linear: 0.8*[regular mix] + 0.1*[sour surprise mix] <= 80
  c1_linear: 0.2*[regular mix] + 0.9*[sour surprise mix] <= 60
  regular mix: continuous, in [0, inf]
  sour surprise mix: continuous, in [0, inf]
```

To grade:
```
max 3*[regular_mix_kg] + 5*[sour_surprise_mix_kg]
  regular_candy_available: 0.8*[regular_mix_kg] + 0.1*[sour_surprise_mix_kg] <= 80
  sour_candy_available: 0.2*[regular_mix_kg] + 0.9*[sour_surprise_mix_kg] <= 60
  regular_mix_kg: continuous, in [0, inf]
  sour_surprise_mix_kg: continuous, in [0, inf]
```

## 6.

> A bee farmer transports his honey in small and large bottles. A small bottle can take 5 units of honey while a large bottle can take 20 units of honey. The farmer has available at most 300 small bottles and at most 100 large bottles. In addition, since small bottles are easier to sell, at least twice as many small bottles must be used than large bottles. Finally, he can transport at most 200 bottles total and at least 50 must be large bottles. How many of each bottle should be use to maximize the total amount of honey he can transport?

Reference:
```
max 5*[small] + 20*[large]
  c0_upperbound: 1*[small] <= 300
  c1_upperbound: 1*[large] <= 100
  c2_xby: 1*[small] - 2*[large] >= 0
  c3_sum: 1*[small] + 1*[large] <= 200
  c4_lowerbound: 1*[large] >= 50
  small: integer, in [0, inf]
  large: integer, in [0, inf]
```

To grade:
```
max 5*[small bottles] + 20*[large bottles]
  small_at_least_twice_large: 1*[small bottles] - 2*[large bottles] >= 0
  total_bottles_at_most_200: 1*[small bottles] + 1*[large bottles] <= 200
  at_least_50_large: 1*[large bottles] >= 50
  small bottles: integer, in [0, 300]
  large bottles: integer, in [0, 100]
```

## 7.

> A travelling salesman only eats ramen and fries. Each pack of ramen contains 400 calories, 20 grams of protein, and 100 mg of sodium. Each pack of fries contains 300 calories, 10 grams of protein, and 75 mg of sodium. Since fries are easier to eat while driving, at most 30% of his meals can be ramen. The salesman wants to ensure he eats at least 3000 calories and 80 grams of protein. How many of each should he eat to minimize his sodium intake?

Reference:
```
min 100*[ramen] + 75*[fries]
  c0_ratio: 0.7*[ramen] - 0.3*[fries] <= 0
  c1_linear: 400*[ramen] + 300*[fries] >= 3000
  c2_linear: 20*[ramen] + 10*[fries] >= 80
  ramen: integer, in [0, inf]
  fries: integer, in [0, inf]
```

To grade:
```
min 100*[ramen packs] + 75*[fries packs]
  calories: 400*[ramen packs] + 300*[fries packs] >= 3000
  protein: 20*[ramen packs] + 10*[fries packs] >= 80
  ramen share of meals: 0.7*[ramen packs] - 0.3*[fries packs] <= 0
  ramen packs: integer, in [0, inf]
  fries packs: integer, in [0, inf]
```

## 8.

> A doctor's office takes the  temperature of patients one by one either by using an electronic or regular thermometer. The electronic thermometer takes 3 minutes to make a reading while the regular thermometer takes 2 minutes to make a reading. Since the electronic thermometer is more accurate, at least twice as many patients should have their temperature checked by the electronic thermometer than the regular thermometer. Since the electronic thermometer has a cooldown time, at least 50 patients should have their temperature checked by a regular thermometer. If the office is open for 15000 minutes, maximize the number of patients whose temperature can be taken?

Reference:
```
max 1*[electronic] + 1*[regular thermometer]
  c0_xby: 1*[electronic] - 2*[regular thermometer] >= 0
  c1_lowerbound: 1*[regular thermometer] >= 50
  c2_linear: 3*[electronic] + 2*[regular thermometer] <= 15000
  electronic: integer, in [0, inf]
  regular thermometer: integer, in [0, inf]
```

To grade:
```
max 1*[electronic thermometer readings] + 1*[regular thermometer readings]
  office_time: 3*[electronic thermometer readings] + 2*[regular thermometer readings] <= 15000
  electronic_at_least_twice_regular: 1*[electronic thermometer readings] - 2*[regular thermometer readings] >= 0
  regular_at_least_50: 1*[regular thermometer readings] >= 50
  electronic thermometer readings: integer, in [0, inf]
  regular thermometer readings: integer, in [0, inf]
```

## 9.

> A theme park transports its visitors around the park either by scooter or rickshaw. A scooter can carry 2 people while a rickshaw can carry 3 people. To avoid excessive pollution, at most 40% of the vehicles used can be rickshaws. If the park needs to transport at least 300 visitors, minimize the total number of scooters used.

Reference:
```
min 1*[scooter]
  c0_ratio: -0.4*[scooter] + 0.6*[rickshaw] <= 0
  c1_linear: 2*[scooter] + 3*[rickshaw] >= 300
  scooter: integer, in [0, inf]
  rickshaw: integer, in [0, inf]
```

To grade:
```
min 1*[scooters]
  visitor_capacity: 2*[scooters] + 3*[rickshaws] >= 300
  rickshaw_share_limit: 0.6*[rickshaws] - 0.4*[scooters] <= 0
  scooters: integer, in [0, inf]
  rickshaws: integer, in [0, inf]
```

## 10.

> A farmer has 140 hectares available to grow tomatoes and potatoes. She prefers to plant more tomatoes than potatoes, but the soil and weather conditions allow her to grow at most twice the amount of tomatoes to that of potatoes. In addition, she must grow at least 20 hectares of tomatoes and at least 30 hectares of potatoes to meet community demands. If the profit per hectare of tomatoes is $350 and the profit per hectare of potatoes is $600, how many hectares of each crop should she plant to maximize profit? What is this profit?

Reference:
```
max 350*[tomatoes] + 600*[potatoes]
  c0_sum: 1*[tomatoes] + 1*[potatoes] <= 140
  c1_xby: 1*[tomatoes] - 2*[potatoes] <= 0
  c2_lowerbound: 1*[tomatoes] >= 20
  c3_lowerbound: 1*[potatoes] >= 30
  tomatoes: integer, in [0, inf]
  potatoes: integer, in [0, inf]
```

To grade:
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

## 11.

> A university research lab can make two types of diabetes medicine, medicine A and medicine B. Per dose, medicine A takes 30 units of imported material and 50 units of mRNA to make. Per dose, medicine B takes 40 units of imported material and 30 units of mRNA to take. The lab has available at most 300 units of imported material and 400 units of mRNA. The lab can make at most 5 doses of medicine A and the number of doses of medicine B must be larger than the number of dosed of medicine A. If one dose of medicine A can treat 12 people and one dose of medicine B can treat 8 people, how many doses of each should be made to maximize the number of people that can be treated?

Reference:
```
max 12*[medicine A] + 8*[medicine B.]
  c0_linear: 30*[medicine A] + 40*[medicine B.] <= 300
  c1_linear: 50*[medicine A] + 30*[medicine B.] <= 400
  c2_upperbound: 1*[medicine A] <= 5
  c3_xy: 1*[medicine B.] - 1*[medicine A] >= 0
  medicine A: integer, in [0, inf]
  medicine B.: integer, in [0, inf]
```

To grade:
```
max 12*[medicine A doses] + 8*[medicine B doses]
  imported material: 30*[medicine A doses] + 40*[medicine B doses] <= 300
  mRNA: 50*[medicine A doses] + 30*[medicine B doses] <= 400
  max medicine A doses: 1*[medicine A doses] <= 5
  B exceeds A: 1*[medicine B doses] - 1*[medicine A doses] >= 1
  medicine A doses: integer, in [0, inf]
  medicine B doses: integer, in [0, inf]
```

## 12.

> A bakery makes almond and pistachio croissants. An almond croissant requires 5 units of butter and 8 units of flour. A pistachio croissant requires 3 units of butter and 6 units of flour. The bakery has available 600 units of butter and 800 units of flour. Since the almond croissant is more popular, at least 3 times as many almond croissants should be made as pistachio croissants. If making an almond croissant takes 12 minutes and making a pistachio croissant takes 10 minutes, how many of each should be made to minimize the total production time?

Reference:
```
min 12*[almond] + 10*[pistachio]
  c0_linear: 5*[almond] + 3*[pistachio] <= 600
  c1_linear: 8*[almond] + 6*[pistachio] <= 800
  c2_xby: 1*[almond] - 3*[pistachio] >= 0
  almond: integer, in [0, inf]
  pistachio: integer, in [0, inf]
```

To grade:
```
min 12*[almond croissants] + 10*[pistachio croissants]
  butter: 5*[almond croissants] + 3*[pistachio croissants] <= 600
  flour: 8*[almond croissants] + 6*[pistachio croissants] <= 800
  almond share: 1*[almond croissants] - 3*[pistachio croissants] >= 0
  almond croissants: integer, in [0, inf]
  pistachio croissants: integer, in [0, inf]
```

## 13.

> A mask making company ships masks to their retail stores using small boxes and large boxes. A small box holds 25 masks whereas a large box holds 45 masks. Since small boxes are easier to stack and will be used first to stock stores, there must be at least three times as many small boxes as large boxes. Additionally, at least 5 large boxes must be used. If at least 750 masks are required to be distributed, how many of each size of box should be used to minimize the total number of boxes needed?

Reference:
```
min 1*[large boxes] + 1*[small boxes]
  c0_linear: 25*[small boxes] + 45*[large boxes] >= 750
  c1_xby: 1*[small boxes] - 3*[large boxes] >= 0
  c2_lowerbound: 1*[large boxes] >= 5
  small boxes: integer, in [0, inf]
  large boxes: integer, in [0, inf]
```

To grade:
```
min 1*[small boxes] + 1*[large boxes]
  small boxes at least three times large boxes: 1*[small boxes] - 3*[large boxes] >= 0
  at least 5 large boxes: 1*[large boxes] >= 5
  at least 750 masks distributed: 25*[small boxes] + 45*[large boxes] >= 750
  small boxes: integer, in [0, inf]
  large boxes: integer, in [0, inf]
```

## 14.

> In a science club, there are two tables that can be set up to make slime. At table 1, 3 units of powder and 5 units of glue are used to make 4 units of slime. At table 2, 8 units of powder and 6 units of glue are used to make 5 units of slime. However, table 1 produces 2 units of mess while table 2 produces 4 units of mess. The science club has available 100 units of powder and 90 units of glue.  If at most 30 units of mess can be made, how many of each table should be set up to maximize the amount of slime produced?

Reference:
```
max 4*[table 1] + 5*[table 2]
  c0_linear: 3*[table 1] + 8*[table 2] <= 100
  c1_linear: 5*[table 1] + 6*[table 2] <= 90
  c2_linear: 2*[table 1] + 4*[table 2] <= 30
  table 1: integer, in [0, inf]
  table 2: integer, in [0, inf]
```

To grade:
```
max 4*[table 1 setups] + 5*[table 2 setups]
  powder: 3*[table 1 setups] + 8*[table 2 setups] <= 100
  glue: 5*[table 1 setups] + 6*[table 2 setups] <= 90
  mess: 2*[table 1 setups] + 4*[table 2 setups] <= 30
  table 1 setups: integer, in [0, inf]
  table 2 setups: integer, in [0, inf]
```

## 15.

> A farmer has 500 acres of land to grow turnips and pumpkins. Turnips require 50 minutes of watering and $80 worth of pesticide per acre. Pumpkins require 90 minutes of watering and $50 worth of pesticide per acre. The farmer has 40000 minutes available for watering and $34000 available to spend on pesticide. If the revenue per acre of turnips is $300 and the revenue per acre of pumpkins is $450, how many acres of each should he grow to maximize his revenue.

Reference:
```
max 300*[turnips] + 450*[pumpkins]
  c0_sum: 1*[turnips] + 1*[pumpkins] <= 500
  c1_linear: 50*[turnips] + 90*[pumpkins] <= 40000
  c2_linear: 80*[turnips] + 50*[pumpkins] <= 34000
  turnips: continuous, in [0, inf]
  pumpkins: continuous, in [0, inf]
```

To grade:
```
max 300*[turnip acres] + 450*[pumpkin acres]
  land: 1*[turnip acres] + 1*[pumpkin acres] <= 500
  watering: 50*[turnip acres] + 90*[pumpkin acres] <= 40000
  pesticide: 80*[turnip acres] + 50*[pumpkin acres] <= 34000
  turnip acres: continuous, in [0, inf]
  pumpkin acres: continuous, in [0, inf]
```

## 16.

> A tropical city full of islands sends mail either by submarine or by boat. A submarine can carry 100 pieces of mail per trip and uses 30 liters of gas. A boat can carry 80 pieces of mail per trip and uses 25 liters of gas. There can be at most 6 submarine trips and a minimum of 50% of the trips must be by boat. If the city needs to transport at least 1000 pieces of mail, how many of each transportation should they use to minimize the total amount of gas used?

Reference:
```
min 30*[submarine] + 25*[boat]
  c0_upperbound: 1*[submarine] <= 6
  c1_ratio: -0.5*[submarine] + 0.5*[boat] >= 0
  c2_linear: 100*[submarine] + 80*[boat] >= 1000
  submarine: integer, in [0, inf]
  boat: integer, in [0, inf]
```

To grade:
```
min 30*[submarine trips] + 25*[boat trips]
  mail capacity: 100*[submarine trips] + 80*[boat trips] >= 1000
  submarine trip limit: 1*[submarine trips] <= 6
  boat share of trips: 1*[boat trips] - 1*[submarine trips] >= 0
  submarine trips: integer, in [0, inf]
  boat trips: integer, in [0, inf]
```

## 17.

> A drug company is making pain killers and sleeping pills using two processes, process 1 and process 2. Process 1 produces 35 units of pain killers and 12 units of sleeping pills per hour. Process 2 produces 50 units of pain killers and 30 units of sleeping pills per hour. Process 1 requires 50 units of preliminary material while process 2 requires 60 units of preliminary material. The drug company has available 2000 units of preliminary material and must make at least 1200 units of pain killers and 1200 units of sleeping pills. How many of each process should be run to minimize the total time needed?

Reference:
```
min 1*[process 1] + 1*[process 2]
  c0_linear: 50*[process 1] + 60*[process 2] <= 2000
  c1_linear: 35*[process 1] + 50*[process 2] >= 1200
  c2_linear: 12*[process 1] + 30*[process 2] >= 1200
  process 1: integer, in [0, inf]
  process 2: integer, in [0, inf]
```

To grade:
```
min 1*[process 1 run hours] + 1*[process 2 run hours]
  pain killer requirement: 35*[process 1 run hours] + 50*[process 2 run hours] >= 1200
  sleeping pill requirement: 12*[process 1 run hours] + 30*[process 2 run hours] >= 1200
  preliminary material limit: 50*[process 1 run hours] + 60*[process 2 run hours] <= 2000
  process 1 run hours: continuous, in [0, inf]
  process 2 run hours: continuous, in [0, inf]
```

## 18.

> A clinic is conducting a throat or nasal swabs on each patient. A throat swab takes 5 minutes while a nasal swab takes 3 minutes. The clinic must administer at least 30 nasal swabs. Since the nasal swab is more uncomfortable, at least 4 times as many throat swabs must be done as nasal swabs. If the clinic is only operational for 20000 minutes, how many of each swab should be done to maximize the number of patients seen?

Reference:
```
max 1*[throat] + 1*[nasal swabs]
  c0_xby: 1*[throat] - 4*[nasal swabs] >= 0
  c1_lowerbound: 1*[nasal swabs] >= 30
  c2_linear: 5*[throat] + 3*[nasal swabs] <= 20000
  throat: integer, in [0, inf]
  nasal swabs: integer, in [0, inf]
```

To grade:
```
max 1*[throat swabs] + 1*[nasal swabs]
  operating time: 5*[throat swabs] + 3*[nasal swabs] <= 20000
  minimum nasal swabs: 1*[nasal swabs] >= 30
  throat to nasal ratio: 1*[throat swabs] - 4*[nasal swabs] >= 0
  throat swabs: integer, in [0, inf]
  nasal swabs: integer, in [0, inf]
```

## 19.

> A brewery can ferment their product into either wine or kombucha. Each unit of wine requires 3 units of fruit and 8 units of water. Each unit of kombucha requires 5 units of fruit and 7 units of tea. The company has available 7000 units of water and 9000 units of tea. Wine sells for more, therefore the number of wine must be larger than the number of kombucha. Additionally, at least 20% of their products made must be kombucha. How many of each should the brewery make to minimize the total units of fruit required?

Reference:
```
min 3*[wine] + 5*[kombucha]
  c0_linear: 8*[wine] <= 7000
  c1_linear: 7*[kombucha] <= 9000
  c2_xy: 1*[wine] - 1*[kombucha] >= 0
  c3_ratio: -0.2*[wine] + 0.8*[kombucha] >= 0
  wine: continuous, in [0, inf]
  kombucha: continuous, in [0, inf]
```

To grade:
```
min 3*[wine units] + 5*[kombucha units]
  water: 8*[wine units] <= 7000
  tea: 7*[kombucha units] <= 9000
  wine_more_than_kombucha: 1*[wine units] - 1*[kombucha units] >= 1
  kombucha_at_least_20_percent: -0.2*[wine units] + 0.8*[kombucha units] >= 0
  wine units: integer, in [0, inf]
  kombucha units: integer, in [0, inf]
```

## 20.

> A grape farmer transports his grapes in either small crates or large crates. A small crate can take 200 grapes while a large crate can take 500.  Because his customers prefer smaller crates, at least 3 times as many small crates must be used than large crates. The farmer has available at most 100 small crates and at most 50 large crates. In addition, his truck can take at most 60 crates total and he must use at least 10 large crates. How many of each crate should he use to maximize the total number of grapes he can transport?

Reference:
```
max 200*[small crates] + 500*[large crates]
  c0_xby: 1*[small crates] - 3*[large crates] >= 0
  c1_upperbound: 1*[small crates] <= 100
  c2_upperbound: 1*[large crates] <= 50
  c3_sum: 1*[small crates] + 1*[large crates] <= 60
  c4_lowerbound: 1*[large crates] >= 10
  small crates: integer, in [0, inf]
  large crates: integer, in [0, inf]
```

To grade:
```
max 200*[small crates] + 500*[large crates]
  small crates at least 3 times large crates: 1*[small crates] - 3*[large crates] >= 0
  total crates at most 60: 1*[small crates] + 1*[large crates] <= 60
  at least 10 large crates: 1*[large crates] >= 10
  small crates: integer, in [0, 100]
  large crates: integer, in [0, 50]
```

## 21.

> Platinum in combination with palladium has been used as a catalyst in cars and it changes carbon monoxide, which is toxic, into carbon dioxide. An automotive company is comparing two different catalysts, a palladium-heavy catalyst and a platinum-heavy catalyst. The process with a palladium-heavy catalyst requires 15 units of platinum and 25 units of palladium and can perform the conversion to carbon dioxide at a rate of 5 units per second. A platinum-heavy catalyst requires 20 units of platinum and 14 units of palladium and converts to carbon dioxide at a rate of 4 units per second. There are 450 units of platinum and 390 units of palladium available. How many of each catalyst should be used to maximize the amount converted into carbon dioxide?

Reference:
```
max 5*[palladium-heavy catalyst] + 4*[platinum-heavy catalyst]
  c0_linear: 14*[platinum-heavy catalyst] + 25*[palladium-heavy catalyst] <= 390
  c1_linear: 15*[palladium-heavy catalyst] + 20*[platinum-heavy catalyst] <= 450
  palladium-heavy catalyst: integer, in [0, inf]
  platinum-heavy catalyst: integer, in [0, inf]
```

To grade:
```
max 5*[palladium-heavy catalyst] + 4*[platinum-heavy catalyst]
  platinum available: 15*[palladium-heavy catalyst] + 20*[platinum-heavy catalyst] <= 450
  palladium available: 25*[palladium-heavy catalyst] + 14*[platinum-heavy catalyst] <= 390
  palladium-heavy catalyst: continuous, in [0, inf]
  platinum-heavy catalyst: continuous, in [0, inf]
```

## 22.

> A music company produces two types of digital keyboards, one is full-weighted and another is semi-weighted. Both keyboards are sold for $2800 and $2400 respectively. There are about 3500 oscillator chips available every day from which the full-weighted version requires 20 chips while the semi-weighted version requires 15 chips. The company has a total of 6 working hours a day. Both of these keyboards require a production time of 1.2 hours. What should be the manufacturing quantity for each of the keyboards to maximize the total revenue?

Reference:
```
max 2800*[full-weighted] + 2400*[semi-weighted]
  c0_linear: 20*[full-weighted] + 15*[semi-weighted] <= 3500
  c1_linear: 1.2*[full-weighted] + 1.2*[semi-weighted] >= 6
  full-weighted: integer, in [0, inf]
  semi-weighted: integer, in [0, inf]
```

To grade:
```
max 2800*[full-weighted keyboards] + 2400*[semi-weighted keyboards]
  oscillator chips: 20*[full-weighted keyboards] + 15*[semi-weighted keyboards] <= 3500
  production hours: 1.2*[full-weighted keyboards] + 1.2*[semi-weighted keyboards] <= 6
  full-weighted keyboards: integer, in [0, inf]
  semi-weighted keyboards: integer, in [0, inf]
```

## 23.

> A food delivery person can either have shifts on bikes or scooters. A shift on a bike can deliver 10 orders, takes 5 units of energy, and brings in $50 on tips because it is faster. A shift on a scooter can deliver 7 orders, takes 6 units of energy, and brings in $43 on tips.  The delivery person has available 40 shifts a month and has 230 units of energy and must bring at least 320 orders. He must have at least 5 shifts on a scooter because bikes are harder to get. How many shifts on each type of transportation should the delivery person schedule to maximize tips received?

Reference:
```
max 50*[bikes] + 43*[scooters]
  c0_sum: 1*[bikes] + 1*[scooters] <= 40
  c1_linear: 5*[bikes] + 6*[scooters] <= 230
  c2_linear: 7*[scooters] + 10*[bikes] >= 320
  c3_lowerbound: 1*[scooters] >= 5
  bikes: integer, in [0, inf]
  scooters: integer, in [0, inf]
```

To grade:
```
max 50*[bike shifts] + 43*[scooter shifts]
  shift_limit: 1*[bike shifts] + 1*[scooter shifts] <= 40
  energy: 5*[bike shifts] + 6*[scooter shifts] <= 230
  orders: 10*[bike shifts] + 7*[scooter shifts] >= 320
  scooter_minimum: 1*[scooter shifts] >= 5
  bike shifts: integer, in [0, inf]
  scooter shifts: integer, in [0, inf]
```

## 24.

> A soda company sends bottles of their soda to stores around the city in old and new vans. An old van can take 100 soda bottles while a new van can take 80 soda bottles. An old van produces 50 units of pollution while a new van only produces 30 units of pollution. The company needs to send at least 5000 bottles. In addition, at most 30 new vans can be used. How many of each van should be used to minimize the total amount of pollution produced?

Reference:
```
min 50*[old] + 30*[new vans]
  c0_linear: 100*[old] + 80*[new vans] >= 5000
  c1_upperbound: 1*[new vans] <= 30
  old: integer, in [0, inf]
  new vans: integer, in [0, inf]
```

To grade:
```
min 50*[old vans] + 30*[new vans]
  bottles: 100*[old vans] + 80*[new vans] >= 5000
  new van limit: 1*[new vans] <= 30
  old vans: integer, in [0, inf]
  new vans: integer, in [0, inf]
```

## 25.

> A electronics store sells premium desktops with more power as well as regular desktops for everyday use. Each premium desktop costs the store $2000 to make and yields a profit of $500. Each regular desktop costs the store $1000 to make and yields a profit of $300. The store sells at most 200 desktops each month and wants to spend at most $300000 on making the desktops. How many of each should be made and sold to maximize profit?

Reference:
```
max 500*[premium desktops] + 300*[regular desktops]
  c0_sum: 1*[premium desktops] + 1*[regular desktops] <= 200
  c1_linear: 2000*[premium desktops] + 1000*[regular desktops] <= 300000
  premium desktops: integer, in [0, inf]
  regular desktops: integer, in [0, inf]
```

To grade:
```
max 500*[premium desktops] + 300*[regular desktops]
  sales limit: 1*[premium desktops] + 1*[regular desktops] <= 200
  production budget: 2000*[premium desktops] + 1000*[regular desktops] <= 300000
  premium desktops: integer, in [0, inf]
  regular desktops: integer, in [0, inf]
```

## 26.

> A dim sum restaurant can deliver their food by cart or by hand. Servers can deliver by cart and have 70 customer interactions and will have to refill food five times an hour. They can also deliver more food by hand, due to the increased mobility, and have 85 customer interactions while refilling food twenty times an hour. However, the customers get more options when delivering by cart, therefore at least 70% of delivery shifts must be by cart. There must be at least 3 servers delivering by hand for their direct customer service. If the restaurant wants to have 4000 customer interactions per hour, how many of each form of delivery should the dim sum restaurant schedule to minimize the total number of refills per hour?

Reference:
```
min 5*[cart] + 20*[hand]
  c0_ratio: 0.3*[cart] - 0.7*[hand] >= 0
  c1_lowerbound: 1*[hand] >= 3
  c2_linear: 70*[cart] + 85*[hand] <= 4000
  cart: integer, in [0, inf]
  hand: integer, in [0, inf]
```

To grade:
```
min 5*[cart_servers] + 20*[hand_servers]
  customer_interactions: 70*[cart_servers] + 85*[hand_servers] == 4000
  cart_share_at_least_70_percent: 0.3*[cart_servers] - 0.7*[hand_servers] >= 0
  min_hand_servers: 1*[hand_servers] >= 3
  cart_servers: integer, in [0, inf]
  hand_servers: integer, in [0, inf]
```

## 27.

> Ben is growing apples and pears on his orchard. He has 50 acres available on which he must grow a minimum of 5 acres of apples and a minimum of 10 acres of pears to meet demands. The profit per apple is $2 and the profit per pear is $4. He prefers to grow more pears than apples but limitations in his workforce allow him to grow at most twice the amount of pears as apples. How many of each fruit should Ben grow in order to maximize his profit? What is that profit?

Reference:
```
max 2*[apples] + 4*[pears]
  c0_sum: 1*[apples] + 1*[pears] <= 50
  c1_lowerbound: 1*[apples] >= 5
  c2_lowerbound: 1*[pears] >= 10
  c3_xby: 1*[pears] - 2*[apples] <= 0
  apples: continuous, in [0, inf]
  pears: continuous, in [0, inf]
```

To grade:
```
max 2*[acres of apples] + 4*[acres of pears]
  land: 1*[acres of apples] + 1*[acres of pears] <= 50
  minimum apple acres: 1*[acres of apples] >= 5
  minimum pear acres: 1*[acres of pears] >= 10
  workforce limit on pears: 1*[acres of pears] - 2*[acres of apples] <= 0
  prefers more pears than apples: 1*[acres of pears] - 1*[acres of apples] >= 0
  acres of apples: continuous, in [0, inf]
  acres of pears: continuous, in [0, inf]
```

## 28.

> A tea estate has available 500 acres of land and they need to pick the tea leaves either using a traditional machine or modern machine. For each acre of land, the traditional machine can pick 30 kg of tea leaves, creates 10 kg of waste, and requires 20 liters of fuel. For each acre of land, the modern machine can pick 40 kg of tea leaves, creates 15 kg of waste, and requires 15 liters of fuel. The estate has available 9000 liters of fuel can handle at most 6000 kg of waste. For how many acres should each machine be used to maximize the amount of tea leaves that can be picked?

Reference:
```
max 30*[traditional machine] + 40*[modern machine]
  c0_linear: 20*[traditional machine] + 15*[modern machine] <= 9000
  c1_linear: 10*[traditional machine] + 15*[modern machine] <= 6000
  traditional machine: continuous, in [0, inf]
  modern machine: continuous, in [0, inf]
```

To grade:
```
max 30*[traditional machine acres] + 40*[modern machine acres]
  land: 1*[traditional machine acres] + 1*[modern machine acres] <= 500
  fuel: 20*[traditional machine acres] + 15*[modern machine acres] <= 9000
  waste: 10*[traditional machine acres] + 15*[modern machine acres] <= 6000
  traditional machine acres: continuous, in [0, inf]
  modern machine acres: continuous, in [0, inf]
```

## 29.

> A crepe store sells chocolate and peanut butter crepes. A chocolate crepe requires 3 units of chocolate spread and 6 units of crepe mix. A peanut butter crepe requires 4 units of peanut butter spread and 7 units of crepe mix. Recently, the peanut butter crepe has been more popular and therefore the number of peanut butter crepes made must exceed the number of chocolate crepes made. However at least 25% of the crepes made should be chocolate. The store has available 400 units of chocolate spread and 450 units of peanut butter spread. How many of each should the store make to minimize the total amount of crepe mix needed?

Reference:
```
min 6*[chocolate crepe] + 7*[peanut butter crepes]
  c0_xy: 1*[peanut butter crepes] - 1*[chocolate crepe] >= 0
  c1_ratio: -0.25*[peanut butter crepes] + 0.75*[chocolate crepe] >= 0
  c2_linear: 3*[chocolate crepe] <= 400
  c3_linear: 4*[peanut butter crepes] <= 450
  peanut butter crepes: continuous, in [0, inf]
  chocolate crepe: continuous, in [0, inf]
```

To grade:
```
min 6*[chocolate crepes made] + 7*[peanut butter crepes made]
  chocolate spread: 3*[chocolate crepes made] <= 400
  peanut butter spread: 4*[peanut butter crepes made] <= 450
  peanut butter exceeds chocolate: 1*[peanut butter crepes made] - 1*[chocolate crepes made] >= 1
  chocolate at least 25 percent of crepes: 3*[chocolate crepes made] - 1*[peanut butter crepes made] >= 0
  chocolate crepes made: integer, in [0, inf]
  peanut butter crepes made: integer, in [0, inf]
```

## 30.

> An incandescent bulb manufacturing company uses either an argon gas approach or halogen gas approach to fill their light bulbs. The argon gas approach uses 10 units of gas and 12 units of glass to make 2 light bulbs. The halogen gas approach uses 12 units of gas and 8 units of glass to make 3 light bulbs. Additionally, the argon gas approach generates 3 units of heat while the halogen gas approach creates 4 units of heat. The manufacturing company has available 150 units of gas and 120 units of glass. If at most 28 units of heat can be generated during the manufacturing process, how many of each method should be used to maximize the number of light bulbs produced?

Reference:
```
max 2*[argon gas approach] + 3*[halogen gas approach]
  c0_linear: 10*[argon gas approach] + 12*[halogen gas approach] <= 150
  c1_linear: 12*[argon gas approach] + 8*[halogen gas approach] <= 120
  c2_linear: 3*[argon gas approach] + 4*[halogen gas approach] <= 28
  argon gas approach: integer, in [0, inf]
  halogen gas approach: integer, in [0, inf]
```

To grade:
```
max 2*[argon gas approach runs] + 3*[halogen gas approach runs]
  gas_available: 10*[argon gas approach runs] + 12*[halogen gas approach runs] <= 150
  glass_available: 12*[argon gas approach runs] + 8*[halogen gas approach runs] <= 120
  heat_limit: 3*[argon gas approach runs] + 4*[halogen gas approach runs] <= 28
  argon gas approach runs: integer, in [0, inf]
  halogen gas approach runs: integer, in [0, inf]
```

## 31.

> A concert organizer has to transport equipment using carts or trolleys. Carts can transport 5 kg/min of equipment and requires 2 workers. Trolleys can transport 7 kg/min of equipment and requires 4 workers. There must be at least 12 trolleys to be used. Additionally, only a maximum of 40% of the transportation can be using trolleys. The organizer has to deliver at a rate of 100 kg/min of equipment. How many of each transportation method should be used to minimize the total number of workers?

Reference:
```
min 2*[carts] + 4*[trolleys]
  c0_linear: 5*[carts] + 7*[trolleys] >= 100
  c1_lowerbound: 1*[trolleys] >= 12
  c2_ratio: -0.4*[carts] + 0.6*[trolleys] <= 0
  carts: integer, in [0, inf]
  trolleys: integer, in [0, inf]
```

To grade:
```
min 2*[carts] + 4*[trolleys]
  delivery_rate: 5*[carts] + 7*[trolleys] >= 100
  min_trolleys: 1*[trolleys] >= 12
  trolley_share_max_40_percent: 4.2*[trolleys] - 2*[carts] <= 0
  carts: integer, in [0, inf]
  trolleys: integer, in [0, inf]
```

## 32.

> An Indian restaurant makes goat and chicken curry. Each bowl of goat curry requires 3 units of goat meat and 6 units of the curry base. Each bowl of chicken curry requires 5 units of chicken meat and 5 units of the curry base. The restaurant has available 1500 units of goat meat and 2000 units of chicken meat. At least 25% of the bowls made must be chicken curry. Since goat curry is more popular, the number of goat curry bowls must be larger than the number of chicken curry bowls. How many of each type of curry bowl should be made to minimize the total amount of curry base used?

Reference:
```
min 6*[goat] + 5*[chicken]
  c0_linear: 3*[goat] <= 1500
  c1_linear: 5*[chicken] <= 2000
  c2_ratio: -0.25*[goat] + 0.75*[chicken] >= 0
  c3_xy: 1*[goat] - 1*[chicken] >= 0
  goat: continuous, in [0, inf]
  chicken: continuous, in [0, inf]
```

To grade:
```
min 6*[goat curry bowls] + 5*[chicken curry bowls]
  goat meat: 3*[goat curry bowls] <= 1500
  chicken meat: 5*[chicken curry bowls] <= 2000
  chicken share: -0.25*[goat curry bowls] + 0.75*[chicken curry bowls] >= 0
  goat popularity: 1*[goat curry bowls] - 1*[chicken curry bowls] >= 1
  goat curry bowls: integer, in [0, inf]
  chicken curry bowls: integer, in [0, inf]
```

## 33.

> A grilled cheese shop sells a light and heavy grilled cheese sandwich. A light grilled cheese sandwich requires 2 slices of bread and 3 slices of cheese. A heavy grilled cheese sandwich requires 3 slices of bread and 5 slices of cheese. Since most people who come to the store love grilled cheese, the store must make at least 3 times as many heavy grilled cheese sandwiches as light grilled cheese sandwiches. The store has available 300 slices of bread and 500 slices of cheese. If a light grilled cheese sandwich takes 10 minutes to make and a heavy grilled cheese sandwich takes 15 minutes to make, how many of each should they make to minimize the total production time?

Reference:
```
min 10*[light] + 15*[heavy]
  c0_xby: 1*[heavy] - 3*[light] >= 0
  c1_linear: 2*[light] + 3*[heavy] <= 300
  c2_linear: 3*[light] + 5*[heavy] <= 500
  light: integer, in [0, inf]
  heavy: integer, in [0, inf]
```

To grade:
```
min 10*[light_sandwiches] + 15*[heavy_sandwiches]
  bread: 2*[light_sandwiches] + 3*[heavy_sandwiches] <= 300
  cheese: 3*[light_sandwiches] + 5*[heavy_sandwiches] <= 500
  heavy_at_least_3x_light: 1*[heavy_sandwiches] - 3*[light_sandwiches] >= 0
  light_sandwiches: integer, in [0, inf]
  heavy_sandwiches: integer, in [0, inf]
```

## 34.

> A bubble tea shop sells mango and lychee bubble tea. Each mango bubble tea requires 4 units of mango juice and 8 units of tea. Each lychee bubble tea requires 6 units of lychee juice and 6 units of tea. The shop has available 2000 units of mango juice and 3000 units of lychee juice. At least 40% of the bubble teas made must be lychee flavored. However, mango bubble tea sells better and thus the number of mango bubble teas made must be large than the number of lychee bubble teas made. How many of each bubble tea flavor should be made to minimize the total amount of tea needed?

Reference:
```
min 8*[mango bubble tea] + 6*[lychee bubble tea]
  c0_linear: 4*[mango bubble tea] <= 2000
  c1_linear: 6*[lychee bubble tea] <= 3000
  c2_ratio: 0.6*[lychee bubble tea] - 0.4*[mango bubble tea] >= 0
  c3_xy: 1*[mango bubble tea] - 1*[lychee bubble tea] >= 0
  lychee bubble tea: continuous, in [0, inf]
  mango bubble tea: continuous, in [0, inf]
```

To grade:
```
min 8*[mango bubble teas made] + 6*[lychee bubble teas made]
  mango juice available: 4*[mango bubble teas made] <= 2000
  lychee juice available: 6*[lychee bubble teas made] >= 0
  lychee at least 40 percent of total: -0.4*[mango bubble teas made] + 0.6*[lychee bubble teas made] >= 0
  mango more than lychee: 1*[mango bubble teas made] - 1*[lychee bubble teas made] >= 1
  mango bubble teas made: integer, in [0, inf]
  lychee bubble teas made: integer, in [0, inf]
```

## 35.

> A man on a strict diet only drinks meal replacement drinks from two brands, alpha and omega. The alpha brand drink contains 30 grams of protein, 20 grams of sugar, and 350 calories per bottle. The omega brand drink contains 20 grams of protein, 15 grams of sugar, and 300 calories per bottle. The man wants to get at least 100 grams of protein and 2000 calories. In addition, because the omega brand drink contains tiny amounts of caffeine, at most 35% of the drink should be omega brand. How many bottles of each should he drink to minimize his sugar intake?

Reference:
```
min 20*[alpha] + 15*[omega]
  c0_linear: 30*[alpha] + 20*[omega] >= 100
  c1_linear: 350*[alpha] + 300*[omega] >= 2000
  c2_ratio: -0.35*[alpha] + 0.65*[omega] <= 0
  alpha: integer, in [0, inf]
  omega: integer, in [0, inf]
```

To grade:
```
min 20*[alpha brand bottles] + 15*[omega brand bottles]
  protein: 30*[alpha brand bottles] + 20*[omega brand bottles] >= 100
  calories: 350*[alpha brand bottles] + 300*[omega brand bottles] >= 2000
  omega caffeine share limit: -0.35*[alpha brand bottles] + 0.65*[omega brand bottles] <= 0
  alpha brand bottles: integer, in [0, inf]
  omega brand bottles: integer, in [0, inf]
```

## 36.

> In order to make carbon dioxide, wood is burned using two processes, with a catalyst and without a catalyst. The process with a catalyst requires 10 units of wood and 20 units of oxygen to make 15 units of carbon dioxide. The process without a catalyst requires 15 units of wood and 12 units of oxygen to make 18 units of carbon dioxide. There are 300 units of wood and 300 units of oxygen available. How many of each process should be used to maximize the amount of carbon dioxide produced?

Reference:
```
max 15*[with a catalyst] + 18*[without a catalyst]
  c0_linear: 10*[with a catalyst] + 15*[without a catalyst] <= 300
  c1_linear: 20*[with a catalyst] + 12*[without a catalyst] <= 300
  with a catalyst: integer, in [0, inf]
  without a catalyst: integer, in [0, inf]
```

To grade:
```
max 15*[catalyst process runs] + 18*[non-catalyst process runs]
  wood: 10*[catalyst process runs] + 15*[non-catalyst process runs] <= 300
  oxygen: 20*[catalyst process runs] + 12*[non-catalyst process runs] <= 300
  catalyst process runs: continuous, in [0, inf]
  non-catalyst process runs: continuous, in [0, inf]
```

## 37.

> A company is deciding where to promote their product. Some options include z-tube, soorchle engine, and wassa advertisements. The cost for each option and the number of viewers they each attract is given. On z-tube, each ad costs $1000 and attracts 400,000 viewers. On soorchle, each ad costs $200 and attracts 5,000 viewers. On wassa, each ad costs $100 and attracts 3,000 viewers. Soorchle limits the number of advertisements from a single company to fifteen. Moreover, in order to balance the advertising among the three types of media, at most a third of the total number of advertisements should occur on wassa. And at least 5% should occur on z-tube. The weekly advertising budget is $10000. How many advertisements should be run in each of the three types of media to maximize the total audience?

Reference:
```
max 400000*[z-tube] + 5000*[soorchle] + 3000*[wassa]
  c0_upperbound: 1*[soorchle] <= 15
  c1_ratio: -0.333333*[z-tube] - 0.333333*[soorchle] + 0.666667*[wassa] <= 0
  c2_ratio: 0.95*[z-tube] - 0.05*[soorchle] - 0.05*[wassa] >= 0
  c3_linear: 1000*[z-tube] + 200*[soorchle] + 100*[wassa] <= 10000
  z-tube: integer, in [0, inf]
  soorchle: integer, in [0, inf]
  wassa: integer, in [0, inf]
```

To grade:
```
max 400000*[z-tube advertisements] + 5000*[soorchle advertisements] + 3000*[wassa advertisements]
  weekly budget: 1000*[z-tube advertisements] + 200*[soorchle advertisements] + 100*[wassa advertisements] <= 10000
  soorchle limit: 1*[soorchle advertisements] <= 15
  wassa at most one third of total: 2*[wassa advertisements] - 1*[z-tube advertisements] - 1*[soorchle advertisements] <= 0
  z-tube at least 5% of total: 0.95*[z-tube advertisements] - 0.05*[soorchle advertisements] - 0.05*[wassa advertisements] >= 0
  z-tube advertisements: integer, in [0, inf]
  soorchle advertisements: integer, in [0, inf]
  wassa advertisements: integer, in [0, inf]
```

## 38.

> A neighbourhood pizza restaurant has opened and sells pizzas in two sizes; large pizza and medium pizza. Large pizzas require 12 units of dough, and 5 units of toppings. Medium pizzas require 8 units of dough, and 4 units of toppings. While large pizzas take 12 minutes to bake, medium pizzas require 8 minutes to bake. The neighbourhood pizza restaurant must use at least 10000 units of dough and 4400 units of toppings. Medium pizzas are popular due to a promotion, therefore, at least 200 medium pizzas must be made. There are regulars that prefer large pizzas and at least two times as many large pizzas should be made than medium pizzas. How many of each size of pizzas should the neighbourhood pizza restaurant make to reduce time spent baking?

Reference:
```
min 8*[medium pizza] + 12*[large pizza]
  c0_linear: 12*[large pizza] + 8*[medium pizza] >= 10000
  c1_linear: 5*[large pizza] + 4*[medium pizza] >= 4400
  c2_lowerbound: 1*[medium pizza] >= 200
  c3_xby: 1*[large pizza] - 2*[medium pizza] >= 0
  large pizza: integer, in [0, inf]
  medium pizza: integer, in [0, inf]
```

To grade:
```
min 12*[large pizzas] + 8*[medium pizzas]
  dough: 12*[large pizzas] + 8*[medium pizzas] >= 10000
  toppings: 5*[large pizzas] + 4*[medium pizzas] >= 4400
  medium promotion: 1*[medium pizzas] >= 200
  large preference: 1*[large pizzas] - 2*[medium pizzas] >= 0
  large pizzas: integer, in [0, inf]
  medium pizzas: integer, in [0, inf]
```

## 39.

> A car manufacturer makes two types of car oils: Oil Max and Oil Max Pro. A container of Oil Max contains 46 grams of substance A, 43 grams of substance B and 56 grams of substance C. A container of Oil Max Pro contains 13 grams of substance A, 4 grams of substance B and 45 grams of substance C. The car manufacturer has 1345 grams of substance A, 346 grams of substance B, 1643 grams of substance C. In addition, the profit per container of Oil Max is $10 and the profit per container of Oil Max Pro is $15. How many containers of each of oil should the car manufacturer make to maximize profit?

Reference:
```
max 10*[Oil Max] + 15*[Oil Max Pro]
  c0_linear: 46*[Oil Max] + 13*[Oil Max Pro] <= 1345
  c1_linear: 43*[Oil Max] + 4*[Oil Max Pro] <= 346
  c2_linear: 56*[Oil Max] + 45*[Oil Max Pro] <= 1643
  Oil Max: integer, in [0, inf]
  Oil Max Pro: integer, in [0, inf]
```

To grade:
```
max 10*[Oil Max containers] + 15*[Oil Max Pro containers]
  substance A: 46*[Oil Max containers] + 13*[Oil Max Pro containers] <= 1345
  substance B: 43*[Oil Max containers] + 4*[Oil Max Pro containers] <= 346
  substance C: 56*[Oil Max containers] + 45*[Oil Max Pro containers] <= 1643
  Oil Max containers: integer, in [0, inf]
  Oil Max Pro containers: integer, in [0, inf]
```

## 40.

> A biotechnology company has 35,000 units of antibiotics available which is important to the process of making a first-dose and second-dose of vaccines. The first-dose vaccine requires 30 units of antibiotics and 20 mg of gelatine whereas the second-dose vaccine requires 65 units of antibiotics and 60 mg of gelatine. Since the first-dose vaccine is required before the second-dose vaccine, there must be more first-dose than second-dose vaccines manufactured. However, at least 40 second-dose vaccines must be made. How many of each vaccine should be made to minimize the amount of gelatine used?

Reference:
```
min 20*[first-dose] + 60*[second-dose]
  c0_linear: 30*[first-dose] + 65*[second-dose] <= 35000
  c1_xy: 1*[first-dose] - 1*[second-dose] >= 0
  c2_lowerbound: 1*[second-dose] >= 40
  first-dose: integer, in [0, inf]
  second-dose: integer, in [0, inf]
```

To grade:
```
min 20*[first-dose vaccines] + 60*[second-dose vaccines]
  antibiotics available: 30*[first-dose vaccines] + 65*[second-dose vaccines] <= 35000
  more first-dose than second-dose: 1*[first-dose vaccines] - 1*[second-dose vaccines] >= 1
  at least 40 second-dose vaccines: 1*[second-dose vaccines] >= 40
  first-dose vaccines: integer, in [0, inf]
  second-dose vaccines: integer, in [0, inf]
```
