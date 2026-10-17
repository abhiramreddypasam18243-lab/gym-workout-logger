# Data Licences

Every food nutrient value in the seed catalogue must come from a source whose licence permits this use. This file records each source.

## Sources

### 1. USDA FoodData Central (SR Legacy / Foundation Foods)

- **Publisher:** U.S. Department of Agriculture, Agricultural Research Service
- **URL:** https://fdc.nal.usda.gov/
- **Licence:** Public domain (U.S. government work, not subject to copyright)
- **Used for:** Nutrient values for common Western foods (chicken, rice, eggs, vegetables, etc.)
- **Access date:** TBD (will be recorded when seed data is created in Step 4)

### 2. Indian Food Composition Tables (IFCT) — NIN/ICMR

- **Publisher:** National Institute of Nutrition (NIN), Indian Council of Medical Research (ICMR)
- **URL:** https://www.nin.res.in/
- **Licence:** Government of India publication — verify specific reuse terms before including data. If the licence is unclear, do not use the data (DL2).
- **Used for:** Nutrient values for Indian foods (dal, roti, paneer, etc.)
- **Access date:** TBD
- **Note:** If IFCT licence does not clearly permit reuse, we will use USDA values for similar foods and document the substitution.

## Rules

- Every food in the seed catalogue has `data_source` and `source_reference` fields (DL1).
- Values that are estimates or imputed are flagged `approximate` (DL1).
- Recipes are original compositions, not copied from external sources (DL3).
- No invented nutrient values outside of clearly marked test fixtures (DL4).
