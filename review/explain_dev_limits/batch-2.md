# Explanation labels, batch 2 of 4

Label every numbered number `correct` or `wrong` in `labels-2.csv`, and every explanation's false claim `yes` or `no` in `claims-2.csv`, by the rules of docs/analysis/explanation_checker.md. This sheet doesn't show the checker's flags, on purpose.

## 892653388

**Problem.** A furniture store only stocks and sells dining tables and chairs. The profit per dining table is $350 and the profit per chair is $75. There is 500 sq ft of space available and a dining table requires 8 sq ft of floor space while a chair requires 2 sq ft. Because chairs sell in larger quantities, at least 70% of all furniture in the store must be chairs. In terms of capital, a dining table ties up $1000 in capital and a chair ties up $150 in capital. The company wants a maximum of $20000 worth of capital tied up at any time. Formulate an LP to maximize profit.

**Model.**
```
max 350*[dining tables] + 75*[chairs]
  floor space: 8*[dining tables] + 2*[chairs] <= 500
  chair share of furniture: -0.7*[dining tables] + 0.3*[chairs] >= 0
  capital: 1000*[dining tables] + 150*[chairs] <= 20000
  dining tables: integer, in [0, inf]
  chairs: integer, in [0, inf]
```

**Facts.** objective 9975; values dining tables = 0, chairs = 133; slack floor space: 234, chair share of furniture: 39.9, capital: 50; binding: none; shadow prices none (a MIP)

**Explanation.**

Stock no dining tables and 133 chairs. This gives a profit of $9,975, the best the model finds with whole-number quantities. The floor space and the chair-share rule (at least 70% chairs) don't hold the result back, since leaving either one out or loosening it would not raise profit. The capital limit does constrain the result, even though $50 of it is unused: removing that limit would improve profit, but raising it by one unit would not, because whole-number quantities can't use a small amount of extra capital.

**Numbers.**

1. `133` ...no dining tables and [133] chairs. This gives a profit of $9,975, the...
2. `$9,975,` ...and 133 chairs. This gives a profit of [$9,975,] the best the model finds with whole-number...
3. `70%` ...space and the chair-share rule (at least [70%] chairs) don't hold the result back, since...
4. `$50` ...does constrain the result, even though [$50] of it is unused: removing that limit would...

## -176363722

**Problem.** A suit store makes 2-piece and 3-piece suits. To make a 2-piece suit requires 1 hour of measuring and 4 hours of stitching. To make a 3-piece suit requires 2 hours of measuring and 5 hours of stitching. The store has 150 hours of measuring time and 300 hours of stitching time available. In order to stay in business, at least 40 2-piece suites should be made. The profit per 2-piece suit is $600 and the profit per 3-piece suit is $800. Formulate a LP to maximize profit?

**Model.**
```
max 600*[2-piece suits] + 800*[3-piece suits]
  measuring_hours: 1*[2-piece suits] + 2*[3-piece suits] <= 150
  stitching_hours: 4*[2-piece suits] + 5*[3-piece suits] <= 300
  min_two_piece_suits: 1*[2-piece suits] >= 40
  2-piece suits: integer, in [0, inf]
  3-piece suits: integer, in [0, inf]
```

**Facts.** objective 46400; values 2-piece suits = 40, 3-piece suits = 28; slack measuring_hours: 54, stitching_hours: 0, min_two_piece_suits: 0; binding: stitching_hours, min_two_piece_suits; shadow prices none (a MIP)

**Explanation.**

Make 40 two-piece suits and 28 three-piece suits. This gives a profit of $46,400, the highest the model allows under whole-number production. Stitching time is fully used at 300 hours, and the store must make at least 40 two-piece suits, which this plan meets exactly. Measuring time has 54 hours left over, and removing that rule would not improve the result, so it is not what limits profit. Both stitching time and the 40-suit minimum do limit profit: removing either one would let the model do better, and making one more unit of either would not help.

**Numbers.**

1. `40` ...[40] two-piece suits and 28 three-piece suits....
2. `28` ...40 two-piece suits and [28] three-piece suits. This gives a profit of...
3. `$46,400,` ...three-piece suits. This gives a profit of [$46,400,] the highest the model allows under...
4. `300` ...production. Stitching time is fully used at [300] hours, and the store must make at least 40...
5. `40` ...300 hours, and the store must make at least [40] two-piece suits, which this plan meets...
6. `54` ...this plan meets exactly. Measuring time has [54] hours left over, and removing that rule...
7. `40` ...limits profit. Both stitching time and the [40]-suit minimum do limit profit: removing...

## -580767881

**Problem.** The Vision Corporation manufactures two models of monitors: Aleph 3 and Gilgamesh Supreme. They share a similar manufacturing process in that they both require a certain amount of assembly and packaging. Each Aleph 3 monitor takes 2 hours of assembly and each Gilgamesh Supreme requires 2.5 hours of assembly. They both require 0.5 hours of packaging time per unit. During the next season, 5000 hours of assembly time are available and at most 2500 hours of packaging time may be used. Each Aleph 3 sold yields a profit of $1500. Each Gilgamesh Supreme sold yields a profit of $2500 profit. Formulate and solve this LP problem and find the best combination of monitors that yields the highest profit.

**Model.**
```
max 1500*[Aleph 3 monitors] + 2500*[Gilgamesh Supreme monitors]
  assembly hours: 2*[Aleph 3 monitors] + 2.5*[Gilgamesh Supreme monitors] <= 5000
  packaging hours: 0.5*[Aleph 3 monitors] + 0.5*[Gilgamesh Supreme monitors] <= 2500
  Aleph 3 monitors: integer, in [0, inf]
  Gilgamesh Supreme monitors: integer, in [0, inf]
```

**Facts.** objective 5e+06; values Aleph 3 monitors = 0, Gilgamesh Supreme monitors = 2000; slack assembly hours: 0, packaging hours: 1500; binding: assembly hours; shadow prices none (a MIP)

**Explanation.**

