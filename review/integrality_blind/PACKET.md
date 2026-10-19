# Blind integrality labels

40 problems drawn at random (seed 20261019, `python -m opt_agent.packets integrality`) from the 131 scorable test problems where integer vs continuous changes the answer. Our labels are deliberately not shown; please don't open `data/nl4opt/integrality.json`, or the review packet (`review/test_reviews/`, which shows labels), until you're done.

For every variable, write `integer` or `continuous` in the `label` column of `labels.csv`, by what the text says it counts or measures. Then run `python -m opt_agent.packets agreement`.

## 1. `1695786577`

> A railway company is planning the infrastructure for the city and is considering two types of transportation, trains and trams. Each train can transport 120 people per hour comfortably and each tram can transport 30 people per hour comfortably. Since trains take longer to build, the number of trams must be at least twice the number of trains. If the railway company wants to transport at least 600 people per hour, minimize the total number of transportation units required.

Variables: `trains`, `trams`

## 2. `-355557676`

> A pharmacy makes eye cream and foot cream using two different machines, machine 1 and machine 2. Machine 1 can  make 30 ml of eye cream and 60 ml of foot cream per hour. Machine 2 can make 45 ml of eye cream and 30 ml of foot cream per hour. Furthermore, machine 1 requires 20 ml of distilled water per hour while machine 2 requires 15 ml of distilled water per hour. The pharmacy has available 1200 ml of distilled water. If the pharmacy needs to make at least 1300 ml of eye cream and 1500 ml of foot cream, how many hours should each machine be used to minimize the total time needed?

Variables: `machine 1`, `machine 2`

## 3. `-926961422`

> A music company produces two types of digital keyboards, one is full-weighted and another is semi-weighted. Both keyboards are sold for $2800 and $2400 respectively. There are about 3500 oscillator chips available every day from which the full-weighted version requires 20 chips while the semi-weighted version requires 15 chips. The company has a total of 6 working hours a day. Both of these keyboards require a production time of 1.2 hours. What should be the manufacturing quantity for each of the keyboards to maximize the total revenue?

Variables: `full-weighted`, `semi-weighted`

## 4. `721056636`

> A bee farmer transports his honey in small and large bottles. A small bottle can take 5 units of honey while a large bottle can take 20 units of honey. The farmer has available at most 300 small bottles and at most 100 large bottles. In addition, since small bottles are easier to sell, at least twice as many small bottles must be used than large bottles. Finally, he can transport at most 200 bottles total and at least 50 must be large bottles. How many of each bottle should be use to maximize the total amount of honey he can transport?

Variables: `small`, `large`

## 5. `1294399767`

> Platinum Database sells two types of subscription software packages: a personal license and a commercial license which will cost $550 and $2000 to generate respectively. The marketing department estimates that they can sell at most 300 licenses for both versions combined a month. The profit per personal license is $450 and the profit per commercial version is $1200. If the company does not want to spend more than $400000, how many of each software package should they produce to maximize the profits.

Variables: `personal license`, `commercial license`

## 6. `-443833341`

> Maple Oil processes three types of crude oil: light oil, non-sticky oil and heavy oil. Each tank of light oil produces a net revenue of $550, each tank of non-sticky oil produces a net revenue of $750, and each tank of heavy oil produces a net revenue of $950. To process a tank of light oil, 3 units of compound A and 3 units of compound B are required. To process a tank of non-sticky oil, 6 units of compound A and 2 units of compound B are required. To process a tank of heavy oil, 9 units of compound A and 3 units of compound B are required. Currently the company has 250 units of compound A and 150 units of compound B to process. How many full or partial tanks of each oil should the company process so that net revenue is maximized?

Variables: `light oil`, `non-sticky oil`, `heavy oil`

## 7. `-382781648`

> A candy store mixes regular candy and sour candy to prepare two products, regular mix and sour surprise mix. Each kilogram of the regular mix contains 0.8 kg of regular candy and 0.2 kg of sour candy. The profit per kilogram of the regular mix is $3. Each kilogram of the sour surprise mix contains 0.1 kg of regular candy and 0.9 kg of sour candy. The profit per kilogram of the sour surprise mix is $5. The candy store has 80 kg of regular candy and 60 kg of sour candy available. How many kilograms of each type of candy mix should be created to maximize profits?

