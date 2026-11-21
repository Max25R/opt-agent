# Explanation labels, batch 1 of 4

Label every numbered number `correct` or `wrong` in `labels-1.csv`, and every explanation's false claim `yes` or `no` in `claims-1.csv`, by the rules of docs/analysis/explanation_checker.md. This sheet doesn't show the checker's flags, on purpose.

## -640645082

**Problem.** A coconut seller has to transport coconuts using either rickshaws or ox carts. The rickshaws can take 50 coconuts each and cost $10 per trip. The ox carts can take 30 coconuts each and cost $8 per trip. The seller has at most $200 to spend on transporting the coconuts. Due to pollution, the number of rickshaws must not exceed the number of ox carts. Formulate a LP to maximize the number of coconuts that can be transported.

**Model.**
```
max 50*[rickshaw trips] + 30*[ox cart trips]
  budget: 10*[rickshaw trips] + 8*[ox cart trips] <= 200
  pollution: 1*[rickshaw trips] - 1*[ox cart trips] <= 0
  rickshaw trips: integer, in [0, inf]
  ox cart trips: integer, in [0, inf]
```

**Facts.** objective 880; values rickshaw trips = 11, ox cart trips = 11; slack budget: 2, pollution: 0; binding: pollution; shadow prices none (a MIP)

**Explanation.**

Send 11 rickshaw trips and 11 ox cart trips, which moves 880 coconuts, the most this plan allows. Both the pollution rule (rickshaws no more than ox carts) and the $200 budget limit the result, even though $2 of the budget is unused. Dropping either rule would allow a better plan, but giving the budget one more dollar or allowing one more rickshaw than ox carts would not help, because trips come in whole units. The plan is only as good as the stated capacities and costs.

**Numbers.**

1. `11` ...[11] rickshaw trips and 11 ox cart trips, which...
2. `11` ...11 rickshaw trips and [11] ox cart trips, which moves 880 coconuts,...
3. `880` ...trips and 11 ox cart trips, which moves [880] coconuts, the most this plan allows. Both...
4. `$200` ...(rickshaws no more than ox carts) and the [$200] budget limit the result, even though $2 of...
5. `$2` ...$200 budget limit the result, even though [$2] of the budget is unused. Dropping either...

## 2117951416

**Problem.** A spicy paste is to be made from units of peppers and tomatoes and is to contain a minimum of 130 units of spice and 90 units of flavor. Peppers cost $8 per unit and tomatoes cost $5 per unit. One unit of peppers contains 12 units of spice and 2 units of flavor. One unit of tomatoes contains 1 unit of spice and 8 units of flavor. Formulate this as an LP and find the minimum cost spicy paste that can be made.

**Model.**
```
min 8*[peppers units] + 5*[tomato units]
  spice minimum: 12*[peppers units] + 1*[tomato units] >= 130
  flavor minimum: 2*[peppers units] + 8*[tomato units] >= 90
  peppers units: continuous, in [0, inf]
  tomato units: continuous, in [0, inf]
```

**Facts.** objective 124.468; values peppers units = 10.1064, tomato units = 8.7234; slack spice minimum: 0, flavor minimum: 0; binding: spice minimum, flavor minimum; shadow prices spice minimum: 0.574468, flavor minimum: 0.553191

**Explanation.**

Make about 10.11 units of peppers and 8.72 units of tomatoes, which gives the cheapest paste at a cost of about $124.47. This mix exactly meets the minimum of 130 spice units and 90 flavor units, with nothing left over. Each extra unit of required spice would raise the cost by about $0.57, and each extra unit of required flavor by about $0.55. The plan is limited by those two minimums, so any stricter requirement makes the paste more expensive.

**Numbers.**

1. `10.11` ...about [10.11] units of peppers and 8.72 units of...
2. `8.72` ...about 10.11 units of peppers and [8.72] units of tomatoes, which gives the cheapest...
3. `$124.47` ...gives the cheapest paste at a cost of about [$124.47]. This mix exactly meets the minimum of 130...
4. `130` ...This mix exactly meets the minimum of [130] spice units and 90 flavor units, with...
5. `90` ...meets the minimum of 130 spice units and [90] flavor units, with nothing left over. Each...
6. `$0.57` ...spice would raise the cost by about [$0.57], and each extra unit of required flavor by...
7. `$0.55` ...each extra unit of required flavor by about [$0.55]. The plan is limited by those two minimums,...

## -1904284746

**Problem.** A cell-phone company makes foldable and regular cell-phones in a factory that is divided into a hardware and software section. The hardware section must work 10 hours on each foldable cell-phone but only 3 hours on each regular one. The software section must work 3 hours for each cell-phone. The profit from the foldable cell-phone is $500 and the profit from the regular cell-phone is $300. Due to a recent strike, the hardware section only has 200 hours available per week and the software section only has 150 hours available per week. How many of each phone should the company produce to maximize profit?

**Model.**
```
max 500*[foldable cell-phones produced] + 300*[regular cell-phones produced]
  hardware hours: 10*[foldable cell-phones produced] + 3*[regular cell-phones produced] <= 200
  software hours: 3*[foldable cell-phones produced] + 3*[regular cell-phones produced] <= 150
  foldable cell-phones produced: integer, in [0, inf]
  regular cell-phones produced: integer, in [0, inf]
```

**Facts.** objective 16400; values foldable cell-phones produced = 7, regular cell-phones produced = 43; slack hardware hours: 1, software hours: 0; binding: software hours; shadow prices none (a MIP)

**Explanation.**

The company should make 7 foldable phones and 43 regular phones each week, which brings in a profit of $16,400. This uses all 150 software hours, and 1 of the 200 hardware hours is left over. Software hours are the bottleneck, but both limits affect the result: removing either constraint would let the model find a better plan. Still, giving the factory one more hour in either section would not raise the profit, because the whole-number requirement on phone counts means extra time can't be used to build another phone.

**Numbers.**

