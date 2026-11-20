# Explanation labels, batch 3 of 4

Label every numbered number `correct` or `wrong` in `labels-3.csv`, and every explanation's false claim `yes` or `no` in `claims-3.csv`, by the rules of docs/analysis/explanation_checker.md. This sheet doesn't show the checker's flags, on purpose.

## 793774916

**Problem.** A bakery sells two types of cakes. They sell a chocolate cake and a vanilla cake. Let's say they make x1 chocolate cakes, at a profit of $10 each, and x2 vanilla cakes, at a profit of $11 each (x1 and x2 are unknowns both greater than or equal to 0). The daily demand for these cakes is at most 50 chocolate cakes and at most 30 vanilla cakes. The bakery is short staffed and can make a maximum of 50 cakes of either type per day. How much of each cake should the bakery make in order to maximize profit?

**Model.**
```
max 10*[chocolate cakes] + 11*[vanilla cakes]
  chocolate demand: 1*[chocolate cakes] <= 50
  vanilla demand: 1*[vanilla cakes] <= 30
  daily production capacity: 1*[chocolate cakes] + 1*[vanilla cakes] <= 50
  chocolate cakes: integer, in [0, inf]
  vanilla cakes: integer, in [0, inf]
```

**Facts.** objective 530; values chocolate cakes = 20, vanilla cakes = 30; slack chocolate demand: 30, vanilla demand: 0, daily production capacity: 0; binding: vanilla demand, daily production capacity; shadow prices none (a MIP)

**Explanation.**

The bakery should make 20 chocolate cakes and 30 vanilla cakes each day. Together these bring in a profit of $530. Vanilla cakes are the more profitable of the two, so they are made up to the 30 that customers will buy, and the rest of the daily capacity goes to chocolate. The limit is the 50-cake daily production capacity, which is completely used, and the vanilla demand of 30, which is also fully used. Chocolate demand is not the constraint, since 30 chocolate cakes of demand go unmet, but the staffing limit means the bakery can't make more.

**Numbers.**

1. `20` ...bakery should make [20] chocolate cakes and 30 vanilla cakes each...
2. `30` ...bakery should make 20 chocolate cakes and [30] vanilla cakes each day. Together these...
3. `$530` ...day. Together these bring in a profit of [$530]. Vanilla cakes are the more profitable of...
4. `30` ...of the two, so they are made up to the [30] that customers will buy, and the rest of...
5. `50` ...goes to chocolate. The limit is the [50]-cake daily production capacity, which is...
6. `30,` ...completely used, and the vanilla demand of [30,] which is also fully used. Chocolate demand...
7. `30` ...demand is not the constraint, since [30] chocolate cakes of demand go unmet, but the...

## -1501301743

**Problem.** The Chips Alloy company produces 150 tons of iron ore and 35 tons of zinc ore each month. These can be treated in different ways to produce three different alloy grades: Standard, Plus or Premium. To produce 1 ton of the Standard grade alloy requires 3 tons of iron ore and 1 ton of zinc ore. To produce 1 ton of the Plus grade alloy requires 5 tons of iron ore and 2 tons of zinc ore. Finally, to produce 1 ton of the Premium grade alloy requires 6 tons of iron ore and 3 tons of zinc ore. The profit per ton from selling the alloys are $1500, $2500 and $5500 for the Standard, Plus, and Premium grades respectively. How much of each alloy grade should be produced to maximize profit?

**Model.**
```
max 1500*[standard_alloy_tons] + 2500*[plus_alloy_tons] + 5500*[premium_alloy_tons]
  iron_ore_available: 3*[standard_alloy_tons] + 5*[plus_alloy_tons] + 6*[premium_alloy_tons] <= 150
  zinc_ore_available: 1*[standard_alloy_tons] + 2*[plus_alloy_tons] + 3*[premium_alloy_tons] <= 35
  standard_alloy_tons: continuous, in [0, inf]
  plus_alloy_tons: continuous, in [0, inf]
  premium_alloy_tons: continuous, in [0, inf]
```

**Facts.** objective 64166.7; values standard_alloy_tons = 0, plus_alloy_tons = 0, premium_alloy_tons = 11.6667; slack iron_ore_available: 80, zinc_ore_available: -1e-06; binding: zinc_ore_available; shadow prices iron_ore_available: 0, zinc_ore_available: 1833.33

**Explanation.**

Produce only the Premium grade, about 11.67 tons per month, and make no Standard or Plus alloy. This plan brings in a profit of about $64,167 per month. Zinc ore is the bottleneck: all 35 tons are used, while about 80 tons of iron ore sit unused, so extra iron would add nothing. Each additional ton of zinc ore would raise profit by about $1,833, so zinc supply is the main limit on earnings.

**Numbers.**

1. `11.67` ...only the Premium grade, about [11.67] tons per month, and make no Standard or...
2. `$64,167` ...This plan brings in a profit of about [$64,167] per month. Zinc ore is the bottleneck: all...
3. `35` ...per month. Zinc ore is the bottleneck: all [35] tons are used, while about 80 tons of iron...
4. `80` ...all 35 tons are used, while about [80] tons of iron ore sit unused, so extra iron...
5. `$1,833,` ...ton of zinc ore would raise profit by about [$1,833,] so zinc supply is the main limit on...

## 1775140418

**Problem.** A factory in India produces rice and corn. To make one kilogram of rice requires 2 hours of human labor, 3 hours of machine work, and 4 hours of resting under the sun. To make one kilogram of corn requires 1 hour of human labor, 5 hours of machine work, and 1 hour of resting under the sun. The factory only has 100 hours of human labor, 200 hours of machine labor, and 75 hours of time under the sun available. The net profit per kilogram of rice is $20 and the net profit per kilogram of corn is $25. How many kilograms of each should the factory make in order to maximize profit?

**Model.**
```
max 20*[rice_kg] + 25*[corn_kg]
  human_labor: 2*[rice_kg] + 1*[corn_kg] <= 100
  machine_work: 3*[rice_kg] + 5*[corn_kg] <= 200
  sun_resting: 4*[rice_kg] + 1*[corn_kg] <= 75
  rice_kg: continuous, in [0, inf]
  corn_kg: continuous, in [0, inf]
```

**Facts.** objective 1051.47; values rice_kg = 10.2941, corn_kg = 33.8235; slack human_labor: 45.5882, machine_work: 1e-06, sun_resting: -1e-06; binding: machine_work, sun_resting; shadow prices human_labor: 0, machine_work: 4.70588, sun_resting: 1.47059

**Explanation.**

