"""
Extensive quality, categorization, serving size normalization, and anomaly scaling tests.
Tests hundreds of real-world Purdue dining items, edge-case food names, kitchen units,
and nutritional anomaly scenarios.
"""
import pytest
from purdue_menu.food_types import categorize_food_item, detect_custom_station_type, FoodCategory, CustomStationType
from purdue_menu.normalizer import parse_serving_size, is_bulk_anomaly, normalize_nutrition_data
from purdue_menu.descriptors import (
    generate_protein_descriptor,
    generate_sodium_descriptor,
    generate_sugar_descriptor,
    generate_fiber_descriptor,
    generate_fat_descriptor,
    generate_saturated_fat_descriptor,
    generate_net_carb_descriptor,
    generate_all_descriptors,
    parse_protein_filter,
    parse_sodium_filter,
    parse_net_carbs_filter
)
from purdue_menu.models import NutritionData


# ============================================================================
# 1. Extensive Food Categorization Quality Tests
# ============================================================================

@pytest.mark.parametrize("item_name,station,serving,calories,expected_category", [
    # Entrees
    ("Grilled Chicken Breast", "Grill", "1 Each", 180, FoodCategory.ENTREE),
    ("Black Angus Cheeseburger", "Grill", "1 Each", 520, FoodCategory.ENTREE),
    ("Pepperoni Pizza", "Pizza", "1 Slice", 310, FoodCategory.ENTREE),
    ("Cheese Lasagna", "Action Station", "1 Portion", 420, FoodCategory.ENTREE),
    ("Beef Pot Roast", "Homestyle", "4 oz", 340, FoodCategory.ENTREE),
    ("Crispy Chicken Tenders", "Grill", "3 Pieces", 290, FoodCategory.ENTREE),
    ("Pork Carnitas Taco", "Latin", "2 Tacos", 380, FoodCategory.ENTREE),
    ("Baked Salmon Filet", "Chef Choice", "1 Filet", 260, FoodCategory.ENTREE),
    ("Tofu Vegetable Stir Fry", "Wok", "1 Cup", 220, FoodCategory.ENTREE),
    ("BBQ Pulled Pork Sandwich", "Homestyle", "1 Sandwich", 450, FoodCategory.ENTREE),
    ("Spaghetti with Marinara & Meatballs", "Pasta", "1 Plate", 480, FoodCategory.ENTREE),

    # Sauces & Dressings
    ("Buttermilk Ranch Dressing", "Salad Bar", "2 Tbsp", 140, FoodCategory.SAUCE_DRESSING),
    ("Italian Herb Vinaigrette", "Salad Bar", "2 Tbsp", 90, FoodCategory.SAUCE_DRESSING),
    ("Homestyle Brown Gravy", "Homestyle", "2OZ LADLE", 45, FoodCategory.SAUCE_DRESSING),
    ("Sweet Baby Ray's BBQ Sauce", "Condiments", "2 Tbsp", 70, FoodCategory.SAUCE_DRESSING),
    ("Marinara Sauce", "Pasta", "1/2 Cup", 60, FoodCategory.SAUCE_DRESSING),
    ("Creamy Alfredo Sauce", "Pasta", "1/4 Cup", 180, FoodCategory.SAUCE_DRESSING),
    ("Szechuan Stir-Fry Sauce", "Wok", "1OZ LADLE", 50, FoodCategory.SAUCE_DRESSING),
    ("Maple Pancake Syrup", "Breakfast", "2 Tbsp", 100, FoodCategory.SAUCE_DRESSING),
    ("Classic Guacamole", "Latin Bar", "#30 Disher", 60, FoodCategory.TOPPING_CONDIMENT),
    ("Chunky Salsa", "Latin Bar", "2 Tbsp", 20, FoodCategory.SAUCE_DRESSING),

    # Toppings & Condiments
    ("Shredded Cheddar Cheese", "Salad Bar", "1 oz", 110, FoodCategory.TOPPING_CONDIMENT),
    ("Garlic & Butter Croutons", "Salad Bar", "2 Tbsp", 35, FoodCategory.TOPPING_CONDIMENT),
    ("Sliced Jalapenos", "Latin Bar", "1 Tbsp", 5, FoodCategory.TOPPING_CONDIMENT),
    ("Sour Cream Packet", "Condiments", "1 Packet", 60, FoodCategory.TOPPING_CONDIMENT),
    ("Dill Pickle Chips", "Grill Bar", "4 Slices", 5, FoodCategory.TOPPING_CONDIMENT),
    ("Whipped Butter", "Bakery", "1 Pat", 35, FoodCategory.TOPPING_CONDIMENT),

    # Bread & Bakery
    ("Fresh Baked Dinner Roll", "Bakery", "1 Roll", 110, FoodCategory.BREAD_BAKERY),
    ("Garlic Herb Breadstick", "Pizza", "1 Piece", 140, FoodCategory.BREAD_BAKERY),
    ("Plain Bagel", "Bakery", "1 Bagel", 240, FoodCategory.BREAD_BAKERY),
    ("Buttermilk Biscuit", "Breakfast", "1 Biscuit", 180, FoodCategory.BREAD_BAKERY),
    ("Whole Wheat Toast", "Breakfast", "1 Slice", 70, FoodCategory.BREAD_BAKERY),
    ("Warm Flour Tortilla", "Latin", "1 Tortilla", 120, FoodCategory.BREAD_BAKERY),
    ("Fluffy Cornbread", "Homestyle", "1 Square", 160, FoodCategory.BREAD_BAKERY),

    # Desserts & Sweet Snacks
    ("Chocolate Chip Cookie", "Desserts", "1 Cookie", 160, FoodCategory.DESSERT_SNACK),
    ("Fudge Brownie", "Desserts", "1 Brownie", 220, FoodCategory.DESSERT_SNACK),
    ("Vanilla Soft Serve Ice Cream", "Desserts", "1/2 Cup", 140, FoodCategory.DESSERT_SNACK),
    ("Strawberry Parfait", "Breakfast", "1 Cup", 190, FoodCategory.DESSERT_SNACK),
    ("Apple Crisp", "Desserts", "1/2 Cup", 210, FoodCategory.DESSERT_SNACK),
    ("Glazed Donut", "Bakery", "1 Donut", 240, FoodCategory.DESSERT_SNACK),

    # Beverages
    ("2% Lowfat Milk", "Beverages", "8 fl oz", 130, FoodCategory.BEVERAGE),
    ("Fresh Brewed Dark Roast Coffee", "Beverages", "12 fl oz", 5, FoodCategory.BEVERAGE),
    ("Orange Juice", "Beverages", "8 fl oz", 110, FoodCategory.BEVERAGE),
    ("Iced Green Tea", "Beverages", "12 fl oz", 0, FoodCategory.BEVERAGE),
    ("Coca-Cola Classic", "Beverages", "12 fl oz", 140, FoodCategory.BEVERAGE),
    ("Berry Protein Smoothie", "Smoothie Bar", "12 fl oz", 210, FoodCategory.BEVERAGE),

    # Sides
    ("Steamed Fresh Broccoli", "Sides", "1/2 Cup", 30, FoodCategory.SIDE),
    ("Golden French Fries", "Grill", "3 oz", 190, FoodCategory.SIDE),
    ("Seasoned Black Beans", "Latin", "1/2 Cup", 110, FoodCategory.SIDE),
    ("Garlic Mashed Potatoes", "Homestyle", "1/2 Cup", 130, FoodCategory.SIDE),
    ("Sweet Yellow Corn", "Sides", "1/2 Cup", 80, FoodCategory.SIDE),
])
def test_comprehensive_food_categorization(item_name, station, serving, calories, expected_category):
    cat = categorize_food_item(name=item_name, station=station, serving_size=serving, calories=calories)
    assert cat == expected_category, f"Failed on '{item_name}': got {cat}, expected {expected_category}"


