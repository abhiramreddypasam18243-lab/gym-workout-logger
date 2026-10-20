# Recipe Cost Estimates

Ten Indian budget recipes (tag `budget_friendly`, decision D-28) cost at most ₹50 per serving. They use only foods already in the catalogue, so every nutrient value comes from the sources in `DATA_LICENCES.md`.

**Prices are estimates, not sourced data.** They are rough Indian retail prices (October 2026) used only for the budget filter and ranking. Change them here and in `recipes.json` if local prices differ.

Cost per serving = Σ (grams × price per kg ÷ 1000) ÷ servings, rounded to the nearest rupee.

## Price assumptions (₹ per kg, as listed in the catalogue)

| Food | ₹/kg | Note |
|---|---:|---|
| White Basmati Rice (Raw) | 100 |  |
| Brown Rice (Raw) | 120 |  |
| Whole Wheat Flour (Atta) | 45 |  |
| Red Lentils (Masoor Dal, Raw) | 100 |  |
| Yellow Lentils (Toor Dal, Boiled) | 64 | dry ≈ ₹160/kg; ~2.5× weight when boiled |
| Chickpeas (Chana, Boiled) | 45 | dry ≈ ₹100/kg; ~2.2× weight when boiled |
| Whole Egg | 140 | ≈ ₹7 per egg (50 g) |
| Egg White | 210 | ≈ ₹7 per egg (33 g white) |
| Rolled Oats | 200 |  |
| Russet Potato (Raw) | 30 |  |
| Yellow Onion (Raw) | 40 |  |
| Tomato (Raw) | 40 |  |
| Spinach (Raw) | 60 |  |
| Carrots (Raw) | 50 |  |
| Sweet Potato (Raw) | 50 |  |
| Banana (Raw) | 60 |  |
| Whole Wheat Bread | 100 |  |
| Peanut Butter (Smooth) | 350 |  |
| Ghee (Clarified Butter) | 650 |  |
| Coconut Oil | 250 |  |

## Recipes

| Recipe | Servings | ₹/serving | kcal | Protein (g) | Ingredients (grams × ₹/kg) |
|---|---:|---:|---:|---:|---|
| Egg Bhurji with Atta Roti | 2 | 20 | 399 | 21 | Whole Egg 200 g x ₹140/kg; Yellow Onion (Raw) 60 g x ₹40/kg; Tomato (Raw) 60 g x ₹40/kg; Coconut Oil 8 g x ₹250/kg; Whole Wheat Flour (Atta) 120 g x ₹45/kg |
| Masala Oats with Egg Whites | 1 | 38 | 310 | 20 | Rolled Oats 60 g x ₹200/kg; Egg White 100 g x ₹210/kg; Yellow Onion (Raw) 40 g x ₹40/kg; Tomato (Raw) 40 g x ₹40/kg; Spinach (Raw) 30 g x ₹60/kg |
| Peanut Butter Banana Toast | 1 | 19 | 355 | 14 | Whole Wheat Bread 60 g x ₹100/kg; Peanut Butter (Smooth) 20 g x ₹350/kg; Banana (Raw) 100 g x ₹60/kg |
| Masoor Dal with Atta Roti | 2 | 16 | 551 | 26 | Red Lentils (Masoor Dal, Raw) 120 g x ₹100/kg; Whole Wheat Flour (Atta) 160 g x ₹45/kg; Yellow Onion (Raw) 60 g x ₹40/kg; Tomato (Raw) 80 g x ₹40/kg; Ghee (Clarified Butter) 10 g x ₹650/kg |
| Chana Aloo Curry with Rice | 2 | 22 | 647 | 21 | Chickpeas (Chana, Boiled) 300 g x ₹45/kg; Russet Potato (Raw) 200 g x ₹30/kg; Yellow Onion (Raw) 80 g x ₹40/kg; Tomato (Raw) 100 g x ₹40/kg; Coconut Oil 10 g x ₹250/kg; White Basmati Rice (Raw) 140 g x ₹100/kg |
| Toor Dal Khichdi with Spinach | 2 | 21 | 430 | 16 | Yellow Lentils (Toor Dal, Boiled) 250 g x ₹64/kg; White Basmati Rice (Raw) 120 g x ₹100/kg; Spinach (Raw) 100 g x ₹60/kg; Ghee (Clarified Butter) 10 g x ₹650/kg; Yellow Onion (Raw) 50 g x ₹40/kg |
| Egg & Potato Curry with Atta Roti | 2 | 24 | 473 | 23 | Whole Egg 200 g x ₹140/kg; Russet Potato (Raw) 150 g x ₹30/kg; Yellow Onion (Raw) 80 g x ₹40/kg; Tomato (Raw) 100 g x ₹40/kg; Coconut Oil 10 g x ₹250/kg; Whole Wheat Flour (Atta) 120 g x ₹45/kg |
| Palak Masoor Dal with Brown Rice | 2 | 23 | 501 | 20 | Red Lentils (Masoor Dal, Raw) 100 g x ₹100/kg; Spinach (Raw) 150 g x ₹60/kg; Brown Rice (Raw) 140 g x ₹120/kg; Ghee (Clarified Butter) 8 g x ₹650/kg; Yellow Onion (Raw) 50 g x ₹40/kg; Tomato (Raw) 60 g x ₹40/kg |
| Chana Chaat | 1 | 11 | 279 | 14 | Chickpeas (Chana, Boiled) 150 g x ₹45/kg; Yellow Onion (Raw) 30 g x ₹40/kg; Tomato (Raw) 50 g x ₹40/kg; Carrots (Raw) 30 g x ₹50/kg |
| Boiled Eggs with Masala Sweet Potato | 1 | 22 | 280 | 15 | Whole Egg 100 g x ₹140/kg; Sweet Potato (Raw) 150 g x ₹50/kg; Yellow Onion (Raw) 20 g x ₹40/kg |