1. `7` ...company should make [7] foldable phones and 43 regular phones each...
2. `43` ...company should make 7 foldable phones and [43] regular phones each week, which brings in a...
3. `$16,400` ...each week, which brings in a profit of [$16,400]. This uses all 150 software hours, and 1 of...
4. `150` ...in a profit of $16,400. This uses all [150] software hours, and 1 of the 200 hardware...
5. `1` ...This uses all 150 software hours, and [1] of the 200 hardware hours is left over....
6. `200` ...uses all 150 software hours, and 1 of the [200] hardware hours is left over. Software hours...

## -927748635

**Problem.** George has 120 acres of farmland on which to grow strawberries and watermelons Both fruits have to be watered and sprayed with bug repellant. There are 150 days per year available for watering and 100 days per year available for spraying bug spray. It takes 0.5 days to water an acre of strawberries and 1 day to spray an acre of strawberries. It takes 0.2 days to water an acre of watermelons and 2 days to spray an acre of watermelons. George earns a profit of $200 per acre of strawberries and $500 per acre of watermelons. How many acres of each fruit should be planted in order to maximize profit?

**Model.**
```
max 200*[strawberry acres] + 500*[watermelon acres]
  land: 1*[strawberry acres] + 1*[watermelon acres] <= 120
  watering: 0.5*[strawberry acres] + 0.2*[watermelon acres] <= 150
  spraying: 1*[strawberry acres] + 2*[watermelon acres] <= 100
  strawberry acres: continuous, in [0, inf]
  watermelon acres: continuous, in [0, inf]
```

**Facts.** objective 25000; values strawberry acres = 0, watermelon acres = 50; slack land: 70, watering: 140, spraying: 0; binding: spraying; shadow prices land: 0, watering: 0, spraying: 250

**Explanation.**

Plant no strawberries and devote all 120 acres... no, plant 50 acres of watermelons and leave the rest of the farmland unplanted. This earns the maximum profit of $25,000. The spraying days are the bottleneck: every watermelon acre needs 2 spraying days, so the 100 days available are fully used. Each extra spraying day would add about $250 in profit, but George's land (70 acres unused) and watering days (140 unused) are not limiting anything.

**Numbers.**

1. `120` ...no strawberries and devote all [120] acres... no, plant 50 acres of watermelons...
2. `50` ...and devote all 120 acres... no, plant [50] acres of watermelons and leave the rest of...
3. `$25,000` ...unplanted. This earns the maximum profit of [$25,000]. The spraying days are the bottleneck:...
4. `2` ...the bottleneck: every watermelon acre needs [2] spraying days, so the 100 days available...
5. `100` ...acre needs 2 spraying days, so the [100] days available are fully used. Each extra...
6. `$250` ...Each extra spraying day would add about [$250] in profit, but George's land (70 acres...
7. `70` ...about $250 in profit, but George's land ([70] acres unused) and watering days (140...
8. `140` ...land (70 acres unused) and watering days ([140] unused) are not limiting...

## 1778958258

**Problem.** Two brothers, John and William, run a stand selling lemonade and brownies. A pitcher of lemonade takes 0.5 hours of John's time along with 0.2 hours of William's time. A batch of brownies take 1 hour of John's time and 0.5 hours of William's time. John has 10 hours available each day, but since William has hockey lessons, he only has 8 hours available each day. They get $20 profit per pitcher of lemonade, and $15 per batch of brownies. Formulate a LP to maximize profit.

**Model.**
```
max 20*[pitchers of lemonade] + 15*[batches of brownies]
  John's hours: 0.5*[pitchers of lemonade] + 1*[batches of brownies] <= 10
  William's hours: 0.2*[pitchers of lemonade] + 0.5*[batches of brownies] <= 8
  pitchers of lemonade: integer, in [0, inf]
  batches of brownies: integer, in [0, inf]
```

**Facts.** objective 400; values pitchers of lemonade = 20, batches of brownies = 0; slack John's hours: 0, William's hours: 4; binding: John's hours; shadow prices none (a MIP)

**Explanation.**

Make 20 pitchers of lemonade and no batches of brownies. This brings in a profit of $400 per day. John's 10 hours are fully used, and that is what holds the result back: giving John more time would raise profit. William has 4 of his 8 hours left over, and removing his hours limit would not improve the result, so it does not restrict the plan.

**Numbers.**

1. `20` ...[20] pitchers of lemonade and no batches of...
2. `$400` ...of brownies. This brings in a profit of [$400] per day. John's 10 hours are fully used,...
3. `10` ...brings in a profit of $400 per day. John's [10] hours are fully used, and that is what...
4. `4` ...more time would raise profit. William has [4] of his 8 hours left over, and removing his...
5. `8` ...would raise profit. William has 4 of his [8] hours left over, and removing his hours...

## -1577213425

**Problem.** A factory makes bike tires and car tires. Bike tires take 4 minutes on the manufacturing machine and 2 minutes to fill with air. Car tires take 6 minutes on the manufacturing machine and 3.5 minutes to fill with air. The factory can run the manufacturing machine for at most 600 minutes and they have 400 minutes available for filling the tires with air. If the profit per bike tire is $12 and the profit per car tire is $20, how many of each tire should the factory make to maximize profit?

**Model.**
```
max 12*[bike tires made] + 20*[car tires made]
  manufacturing machine time: 4*[bike tires made] + 6*[car tires made] <= 600
  air filling time: 2*[bike tires made] + 3.5*[car tires made] <= 400
  bike tires made: integer, in [0, inf]
  car tires made: integer, in [0, inf]
```

**Facts.** objective 2000; values bike tires made = 0, car tires made = 100; slack manufacturing machine time: 0, air filling time: 50; binding: manufacturing machine time; shadow prices none (a MIP)

**Explanation.**

**What to do:** Make no bike tires and 100 car tires. **What it achieves:** This gives the highest profit the factory can reach, $2000. **What limits it:** The manufacturing machine time is fully used, and dropping that limit would allow a better result, so it is the constraint holding profit down. Adding one more unit of machine time would not raise profit, because whole tires can't be made from a fraction of a unit. The air-filling time has 50 units left over and doesn't limit the result, since neither loosening nor removing it would improve profit.

**Numbers.**

1. `100` ...to do:** Make no bike tires and [100] car tires. **What it achieves:** This gives...
2. `$2000` ...the highest profit the factory can reach, [$2000]. **What limits it:** The manufacturing...
3. `50` ...of a unit. The air-filling time has [50] units left over and doesn't limit the...