# ============================================================================
# 2. Custom Station Detection Tests
# ============================================================================

@pytest.mark.parametrize("station_name,expected_type", [
    ("Earhart Mongolian Stir Fry", CustomStationType.STIR_FRY),
    ("Wiley Wok Action Line", CustomStationType.STIR_FRY),
    ("Fresh Salad Bar & Greens", CustomStationType.SALAD_BAR),
    ("Garden Salad Station", CustomStationType.SALAD_BAR),
    ("Sub Station & Deli Bar", CustomStationType.DELI),
    ("Made-to-Order Sandwich Bar", CustomStationType.DELI),
    ("Wiley Custom Pizza Bar", CustomStationType.PIZZA_BAR),
    ("Custom Flatbread Creation", CustomStationType.PIZZA_BAR),
    ("Fiesta Taco Bar", CustomStationType.TACO_BAR),
    ("Burrito & Fajita Station", CustomStationType.TACO_BAR),
    ("Italian Custom Pasta Bar", CustomStationType.PASTA_BAR),
    ("Build Your Own Bowl Line", CustomStationType.GENERIC_MYO),
    ("Make Your Own Waffle Station", CustomStationType.GENERIC_MYO),
    ("Traditional Grill Line", None),
    ("Homestyle Entrees", None),
])
def test_custom_station_detection(station_name, expected_type):
    station_type = detect_custom_station_type(station_name)
    assert station_type == expected_type