The factory should make about 10.29 kg of rice and 33.82 kg of corn, which yields a maximum profit of about $1,051.47. Machine work and sun-resting time are both used up completely, so they are the bottlenecks. Each extra machine hour would add about $4.71 to profit, and each extra hour of sun-resting time about $1.47. Human labor is not a constraint, with about 45.59 hours left unused, so adding more of it would not help. These results assume the stated hourly requirements and profits are exact and that the factory can produce fractional kilograms.

**Numbers.**

1. `10.29` ...factory should make about [10.29] kg of rice and 33.82 kg of corn, which...
2. `33.82` ...should make about 10.29 kg of rice and [33.82] kg of corn, which yields a maximum profit...
3. `$1,051.47` ...which yields a maximum profit of about [$1,051.47]. Machine work and sun-resting time are both...
4. `$4.71` ...Each extra machine hour would add about [$4.71] to profit, and each extra hour of...
5. `$1.47` ...each extra hour of sun-resting time about [$1.47]. Human labor is not a constraint, with...
6. `45.59` ...Human labor is not a constraint, with about [45.59] hours left unused, so adding more of it...

## 1213406437

**Problem.** Bold Tycoon wants to put his $10,000 to work and decides to invest his money in GICs and index ETF. GICs  yields a 2% return whereas index ETF yields an average return of 7.5%. To meet his long-term investment goal, he needs to place at least $4,000 in index ETF.  Nonetheless, he is risk averse and wants at least 30% of his money to be safely invested in GICs.  Help Bold Tycoon determine an asset allocation that will maximize his average return.

**Model.**
```
max 0.02*[GIC dollars invested] + 0.075*[index ETF dollars invested]
  budget: 1*[GIC dollars invested] + 1*[index ETF dollars invested] <= 10000
  minimum ETF investment: 1*[index ETF dollars invested] >= 4000
  minimum safe GIC allocation: 1*[GIC dollars invested] >= 3000
  GIC dollars invested: continuous, in [0, inf]
  index ETF dollars invested: continuous, in [0, inf]
```

**Facts.** objective 585; values GIC dollars invested = 3000, index ETF dollars invested = 7000; slack budget: 0, minimum ETF investment: 3000, minimum safe GIC allocation: 0; binding: budget, minimum safe GIC allocation; shadow prices budget: 0.075, minimum ETF investment: 0, minimum safe GIC allocation: -0.055

**Explanation.**

Put **$3,000 in GICs** and **$7,000 in the index ETF**. This mix earns the maximum expected return of **$585** for the year and meets both the $4,000 minimum ETF requirement and the 30% safe-GIC requirement. The plan is limited by two constraints: the full $10,000 is already used, and the GIC floor is exactly met, so the $3,000 in low-yield GICs is what holds the return down. Each extra dollar of budget would add about $0.075 in return, but each extra dollar required in GICs would cost about $0.055. The ETF minimum has $3,000 of room, so it does not limit the plan.

**Numbers.**

1. `$3,000` ...**[$3,000] in GICs** and **$7,000 in the index ETF**....
2. `$7,000` ...**$3,000 in GICs** and **[$7,000] in the index ETF**. This mix earns the...
3. `$585` ...mix earns the maximum expected return of **[$585]** for the year and meets both the $4,000...
4. `$4,000` ...of **$585** for the year and meets both the [$4,000] minimum ETF requirement and the 30%...
5. `30%` ...the $4,000 minimum ETF requirement and the [30%] safe-GIC requirement. The plan is limited...
6. `$10,000` ...is limited by two constraints: the full [$10,000] is already used, and the GIC floor is...
7. `$3,000` ...and the GIC floor is exactly met, so the [$3,000] in low-yield GICs is what holds the return...
8. `$0.075` ...Each extra dollar of budget would add about [$0.075] in return, but each extra dollar required...
9. `$0.055` ...dollar required in GICs would cost about [$0.055]. The ETF minimum has $3,000 of room, so it...
10. `$3,000` ...cost about $0.055. The ETF minimum has [$3,000] of room, so it does not limit the...

## -1684549839

**Problem.** A meat processing plant has a machine that makes ham and bacon. Each kg of ham takes 15 minutes of machine time and each kg of bacon takes 8 minutes of machine time.  In a week the machine is only available for 2000 minutes. The plant can also make at most 200 kg of ham and at most 220 kg of bacon per week. If the profit per kg of ham is $20 and the profit per kg of bacon is $12, how many of each should the plant make to maximize profit?

**Model.**
```
max 20*[kg of ham produced per week] + 12*[kg of bacon produced per week]
  machine time: 15*[kg of ham produced per week] + 8*[kg of bacon produced per week] <= 2000
  ham capacity: 1*[kg of ham produced per week] <= 200
  bacon capacity: 1*[kg of bacon produced per week] <= 220
  kg of ham produced per week: continuous, in [0, inf]
  kg of bacon produced per week: continuous, in [0, inf]
```

**Facts.** objective 2960; values kg of ham produced per week = 16, kg of bacon produced per week = 220; slack machine time: 0, ham capacity: 184, bacon capacity: 0; binding: machine time, bacon capacity; shadow prices machine time: 1.33333, ham capacity: 0, bacon capacity: 1.33333

**Explanation.**

The plant should make 16 kg of ham and 220 kg of bacon per week, which uses all 2000 machine minutes and fills the bacon limit. This gives a weekly profit of $2960. The machine time and the bacon capacity are both fully used, so they are what limit profit. Each extra machine minute would add about $1.33 to profit, and each extra kg of bacon allowed would add the same amount. The ham limit is not a constraint, since 184 kg of ham capacity goes unused.

**Numbers.**

1. `16` ...plant should make [16] kg of ham and 220 kg of bacon per week,...
2. `220` ...plant should make 16 kg of ham and [220] kg of bacon per week, which uses all 2000...
3. `2000` ...220 kg of bacon per week, which uses all [2000] machine minutes and fills the bacon limit....
4. `$2960` ...bacon limit. This gives a weekly profit of [$2960]. The machine time and the bacon capacity...
5. `$1.33` ...Each extra machine minute would add about [$1.33] to profit, and each extra kg of bacon...
6. `184` ...The ham limit is not a constraint, since [184] kg of ham capacity goes...

## 584268166

**Problem.** A TCM company makes powdered medicine in two different packages, a regular package and premium package, to sell to TCM doctors. The regular package requires 100 g of medicinal herbs and 30 seconds of drying. A premium package requires 130 units of medicinal herbs and 60 seconds of drying. The company has available 9000 units of medicinal herbs and has available 3500 seconds in the drying machine. Since the premium package sells better, the number of regular packages must be less than the number of premium packages. In addition, the company must make at least 15 regular packages. If a regular package can treat 2 people and a premium batch can treat 3 people, how many of each type of package should be made to maximize the number of people that can be treated?