## -156815021

**Problem.** A university has 1200 units of antibiotics to make two creams, a anti-inflammatory cream and a pain-killing cream. A container of anti-inflammatory cream requires 2 units of antibiotics and 4 units of water. A container of pain-killing cream requires 3 units of antibiotics and 2 units of water. The lab has to make at least 50 anti-inflammatory creams. However, since pain-killing creams are in high demand, at least 55% of the total number of creams must be pain-killing creams. How many of each should be made to minimize the total amount of water needed?

**Model.**
```
min 4*[anti-inflammatory cream containers] + 2*[pain-killing cream containers]
  antibiotics: 2*[anti-inflammatory cream containers] + 3*[pain-killing cream containers] <= 1200
  min anti-inflammatory: 1*[anti-inflammatory cream containers] >= 50
  pain-killing share: 0.55*[anti-inflammatory cream containers] - 0.45*[pain-killing cream containers] <= 0
  anti-inflammatory cream containers: integer, in [0, inf]
  pain-killing cream containers: integer, in [0, inf]
```

**Facts.** objective 324; values anti-inflammatory cream containers = 50, pain-killing cream containers = 62; slack antibiotics: 914, min anti-inflammatory: 0, pain-killing share: 0.4; binding: min anti-inflammatory; shadow prices none (a MIP)

**Explanation.**

Make 50 anti-inflammatory cream containers and 62 pain-killing cream containers. This uses 324 units of water, the lowest amount that meets the requirements. The minimum of 50 anti-inflammatory containers and the 55% pain-killing share both limit the result, and easing either one would reduce the water needed. The antibiotic supply does not limit it, since 914 units are left over.

**Numbers.**

1. `50` ...[50] anti-inflammatory cream containers and 62...
2. `62` ...50 anti-inflammatory cream containers and [62] pain-killing cream containers. This uses...
3. `324` ...62 pain-killing cream containers. This uses [324] units of water, the lowest amount that...
4. `50` ...that meets the requirements. The minimum of [50] anti-inflammatory containers and the 55%...
5. `55%` ...of 50 anti-inflammatory containers and the [55%] pain-killing share both limit the result,...
6. `914` ...antibiotic supply does not limit it, since [914] units are left...

## -458048177

**Problem.** A fitness trainer meal-preps two types of meals, a salmon lunch and a bison burger. The salmon lunch contains 15 grams of protein, 20 grams of carbs, and 8 grams of fat. The bison burger contains 30 grams of protein, 20 grams of carbs, and 13 grams of fat. The fitness trainer wants to get at least 160 grams of protein and 180 grams of carbs. In addition, because the salmon lunch is expensive, at most 25% of the meals should be salmon lunch. How many of each meal should he eat if he wants to minimize his fat intake?

**Model.**
```
min 8*[salmon lunches] + 13*[bison burgers]
  protein: 15*[salmon lunches] + 30*[bison burgers] >= 160
  carbs: 20*[salmon lunches] + 20*[bison burgers] >= 180
  salmon share at most 25 percent: 0.75*[salmon lunches] - 0.25*[bison burgers] <= 0
  salmon lunches: integer, in [0, inf]
  bison burgers: integer, in [0, inf]
```

**Facts.** objective 107; values salmon lunches = 2, bison burgers = 7; slack protein: 80, carbs: 0, salmon share at most 25 percent: 0.25; binding: carbs; shadow prices none (a MIP)

**Explanation.**

Eat 2 salmon lunches and 7 bison burgers, which gives the lowest fat intake the model allows: 107 grams. The protein requirement doesn't restrict this choice, since the plan provides 80 grams more protein than needed. The carb requirement does restrict it: the plan meets it exactly, and dropping it would lower the fat total, though raising the carb target by one unit wouldn't help because meals come in whole units. The 25% salmon cap also limits the result, even though the plan leaves some room under it, because relaxing it by one unit would lower fat.

**Numbers.**

1. `2` ...[2] salmon lunches and 7 bison burgers, which...
2. `7` ...2 salmon lunches and [7] bison burgers, which gives the lowest fat...
3. `107` ...the lowest fat intake the model allows: [107] grams. The protein requirement doesn't...
4. `80` ...this choice, since the plan provides [80] grams more protein than needed. The carb...
5. `25%` ...help because meals come in whole units. The [25%] salmon cap also limits the result, even...

## 882129265

**Problem.** A lumber company owns and can use at most 450 acres of land where they can transport the lumber out using large and small logging trucks. Per acre of land, small logging trucks can be used to transport 3 units of wood. Per acre of land, a large logging truck can transport 7 units of wood. However, a small logging truck produces 12 units of carbon dioxide and requires 7 units of gasoline per acre. A large logging truck produces 25 units of carbon dioxide and requires 12 units of gasoline per acre. The lumbering company has access to 3200 units of gasoline and the company has vowed to limiting pollution to 5200 units of carbon dioxide. How should the two types of logging trucks be distributed to stay within the limits of carbon dioxide while maximizing the amount of wood transported?

**Model.**
```
max 3*[acres of land allocated to small logging trucks] + 7*[acres of land allocated to large logging trucks]
  land: 1*[acres of land allocated to small logging trucks] + 1*[acres of land allocated to large logging trucks] <= 450
  gasoline: 7*[acres of land allocated to small logging trucks] + 12*[acres of land allocated to large logging trucks] <= 3200
  carbon_dioxide: 12*[acres of land allocated to small logging trucks] + 25*[acres of land allocated to large logging trucks] <= 5200
  acres of land allocated to small logging trucks: continuous, in [0, inf]
  acres of land allocated to large logging trucks: continuous, in [0, inf]
```

**Facts.** objective 1456; values acres of land allocated to small logging trucks = 0, acres of land allocated to large logging trucks = 208; slack land: 242, gasoline: 704, carbon_dioxide: 0; binding: carbon_dioxide; shadow prices land: 0, gasoline: 0, carbon_dioxide: 0.28

**Explanation.**

