# Is each review right?

Below are 26 optimization word problems from a dataset. Each comes with the dataset's annotation (the reference model, with whole-number or fractional variables as the problem's label says), the answer that model gives, and a reviewer's claim about the problem, with the reviewer's reason. Decide whether the claim is right for the text as written, and answer:

- `agree`: the claim is right.
- `disagree`: it's wrong; say what's wrong in the reason.
- `unsure`: you can't tell from the text.

Judge against the text, not the annotation: the annotation can be wrong.

Reply with CSV only, and no other text: the header `number,problem_id,judgment,reason`, then one row per problem, with its number and problem id exactly as given, a judgment, and a one-sentence reason in double quotes.

## 1. `431521997`

> A bubble tea shop sells mango and lychee bubble tea. Each mango bubble tea requires 4 units of mango juice and 8 units of tea. Each lychee bubble tea requires 6 units of lychee juice and 6 units of tea. The shop has available 2000 units of mango juice and 3000 units of lychee juice. At least 40% of the bubble teas made must be lychee flavored. However, mango bubble tea sells better and thus the number of mango bubble teas made must be large than the number of lychee bubble teas made. How many of each bubble tea flavor should be made to minimize the total amount of tea needed?

Reference model (label: continuous):
```
min 8*[mango bubble tea] + 6*[lychee bubble tea]
  c0_linear: 4*[mango bubble tea] <= 2000
  c1_linear: 6*[lychee bubble tea] <= 3000
  c2_ratio: 0.6*[lychee bubble tea] - 0.4*[mango bubble tea] >= 0
  c3_xy: 1*[mango bubble tea] - 1*[lychee bubble tea] >= 0
  lychee bubble tea: continuous, in [0, inf]
  mango bubble tea: continuous, in [0, inf]
```

**Its answer:** 0  
**The claim:** As written, nothing has to be made, so making nothing (objective 0) is optimal. That's the right answer, if a trivial one.  
**The reviewer's reason:** nothing has to be made, so making nothing (objective 0) is optimal as written; each unlisted coefficient really is 0: the resource is used by one product only

## 2. `-1979635456`

> A bakery makes almond and pistachio croissants. An almond croissant requires 5 units of butter and 8 units of flour. A pistachio croissant requires 3 units of butter and 6 units of flour. The bakery has available 600 units of butter and 800 units of flour. Since the almond croissant is more popular, at least 3 times as many almond croissants should be made as pistachio croissants. If making an almond croissant takes 12 minutes and making a pistachio croissant takes 10 minutes, how many of each should be made to minimize the total production time?

Reference model (label: integer):
```
min 12*[almond] + 10*[pistachio]
  c0_linear: 5*[almond] + 3*[pistachio] <= 600
  c1_linear: 8*[almond] + 6*[pistachio] <= 800
  c2_xby: 1*[almond] - 3*[pistachio] >= 0
  almond: integer, in [0, inf]
  pistachio: integer, in [0, inf]
```

**Its answer:** 0  
**The claim:** As written, nothing has to be made, so making nothing (objective 0) is optimal. That's the right answer, if a trivial one.  
**The reviewer's reason:** nothing has to be made, so making nothing (objective 0) is optimal as written

## 3. `1151835649`

> A bakery makes fiber supplemented brownies and lemon squares. Each brownie requires 5 units of chocolate mix and 4 units of fiber. Each lemon square requires 7 units of lemon mix and 6 units of fiber. Lemon squares sell much faster and thus the number of lemon squares made must be larger than the number of brownies made. However, to please all customers, at least 40% of the items made must be brownies. If the bakery has 2500 units of chocolate mix and 3300 units of lemon mix, how many of each should be made to minimize the total amount of fiber needed?

Reference model (label: integer):
```
min 4*[brownies] + 6*[lemon squares]
  c0_xy: 1*[lemon squares] - 1*[brownies] >= 0
  c1_ratio: 0.6*[brownies] - 0.4*[lemon squares] >= 0
  c2_linear: 5*[brownies] <= 2500
  c3_linear: 7*[lemon squares] <= 3300
  brownies: integer, in [0, inf]
  lemon squares: integer, in [0, inf]
```