**Model.**
```
max 2*[regular packages] + 3*[premium packages]
  medicinal herbs: 100*[regular packages] + 130*[premium packages] <= 9000
  drying machine time: 30*[regular packages] + 60*[premium packages] <= 3500
  regular fewer than premium: 1*[regular packages] - 1*[premium packages] <= -1
  minimum regular packages: 1*[regular packages] >= 15
  regular packages: integer, in [0, inf]
  premium packages: integer, in [0, inf]
```

**Facts.** objective 193; values regular packages = 38, premium packages = 39; slack medicinal herbs: 130, drying machine time: 20, regular fewer than premium: 0, minimum regular packages: 23; binding: regular fewer than premium; shadow prices none (a MIP)

**Explanation.**

Make 38 regular packages and 39 premium packages. This plan treats 193 people, the most possible under the rules. The rule that regular packages must be fewer than premium packages is the one that holds the plan back, since it is fully used. The medicinal herbs have 130 units left over, the drying machine has 20 seconds left over, and the minimum of 15 regular packages is exceeded by 23, so those resources and requirements are not what limit the result.

**Numbers.**

1. `38` ...[38] regular packages and 39 premium packages....
2. `39` ...38 regular packages and [39] premium packages. This plan treats 193...
3. `193` ...and 39 premium packages. This plan treats [193] people, the most possible under the rules....
4. `130` ...it is fully used. The medicinal herbs have [130] units left over, the drying machine has 20...
5. `20` ...130 units left over, the drying machine has [20] seconds left over, and the minimum of 15...
6. `15` ...20 seconds left over, and the minimum of [15] regular packages is exceeded by 23, so...
7. `23,` ...of 15 regular packages is exceeded by [23,] so those resources and requirements are not...

## -491780757

**Problem.** A nutritionist recommends that a child eat fruits and drink juice to tackle a certain disease. Each serving of fruit contains 5 units of the necessary mineral and 3 units of hydration. Each serving of juice contains 7 units of the necessary mineral and 6 units of hydration. According to the nutritionist, the child must intake at least 60 units of the necessary mineral every week and 40 units of hydration for their body to better absorb the mineral into their body. Further, each serving of fruit contains 9 units of sugar and each serving of juice contains 14 units of sugar. Since juice is more convenient, the child wants to take at least twice as many servings of juice as fruits. How many of each should the child be served to minimize the total sugar intake?

**Model.**
```
min 9*[fruit servings] + 14*[juice servings]
  mineral: 5*[fruit servings] + 7*[juice servings] >= 60
  hydration: 3*[fruit servings] + 6*[juice servings] >= 40
  juice_at_least_twice_fruit: 1*[juice servings] - 2*[fruit servings] >= 0
  fruit servings: integer, in [0, inf]
  juice servings: integer, in [0, inf]
```

**Facts.** objective 121; values fruit servings = 1, juice servings = 8; slack mineral: 1, hydration: 11, juice_at_least_twice_fruit: 6; binding: none; shadow prices none (a MIP)

**Explanation.**

The child should have **1 serving of fruit and 8 servings of juice per week**, which gives the lowest possible sugar intake of **121 units**. This plan meets the mineral requirement with only **1 unit to spare**, so the mineral target is nearly the limiting factor. Hydration has **11 units** of extra margin, and the rule that juice servings be at least twice the fruit servings has **6 servings** of margin. No constraint is exactly fully used, so the plan is limited mainly by the tight mineral target, and it would need to be rechecked if the nutritionist's targets or the food contents change.

**Numbers.**

1. `1` ...child should have **[1] serving of fruit and 8 servings of juice...
2. `8` ...child should have **1 serving of fruit and [8] servings of juice per week**, which gives...
3. `121` ...gives the lowest possible sugar intake of **[121] units**. This plan meets the mineral...
4. `1` ...meets the mineral requirement with only **[1] unit to spare**, so the mineral target is...
5. `11` ...nearly the limiting factor. Hydration has **[11] units** of extra margin, and the rule that...
6. `6` ...be at least twice the fruit servings has **[6] servings** of margin. No constraint is...

## 947008343

**Problem.** A smoothie company offers delivery and ships in specialty delivery and medium bags. A specialty delivery bag can hold 12 orders while a medium bag can hold 7 orders. Most delivery drivers prefer medium bags, so at least three times as many medium bags must be used as specialty delivery bags. The smoothie company has at most 45 medium bags and 60 specialty delivery bags. If the company must send at least 6 specialty delivery bags and can send at most 50 bags in total, how many of each should they send to maximize the total number of smoothies that can be delivered?

**Model.**
```
max 12*[specialty delivery bags] + 7*[medium bags]
  medium bags at least 3 times specialty bags: 1*[medium bags] - 3*[specialty delivery bags] >= 0
  total bags at most 50: 1*[specialty delivery bags] + 1*[medium bags] <= 50
  specialty delivery bags: integer, in [6, 60]
  medium bags: integer, in [0, 45]
```

**Facts.** objective 410; values specialty delivery bags = 12, medium bags = 38; slack medium bags at least 3 times specialty bags: 2, total bags at most 50: 0; binding: total bags at most 50; shadow prices none (a MIP)

**Explanation.**

Send 12 specialty delivery bags and 38 medium bags, which together can deliver 410 orders, the most the rules allow. The 50-bag total is the limit that matters most, since it is fully used and caps how many orders can go out. The rule requiring at least three medium bags per specialty bag is met with 2 bags to spare, so it isn't what holds the total down. The stock limits of 45 medium bags and 60 specialty bags are not reached, so they don't restrict this plan.

**Numbers.**

1. `12` ...[12] specialty delivery bags and 38 medium bags,...
2. `38` ...12 specialty delivery bags and [38] medium bags, which together can deliver 410...
3. `410` ...38 medium bags, which together can deliver [410] orders, the most the rules allow. The...
4. `50` ...410 orders, the most the rules allow. The [50]-bag total is the limit that matters most,...
5. `2` ...medium bags per specialty bag is met with [2] bags to spare, so it isn't what holds the...
6. `45` ...holds the total down. The stock limits of [45] medium bags and 60 specialty bags are not...
7. `60` ...The stock limits of 45 medium bags and [60] specialty bags are not reached, so they...

## -356853555

**Problem.** A house painting company can transport their paint in large cans or small cans. Large cans can hold 6 litres of paint while small cans can hold 2 litres of paint. Since small cans can be used up quickly and thus, not dry up as easily, the company wants to have at most 30% of the cans be large cans. However, there has to be at least 20 large cans especially for the basic colours. If the company needs to transport at least 120 litres of paint, how many of each size of cans should be transported to minimize the total number of cans?

