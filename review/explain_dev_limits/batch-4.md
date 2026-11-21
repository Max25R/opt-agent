# Explanation labels, batch 4 of 4

Label every numbered number `correct` or `wrong` in `labels-4.csv`, and every explanation's false claim `yes` or `no` in `claims-4.csv`, by the rules of docs/analysis/explanation_checker.md. This sheet doesn't show the checker's flags, on purpose.

## 1962552394

**Problem.** A company wants to advertise its product. They want to use three types of ads: magazine ads, flyers, and billboard ads. The cost for each option along with the expected viewership is given. A magazine ad costs $1000 and attracts 10000 viewers. A flyer costs $200 and attracts 5000 viewers. A billboard ad costs $7000 and attracts 25000 viewers. To avoid annoying customers, the city has limited the number of flyers from a single company to 8. In addition, at most a third of the total number of ads should be billboard ads and at least 15% of the ads should be magazine ads. If the weekly budget is $50000, how many ads of each type should be run in order to maximize the number of viewers?

**Model.**
```
max 10000*[magazine ads] + 5000*[flyers] + 25000*[billboard ads]
  budget: 1000*[magazine ads] + 200*[flyers] + 7000*[billboard ads] <= 50000
  flyer_limit: 1*[flyers] <= 8
  billboard_share: 2*[billboard ads] - 1*[magazine ads] - 1*[flyers] <= 0
  magazine_share: 0.85*[magazine ads] - 0.15*[flyers] - 0.15*[billboard ads] >= 0
  magazine ads: integer, in [0, inf]
  flyers: integer, in [0, inf]
  billboard ads: integer, in [0, inf]
```

**Facts.** objective 520000; values magazine ads = 48, flyers = 8, billboard ads = 0; slack budget: 400, flyer_limit: 0, billboard_share: 56, magazine_share: 39.6; binding: flyer_limit; shadow prices none (a MIP)

**Explanation.**

Run 48 magazine ads, 8 flyers, and no billboard ads, which reaches an estimated 520,000 viewers. The city's cap of 8 flyers is the main limit: it is fully used, and allowing more flyers would improve the result. The $50,000 budget also constrains the plan, since removing it would improve the outcome, but the $400 left over and the whole-ad purchases mean one more dollar of budget would not help. The billboard-share and magazine-share rules do not limit the result, because removing either would not improve it.

**Numbers.**

1. `48` ...[48] magazine ads, 8 flyers, and no billboard...
2. `8` ...48 magazine ads, [8] flyers, and no billboard ads, which reaches...
3. `520,000` ...billboard ads, which reaches an estimated [520,000] viewers. The city's cap of 8 flyers is the...
4. `8` ...520,000 viewers. The city's cap of [8] flyers is the main limit: it is fully used,...
5. `$50,000` ...more flyers would improve the result. The [$50,000] budget also constrains the plan, since...
6. `$400` ...it would improve the outcome, but the [$400] left over and the whole-ad purchases mean...

## 368302984

**Problem.** A kitchen prepares diced onions and carrots each involving both peeling and cutting. To prepare a container of diced onions takes 10 minutes of peeling and 20 minutes of cutting. To prepare a container of diced carrots takes 20 minutes of peeling and 15 minutes of cutting. There are 2000 minutes of peeling time and 2500 minutes of cutting time available. If the profit per container of diced onions is $8 and the profit per container of diced carrots is $6, how many containers of each should be prepared to maximize profit?

**Model.**
```
max 8*[containers of diced onions] + 6*[containers of diced carrots]
  peeling time: 10*[containers of diced onions] + 20*[containers of diced carrots] <= 2000
  cutting time: 20*[containers of diced onions] + 15*[containers of diced carrots] <= 2500
  containers of diced onions: integer, in [0, inf]
  containers of diced carrots: integer, in [0, inf]
```

**Facts.** objective 1000; values containers of diced onions = 80, containers of diced carrots = 60; slack peeling time: 0, cutting time: 0; binding: peeling time, cutting time; shadow prices none (a MIP)

**Explanation.**

Prepare **80 containers of diced onions** and **60 containers of diced carrots**. This yields the maximum profit of **$1000**. Both peeling time (2000 minutes) and cutting time (2500 minutes) are fully used. Cutting time is the constraint that limits the result: removing it would let the solver find a better plan, even though adding more cutting minutes would not improve profit. Peeling time does not limit the result, since removing it would not improve the plan.

**Numbers.**

1. `80` ...**[80] containers of diced onions** and **60...
2. `60` ...**80 containers of diced onions** and **[60] containers of diced carrots**. This yields...
3. `$1000` ...This yields the maximum profit of **[$1000]**. Both peeling time (2000 minutes) and...
4. `2000` ...profit of **$1000**. Both peeling time ([2000] minutes) and cutting time (2500 minutes)...
5. `2500` ...time (2000 minutes) and cutting time ([2500] minutes) are fully used. Cutting time is...

## -551748874

**Problem.** David likes to mix his two post workout drinks: coconut water and blue energade. Coconut water costs $3 per bottle, contains 5 units of potassium, 3 units of magnesium, and 8 units of calcium. Blue energade costs $5 per bottle and contains 10 units of potassium, 4 units of magnesium, and 4 units of calcium. David likes to make sure he gets at least 15 units of potassium, 10 units of magnesium, and 20 units of calcium after each workout. How many bottles of each drink should he buy and mix in order to ensure a minimum cost? What is the minimum cost?

**Model.**
```
min 3*[coconut water bottles] + 5*[blue energade bottles]
  potassium: 5*[coconut water bottles] + 10*[blue energade bottles] >= 15
  magnesium: 3*[coconut water bottles] + 4*[blue energade bottles] >= 10
  calcium: 8*[coconut water bottles] + 4*[blue energade bottles] >= 20
  coconut water bottles: integer, in [0, inf]
  blue energade bottles: integer, in [0, inf]
```

**Facts.** objective 11; values coconut water bottles = 2, blue energade bottles = 1; slack potassium: 5, magnesium: 0, calcium: 0; binding: magnesium, calcium; shadow prices none (a MIP)

**Explanation.**