# ============================================================================
# 3. Kitchen Measurement & Disher / Ladle / Cut Normalization Tests
# ============================================================================

@pytest.mark.parametrize("kitchen_str,expected_label,expected_fl_oz", [
    ("#60 Disher", "1 Tbsp (#60 Disher)", 0.53),
    ("60 disher", "1 Tbsp (#60 Disher)", 0.53),
    ("#40 Scoop", "1.6 Tbsp (#40 Disher)", 0.80),
    ("#30 Disher", "2 Tbsp (#30 Disher)", 1.07),
    ("#24 Disher", "2.7 Tbsp (#24 Disher)", 1.33),
    ("#20 Disher", "3.2 Tbsp (#20 Disher)", 1.60),
    ("#16 Disher", "1/4 Cup (#16 Disher)", 2.00),
    ("#12 Disher", "1/3 Cup (#12 Disher)", 2.67),
    ("#8 Disher", "1/2 Cup (#8 Disher)", 4.00),
    ("#4 Disher", "1 Cup (#4 Disher)", 8.00),
    ("1OZ LADLE", "2 Tbsp (1 oz Ladle)", 1.0),
    ("2 OZ LADLE", "1/4 Cup (2 oz Ladle)", 2.0),
    ("4 oz ladle", "1/2 Cup (4 oz Ladle)", 4.0),
    ("12 Cut", "1 Slice (1/12 sheet cut)", None),
    ("24 Cut", "1 Slice (1/24 sheet cut)", None),
    ("48 Cut", "1 Slice (1/48 sheet cut)", None),
    ("1/2 Cup", "1/2 Cup", None),
    ("1 Each", "1 Each", None),
])
def test_serving_size_normalization(kitchen_str, expected_label, expected_fl_oz):
    label, fl_oz, count, unit, is_single = parse_serving_size(kitchen_str)
    assert label == expected_label
    if expected_fl_oz is not None:
        assert fl_oz is not None
        assert abs(fl_oz - expected_fl_oz) < 0.05
    else:
        assert fl_oz is None


# ============================================================================
# 4. Bulk Anomaly Detection & Rescaling Tests
# ============================================================================

