# Error taxonomy: `dev-1`

The 7 distinct silent failures in `runs/dev-1` (the dev split): answers that were confirmed (or, for the baseline, parsed) but are wrong. For each, write one category in the `category` column of `labels.csv`, for its main error: the one whose fix alone would give an accepted answer, if there is one. Any other errors go in `note`. Then run `python -m opt_agent.report runs/dev-1`.

**If this run has a blind-grading packet (`review/blind_grading/`), grade it first**: this one shows which answers are wrong.

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

## 1. `793774916`: baseline (key `e64fe050e36b`)

> A bakery sells two types of cakes. They sell a chocolate cake and a vanilla cake. Let's say they make x1 chocolate cakes, at a profit of $10 each, and x2 vanilla cakes, at a profit of $11 each (x1 and x2 are unknowns both greater than or equal to 0). The daily demand for these cakes is at most 50 chocolate cakes and at most 30 vanilla cakes. The bakery is short staffed and can make a maximum of 50 cakes of either type per day. How much of each cake should the bakery make in order to maximize profit?

**Answered:** optimal 830  
**Accepted:** optimal 530 (annotated)  
**As annotated:** LP optimal 530, IP optimal 530; label continuous (rule)

Reference (the annotation, with its label):
```
max 10*[chocolate cake] + 11*[vanilla cake]
  c0_upperbound: 1*[chocolate cake] <= 50
  c1_upperbound: 1*[vanilla cake] <= 30
  c2_sum: 1*[chocolate cake] + 1*[vanilla cake] <= 50
  chocolate cake: continuous, in [0, inf]
  vanilla cake: continuous, in [0, inf]
```

No model: the baseline answers directly.

## 2. `562583112`: baseline (key `dd4985001fb0`)

> A company is delivering packages using two methods, drones and couriers. A drone can transport 4 packages every hour while a courier can transport 25 packages every hour. Drones cost an average of $2 per hour to maintain and couriers are paid $20 per hour. The company needs to deliver at least 800 packages and they can spend at most $1300 per hour for delivery. Since drones have a high up-front cost, the number of drones cannot exceed the number of couriers. How many of each method of delivering packages should be used to minimize the total number of deliveries using drones and couriers?

**Answered:** optimal 32  
**Accepted:** optimal 800 (annotated)  
**As annotated:** LP optimal 800, IP optimal 800; label integer (rule)

- The same answer as row 3's model.

Reference (the annotation, with its label):
```
min 4*[drones] + 25*[couriers]
  c0_linear: 4*[drones] + 25*[couriers] >= 800
  c1_linear: 2*[drones] + 20*[couriers] <= 1300
  c2_xy: 1*[drones] - 1*[couriers] <= 0
  drones: integer, in [0, inf]
  couriers: integer, in [0, inf]
```

No model: the baseline answers directly.

## 3. `562583112`: single-shot, self-correction (key `9edce1ec8e1d`)

> A company is delivering packages using two methods, drones and couriers. A drone can transport 4 packages every hour while a courier can transport 25 packages every hour. Drones cost an average of $2 per hour to maintain and couriers are paid $20 per hour. The company needs to deliver at least 800 packages and they can spend at most $1300 per hour for delivery. Since drones have a high up-front cost, the number of drones cannot exceed the number of couriers. How many of each method of delivering packages should be used to minimize the total number of deliveries using drones and couriers?

**Answered:** optimal 32  
**Accepted:** optimal 800 (annotated)  
**As annotated:** LP optimal 800, IP optimal 800; label integer (rule)

Reference (the annotation, with its label):
```
min 4*[drones] + 25*[couriers]
  c0_linear: 4*[drones] + 25*[couriers] >= 800
  c1_linear: 2*[drones] + 20*[couriers] <= 1300
  c2_xy: 1*[drones] - 1*[couriers] <= 0
  drones: integer, in [0, inf]
  couriers: integer, in [0, inf]
```

Claude's model:
```
min 1*[drones] + 1*[couriers]
  package_requirement: 4*[drones] + 25*[couriers] >= 800
  cost_budget: 2*[drones] + 20*[couriers] <= 1300
  drone_limit: 1*[drones] - 1*[couriers] <= 0
  drones: integer, in [0, inf]
  couriers: integer, in [0, inf]
```

## 4. `-1303541177`: single-shot, self-correction (key `fc37997ef2ef`)

> A physics class is performing a volcano experiment using two mixtures, mixture A and mixture B. Mixture A uses 3 units of baking soda, 5 units of vinegar, and produces 2 units of eruption. Mixture B uses 4 units of baking soda, 7 units of vinegar, and produces 4 units of eruption. However, mixture A generates 2 units of garbage and mixture B generates 1 unit of garbage. The physics class has available 200 units of baking soda and 300 units of vinegar. If at most 60 units of garbage can be generated, how many of each type of mixture should be used to maximize the total amount of eruption produced?

**Answered:** optimal 171.428572  
**Accepted:** optimal 170 (annotated)  
**As annotated:** LP optimal 171.428572, IP optimal 170; label integer (claude)