David should buy 2 bottles of coconut water and 1 bottle of blue energade, for a minimum cost of $11. This mix meets his magnesium and calcium needs exactly and leaves 5 units of potassium above his minimum. Magnesium is the constraint that limits the result: the cost would be lower without that requirement, and it would also drop if the requirement were relaxed by one unit. Potassium and calcium do not limit the result, since removing either requirement would not lower the cost.

**Numbers.**

1. `2` ...should buy [2] bottles of coconut water and 1 bottle of...
2. `1` ...should buy 2 bottles of coconut water and [1] bottle of blue energade, for a minimum cost...
3. `$11` ...of blue energade, for a minimum cost of [$11]. This mix meets his magnesium and calcium...
4. `5` ...and calcium needs exactly and leaves [5] units of potassium above his minimum....

## 2042898874

**Problem.** A paint manufacturer produces 300 kg of dye and 200 kg of filler each week. By using different combinations, they can produce three different paint products for sale: Low Quality, Regular Quality, and Premium Quality. The profit per kg for selling the paint is $100, $200, $230 for the low quality, regular quality, and premium quality respectively. To produce 1 kg of low quality paint requires 6 kg of dye and 20 kg of filler. To produce 1 kg of regular quality paint requires 10 kg of dye and 10 kg of filler. To produce 1 kg of premium quality paint require 15 kg of dye and 2 kg of dye. Formulate the problem of deciding how much of each paint to make each week as a LP problem in order to maximize profit.

**Model.**
```
max 100*[low quality paint produced (kg per week)] + 200*[regular quality paint produced (kg per week)] + 230*[premium quality paint produced (kg per week)]
  dye_available: 6*[low quality paint produced (kg per week)] + 10*[regular quality paint produced (kg per week)] + 15*[premium quality paint produced (kg per week)] <= 300
  filler_available: 20*[low quality paint produced (kg per week)] + 10*[regular quality paint produced (kg per week)] + 2*[premium quality paint produced (kg per week)] <= 200
  low quality paint produced (kg per week): continuous, in [0, inf]
  regular quality paint produced (kg per week): continuous, in [0, inf]
  premium quality paint produced (kg per week): continuous, in [0, inf]
```

**Facts.** objective 5461.54; values low quality paint produced (kg per week) = 0, regular quality paint produced (kg per week) = 18.4615, premium quality paint produced (kg per week) = 7.69231; slack dye_available: 4e-06, filler_available: 5e-06; binding: dye_available, filler_available; shadow prices dye_available: 14.6154, filler_available: 5.38462

**Explanation.**

Make no low-quality paint, about 18.46 kg of regular-quality paint, and about 7.69 kg of premium-quality paint each week. This plan earns about $5,461.54 in weekly profit. Both the dye and the filler are fully used, so they are the limits: one more kg of dye would add about $14.62 in profit, and one more kg of filler would add about $5.38.

**Numbers.**

1. `18.46` ...no low-quality paint, about [18.46] kg of regular-quality paint, and about 7.69...
2. `7.69` ...kg of regular-quality paint, and about [7.69] kg of premium-quality paint each week. This...
3. `$5,461.54` ...paint each week. This plan earns about [$5,461.54] in weekly profit. Both the dye and the...
4. `$14.62` ...limits: one more kg of dye would add about [$14.62] in profit, and one more kg of filler would...
5. `$5.38` ...and one more kg of filler would add about [$5.38]....

## -188381292

**Problem.** A software company has UI designers earning $2500 per week and software engineers earning $2000 per week. The contracts with companies to provide cloud services require at least 50 workers, of whom at least 10 must be software engineers. To make sure there is enough experience on the team, the number of software engineers should be at least a third of the number to UI designers. The company wants to keep the weekly wage bill below $200000. Formulate an LP problem to minimize the wage bill.

**Model.**
```
min 2500*[UI designers] + 2000*[software engineers]
  minimum workers: 1*[UI designers] + 1*[software engineers] >= 50
  minimum software engineers: 1*[software engineers] >= 10
  experience ratio: 3*[software engineers] - 1*[UI designers] >= 0
  wage bill limit: 2500*[UI designers] + 2000*[software engineers] <= 200000
  UI designers: integer, in [0, inf]
  software engineers: integer, in [0, inf]
```

**Facts.** objective 100000; values UI designers = 0, software engineers = 50; slack minimum workers: 0, minimum software engineers: 40, experience ratio: 150, wage bill limit: 100000; binding: minimum workers; shadow prices none (a MIP)

**Explanation.**

The lowest-cost plan is to hire no UI designers and 50 software engineers, for a weekly wage bill of $100000. This is the cheapest way to reach the 50-worker minimum, since engineers cost less per week than designers. The 50-worker minimum is the only constraint that limits the result: relaxing it would lower the bill, so the team size requirement drives the cost. The other rules (at least 10 engineers, engineers at least a third of designers, and the $200000 wage cap) are not limiting here, even though they have room to spare.

**Numbers.**

1. `50` ...plan is to hire no UI designers and [50] software engineers, for a weekly wage bill...
2. `$100000` ...engineers, for a weekly wage bill of [$100000]. This is the cheapest way to reach the...
3. `50` ...This is the cheapest way to reach the [50]-worker minimum, since engineers cost less...
4. `50` ...cost less per week than designers. The [50]-worker minimum is the only constraint that...
5. `10` ...drives the cost. The other rules (at least [10] engineers, engineers at least a third of...
6. `$200000` ...at least a third of designers, and the [$200000] wage cap) are not limiting here, even...

## 562583112

**Problem.** A company is delivering packages using two methods, drones and couriers. A drone can transport 4 packages every hour while a courier can transport 25 packages every hour. Drones cost an average of $2 per hour to maintain and couriers are paid $20 per hour. The company needs to deliver at least 800 packages and they can spend at most $1300 per hour for delivery. Since drones have a high up-front cost, the number of drones cannot exceed the number of couriers. How many of each method of delivering packages should be used to minimize the total number of deliveries using drones and couriers?