**Model.**
```
min 1*[large_cans] + 1*[small_cans]
  large_share_limit: 0.7*[large_cans] - 0.3*[small_cans] <= 0
  minimum_large_cans: 1*[large_cans] >= 20
  minimum_paint_litres: 6*[large_cans] + 2*[small_cans] >= 120
  large_cans: integer, in [0, inf]
  small_cans: integer, in [0, inf]
```

**Facts.** objective 67; values large_cans = 20, small_cans = 47; slack large_share_limit: 0.1, minimum_large_cans: 0, minimum_paint_litres: 94; binding: minimum_large_cans; shadow prices none (a MIP)

**Explanation.**

The company should transport 20 large cans and 47 small cans, for 67 cans in total, which is the fewest that meets all the requirements. The minimum of 20 large cans for the basic colours is the binding requirement, so it sets the number of large cans. The paint requirement is comfortably exceeded, with 94 litres more than the 120-litre minimum, so it is not what limits the plan. The 30% cap on large cans is also met, with a small margin of 0.1 in the constraint's terms, so it is nearly the limit as well.

**Numbers.**

1. `20` ...company should transport [20] large cans and 47 small cans, for 67 cans...
2. `47` ...company should transport 20 large cans and [47] small cans, for 67 cans in total, which is...
3. `67` ...20 large cans and 47 small cans, for [67] cans in total, which is the fewest that...
4. `20` ...meets all the requirements. The minimum of [20] large cans for the basic colours is the...
5. `94` ...requirement is comfortably exceeded, with [94] litres more than the 120-litre minimum, so...
6. `120` ...exceeded, with 94 litres more than the [120]-litre minimum, so it is not what limits the...
7. `30%` ...so it is not what limits the plan. The [30%] cap on large cans is also met, with a small...
8. `0.1` ...cans is also met, with a small margin of [0.1] in the constraint's terms, so it is nearly...

## 558300309

**Problem.** A dental firm hires two types of employees: dentists and oral hygienists. Dentists work 12 hours every shift and oral hygienists work 5 hours every shift. Additionally, dentists are paid $900 per shift while oral hygienists are paid $250 per shift. It is close to Halloween and the dental firm expects more patients coming in. They require 1000 hours of labour. There must be at least 20 shifts of dentist to keep the office running. If there is a budget of $65000, how many of each type of employee should the firm schedule to work to minimize the total number of shifts?

**Model.**
```
min 1*[dentist shifts] + 1*[oral hygienist shifts]
  labour hours: 12*[dentist shifts] + 5*[oral hygienist shifts] >= 1000
  minimum dentist shifts: 1*[dentist shifts] >= 20
  budget: 900*[dentist shifts] + 250*[oral hygienist shifts] <= 65000
  dentist shifts: integer, in [0, inf]
  oral hygienist shifts: integer, in [0, inf]
```

**Facts.** objective 130; values dentist shifts = 50, oral hygienist shifts = 80; slack labour hours: 0, minimum dentist shifts: 30, budget: 0; binding: labour hours, budget; shadow prices none (a MIP)

**Explanation.**

Schedule **50 dentist shifts** and **80 oral hygienist shifts**, for a total of **130 shifts**, the fewest that still meets the requirements. This covers the 1,000 hours of labour the firm needs and stays within the $65,000 budget. Both the hours and the budget are used up exactly, so the plan has no spare capacity in either. The plan is also limited by those two constraints: any change that adds hours or spends more would need more money or more shifts. The minimum of 20 dentist shifts is not what limits the plan, since 50 dentist shifts are scheduled, which leaves 30 above the minimum.

**Numbers.**

1. `50` ...**[50] dentist shifts** and **80 oral hygienist...
2. `80` ...**50 dentist shifts** and **[80] oral hygienist shifts**, for a total of...
3. `130` ...oral hygienist shifts**, for a total of **[130] shifts**, the fewest that still meets the...
4. `1,000` ...meets the requirements. This covers the [1,000] hours of labour the firm needs and stays...
5. `$65,000` ...labour the firm needs and stays within the [$65,000] budget. Both the hours and the budget are...
6. `20` ...more money or more shifts. The minimum of [20] dentist shifts is not what limits the plan,...
7. `50` ...shifts is not what limits the plan, since [50] dentist shifts are scheduled, which leaves...
8. `30` ...dentist shifts are scheduled, which leaves [30] above the...

## 1030062804

**Problem.** A nurse suggests that his patient drink more protein shakes and milk to meet their calcium and protein requirements. One glass of protein shake contains 3 units of calcium, 2 units of protein, and 3 grams of sugar. One glass of milk contains 5 units of calcium, 1 unit of protein, and 5 grams of sugar. The patient must get at least 90 units of calcium and 85 units of protein. Since the patent prefers milk, they must drink at least 3 times as many glasses of milk as glasses of protein shakes. How many glasses of each should they drink to minimize their sugar intake?

**Model.**
```
min 3*[protein shake glasses] + 5*[milk glasses]
  calcium requirement: 3*[protein shake glasses] + 5*[milk glasses] >= 90
  protein requirement: 2*[protein shake glasses] + 1*[milk glasses] >= 85
  milk preference: 1*[milk glasses] - 3*[protein shake glasses] >= 0
  protein shake glasses: integer, in [0, inf]
  milk glasses: integer, in [0, inf]
```

**Facts.** objective 306; values protein shake glasses = 17, milk glasses = 51; slack calcium requirement: 216, protein requirement: 0, milk preference: 0; binding: protein requirement, milk preference; shadow prices none (a MIP)

**Explanation.**

The patient should drink 17 protein shakes and 51 glasses of milk, which meets the protein and milk-preference rules at the lowest sugar intake the model allows, 306 grams. The protein requirement and the milk-preference rule are both exactly met, so this plan leaves no room to drink less of either. The calcium requirement is exceeded by 216 units, so calcium is not what limits the plan. The model does not give shadow prices, so it cannot say how much the sugar total would change if the protein target or the milk ratio changed.

**Numbers.**

1. `17` ...patient should drink [17] protein shakes and 51 glasses of milk,...
2. `51` ...patient should drink 17 protein shakes and [51] glasses of milk, which meets the protein...
3. `306` ...the lowest sugar intake the model allows, [306] grams. The protein requirement and the...
4. `216` ...The calcium requirement is exceeded by [216] units, so calcium is not what limits the...

## 691521231

**Problem.** A sample can be analyzed by two machines for their chemical make-up, Analyzer 3000 and QuickAnalytics. Analyzer 3000 analyzes 20 samples of water and 30 samples of dirt per hour. QuickAnalytics examines 40 samples of water and 10 samples of dirt per hour. In addition, Analyzer 3000 creates 3.5 units of heat per hour while QuickAnalytics creates 4.5 units of heat per hour. If at least 1000 samples of water and 800 samples of dirt must be analyzed, how many hours should each machine be used to minimize the total amount of heat produced?

