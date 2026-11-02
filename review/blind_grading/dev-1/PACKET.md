# Blind grading: `dev-1`

10 models of word problems, drawn at random (seed 20261030, `python -m opt_agent.blind_grading runs/dev-1`). For each, decide whether the model says what the text says, and write `right`, `wrong` or `unsure` in the `grade` column of `grades.csv`, with a note if it helps. Then run `python -m opt_agent.report runs/dev-1`.

- **right**: a correct model of the text, under any reading the text supports. Names, the order of terms, and equivalent forms (x <= 3y written as x - 3y <= 0) don't matter.
- **wrong**: some part doesn't say what the text says: the objective, a constraint, a number, a direction, or whole numbers vs fractions.
- **unsure**: you can't decide.

The reference is the dataset's annotation, with the problem's integrality label. It's usually right, but it can be wrong or be one of several readings: grade against the text.

Answers, scores, conditions and problem ids are left out on purpose. Until you're done, please don't open the run's files, its report, or `review/taxonomy/`, which lists the wrong answers.

## 1.

> The Vision Corporation manufactures two models of monitors: Aleph 3 and Gilgamesh Supreme. They share a similar manufacturing process in that they both require a certain amount of assembly and packaging. Each Aleph 3 monitor takes 2 hours of assembly and each Gilgamesh Supreme requires 2.5 hours of assembly. They both require 0.5 hours of packaging time per unit. During the next season, 5000 hours of assembly time are available and at most 2500 hours of packaging time may be used. Each Aleph 3 sold yields a profit of $1500. Each Gilgamesh Supreme sold yields a profit of $2500 profit. Formulate and solve this LP problem and find the best combination of monitors that yields the highest profit.

Reference:
```
max 2500*[Gilgamesh Supreme] + 1500*[Aleph 3]
  c0_linear: 2*[Aleph 3] + 2.5*[Gilgamesh Supreme] <= 5000
  c1_linear: 0.5*[Aleph 3] + 0.5*[Gilgamesh Supreme] <= 2500
  Aleph 3: integer, in [0, inf]
  Gilgamesh Supreme: integer, in [0, inf]
```

To grade:
```
max 1500*[Aleph 3 monitors] + 2500*[Gilgamesh Supreme monitors]
  assembly hours: 2*[Aleph 3 monitors] + 2.5*[Gilgamesh Supreme monitors] <= 5000
  packaging hours: 0.5*[Aleph 3 monitors] + 0.5*[Gilgamesh Supreme monitors] <= 2500
  Aleph 3 monitors: integer, in [0, inf]
  Gilgamesh Supreme monitors: integer, in [0, inf]
```

## 2.

> There are two methods of extracting a chemical element, method X and method Y.  Method X requires 5 atomic units (au) of aluminum, 1 au of oxygen, and can extract 0.5 au of the desired chemical element. Method Y requires 6 au of aluminum, 2 au of oxygen, and can extract 0.7 au of the desired chemical element. There are 650 au of aluminum, and 425 au of oxygen available. What is the best combination of these two methods to maximize the total amount of desired chemical element?

Reference:
```
max 0.5*[method X] + 0.7*[method Y.]
  c0_linear: 5*[method X] + 6*[method Y.] <= 650
  c1_linear: 1*[method X] + 2*[method Y.] <= 425
  method X: integer, in [0, inf]
  method Y.: integer, in [0, inf]
```

To grade:
```
max 0.5*[method X runs] + 0.7*[method Y runs]
  aluminum: 5*[method X runs] + 6*[method Y runs] <= 650
  oxygen: 1*[method X runs] + 2*[method Y runs] <= 425
  method X runs: continuous, in [0, inf]
  method Y runs: continuous, in [0, inf]
```

## 3.

> A physics class is performing a volcano experiment using two mixtures, mixture A and mixture B. Mixture A uses 3 units of baking soda, 5 units of vinegar, and produces 2 units of eruption. Mixture B uses 4 units of baking soda, 7 units of vinegar, and produces 4 units of eruption. However, mixture A generates 2 units of garbage and mixture B generates 1 unit of garbage. The physics class has available 200 units of baking soda and 300 units of vinegar. If at most 60 units of garbage can be generated, how many of each type of mixture should be used to maximize the total amount of eruption produced?

Reference:
```
max 2*[mixture A] + 4*[mixture B.]
  c0_linear: 3*[mixture A] + 4*[mixture B.] <= 200
  c1_linear: 5*[mixture A] + 7*[mixture B.] <= 300
  c2_linear: 2*[mixture A] + 1*[mixture B.] <= 60
  mixture A: integer, in [0, inf]
  mixture B.: integer, in [0, inf]
```

