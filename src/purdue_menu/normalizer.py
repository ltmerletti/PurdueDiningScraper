"""
Serving size parser, unit normalizer, portion analyzer, and bulk anomaly scaler.
Handles institutional kitchen units (dishers, ladles, cuts), discrete piece items
(potstickers, wings, nuggets, dumplings), and prevents 5-gallon/bulk batch entries
from distorting nutritional metrics.
"""
import re
from typing import Optional, Tuple, Dict, Any
from .food_types import FoodCategory, DISCRETE_PIECE_KEYWORDS
from .models import NutritionData


# Standard kitchen disher conversion table to fluid ounces and Tbsp
# Formula: Size = 32 / (fl oz capacity), or fl oz = 32 / Size
DISHER_TABLE = {
    60: {"fl_oz": 0.53, "tbsp": 1.06, "ml": 15.7, "label": "1 Tbsp (#60 Disher)"},
    40: {"fl_oz": 0.80, "tbsp": 1.60, "ml": 23.7, "label": "1.6 Tbsp (#40 Disher)"},
    30: {"fl_oz": 1.07, "tbsp": 2.14, "ml": 31.5, "label": "2 Tbsp (#30 Disher)"},
    24: {"fl_oz": 1.33, "tbsp": 2.66, "ml": 39.4, "label": "2.7 Tbsp (#24 Disher)"},
    20: {"fl_oz": 1.60, "tbsp": 3.20, "ml": 47.3, "label": "3.2 Tbsp (#20 Disher)"},
    16: {"fl_oz": 2.00, "tbsp": 4.00, "ml": 59.1, "label": "1/4 Cup (#16 Disher)"},
    12: {"fl_oz": 2.67, "tbsp": 5.34, "ml": 78.9, "label": "1/3 Cup (#12 Disher)"},
    10: {"fl_oz": 3.20, "tbsp": 6.40, "ml": 94.6, "label": "0.4 Cup (#10 Disher)"},
    8:  {"fl_oz": 4.00, "tbsp": 8.00, "ml": 118.3, "label": "1/2 Cup (#8 Disher)"},
    6:  {"fl_oz": 5.33, "tbsp": 10.66, "ml": 157.7, "label": "2/3 Cup (#6 Disher)"},
    4:  {"fl_oz": 8.00, "tbsp": 16.00, "ml": 236.6, "label": "1 Cup (#4 Disher)"},
}

# Regex matchers for kitchen equipment strings
DISHER_REGEX = re.compile(r"#?\s*(\d+)\s*(?:scoop|disher)", re.IGNORECASE)
LADLE_REGEX = re.compile(r"(\d+(?:\.\d+)?|\d+\s*/\s*\d+)?\s*(?:oz|ounce)?\s*ladle", re.IGNORECASE)
CUT_REGEX = re.compile(r"(\d+)\s*cut", re.IGNORECASE)
GALLON_REGEX = re.compile(r"(\d+(?:\.\d+)?)\s*gal(?:lon)?s?", re.IGNORECASE)
QUART_REGEX = re.compile(r"(\d+(?:\.\d+)?)\s*qt|quart", re.IGNORECASE)
BATCH_REGEX = re.compile(r"batch|pan|recipe", re.IGNORECASE)
PIECE_REGEX = re.compile(r"(\d+(?:\.\d+)?)\s*(?:each|ea|piece|pieces|pc|pcs|potsticker|dumpling|wing|nugget|tender|strip|roll|slice|patty|pat|biscuit|cookie|muffin|donut|taco)", re.IGNORECASE)


