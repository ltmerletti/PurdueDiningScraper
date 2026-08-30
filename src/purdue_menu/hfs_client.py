"""
High-performance asynchronous and synchronous HTTP client for Purdue HFS REST API.
API Base: https://api.hfs.purdue.edu/menus/v2/
Includes in-memory TTL caching and graceful handling of interactive stations.
"""
import time
import datetime
import asyncio
from typing import Dict, List, Optional, Any, Union
import httpx

from .models import NutritionData, NormalizedItem, CustomStation
from .food_types import categorize_food_item, detect_custom_station_type, FoodCategory
from .normalizer import normalize_nutrition_data
from .descriptors import generate_all_descriptors

HFS_BASE_URL = "https://api.hfs.purdue.edu/menus/v2"

# In-memory caches
# _LOCATIONS_CACHE: (timestamp, data)
_LOCATIONS_CACHE: Optional[tuple[float, List[Dict[str, Any]]]] = None
_LOCATIONS_TTL = 3600 * 6  # 6 hours

# _MENUS_CACHE: key = "location:YYYY-MM-DD" -> (timestamp, data)
_MENUS_CACHE: Dict[str, tuple[float, Dict[str, Any]]] = {}
_MENUS_TTL = 3600 * 4  # 4 hours

# _ITEM_CACHE: key = item_id -> NutritionData / raw_dict
_ITEM_CACHE: Dict[str, Dict[str, Any]] = {}