Nutrients are per serving, calculated from the catalogue's per-100 g values. The app recalculates them the same way (spec 5.3).

## Vegetarian protein recipes (2026-10-20)

Six egg-free, high-protein Indian dishes built around paneer, tofu, dahi and quinoa. They are not budget recipes (₹31–117 per serving). Extra price assumptions (₹/kg): paneer 400, firm tofu 300, Greek yogurt (used as thick dahi) 450, quinoa 500, almonds 900, red bell pepper 150.

| Recipe | Servings | ₹/serving | kcal | Protein (g) | Ingredients (grams × ₹/kg) |
|---|---:|---:|---:|---:|---|
| Tofu Bhurji with Atta Roti | 2 | 53 | 386 | 24 | Firm Tofu 300 g x ₹300/kg; Yellow Onion (Raw) 60 g x ₹40/kg; Tomato (Raw) 60 g x ₹40/kg; Spinach (Raw) 50 g x ₹60/kg; Coconut Oil 8 g x ₹250/kg; Whole Wheat Flour (Atta) 120 g x ₹45/kg |
| Dahi Oats Bowl with Almonds | 1 | 117 | 448 | 31 | Greek Yogurt (Nonfat, Plain) 200 g x ₹450/kg; Rolled Oats 50 g x ₹200/kg; Almonds (Raw) 15 g x ₹900/kg; Banana (Raw) 60 g x ₹60/kg |
| Quinoa Vegetable Upma with Paneer | 2 | 55 | 405 | 18 | Quinoa (Raw) 120 g x ₹500/kg; Paneer (Indian Cottage Cheese) 100 g x ₹400/kg; Yellow Onion (Raw) 60 g x ₹40/kg; Carrots (Raw) 60 g x ₹50/kg; Ghee (Clarified Butter) 6 g x ₹650/kg |
| Palak Paneer with Brown Rice | 2 | 51 | 534 | 23 | Paneer (Indian Cottage Cheese) 150 g x ₹400/kg; Spinach (Raw) 250 g x ₹60/kg; Yellow Onion (Raw) 60 g x ₹40/kg; Tomato (Raw) 60 g x ₹40/kg; Ghee (Clarified Butter) 8 g x ₹650/kg; Brown Rice (Raw) 140 g x ₹120/kg |
| Paneer Tikka with Peppers | 2 | 63 | 345 | 22 | Paneer (Indian Cottage Cheese) 200 g x ₹400/kg; Bell Pepper (Red, Raw) 100 g x ₹150/kg; Yellow Onion (Raw) 60 g x ₹40/kg; Greek Yogurt (Nonfat, Plain) 60 g x ₹450/kg; Coconut Oil 8 g x ₹250/kg |
| Chana Paneer Salad | 2 | 31 | 321 | 19 | Chickpeas (Chana, Boiled) 200 g x ₹45/kg; Paneer (Indian Cottage Cheese) 100 g x ₹400/kg; Tomato (Raw) 80 g x ₹40/kg; Yellow Onion (Raw) 40 g x ₹40/kg; Bell Pepper (Red, Raw) 60 g x ₹150/kg |