The best plan is to use no small trucks and assign all 208 acres to large logging trucks, which transports 1456 units of wood. The carbon dioxide cap of 5200 units is the binding limit, so it stops any further gain, while 242 acres of land and 704 units of gasoline remain unused. Each extra unit of carbon dioxide allowed would add about 0.28 units of wood transported, so loosening the pollution cap is the only change that would increase output. This result depends only on the land, gasoline, and carbon dioxide limits in the model, and it assumes the per-acre figures hold.

**Numbers.**

1. `208` ...is to use no small trucks and assign all [208] acres to large logging trucks, which...
2. `1456` ...to large logging trucks, which transports [1456] units of wood. The carbon dioxide cap of...
3. `5200` ...units of wood. The carbon dioxide cap of [5200] units is the binding limit, so it stops any...
4. `242` ...limit, so it stops any further gain, while [242] acres of land and 704 units of gasoline...
5. `704` ...further gain, while 242 acres of land and [704] units of gasoline remain unused. Each extra...
6. `0.28` ...of carbon dioxide allowed would add about [0.28] units of wood transported, so loosening the...

## -1603423876

**Problem.** A supermarket can purchase two types of refrigerators to properly store their food, refrigerator ABC and refrigerator XYZ, and they have different specifications to consider. Refrigerator ABC is larger and can store 120 items but uses 3 kWh. Refrigerator XYZ is smaller more efficient and can store 80 items but uses 1 kWh. Due to soaring electric prices, the store is limited to at most 55 kWh but must store at least 1500 items. The store must have at least 8 refrigerator ABC’s and 5 refrigerator XYZ’s. How many of each type of refrigerator should the supermarket purchase to minimize the number of refrigerators needed?

**Model.**
```
min 1*[ABC refrigerators purchased] + 1*[XYZ refrigerators purchased]
  energy_limit: 3*[ABC refrigerators purchased] + 1*[XYZ refrigerators purchased] <= 55
  item_storage: 120*[ABC refrigerators purchased] + 80*[XYZ refrigerators purchased] >= 1500
  min_ABC: 1*[ABC refrigerators purchased] >= 8
  min_XYZ: 1*[XYZ refrigerators purchased] >= 5
  ABC refrigerators purchased: integer, in [0, inf]
  XYZ refrigerators purchased: integer, in [0, inf]
```

**Facts.** objective 15; values ABC refrigerators purchased = 10, XYZ refrigerators purchased = 5; slack energy_limit: 20, item_storage: 100, min_ABC: 2, min_XYZ: 0; binding: min_XYZ; shadow prices none (a MIP)

**Explanation.**

Buy 10 ABC refrigerators and 5 XYZ refrigerators, for 15 units in total, the fewest that meets the store's rules. The minimum of 5 XYZ units is fully used and is holding the count up, since lowering that minimum would let the store buy fewer. The 1,500-item storage requirement also limits the result, even though 100 items of capacity are unused, because dropping it would allow a smaller purchase. The 55 kWh power limit (20 kWh to spare) and the minimum of 8 ABC units (2 extra) do not limit the result, and raising the power limit would not reduce the count.

**Numbers.**

1. `10` ...[10] ABC refrigerators and 5 XYZ refrigerators,...
2. `5` ...10 ABC refrigerators and [5] XYZ refrigerators, for 15 units in total,...
3. `15` ...refrigerators and 5 XYZ refrigerators, for [15] units in total, the fewest that meets the...
4. `5` ...meets the store's rules. The minimum of [5] XYZ units is fully used and is holding the...
5. `1,500` ...minimum would let the store buy fewer. The [1,500]-item storage requirement also limits the...
6. `100` ...also limits the result, even though [100] items of capacity are unused, because...
7. `55` ...it would allow a smaller purchase. The [55] kWh power limit (20 kWh to spare) and the...
8. `20` ...a smaller purchase. The 55 kWh power limit ([20] kWh to spare) and the minimum of 8 ABC...
9. `8` ...limit (20 kWh to spare) and the minimum of [8] ABC units (2 extra) do not limit the...
10. `2` ...to spare) and the minimum of 8 ABC units ([2] extra) do not limit the result, and raising...

## 542112273

**Problem.** A logging company ships their lumber to a nearby country using logging trucks and by lumber carrier vessels. Each logging truck costs the logging company $250 for every trip and moves 1000 lbs of lumber. A lumber carrier vessel costs $1000 every trip and moves 6000 lbs of lumber. Due to limited waters and difficulties in scheduling the trips for lumber carrier vessels, the company’s management asks that the number of logging trucks must exceed the number of lumber carrier vessels. The logging company must transport at least 300000 lbs of lumber to the nearby country. How many of each type of transportation should the company schedule to move their lumber to minimize the total cost?

**Model.**
```
min 250*[logging truck trips] + 1000*[lumber carrier vessel trips]
  trucks_exceed_vessels: 1*[logging truck trips] - 1*[lumber carrier vessel trips] >= 1
  lumber_requirement: 1000*[logging truck trips] + 6000*[lumber carrier vessel trips] >= 300000
  logging truck trips: integer, in [0, inf]
  lumber carrier vessel trips: integer, in [0, inf]
```

**Facts.** objective 54000; values logging truck trips = 44, lumber carrier vessel trips = 43; slack trucks_exceed_vessels: 0, lumber_requirement: 2000; binding: trucks_exceed_vessels; shadow prices none (a MIP)

**Explanation.**

The company should schedule **44 logging truck trips** and **43 lumber carrier vessel trips**, for a minimum total cost of **$54,000**. The trucks-exceed-vessels rule is fully used (trucks lead vessels by exactly 1), and it limits the result: easing that rule by one unit would lower the cost. The 300,000 lb lumber requirement has 2,000 lbs to spare, but it still limits the result because dropping it would lower the cost, and making it one unit easier would not help, since whole trips can't cover a smaller gap. So this plan is the cheapest option that keeps both the management rule and the lumber target.

**Numbers.**

1. `44` ...company should schedule **[44] logging truck trips** and **43 lumber...
2. `43` ...schedule **44 logging truck trips** and **[43] lumber carrier vessel trips**, for a...
3. `$54,000` ...trips**, for a minimum total cost of **[$54,000]**. The trucks-exceed-vessels rule is fully...
4. `1` ...fully used (trucks lead vessels by exactly [1]), and it limits the result: easing that...
5. `300,000` ...rule by one unit would lower the cost. The [300,000] lb lumber requirement has 2,000 lbs to...
6. `2,000` ...cost. The 300,000 lb lumber requirement has [2,000] lbs to spare, but it still limits the...