To grade:
```
max 2*[mixture A batches] + 4*[mixture B batches]
  baking soda: 3*[mixture A batches] + 4*[mixture B batches] <= 200
  vinegar: 5*[mixture A batches] + 7*[mixture B batches] <= 300
  garbage: 2*[mixture A batches] + 1*[mixture B batches] <= 60
  mixture A batches: continuous, in [0, inf]
  mixture B batches: continuous, in [0, inf]
```

## 4.

> A car manufacturing company needs to distribute their cars to their retail stores by either large trailers or small trailers. A large trailer can carry 6 cars while a small trailer can carry 4 cars. Since large trailers are harder to get a hold of, the number of small trailers used has to be at least three times the number of large trailers used. If at least 80 cars need to be transported, minimize the total number of trailers needed.

Reference:
```
min 1*[large trailers] + 1*[small trailers]
  c0_linear: 6*[large trailers] + 4*[small trailers] >= 80
  c1_xby: 1*[small trailers] - 3*[large trailers] >= 0
  large trailers: integer, in [0, inf]
  small trailers: integer, in [0, inf]
```

To grade:
```
min 1*[large trailers used] + 1*[small trailers used]
  small_at_least_three_times_large: 1*[small trailers used] - 3*[large trailers used] >= 0
  cars_transported: 6*[large trailers used] + 4*[small trailers used] >= 80
  large trailers used: integer, in [0, inf]
  small trailers used: integer, in [0, inf]
```

## 5.

> A pharmaceutical manufacturing plant has 1000 mg of cornstarch to rush orders of diabetic pills and latex gloves. Each diabetic pill requires 4 mg of cornstarch and 0.2 minutes to manufacture. Each individual latex glove requires 7 mg of cornstarch and 0.15 minutes to manufacture. The pharmaceutical manufacturing plant needs to make at least 20 diabetic pills. Since latex gloves are important, at least 60% of produced items must be latex gloves. How many of each should the pharmaceutical manufacturing plant make to minimize the total number of minutes needed?

Reference:
```
min 0.2*[diabetic pills] + 0.15*[latex gloves]
  c0_linear: 7*[latex gloves] + 4*[diabetic pills] <= 1000
  c1_lowerbound: 1*[diabetic pills] >= 20
  c2_ratio: -0.6*[diabetic pills] + 0.4*[latex gloves] >= 0
  diabetic pills: integer, in [0, inf]
  latex gloves: integer, in [0, inf]
```

To grade:
```
min 0.2*[diabetic pills] + 0.15*[latex gloves]
  cornstarch: 4*[diabetic pills] + 7*[latex gloves] <= 1000
  min_pills: 1*[diabetic pills] >= 20
  glove_share: -0.6*[diabetic pills] + 0.4*[latex gloves] >= 0
  diabetic pills: integer, in [0, inf]
  latex gloves: integer, in [0, inf]
```

## 6.

> A nurse suggests that his patient drink more protein shakes and milk to meet their calcium and protein requirements. One glass of protein shake contains 3 units of calcium, 2 units of protein, and 3 grams of sugar. One glass of milk contains 5 units of calcium, 1 unit of protein, and 5 grams of sugar. The patient must get at least 90 units of calcium and 85 units of protein. Since the patent prefers milk, they must drink at least 3 times as many glasses of milk as glasses of protein shakes. How many glasses of each should they drink to minimize their sugar intake?

Reference:
```
min 3*[protein shakes] + 5*[milk]
  c0_linear: 3*[protein shakes] + 5*[milk] >= 90
  c1_linear: 2*[protein shakes] + 1*[milk] >= 85
  c2_xby: 1*[milk] - 3*[protein shakes] >= 0
  protein shakes: integer, in [0, inf]
  milk: integer, in [0, inf]
```

To grade:
```
min 3*[protein shake glasses] + 5*[milk glasses]
  calcium requirement: 3*[protein shake glasses] + 5*[milk glasses] >= 90
  protein requirement: 2*[protein shake glasses] + 1*[milk glasses] >= 85
  milk preference: 1*[milk glasses] - 3*[protein shake glasses] >= 0
  protein shake glasses: integer, in [0, inf]
  milk glasses: integer, in [0, inf]
```

## 7.

> A cell-phone company makes foldable and regular cell-phones in a factory that is divided into a hardware and software section. The hardware section must work 10 hours on each foldable cell-phone but only 3 hours on each regular one. The software section must work 3 hours for each cell-phone. The profit from the foldable cell-phone is $500 and the profit from the regular cell-phone is $300. Due to a recent strike, the hardware section only has 200 hours available per week and the software section only has 150 hours available per week. How many of each phone should the company produce to maximize profit?