def parse_serving_size(raw_str: Optional[str], item_name: Optional[str] = None) -> Tuple[Optional[str], Optional[float], Optional[float], Optional[str], bool]:
    """
    Parse and standardize kitchen serving size strings into consumer-friendly labels.
    Returns:
        (normalized_label, estimated_volume_fl_oz, portion_count, portion_unit, is_single_piece)
    """
    name_lower = (item_name or "").lower()
    is_discrete_name = any(re.search(rf"\b{re.escape(kw)}\b", name_lower) for kw in DISCRETE_PIECE_KEYWORDS)

    if not raw_str:
        if is_discrete_name:
            return "1 Piece", None, 1.0, "piece", True
        return None, None, None, None, False

    cleaned = raw_str.strip()

    # 1. Disher matching (e.g., "#60 Disher", "30 disher")
    disher_match = DISHER_REGEX.search(cleaned)
    if disher_match:
        disher_num = int(disher_match.group(1))
        if disher_num in DISHER_TABLE:
            info = DISHER_TABLE[disher_num]
            return info["label"], info["fl_oz"], 1.0, "disher", False
        else:
            fl_oz = 32.0 / disher_num if disher_num > 0 else 1.0
            return f"{fl_oz:.1f} fl oz (#{disher_num} Disher)", fl_oz, 1.0, "disher", False

    # 2. Ladle matching (e.g. "1OZ LADLE", "2 OZ LADLE", "1/2 oz ladle")
    ladle_match = LADLE_REGEX.search(cleaned)
    if ladle_match:
        oz_str = ladle_match.group(1)
        if oz_str:
            if "/" in oz_str:
                num, denom = oz_str.split("/")
                fl_oz = float(num.strip()) / float(denom.strip())
            else:
                fl_oz = float(oz_str.strip())
        else:
            fl_oz = 1.0  # default ladle if unspecified

        if abs(fl_oz - 1.0) < 0.05:
            return "2 Tbsp (1 oz Ladle)", fl_oz, 1.0, "ladle", False
        elif abs(fl_oz - 2.0) < 0.05:
            return "1/4 Cup (2 oz Ladle)", fl_oz, 1.0, "ladle", False
        elif abs(fl_oz - 4.0) < 0.05:
            return "1/2 Cup (4 oz Ladle)", fl_oz, 1.0, "ladle", False
        else:
            return f"{fl_oz:.1f} fl oz Ladle", fl_oz, 1.0, "ladle", False

    # 3. Sheet pan cut matching (e.g. "12 Cut", "24 Cut", "48 Cut")
    cut_match = CUT_REGEX.search(cleaned)
    if cut_match:
        cut_num = cut_match.group(1)
        return f"1 Slice (1/{cut_num} sheet cut)", None, 1.0, "slice", False

    # 4. Piece / Each count parsing (e.g. "1 Each", "3 Pieces", "1 Potsticker")
    piece_match = PIECE_REGEX.search(cleaned)
    if piece_match:
        count = float(piece_match.group(1))
        unit = "piece" if count == 1.0 else "pieces"

        # Check if item name is a discrete piece item
        is_discrete = False
        name_lower = (item_name or "").lower()
        if any(re.search(rf"\b{re.escape(kw)}\b", name_lower) for kw in DISCRETE_PIECE_KEYWORDS):
            is_discrete = True

        is_single = (count == 1.0) and (is_discrete or "each" in cleaned.lower() or "piece" in cleaned.lower())

        if count == 1.0:
            if is_discrete:
                # E.g. "1 Potsticker (Single Piece)" or "1 Piece"
                label = f"1 Piece ({cleaned})" if "piece" not in cleaned.lower() else cleaned
            else:
                label = cleaned
        else:
            label = f"{int(count) if count.is_integer() else count} Pieces"

        return label, None, count, unit, is_single

    # 5. Default cleanup
    return cleaned, None, 1.0, "portion", False