**Model.**
```
min 1*[drones] + 1*[couriers]
  package_requirement: 4*[drones] + 25*[couriers] >= 800
  cost_budget: 2*[drones] + 20*[couriers] <= 1300
  drone_limit: 1*[drones] - 1*[couriers] <= 0
  drones: integer, in [0, inf]
  couriers: integer, in [0, inf]
```

**Facts.** objective 32; values drones = 0, couriers = 32; slack package_requirement: 0, cost_budget: 660, drone_limit: 32; binding: package_requirement; shadow prices none (a MIP)

**Explanation.**

Use no drones and 32 couriers, which gives the minimum of 32 deliveries (the objective value). This exactly meets the 800-package requirement, and the cost is well within the budget, with $660 of the $1300 left unused. The package requirement is the constraint that limits the result: dropping it would reduce the count, so it is what forces the number up to 32. The budget and the drone limit do not limit the result, since removing either would not improve the answer, even though the drone limit leaves 32 units of slack.

**Numbers.**

1. `32` ...no drones and [32] couriers, which gives the minimum of 32...
2. `32` ...and 32 couriers, which gives the minimum of [32] deliveries (the objective value). This...
3. `800` ...objective value). This exactly meets the [800]-package requirement, and the cost is well...
4. `$660` ...the cost is well within the budget, with [$660] of the $1300 left unused. The package...
5. `$1300` ...is well within the budget, with $660 of the [$1300] left unused. The package requirement is the...
6. `32` ...so it is what forces the number up to [32]. The budget and the drone limit do not...
7. `32` ...answer, even though the drone limit leaves [32] units of...

## 901713880

**Problem.** A patient lacking sleep can take two drowsiness medications, sleeping pills, and sleep supplement. Per serving, sleeping pills increase sleepiness by 2 units and introduces 0.6 units of discomfort. Per serving, sleep supplement increases sleepiness by 3.5 units and introduces 0.3 units of discomfort. Furthermore, pills contain 1 unit of sugar while sleep supplement contains 2.5 units of sugar per serving. The patient needs at least 10 units of sleepiness and can take at most 2.5 units of discomfort. How many servings of each should the patient take to minimize his sugar intake?

**Model.**
```
min 1*[sleeping pill servings] + 2.5*[sleep supplement servings]
  sleepiness: 2*[sleeping pill servings] + 3.5*[sleep supplement servings] >= 10
  discomfort: 0.6*[sleeping pill servings] + 0.3*[sleep supplement servings] <= 2.5
  sleeping pill servings: integer, in [0, inf]
  sleep supplement servings: integer, in [0, inf]
```

**Facts.** objective 7; values sleeping pill servings = 2, sleep supplement servings = 2; slack sleepiness: 1, discomfort: 0.7; binding: none; shadow prices none (a MIP)

**Explanation.**

Take 2 servings of the sleeping pills and 2 servings of the sleep supplement. This gives a sugar intake of 7.0 units, the lowest total that meets the sleepiness and discomfort limits with whole servings. Both limits still restrict the result, even though each has some room left: sleepiness is 1.0 unit above its minimum and discomfort is 0.7 unit below its maximum. Removing either limit would let the sugar total drop, and easing either one by a unit would also lower it, so the patient should treat both as real constraints.

**Numbers.**

1. `2` ...[2] servings of the sleeping pills and 2...
2. `2` ...2 servings of the sleeping pills and [2] servings of the sleep supplement. This...
3. `7.0` ...supplement. This gives a sugar intake of [7.0] units, the lowest total that meets the...
4. `1.0` ...each has some room left: sleepiness is [1.0] unit above its minimum and discomfort is...
5. `0.7` ...unit above its minimum and discomfort is [0.7] unit below its maximum. Removing either...

## 471112257

**Problem.** A children clothing manufacturer can either implement small or large production lines. A small production line is capable of creating 150 sets of clothing every day and takes 12 employees to run. Conversely, the children clothing manufacturer may implement a large production line which requires 26 employees to create 500 sets of clothing per day. There are 435 employees and the manufacturer must meet the demand of at least 6300 sets of children clothing every day. How many of each production line type should be put in place to decrease the total number of production lines?

**Model.**
```
min 1*[small production lines] + 1*[large production lines]
  employees: 12*[small production lines] + 26*[large production lines] <= 435
  daily demand: 150*[small production lines] + 500*[large production lines] >= 6300
  small production lines: integer, in [0, inf]
  large production lines: integer, in [0, inf]
```

**Facts.** objective 13; values small production lines = 0, large production lines = 13; slack employees: 97, daily demand: 200; binding: none; shadow prices none (a MIP)

**Explanation.**

Set up **zero small production lines and 13 large ones**, which gives the fewest total lines (13) while meeting demand. This plan leaves 97 employees unassigned and produces 200 sets more than the 6,300-set daily requirement. The employee limit does not restrict the result, since loosening it or dropping it would not improve the plan. The daily demand requirement does restrict it: removing it would give a better objective, even though the plan has slack there. Making that requirement looser would not help, because the plan is already limited by the need to meet demand.

**Numbers.**

1. `13` ...up **zero small production lines and [13] large ones**, which gives the fewest total...
2. `13` ...ones**, which gives the fewest total lines ([13]) while meeting demand. This plan leaves 97...
3. `97` ...(13) while meeting demand. This plan leaves [97] employees unassigned and produces 200 sets...
4. `200` ...leaves 97 employees unassigned and produces [200] sets more than the 6,300-set daily...
5. `6,300` ...and produces 200 sets more than the [6,300]-set daily requirement. The employee limit...

## -1211890581

**Problem.** A strawberry farmer delivers his strawberries in two types of containers, a box and a bucket. A box contains 7 units of strawberries whereas a bucket contains 9 units of strawberries. The farmer has access to 500 boxes and 300 buckets. Buckets sell for more profit; therefore, the farmer wants to sell at least three times more buckets than boxes. Additionally, he can transport at most 650 containers and at least 25 must be boxes. How many of each type of container should the farmer order to maximize the total amount of strawberries he can transport?

**Model.**
```
max 7*[boxes] + 9*[buckets]
  buckets_at_least_three_times_boxes: 1*[buckets] - 3*[boxes] >= 0
  max_total_containers: 1*[boxes] + 1*[buckets] <= 650
  min_boxes: 1*[boxes] >= 25
  boxes: integer, in [0, 500]
  buckets: integer, in [0, 300]
```