Variables: `regular mix`, `sour surprise mix`

## 8. `1973401520`

> Calcium and Magnesium are found in two health supplements, health supplement A and health supplement B. One serving of health supplement A contains 30 grams of Calcium and 50 grams of Magnesium. One serving of health supplement B contains 60 grams of Calcium and 10 grams of Magnesium. The cost per health supplement for health supplement A is $14 and the cost per health supplement for health supplement B is $25. A patient must consume these two health supplements every day to get at least 400 grams of Calcium and 50 grams of Magnesium. Determine how much servings of each supplement the patient needs to minimize her daily cost.

Variables: `health supplement A`, `health supplement B.`

## 9. `-1396068089`

> A golf course is hosting an event and can transport guests using either golf carts or pull carts. A golf cart can take 4 guests while a pull cart can take 1 guest. Since golf carts take up a lot of space, at most 60% of carts can be golf carts. If the golf course needs to transport at least 80 guests, how many of each cart should be used to minimize the total number of carts needed?

Variables: `golf carts`, `pull carts`

## 10. `-578452959`

> A school is organizing a field trip to a science center and wants to hire small buses and large buses. A small bus can carry 20 students while a large bus can carry 50 students.  The school needs to provide transportation for at least 500 students.  In addition, since the parking lot is rather small, a maximum of 20% of the buses can be large buses. How many of each type of bus should be hired to minimize the total number of buses?

Variables: `small buses`, `large buses`

## 11. `-1819716628`

> A patient in the hospital can take two different pain killers, pain killer 1 and pain killer 2. Per dose, pain killer 1 delivers 0.5 units of medicine to the legs and 0.8 units of medicine to the back. Per dose, pain killer 2 delivers 0.7 units of medicine to the legs and 0.4 units of medicine to the back. In, addition pain killer 1 deliver 0.3 units of sleeping medicine and pain killer 2 delivers 0.6 units of sleeping medicine. At most 8 units of sleep medicine should be delivered and at least 4 units of medicine should be delivered to the legs. How many doses of each should be taken to maximize the amount of medicine delivered to the back?

Variables: `pain killer 1`, `pain killer 2`

## 12. `-1023375267`

> A sailor can eat either a crab cakes or a lobster roll for his meals. He needs to ensure he gets at least 80 units of vitamin A and 100 units of vitamin C. Each crab cake contains 5 units of vitamin A and 7 units of vitamin C. Each lobster roll contains 8 units of vitamin A and 4 units of vitamin C. In addition, since lobster is more expensive, at most 40% of his meals should be lobster rolls. If each crab cake contains 4 units of unsaturated fat and each lobster roll contains 6 units of unsaturated fat, how many of each should he eat to minimize his unsaturated fat intake?

Variables: `crab cakes`, `lobster roll`

## 13. `2005236115`

> Mr. Roberts want to invest in the telecom and healthcare industries. He has $100000 to invest. He has decided that the amount invested in telecom be at least three times as much as the amount invested in healthcare. But the money invested in telecom must be at most $70000. If investments in telecom earn 3% and investments in healthcare earn 1%, how much should Mr. Roberts invest in each to maximize profit?

Variables: `telecom`, `healthcare`

## 14. `892143253`

> A magic school sends letters to student either by carrier pigeons or owls. A carrier pigeon can carry two letters at a time and requires 3 treats for service. An owl can carry 5 letters at a time and requires 5 treats for service.  At most 40% of the birds can be owls. In addition, the school only has 1000 treats available and at least 20 carrier pigeons must be uses. How many of each bird can be used to maximize the total number of letters that can be sent.

Variables: `carrier pigeons`, `owls`

## 15. `861462634`