def is_bulk_anomaly(
    category: FoodCategory,
    serving_str: Optional[str],
    calories: Optional[float]
) -> bool:
    """
    Determine if an item's data represents an institutional batch/preparation anomaly
    (e.g., 5 gallons of salad dressing logged as 1 serving of 28,000 calories).
    """
    serving_lower = (serving_str or "").lower()

    # If explicit bulk units are found in serving size
    if any(bulk in serving_lower for bulk in ["gallon", "gal", "quart", "qt", "batch", "full pan", "half pan", "5000g"]):
        return True

    # High-calorie sauce or condiment anomaly check
    if category in (FoodCategory.SAUCE_DRESSING, FoodCategory.TOPPING_CONDIMENT):
        if calories and calories > 800:
            return True

    return False


def normalize_nutrition_data(
    nutrition: NutritionData,
    category: FoodCategory,
    item_name: Optional[str] = None
) -> NutritionData:
    """
    Normalizes a NutritionData object by resolving kitchen measurements, identifying
    single-piece discrete items, and rescaling bulk anomalies to standardized reference portions.
    """
    norm_serving, _, p_count, p_unit, is_single = parse_serving_size(nutrition.serving_size, item_name)
    nutrition.normalized_serving_size = norm_serving or nutrition.serving_size
    nutrition.portion_count = p_count
    nutrition.portion_unit = p_unit
    nutrition.is_single_piece_entry = is_single

    # Check for bulk anomaly
    if is_bulk_anomaly(category, nutrition.serving_size, nutrition.calories):
        nutrition.rescaled_from_bulk = True

        scale_factor = 1.0
        target_serving_label = "2 Tbsp (normalized from batch)"

        if category == FoodCategory.SAUCE_DRESSING:
            if nutrition.calories and nutrition.calories > 150:
                scale_factor = nutrition.calories / 120.0
            target_serving_label = "2 Tbsp (normalized from batch)"
        elif category == FoodCategory.TOPPING_CONDIMENT:
            if nutrition.calories and nutrition.calories > 100:
                scale_factor = nutrition.calories / 70.0
            target_serving_label = "1 Tbsp (normalized from batch)"
        else:
            if nutrition.calories and nutrition.calories > 1500:
                scale_factor = nutrition.calories / 500.0
            target_serving_label = "1 Portion (normalized from batch)"

        if scale_factor > 1.0:
            nutrition.normalized_serving_size = target_serving_label
            if nutrition.calories is not None:
                nutrition.calories = round(nutrition.calories / scale_factor, 1)
            if nutrition.protein_g is not None:
                nutrition.protein_g = round(nutrition.protein_g / scale_factor, 1)
            if nutrition.carbohydrates_g is not None:
                nutrition.carbohydrates_g = round(nutrition.carbohydrates_g / scale_factor, 1)
            if nutrition.fat_g is not None:
                nutrition.fat_g = round(nutrition.fat_g / scale_factor, 1)
            if nutrition.saturated_fat_g is not None:
                nutrition.saturated_fat_g = round(nutrition.saturated_fat_g / scale_factor, 1)
            if nutrition.trans_fat_g is not None:
                nutrition.trans_fat_g = round(nutrition.trans_fat_g / scale_factor, 1)
            if nutrition.sugar_g is not None:
                nutrition.sugar_g = round(nutrition.sugar_g / scale_factor, 1)
            if nutrition.added_sugar_g is not None:
                nutrition.added_sugar_g = round(nutrition.added_sugar_g / scale_factor, 1)
            if nutrition.fiber_g is not None:
                nutrition.fiber_g = round(nutrition.fiber_g / scale_factor, 1)
            if nutrition.sodium_mg is not None:
                nutrition.sodium_mg = round(nutrition.sodium_mg / scale_factor, 1)
            if nutrition.cholesterol_mg is not None:
                nutrition.cholesterol_mg = round(nutrition.cholesterol_mg / scale_factor, 1)

    # Compute net carbs if carbs and fiber exist
    if nutrition.carbohydrates_g is not None:
        fiber = nutrition.fiber_g or 0.0
        nutrition.net_carbohydrates_g = max(0.0, round(nutrition.carbohydrates_g - fiber, 1))

    return nutrition