**Model.**
```
min 3.5*[hours of Analyzer 3000 used] + 4.5*[hours of QuickAnalytics used]
  water samples analyzed: 20*[hours of Analyzer 3000 used] + 40*[hours of QuickAnalytics used] >= 1000
  dirt samples analyzed: 30*[hours of Analyzer 3000 used] + 10*[hours of QuickAnalytics used] >= 800
  hours of Analyzer 3000 used: continuous, in [0, inf]
  hours of QuickAnalytics used: continuous, in [0, inf]
```

**Facts.** objective 140; values hours of Analyzer 3000 used = 22, hours of QuickAnalytics used = 14; slack water samples analyzed: 0, dirt samples analyzed: 0; binding: water samples analyzed, dirt samples analyzed; shadow prices water samples analyzed: 0.1, dirt samples analyzed: 0.05

**Explanation.**

Run Analyzer 3000 for 22 hours and QuickAnalytics for 14 hours. This produces the lowest possible total heat, 140 units, while analyzing at least 1,000 water samples and 800 dirt samples. Both requirements are met exactly, with no extra capacity left over. Each additional water sample required would add about 0.1 units of heat, and each additional dirt sample about 0.05 units, so these two sample requirements are what limit how low the heat can go.

**Numbers.**

1. `3000` ...Analyzer [3000] for 22 hours and QuickAnalytics for 14...
2. `22` ...Analyzer 3000 for [22] hours and QuickAnalytics for 14 hours. This...
3. `14` ...3000 for 22 hours and QuickAnalytics for [14] hours. This produces the lowest possible...
4. `140` ...produces the lowest possible total heat, [140] units, while analyzing at least 1,000 water...
5. `1,000` ...heat, 140 units, while analyzing at least [1,000] water samples and 800 dirt samples. Both...
6. `800` ...analyzing at least 1,000 water samples and [800] dirt samples. Both requirements are met...
7. `0.1` ...water sample required would add about [0.1] units of heat, and each additional dirt...
8. `0.05` ...heat, and each additional dirt sample about [0.05] units, so these two sample requirements are...

## -1384117219

**Problem.** A government sanitization plant processes liquid waste and solid waste in batches. Liquid waste requires 30 units of disinfectant and 20 units of bacteria. Solid waste requires 25 units of disinfectant and 15 units of bacteria. The sanitization plant has available 1500 units of disinfectant and 1000 units of bacteria. The batches of liquid waste processed must be twice the number of solid waste processed. In addition, at most 10 batches of solid waste can be processed due to storage limitations. If each liquid waste batch is the result of 10 people and each solid waste batch is the result of 3 people, how many of each should the plant process to maximize the number of people served?

**Model.**
```
max 10*[liquid waste batches] + 3*[solid waste batches]
  disinfectant: 30*[liquid waste batches] + 25*[solid waste batches] <= 1500
  bacteria: 20*[liquid waste batches] + 15*[solid waste batches] <= 1000
  liquid twice solid: 1*[liquid waste batches] - 2*[solid waste batches] == 0
  solid storage limit: 1*[solid waste batches] <= 10
  liquid waste batches: integer, in [0, inf]
  solid waste batches: integer, in [0, inf]
```

**Facts.** objective 230; values liquid waste batches = 20, solid waste batches = 10; slack disinfectant: 650, bacteria: 450, liquid twice solid: 0, solid storage limit: 0; binding: liquid twice solid, solid storage limit; shadow prices none (a MIP)

**Explanation.**

The plant should process **20 batches of liquid waste and 10 batches of solid waste**. This serves **230 people**, the maximum possible under the constraints. The main limits are the 2-to-1 rule between liquid and solid batches and the storage cap of 10 solid batches, which are both fully used. Disinfectant and bacteria are not the bottleneck: 650 units of disinfectant and 450 units of bacteria would remain unused.

**Numbers.**

1. `20` ...plant should process **[20] batches of liquid waste and 10 batches of...
2. `10` ...process **20 batches of liquid waste and [10] batches of solid waste**. This serves **230...
3. `230` ...10 batches of solid waste**. This serves **[230] people**, the maximum possible under the...
4. `2` ...the constraints. The main limits are the [2]-to-1 rule between liquid and solid batches...
5. `1` ...constraints. The main limits are the 2-to-[1] rule between liquid and solid batches and...
6. `10` ...and solid batches and the storage cap of [10] solid batches, which are both fully used....
7. `650` ...and bacteria are not the bottleneck: [650] units of disinfectant and 450 units of...
8. `450` ...bottleneck: 650 units of disinfectant and [450] units of bacteria would remain...

## -1091195781

**Problem.** A clothing manufacturing company needs to transport their product by cargo ship or airplane. A cargo ship can transport 40 units per trip while by airplane can transport 60 units per trip. A cargo ship produces 20 units of pollution and an airplane produces 35 units of pollution. There can be at least 6 airplane trips made and at least 25% of all trips must be made by cargo ship. The company needs to transport at least 750 units of their product. How many of each transportation should they use to minimize the total amount of pollution produced?

**Model.**
```
min 20*[cargo ship trips] + 35*[airplane trips]
  minimum airplane trips: 1*[airplane trips] >= 6
  ship share of all trips: 0.75*[cargo ship trips] - 0.25*[airplane trips] >= 0
  units transported: 40*[cargo ship trips] + 60*[airplane trips] >= 750
  cargo ship trips: integer, in [0, inf]
  airplane trips: integer, in [0, inf]
```

**Facts.** objective 410; values cargo ship trips = 10, airplane trips = 6; slack minimum airplane trips: 0, ship share of all trips: 6, units transported: 10; binding: minimum airplane trips; shadow prices none (a MIP)

**Explanation.**

Schedule **10 cargo ship trips and 6 airplane trips**, which produces the lowest total pollution possible: **410** units. The plan sits exactly at the requirement of at least 6 airplane trips, so that rule is the one that is fully used and it is what forces the airplane count. The rule that at least 750 units be shipped has 10 units of spare capacity, and the rule that ships make up at least 25% of trips has 6 units of slack, so neither is currently limiting the plan. The data don't include shadow prices, so this doesn't show how much the pollution total would change if those limits were loosened.

**Numbers.**

