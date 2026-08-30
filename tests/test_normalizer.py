"""
Unit tests for serving size normalizer and bulk anomaly scaling.
"""
import pytest
from purdue_menu.normalizer import parse_serving_size, is_bulk_anomaly, normalize_nutrition_data
from purdue_menu.food_types import FoodCategory
from purdue_menu.models import NutritionData


def test_parse_disher_sizes():
    label, fl_oz, count, unit, is_single = parse_serving_size("#60 Disher")
    assert label == "1 Tbsp (#60 Disher)"
    assert abs(fl_oz - 0.53) < 0.01

    label, fl_oz, count, unit, is_single = parse_serving_size("#16 Disher")
    assert label == "1/4 Cup (#16 Disher)"
    assert abs(fl_oz - 2.0) < 0.01

    label, fl_oz, count, unit, is_single = parse_serving_size("#8 Disher")
    assert label == "1/2 Cup (#8 Disher)"
    assert abs(fl_oz - 4.0) < 0.01


def test_parse_ladle_sizes():
    label, fl_oz, count, unit, is_single = parse_serving_size("1OZ LADLE")
    assert label == "2 Tbsp (1 oz Ladle)"
    assert fl_oz == 1.0

    label, fl_oz, count, unit, is_single = parse_serving_size("2 OZ LADLE")
    assert label == "1/4 Cup (2 oz Ladle)"
    assert fl_oz == 2.0


def test_parse_sheet_cuts():
    label, fl_oz, count, unit, is_single = parse_serving_size("12 Cut")
    assert label == "1 Slice (1/12 sheet cut)"
    assert fl_oz is None


def test_parse_piece_and_multi_piece():
    # Single potsticker
    label, fl_oz, count, unit, is_single = parse_serving_size("1 Each", "Pork Potstickers")
    assert count == 1.0
    assert is_single is True
    assert "Piece" in label or "Each" in label

    # Multi-piece tenders
    label, fl_oz, count, unit, is_single = parse_serving_size("3 Pieces", "Crispy Chicken Tenders")
    assert count == 3.0
    assert unit == "pieces"
    assert is_single is False
    assert "3 Pieces" in label


def test_bulk_anomaly_detection():
    # Salad dressing logged as 5 gallons or 28,000 calories
    assert is_bulk_anomaly(FoodCategory.SAUCE_DRESSING, "5 Gallon", 28000.0) is True
    assert is_bulk_anomaly(FoodCategory.SAUCE_DRESSING, "2 Tbsp", 1200.0) is True
    assert is_bulk_anomaly(FoodCategory.SAUCE_DRESSING, "2 Tbsp", 120.0) is False
    assert is_bulk_anomaly(FoodCategory.ENTREE, "1 Each", 450.0) is False


def test_normalize_nutrition_bulk_sauce_rescaling():
    # A batch sauce logged as 1200 calories and 60g fat
    nut = NutritionData(
        calories=1200.0,
        serving_size="1 Quart",
        protein_g=10.0,
        carbohydrates_g=40.0,
        fat_g=100.0,
        sodium_mg=5000.0,
        fiber_g=0.0
    )
    normalized = normalize_nutrition_data(nut, FoodCategory.SAUCE_DRESSING)

    assert normalized.rescaled_from_bulk is True
    assert "2 Tbsp (normalized from batch)" in normalized.normalized_serving_size
    assert normalized.calories <= 160.0
    assert normalized.fat_g < 20.0
    assert normalized.sodium_mg < 1000.0
    assert normalized.net_carbohydrates_g == normalized.carbohydrates_g