**Facts.** objective 3400; values boxes = 100, buckets = 300; slack buckets_at_least_three_times_boxes: 0, max_total_containers: 250, min_boxes: 75; binding: buckets_at_least_three_times_boxes; shadow prices none (a MIP)

**Explanation.**

Order **100 boxes and 300 buckets**, which carries 3,400 units of strawberries. The buckets are exactly three times the boxes, so that rule is fully used. Dropping that rule would allow a better result, so it is what holds the total back. Even though it is the only fully used constraint, extending its limit by one unit would not help, because the solver's result says a one-unit extension doesn't improve the outcome. The 650-container cap (250 left unused) and the minimum of 25 boxes (75 above the minimum) do not limit the result, since removing either one would not improve it.

**Numbers.**

1. `100` ...**[100] boxes and 300 buckets**, which carries...
2. `300` ...**100 boxes and [300] buckets**, which carries 3,400 units of...
3. `3,400` ...boxes and 300 buckets**, which carries [3,400] units of strawberries. The buckets are...
4. `650` ...extension doesn't improve the outcome. The [650]-container cap (250 left unused) and the...
5. `250` ...improve the outcome. The 650-container cap ([250] left unused) and the minimum of 25 boxes...
6. `25` ...cap (250 left unused) and the minimum of [25] boxes (75 above the minimum) do not limit...
7. `75` ...left unused) and the minimum of 25 boxes ([75] above the minimum) do not limit the result,...

## -1829385566

**Problem.** A milk company is delivering milk to their local families’ homes directly either through bikes or by car. A worker on a bike can deliver 12 orders of milk and takes 40 minutes per trip. A worker on a car can deliver 50 orders of milk and takes 30 minutes per trip. The milk company needs to deliver at least 850 orders of milk. Additionally, at least 70% of delivery trips must be by bike to reduce the pollution. How many of each type of delivery trips must be scheduled to minimize the minutes per trip?

**Model.**
```
min 40*[bike delivery trips] + 30*[car delivery trips]
  orders: 12*[bike delivery trips] + 50*[car delivery trips] >= 850
  bike share: 0.3*[bike delivery trips] - 0.7*[car delivery trips] >= 0
  bike delivery trips: integer, in [0, inf]
  car delivery trips: integer, in [0, inf]
```

**Facts.** objective 1370; values bike delivery trips = 26, car delivery trips = 11; slack orders: 12, bike share: 0.1; binding: none; shadow prices none (a MIP)

**Explanation.**

Schedule **26 bike trips** and **11 car trips**, for a total of **1370 minutes**, the lowest possible under these rules. The plan meets the requirement of at least 850 orders and keeps bike trips at or above 70% of all trips, leaving 12 orders and 0.1 of bike-share margin unused. Both rules still limit the result, even with that margin: dropping either one would lower the total minutes, and loosening the bike-share rule would also improve it. Loosening the orders rule would not help by itself, so the bike-share rule is the tighter restriction.

**Numbers.**

1. `26` ...**[26] bike trips** and **11 car trips**, for a...
2. `11` ...**26 bike trips** and **[11] car trips**, for a total of **1370...
3. `1370` ...and **11 car trips**, for a total of **[1370] minutes**, the lowest possible under these...
4. `850` ...The plan meets the requirement of at least [850] orders and keeps bike trips at or above 70%...
5. `70%` ...850 orders and keeps bike trips at or above [70%] of all trips, leaving 12 orders and 0.1 of...
6. `12` ...trips at or above 70% of all trips, leaving [12] orders and 0.1 of bike-share margin unused....
7. `0.1` ...70% of all trips, leaving 12 orders and [0.1] of bike-share margin unused. Both rules...

## -1362864316

**Problem.** A food distributer can either move their product using trucks or boats. A truck can take 30 units of product and produces 80 units of pollution per trip whereas boats take 50 units of product and produces 60 units of pollution per trip. The food distributer needs to move 1000 units of product and must have a maximum of 40% of the trips using boats due to limitations of sea transportation regulations. Additionally, there must be at least 10 trips using a truck. How many of each form of transportation should be used to minimize the total amount of pollution produced?

**Model.**
```
min 80*[truck trips] + 60*[boat trips]
  product moved: 30*[truck trips] + 50*[boat trips] >= 1000
  boat trip share at most 40%: 0.6*[boat trips] - 0.4*[truck trips] <= 0
  at least 10 truck trips: 1*[truck trips] >= 10
  truck trips: integer, in [0, inf]
  boat trips: integer, in [0, inf]
```

**Facts.** objective 1960; values truck trips = 17, boat trips = 10; slack product moved: 10, boat trip share at most 40%: 0.8, at least 10 truck trips: 7; binding: none; shadow prices none (a MIP)

**Explanation.**

Use **17 truck trips and 10 boat trips**, which gives the lowest pollution total of **1960**. This plan moves at least the required 1000 units, with 10 units to spare. The requirement to move the product and the 40% cap on boat trips both restrict the result: dropping either one would improve the pollution figure, even though the boat-share rule still has 0.8 of slack. Loosening the boat-share limit by one unit would also help, but loosening the product requirement by one unit would not, because the whole-number trips make a small change unhelpful. The minimum of 10 truck trips does not limit the result, since dropping it would not improve the pollution figure and the plan already uses 7 more truck trips than that minimum.

**Numbers.**

1. `17` ...**[17] truck trips and 10 boat trips**, which...
2. `10` ...**17 truck trips and [10] boat trips**, which gives the lowest...
3. `1960` ...which gives the lowest pollution total of **[1960]**. This plan moves at least the required...
4. `1000` ...This plan moves at least the required [1000] units, with 10 units to spare. The...
5. `10` ...at least the required 1000 units, with [10] units to spare. The requirement to move the...
6. `40%` ...The requirement to move the product and the [40%] cap on boat trips both restrict the result:...
7. `0.8` ...even though the boat-share rule still has [0.8] of slack. Loosening the boat-share limit by...
8. `10` ...a small change unhelpful. The minimum of [10] truck trips does not limit the result,...
9. `7` ...pollution figure and the plan already uses [7] more truck trips than that...