1. `10` ...**[10] cargo ship trips and 6 airplane trips**,...
2. `6` ...**10 cargo ship trips and [6] airplane trips**, which produces the lowest...
3. `410` ...the lowest total pollution possible: **[410]** units. The plan sits exactly at the...
4. `6` ...sits exactly at the requirement of at least [6] airplane trips, so that rule is the one...
5. `750` ...the airplane count. The rule that at least [750] units be shipped has 10 units of spare...
6. `10` ...rule that at least 750 units be shipped has [10] units of spare capacity, and the rule that...
7. `25%` ...and the rule that ships make up at least [25%] of trips has 6 units of slack, so neither...
8. `6` ...ships make up at least 25% of trips has [6] units of slack, so neither is currently...

## -577606329

**Problem.** There are two methods of extracting a chemical element, method X and method Y.  Method X requires 5 atomic units (au) of aluminum, 1 au of oxygen, and can extract 0.5 au of the desired chemical element. Method Y requires 6 au of aluminum, 2 au of oxygen, and can extract 0.7 au of the desired chemical element. There are 650 au of aluminum, and 425 au of oxygen available. What is the best combination of these two methods to maximize the total amount of desired chemical element?

**Model.**
```
max 0.5*[method X runs] + 0.7*[method Y runs]
  aluminum: 5*[method X runs] + 6*[method Y runs] <= 650
  oxygen: 1*[method X runs] + 2*[method Y runs] <= 425
  method X runs: continuous, in [0, inf]
  method Y runs: continuous, in [0, inf]
```

**Facts.** objective 75.8333; values method X runs = 0, method Y runs = 108.333; slack aluminum: 2e-05, oxygen: 208.333; binding: aluminum; shadow prices aluminum: 0.116667, oxygen: 0

**Explanation.**

Run Method Y 108.3 times and don't run Method X at all. This yields about 75.83 units of the desired element, the most possible with the available materials. Aluminum is the bottleneck: all 650 au is used, and each extra au would add about 0.117 units of output. Oxygen is not the limit, since about 208.3 au of it would go unused.

**Numbers.**

1. `108.3` ...Method Y [108.3] times and don't run Method X at all. This...
2. `75.83` ...run Method X at all. This yields about [75.83] units of the desired element, the most...
3. `650` ...materials. Aluminum is the bottleneck: all [650] au is used, and each extra au would add...
4. `0.117` ...is used, and each extra au would add about [0.117] units of output. Oxygen is not the limit,...
5. `208.3` ...Oxygen is not the limit, since about [208.3] au of it would go...

## -706167573

**Problem.** A strawberry farmer has available 225 hectares of land and she needs to harvest the strawberries either through employees or U-pick. For each hectare of land, employees can hand-pick 60 lbs of strawberries which creates 5 lbs of waste, and takes 30 minutes. Conversely, for each hectare of land, opening the farm for U-pick can pick 45 lbs of strawberries which creates 20 lbs of waste, but only takes 20 minutes. The farmer has a maximum amount of people allowed on the field at all times and due to the restriction of trying to sell the product while it is still fresh, expects that at maximum capacity she only has 8000 minutes available for picking. Additionally, there can be at most 6400 lbs of waste. How many hectares should be allocated to each harvesting technique to maximize the amount of strawberries that can be picked?

**Model.**
```
max 60*[employee_hectares] + 45*[upick_hectares]
  land: 1*[employee_hectares] + 1*[upick_hectares] <= 225
  picking_minutes: 30*[employee_hectares] + 20*[upick_hectares] <= 8000
  waste: 5*[employee_hectares] + 20*[upick_hectares] <= 6400
  employee_hectares: continuous, in [0, inf]
  upick_hectares: continuous, in [0, inf]
```

**Facts.** objective 13500; values employee_hectares = 225, upick_hectares = 0; slack land: 0, picking_minutes: 1250, waste: 5275; binding: land; shadow prices land: 60, picking_minutes: 0, waste: 0

**Explanation.**

Allocate all 225 hectares to employee hand-picking and none to U-pick. This yields the maximum of 13,500 lbs of strawberries. The land is the only limit that is fully used: each additional hectare would add about 60 lbs, so more land would help if it could be obtained. Picking time (1,250 minutes) and waste (5,275 lbs) both still have room to spare, so they are not restricting the result at this plan.

**Numbers.**

1. `225` ...all [225] hectares to employee hand-picking and none...
2. `13,500` ...none to U-pick. This yields the maximum of [13,500] lbs of strawberries. The land is the only...
3. `60` ...each additional hectare would add about [60] lbs, so more land would help if it could be...
4. `1,250` ...help if it could be obtained. Picking time ([1,250] minutes) and waste (5,275 lbs) both still...
5. `5,275` ...Picking time (1,250 minutes) and waste ([5,275] lbs) both still have room to spare, so they...

## 1947901559

**Problem.** A woman with vitamin deficiency is taking supplements from two brands, super vitamin XYZ and vitamin ABC. Super vitamin XYZ contains 2 mg of vitamin, 5 mg of fiber, and causes 2 units of drowsiness per serving. Vitamin ABC contains 1.5 mg of vitamin, 3 mg of fiber, and causes 3 units of drowsiness per serving. The woman wants to get at least 30 mg of vitamin and 55 mg of fiber. In addition, there must be at most 40% of the supplements taken from super vitamin XYZ and there must be at least 3 servings of super vitamin XYZ because it is expiring soon. How many servings of each should she take to minimize her total drowsiness.

**Model.**
```
min 2*[servings of super vitamin XYZ] + 3*[servings of vitamin ABC]
  vitamin_requirement: 2*[servings of super vitamin XYZ] + 1.5*[servings of vitamin ABC] >= 30
  fiber_requirement: 5*[servings of super vitamin XYZ] + 3*[servings of vitamin ABC] >= 55
  xyz_share_max: 0.6*[servings of super vitamin XYZ] - 0.4*[servings of vitamin ABC] <= 0
  xyz_minimum: 1*[servings of super vitamin XYZ] >= 3
  servings of super vitamin XYZ: integer, in [0, inf]
  servings of vitamin ABC: integer, in [0, inf]
```

**Facts.** objective 47; values servings of super vitamin XYZ = 7, servings of vitamin ABC = 11; slack vitamin_requirement: 0.5, fiber_requirement: 13, xyz_share_max: 0.2, xyz_minimum: 4; binding: none; shadow prices none (a MIP)

**Explanation.**

Take 7 servings of super vitamin XYZ and 11 servings of vitamin ABC. This gives the lowest total drowsiness possible under the rules, a total of 47 units. Every requirement is met: vitamin intake exceeds the 30 mg minimum by 0.5 mg, fiber exceeds 55 mg by 13 mg, XYZ makes up less than the 40% limit with room to spare, and you're taking 4 more XYZ servings than the 3-serving minimum. No limit is fully used up, so the plan has some room, but the vitamin target is the closest to its limit. Because all whole-serving amounts are required, the answer is only valid for whole servings, which is what the model enforces.

**Numbers.**