Reference:
```
max 500*[foldable] + 300*[regular]
  c0_linear: 10*[foldable] + 3*[regular] <= 200
  c1_linear: 3*[foldable] + 3*[regular] <= 150
  foldable: integer, in [0, inf]
  regular: integer, in [0, inf]
```

To grade:
```
max 500*[foldable cell-phones produced] + 300*[regular cell-phones produced]
  hardware hours: 10*[foldable cell-phones produced] + 3*[regular cell-phones produced] <= 200
  software hours: 3*[foldable cell-phones produced] + 3*[regular cell-phones produced] <= 150
  foldable cell-phones produced: integer, in [0, inf]
  regular cell-phones produced: integer, in [0, inf]
```

## 8.

> An extremely large mall needs at least 100 transportation methods for customers to move up and down floors. They can either purchase an escalator or an elevator. Due to space limitations, there must be more escalators than elevators, but for convenience, there must be at least 10 elevators. An elevator can transport 1000 customers every day and uses 6 units of electricity in that time span. An escalator can transport 2400 customers every day and uses 9 units of electricity in that time span. The mall has available 800 units of electricity every day. How many of each transportation method should the mall install to maximize the number of customers they can transport every day?

Reference:
```
max 1000*[elevator] + 2400*[escalator]
  c0_sum: 1*[escalator] + 1*[elevator] >= 100
  c1_lowerbound: 1*[elevator] >= 10
  c2_linear: 6*[elevator] + 9*[escalator] <= 800
  escalator: integer, in [0, inf]
  elevator: integer, in [0, inf]
```

To grade:
```
max 2400*[escalators] + 1000*[elevators]
  total_transportation_methods: 1*[escalators] + 1*[elevators] >= 100
  more_escalators_than_elevators: 1*[escalators] - 1*[elevators] >= 1
  minimum_elevators: 1*[elevators] >= 10
  electricity_available: 9*[escalators] + 6*[elevators] <= 800
  escalators: integer, in [0, inf]
  elevators: integer, in [0, inf]
```

## 9.

> George has 120 acres of farmland on which to grow strawberries and watermelons Both fruits have to be watered and sprayed with bug repellant. There are 150 days per year available for watering and 100 days per year available for spraying bug spray. It takes 0.5 days to water an acre of strawberries and 1 day to spray an acre of strawberries. It takes 0.2 days to water an acre of watermelons and 2 days to spray an acre of watermelons. George earns a profit of $200 per acre of strawberries and $500 per acre of watermelons. How many acres of each fruit should be planted in order to maximize profit?

Reference:
```
max 200*[strawberries] + 500*[watermelons]
  c0_sum: 1*[strawberries] + 1*[watermelons] <= 120
  c1_linear: 0.5*[strawberries] + 0.2*[watermelons] <= 150
  c2_linear: 1*[strawberries] + 2*[watermelons] <= 100
  strawberries: continuous, in [0, inf]
  watermelons: continuous, in [0, inf]
```

To grade:
```
max 200*[strawberry acres] + 500*[watermelon acres]
  land: 1*[strawberry acres] + 1*[watermelon acres] <= 120
  watering: 0.5*[strawberry acres] + 0.2*[watermelon acres] <= 150
  spraying: 1*[strawberry acres] + 2*[watermelon acres] <= 100
  strawberry acres: continuous, in [0, inf]
  watermelon acres: continuous, in [0, inf]
```

## 10.

> A company is delivering packages using two methods, drones and couriers. A drone can transport 4 packages every hour while a courier can transport 25 packages every hour. Drones cost an average of $2 per hour to maintain and couriers are paid $20 per hour. The company needs to deliver at least 800 packages and they can spend at most $1300 per hour for delivery. Since drones have a high up-front cost, the number of drones cannot exceed the number of couriers. How many of each method of delivering packages should be used to minimize the total number of deliveries using drones and couriers?

Reference:
```
min 4*[drones] + 25*[couriers]
  c0_linear: 4*[drones] + 25*[couriers] >= 800
  c1_linear: 2*[drones] + 20*[couriers] <= 1300
  c2_xy: 1*[drones] - 1*[couriers] <= 0
  drones: integer, in [0, inf]
  couriers: integer, in [0, inf]
```

To grade:
```
min 1*[drones] + 1*[couriers]
  package_requirement: 4*[drones] + 25*[couriers] >= 800
  cost_budget: 2*[drones] + 20*[couriers] <= 1300
  drone_limit: 1*[drones] - 1*[couriers] <= 0
  drones: integer, in [0, inf]
  couriers: integer, in [0, inf]
```