**Its answer:** 0; 26 (strict reading: c0_xy: >= 0 became >= 1)  
**The claim:** As written, nothing has to be made, so making nothing (objective 0) is optimal. That's the right answer, if a trivial one.  
**The reviewer's reason:** nothing has to be made, so making nothing (objective 0) is optimal as written; each unlisted coefficient really is 0: the resource is used by one product only

## 4. `-1584110645`

> A grilled cheese shop sells a light and heavy grilled cheese sandwich. A light grilled cheese sandwich requires 2 slices of bread and 3 slices of cheese. A heavy grilled cheese sandwich requires 3 slices of bread and 5 slices of cheese. Since most people who come to the store love grilled cheese, the store must make at least 3 times as many heavy grilled cheese sandwiches as light grilled cheese sandwiches. The store has available 300 slices of bread and 500 slices of cheese. If a light grilled cheese sandwich takes 10 minutes to make and a heavy grilled cheese sandwich takes 15 minutes to make, how many of each should they make to minimize the total production time?

Reference model (label: integer):
```
min 10*[light] + 15*[heavy]
  c0_xby: 1*[heavy] - 3*[light] >= 0
  c1_linear: 2*[light] + 3*[heavy] <= 300
  c2_linear: 3*[light] + 5*[heavy] <= 500
  light: integer, in [0, inf]
  heavy: integer, in [0, inf]
```

**Its answer:** 0  
**The claim:** As written, nothing has to be made, so making nothing (objective 0) is optimal. That's the right answer, if a trivial one.  
**The reviewer's reason:** nothing has to be made, so making nothing (objective 0) is optimal as written

## 5. `-468779640`

> A banana company sells their bananas in small and large crates. A small crate can hold 20 bananas while a large crate can hole 50 bananas. Since large crates are more manageable, the number of large crates must be at least twice the number of small crates. However, at least 5 small crates should be used. If the company has available 500 bananas, how many of each crate should the company use to maximize the total number of crates produced?

Reference model (label: integer):
```
max 1*[small] + 1*[large]
  c0_xby: 1*[large] - 2*[small] >= 0
  c1_lowerbound: 1*[small] >= 5
  c2_linear: 20*[small] + 50*[large] <= 500
  small: integer, in [0, inf]
  large: integer, in [0, inf]
```

**Its answer:** infeasible  
**The claim:** As written, the problem has no optimal solution: no choice meets every requirement, or the objective can improve without limit. That status is the right answer.  
**The reviewer's reason:** the minimums need 600 bananas; only 500 are available

## 6. `1605420061`

> A crepe store sells chocolate and peanut butter crepes. A chocolate crepe requires 3 units of chocolate spread and 6 units of crepe mix. A peanut butter crepe requires 4 units of peanut butter spread and 7 units of crepe mix. Recently, the peanut butter crepe has been more popular and therefore the number of peanut butter crepes made must exceed the number of chocolate crepes made. However at least 25% of the crepes made should be chocolate. The store has available 400 units of chocolate spread and 450 units of peanut butter spread. How many of each should the store make to minimize the total amount of crepe mix needed?

Reference model (label: continuous):
```
min 6*[chocolate crepe] + 7*[peanut butter crepes]
  c0_xy: 1*[peanut butter crepes] - 1*[chocolate crepe] >= 0
  c1_ratio: -0.25*[peanut butter crepes] + 0.75*[chocolate crepe] >= 0
  c2_linear: 3*[chocolate crepe] <= 400
  c3_linear: 4*[peanut butter crepes] <= 450
  peanut butter crepes: continuous, in [0, inf]
  chocolate crepe: continuous, in [0, inf]
```

**Its answer:** 0  
**The claim:** As written, nothing has to be made, so making nothing (objective 0) is optimal. That's the right answer, if a trivial one.  
**The reviewer's reason:** nothing has to be made, so making nothing (objective 0) is optimal as written; each unlisted coefficient really is 0: the resource is used by one product only