> There is 1000 mg of gold available that is needed to make long and short cables. Long cables require 10 mg of gold while short cables require 7 mg of gold. Because of their compact size, at least 5 times the number of short cables are needed than the long cables. In addition, there needs to be at least 10 long cables made. If each long cable sold results in a $12 profit and each short cable sold results in a $5 profit, how many of each type of cable should be made to maximize profit?

Variables: `long`, `short cables`

## 16. `-964250787`

> Ayse produces a plant growth compound by mixing two types of fertilizer: C and Y. This growth compound must contain at least 5 units of nitrous oxide and 8 units of vitamin mix. Fertilizer C and Y cost $2 and $3 per kg respectively. Fertilizer C contains 1.5 units of nitrous oxide per kg and 3 units of vitamin mix per kg. Fertilizer Y contains 5 units of nitrous oxide per kg and 1 unit of vitamin mix per kg. Determine the minimum cost of Ayse's compound.

Variables: `C`, `Y.`

## 17. `981967779`

> A car manufacturing company makes hamburgers and chicken wraps for workers. They need to ensure workers get at least 2200 calories, 50 grams of protein, and 70 grams of carbs. One hamburger costs $6.5 and contains 800 calories, 19 grams of protein, and 20 grams of carbs. One chicken wrap costs $4 and contains 450 calories, 12 grams of protein, and 10 grams of carbs. What is the minimum cost diet that the company can provide for its workers?

Variables: `hamburgers`, `chicken wraps`

## 18. `844555197`

> A hot dog company can build two types of butcher shops, a small shop and a large shop. A small shop can make 30 hot dogs per day and requires 2 workers. A large shop can make 70 hot dogs per day and requires 4 workers. The company must make at least 500 hot dogs per day but they only have available 30 workers. How many of each butcher shop should the company build to minimize the total number of butcher shops?

Variables: `small shop`, `large shop`

## 19. `1402521519`

> A lab has 20000 mg of mRNA anti-viral available to make children's and adult vaccines. Each children's vaccine contains 50 mg of mRNA and 50 mg of fever suppressant. Each adult vaccine contains 75 mg of mRNA and 75 mg of fever suppressant. Since adult vaccines are more essential, at least 70% of vaccines should be adult vaccines. However, at least 50 children's vaccines should be made. How many of each vaccine should be made to minimize the amount of fever suppressant used?

Variables: `children's`, `adult vaccines`

## 20. `-530211023`

> A patient takes anxiety medication and anti-depressants one after the other. Each unit of anxiety medication takes 3 minutes to be effective while each unit of anti-depressant takes 5 minutes to be effective. The patient must take at least 100 units of medication and at least 30 should be anxiety medication. Since the anxiety medication is strong, the patient can take at most twice the amount of anxiety medication as anti-depressants. How many units of each should the patient take to minimize the total time it take for the medication to be effective?

Variables: `anxiety medication`, `anti-depressants one`

## 21. `-1598952138`

> A car manufacturer ships their cars on large and small planes. A large plane can carry 30 cars while a small plane can carry 10 cars. Since large planes cause more pollution, the number of large planes must be less than the number of small planes. If the manufacturer wants to deliver at least 300 cars, find the minimum number of planes that can be used.

Variables: `large`, `small`

## 22. `-1609306796`

> A shoe company supplies shoes to stores via vans and trucks. A van can transport 50 pairs of shoes while a truck can transport 100 pairs of shoes. The company must supply a minimum of 2000 pairs of shoes around the city. Since most stores are small, the number of trucks used cannot exceed the number of vans used.  Find the minimum number of vans that can be used?

Variables: `vans`, `trucks`

## 23. `-717448510`

> A volunteer organization transports voters to the polls on Election Day either by vans or cars. They have vans which can carry 6 people and cars which can carry 3 people.  They need to transport at least 200 voters to the polls. In addition, at most 30% of the vehicles can be vans. How many of each vehicle should be used to minimize the total number of cars used?

Variables: `vans`, `cars`

## 24. `587452310`

> An office company makes desks and drawers. Each desk requires 40 minutes of assembly and 20 minutes of sanding. Each drawer requires 30 minutes of assembly and 10 minutes of sanding. The company has available 4000 minutes for assembly and 3500 minutes for sanding. If the profit per desk is $100 and the profit per drawer is $90, how many of each should the company make to maximize profit?

