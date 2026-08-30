"""
Purdue Dining Scraper, Menu Intelligence & FastMCP Package.
"""
from .models import (
    NUT_MAP,
    NutritionData,
    NormalizedItem,
    CustomStation,
    MenuItem,
    StationMenu,
    LocationMealMenu,
    LocationStats,
    MenuRequest,
    MenuResponse,
    HealthResponse,
    MealAssemblyItemRequest,
    MealAssemblyResponse,
)
from .food_types import FoodCategory, CustomStationType
from .normalizer import normalize_nutrition_data, parse_serving_size, is_bulk_anomaly
from .descriptors import generate_all_descriptors
from .hfs_client import HFSClient, get_enriched_court_menu
from .scraper import PurdueDiningScraper
from .stats import calculate_statistics
from .utils import parse_numeric, format_statistics, save_menu_data
from .api import app

__version__ = "2.0.0"

__all__ = [
    "NUT_MAP",
    "NutritionData",
    "NormalizedItem",
    "CustomStation",
    "MenuItem",
    "StationMenu",
    "LocationMealMenu",
    "LocationStats",
    "MenuRequest",
    "MenuResponse",
    "HealthResponse",
    "MealAssemblyRequest",
    "MealAssemblyResponse",
    "FoodCategory",
    "CustomStationType",
    "normalize_nutrition_data",
    "parse_serving_size",
    "is_bulk_anomaly",
    "generate_all_descriptors",
    "HFSClient",
    "get_enriched_court_menu",
    "PurdueDiningScraper",
    "calculate_statistics",
    "parse_numeric",
    "format_statistics",
    "save_menu_data",
    "app",
]