## 7. `498603121`

> A coffee shop sells mochas and regular coffees. Each mocha requires 3 units of coffee powder and 6 units of milk. Each regular coffee requires 6 units of coffee powder and 2 units of milk. The shop has available 400 units of coffee powder and 500 units of milk. Making a mocha takes 5 minutes and making a regular coffee takes 3 minutes. Since mochas are more popular among people, the shop must make at least 3 times as many mochas as regular coffees. How many of each should they make to minimize the total production time?

Reference model (label: integer):
```
min 5*[mochas] + 3*[regular coffees]
  c0_linear: 3*[mochas] + 6*[regular coffees] <= 400
  c1_linear: 6*[mochas] + 2*[regular coffees] <= 500
  c2_xby: 1*[mochas] - 3*[regular coffees] >= 0
  mochas: integer, in [0, inf]
  regular coffees: integer, in [0, inf]
```

**Its answer:** 0  
**The claim:** As written, nothing has to be made, so making nothing (objective 0) is optimal. That's the right answer, if a trivial one.  
**The reviewer's reason:** nothing has to be made, so making nothing (objective 0) is optimal as written

## 8. `-1540907330`

> An Indian restaurant makes goat and chicken curry. Each bowl of goat curry requires 3 units of goat meat and 6 units of the curry base. Each bowl of chicken curry requires 5 units of chicken meat and 5 units of the curry base. The restaurant has available 1500 units of goat meat and 2000 units of chicken meat. At least 25% of the bowls made must be chicken curry. Since goat curry is more popular, the number of goat curry bowls must be larger than the number of chicken curry bowls. How many of each type of curry bowl should be made to minimize the total amount of curry base used?

Reference model (label: continuous):
```
min 6*[goat] + 5*[chicken]
  c0_linear: 3*[goat] <= 1500
  c1_linear: 5*[chicken] <= 2000
  c2_ratio: -0.25*[goat] + 0.75*[chicken] >= 0
  c3_xy: 1*[goat] - 1*[chicken] >= 0
  goat: continuous, in [0, inf]
  chicken: continuous, in [0, inf]
```

**Its answer:** 0  
**The claim:** As written, nothing has to be made, so making nothing (objective 0) is optimal. That's the right answer, if a trivial one.  
**The reviewer's reason:** nothing has to be made, so making nothing (objective 0) is optimal as written; each unlisted coefficient really is 0: the resource is used by one product only

## 9. `-1603650758`

> A chemical plant can buy two types of generators, generator A and generator B, which use two different processes to generate hydrogen. Generator A uses an electrolysis process and produces 40 cubic meters of hydrogen as well as 300 units of pollutants every day. Generator B uses a fermentation process to produce 30 cubic meters of hydrogen per day while outputting 200 units of pollutants. The chemical plant must make a minimum of 1000 cubic meters of hydrogen per day but due to environmental restrictions they can produce at most 3000 units of pollutant. How many of each type of generator should they buy to minimize the number of generators needed?

Reference model (label: integer):
```
min 1*[generator A] + 1*[generator B]
  c0_linear: 40*[generator A] + 30*[generator B] >= 1000
  c1_linear: 300*[generator A] + 200*[generator B] <= 3000
  generator A: integer, in [0, inf]
  generator B: integer, in [0, inf]
```

**Its answer:** infeasible  
**The claim:** As written, the problem has no optimal solution: no choice meets every requirement, or the objective can improve without limit. That status is the right answer.  
**The reviewer's reason:** the pollution cap limits hydrogen to 450 m3/day, below the 1000 required

## 10. `492091808`

> A small chocolate shop makes milk chocolate and dark chocolate bars. Milk chocolate bars require 4 units of cocoa and 7 units of milk. Dark chocolate bars require 6 units of cocoa and 3 units of milk. The shop has 2000 units of cocoa and 1750 units of milk available. In addition since milk chocolate sells better, at least 2 times as many milk chocolate bars need to be made as dark chocolate bars.  If making a milk chocolate bar takes 15 minutes and making a dark chocolate bar takes 12 mins, how many of each should the make to minimize total production time?