## 1122311364

**Problem.** A university has a car building fundraiser where students build toy cars and toy trucks using wheels and wood and sell to benefit a nearby shelter. A toy car requires 4 wheels and 7 units of wood while a toy truck requires 6 wheels and 10 units of wood. Each team has at most 40 wheels and 75 units of wood. In addition, each team can build at most 3 toy cars and the number of toy trucks must be larger than the number toy cars. If a toy car can fundraise $30 and a toy truck can fundraise $35, how many of each toy should a team build to maximize the total amount fundraised?

**Model.**
```
max 30*[toy cars] + 35*[toy trucks]
  wheels: 4*[toy cars] + 6*[toy trucks] <= 40
  wood: 7*[toy cars] + 10*[toy trucks] <= 75
  car limit: 1*[toy cars] <= 3
  more trucks than cars: 1*[toy trucks] - 1*[toy cars] >= 1
  toy cars: integer, in [0, inf]
  toy trucks: integer, in [0, inf]
```

**Facts.** objective 240; values toy cars = 1, toy trucks = 6; slack wheels: 0, wood: 8, car limit: 2, more trucks than cars: 4; binding: wheels; shadow prices none (a MIP)

**Explanation.**

The team should build **1 toy car and 6 toy trucks**, which raises **$240**. The wheel supply is the constraint that limits this result: all 40 wheels are used, and removing that limit would let the team do better. However, one extra wheel wouldn't help on its own, because whole toys can't use a fraction of a wheel. The wood supply, the limit of 3 cars, and the rule requiring more trucks than cars are not limiting the result, since none of them would improve the outcome if removed.

**Numbers.**

1. `1` ...team should build **[1] toy car and 6 toy trucks**, which raises...
2. `6` ...team should build **1 toy car and [6] toy trucks**, which raises **$240**. The...
3. `$240` ...toy car and 6 toy trucks**, which raises **[$240]**. The wheel supply is the constraint that...
4. `40` ...the constraint that limits this result: all [40] wheels are used, and removing that limit...
5. `3` ...of a wheel. The wood supply, the limit of [3] cars, and the rule requiring more trucks...

## 172061722

**Problem.** A researcher is transporting their arsenal of imaging systems using two different methods, by delivery truck and by van. Transporting by delivery truck takes 12 hours and costs $300 per trip. Transporting by van takes 10 hours and costs $200 per trip. The researcher needs to transport 20 trips worth of equipment and has a budget of $5500. Additionally, the number of transports by the delivery truck must be less than the number of transports by van. How many of each transportation method should they use to minimize the total number of hours spent on delivery?

**Model.**
```
min 12*[delivery truck transports] + 10*[van transports]
  trips_required: 1*[delivery truck transports] + 1*[van transports] >= 20
  budget: 300*[delivery truck transports] + 200*[van transports] <= 5500
  truck_fewer_than_van: 1*[delivery truck transports] - 1*[van transports] <= -1
  delivery truck transports: integer, in [0, inf]
  van transports: integer, in [0, inf]
```

**Facts.** objective 200; values delivery truck transports = 0, van transports = 20; slack trips_required: 0, budget: 1500, truck_fewer_than_van: 19; binding: trips_required; shadow prices none (a MIP)

**Explanation.**

Use no delivery trucks and 20 vans, which completes all 20 required trips in 200 total hours, the lowest possible under these rules. The trip requirement is what drives this result: removing it, or loosening it by one trip, would both improve the outcome, and it has no slack. The budget and the rule that trucks must be fewer than vans do not limit the result, since removing either would not improve it, even though $1500 of the budget and a gap of 19 transports go unused.

**Numbers.**

1. `20` ...no delivery trucks and [20] vans, which completes all 20 required trips...
2. `20` ...trucks and 20 vans, which completes all [20] required trips in 200 total hours, the...
3. `200` ...which completes all 20 required trips in [200] total hours, the lowest possible under...
4. `$1500` ...either would not improve it, even though [$1500] of the budget and a gap of 19 transports go...
5. `19` ...though $1500 of the budget and a gap of [19] transports go...

## -920265113

**Problem.** A garbage collection company uses two types of vehicles, truck A and truck B. Truck A requires 3 workers while truck B requires 4 workers. Truck A can collect 40 units of garbage and truck B can collect 50 units of garbage. The garbage collection company has employed 150 workers. The company must use more truck A models than truck B models. Additionally, there must be at least 5 truck A’s and 8 truck B’s. How many of each type of vehicles should the company use to maximize the total amount of garbage that can be collected?

**Model.**
```
max 40*[truck A vehicles] + 50*[truck B vehicles]
  workers: 3*[truck A vehicles] + 4*[truck B vehicles] <= 150
  more truck A than truck B: 1*[truck A vehicles] - 1*[truck B vehicles] >= 1
  truck A vehicles: integer, in [5, inf]
  truck B vehicles: integer, in [8, inf]
```

**Facts.** objective 1970; values truck A vehicles = 38, truck B vehicles = 9; slack workers: 0, more truck A than truck B: 28; binding: workers; shadow prices none (a MIP)

**Explanation.**

Run 38 truck A vehicles and 9 truck B vehicles, which should collect 1,970 units of garbage. This uses all 150 workers, and the requirement that truck A outnumber truck B has 28 units of slack, so it does not restrict the result. The worker supply is the real limit: the plan would improve if the company dropped that limit or had more workers. The plan also meets the minimums of at least 5 truck A and at least 8 truck B.

**Numbers.**

1. `38` ...[38] truck A vehicles and 9 truck B vehicles,...
2. `9` ...38 truck A vehicles and [9] truck B vehicles, which should collect...
3. `1,970` ...9 truck B vehicles, which should collect [1,970] units of garbage. This uses all 150...
4. `150` ...1,970 units of garbage. This uses all [150] workers, and the requirement that truck A...
5. `28` ...that truck A outnumber truck B has [28] units of slack, so it does not restrict the...
6. `5` ...plan also meets the minimums of at least [5] truck A and at least 8 truck...
7. `8` ...minimums of at least 5 truck A and at least [8] truck...