1. `7` ...[7] servings of super vitamin XYZ and 11...
2. `11` ...7 servings of super vitamin XYZ and [11] servings of vitamin ABC. This gives the...
3. `47` ...possible under the rules, a total of [47] units. Every requirement is met: vitamin...
4. `30` ...is met: vitamin intake exceeds the [30] mg minimum by 0.5 mg, fiber exceeds 55 mg...
5. `0.5` ...vitamin intake exceeds the 30 mg minimum by [0.5] mg, fiber exceeds 55 mg by 13 mg, XYZ makes...
6. `55` ...the 30 mg minimum by 0.5 mg, fiber exceeds [55] mg by 13 mg, XYZ makes up less than the 40%...
7. `13` ...minimum by 0.5 mg, fiber exceeds 55 mg by [13] mg, XYZ makes up less than the 40% limit...
8. `40%` ...55 mg by 13 mg, XYZ makes up less than the [40%] limit with room to spare, and you're taking...
9. `4` ...limit with room to spare, and you're taking [4] more XYZ servings than the 3-serving...
10. `3` ...you're taking 4 more XYZ servings than the [3]-serving minimum. No limit is fully used up,...

## 2114430988

**Problem.** A famous chocolate shop is expecting a lot of orders because of an upcoming holiday. The chocolate shop is famous for selling two products, large boxes of chocolates, or small boxes of chocolates. A large box of chocolate has 24 individual chocolates while a small box of chocolate has 12 individual chocolates. The chocolate shop has a delivery service, and each trip, the shop owner can prepare ahead of time at most 110 large boxes of chocolates or 150 small boxes of chocolates. Due to space limitations of their truck, the truck can fit at most 90 total boxes of chocolates and because of a sale, there must be at least 10 large boxes of chocolates. However, small boxes of chocolates are less expensive and the shop owner expects to move at least three times as many small boxes of chocolates than large boxes of chocolates. How many of each size of chocolate box should the shop owner put in their truck for each trip to maximize the total number of individual chocolates transported to their customers?

**Model.**
```
max 24*[large boxes of chocolates] + 12*[small boxes of chocolates]
  large box preparation limit: 1*[large boxes of chocolates] <= 110
  small box preparation limit: 1*[small boxes of chocolates] <= 150
  truck capacity: 1*[large boxes of chocolates] + 1*[small boxes of chocolates] <= 90
  sale minimum large boxes: 1*[large boxes of chocolates] >= 10
  small boxes at least three times large: 1*[small boxes of chocolates] - 3*[large boxes of chocolates] >= 0
  large boxes of chocolates: integer, in [0, inf]
  small boxes of chocolates: integer, in [0, inf]
```

**Facts.** objective 1344; values large boxes of chocolates = 22, small boxes of chocolates = 68; slack large box preparation limit: 88, small box preparation limit: 82, truck capacity: 0, sale minimum large boxes: 12, small boxes at least three times large: 2; binding: truck capacity; shadow prices none (a MIP)

**Explanation.**

Load **22 large boxes** and **68 small boxes** on each trip. Together they carry **1,344 individual chocolates**, the most the rules allow. The truck's limit of **90 boxes** is the binding constraint, so it is the real bottleneck: no more boxes can fit, and a box of either size would have to replace another. The other rules are met with room to spare: the large-box preparation limit has 88 to spare, the small-box limit has 82 to spare, the sale minimum of 10 large boxes is exceeded by 12, and the "small boxes at least three times large" rule is exceeded by 2. Because the problem gives no shadow prices, the model does not show how much the total would rise with more truck space.

**Numbers.**

1. `22` ...**[22] large boxes** and **68 small boxes** on...
2. `68` ...**22 large boxes** and **[68] small boxes** on each trip. Together they...
3. `1,344` ...boxes** on each trip. Together they carry **[1,344] individual chocolates**, the most the rules...
4. `90` ...the rules allow. The truck's limit of **[90] boxes** is the binding constraint, so it is...
5. `88` ...spare: the large-box preparation limit has [88] to spare, the small-box limit has 82 to...
6. `82` ...has 88 to spare, the small-box limit has [82] to spare, the sale minimum of 10 large...
7. `10` ...limit has 82 to spare, the sale minimum of [10] large boxes is exceeded by 12, and the...
8. `12,` ...minimum of 10 large boxes is exceeded by [12,] and the "small boxes at least three times...
9. `2` ...three times large" rule is exceeded by [2]. Because the problem gives no shadow...

## -654999513

**Problem.** A waste treatment company must remove waste using a large container or a medium container. A large container can take 5 tons of waste while a medium container can take 3.5 tons of waste. The treatment plant has available at most 40 large containers and 35 medium containers. Additionally, due to logistics in the storage warehouse, there must be at most 65 total containers and they must use at least 6 medium containers. Finally, there must be twice as many medium containers than large containers. How many of each container should they use to maximize the total amount of waste they can transport?

**Model.**
```
max 5*[large containers] + 3.5*[medium containers]
  large container availability: 1*[large containers] <= 40
  medium container availability: 1*[medium containers] <= 35
  total containers: 1*[large containers] + 1*[medium containers] <= 65
  minimum medium containers: 1*[medium containers] >= 6
  medium twice large: 1*[medium containers] - 2*[large containers] == 0
  large containers: integer, in [0, inf]
  medium containers: integer, in [0, inf]
```

**Facts.** objective 204; values large containers = 17, medium containers = 34; slack large container availability: 23, medium container availability: 1, total containers: 14, minimum medium containers: 28, medium twice large: 0; binding: medium twice large; shadow prices none (a MIP)

**Explanation.**

Use **17 large containers** and **34 medium containers**. This plan carries the most waste possible, **204 tons**. The rule that medium containers must be exactly twice the number of large ones is the main limit, and it is the only constraint that is fully used. Medium containers are almost all used up, with just 1 spare, while 23 large containers and 14 total containers remain unused.

**Numbers.**

1. `17` ...**[17] large containers** and **34 medium...
2. `34` ...**17 large containers** and **[34] medium containers**. This plan carries the...
3. `204` ...plan carries the most waste possible, **[204] tons**. The rule that medium containers...
4. `1` ...are almost all used up, with just [1] spare, while 23 large containers and 14...
5. `23` ...all used up, with just 1 spare, while [23] large containers and 14 total containers...
6. `14` ...just 1 spare, while 23 large containers and [14] total containers remain...

## -955370712

**Problem.** A commercial fishing company has available 200 square kilometers of water that they can fish from. They can either allocate a square kilometer for fish farming or trawling. For each square kilometer of ocean, fish farming causes 8 units of pollution and nets 4 tons of fish and requires 6 workers every day. For each square kilometer of ocean, trawling causes 10 units of pollution, nets 3 tons of fish and requires 2 workers every day. Due to environmental regulations, there must be at most 1700 units of pollution and the company has available 500 workers daily. Find the proportion of lands that use each fishing technique to maximize the daily yield of fish.