Reference model (label: integer):
```
min 15*[milk chocolate] + 12*[dark chocolate bars]
  c0_linear: 4*[milk chocolate] + 6*[dark chocolate bars] <= 2000
  c1_linear: 7*[milk chocolate] + 3*[dark chocolate bars] <= 1750
  c2_xby: 1*[milk chocolate] - 2*[dark chocolate bars] >= 0
  milk chocolate: integer, in [0, inf]
  dark chocolate bars: integer, in [0, inf]
```

**Its answer:** 0  
**The claim:** As written, nothing has to be made, so making nothing (objective 0) is optimal. That's the right answer, if a trivial one.  
**The reviewer's reason:** nothing has to be made, so making nothing (objective 0) is optimal as written

## 11. `1268238141`

> A candy company is making peach flavored candy and cherry flavored candy. Each pack of peach flavored candy requires 3 units of peach flavoring and 5 units of special syrup. Each pack of cherry flavored candy requires 5 units of cherry flavoring and 4 units of special syrup. The company has available 3000 units of peach flavoring and 4000 units of cherry flavoring. Peach candy is much more popular and thus the number of peach candy packs must be larger than the number of cherry candy packs. In addition, at least 30% of the pack must be cherry flavored. How many of each should be made to minimize the total amount of special syrup used?

Reference model (label: integer):
```
min 5*[peach flavored candy] + 4*[cherry flavored candy]
  c0_linear: 3*[peach flavored candy] <= 3000
  c1_linear: 5*[cherry flavored candy] <= 4000
  c2_xy: 1*[peach flavored candy] - 1*[cherry flavored candy] >= 0
  c3_ratio: -0.3*[peach flavored candy] + 0.7*[cherry flavored candy] >= 0
  peach flavored candy: integer, in [0, inf]
  cherry flavored candy: integer, in [0, inf]
```

**Its answer:** 0; 14 (strict reading: c2_xy: >= 0 became >= 1)  
**The claim:** As written, nothing has to be made, so making nothing (objective 0) is optimal. That's the right answer, if a trivial one.  
**The reviewer's reason:** nothing has to be made, so making nothing (objective 0) is optimal as written; each unlisted coefficient really is 0: the resource is used by one product only

## 12. `1238353423`

> A drug company is making pain killers and sleeping pills using two processes, process 1 and process 2. Process 1 produces 35 units of pain killers and 12 units of sleeping pills per hour. Process 2 produces 50 units of pain killers and 30 units of sleeping pills per hour. Process 1 requires 50 units of preliminary material while process 2 requires 60 units of preliminary material. The drug company has available 2000 units of preliminary material and must make at least 1200 units of pain killers and 1200 units of sleeping pills. How many of each process should be run to minimize the total time needed?

Reference model (label: integer):
```
min 1*[process 1] + 1*[process 2]
  c0_linear: 50*[process 1] + 60*[process 2] <= 2000
  c1_linear: 35*[process 1] + 50*[process 2] >= 1200
  c2_linear: 12*[process 1] + 30*[process 2] >= 1200
  process 1: integer, in [0, inf]
  process 2: integer, in [0, inf]
```

**Its answer:** infeasible  
**The claim:** As written, the problem has no optimal solution: no choice meets every requirement, or the objective can improve without limit. That status is the right answer.  
**The reviewer's reason:** 2000 units of material give at most 1000 sleeping pills, below the 1200 required

## 13. `905906224`

> A restaurant has two combos available to their customers, an original and an experimental meal. The original meal typically generates 20 units of food waste and 45 units of wrapping waste and takes 10 minutes to cook. In comparison, the experimental meal generates 25 units of food waste and 35 units of wrapping waste and takes 15 minutes to cook. The restaurant can have at most 900 units of wrapping waste and can have at most 800 units of food waste as regulated by the government. How many of each combo should be pushed for by the waiting staff to minimize the cooking time?