Make 2,000 Gilgamesh Supreme monitors and no Aleph 3 monitors. This plan yields the highest profit, $5,000,000. Assembly hours are fully used, and 1,500 packaging hours are left over. Assembly time is the constraint that limits the result: removing it would improve the profit, even though one more assembly hour would not improve it under the whole-number requirement. Packaging time does not limit the result, so the spare packaging hours have no effect on profit.

**Numbers.**

1. `2,000` ...[2,000] Gilgamesh Supreme monitors and no Aleph 3...
2. `3` ...Gilgamesh Supreme monitors and no Aleph [3] monitors. This plan yields the highest...
3. `$5,000,000` ...This plan yields the highest profit, [$5,000,000]. Assembly hours are fully used, and 1,500...
4. `1,500` ...Assembly hours are fully used, and [1,500] packaging hours are left over. Assembly...

## -934921495

**Problem.** A fashion company produces two types of nail paints, gel and acrylic. The profit per unit of gel is $80 and the profit per unit of acrylic is $200. It takes 4 hours to produce the raw materials for one unit of gel, 3 hour to mix and 6 hours in packing. It takes 2 hours to produce the raw materials for one unit of acrylic, 5 hour to mix and 2.3 hours in packing. Per month, 290 hours are available for preparing the raw materials, 480 hours for mixing and 510 hours for packing the nail paints.  How many of each type of nail paint should be produced in order to maximize the total monthly profit?

**Model.**
```
max 80*[gel nail paint units] + 200*[acrylic nail paint units]
  raw material hours: 4*[gel nail paint units] + 2*[acrylic nail paint units] <= 290
  mixing hours: 3*[gel nail paint units] + 5*[acrylic nail paint units] <= 480
  packing hours: 6*[gel nail paint units] + 2.3*[acrylic nail paint units] <= 510
  gel nail paint units: integer, in [0, inf]
  acrylic nail paint units: integer, in [0, inf]
```

**Facts.** objective 19200; values gel nail paint units = 0, acrylic nail paint units = 96; slack raw material hours: 98, mixing hours: 0, packing hours: 289.2; binding: mixing hours; shadow prices none (a MIP)

**Explanation.**

Make 96 acrylic nail paints and no gel paints, for a monthly profit of $19,200. The mixing hours are fully used, and that is the constraint that caps production. Raw material hours (98 left over) and packing hours (289.2 left over) don't limit the result, since removing either one wouldn't improve the outcome. Mixing hours do limit it: removing that limit would let the solver find a better plan, and adding one more mixing hour wouldn't improve the whole-unit answer.

**Numbers.**