**Model.**
```
max 4*[square kilometers allocated to fish farming] + 3*[square kilometers allocated to trawling]
  available water: 1*[square kilometers allocated to fish farming] + 1*[square kilometers allocated to trawling] <= 200
  pollution limit: 8*[square kilometers allocated to fish farming] + 10*[square kilometers allocated to trawling] <= 1700
  daily workers: 6*[square kilometers allocated to fish farming] + 2*[square kilometers allocated to trawling] <= 500
  square kilometers allocated to fish farming: continuous, in [0, inf]
  square kilometers allocated to trawling: continuous, in [0, inf]
```

**Facts.** objective 568.182; values square kilometers allocated to fish farming = 36.3636, square kilometers allocated to trawling = 140.909; slack available water: 22.7273, pollution limit: 1.2e-05, daily workers: 4e-06; binding: pollution limit, daily workers; shadow prices available water: 0, pollution limit: 0.227273, daily workers: 0.363636

**Explanation.**

Use about 36.36 square kilometers for fish farming and about 140.91 square kilometers for trawling, which leaves about 22.73 square kilometers of the 200 unused. This allocation produces a maximum of about 568.18 tons of fish per day. The pollution limit and the daily worker limit are both fully used, and they are what keep the yield from rising further. Each extra unit of allowed pollution would add about 0.23 tons per day, and each extra worker about 0.36 tons, while extra water would add nothing.

**Numbers.**

1. `36.36` ...about [36.36] square kilometers for fish farming and...
2. `140.91` ...kilometers for fish farming and about [140.91] square kilometers for trawling, which...
3. `22.73` ...kilometers for trawling, which leaves about [22.73] square kilometers of the 200 unused. This...
4. `200` ...leaves about 22.73 square kilometers of the [200] unused. This allocation produces a maximum...
5. `568.18` ...This allocation produces a maximum of about [568.18] tons of fish per day. The pollution limit...
6. `0.23` ...unit of allowed pollution would add about [0.23] tons per day, and each extra worker about...
7. `0.36` ...tons per day, and each extra worker about [0.36] tons, while extra water would add...

## 38885939

**Problem.** An engineering kids kit has two sets, a mechanical and chemistry kit. The mechanical kit requires 2 units of plastic, 4 units of materials and entertains a kid for 4 hours. The chemistry kit requires 3 units of plastic, 7 units of materials and entertains a kid for 2 hours. The chemistry kit however produces 8 units of waste while the mechanical kit produces 5 units of waste. The company has available 500 units of plastic and 450 units of materials. If the company has committed to producing at most 300 units of waste, how many of each type of kit should the company make to maximize the number of hours of entertainment?

**Model.**
```
max 4*[mechanical kits] + 2*[chemistry kits]
  plastic: 2*[mechanical kits] + 3*[chemistry kits] <= 500
  materials: 4*[mechanical kits] + 7*[chemistry kits] <= 450
  waste: 5*[mechanical kits] + 8*[chemistry kits] <= 300
  mechanical kits: integer, in [0, inf]
  chemistry kits: integer, in [0, inf]
```

**Facts.** objective 240; values mechanical kits = 60, chemistry kits = 0; slack plastic: 380, materials: 210, waste: 0; binding: waste; shadow prices none (a MIP)

**Explanation.**

Make 60 mechanical kits and no chemistry kits. This gives the most entertainment possible, 240 hours. The waste limit of 300 units is the constraint that stops production: it is fully used, so it is what holds the total down. Plastic has 380 units left over and materials have 210 left over, so neither is what limits the plan. The model does not give shadow prices, so it cannot say how much more entertainment an extra unit of waste allowance would add.

**Numbers.**

1. `60` ...[60] mechanical kits and no chemistry kits. This...
2. `240` ...This gives the most entertainment possible, [240] hours. The waste limit of 300 units is the...
3. `300` ...possible, 240 hours. The waste limit of [300] units is the constraint that stops...
4. `380` ...is what holds the total down. Plastic has [380] units left over and materials have 210 left...
5. `210` ...has 380 units left over and materials have [210] left over, so neither is what limits the...

## -279354943

**Problem.** A dietician recommends his patient drink more juice and vitamin-added milk to increase her vitamin and hydration intake. Each cup of juice contains 12 units of vitamins and 8 units of hydration. Each vitamin-added milk contains 14 units of vitamins and 10 units of hydration. The patient needs to consume at least 180 units of vitamins and 140 units of hydration. Since the patient is slightly lactose-intolerant, there must be at most 10% of all cups of drinks be vitamin-added milk. If each cup of vitamin-added milk contains 3 units of sugar and each cup of juice contains 10 units of sugar, how many cups of each should she drink to minimize her sugar intake?

**Model.**
```
min 10*[cups of juice] + 3*[cups of vitamin-added milk]
  vitamins: 12*[cups of juice] + 14*[cups of vitamin-added milk] >= 180
  hydration: 8*[cups of juice] + 10*[cups of vitamin-added milk] >= 140
  lactose limit: -0.1*[cups of juice] + 0.9*[cups of vitamin-added milk] <= 0
  cups of juice: integer, in [0, inf]
  cups of vitamin-added milk: integer, in [0, inf]
```

**Facts.** objective 173; values cups of juice = 17, cups of vitamin-added milk = 1; slack vitamins: 38, hydration: 6, lactose limit: 0.8; binding: none; shadow prices none (a MIP)

**Explanation.**

Drink **17 cups of juice and 1 cup of vitamin-added milk**. This meets the requirements with the least sugar, 173 units in total. Vitamins come to 38 units above the minimum, hydration to 6 units above, and the milk share stays 0.8 below the 10% lactose cap. No limit is fully used, so the plan has some room to spare, and the solver reports no shadow prices. The answer assumes she drinks whole cups only.

**Numbers.**

1. `17` ...**[17] cups of juice and 1 cup of vitamin-added...
2. `1` ...**17 cups of juice and [1] cup of vitamin-added milk**. This meets the...
3. `173` ...the requirements with the least sugar, [173] units in total. Vitamins come to 38 units...
4. `38` ...sugar, 173 units in total. Vitamins come to [38] units above the minimum, hydration to 6...
5. `6` ...to 38 units above the minimum, hydration to [6] units above, and the milk share stays 0.8...
6. `0.8` ...to 6 units above, and the milk share stays [0.8] below the 10% lactose cap. No limit is...
7. `10%` ...and the milk share stays 0.8 below the [10%] lactose cap. No limit is fully used, so the...