Reference model (label: integer):
```
min 15*[experimental meal] + 10*[original]
  c0_linear: 35*[experimental meal] + 45*[original] <= 900
  c1_linear: 20*[original] + 25*[experimental meal] <= 800
  original: integer, in [0, inf]
  experimental meal: integer, in [0, inf]
```

**Its answer:** 0  
**The claim:** As written, nothing has to be made, so making nothing (objective 0) is optimal. That's the right answer, if a trivial one.  
**The reviewer's reason:** nothing has to be made, so making nothing (objective 0) is optimal as written

## 14. `-1704758994`

> A market owner wants to start a jam business. He can either sell one unit of jam to customers in a set of small packets or jugs. A set of small packets can hold 1000 ml of jam while a jug can hold 1250 ml of jam. Since a set of small packets are more expensive to make, at least three times as many jugs must be used than sets of small packets. On the other hand, at least 35 sets of small packets should be filled. If the market owner has 65000 ml of jam, how many sets of small packets or jugs should be selected to maximize the total number of units that he can sell to his customers?

Reference model (label: integer):
```
max 1*[small packets] + 1*[jugs]
  c0_xby: 1*[jugs] - 3*[small packets] >= 0
  c1_lowerbound: 1*[small packets] >= 35
  c2_linear: 1000*[small packets] + 1250*[jugs] <= 65000
  small packets: integer, in [0, inf]
  jugs: integer, in [0, inf]
```

**Its answer:** infeasible  
**The claim:** As written, the problem has no optimal solution: no choice meets every requirement, or the objective can improve without limit. That status is the right answer.  
**The reviewer's reason:** the minimums need 166,250 ml of jam; only 65,000 ml is available

## 15. `1278831553`

> A navy ship is stocking food onto their submarine and their staff can eat either a salad or fruit bowl for their fibre and vitamin intake. The nutritionist in charge of this voyage needs to ensure that their staff gets at least 90 units of vitamin and 110 units of fibre each. Each salad contains 7 units of vitamins and 12 units of fibre. Each fruit bowl contains 15 units of vitamin and 3 units of fibre. In addition, since fruit bowls take longer to prepare, at most 30% of their meals should be fruit bowls. If each salad contains 2 units of potassium and each fruit bowl contains 8 units of potassium, how many of each should they prepare for each staff to maximize their potassium intake?

Reference model (label: integer):
```
max 2*[salad] + 8*[fruit bowl]
  c0_linear: 15*[fruit bowl] + 7*[salad] >= 90
  c1_linear: 12*[salad] + 3*[fruit bowl] >= 110
  c2_ratio: -0.3*[salad] + 0.7*[fruit bowl] <= 0
  salad: integer, in [0, inf]
  fruit bowl: integer, in [0, inf]
```

**Its answer:** unbounded  
**The claim:** As written, the problem has no optimal solution: no choice meets every requirement, or the objective can improve without limit. That status is the right answer.  
**The reviewer's reason:** maximizes potassium subject only to minimum requirements, so it's unbounded

## 16. `1677678357`

> A soda company sells soda in two types of containers: cans and glass bottles. A can holds 250 ml of soda whereas a bottle holds 1000 ml of soda. The soda company needs to bottle at least 1000000 ml of soda every day and due to the ability to sell soda cans as packs, there must be at least three times more cans than glass bottles. However, because of previous contracts with gas stations, there must be at least 100 glass bottles made. How many of each should be made to maximize the total number of units produced?

Reference model (label: integer):
```
max 1*[cans] + 1*[glass bottles]
  c0_linear: 250*[cans] + 1000*[glass bottles] >= 1e+06
  c1_xby: 1*[cans] - 3*[glass bottles] >= 0
  c2_lowerbound: 1*[glass bottles] >= 100
  cans: integer, in [0, inf]
  glass bottles: integer, in [0, inf]
```

**Its answer:** unbounded  
**The claim:** As written, the problem has no optimal solution: no choice meets every requirement, or the objective can improve without limit. That status is the right answer.  
**The reviewer's reason:** maximizes units subject only to minimum requirements, so it's unbounded

