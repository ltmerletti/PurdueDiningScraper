"""
Food categories, custom station taxonomies, and categorization heuristics.
"""
from enum import Enum
from typing import Optional, List, Tuple
import re


class FoodCategory(str, Enum):
    ENTREE = "ENTREE"
    SIDE = "SIDE"
    SAUCE_DRESSING = "SAUCE_DRESSING"
    TOPPING_CONDIMENT = "TOPPING_CONDIMENT"
    BREAD_BAKERY = "BREAD_BAKERY"
    DESSERT_SNACK = "DESSERT_SNACK"
    BEVERAGE = "BEVERAGE"
    CUSTOM_STATION = "CUSTOM_STATION"


class CustomStationType(str, Enum):
    STIR_FRY = "STIR_FRY"
    SALAD_BAR = "SALAD_BAR"
    DELI = "DELI"
    PIZZA_BAR = "PIZZA_BAR"
    TACO_BAR = "TACO_BAR"
    PASTA_BAR = "PASTA_BAR"
    GENERIC_MYO = "GENERIC_MYO"


# Discrete piece items where HFS logs nutrition per 1 piece (requiring portion awareness)
DISCRETE_PIECE_KEYWORDS = {
    "potsticker", "potstickers", "dumpling", "dumplings", "egg roll", "egg rolls",
    "spring roll", "spring rolls", "wing", "wings", "nugget", "nuggets", "tender",
    "tenders", "meatball", "meatballs", "taco", "tacos", "strip", "strips",
    "taquito", "taquitos", "cookie", "cookies", "donut", "doughnut", "muffin",
    "biscuit", "biscuits", "roll", "rolls", "patty", "patties"
}

# Station name patterns mapped to CustomStationType
STATION_MYO_PATTERNS: List[Tuple[re.Pattern, CustomStationType]] = [
    (re.compile(r"stir[- ]?fry|wok", re.IGNORECASE), CustomStationType.STIR_FRY),
    (re.compile(r"salad\s*bar|greens|garden", re.IGNORECASE), CustomStationType.SALAD_BAR),
    (re.compile(r"deli|sub\s*station|sandwich\s*bar", re.IGNORECASE), CustomStationType.DELI),
    (re.compile(r"pizza\s*bar|custom\s*pizza|flatbread\s*creation", re.IGNORECASE), CustomStationType.PIZZA_BAR),
    (re.compile(r"taco\s*bar|burrito|fajita|mexican\s*station", re.IGNORECASE), CustomStationType.TACO_BAR),
    (re.compile(r"pasta\s*bar|noodle\s*bar|custom\s*pasta", re.IGNORECASE), CustomStationType.PASTA_BAR),
    (re.compile(r"make\s*your\s*own|build\s*your\s*own|byo|myo", re.IGNORECASE), CustomStationType.GENERIC_MYO),
]

# Keywords for rule-based food categorization
BEVERAGE_KEYWORDS = {
    "milk", "coffee", "tea", "coke", "coca-cola", "pepsi", "soda", "water", "juice",
    "lemonade", "cider", "latte", "cappuccino", "espresso", "smoothie",
    "gatorade", "powerade", "punch", "beverage", "soft drink"
}

DESSERT_KEYWORDS = {
    "cookie", "cookies", "cake", "cakes", "brownie", "brownies", "pudding",
    "ice cream", "gelato", "pie", "cupcake", "donut", "doughnut", "muffin",
    "parfait", "sorbet", "frosting", "churro", "pastry", "bar", "fudge", "crisp",
    "cobbler", "sundae", "cheesecake"
}

BREAD_KEYWORDS = {
    "roll", "rolls", "bread", "bun", "buns", "bagel", "bagels", "toast",
    "biscuit", "biscuits", "croissant", "pita", "naan", "tortilla", "garlic bread",
    "cornbread", "breadstick", "breadsticks", "focaccia"
}

SAUCE_DRESSING_KEYWORDS = {
    "sauce", "dressing", "gravy", "vinaigrette", "syrup", "salsa", "marinara",
    "alfredo", "ranch", "mayonnaise", "mayo", "mustard", "ketchup", "bbq sauce",
    "barbecue sauce", "teriyaki", "sriracha", "hollandaise", "pesto", "tzatziki",
    "hummus", "aioli", "glaze", "oil", "vinegar", "dip"
}

TOPPING_CONDIMENT_KEYWORDS = {
    "cheese", "crouton", "croutons", "pickle", "pickles", "jalapeno", "jalapenos",
    "olive", "olives", "bacon bits", "sour cream", "guacamole", "butter",
    "margarine", "sprinkles", "parmesan", "relish", "topping", "toppings"
}