class HFSClient:
    """Client for Purdue University Dining HFS REST API."""

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        self.base_url = HFS_BASE_URL

    def _get_today_str(self) -> str:
        return datetime.date.today().strftime("%Y-%m-%d")

    def _format_date(self, date_str: Optional[str]) -> str:
        if not date_str:
            return self._get_today_str()
        return date_str.replace("/", "-").strip()

    # --- Async Methods ---

    async def get_locations(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Fetch all dining locations, meal periods, and operating hours."""
        global _LOCATIONS_CACHE
        now = time.time()
        if not force_refresh and _LOCATIONS_CACHE and (now - _LOCATIONS_CACHE[0] < _LOCATIONS_TTL):
            return _LOCATIONS_CACHE[1]

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(f"{self.base_url}/locations")
            resp.raise_for_status()
            data = resp.json().get("Location", [])
            _LOCATIONS_CACHE = (now, data)
            return data

    async def get_court_daily_menu(
        self,
        location: str,
        date_str: Optional[str] = None,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """Fetch raw daily menu for a specific location and date."""
        fmt_date = self._format_date(date_str)
        cache_key = f"{location.lower().strip()}:{fmt_date}"
        now = time.time()

        if not force_refresh and cache_key in _MENUS_CACHE:
            ts, cached_data = _MENUS_CACHE[cache_key]
            if now - ts < _MENUS_TTL:
                return cached_data

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = f"{self.base_url}/locations/{location.strip()}/{fmt_date}"
            resp = await client.get(url)
            if resp.status_code == 404:
                return {}
            resp.raise_for_status()
            data = resp.json()
            _MENUS_CACHE[cache_key] = (now, data)
            return data

    async def get_item_details(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Fetch exact unrounded nutritional facts, ingredients, and allergens for an item."""
        if not item_id:
            return None
        if item_id in _ITEM_CACHE:
            return _ITEM_CACHE[item_id]

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            url = f"{self.base_url}/items/{item_id}"
            try:
                resp = await client.get(url)
                if resp.status_code in (404, 500):
                    return None
                resp.raise_for_status()
                data = resp.json()
                _ITEM_CACHE[item_id] = data
                return data
            except Exception:
                return None

    # --- Sync Wrappers (for convenient CLI/FastAPI/Testing use) ---

    def get_locations_sync(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        return asyncio.run(self.get_locations(force_refresh=force_refresh))

    def get_court_daily_menu_sync(
        self,
        location: str,
        date_str: Optional[str] = None,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        return asyncio.run(self.get_court_daily_menu(location, date_str, force_refresh=force_refresh))

    def get_item_details_sync(self, item_id: str) -> Optional[Dict[str, Any]]:
        return asyncio.run(self.get_item_details(item_id))


# --- High-Level Ingestion & Enrichment Pipeline ---

def parse_hfs_nutrition(item_json: Dict[str, Any], category: FoodCategory, item_name: Optional[str] = None) -> NutritionData:
    """Extract, parse, and normalize nutrition facts from HFS item JSON."""
    raw_nutrition = item_json.get("Nutrition", [])
    raw_dict = {}

    def get_val(name: str) -> Optional[float]:
        for n in raw_nutrition:
            if n.get("Name", "").lower() == name.lower():
                val = n.get("Value")
                raw_dict[name] = str(val)
                if val is not None:
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        return None
        return None

    serving_size = item_json.get("ServingSize") or item_json.get("ServingSizeUnit")

    nutrition = NutritionData(
        calories=get_val("Calories"),
        serving_size=str(serving_size) if serving_size else None,
        protein_g=get_val("Protein"),
        carbohydrates_g=get_val("Total Carbohydrate") or get_val("Carbohydrates"),
        fat_g=get_val("Total Fat") or get_val("Fat"),
        saturated_fat_g=get_val("Saturated Fat"),
        trans_fat_g=get_val("Trans Fat"),
        sugar_g=get_val("Sugar") or get_val("Total Sugars"),
        added_sugar_g=get_val("Added Sugar"),
        fiber_g=get_val("Dietary Fiber"),
        sodium_mg=get_val("Sodium"),
        cholesterol_mg=get_val("Cholesterol"),
        calcium_dv=get_val("Calcium"),
        iron_dv=get_val("Iron"),
        potassium_mg=get_val("Potassium"),
        raw=raw_dict
    )

    return normalize_nutrition_data(nutrition, category, item_name or item_json.get("Name"))


async def get_enriched_court_menu(
    location: str,
    date_str: Optional[str] = None,
    meal_filter: Optional[str] = None,
    fetch_nutrition: bool = False,
    client: Optional[HFSClient] = None
) -> Dict[str, Any]:
    """
    Fetch court menu and enrich items with categories, custom stations, and semantic tags.
    """
    client = client or HFSClient()
    raw_menu = await client.get_court_daily_menu(location, date_str)
    if not raw_menu:
        return {"location": location, "meals": [], "custom_stations": []}

    meals_out = []
    custom_stations = []

    raw_meals = raw_menu.get("Meals", [])
    for meal in raw_meals:
        meal_name = meal.get("Name", "")
        if meal_filter and meal_name.lower() != meal_filter.lower():
            continue

        if meal.get("Status", "").lower() != "open" and not meal.get("Stations"):
            continue

        stations_out = []
        raw_stations = meal.get("Stations", [])

        # Item nutrition lookup tasks if requested
        item_ids_to_fetch = []

        for station in raw_stations:
            st_name = station.get("Name", "")
            myo_type = detect_custom_station_type(st_name)

            if myo_type:
                custom_stations.append(
                    CustomStation(
                        court=location,
                        station_name=st_name,
                        station_type=myo_type,
                        status="OPEN",
                        available_lines=[item.get("Name") for item in station.get("Items", []) if item.get("Name")],
                        notes=f"Interactive station ({myo_type.value}) at {location}"
                    )
                )

            st_items = []
            for item in station.get("Items", []):
                item_id = item.get("ID")
                item_name = item.get("Name", "")
                if not item_name:
                    continue

                is_veg = item.get("IsVegetarian", False)
                # Infer category
                cat = categorize_food_item(name=item_name, station=st_name)

                norm_item = NormalizedItem(
                    id=item_id,
                    name=item_name,
                    court=location,
                    meal=meal_name,
                    station=st_name,
                    category=cat,
                    is_vegetarian=is_veg,
                    is_vegan=any(t.get("Name", "").lower() == "vegan" for t in item.get("Traits", [])),
                    is_gluten_free=any(t.get("Name", "").lower() == "gluten free" for t in item.get("Traits", [])),
                    allergens=[
                        a.get("Name") for a in item.get("Allergens", [])
                        if a.get("Name") and (a.get("Value") is True or a.get("IsAllergen") is True or "Value" not in a)
                    ]
                )

                if fetch_nutrition and item_id:
                    item_ids_to_fetch.append((norm_item, item_id))

                st_items.append(norm_item)

            stations_out.append({
                "station": st_name,
                "items": st_items
            })

        # Fetch nutrition concurrently if requested
        if fetch_nutrition and item_ids_to_fetch:
            tasks = [client.get_item_details(i_id) for _, i_id in item_ids_to_fetch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for (norm_item, _), res in zip(item_ids_to_fetch, results):
                if isinstance(res, dict) and res:
                    nutrition = parse_hfs_nutrition(res, norm_item.category, norm_item.name)
                    norm_item.nutrition = nutrition
                    norm_item.serving_size = nutrition.normalized_serving_size or nutrition.serving_size
                    norm_item.is_single_piece_entry = nutrition.is_single_piece_entry
                    norm_item.ingredients = res.get("Ingredients")
                    norm_item.descriptors = generate_all_descriptors(nutrition, norm_item.category)

        meals_out.append({
            "meal": meal_name,
            "status": meal.get("Status", "Open"),
            "stations": stations_out
        })

    return {
        "location": location,
        "date": raw_menu.get("Date", date_str),
        "meals": meals_out,
        "custom_stations": [cs.model_dump() for cs in custom_stations]
    }