## 17. `915960254`

> An autobody shop needs to purchase two types of car jacks, an automatic electric one, or a gas-powered one. The automatic electric one can process 5 cars every hour and uses 6 units of electricity whereas the gas-powered one can process 4 cars each hour using 7 units of gas. Since there is a limit to how many automatic electric ones there can be due to the limited number of power outlets, the shop must use less than 15 automatic electric ones. The shop can use at most 50 units of electricity and 80 units of gas. How many of each type of jack should the shop purchase to maximize the amount of cars processed every hour?

Reference model (label: integer):
```
max 4*[gas-powered one] + 5*[automatic electric one]
  c0_upperbound: 1*[automatic electric one] <= 15
  c1_linear: 6*[automatic electric one] <= 50
  c2_linear: 7*[gas-powered one] <= 80
  automatic electric one: integer, in [0, inf]
  gas-powered one: integer, in [0, inf]
```

**Its answer:** 84; 84 (strict reading: c0_upperbound: <= 15 became <= 14)  
**The claim:** The problem looked suspicious, but the annotated answer is right.  
**The reviewer's reason:** electricity is used only by the electric jacks and gas only by the gas-powered ones (coefficients 0)

## 18. `1197838065`

> A drop-in clinic is performing a test either through the ear or blood. A blood test takes 30 minutes to perform while an ear test takes 5 minutes to perform. Since the blood test is more accurate, at least three times as many blood tests should be performed as ear tests. However, at least 12 ear tests must be administered. If the drop-in clinic operates for 7525 minutes, maximize the number of tests that can be performed.

Reference model (label: integer):
```
max 1*[ear] + 1*[blood]
  c0_xby: 1*[blood] - 3*[ear] >= 0
  c1_lowerbound: 1*[ear] >= 12
  ear: integer, in [0, inf]
  blood: integer, in [0, inf]
```

**Its answer:** unbounded  
**The claim:** The annotated model doesn't say what the text says.  
**The reviewer's reason:** the 7525-minute opening-hours limit is missing, so the annotated model is unbounded

## 19. `1384123609`

> A researcher must perform two types of experiments, in-vivo and ex-vivo. In-vivo experiments requires 30 minutes to prepare and 60 minutes to execute. Ex-vivo experiments require 45 minutes to prepare and 30 minutes to execute. In addition, in-vivo experiments gives the researcher 2 units of radiation while ex-vivo experiments give the researcher 3 unites of radiation. At most 400 minutes can be used for preparation and 500 minutes for execution of the experiment. How many of each experiment should be scheduled by the researcher to minimize the total radiation received by the researcher?

Reference model (label: integer):
```
min 2*[in-vivo] + 3*[ex-vivo]
  c0_linear: 30*[in-vivo] + 45*[ex-vivo] <= 400
  c1_linear: 60*[in-vivo] + 30*[ex-vivo] <= 500
  in-vivo: integer, in [0, inf]
  ex-vivo: integer, in [0, inf]
```

**Its answer:** 0  
**The claim:** As written, nothing has to be made, so making nothing (objective 0) is optimal. That's the right answer, if a trivial one.  
**The reviewer's reason:** 'must perform' suggests at least one of each, but no number is given; as written the optimum is to do nothing

## 20. `249236183`

> A senior home has snacks of spinach and soybeans to increase their intake of iron. A cup of spinach contains 100 units of fibre and 5 mg of iron. A cup of soybeans contains 80 units of fibre and 12 mg of iron. Due to other nutritional requirements, the nurses decided that the number of cups of spinach must exceed the number of cups of soybeans. Furthermore, a cup of spinach contains 30 calories while a cup of soybeans contains 100 calories. If they schedule that the elderly need in total at least 12000 units of fibre and 300 mg of iron, how many cups of each should the nurses schedule to maximize the seniors’ total caloric intake?