## -1784457731

**Problem.** A toy storage company needs to transport toys using a manual pallet jack or an electric pallet jack. The toy storage company has access to at most 6 manual pallet jacks and 15 electric pallet jacks. The manual pallet jacks can transport 15 boxes every hour while electric pallet jacks can transport 25 boxes every hour. Since electric jacks require less work, the number of electric pallet jacks must exceed the number of manual pallet jacks. If the company can use at most 8 manual pallet jacks and at least 5 electric pallet jacks, how many of each should the company use to maximize the number of boxes they can transport?

**Model.**
```
max 15*[manual pallet jacks] + 25*[electric pallet jacks]
  manual access limit: 1*[manual pallet jacks] <= 6
  electric access limit: 1*[electric pallet jacks] <= 15
  manual use limit: 1*[manual pallet jacks] <= 8
  minimum electric jacks: 1*[electric pallet jacks] >= 5
  electric exceeds manual: 1*[electric pallet jacks] - 1*[manual pallet jacks] >= 1
  manual pallet jacks: integer, in [0, inf]
  electric pallet jacks: integer, in [0, inf]
```

**Facts.** objective 465; values manual pallet jacks = 6, electric pallet jacks = 15; slack manual access limit: 0, electric access limit: 0, manual use limit: 2, minimum electric jacks: 10, electric exceeds manual: 8; binding: manual access limit, electric access limit; shadow prices none (a MIP)

**Explanation.**

The company should use all 6 manual pallet jacks and all 15 electric pallet jacks, which together move 465 boxes per hour. Both fleet limits are fully used, and each one limits the result: having more of either type of jack would raise the total, and dropping either limit would also raise it. The cap of 8 manual jacks, the minimum of 5 electric jacks, and the rule that electric jacks must outnumber manual jacks do not limit the result, since removing or relaxing any of them would not improve the total. The plan is only as good as the 6 manual and 15 electric jacks the company actually has access to.

**Numbers.**

1. `6` ...company should use all [6] manual pallet jacks and all 15 electric...
2. `15` ...use all 6 manual pallet jacks and all [15] electric pallet jacks, which together move...
3. `465` ...electric pallet jacks, which together move [465] boxes per hour. Both fleet limits are fully...
4. `8` ...limit would also raise it. The cap of [8] manual jacks, the minimum of 5 electric...
5. `5` ...The cap of 8 manual jacks, the minimum of [5] electric jacks, and the rule that electric...
6. `6` ...the total. The plan is only as good as the [6] manual and 15 electric jacks the company...
7. `15` ...plan is only as good as the 6 manual and [15] electric jacks the company actually has...

## -978446117

**Problem.** A furniture store builds and sells sofas and beds. Each sofa costs 6 units of wood and 8 units of time while each bed costs 5 units of wood and 10 units of time. The store has available 620 units of wood and 1055 units of time. Each bed takes an additional 5 hours of shipping time while each sofa takes 3 hours of shipping time. Since there are usually more sofas than beds, the store aims to build twice as many sofas than beds. How many of each should the store make to minimize the total shipping time?

**Model.**
```
min 3*[sofas] + 5*[beds]
  wood: 6*[sofas] + 5*[beds] <= 620
  time: 8*[sofas] + 10*[beds] <= 1055
  sofa_bed_ratio: 1*[sofas] - 2*[beds] == 0
  sofas: integer, in [0, inf]
  beds: integer, in [0, inf]
```

**Facts.** objective 0; values sofas = 0, beds = 0; slack wood: 620, time: 1055, sofa_bed_ratio: 0; binding: sofa_bed_ratio; shadow prices none (a MIP)

**Explanation.**

The store should make **no sofas and no beds**. This plan gives a total shipping time of 0, and it meets the rule that sofas be twice the number of beds. The wood limit of 620 and the time limit of 1055 don't limit the result, since removing or loosening either one would not improve it. The answer is zero only because the model asks for the least shipping time and requires no production, so a useful plan would need a minimum number of sofas or beds to make.

**Numbers.**

1. `0,` ...This plan gives a total shipping time of [0,] and it meets the rule that sofas be twice...
2. `620` ...twice the number of beds. The wood limit of [620] and the time limit of 1055 don't limit the...
3. `1055` ...The wood limit of 620 and the time limit of [1055] don't limit the result, since removing or...

## 1824796169

**Problem.** An internet supplier needs to deliver routers to their customers when they first sign up. They can either transport using their internal drivers or outsource to external drivers. Internal drivers spend more time to help the customers set up and can deliver 20 routers every day whereas the external drivers can deliver 35 routers every day. External drivers use hybrid cars and produce 5 units of pollution while the internal drivers use gasoline cars and produce 12 units of pollution. The internet supplier needs to deliver at least 500 routers every day and internal drivers must make up at least 20% of all drivers due to their customer service. There must also be at least 5 external drivers. How many of each type of driver should the internet supplier plan to contract to minimize the total amount of pollution?

**Model.**
```
min 12*[internal drivers] + 5*[external drivers]
  daily deliveries: 20*[internal drivers] + 35*[external drivers] >= 500
  internal share of drivers: 0.8*[internal drivers] - 0.2*[external drivers] >= 0
  minimum external drivers: 1*[external drivers] >= 5
  internal drivers: integer, in [0, inf]
  external drivers: integer, in [0, inf]
```

**Facts.** objective 108; values internal drivers = 4, external drivers = 12; slack daily deliveries: 0, internal share of drivers: 0.8, minimum external drivers: 7; binding: daily deliveries; shadow prices none (a MIP)

**Explanation.**

The supplier should contract 4 internal drivers and 12 external drivers, for a total pollution of 108. This plan exactly meets the 500-router daily requirement. The delivery requirement is the main limit: dropping it would improve the result, but raising it by one router wouldn't, because the driver counts must be whole numbers. The 20% internal-driver rule also limits the plan even though it has 0.8 of slack, since removing it would reduce pollution. The minimum of 5 external drivers does not limit the result, because removing it wouldn't help and the plan already has 7 more external drivers than that minimum.

**Numbers.**