# Explicit multi-word entree dishes
ENTREE_PRIMARY_KEYWORDS = {
    "chicken", "beef", "pork", "steak", "fish", "salmon", "tilapia", "turkey",
    "burger", "patty", "pizza", "casserole", "curry", "stir-fry", "lasagna",
    "tofu", "tempeh", "tacos", "taco", "enchilada", "burrito", "meatball", "meatballs",
    "meatloaf", "sausage", "bratwurst", "hot dog", "ribs", "shrimp", "cod",
    "roast", "pot roast", "filet", "tenderloin", "wings", "tenders", "nuggets",
    "fried rice", "lo mein", "pad thai", "fajitas", "quesadilla", "sandwich",
    "wrap", "panini", "gyro", "macaroni and cheese", "mac & cheese", "spaghetti",
    "ravioli", "manicotti", "ziti", "fettuccine", "penne", "linguine", "calzone",
    "omelet", "omelette", "frittata", "quiche", "potsticker", "potstickers",
    "dumpling", "dumplings", "egg roll", "egg rolls", "spring roll", "spring rolls"
}

SIDE_KEYWORDS = {
    "broccoli", "carrots", "carrot", "green beans", "corn", "peas", "french fries",
    "fries", "mashed potatoes", "potato", "potatoes", "tater tots", "beans",
    "rice", "quinoa", "coleslaw", "slaw", "salad", "asparagus", "spinach",
    "zucchini", "squash", "cauliflower", "edamame", "chips", "hashbrown", "hash browns"
}


def detect_custom_station_type(station_name: str) -> Optional[CustomStationType]:
    """Detect if a station is an interactive / build-your-own station."""
    if not station_name:
        return None
    for pattern, station_type in STATION_MYO_PATTERNS:
        if pattern.search(station_name):
            return station_type
    return None


def categorize_food_item(
    name: str,
    station: Optional[str] = None,
    serving_size: Optional[str] = None,
    calories: Optional[float] = None
) -> FoodCategory:
    """
    Categorize a food item based on its name, station, serving size, and nutritional characteristics.
    """
    name_lower = name.lower().strip()
    station_lower = (station or "").lower().strip()
    serving_lower = (serving_size or "").lower().strip()

    # 1. Station-based check for custom interactive stations
    if station:
        station_type = detect_custom_station_type(station)
        if station_type and ("bar" in name_lower or "station" in name_lower or "line" in name_lower):
            return FoodCategory.CUSTOM_STATION

    # 2. Beverage check
    for kw in BEVERAGE_KEYWORDS:
        if re.search(rf"\b{re.escape(kw)}\b", name_lower):
            return FoodCategory.BEVERAGE

    # 3. Dessert / Sweet snack check
    for kw in DESSERT_KEYWORDS:
        if re.search(rf"\b{re.escape(kw)}\b", name_lower):
            return FoodCategory.DESSERT_SNACK

    # 4. Bread & Bakery check
    for kw in BREAD_KEYWORDS:
        if re.search(rf"\b{re.escape(kw)}\b", name_lower):
            return FoodCategory.BREAD_BAKERY

    # 5. Dedicated Sauces / Dressings check (must take precedence when item explicitly ends in or is a Sauce/Dressing)
    if any(re.search(rf"\b{re.escape(kw)}\b", name_lower) for kw in ["sauce", "dressing", "vinaigrette", "gravy", "syrup", "dip"]):
        return FoodCategory.SAUCE_DRESSING

    # 6. Specific Toppings / Condiments check (pickles, cheeses, croutons)
    if any(re.search(rf"\b{re.escape(kw)}\b", name_lower) for kw in ["pickle", "pickles", "jalapeno", "crouton", "croutons", "relish", "butter", "sour cream"]):
        return FoodCategory.TOPPING_CONDIMENT

    # 7. Primary Entree check
    for kw in ENTREE_PRIMARY_KEYWORDS:
        if re.search(rf"\b{re.escape(kw)}\b", name_lower):
            return FoodCategory.ENTREE

    # 8. Broader Sauce / Dressing check
    for kw in SAUCE_DRESSING_KEYWORDS:
        if re.search(rf"\b{re.escape(kw)}\b", name_lower):
            return FoodCategory.SAUCE_DRESSING

    # 9. Side check
    for kw in SIDE_KEYWORDS:
        if re.search(rf"\b{re.escape(kw)}\b", name_lower):
            return FoodCategory.SIDE

    # 10. Remaining Topping & Condiment check
    for kw in TOPPING_CONDIMENT_KEYWORDS:
        if re.search(rf"\b{re.escape(kw)}\b", name_lower):
            return FoodCategory.TOPPING_CONDIMENT

    # 11. Serving size hints
    if any(unit in serving_lower for unit in ["ladle", "tbsp", "tsp", "fl oz"]):
        if calories is not None and calories < 250:
            return FoodCategory.SAUCE_DRESSING

    # 12. Fallback heuristics based on calories
    if calories is not None:
        if calories >= 250:
            return FoodCategory.ENTREE
        elif calories >= 15:
            return FoodCategory.SIDE
        else:
            return FoodCategory.TOPPING_CONDIMENT

    return FoodCategory.SIDE