Reference model (label: integer):
```
max 30*[spinach] + 100*[soybeans]
  c0_linear: 100*[spinach] + 80*[soybeans] >= 12000
  c1_linear: 5*[spinach] + 12*[soybeans] >= 300
  c2_xy: 1*[spinach] - 1*[soybeans] >= 0
  spinach: integer, in [0, inf]
  soybeans: integer, in [0, inf]
```

**Its answer:** unbounded; unbounded (strict reading: c2_xy: >= 0 became >= 1)  
**The claim:** As written, the problem has no optimal solution: no choice meets every requirement, or the objective can improve without limit. That status is the right answer.  
**The reviewer's reason:** maximizes calories subject only to minimum requirements, so it's unbounded

## 21. `-685300642`

> A dessert shop is popular for their only two desserts - matcha ice cream and orange sorbet. Two units of flavouring and four units of ice cream is required to make one order of matcha ice cream. Four units of flavouring and three units of water is required to make an order of orange sorbet. The dessert shop has recently been getting more orders online for orange sorbet and therefore, there should be more orange sorbet made than matcha ice cream. However, at least fifteen percent of desserts made must be matcha ice cream. The dessert shop has available 600 units of ice cream and 550 units of water. How many of each dessert should the shop make to minimize the total amount of flavouring needed?

Reference model (label: integer):
```
min 2*[matcha ice cream] + 4*[orange sorbet]
  c0_xy: 1*[orange sorbet] - 1*[matcha ice cream] >= 0
  c1_ratio: 0.85*[matcha ice cream] - 0.15*[orange sorbet] >= 0
  c2_linear: 4*[matcha ice cream] <= 600
  c3_linear: 3*[orange sorbet] <= 550
  matcha ice cream: integer, in [0, inf]
  orange sorbet: integer, in [0, inf]
```

**Its answer:** 0; 10 (strict reading: c0_xy: >= 0 became >= 1)  
**The claim:** As written, nothing has to be made, so making nothing (objective 0) is optimal. That's the right answer, if a trivial one.  
**The reviewer's reason:** nothing has to be made, so making nothing (objective 0) is optimal as written; each unlisted coefficient really is 0: the resource is used by one product only

## 22. `1878130600`

> A landscaper has 2500 square feet of grass land in a customer’s backyard where they need to cut grass using either a heavy-duty yard machine or a gas lawn mower. For each square foot of land, the heavy-duty yard machine requires 2 seconds while the gas lawn mower takes 5 seconds. Per square foot, the heavy-duty yard machine produces 12 units of pollution and requires 3 units of fuel. Conversely, the gas lawn mower generates 10 units of pollution for each square foot and requires 2 units of fuel. There are 450 units of fuel available and the landscaper can produce no more than 2000 units of pollution. For how many square feet should each machine be used to minimize the time required to cut this customer’s backyard?

Reference model (label: continuous):
```
min 5*[gas lawn mower] + 2*[heavy-duty yard machine]
  c0_linear: 2*[gas lawn mower] + 3*[heavy-duty yard machine] <= 450
  c1_linear: 12*[heavy-duty yard machine] + 10*[gas lawn mower] <= 2000
  c2_sum: 1*[heavy-duty yard machine] + 1*[gas lawn mower] <= 2500
  heavy-duty yard machine: continuous, in [0, inf]
  gas lawn mower: continuous, in [0, inf]
```

**Its answer:** 0  
**The claim:** The annotated model doesn't say what the text says.  
**The reviewer's reason:** the 2500 sq ft that must be cut is annotated as an upper limit (<= 2500); read as a requirement the text is infeasible (fuel)

## 23. `2018818116`

> A park is designing their trails and can either create a wide trail or a narrow trail. A wide trail can take 50 visitors every day while the narrow trail expects 20 visitors every day. The wide trail will introduce 6 units of garbage and the narrow trail will introduce 3 units of garbage. There can be at most 3 wide trails and the park hopes to have at most 225 visitors every day. How many of each type of trail should the park construct to minimize the total amount of garbage produced.