1. `4` ...supplier should contract [4] internal drivers and 12 external drivers,...
2. `12` ...should contract 4 internal drivers and [12] external drivers, for a total pollution of...
3. `108` ...external drivers, for a total pollution of [108]. This plan exactly meets the 500-router...
4. `500` ...of 108. This plan exactly meets the [500]-router daily requirement. The delivery...
5. `20%` ...driver counts must be whole numbers. The [20%] internal-driver rule also limits the plan...
6. `0.8` ...also limits the plan even though it has [0.8] of slack, since removing it would reduce...
7. `5` ...it would reduce pollution. The minimum of [5] external drivers does not limit the result,...
8. `7` ...it wouldn't help and the plan already has [7] more external drivers than that...

## -254808664

**Problem.** A competitive swimmer is training heavily and to do so, plans to eat steaks and chicken breasts over the coming week. Each steak contains 900 calories and 40 g of protein. Each chicken breast contains 700 calories and 20 g of protein. He prefers to eat chicken breasts and decides to eat at least 2 times as many chicken breasts as steaks over the coming week. However, he must also eat at least 10 steaks over the week. If he must consume at least 1200 g of protein over this coming week, how many steaks and chicken breasts should he eat to minimize the total amount of calories he is eating?

**Model.**
```
min 900*[steaks eaten] + 700*[chicken breasts eaten]
  chicken at least twice steaks: 1*[chicken breasts eaten] - 2*[steaks eaten] >= 0
  at least 10 steaks: 1*[steaks eaten] >= 10
  protein requirement: 40*[steaks eaten] + 20*[chicken breasts eaten] >= 1200
  steaks eaten: integer, in [0, inf]
  chicken breasts eaten: integer, in [0, inf]
```

**Facts.** objective 34500; values steaks eaten = 15, chicken breasts eaten = 30; slack chicken at least twice steaks: 0, at least 10 steaks: 5, protein requirement: 0; binding: chicken at least twice steaks, protein requirement; shadow prices none (a MIP)

**Explanation.**

Eat 15 steaks and 30 chicken breasts over the week. That plan meets the 1,200 g protein target exactly and gives the lowest possible total of 34,500 calories. Two rules set the plan: chicken breasts must be at least twice the number of steaks, and protein must reach 1,200 g. Both are fully used, and removing either one would let the calorie total drop, so they are what hold the result in place. The rule to eat at least 10 steaks does not limit the result. The plan already has 5 more steaks than that minimum, and removing the rule would not help.

**Numbers.**

1. `15` ...[15] steaks and 30 chicken breasts over the...
2. `30` ...15 steaks and [30] chicken breasts over the week. That plan...
3. `1,200` ...breasts over the week. That plan meets the [1,200] g protein target exactly and gives the...
4. `34,500` ...and gives the lowest possible total of [34,500] calories. Two rules set the plan: chicken...
5. `1,200` ...number of steaks, and protein must reach [1,200] g. Both are fully used, and removing either...
6. `10` ...result in place. The rule to eat at least [10] steaks does not limit the result. The plan...
7. `5` ...not limit the result. The plan already has [5] more steaks than that minimum, and removing...

## -594806556

**Problem.** A car manufacturing company needs to distribute their cars to their retail stores by either large trailers or small trailers. A large trailer can carry 6 cars while a small trailer can carry 4 cars. Since large trailers are harder to get a hold of, the number of small trailers used has to be at least three times the number of large trailers used. If at least 80 cars need to be transported, minimize the total number of trailers needed.

**Model.**
```
min 1*[large trailers used] + 1*[small trailers used]
  small_at_least_three_times_large: 1*[small trailers used] - 3*[large trailers used] >= 0
  cars_transported: 6*[large trailers used] + 4*[small trailers used] >= 80
  large trailers used: integer, in [0, inf]
  small trailers used: integer, in [0, inf]
```

**Facts.** objective 18; values large trailers used = 4, small trailers used = 14; slack small_at_least_three_times_large: 2, cars_transported: 0; binding: cars_transported; shadow prices none (a MIP)

**Explanation.**

Send 4 large trailers and 14 small trailers, for 18 trailers in total. This covers the required 80 cars exactly, and it meets the rule that small trailers must be at least three times the number of large ones, with 2 small trailers to spare. Both the car requirement and the trailer ratio rule are limiting the result. Dropping the trailer ratio rule would reduce the trailer count, but the rule is there because large trailers are hard to get, so it can't simply be ignored. Adding more cars to the requirement or loosening the ratio wouldn't reduce the count further.

**Numbers.**

1. `4` ...[4] large trailers and 14 small trailers, for...
2. `14` ...4 large trailers and [14] small trailers, for 18 trailers in total....
3. `18` ...4 large trailers and 14 small trailers, for [18] trailers in total. This covers the required...
4. `80` ...trailers in total. This covers the required [80] cars exactly, and it meets the rule that...
5. `2` ...three times the number of large ones, with [2] small trailers to spare. Both the car...

## -1389517053

**Problem.** A chemical company makes an acidic liquid and a basic liquid using two types of techniques, reaction X and reaction Y. Reaction X can make 35 au of the acidic liquid and 75 au of the basic liquid per minute. Reaction Y can make 42 au of the acidic liquid and 35 au of the basic liquid per minute. Furthermore, reaction X requires 18 units of heat every minute while reaction Y requires 12 units of heat every minute. The chemical company has the capacity to generate at most 1400 units of heat every minute. If the chemical company needs to make at least 900 au of the acidic liquid and 1200 au of the basic liquid per minute, how many minutes should each reaction be run for to minimize the total time needed?

**Model.**
```
min 1*[reaction X minutes] + 1*[reaction Y minutes]
  acidic liquid: 35*[reaction X minutes] + 42*[reaction Y minutes] >= 900
  basic liquid: 75*[reaction X minutes] + 35*[reaction Y minutes] >= 1200
  heat capacity: 18*[reaction X minutes] + 12*[reaction Y minutes] <= 1400
  reaction X minutes: continuous, in [0, inf]
  reaction Y minutes: continuous, in [0, inf]
```