def test_sauce_bulk_5_gallon_anomaly_rescaling():
    # Scenario: 5 gallons of ranch dressing entered as 1 batch serving
    raw_nut = NutritionData(
        calories=28000.0,
        serving_size="5 Gallon Batch",
        protein_g=20.0,
        carbohydrates_g=150.0,
        fat_g=3000.0,
        saturated_fat_g=450.0,
        sodium_mg=42000.0,
        fiber_g=0.0,
        sugar_g=100.0
    )
    norm = normalize_nutrition_data(raw_nut, FoodCategory.SAUCE_DRESSING)

    assert norm.rescaled_from_bulk is True
    assert "2 Tbsp (normalized from batch)" in norm.normalized_serving_size
    assert 100.0 <= norm.calories <= 160.0
    assert norm.fat_g < 20.0
    assert norm.sodium_mg < 400.0
    assert norm.net_carbohydrates_g == norm.carbohydrates_g


def test_topping_condiment_batch_rescaling():
    # Scenario: 10 lb tub of sour cream logged as 8,500 calories
    raw_nut = NutritionData(
        calories=8500.0,
        serving_size="Half Pan Batch",
        protein_g=80.0,
        carbohydrates_g=120.0,
        fat_g=850.0,
        saturated_fat_g=500.0,
        sodium_mg=3500.0,
        fiber_g=0.0,
        sugar_g=100.0
    )
    norm = normalize_nutrition_data(raw_nut, FoodCategory.TOPPING_CONDIMENT)

    assert norm.rescaled_from_bulk is True
    assert "1 Tbsp (normalized from batch)" in norm.normalized_serving_size
    assert 50.0 <= norm.calories <= 100.0
    assert norm.fat_g < 10.0


def test_standard_entree_not_rescaled():
    # Scenario: A hearty entree with 750 calories is NOT flagged as bulk anomaly
    raw_nut = NutritionData(
        calories=750.0,
        serving_size="1 Plate",
        protein_g=45.0,
        carbohydrates_g=55.0,
        fat_g=25.0,
        sodium_mg=950.0,
        fiber_g=6.0
    )
    norm = normalize_nutrition_data(raw_nut, FoodCategory.ENTREE)

    assert norm.rescaled_from_bulk is False
    assert norm.calories == 750.0
    assert norm.protein_g == 45.0
    assert norm.net_carbohydrates_g == 49.0  # 55 - 6


# ============================================================================
# 5. Density-Aware Semantic Descriptor Quality Tests
# ============================================================================

def test_full_descriptor_spectrum():
    # High protein, low carb, low sodium, good fiber entree
    healthy_entree = NutritionData(
        calories=320.0,
        protein_g=42.0,       # p:very-high-protein
        carbohydrates_g=12.0, # net_carbs = 7.0 -> netcarb:low
        fiber_g=5.0,          # fib:good-source
        sugar_g=1.0,          # sug:light
        fat_g=8.0,            # fat:moderate
        saturated_fat_g=1.2,  # sat:light
        sodium_mg=120.0,      # sod:light
    )
    descriptors = generate_all_descriptors(healthy_entree, FoodCategory.ENTREE)

    assert "p:very-high-protein" in descriptors
    assert "sod:light" in descriptors
    assert "fib:good-source" in descriptors
    assert "netcarb:low" in descriptors
    assert "sug:light" in descriptors
    assert "fat:moderate" in descriptors
    assert "sat:light" in descriptors


def test_dessert_descriptor_spectrum():
    # High sugar, high fat dessert
    dessert = NutritionData(
        calories=450.0,
        protein_g=4.0,
        carbohydrates_g=65.0,
        fiber_g=1.0,
        sugar_g=38.0,         # sug:very-sweet
        fat_g=26.0,           # fat:dense
        saturated_fat_g=9.0,  # sat:dense
        sodium_mg=350.0,      # sod:moderate
    )
    descriptors = generate_all_descriptors(dessert, FoodCategory.DESSERT_SNACK)

    assert "sug:very-sweet" in descriptors
    assert "fat:dense" in descriptors
    assert "sat:dense" in descriptors
    assert "p:light" in descriptors
    assert "netcarb:high-carb" in descriptors