Variables: `desks`, `drawers`

## 25. `-369455986`

> A clinic administers two vaccines available for the public to take one at a time. One vaccine is taken as a pill and another is taken as a shot. The pill vaccine takes 10 minutes to administer while the shot takes 20 minutes to administer. Since the shot has been more thoroughly studied, the clinic must deliver at least 3 times as many shots as pill. In addition, the clinic must administer at least 30 pill vaccines. If the clinic only operates for 10000 minutes, maximize the number of patients that can be vaccinated.

Variables: `pill`, `shot`

## 26. `-352305044`

> A farmer on an island sends corn to the main land either by ferry or light rail. Each ferry trip can take 20 boxes of corn while each light rail trip can take 15 boxes of corn. Since ferry trips are slow, the number of light rail trip has to be at least 4 times the number of ferry trips. If the farmer wants to send at least 500 boxes of corn, minimize the total number of trips of either type needed.

Variables: `ferry`, `light rail`

## 27. `102495722`

> A doctor suggests that his patient eat oranges and grapefruit to meet his vitamin C and vitamin A requirements. One orange contains 5 units of vitamin C, 3 units of vitamin A, and 5 grams of sugar. One grapefruit contains 7 units of vitamin C, 5 units of vitamin A, and 6 grams of sugar. The patient must get at least 80 units of vitamin C and 70 units of vitamin A. Since the patent prefers oranges, he must eat at least 2 times as many oranges as grapefruit. How many of each should he eat to minimize his sugar intake?

Variables: `oranges`, `grapefruit`

## 28. `37344130`

> A young boy is trying to grow taller by drinking milk and eating vegetables. He wants to get a minimum of 100 units of calcium and 50 units of iron per day. A glass of milk costs $1 and contains 40 units of calcium and 25 units of iron. A plate of vegetables costs $2 and contains 15 units of calcium and 30 units of iron. How many of each should he consume to minimize his cost?

Variables: `milk`, `vegetables`

## 29. `-1981528237`

> A shipping company need to transport packages by either truck or car. A truck can transport 50 packages per trip while a car can transport 30 packages per trip. In addition, a truck uses 20 liters of gas per trip while a car uses 15 liters of gas per trip. There can be at most 5 truck trips made and at least 30% of all the trips must be made by car. The company needs to transport at least 500 packages. How many of each transportation should they use to minimize the total amount of gas consumed?

Variables: `truck`, `car`

## 30. `-737389251`

> A hospital purchases two pills available for the patients to take one at a time. One pill is taken as a prevention and another is taken for treatment. The prevention pill takes 15 dollars to make while the treatment pill takes 25 dollars to make. Since the prevention pill is in higher demand, the hospital must purchase at least two times as many prevention pills as treatment pills. In addition, the hospital must purchase at least 50 treatment pills. If the clinic only has a budget of 10000 dollars, maximize the number of patients that can be treated.

Variables: `prevention`, `treatment`

## 31. `-568965344`

> The government is reworking the pipes to transport water to houses in the area. The water can be transported through wide pipes or narrow pipes. Wide pipes can transport 25 units of water per minute and narrow pipes can transport 15 units of water per minute. Due to logistics, the number of wide pipes can be at most a third the number of narrow pipes. If there needs to be at least 900 units of water transported every minute, and at least 5 wide pipes must be used, minimize the total number of pipes required.

Variables: `wide pipes`, `narrow pipes`

## 32. `-125243875`

> A toy store hires seasonal and full-time volunteers to deliver gifts and gives them points for service. A seasonal volunteer can deliver 5 gifts and gets 2 points. A full-time volunteer can deliver 8 gifts and gets 5 points. The store can only give out 200 points. In addition, a maximum of 30% of the volunteers can be seasonal and at least 10 must be full-time. How many of each volunteer is needed to maximize the total number of gifts that can be delivered?

Variables: `seasonal`, `full-time`

## 33. `1333247991`

