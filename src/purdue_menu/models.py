"""
Pydantic data models and schemas for Purdue Dining menus and nutrition intelligence.
Compatible with existing scraping pipeline while enabling FastMCP server tools.
"""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from .food_types import FoodCategory, CustomStationType


NUT_MAP = {
    "Calories": "cal",
    "Serving Size": "ss",
    "Protein": "prot",
    "Total Carbohydrate": "carb",
    "Total fat": "fat",
    "Saturated fat": "sat_fat",
    "Sugar": "sug",
    "Dietary Fiber": "fib",
    "Sodium": "sod",
    "Cholesterol": "chol"
}


class NutritionData(BaseModel):
    """Nutritional facts for a single food item with exact numbers and normalization metadata."""
    calories: Optional[float] = Field(None, description="Calories in kcal")
    serving_size: Optional[str] = Field(None, description="Raw or original serving size string")
    normalized_serving_size: Optional[str] = Field(None, description="Normalized consumer-friendly serving string")
    portion_count: Optional[float] = Field(None, description="Parsed piece/unit count if discrete item (e.g. 1.0 for '1 Potsticker')")
    portion_unit: Optional[str] = Field(None, description="Portion unit (e.g. 'piece', 'potsticker', 'wing', 'slice', 'cup', 'tbsp')")
    is_single_piece_entry: bool = Field(False, description="True if nutritional entry represents a single unit/piece rather than a full meal serving")
    protein_g: Optional[float] = Field(None, description="Protein in grams")
    carbohydrates_g: Optional[float] = Field(None, description="Total carbohydrates in grams")
    net_carbohydrates_g: Optional[float] = Field(None, description="Net carbohydrates (Total Carb - Fiber) in grams")
    fat_g: Optional[float] = Field(None, description="Total fat in grams")
    saturated_fat_g: Optional[float] = Field(None, description="Saturated fat in grams")
    trans_fat_g: Optional[float] = Field(None, description="Trans fat in grams")
    sugar_g: Optional[float] = Field(None, description="Total sugar in grams")
    added_sugar_g: Optional[float] = Field(None, description="Added sugar in grams")
    fiber_g: Optional[float] = Field(None, description="Dietary fiber in grams")
    sodium_mg: Optional[float] = Field(None, description="Sodium in mg")
    cholesterol_mg: Optional[float] = Field(None, description="Cholesterol in mg")
    calcium_dv: Optional[float] = Field(None, description="Calcium % Daily Value")
    iron_dv: Optional[float] = Field(None, description="Iron % Daily Value")
    potassium_mg: Optional[float] = Field(None, description="Potassium in mg")
    rescaled_from_bulk: bool = Field(False, description="True if scaled down from institutional batch size")
    raw: Dict[str, str] = Field(default_factory=dict, description="Original unparsed nutrition key-values")


class NormalizedItem(BaseModel):
    """A fully enriched menu item ready for MCP tool output and LLM reasoning."""
    id: Optional[str] = Field(None, description="Purdue HFS UUID or item ID")
    name: str = Field(..., description="Food item name")
    court: Optional[str] = Field(None, description="Dining court name (e.g. Wiley, Earhart)")
    meal: Optional[str] = Field(None, description="Meal period (e.g. Breakfast, Lunch, Dinner)")
    station: Optional[str] = Field(None, description="Station name within the dining court")
    category: FoodCategory = Field(FoodCategory.SIDE, description="Classified food role")
    serving_size: Optional[str] = Field(None, description="Portion / serving size label")
    is_single_piece_entry: bool = Field(False, description="Flag indicating entry represents 1 unit/piece")
    is_vegetarian: bool = False
    is_vegan: bool = False
    is_gluten_free: bool = False
    allergens: List[str] = Field(default_factory=list, description="Allergen tags")
    ingredients: Optional[str] = Field(None, description="Ingredient list text")
    nutrition: Optional[NutritionData] = None
    descriptors: List[str] = Field(default_factory=list, description="Qualitative semantic density descriptors")


class CustomStation(BaseModel):
    """An interactive build-your-own station (e.g., Stir Fry, Salad Bar, Deli)."""
    court: str
    station_name: str
    station_type: CustomStationType
    status: str = Field("OPEN", description="Operating status (OPEN / CLOSED)")
    available_lines: List[str] = Field(default_factory=list, description="Available component bars/lines")
    notes: Optional[str] = Field(None, description="Custom assembly instructions or notes")


class MenuItem(BaseModel):
    """Legacy individual menu item or component for backwards compatibility."""
    name: str
    station: Optional[str] = None
    url: Optional[str] = None
    is_collection: bool = False
    nutrition: Dict[str, Any] = Field(default_factory=dict)
    ingredients: Optional[str] = None
    allergens: List[str] = Field(default_factory=list)
    components: List["MenuItem"] = Field(default_factory=list)


class StationMenu(BaseModel):
    """Menu items grouped under a specific dining court station."""
    station: str
    items: List[MenuItem] = Field(default_factory=list)


class LocationMealMenu(BaseModel):
    """Menu for a specific location and meal."""
    location: str
    meal: str
    stations: List[StationMenu] = Field(default_factory=list)


class LocationStats(BaseModel):
    """Macro and calorie averages for a dining court."""
    location: str
    averages: Dict[str, float]
    protein_per_100_cal: float


class MealAssemblyItemRequest(BaseModel):
    """Individual item component for assemble_meal tool."""
    item_id: Optional[str] = None
    name: Optional[str] = None
    servings: float = Field(1.0, gt=0, description="Number of portions/servings")


class MealAssemblyResponse(BaseModel):
    """Aggregated nutritional totals and evaluation for an assembled combination meal."""
    items: List[Dict[str, Any]] = Field(default_factory=list)
    total_calories: float = 0.0
    total_protein_g: float = 0.0
    total_carbohydrates_g: float = 0.0
    total_net_carbohydrates_g: float = 0.0
    total_fat_g: float = 0.0
    total_saturated_fat_g: float = 0.0
    total_sodium_mg: float = 0.0
    total_fiber_g: float = 0.0
    total_sugar_g: float = 0.0
    descriptors: List[str] = Field(default_factory=list)


class MenuRequest(BaseModel):
    """API / Scraper invocation request parameters."""
    date: Optional[str] = Field(None, description="Date in YYYY/MM/DD or YYYY-MM-DD format (default: today)")
    location: Optional[str] = Field(None, description="Filter by location name")
    meals: Optional[List[str]] = Field(
        default=["Breakfast", "Lunch", "Dinner"],
        description="List of meals to scrape"
    )
    for_llm: bool = Field(False, description="Minify JSON for LLM consumption")
    simple: bool = Field(False, description="Flatten items, omit ingredients/allergens")
    threads: int = Field(5, ge=1, le=10, description="Number of threads (1-10)")
    include_statistics: bool = Field(False, description="Include nutrition statistics")


class MenuResponse(BaseModel):
    """API / Scraper output payload."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    statistics: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    cached: bool = False


class HealthResponse(BaseModel):
    """Health check status."""
    status: str
    timestamp: str