## 1738481857

**Problem.** A physics teacher shows her students two experiments, a force experiment and a hydraulics experiment. In the force experiment, 5 units of the solid and 2 units of the gas mixes and reacts to create 3 units of excitement. In the hydraulics experiment, 7 units of the solid and 6 units of the gas mixes and reacts to create 5 units of excitement. In addition, the hydraulics experiment produces 2 units of heat while the force experiment produces 3 units of heat.  The lab has available 90 units of the solid and 85 units of the gas. If at most 15 units of heat can be produced, how many experiments of each should be done to maximize the total excitement?

**Model.**
```
max 3*[force experiments] + 5*[hydraulics experiments]
  solid available: 5*[force experiments] + 7*[hydraulics experiments] <= 90
  gas available: 2*[force experiments] + 6*[hydraulics experiments] <= 85
  heat limit: 3*[force experiments] + 2*[hydraulics experiments] <= 15
  force experiments: integer, in [0, inf]
  hydraulics experiments: integer, in [0, inf]
```

**Facts.** objective 35; values force experiments = 0, hydraulics experiments = 7; slack solid available: 41, gas available: 43, heat limit: 1; binding: none; shadow prices none (a MIP)

**Explanation.**

Do 7 hydraulics experiments and no force experiments. This gives a total excitement of 35. The heat limit is what holds the result back: even though 1 unit of heat is left unused, the solution would be worse without that limit. Solid and gas are not limiting, since the result would not improve with either dropped or loosened, so the lab has plenty of them to spare.

**Numbers.**

1. `7` ...[7] hydraulics experiments and no force...
2. `35` ...This gives a total excitement of [35]. The heat limit is what holds the result...
3. `1` ...is what holds the result back: even though [1] unit of heat is left unused, the solution...

## 1206867214

**Problem.** Architects ABC has a budget of one hundred thousand dollars to spend every week on their employees. They hire architects and drafters to help with their clients’ projects. An architect averages 3000 dollars every week and can complete 2 projects every week. A drafter does not have all the certifications and requires an architect for supervision at all times. Therefore, there must be more architects than drafters. Additionally, a drafter averages 1200 dollars every week and completes 1 project every week. How many architects and drafters should be contracted to maximize the number of projects completed every week?

**Model.**
```
max 2*[architects hired] + 1*[drafters hired]
  weekly budget: 3000*[architects hired] + 1200*[drafters hired] <= 100000
  more architects than drafters: 1*[architects hired] - 1*[drafters hired] >= 1
  architects hired: integer, in [0, inf]
  drafters hired: integer, in [0, inf]
```

**Facts.** objective 71; values architects hired = 24, drafters hired = 23; slack weekly budget: 400, more architects than drafters: 0; binding: more architects than drafters; shadow prices none (a MIP)

**Explanation.**

Hire 24 architects and 23 drafters each week to complete 71 projects, the most the budget and staffing rule allow. The one-more-architect-than-drafter rule is exactly met, so it sets the mix. The weekly budget leaves 400 dollars unspent, but it still limits the result: removing it entirely would allow a better plan, though adding one unit to its limit would not help because hires come in whole people. Likewise, the supervision rule limits the result, since dropping it would improve the outcome even though loosening it by one more unit would not.

**Numbers.**

1. `24` ...[24] architects and 23 drafters each week to...
2. `23` ...24 architects and [23] drafters each week to complete 71 projects,...
3. `71` ...and 23 drafters each week to complete [71] projects, the most the budget and staffing...
4. `400` ...it sets the mix. The weekly budget leaves [400] dollars unspent, but it still limits the...

## 1455902979

**Problem.** A butcher sells marinated wild boar and processed lamb chops. Each portion of marinated wild boar requires 3 minutes of preparation and 6 ounces of meat. One portion of processed lamb chops requires 1 minute of preparation and 7 ounces of meat. Since processed lamb chops are more popular and common, the butcher plans to make at least twice as many processed lamb chops as marinated wild boars. The butcher has a small staff and only has available 250 collective minutes every week to preparing these two items and only has available 1375 ounces of meat. If a portion of marinated wild boar sells for a revenue of 6 dollars whereas a portion of processed lamb chops sells for a revenue of 4 dollars, how many of each should the butcher make to maximize their revenue?

**Model.**
```
max 6*[marinated wild boar portions] + 4*[processed lamb chop portions]
  preparation_minutes: 3*[marinated wild boar portions] + 1*[processed lamb chop portions] <= 250
  meat_ounces: 6*[marinated wild boar portions] + 7*[processed lamb chop portions] <= 1375
  lamb_at_least_twice_boar: 1*[processed lamb chop portions] - 2*[marinated wild boar portions] >= 0
  marinated wild boar portions: integer, in [0, inf]
  processed lamb chop portions: integer, in [0, inf]
```

**Facts.** objective 850; values marinated wild boar portions = 25, processed lamb chop portions = 175; slack preparation_minutes: 0, meat_ounces: 0, lamb_at_least_twice_boar: 125; binding: preparation_minutes, meat_ounces; shadow prices none (a MIP)

**Explanation.**

The butcher should make 25 portions of marinated wild boar and 175 portions of processed lamb chops, for a total revenue of $850. Both the weekly preparation time (250 minutes) and the meat supply (1375 ounces) are fully used, so they are what caps production. The requirement to make at least twice as many lamb chops as boar has 125 portions to spare, so it is not holding the result back. Making one more unit of either limit wouldn't raise revenue, but removing either limit would, so both are real constraints on the result. The plan is only as good as those two limits, so more time or meat would be the main way to earn more.

**Numbers.**

