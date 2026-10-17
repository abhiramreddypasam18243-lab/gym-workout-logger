"""Tests for grocery list scaling and unit aggregation domain functions.

Acceptance criteria:
AC-77 (5.7): 250 g + 0.5 kg aggregates to 750 g;
            2 tbsp + 1 tsp to 35 ml;
            1 cup + 100 ml to 340 ml;
            1,200 g displays as 1.2 kg;
            >= 1,000 ml displays in l.
AC-78 (5.7): 2 piece of onion and 300 g of onion stay on separate lines;
            mass and volume amounts of the same food stay on separate lines.
AC-79 (5.7): A 4-serving recipe with 400 g of an ingredient, planned at 1.5 servings,
            contributes 150 g.
"""

from decimal import Decimal

from app.domain.grocery import (
    GroceryItemInput,
    UnitFamily,
    aggregate_grocery_items,
    scale_ingredient_quantity,
)


def test_ac_79_scale_ingredient_quantity():
    # A 4-serving recipe with 400 g of an ingredient, planned at 1.5 servings -> 150 g
    scaled = scale_ingredient_quantity(
        quantity=Decimal("400"),
        recipe_servings=Decimal("4"),
        planned_servings=Decimal("1.5"),
    )
    assert scaled == Decimal("150")


def test_ac_77_mass_aggregation_and_formatting():
    # 250 g + 0.5 kg aggregates to 750 g
    items = [
        GroceryItemInput(food_id="food-1", name="Chicken", quantity=Decimal("250"), unit="g"),
        GroceryItemInput(food_id="food-1", name="Chicken", quantity=Decimal("0.5"), unit="kg"),
    ]
    aggregated = aggregate_grocery_items(items)
    assert len(aggregated) == 1
    assert aggregated[0].total_quantity == Decimal("750")
    assert aggregated[0].canonical_unit == "g"
    assert aggregated[0].display_quantity == "750 g"

    # 1,200 g displays as 1.2 kg (>= 1,000 g displays as kg)
    items_large = [
        GroceryItemInput(food_id="food-1", name="Chicken", quantity=Decimal("1200"), unit="g"),
    ]
    agg_large = aggregate_grocery_items(items_large)
    assert agg_large[0].display_quantity == "1.2 kg"


def test_ac_77_volume_aggregation_and_formatting():
    # 2 tbsp + 1 tsp to 35 ml
    items1 = [
        GroceryItemInput(food_id="oil-1", name="Olive oil", quantity=Decimal("2"), unit="tbsp"),
        GroceryItemInput(food_id="oil-1", name="Olive oil", quantity=Decimal("1"), unit="tsp"),
    ]
    agg1 = aggregate_grocery_items(items1)
    assert len(agg1) == 1
    assert agg1[0].total_quantity == Decimal("35")
    assert agg1[0].canonical_unit == "ml"
    assert agg1[0].display_quantity == "35 ml"

    # 1 cup + 100 ml to 340 ml
    items2 = [
        GroceryItemInput(food_id="milk-1", name="Milk", quantity=Decimal("1"), unit="cup"),
        GroceryItemInput(food_id="milk-1", name="Milk", quantity=Decimal("100"), unit="ml"),
    ]
    agg2 = aggregate_grocery_items(items2)
    assert len(agg2) == 1
    assert agg2[0].total_quantity == Decimal("340")
    assert agg2[0].canonical_unit == "ml"
    assert agg2[0].display_quantity == "340 ml"

    # >= 1000 ml displays in l (e.g. 1500 ml -> 1.5 l)
    items_liter = [
        GroceryItemInput(food_id="milk-1", name="Milk", quantity=Decimal("1500"), unit="ml"),
    ]
    agg_liter = aggregate_grocery_items(items_liter)
    assert agg_liter[0].display_quantity == "1.5 l"


def test_ac_78_separate_lines_across_unit_families():
    # 2 piece of onion and 300 g of onion stay on separate lines
    # Mass and volume amounts stay on separate lines (no density conversion)
    items = [
        GroceryItemInput(food_id="onion-1", name="Onion", quantity=Decimal("2"), unit="piece"),
        GroceryItemInput(food_id="onion-1", name="Onion", quantity=Decimal("300"), unit="g"),
    ]
    agg = aggregate_grocery_items(items)
    # Must remain 2 separate lines!
    assert len(agg) == 2

    # Check the two distinct lines
    count_item = next(it for it in agg if it.unit_family == UnitFamily.COUNT)
    mass_item = next(it for it in agg if it.unit_family == UnitFamily.MASS)

    assert count_item.total_quantity == Decimal("2")
    assert count_item.canonical_unit == "piece"
    assert count_item.display_quantity == "2 piece"

    assert mass_item.total_quantity == Decimal("300")
    assert mass_item.canonical_unit == "g"
    assert mass_item.display_quantity == "300 g"