- Correct if integrality weren't graded (the lenient score, 3f).

Reference (the annotation, with its label):
```
max 2*[mixture A] + 4*[mixture B.]
  c0_linear: 3*[mixture A] + 4*[mixture B.] <= 200
  c1_linear: 5*[mixture A] + 7*[mixture B.] <= 300
  c2_linear: 2*[mixture A] + 1*[mixture B.] <= 60
  mixture A: integer, in [0, inf]
  mixture B.: integer, in [0, inf]
```

Claude's model:
```
max 2*[mixture A batches] + 4*[mixture B batches]
  baking soda: 3*[mixture A batches] + 4*[mixture B batches] <= 200
  vinegar: 5*[mixture A batches] + 7*[mixture B batches] <= 300
  garbage: 2*[mixture A batches] + 1*[mixture B batches] <= 60
  mixture A batches: continuous, in [0, inf]
  mixture B batches: continuous, in [0, inf]
```

## 5. `-577606329`: baseline (key `8f5558d857f5`)

> There are two methods of extracting a chemical element, method X and method Y.  Method X requires 5 atomic units (au) of aluminum, 1 au of oxygen, and can extract 0.5 au of the desired chemical element. Method Y requires 6 au of aluminum, 2 au of oxygen, and can extract 0.7 au of the desired chemical element. There are 650 au of aluminum, and 425 au of oxygen available. What is the best combination of these two methods to maximize the total amount of desired chemical element?

**Answered:** optimal 75.83333333  
**Accepted:** optimal 75.6 (annotated)  
**As annotated:** LP optimal 75.833331, IP optimal 75.6; label integer (claude)

- Correct if integrality weren't graded (the lenient score, 3f).
- The same answer as row 6's model.

Reference (the annotation, with its label):
```
max 0.5*[method X] + 0.7*[method Y.]
  c0_linear: 5*[method X] + 6*[method Y.] <= 650
  c1_linear: 1*[method X] + 2*[method Y.] <= 425
  method X: integer, in [0, inf]
  method Y.: integer, in [0, inf]
```

No model: the baseline answers directly.

## 6. `-577606329`: single-shot, self-correction (key `efbb5818d19b`)

> There are two methods of extracting a chemical element, method X and method Y.  Method X requires 5 atomic units (au) of aluminum, 1 au of oxygen, and can extract 0.5 au of the desired chemical element. Method Y requires 6 au of aluminum, 2 au of oxygen, and can extract 0.7 au of the desired chemical element. There are 650 au of aluminum, and 425 au of oxygen available. What is the best combination of these two methods to maximize the total amount of desired chemical element?

**Answered:** optimal 75.833331  
**Accepted:** optimal 75.6 (annotated)  
**As annotated:** LP optimal 75.833331, IP optimal 75.6; label integer (claude)

- Correct if integrality weren't graded (the lenient score, 3f).

Reference (the annotation, with its label):
```
max 0.5*[method X] + 0.7*[method Y.]
  c0_linear: 5*[method X] + 6*[method Y.] <= 650
  c1_linear: 1*[method X] + 2*[method Y.] <= 425
  method X: integer, in [0, inf]
  method Y.: integer, in [0, inf]
```

Claude's model:
```
max 0.5*[method X runs] + 0.7*[method Y runs]
  aluminum: 5*[method X runs] + 6*[method Y runs] <= 650
  oxygen: 1*[method X runs] + 2*[method Y runs] <= 425
  method X runs: continuous, in [0, inf]
  method Y runs: continuous, in [0, inf]
```

## 7. `-1389517053`: baseline (key `2795a876d06e`)

> A chemical company makes an acidic liquid and a basic liquid using two types of techniques, reaction X and reaction Y. Reaction X can make 35 au of the acidic liquid and 75 au of the basic liquid per minute. Reaction Y can make 42 au of the acidic liquid and 35 au of the basic liquid per minute. Furthermore, reaction X requires 18 units of heat every minute while reaction Y requires 12 units of heat every minute. The chemical company has the capacity to generate at most 1400 units of heat every minute. If the chemical company needs to make at least 900 au of the acidic liquid and 1200 au of the basic liquid per minute, how many minutes should each reaction be run for to minimize the total time needed?

**Answered:** optimal 23.065  
**Accepted:** optimal 23.0649348 (annotated)  
**As annotated:** LP optimal 23.0649348, IP optimal 24; label continuous (claude)

- Within 0.0001 of an accepted answer.

Reference (the annotation, with its label):
```
min 1*[reaction X] + 1*[reaction Y.]
  c0_linear: 35*[reaction X] + 42*[reaction Y.] >= 900
  c1_linear: 75*[reaction X] + 35*[reaction Y.] >= 1200
  c2_linear: 18*[reaction X] + 12*[reaction Y.] <= 1400
  reaction X: continuous, in [0, inf]
  reaction Y.: continuous, in [0, inf]
```

No model: the baseline answers directly.
