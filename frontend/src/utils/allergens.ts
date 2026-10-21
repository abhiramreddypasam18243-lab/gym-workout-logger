// Codes must match the catalogue's food tags exactly; the planner filter is an exact match (D-31)
export const EU_ALLERGENS = [
  'gluten',
  'crustaceans',
  'eggs',
  'fish',
  'peanuts',
  'soy',
  'milk',
  'tree_nuts',
  'celery',
  'mustard',
  'sesame',
  'sulphites',
  'lupin',
  'molluscs',
]

export const ALLERGEN_LABELS: Record<string, string> = {
  gluten: 'cereals with gluten',
  soy: 'soybeans',
  tree_nuts: 'tree nuts',
}

export const allergenLabel = (code: string): string => ALLERGEN_LABELS[code] ?? code