Reference model (label: integer):
```
min 6*[wide trail] + 3*[narrow trail]
  c0_linear: 50*[wide trail] + 20*[narrow trail] <= 225
  c1_upperbound: 1*[wide trail] <= 3
  wide trail: integer, in [0, inf]
  narrow trail: integer, in [0, inf]
```

**Its answer:** 0  
**The claim:** As written, nothing has to be made, so making nothing (objective 0) is optimal. That's the right answer, if a trivial one.  
**The reviewer's reason:** nothing has to be made, so making nothing (objective 0) is optimal as written

## 24. `2078392466`

> A brewery can ferment their product into either wine or kombucha. Each unit of wine requires 3 units of fruit and 8 units of water. Each unit of kombucha requires 5 units of fruit and 7 units of tea. The company has available 7000 units of water and 9000 units of tea. Wine sells for more, therefore the number of wine must be larger than the number of kombucha. Additionally, at least 20% of their products made must be kombucha. How many of each should the brewery make to minimize the total units of fruit required?

Reference model (label: continuous):
```
min 3*[wine] + 5*[kombucha]
  c0_linear: 8*[wine] <= 7000
  c1_linear: 7*[kombucha] <= 9000
  c2_xy: 1*[wine] - 1*[kombucha] >= 0
  c3_ratio: -0.2*[wine] + 0.8*[kombucha] >= 0
  wine: continuous, in [0, inf]
  kombucha: continuous, in [0, inf]
```

**Its answer:** 0  
**The claim:** As written, nothing has to be made, so making nothing (objective 0) is optimal. That's the right answer, if a trivial one.  
**The reviewer's reason:** nothing has to be made, so making nothing (objective 0) is optimal as written; each unlisted coefficient really is 0: the resource is used by one product only

## 25. `1283305022`

> A cleaning company uses a cleansing chemical and odor-removing chemical to clean a house. Each unit of the cleansing chemical takes 4 units to be effective while each unit of the odor-removing chemical takes 6 minutes to be effective. The company must use at least 100 units of the cleansing chemical. In total, at least 300 units of chemicals can be used per house. Further, because the cleansing chemical is strong, there can be at most twice the amount of cleansing chemical as odor-removing chemical. How many units of each should be used to minimize the total time it takes for a house to be cleaned?

Reference model (label: continuous):
```
min 4*[cleansing chemical] + 6*[odor-removing chemical]
  c0_lowerbound: 1*[cleansing chemical] >= 100
  c1_sum: 1*[cleansing chemical] + 1*[odor-removing chemical] >= 300
  c2_xby: 1*[cleansing chemical] - 2*[odor-removing chemical] <= 0
  cleansing chemical: continuous, in [0, inf]
  odor-removing chemical: continuous, in [0, inf]
```

**Its answer:** 1400  
**The claim:** The annotated model says what the text says, so its answer is right.  
**The reviewer's reason:** (no review: this is the annotation's claim)

## 26. `-1715698555`

> A recycling company collects recycling from neighborhoods using small and large bins. A small bin requires 2 workers while a large bin requires 5 workers. A small bin can hold 25 units of recycling material and a large bin can hold 60 units of recycling material. The company has available 100 workers. Because most people don't recycle, the number of small bins must be three times the number of large bins. In addition, there must be at least 10 small bins and 4 large bins. How many of each bin type should be used to maximize the total amount of recycling material that can be collected?

Reference model (label: integer):
```
max 25*[small] + 60*[large bins]
  c0_linear: 2*[small] + 5*[large bins] <= 100
  c1_xby: 1*[small] - 3*[large bins] >= 0
  c2_lowerbound: 1*[small] >= 10
  c3_lowerbound: 1*[large bins] >= 4
  small: integer, in [0, inf]
  large bins: integer, in [0, inf]
```

**Its answer:** 1240; 1215 (equality reading: c1_xby: >= 0 became == 0)  
**The claim:** The text supports more than one reading of one constraint, and each reading's answer below is right.  
**The reviewer's reason:** 'must be three times the number of large bins': >= (annotation, 1240) or = (1215 as integers)