1. `25` ...butcher should make [25] portions of marinated wild boar and 175...
2. `175` ...make 25 portions of marinated wild boar and [175] portions of processed lamb chops, for a...
3. `$850` ...lamb chops, for a total revenue of [$850]. Both the weekly preparation time (250...
4. `250` ...of $850. Both the weekly preparation time ([250] minutes) and the meat supply (1375 ounces)...
5. `1375` ...time (250 minutes) and the meat supply ([1375] ounces) are fully used, so they are what...
6. `125` ...least twice as many lamb chops as boar has [125] portions to spare, so it is not holding the...

## -668544637

**Problem.** A landscaping company provides services from an expert or an apprentice. An expert costs the company 500 dollars for each shift and can care for 100 square meters of land whereas an apprentice costs the company 300 dollars for each shift and can care for 80 square meters of land. Because of the price to the customer, the company expects the demand of the public to want at least twice as many apprentices than experts. However, there are loyal customers that prefer the experts. Therefore, at least 10% of shifts must be expert shifts. The company must care for 5000 square meters of land. How many of each type of service should be used to minimize the total cost to the company?

**Model.**
```
min 500*[expert shifts] + 300*[apprentice shifts]
  land care: 100*[expert shifts] + 80*[apprentice shifts] >= 5000
  apprentice demand: 1*[apprentice shifts] - 2*[expert shifts] >= 0
  expert share: 0.9*[expert shifts] - 0.1*[apprentice shifts] >= 0
  expert shifts: integer, in [0, inf]
  apprentice shifts: integer, in [0, inf]
```

**Facts.** objective 19700; values expert shifts = 7, apprentice shifts = 54; slack land care: 20, apprentice demand: 40, expert share: 0.9; binding: none; shadow prices none (a MIP)

**Explanation.**

Schedule 7 expert shifts and 54 apprentice shifts. This covers the required 5,000 square meters at the lowest total cost, 19,700 dollars. The expert-share rule limits the result: relaxing it by one unit would lower the cost, and dropping it would too. The land requirement also limits the result, even though 20 square meters of extra care is left over. Dropping that requirement would lower the cost, but adding more land to the requirement would not help. The apprentice-demand rule does not limit the result, since it has 40 units of room and removing it would not improve the cost.

**Numbers.**

1. `7` ...[7] expert shifts and 54 apprentice shifts....
2. `54` ...7 expert shifts and [54] apprentice shifts. This covers the required...
3. `5,000` ...apprentice shifts. This covers the required [5,000] square meters at the lowest total cost,...
4. `19,700` ...square meters at the lowest total cost, [19,700] dollars. The expert-share rule limits the...
5. `20` ...also limits the result, even though [20] square meters of extra care is left over....
6. `40` ...does not limit the result, since it has [40] units of room and removing it would not...

## -1633326119

**Problem.** A composting company can store compost in medium containers and large containers. A medium container needs to be checked 5 times a week and can store 25 units of compost. A large container needs to be checked 2 times a week and can store 40 units of compost. The company needs to store at least 500 units of compost and there must be at least 3 medium containers. There must also be at least 2 large containers and the number of large containers must be three times as much as the number of medium containers. How many of each type of containers should be used to minimize the total number of times checking containers?

**Model.**
```
min 5*[medium containers] + 2*[large containers]
  storage: 25*[medium containers] + 40*[large containers] >= 500
  minimum medium containers: 1*[medium containers] >= 3
  minimum large containers: 1*[large containers] >= 2
  large containers three times medium: 1*[large containers] - 3*[medium containers] == 0
  medium containers: integer, in [0, inf]
  large containers: integer, in [0, inf]
```

**Facts.** objective 44; values medium containers = 4, large containers = 12; slack storage: 80, minimum medium containers: 1, minimum large containers: 10, large containers three times medium: 0; binding: large containers three times medium; shadow prices none (a MIP)

**Explanation.**

Use 4 medium containers and 12 large containers, which keeps the number of large containers at three times the number of medium ones. This gives the lowest weekly checking workload of 44 checks. The storage requirement of 500 units is a real limit: it still has 80 units of spare capacity, but removing it would improve the result, so it is shaping the answer. The rule that large containers must be three times the medium ones also limits the result, since dropping it would improve the objective, and the two minimum-count rules (at least 3 medium, at least 2 large) do not limit it.

**Numbers.**

1. `4` ...[4] medium containers and 12 large containers,...
2. `12` ...4 medium containers and [12] large containers, which keeps the number of...
3. `44` ...the lowest weekly checking workload of [44] checks. The storage requirement of 500...
4. `500` ...of 44 checks. The storage requirement of [500] units is a real limit: it still has 80...
5. `80` ...of 500 units is a real limit: it still has [80] units of spare capacity, but removing it...
6. `3` ...and the two minimum-count rules (at least [3] medium, at least 2 large) do not limit...
7. `2` ...rules (at least 3 medium, at least [2] large) do not limit...

## 1062319269

**Problem.** A pharmaceutical manufacturing plant has 1000 mg of cornstarch to rush orders of diabetic pills and latex gloves. Each diabetic pill requires 4 mg of cornstarch and 0.2 minutes to manufacture. Each individual latex glove requires 7 mg of cornstarch and 0.15 minutes to manufacture. The pharmaceutical manufacturing plant needs to make at least 20 diabetic pills. Since latex gloves are important, at least 60% of produced items must be latex gloves. How many of each should the pharmaceutical manufacturing plant make to minimize the total number of minutes needed?

**Model.**
```
min 0.2*[diabetic pills] + 0.15*[latex gloves]
  cornstarch: 4*[diabetic pills] + 7*[latex gloves] <= 1000
  min_pills: 1*[diabetic pills] >= 20
  glove_share: -0.6*[diabetic pills] + 0.4*[latex gloves] >= 0
  diabetic pills: integer, in [0, inf]
  latex gloves: integer, in [0, inf]
```

**Facts.** objective 8.5; values diabetic pills = 20, latex gloves = 30; slack cornstarch: 710, min_pills: 0, glove_share: 0; binding: min_pills, glove_share; shadow prices none (a MIP)

**Explanation.**

Make 20 diabetic pills and 30 latex gloves, which takes 8.5 minutes in total. This meets the minimum of 20 pills and the rule that gloves make up at least 60% of items. The plant has 710 mg of cornstarch left over, but more cornstarch would not reduce the time, so it is not what holds the result back. The two real limits are the 20-pill minimum and the 60% glove share: relaxing either one would lower the minutes needed.

**Numbers.**

1. `20` ...[20] diabetic pills and 30 latex gloves, which...
2. `30` ...20 diabetic pills and [30] latex gloves, which takes 8.5 minutes in...
3. `8.5` ...pills and 30 latex gloves, which takes [8.5] minutes in total. This meets the minimum of...
4. `20` ...minutes in total. This meets the minimum of [20] pills and the rule that gloves make up at...
5. `60%` ...and the rule that gloves make up at least [60%] of items. The plant has 710 mg of...
6. `710` ...up at least 60% of items. The plant has [710] mg of cornstarch left over, but more...
7. `20` ...result back. The two real limits are the [20]-pill minimum and the 60% glove share:...
8. `60%` ...real limits are the 20-pill minimum and the [60%] glove share: relaxing either one would...

## -1910834629

**Problem.** Emergency supplies need to be delivered to a remote area and can either go by airplane or helicopter. An airplane can transport 35 units of goods and takes 30 minutes while a helicopter can transport 20 units of goods and takes 10 minutes due to easier take-off and landing. The number of helicopters must exceed the number of airplanes. Additionally, there must be at least 5 airplanes to fully utilize the landing space.  If there needs to be at least 500 units of goods transported, how many of each type of transportation should be utilized to minimize the total number of minutes needed?

**Model.**
```
min 30*[airplanes] + 10*[helicopters]
  goods_transported: 35*[airplanes] + 20*[helicopters] >= 500
  helicopters_exceed_airplanes: 1*[helicopters] - 1*[airplanes] >= 1
  min_airplanes: 1*[airplanes] >= 5
  airplanes: integer, in [0, inf]
  helicopters: integer, in [0, inf]
```

**Facts.** objective 320; values airplanes = 5, helicopters = 17; slack goods_transported: 15, helicopters_exceed_airplanes: 11, min_airplanes: 0; binding: min_airplanes; shadow prices none (a MIP)

**Explanation.**

Send 5 airplanes and 17 helicopters, for a total of 320 minutes, the lowest time that meets the requirements. The rule requiring at least 5 airplanes is the main limit: relaxing it by one unit would reduce the time, so it is what holds the airplane count at 5. The 500-unit goods requirement also limits the result, since dropping it would improve the objective even though 15 units of capacity are spare. The rule that helicopters must exceed airplanes does not limit the result, because neither dropping it nor loosening it would change the plan.

**Numbers.**

1. `5` ...[5] airplanes and 17 helicopters, for a total...
2. `17` ...5 airplanes and [17] helicopters, for a total of 320 minutes,...
3. `320` ...and 17 helicopters, for a total of [320] minutes, the lowest time that meets the...
4. `5` ...requirements. The rule requiring at least [5] airplanes is the main limit: relaxing it by...
5. `5` ...so it is what holds the airplane count at [5]. The 500-unit goods requirement also limits...
6. `500` ...is what holds the airplane count at 5. The [500]-unit goods requirement also limits the...
7. `15` ...it would improve the objective even though [15] units of capacity are spare. The rule that...

## 85177523

**Problem.** A nearby lake is frequently artificially seeded with trout for local fishermen. The trout are transported using either large trucks or by boat. Transporting using large trucks can take 2000 trout and costs $300 per trip. Transporting with boat can take 1200 trout and costs $100 per trip. Since boats take extra preparation, at least 75% of trips should be by large trucks. Additionally, there can be at most 5 trips by boat. If at least 7000 trout need to be seeded into the nearby lake, how many of each type of trip should be taken to minimize the total cost?

**Model.**
```
min 300*[large truck trips] + 100*[boat trips]
  demand: 2000*[large truck trips] + 1200*[boat trips] >= 7000
  truck_share: 0.25*[large truck trips] - 0.75*[boat trips] >= 0
  boat_limit: 1*[boat trips] <= 5
  large truck trips: integer, in [0, inf]
  boat trips: integer, in [0, inf]
```

**Facts.** objective 1000; values large truck trips = 3, boat trips = 1; slack demand: 200, truck_share: 0, boat_limit: 4; binding: truck_share; shadow prices none (a MIP)

**Explanation.**

Use 3 large-truck trips and 1 boat trip, which seeds more than the 7,000 trout needed (200 extra) at a total cost of $1000. The 75% truck requirement is fully used, so the plan sits right at that limit and can't shift more trips to boats. The 7,000-trout requirement also limits the result, even with 200 trout of spare capacity, because dropping it would change the best plan, though making it one unit stricter wouldn't help. The limit of 5 boat trips does not constrain the result, since only 1 boat trip is used and dropping the limit wouldn't improve the plan. The answer is limited to whole trips, so the plan can't be adjusted in fractions.

**Numbers.**

1. `3` ...[3] large-truck trips and 1 boat trip, which...
2. `1` ...3 large-truck trips and [1] boat trip, which seeds more than the 7,000...
3. `7,000` ...and 1 boat trip, which seeds more than the [7,000] trout needed (200 extra) at a total cost of...
4. `200` ...seeds more than the 7,000 trout needed ([200] extra) at a total cost of $1000. The 75%...
5. `$1000` ...trout needed (200 extra) at a total cost of [$1000]. The 75% truck requirement is fully used,...
6. `75%` ...(200 extra) at a total cost of $1000. The [75%] truck requirement is fully used, so the...
7. `7,000` ...and can't shift more trips to boats. The [7,000]-trout requirement also limits the result,...
8. `200` ...also limits the result, even with [200] trout of spare capacity, because dropping...
9. `5` ...unit stricter wouldn't help. The limit of [5] boat trips does not constrain the result,...
10. `1` ...does not constrain the result, since only [1] boat trip is used and dropping the limit...

## 439170086

**Problem.** A gas company can transport gas using a pipeline or by train. A pipeline can carry 8000 units of gas and a train can carry 2000 units of gas every day. Due to recent environmental changes, the number of trains used must be at least twice as many as the number of pipelines. If at least 1000000 units of gas needs to be transported every day, minimize the total number of pipelines and trains needed.

**Model.**
```
min 1*[pipelines] + 1*[trains]
  trains_at_least_twice_pipelines: 1*[trains] - 2*[pipelines] >= 0
  gas_transport_requirement: 8000*[pipelines] + 2000*[trains] >= 1e+06
  pipelines: integer, in [0, inf]
  trains: integer, in [0, inf]
```

**Facts.** objective 251; values pipelines = 83, trains = 168; slack trains_at_least_twice_pipelines: 2, gas_transport_requirement: 0; binding: gas_transport_requirement; shadow prices none (a MIP)

**Explanation.**

The plan is to run 83 pipelines and 168 trains, for a total of 251 units, which is the fewest combined pipelines and trains that still moves at least 1,000,000 units of gas per day. The gas requirement is fully used, so the plan just meets it. The rule that trains must be at least twice the pipelines has 2 spare, but it still limits the result: removing that rule would give a better total, so it is holding the answer in place. Raising the gas requirement's limit would not improve the result, but removing the requirement entirely would, so the gas target is the other real constraint on the plan.

**Numbers.**

1. `83` ...plan is to run [83] pipelines and 168 trains, for a total of...
2. `168` ...plan is to run 83 pipelines and [168] trains, for a total of 251 units, which is...
3. `251` ...83 pipelines and 168 trains, for a total of [251] units, which is the fewest combined...
4. `1,000,000` ...and trains that still moves at least [1,000,000] units of gas per day. The gas requirement...
5. `2` ...must be at least twice the pipelines has [2] spare, but it still limits the result:...

## -1846151655

**Problem.** A tea shop brews two types of teas; black and green tea. Brewing black tea takes 2 minutes and green tea 3 minutes. It takes 7 units of tea leaves and 15 units of filtered hot water to make a cup of black tea. It takes 5 units of tea leaves and 18 units of filtered hot water to make a cup of green tea. The owner of the tea shop has a deal with her distributer to acquire 700 units of tea leaves and 700 units of filtered hot water every week.  The tea shop also has a repeating customer in a Japanese restaurant to brew green tea for them. Therefore, the shop must brew at least four times more green tea than black tea. How many of each type of tea should be made to minimize the total time spent brewing tea?

**Model.**
```
min 2*[black tea cups] + 3*[green tea cups]
  tea leaves: 7*[black tea cups] + 5*[green tea cups] <= 700
  filtered hot water: 15*[black tea cups] + 18*[green tea cups] <= 700
  green to black ratio: 1*[green tea cups] - 4*[black tea cups] >= 0
  black tea cups: integer, in [0, inf]
  green tea cups: integer, in [0, inf]
```

**Facts.** objective 0; values black tea cups = 0, green tea cups = 0; slack tea leaves: 700, filtered hot water: 700, green to black ratio: 0; binding: green to black ratio; shadow prices none (a MIP)

**Explanation.**

The model's answer is to brew no tea at all: 0 black cups and 0 green cups, for a total brewing time of 0 minutes. The shop's 700 units of tea leaves and 700 units of filtered hot water both go unused. The green-to-black ratio constraint is exactly met (0 green cups for 0 black cups), but removing it or relaxing its limit would not improve the result, so none of the three constraints is what holds the answer at zero. The model has no minimum number of cups, so it can't account for the Japanese restaurant's order, and zero is the trivially cheapest plan. If the shop needs a required amount of green tea, that requirement has to be added before the result means anything.

**Numbers.**

1. `0` ...model's answer is to brew no tea at all: [0] black cups and 0 green cups, for a total...
2. `0` ...is to brew no tea at all: 0 black cups and [0] green cups, for a total brewing time of 0...
3. `0` ...0 green cups, for a total brewing time of [0] minutes. The shop's 700 units of tea leaves...
4. `700` ...total brewing time of 0 minutes. The shop's [700] units of tea leaves and 700 units of...
5. `700` ...The shop's 700 units of tea leaves and [700] units of filtered hot water both go unused....
6. `0` ...ratio constraint is exactly met ([0] green cups for 0 black cups), but removing...
7. `0` ...constraint is exactly met (0 green cups for [0] black cups), but removing it or relaxing...

## 987782367

**Problem.** A fitness trainer is scheduling her client to eat more fruits and vegetables to meet their vitamin and fiber requirements. A pack of fruits contains 4 units of vitamin and 7.5 units of fiber. A pack of vegetables contains 7 units of vitamin and 5 units of fiber. The client must meet their weekly minimum requirements of 100 units of vitamin and 120 units of fiber. In addition, because fruits contain more hydration, the client must eat at least twice as many packs of fruits as packs of vegetables. If a pack of fruits contains 3 units of sugar and a pack of vegetables contains 1 unit of sugar, how many of packs of each should the client consume to minimize their sugar intake?

**Model.**
```
min 3*[fruit packs] + 1*[vegetable packs]
  vitamin: 4*[fruit packs] + 7*[vegetable packs] >= 100
  fiber: 7.5*[fruit packs] + 5*[vegetable packs] >= 120
  hydration: 1*[fruit packs] - 2*[vegetable packs] >= 0
  fruit packs: integer, in [0, inf]
  vegetable packs: integer, in [0, inf]
```

**Facts.** objective 49; values fruit packs = 14, vegetable packs = 7; slack vitamin: 5, fiber: 20, hydration: 0; binding: hydration; shadow prices none (a MIP)

**Explanation.**

Have the client eat 14 packs of fruit and 7 packs of vegetables each week. This meets the vitamin and fiber minimums and the rule of at least twice as many fruit packs as vegetable packs, and it gives the lowest possible sugar intake of 49 units. The hydration rule is the main constraint: it is exactly met, and relaxing it by one unit would reduce sugar further. The vitamin requirement also limits the result, even though 5 units of vitamin are left over, because removing it would lower sugar, though adding one more unit of vitamin would not help. The fiber requirement does not limit the result, since it has 20 units to spare and dropping it would not improve the plan.

**Numbers.**

1. `14` ...the client eat [14] packs of fruit and 7 packs of vegetables...
2. `7` ...the client eat 14 packs of fruit and [7] packs of vegetables each week. This meets...
3. `49` ...gives the lowest possible sugar intake of [49] units. The hydration rule is the main...
4. `5` ...also limits the result, even though [5] units of vitamin are left over, because...
5. `20` ...does not limit the result, since it has [20] units to spare and dropping it would not...