1. `96` ...[96] acrylic nail paints and no gel paints, for...
2. `$19,200` ...and no gel paints, for a monthly profit of [$19,200]. The mixing hours are fully used, and that...
3. `98` ...that caps production. Raw material hours ([98] left over) and packing hours (289.2 left...
4. `289.2` ...hours (98 left over) and packing hours ([289.2] left over) don't limit the result, since...

## 1670020945

**Problem.** An electronics company makes economical and premium mobile phones in a factory that is divided into a hardware and software section. The hardware section must work 5 hours on each economical mobile phone but 12 hours on each premium one. The software section must work 3 hours for each mobile phone. The profit from the economical mobile phone is $150 and the profit from the premium mobile phone is $400. Due to a recent strike, the hardware section only has 150 hours available per week and the software section only has 100 hours available per week. How many of each phone should the company produce to maximize profit?

**Model.**
```
max 150*[economical phones] + 400*[premium phones]
  hardware hours: 5*[economical phones] + 12*[premium phones] <= 150
  software hours: 3*[economical phones] + 3*[premium phones] <= 100
  economical phones: integer, in [0, inf]
  premium phones: integer, in [0, inf]
```

**Facts.** objective 4950; values economical phones = 1, premium phones = 12; slack hardware hours: 1, software hours: 61; binding: none; shadow prices none (a MIP)

**Explanation.**

The company should make 1 economical phone and 12 premium phones each week, for a profit of $4950. Hardware hours are the real bottleneck: the hardware constraint still limits the result even though 1 hour is left over, because removing that limit would improve the outcome. However, adding one more hour of hardware time would not raise profit, since the whole-number requirement leaves that spare hour unusable. Software hours do not limit the result, with 61 hours going unused.

**Numbers.**

1. `1` ...company should make [1] economical phone and 12 premium phones each...
2. `12` ...company should make 1 economical phone and [12] premium phones each week, for a profit of...
3. `$4950` ...premium phones each week, for a profit of [$4950]. Hardware hours are the real bottleneck:...
4. `1` ...still limits the result even though [1] hour is left over, because removing that...
5. `61` ...hours do not limit the result, with [61] hours going...

## 1319496932

**Problem.** A company makes raincoats and umbrellas with images of Latin alphabet on them using a printing machine. Due to the popularity of Latin alphabet, the company must make at least 1200 raincoats or umbrellas, in any combination, per week. Also, in one week, the printing machine must be kept running for at least 70 hours. A raincoat takes 0.3 hours of printing time and costs $7. An umbrella takes 0.5 hours of printing time and costs $12. Formulate this problem so as to minimize total production costs.

**Model.**
```
min 7*[raincoats] + 12*[umbrellas]
  total_output: 1*[raincoats] + 1*[umbrellas] >= 1200
  machine_hours: 0.3*[raincoats] + 0.5*[umbrellas] >= 70
  raincoats: integer, in [0, inf]
  umbrellas: integer, in [0, inf]
```

**Facts.** objective 8400; values raincoats = 1200, umbrellas = 0; slack total_output: 0, machine_hours: 290; binding: total_output; shadow prices none (a MIP)

**Explanation.**

The best plan is to make 1,200 raincoats and no umbrellas, which gives the lowest total production cost of $8,400. This meets the weekly requirement of at least 1,200 items exactly, and raincoats are the cheaper item at $7 each versus $12 for umbrellas. The machine-hours requirement of at least 70 hours has 290 hours of slack, and the model says it does not limit the result, so the plan comfortably keeps the machine running. The 1,200-item minimum is what limits the result: the model says that lowering it would reduce cost, so the company's costs depend on that order requirement. Because the model uses whole-number quantities, these conclusions come from re-solving the model, not from the slack figures alone.

**Numbers.**

1. `1,200` ...best plan is to make [1,200] raincoats and no umbrellas, which gives the...
2. `$8,400` ...gives the lowest total production cost of [$8,400]. This meets the weekly requirement of at...
3. `1,200` ...meets the weekly requirement of at least [1,200] items exactly, and raincoats are the...
4. `$7` ...and raincoats are the cheaper item at [$7] each versus $12 for umbrellas. The...
5. `$12` ...are the cheaper item at $7 each versus [$12] for umbrellas. The machine-hours...
6. `70` ...The machine-hours requirement of at least [70] hours has 290 hours of slack, and the model...
7. `290` ...requirement of at least 70 hours has [290] hours of slack, and the model says it does...
8. `1,200` ...comfortably keeps the machine running. The [1,200]-item minimum is what limits the result: the...

## 690843809

**Problem.** A florist can deliver their flowers either by car or by truck. A car can deliver 6 units of flowers and uses 10 units of gas. A truck can deliver 9 units of flowers and uses 14 units of gas. The florist needs to deliver at least 130 units of flowers. Additionally, the number of cars used must exceed the number of trucks used. How many of each should be used to minimize the total amount of gas used?

**Model.**
```
min 10*[cars] + 14*[trucks]
  flower_delivery: 6*[cars] + 9*[trucks] >= 130
  cars_exceed_trucks: 1*[cars] - 1*[trucks] >= 1
  cars: integer, in [0, inf]
  trucks: integer, in [0, inf]
```

**Facts.** objective 212; values cars = 10, trucks = 8; slack flower_delivery: 2, cars_exceed_trucks: 1; binding: none; shadow prices none (a MIP)

**Explanation.**

Send 10 cars and 8 trucks, which uses the minimum of 212 units of gas that the model finds while meeting the flower requirement. This plan delivers at least 130 units with 2 units to spare, and it keeps cars above trucks by the required margin. Both rules limit the result: the objective would improve if the flower requirement were dropped or raised by one unit, and it would also improve if the cars-exceed-trucks rule were dropped. That rule has 1 unit of slack, but raising its limit wouldn't help, so the slack alone doesn't show that it's limiting the answer. Because the vehicles come in whole units, these re-solves are a more reliable guide than the slack amounts.

**Numbers.**

1. `10` ...[10] cars and 8 trucks, which uses the minimum...
2. `8` ...10 cars and [8] trucks, which uses the minimum of 212 units...
3. `212` ...and 8 trucks, which uses the minimum of [212] units of gas that the model finds while...
4. `130` ...requirement. This plan delivers at least [130] units with 2 units to spare, and it keeps...
5. `2` ...This plan delivers at least 130 units with [2] units to spare, and it keeps cars above...
6. `1` ...rule were dropped. That rule has [1] unit of slack, but raising its limit...

## -1303541177

**Problem.** A physics class is performing a volcano experiment using two mixtures, mixture A and mixture B. Mixture A uses 3 units of baking soda, 5 units of vinegar, and produces 2 units of eruption. Mixture B uses 4 units of baking soda, 7 units of vinegar, and produces 4 units of eruption. However, mixture A generates 2 units of garbage and mixture B generates 1 unit of garbage. The physics class has available 200 units of baking soda and 300 units of vinegar. If at most 60 units of garbage can be generated, how many of each type of mixture should be used to maximize the total amount of eruption produced?

**Model.**
```
max 2*[mixture A batches] + 4*[mixture B batches]
  baking soda: 3*[mixture A batches] + 4*[mixture B batches] <= 200
  vinegar: 5*[mixture A batches] + 7*[mixture B batches] <= 300
  garbage: 2*[mixture A batches] + 1*[mixture B batches] <= 60
  mixture A batches: continuous, in [0, inf]
  mixture B batches: continuous, in [0, inf]
```

**Facts.** objective 171.429; values mixture A batches = 0, mixture B batches = 42.8571; slack baking soda: 28.5714, vinegar: -1e-06, garbage: 17.1429; binding: vinegar; shadow prices baking soda: 0, vinegar: 0.571429, garbage: 0

**Explanation.**

Make no batches of mixture A and about 42.86 batches of mixture B. This gives the largest total eruption, about 171.43 units. Vinegar is the limiting ingredient: all 300 units are used, so it caps the result. Each extra unit of vinegar would add about 0.57 units of eruption, while the leftover baking soda (about 28.57 units) and garbage allowance (about 17.14 units) would not help on their own.

**Numbers.**

1. `42.86` ...no batches of mixture A and about [42.86] batches of mixture B. This gives the...
2. `171.43` ...gives the largest total eruption, about [171.43] units. Vinegar is the limiting ingredient:...
3. `300` ...Vinegar is the limiting ingredient: all [300] units are used, so it caps the result. Each...
4. `0.57` ...Each extra unit of vinegar would add about [0.57] units of eruption, while the leftover...
5. `28.57` ...while the leftover baking soda (about [28.57] units) and garbage allowance (about 17.14...
6. `17.14` ...28.57 units) and garbage allowance (about [17.14] units) would not help on their...

## 648491494

**Problem.** An airport can transport travelers using commercial planes and private planes. A commercial plane can carry 180 travelers while a private plane can carry 30 travelers. Because the destination is more remote, there are few airport runways. Therefore, there must be twice as many private planes as commercial planes. If the airport needs to transport at least 3500 travelers, how many of each type of planes should be used to minimize the total number of planes used.

**Model.**
```
min 1*[commercial planes] + 1*[private planes]
  travelers: 180*[commercial planes] + 30*[private planes] >= 3500
  private to commercial ratio: 1*[private planes] - 2*[commercial planes] == 0
  commercial planes: integer, in [0, inf]
  private planes: integer, in [0, inf]
```

**Facts.** objective 45; values commercial planes = 15, private planes = 30; slack travelers: 100, private to commercial ratio: 0; binding: private to commercial ratio; shadow prices none (a MIP)

**Explanation.**

Use **15 commercial planes and 30 private planes**, for a total of **45 planes**, the fewest that meets the traveler requirement while keeping private planes at twice the number of commercial ones. This plan carries the 3,500 travelers needed, with 100 seats of spare capacity. The twice-as-many-private-planes rule is fully used, so it is what fixes the mix. Both the traveler requirement and that ratio rule limit the result: removing either would allow a better plan, even though the traveler requirement has 100 spare capacity. Raising the traveler requirement by one would not help, but the ratio rule's effect on loosening is unclear from the solution.

**Numbers.**

1. `15` ...**[15] commercial planes and 30 private planes**,...
2. `30` ...**15 commercial planes and [30] private planes**, for a total of **45...
3. `45` ...and 30 private planes**, for a total of **[45] planes**, the fewest that meets the...
4. `3,500` ...of commercial ones. This plan carries the [3,500] travelers needed, with 100 seats of spare...
5. `100` ...carries the 3,500 travelers needed, with [100] seats of spare capacity. The...
6. `100` ...even though the traveler requirement has [100] spare capacity. Raising the traveler...

## 343813684

**Problem.** An MOA checks a patient’s eye pressure one-by-one either by using a tonometer or a “puff of air” test. The tonometer test takes 0.05 hours to make a reading while the ”puff of air” test takes 0.02 hours to make a reading. Since the tonometer is more standard, the number of tonometer tests must be larger than the number of “puff of air” tests. Since a lot of these patients are low risk here for a check-up, at least 30 patients should have their eye pressure checked using the “puff of air” test. If the office is open for 8 hours, maximize the number of patients whose temperature can be taken?

**Model.**
```
max 1*[tonometer tests] + 1*[puff of air tests]
  office hours: 0.05*[tonometer tests] + 0.02*[puff of air tests] <= 8
  more tonometer than puff tests: 1*[tonometer tests] - 1*[puff of air tests] >= 1
  minimum puff of air tests: 1*[puff of air tests] >= 30
  tonometer tests: integer, in [0, inf]
  puff of air tests: integer, in [0, inf]
```

**Facts.** objective 227; values tonometer tests = 115, puff of air tests = 112; slack office hours: 0.01, more tonometer than puff tests: 2, minimum puff of air tests: 82; binding: none; shadow prices none (a MIP)

**Explanation.**

Schedule 115 tonometer tests and 112 "puff of air" tests, for a total of 227 patients. The office-hours limit is a real constraint: the 8-hour day is almost fully used (0.01 hours left), and adding more time would allow more patients. The rule that tonometer tests must exceed puff tests also limits the result, and relaxing it would help even though 2 tests of room remain. The minimum of 30 puff tests does not limit the result, since the plan uses 112, and removing that requirement would not improve the total. Note that the model counts eye-pressure checks, while the question asks about temperature checks, so the 227 applies to eye-pressure patients.

**Numbers.**

1. `115` ...[115] tonometer tests and 112 "puff of air"...
2. `112` ...115 tonometer tests and [112] "puff of air" tests, for a total of 227...
3. `227` ...and 112 "puff of air" tests, for a total of [227] patients. The office-hours limit is a real...
4. `8` ...limit is a real constraint: the [8]-hour day is almost fully used (0.01 hours...
5. `0.01` ...the 8-hour day is almost fully used ([0.01] hours left), and adding more time would...
6. `2` ...and relaxing it would help even though [2] tests of room remain. The minimum of 30...
7. `30` ...2 tests of room remain. The minimum of [30] puff tests does not limit the result, since...
8. `112,` ...not limit the result, since the plan uses [112,] and removing that requirement would not...
9. `227` ...asks about temperature checks, so the [227] applies to eye-pressure...

## 1367844202

**Problem.** A tutoring company hires full-time tutors and supplements with assistant tutors from a nearby high school. Every day, full-time tutors work 8 hours and get paid $650 while assistant tutors work 4 hours and get paid $120. During Christmas break, the tutoring company expects more interest and plans to require 1200 hours of teaching availability. If the tutoring company has a budget of $55000, how many tutors and assistant tutors should be hired to minimize the amount of staff?

**Model.**
```
min 1*[full-time tutors] + 1*[assistant tutors]
  teaching hours: 8*[full-time tutors] + 4*[assistant tutors] >= 1200
  budget: 650*[full-time tutors] + 120*[assistant tutors] <= 55000
  full-time tutors: integer, in [0, inf]
  assistant tutors: integer, in [0, inf]
```

**Facts.** objective 254; values full-time tutors = 46, assistant tutors = 208; slack teaching hours: 0, budget: 140; binding: teaching hours; shadow prices none (a MIP)

**Explanation.**

Hire 46 full-time tutors and 208 assistant tutors, for 254 staff in total, which is the smallest headcount that still meets the Christmas-break need. This covers the required 1200 teaching hours exactly and stays within the $55,000 budget, with $140 to spare. The teaching-hours requirement is the main limit: it is fully used, and dropping it would change the result, so the hours target is what sets the headcount. The budget also limits the result even though $140 is left unused: removing the budget limit would improve the outcome, while raising the budget by one unit would not help, because whole-number hiring makes the leftover money too small to matter. Since the model requires whole numbers of people, the budget and hours limits interact, so the plan should be treated as the best whole-number mix, not an exact fractional one.

**Numbers.**

1. `46` ...[46] full-time tutors and 208 assistant tutors,...
2. `208` ...46 full-time tutors and [208] assistant tutors, for 254 staff in total,...
3. `254` ...tutors and 208 assistant tutors, for [254] staff in total, which is the smallest...
4. `1200` ...need. This covers the required [1200] teaching hours exactly and stays within the...
5. `$55,000` ...teaching hours exactly and stays within the [$55,000] budget, with $140 to spare. The...
6. `$140` ...and stays within the $55,000 budget, with [$140] to spare. The teaching-hours requirement is...
7. `$140` ...budget also limits the result even though [$140] is left unused: removing the budget limit...

## -1003923679

**Problem.** An athlete drinks protein shakes in the morning before a workout and is planning for the coming month. She has two selections of protein shakes, chocolate powder or vanilla powder shakes. Each scoop of chocolate powder protein shake contains 20 grams of protein and 4 grams of sugar. Each scoop of vanilla powder protein shake contains 18 grams of protein and 7 grams of sugar. Since she prefers the vanilla flavour, she would like to drink at least twice as many vanilla powder shakes as chocolate powder shakes. However, she must also drink at least 2 scoops of the chocolate powder shake. To avoid high blood glucose levels, she is limiting her consumption to at most 500 grams of sugar over this period of time. How many of each protein shake should the athlete drink to maximize her total protein intake over this period of time?

**Model.**
```
max 20*[chocolate powder scoops] + 18*[vanilla powder scoops]
  vanilla at least twice chocolate: 1*[vanilla powder scoops] - 2*[chocolate powder scoops] >= 0
  minimum chocolate scoops: 1*[chocolate powder scoops] >= 2
  sugar limit: 4*[chocolate powder scoops] + 7*[vanilla powder scoops] <= 500
  chocolate powder scoops: integer, in [0, inf]
  vanilla powder scoops: integer, in [0, inf]
```

**Facts.** objective 1548; values chocolate powder scoops = 27, vanilla powder scoops = 56; slack vanilla at least twice chocolate: 2, minimum chocolate scoops: 25, sugar limit: 0; binding: sugar limit; shadow prices none (a MIP)

**Explanation.**

Drink 27 scoops of chocolate powder and 56 scoops of vanilla powder over the month. This gives the most protein possible, 1548 grams, while staying exactly at the 500-gram sugar cap. The sugar limit is the main constraint: raising the cap by one gram would not help because scoops come in whole units, but removing the limit would raise the protein total, so it is what holds the result back. The rule that vanilla must be at least twice the chocolate also limits the result, even though 2 scoops of slack remain, since dropping it would improve the total. The minimum of 2 chocolate scoops does not limit the result.

**Numbers.**

1. `27` ...[27] scoops of chocolate powder and 56 scoops of...
2. `56` ...27 scoops of chocolate powder and [56] scoops of vanilla powder over the month....
3. `1548` ...This gives the most protein possible, [1548] grams, while staying exactly at the...
4. `500` ...1548 grams, while staying exactly at the [500]-gram sugar cap. The sugar limit is the main...
5. `2` ...also limits the result, even though [2] scoops of slack remain, since dropping it...
6. `2` ...it would improve the total. The minimum of [2] chocolate scoops does not limit the...

## 1426711389

**Problem.** A manufacturing plant has the option to offer a shuttle bus and outsource to a taxi service. A shuttle bus costs $20 and carries 7 workers, whereas a taxi service costs $50 and carries 5 workers. The manufacturing plant has to transport at least 250 workers and at most 5 shuttle buses can be used. How many of each type of transport should be taken to minimize the total cost?

**Model.**
```
min 20*[shuttle buses] + 50*[taxis]
  worker transport requirement: 7*[shuttle buses] + 5*[taxis] >= 250
  shuttle bus limit: 1*[shuttle buses] <= 5
  shuttle buses: integer, in [0, inf]
  taxis: integer, in [0, inf]
```

**Facts.** objective 2250; values shuttle buses = 5, taxis = 43; slack worker transport requirement: 0, shuttle bus limit: 0; binding: worker transport requirement, shuttle bus limit; shadow prices none (a MIP)

**Explanation.**

Run 5 shuttle buses and 43 taxis, which covers all 250 workers (35 on buses plus 215 in taxis) for a total cost of $2250. Both the worker requirement and the 5-bus cap are fully used, and the cap is the limit that matters most: raising it would lower the cost. The worker requirement also limits the result. Adding one more worker to the requirement wouldn't reduce cost, but dropping the requirement entirely would, so it is what keeps the cost from being lower. Because the model requires whole vehicles, the plan is only as good as these two limits allow.

**Numbers.**

1. `5` ...[5] shuttle buses and 43 taxis, which covers...
2. `43` ...5 shuttle buses and [43] taxis, which covers all 250 workers (35 on...
3. `250` ...buses and 43 taxis, which covers all [250] workers (35 on buses plus 215 in taxis) for...
4. `35` ...and 43 taxis, which covers all 250 workers ([35] on buses plus 215 in taxis) for a total...
5. `215` ...covers all 250 workers (35 on buses plus [215] in taxis) for a total cost of $2250. Both...
6. `$2250` ...plus 215 in taxis) for a total cost of [$2250]. Both the worker requirement and the 5-bus...
7. `5` ...$2250. Both the worker requirement and the [5]-bus cap are fully used, and the cap is the...

## -188754660

**Problem.** A water purification station has a large plant and a small plant. The large plant purifies 30 units of water per hour and produces 20 units of by-product per hour. The small plant purifies 12 units of water per hour and produces 2 units of by-product per hour. The large plant requires 15 filters while the small plant requires 12 filters per hour. The water purification station only has available 1200 filters right now. If the station must purify at least 1200 units of water and at least 500 units of by-product, how many hours should each plant be run to minimize the total time needed?

**Model.**
```
min 1*[large_plant_hours] + 1*[small_plant_hours]
  water_purified: 30*[large_plant_hours] + 12*[small_plant_hours] >= 1200
  by_product: 20*[large_plant_hours] + 2*[small_plant_hours] >= 500
  filters_available: 15*[large_plant_hours] + 12*[small_plant_hours] <= 1200
  large_plant_hours: continuous, in [0, inf]
  small_plant_hours: continuous, in [0, inf]
```

**Facts.** objective 40; values large_plant_hours = 40, small_plant_hours = 0; slack water_purified: 0, by_product: 300, filters_available: 600; binding: water_purified; shadow prices water_purified: 0.033333, by_product: 0, filters_available: 0

**Explanation.**

Run the large plant for 40 hours and keep the small plant off (0 hours), which gives the shortest total time of 40 hours. This schedule exactly meets the requirement of 1200 units of water, so the water target is the limiting factor. The by-product requirement is met with 300 units to spare, and 600 filters remain unused, so neither of those limits the schedule. Each extra unit of water required would add about 0.033333 hours to the total.

**Numbers.**

1. `40` ...the large plant for [40] hours and keep the small plant off (0...
2. `0` ...for 40 hours and keep the small plant off ([0] hours), which gives the shortest total time...
3. `40` ...which gives the shortest total time of [40] hours. This schedule exactly meets the...
4. `1200` ...schedule exactly meets the requirement of [1200] units of water, so the water target is the...
5. `300` ...The by-product requirement is met with [300] units to spare, and 600 filters remain...
6. `600` ...is met with 300 units to spare, and [600] filters remain unused, so neither of those...
7. `0.033333` ...unit of water required would add about [0.033333] hours to the...

## -206261087

**Problem.** A doctor can prescribe two types of medication for high glucose levels, a diabetic pill and a diabetic shot. Per dose, diabetic pill delivers 1 unit of glucose reducing medicine and 2 units of blood pressure reducing medicine. Per dose, a diabetic shot delivers 2 units of glucose reducing medicine and 3 units of blood pressure reducing medicine. In addition, diabetic pills provide 0.4 units of stress and the diabetic shot provides 0.9 units of stress. At most 20 units of stress can be applied over a week and the doctor must deliver at least 30 units of glucose reducing medicine. How many doses of each should be delivered to maximize the amount of blood pressure reducing medicine delivaered to the patient?

**Model.**
```
max 2*[diabetic pill doses] + 3*[diabetic shot doses]
  stress: 0.4*[diabetic pill doses] + 0.9*[diabetic shot doses] <= 20
  glucose: 1*[diabetic pill doses] + 2*[diabetic shot doses] >= 30
  diabetic pill doses: integer, in [0, inf]
  diabetic shot doses: integer, in [0, inf]
```

**Facts.** objective 100; values diabetic pill doses = 50, diabetic shot doses = 0; slack stress: 0, glucose: 20; binding: stress; shadow prices none (a MIP)

**Explanation.**

Prescribe 50 diabetic pill doses and no diabetic shots. This delivers 100 units of blood pressure reducing medicine, the most the model allows. The weekly stress cap of 20 units is fully used, and it is what limits the result: dropping that cap would improve the outcome, and so would relaxing it by one unit. The glucose requirement does not limit the result, since removing it would not help and neither would loosening it, and the plan already delivers 20 units more glucose medicine than required.

**Numbers.**

1. `50` ...[50] diabetic pill doses and no diabetic shots....
2. `100` ...doses and no diabetic shots. This delivers [100] units of blood pressure reducing medicine,...
3. `20` ...the model allows. The weekly stress cap of [20] units is fully used, and it is what limits...
4. `20` ...loosening it, and the plan already delivers [20] units more glucose medicine than...

## -659035994

**Problem.** A chemist is performing novel research to create element A using two known methods: the gamma experiment and the omega experiment. The gamma experiment creates 12 units of element A and uses 3 units of electricity, 6 units of copper, and 3 minutes. The omega experiment creates 16 units of element A and uses 2 units of electricity, 9 units of copper, and 1 minutes. The chemist has available 1000 minutes, 4200 units of copper, and 1100 units of electricity. How many of each experiment should the chemist perform to maximize the total amount of element A produced?

**Model.**
```
max 12*[gamma experiments performed] + 16*[omega experiments performed]
  electricity: 3*[gamma experiments performed] + 2*[omega experiments performed] <= 1100
  copper: 6*[gamma experiments performed] + 9*[omega experiments performed] <= 4200
  time: 3*[gamma experiments performed] + 1*[omega experiments performed] <= 1000
  gamma experiments performed: integer, in [0, inf]
  omega experiments performed: integer, in [0, inf]
```

**Facts.** objective 7600; values gamma experiments performed = 100, omega experiments performed = 400; slack electricity: 0, copper: 0, time: 300; binding: electricity, copper; shadow prices none (a MIP)

**Explanation.**

Perform 100 gamma experiments and 400 omega experiments, which produces 7600 units of element A. Electricity and copper are fully used, and together they cap the result. Dropping either limit would allow a better total, so both are real constraints. Adding one more unit to either limit would not raise the total, because whole experiments can't use a fraction of a unit. The time limit is not what holds the result back, since 300 minutes remain unused.

**Numbers.**

1. `100` ...[100] gamma experiments and 400 omega...
2. `400` ...100 gamma experiments and [400] omega experiments, which produces 7600...
3. `7600` ...and 400 omega experiments, which produces [7600] units of element A. Electricity and copper...
4. `300` ...is not what holds the result back, since [300] minutes remain...

## -537539268

**Problem.** A popular coffee shop has coffee and cappuccinos. Each coffee requires 8 units of milk and 2 units of water. Each cappuccino requires 7 units of cream and 4 units of water. The coffee shop purchases a total of 3300 units of milk and 2600 units of cream. Regulars like the coffee and at least thirty percent of drinks must be coffee. However, cappuccinos make more profit, and the owner wants to sell more cappuccino than coffee. Since the town is in a water shortage, how many of each drink should be made to minimize the total amount of water needed?

**Model.**
```
min 2*[coffee drinks] + 4*[cappuccino drinks]
  milk: 8*[coffee drinks] <= 3300
  cream: 7*[cappuccino drinks] <= 2600
  at least 30% coffee: 0.7*[coffee drinks] - 0.3*[cappuccino drinks] >= 0
  more cappuccino than coffee: 1*[cappuccino drinks] - 1*[coffee drinks] >= 1
  coffee drinks: integer, in [0, inf]
  cappuccino drinks: integer, in [0, inf]
```

**Facts.** objective 10; values coffee drinks = 1, cappuccino drinks = 2; slack milk: 3292, cream: 2586, at least 30% coffee: 0.1, more cappuccino than coffee: 0; binding: more cappuccino than coffee; shadow prices none (a MIP)

**Explanation.**

The shop should make 1 coffee and 2 cappuccinos, which uses the least water possible: 10 units in total. Milk and cream are not what holds this result back, since they have plenty of room left and removing or loosening those limits would not change it. The two drink-mix rules do limit the result, even though they are not fully used up. The "more cappuccino than coffee" rule is fully used, and dropping it would give a better (lower) water total, so the owner would need to accept fewer cappuccinos to reach the minimum. The "at least 30% coffee" rule also limits the result, and loosening it would improve the outcome too.

**Numbers.**

1. `1` ...shop should make [1] coffee and 2 cappuccinos, which uses the...
2. `2` ...shop should make 1 coffee and [2] cappuccinos, which uses the least water...
3. `10` ...which uses the least water possible: [10] units in total. Milk and cream are not what...
4. `30%` ...to reach the minimum. The "at least [30%] coffee" rule also limits the result, and...

## -1292542531

**Problem.** A hospital gives pupil dilation drops using two types of dilation drops, fast-acting eye drops and slow-acting eye drops. The fast-acting eye drops take 5 minutes per patient to adjust the patient’s pupils while the slow-acting eye drops take 25 minutes per patient. Since the fast-acting eye drops are more expensive, at least twice as many patients must be dilated using the slow-acting eye drops than the fast-acting eye drops. However, at least 25 patients must be dilated with the fast-acting eye drops. If the clinic is open for 15000 minutes, maximize the number of patients that can be dilated.

**Model.**
```
max 1*[fast-acting drop patients] + 1*[slow-acting drop patients]
  slow_at_least_twice_fast: 1*[slow-acting drop patients] - 2*[fast-acting drop patients] >= 0
  fast_minimum: 1*[fast-acting drop patients] >= 25
  clinic_time: 5*[fast-acting drop patients] + 25*[slow-acting drop patients] <= 15000
  fast-acting drop patients: integer, in [0, inf]
  slow-acting drop patients: integer, in [0, inf]
```

**Facts.** objective 817; values fast-acting drop patients = 272, slow-acting drop patients = 545; slack slow_at_least_twice_fast: 1, fast_minimum: 247, clinic_time: 15; binding: none; shadow prices none (a MIP)

**Explanation.**

Use 272 fast-acting and 545 slow-acting drops, which dilates 817 patients, the most this model allows. The clinic-time limit restricts the result: removing it would produce a better total, but adding one more minute would not, because patients come in whole numbers. The rule that slow-acting drops must be at least twice the fast-acting count also restricts the result, even though it has 1 patient of slack. The minimum of 25 fast-acting patients does not restrict the result, since dropping or loosening it would not improve the total.

**Numbers.**

1. `272` ...[272] fast-acting and 545 slow-acting drops,...
2. `545` ...272 fast-acting and [545] slow-acting drops, which dilates 817...
3. `817` ...and 545 slow-acting drops, which dilates [817] patients, the most this model allows. The...
4. `1` ...restricts the result, even though it has [1] patient of slack. The minimum of 25...
5. `25` ...it has 1 patient of slack. The minimum of [25] fast-acting patients does not restrict the...

## -1873921235

**Problem.** In the North, a delivery service can deliver using either sleds or snowmobile. Snowmobiles can deliver 150 packages while sleds can deliver 125 packages. Most villages do not want snowmobiles to pollute their regions. Therefore, there must be at least two times more sleds than snowmobiles. If the delivery service wants to deliver 150000 packages, minimize the total number of deliveries.

**Model.**
```
min 1*[sleds] + 1*[snowmobiles]
  package_target: 125*[sleds] + 150*[snowmobiles] == 150000
  sleds_at_least_twice_snowmobiles: 1*[sleds] - 2*[snowmobiles] >= 0
  sleds: integer, in [0, inf]
  snowmobiles: integer, in [0, inf]
```

**Facts.** objective 1125; values sleds = 750, snowmobiles = 375; slack package_target: 0, sleds_at_least_twice_snowmobiles: 0; binding: package_target, sleds_at_least_twice_snowmobiles; shadow prices none (a MIP)

**Explanation.**

Send 750 sleds and 375 snowmobiles, for 1,125 deliveries in total. This is the fewest deliveries that move exactly 150,000 packages while keeping sleds at least twice the snowmobile count. Both the package target and the two-to-one sled rule are fully used, and removing either one would lower the total, so both are real limits on the result. The two-to-one rule is the one to watch: loosening it by one unit would not reduce the total further, but the rule is still what forces the sled count up.

**Numbers.**

1. `750` ...[750] sleds and 375 snowmobiles, for 1,125...
2. `375` ...750 sleds and [375] snowmobiles, for 1,125 deliveries in total....
3. `1,125` ...750 sleds and 375 snowmobiles, for [1,125] deliveries in total. This is the fewest...
4. `150,000` ...is the fewest deliveries that move exactly [150,000] packages while keeping sleds at least twice...

## -1447728775

**Problem.** An ice cream company sells ice cream as cones and tubs. A cone of ice cream contains 3 oz of ice cream while a tub contains 24 oz of ice cream.  Due to the recent wave of heat and a recent promotion, the company expects to sell at least 2 times more cones than tubs of ice cream. However, to reduce labour time and looking at previous sales, management decided to require stores to at least create 30 tubs of ice cream. If the company has the capacity to make 5000 oz of ice cream, how many orders of each should be made to maximize the total number of sales of ice cream?

**Model.**
```
max 1*[cones] + 1*[tubs]
  cones_at_least_2x_tubs: 1*[cones] - 2*[tubs] >= 0
  min_tubs: 1*[tubs] >= 30
  capacity_oz: 3*[cones] + 24*[tubs] <= 5000
  cones: integer, in [0, inf]
  tubs: integer, in [0, inf]
```

**Facts.** objective 1456; values cones = 1426, tubs = 30; slack cones_at_least_2x_tubs: 1366, min_tubs: 0, capacity_oz: 2; binding: min_tubs; shadow prices none (a MIP)

**Explanation.**

Make **1,426 cones and 30 tubs**, which gives the maximum of **1,456 total items**. The 30-tub minimum and the 5,000 oz capacity both limit this result: the tub minimum is fully used, and removing it would improve the total, while capacity (with 2 oz left unused) would also improve if it were loosened or dropped. The rule that cones be at least twice the tubs does not limit the result, since it has 1,366 cones of room to spare and neither removing nor loosening it would help.

**Numbers.**

1. `1,426` ...**[1,426] cones and 30 tubs**, which gives the...
2. `30` ...**1,426 cones and [30] tubs**, which gives the maximum of **1,456...
3. `1,456` ...and 30 tubs**, which gives the maximum of **[1,456] total items**. The 30-tub minimum and the...
4. `30` ...the maximum of **1,456 total items**. The [30]-tub minimum and the 5,000 oz capacity both...
5. `5,000` ...total items**. The 30-tub minimum and the [5,000] oz capacity both limit this result: the tub...
6. `2` ...improve the total, while capacity (with [2] oz left unused) would also improve if it...
7. `1,366` ...does not limit the result, since it has [1,366] cones of room to spare and neither removing...

## 1392566545

**Problem.** A construction site can use two transfer methods to move equipment using cranes or elevators. Each crane can transport 5 units of equipment and costs $2000 per hour. Each elevator can transport 2 units of equipment and costs $500 per hour. The construction site needs to transport at least 90 units of equipment and has available $30000. There must be at least three times more elevators than cranes. How many of each type of transfer method should be done to minimize the total number of transfer methods?

**Model.**
```
min 1*[cranes] + 1*[elevators]
  capacity: 5*[cranes] + 2*[elevators] >= 90
  budget: 2000*[cranes] + 500*[elevators] <= 30000
  elevator_ratio: 1*[elevators] - 3*[cranes] >= 0
  cranes: integer, in [0, inf]
  elevators: integer, in [0, inf]
```

**Facts.** objective 33; values cranes = 8, elevators = 25; slack capacity: 0, budget: 1500, elevator_ratio: 1; binding: capacity; shadow prices none (a MIP)

**Explanation.**

Use **8 cranes and 25 elevators**. This gives the fewest transfer methods, 33, while still moving at least 90 units of equipment. The capacity requirement is fully used, and dropping it would improve the result, so it is a real limit even though more capacity would not help further. The rule that there be at least three times as many elevators as cranes also limits the result: dropping it would improve the answer, even though it has 1.0 of slack. The budget does not limit the result, since it has 1500 dollars unused and neither loosening nor dropping it would improve the answer.

**Numbers.**

1. `8` ...**[8] cranes and 25 elevators**. This gives the...
2. `25` ...**8 cranes and [25] elevators**. This gives the fewest transfer...
3. `33,` ...This gives the fewest transfer methods, [33,] while still moving at least 90 units of...
4. `90` ...methods, 33, while still moving at least [90] units of equipment. The capacity...
5. `1.0` ...improve the answer, even though it has [1.0] of slack. The budget does not limit the...
6. `1500` ...does not limit the result, since it has [1500] dollars unused and neither loosening nor...

## -2043853315

**Problem.** A skiing resort has two methods of getting their customers up to their resort. They can either use a gondola, or a large bus. On average, a gondola can transport skiers and snowboarders at a rate of 20 people per minute whereas a large bus can transport at a rate of 5 people per minute. However, gondolas cost the resort a lot to maintain and at most 40% of the transportation methods implemented can be gondolas. Since large buses are easier to implement, there must be at least ten times more large buses than gondolas. If the manufacturer wants to move at least 500 customers every minute up the mountain, find the minimum transportation implementations that can be used.

**Model.**
```
min 1*[gondolas] + 1*[large buses]
  throughput: 20*[gondolas] + 5*[large buses] >= 500
  gondola share limit: 0.6*[gondolas] - 0.4*[large buses] <= 0
  bus to gondola ratio: 1*[large buses] - 10*[gondolas] >= 0
  gondolas: integer, in [0, inf]
  large buses: integer, in [0, inf]
```

**Facts.** objective 79; values gondolas = 7, large buses = 72; slack throughput: 0, gondola share limit: 24.6, bus to gondola ratio: 2; binding: throughput; shadow prices none (a MIP)

**Explanation.**

Run the resort with 7 gondolas and 72 large buses, for a total of 79 transportation implementations. This is the smallest combination that still moves at least 500 customers per minute. The 500-customer requirement is exactly met, and removing it would allow a smaller total, so it is the main limit. Relaxing it by one customer per minute would not lower the total, but dropping it entirely would. The bus-to-gondola ratio has 2 units of slack but still limits the result, since removing it would also lower the total. The 40% gondola share limit has slack and does not limit the result at all.

**Numbers.**

1. `7` ...the resort with [7] gondolas and 72 large buses, for a total of...
2. `72` ...the resort with 7 gondolas and [72] large buses, for a total of 79...
3. `79` ...gondolas and 72 large buses, for a total of [79] transportation implementations. This is the...
4. `500` ...combination that still moves at least [500] customers per minute. The 500-customer...
5. `500` ...at least 500 customers per minute. The [500]-customer requirement is exactly met, and...
6. `2` ...would. The bus-to-gondola ratio has [2] units of slack but still limits the result,...
7. `40%` ...removing it would also lower the total. The [40%] gondola share limit has slack and does not...