> An office is buying printers for their headquarters, a premium model and regular model. The premium model can print 30 pages per minute while the regular model can print 20 pages per minute. In addition, the premium model requires 4 units of ink per minute while the regular model requires 3 units of ink per minute. The office wants to make sure that at least 200 pages can be printed per minute and that at most 35 units of ink are used per minute.  Since the premium model is more user friendly, the number regular printers must be less than the number of premium printers. How many of each printer should be bought to minimize the total number of printers in the office?

Variables: `premium model`, `regular model`

## 34. `1738773919`

> A village delivers mail to nearby villages either by runners or canoers. Runners can carry three bags of mail each time and takes 4 hours. Canoers can carry ten bags of mail each time and takes 2 hours. At most 33% of deliveries can be by canoe. Additionally, the village can spare at most 200 total hours and at least 4 runners must be used. How many of each way to deliver must be used to maximize the total amount of mail that can be delivered?

Variables: `runners`, `canoers`

## 35. `-550351289`

> A company in the desert can transport goods to rural cities either by camel caravans or desert trucks. A camel caravan can deliver 50 units of goods per trip and takes 12 hours. A desert truck can deliver 150 units of goods per trip and takes 5 hours. However, due to the cost of fuel, the company prefers to have more camel caravans than desert trucks.  If the company needs to deliver 1500 units of goods, how many of each method of transportation should the company organize to minimize the total number of hours required?

Variables: `camel caravans`, `desert trucks`

## 36. `465775172`

> An appliance company sells and installs refrigerators and stoves. Each refrigerator takes 60 minutes of mover time and 20 minutes of setup time. Each stove takes 45 minutes of mover time and 25 minutes of setup time. The company has available 20000 minutes of mover time and 13000 minutes of setup time. If the profit per refrigerator is $400 and the profit per stove is $260, how many of each should they sell in order to maximize profit?

Variables: `refrigerators`, `stoves`

## 37. `256126407`

> Forest Paper makes two types of products: graph paper and music paper. Each type of paper requires the use of two machines, a printing machine and a scanning machine. It takes 3 minutes on the printing machine and 5.5 minutes on the scanning machine to make a ream of graph paper. On the other hand, it takes 1.5 minutes on the printing machine and 3 minutes on the scanning machine to make a ream of music paper. Each machine is available for a maximum of 350 minutes per day. The company sells a package of graph paper at a profit of $4 and a package of music paper at a profit of $2.5. The company can sell all the paper it makes. How many reams of each type should the company produce in a day in order to maximize profit? What is that profit?

Variables: `graph paper`, `music paper`

## 38. `1475265046`

> A pharmacy has 3000 mg of morphine to make painkillers and sleeping pills. Each painkiller pill requires 10 mg of morphine and 3 units of digestive medicine. Each sleeping pill requires 6 mg of morphine and 5 units of digestive medicine. The pharmacy needs to make at least 50 painkiller pills. Since sleeping pills are more popular, at least 70% of the pills should be sleeping pills. How many of each should the pharmacy make to minimize the total amount of digestive medicine needed?

Variables: `painkillers`, `sleeping pills`

## 39. `-1744875694`

> A city employs seasonal and permanent snow removers. A seasonal snow remover works 6 hours per shift and gets paid $120. A permanent snow remover works 10 hours per shift and gets paid $250. Currently the city needs 300 hours of snow remover labor after a heavy snowfall. If the city has a budget of $6500, how many of each type of worker should be hired to minimize the total number of snow removers?

Variables: `seasonal`, `permanent`

## 40. `-682137487`

> A florist transports his flowers to stores in small bouquets and large bouquets. A small bouquet has 5 flowers while a large bouquet has 10 flowers. The florist can transport at most 80 small bouquets and 50 large bouquets. In total, he can transport at most 70 bouquets and he must transport at least 20 large bouquets. Since small bouquets are more popular, he must transport at least twice as many small bouquets as large bouquets. How many of each bouquet should he transport to maximize the total number of flowers that reach the stores?

Variables: `small bouquets`, `large bouquets`
