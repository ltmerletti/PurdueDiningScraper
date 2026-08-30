"""
Unit tests for semantic density descriptors and filter mappers.
"""
import pytest
from purdue_menu.descriptors import (
    generate_protein_descriptor,
    generate_sodium_descriptor,
    generate_sugar_descriptor,
    generate_fiber_descriptor,
    generate_fat_descriptor,
    generate_net_carb_descriptor,
    generate_all_descriptors,
    parse_protein_filter,
    parse_sodium_filter,
    parse_net_carbs_filter
)
from purdue_menu.models import NutritionData
from purdue_menu.food_types import FoodCategory


def test_protein_descriptors():
    assert generate_protein_descriptor(35.0) == "p:protein-dense"
    assert generate_protein_descriptor(25.0) == "p:protein-rich"
    assert generate_protein_descriptor(12.0) == "p:moderate"
    assert generate_protein_descriptor(3.0) == "p:light"


def test_sodium_descriptors():
    assert generate_sodium_descriptor(100.0) == "sod:light"
    assert generate_sodium_descriptor(500.0) == "sod:moderate"
    assert generate_sodium_descriptor(800.0) == "sod:concentrated"
    assert generate_sodium_descriptor(1200.0) == "sod:sodium-dense"


def test_generate_all_descriptors():
    nut = NutritionData(
        calories=350.0,
        protein_g=32.0,
        carbohydrates_g=15.0,
        fiber_g=5.0,
        fat_g=12.0,
        saturated_fat_g=2.0,
        sodium_mg=550.0,
        sugar_g=2.0
    )
    descriptors = generate_all_descriptors(nut, FoodCategory.ENTREE)
    assert "p:protein-dense" in descriptors
    assert "sod:moderate" in descriptors
    assert "fib:good-source" in descriptors
    assert "netcarb:low" in descriptors
    assert "sug:light" in descriptors


def test_filter_parsers():
    assert parse_protein_filter("protein-dense") == 30.0
    assert parse_protein_filter("25") == 25.0
    assert parse_protein_filter(35) == 35.0

    assert parse_sodium_filter("moderate") == 600.0
    assert parse_sodium_filter("600") == 600.0

    assert parse_net_carbs_filter("low") == 15.0