**Facts.** objective 23.0649; values reaction X minutes = 9.81818, reaction Y minutes = 13.2468; slack acidic liquid: -1.1e-05, basic liquid: -1e-05, heat capacity: 1064.31; binding: acidic liquid, basic liquid; shadow prices acidic liquid: 0.020779, basic liquid: 0.003636, heat capacity: 0

**Explanation.**

Run reaction X for about 9.82 minutes and reaction Y for about 13.25 minutes, which gives the shortest total time of about 23.06 minutes. This schedule just meets the required 900 au of acidic liquid and 1200 au of basic liquid per minute, so both targets are exactly met with no surplus. The heat limit is not what restricts the plan, since about 1064.31 units of heat capacity go unused. The real limits are the two output targets: each extra au of acidic liquid per minute would add roughly 0.02 minutes, and each extra au of basic liquid would add roughly 0.0036 minutes.

**Numbers.**

1. `9.82` ...reaction X for about [9.82] minutes and reaction Y for about 13.25...
2. `13.25` ...about 9.82 minutes and reaction Y for about [13.25] minutes, which gives the shortest total...
3. `23.06` ...gives the shortest total time of about [23.06] minutes. This schedule just meets the...
4. `900` ...This schedule just meets the required [900] au of acidic liquid and 1200 au of basic...
5. `1200` ...the required 900 au of acidic liquid and [1200] au of basic liquid per minute, so both...
6. `1064.31` ...is not what restricts the plan, since about [1064.31] units of heat capacity go unused. The real...
7. `0.02` ...acidic liquid per minute would add roughly [0.02] minutes, and each extra au of basic liquid...
8. `0.0036` ...extra au of basic liquid would add roughly [0.0036]...

## 709701618

**Problem.** An extremely large mall needs at least 100 transportation methods for customers to move up and down floors. They can either purchase an escalator or an elevator. Due to space limitations, there must be more escalators than elevators, but for convenience, there must be at least 10 elevators. An elevator can transport 1000 customers every day and uses 6 units of electricity in that time span. An escalator can transport 2400 customers every day and uses 9 units of electricity in that time span. The mall has available 800 units of electricity every day. How many of each transportation method should the mall install to maximize the number of customers they can transport every day?

**Model.**
```
max 2400*[escalators] + 1000*[elevators]
  total_transportation_methods: 1*[escalators] + 1*[elevators] >= 100
  more_escalators_than_elevators: 1*[escalators] - 1*[elevators] >= 1
  minimum_elevators: 1*[elevators] >= 10
  electricity_available: 9*[escalators] + 6*[elevators] <= 800
  escalators: integer, in [0, inf]
  elevators: integer, in [0, inf]
```

**Facts.** objective 192400; values escalators = 66, elevators = 34; slack total_transportation_methods: 0, more_escalators_than_elevators: 31, minimum_elevators: 24, electricity_available: 2; binding: total_transportation_methods; shadow prices none (a MIP)

**Explanation.**

Install 66 escalators and 34 elevators, which should move 192,400 customers per day. The 100-method requirement is exactly met, and the mall's 800 units of electricity are nearly all used, with 2 units left over. Both the total-methods requirement and the electricity limit are holding back the result: adding one more method or one more unit of electricity would raise the total, and dropping either would too. The "more escalators than elevators" rule and the "at least 10 elevators" rule are not limiting the result, since removing either would not improve it.

**Numbers.**

1. `66` ...[66] escalators and 34 elevators, which should...
2. `34` ...66 escalators and [34] elevators, which should move 192,400...
3. `192,400` ...and 34 elevators, which should move [192,400] customers per day. The 100-method...
4. `100` ...should move 192,400 customers per day. The [100]-method requirement is exactly met, and the...
5. `800` ...requirement is exactly met, and the mall's [800] units of electricity are nearly all used,...
6. `2` ...of electricity are nearly all used, with [2] units left over. Both the total-methods...
7. `10` ...than elevators" rule and the "at least [10] elevators" rule are not limiting the...

## -1394768760

**Problem.** A restaurant chain can make two types of meals, a steak or vegetarian meal. The steak meal makes $18 profit each and it takes 3 minutes for a chef to make. A vegetarian meal makes $9 profit each and takes 2 minutes for a chef make. The restaurant chain needs to make at least $500 profit every day and has available 1000 minutes of chef involvement. How many of each meal should the restaurant try to push through the waiting staff to minimize the total number of meals they need to make?

**Model.**
```
min 1*[steak meals] + 1*[vegetarian meals]
  minimum daily profit: 18*[steak meals] + 9*[vegetarian meals] >= 500
  chef minutes available: 3*[steak meals] + 2*[vegetarian meals] <= 1000
  steak meals: integer, in [0, inf]
  vegetarian meals: integer, in [0, inf]
```

**Facts.** objective 28; values steak meals = 28, vegetarian meals = 0; slack minimum daily profit: 4, chef minutes available: 916; binding: none; shadow prices none (a MIP)

**Explanation.**

The restaurant should make 28 steak meals and no vegetarian meals, for a total of 28 meals, the fewest that still meets the daily profit target. This plan clears the $500 minimum profit with $4 to spare and uses far less than the 1000 available chef minutes. The $500 profit requirement is what limits the result: if it were removed, fewer meals would be possible, so it is why the count can't go lower. Nudging that $500 target by one dollar wouldn't change the plan, however. The chef-minute limit does not restrict the answer, since removing it wouldn't improve the outcome and 916 minutes go unused.

**Numbers.**

1. `28` ...restaurant should make [28] steak meals and no vegetarian meals, for a...
2. `28` ...and no vegetarian meals, for a total of [28] meals, the fewest that still meets the...
3. `$500` ...daily profit target. This plan clears the [$500] minimum profit with $4 to spare and uses...
4. `$4` ...plan clears the $500 minimum profit with [$4] to spare and uses far less than the 1000...
5. `1000` ...with $4 to spare and uses far less than the [1000] available chef minutes. The $500 profit...
6. `$500` ...than the 1000 available chef minutes. The [$500] profit requirement is what limits the...
7. `$500` ...why the count can't go lower. Nudging that [$500] target by one dollar wouldn't change the...
8. `916` ...it wouldn't improve the outcome and [916] minutes go...
