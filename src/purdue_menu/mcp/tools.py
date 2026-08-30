"""
FastMCP tool implementations for Purdue Dining & Nutrition Intelligence.
Enables token-efficient querying of locations, menus, dishes, custom stations,
item nutrition, and combination meal assembly.
"""
import asyncio
import datetime
from typing import List, Optional, Dict, Any, Union
from ..hfs_client import HFSClient, get_enriched_court_menu, parse_hfs_nutrition
from ..food_types import FoodCategory, detect_custom_station_type, categorize_food_item
from ..descriptors import (
    parse_protein_filter,
    parse_sodium_filter,
    parse_net_carbs_filter,
    generate_all_descriptors
)
from ..models import CustomStation, MealAssemblyResponse, NutritionData

client = HFSClient()


async def tool_get_current_date() -> Dict[str, Any]:
    """
    Get the current system date, day of week, and ISO format date.
    Recommended to call this before looking up menus or schedules if date is unspecified.
    """
    now = datetime.datetime.now()
    return {
        "date": now.strftime("%Y-%m-%d"),
        "day_of_week": now.strftime("%A"),
        "iso": now.isoformat(),
        "year": now.year,
        "month": now.month,
        "day": now.day,
        "formatted": now.strftime("%A, %B %d, %Y"),
    }


async def tool_get_open_locations(date: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fast check of which dining courts and locations are open, operating hours, and meal periods.
    """
    locations = await client.get_locations()
    results = []

    for loc in locations:
        loc_name = loc.get("Name", "")
        # Filter for dining courts / dining locations
        meals = loc.get("Meals", []) or loc.get("NormalHours", [])
        results.append({
            "name": loc_name,
            "formal_name": loc.get("FormalName", loc_name),
            "location_type": loc.get("LocationType", "Dining Court"),
            "url": loc.get("Url"),
            "open_meals": [
                {
                    "name": m.get("Name"),
                    "start": m.get("StartTime"),
                    "end": m.get("EndTime"),
                    "status": m.get("Status", "Open")
                }
                for m in loc.get("Meals", [])
            ]
        })

    return results


async def tool_get_court_menu(
    location: str,
    meal: Optional[str] = None,
    date: Optional[str] = None,
    category: Optional[str] = None,
    include_nutrition: bool = False
) -> Dict[str, Any]:
    """
    Get the menu for a dining court, organized by station.
    Keeps token context lightweight unless include_nutrition is requested.
    """
    enriched = await get_enriched_court_menu(
        location=location,
        date_str=date,
        meal_filter=meal,
        fetch_nutrition=include_nutrition,
        client=client
    )

    cat_filter = category.upper().strip() if category else None

    # Filter categories if requested
    for meal_entry in enriched.get("meals", []):
        for station in meal_entry.get("stations", []):
            filtered_items = []
            for item in station.get("items", []):
                if cat_filter and item.category.value != cat_filter:
                    continue
                item_dict = {
                    "id": item.id,
                    "name": item.name,
                    "category": item.category.value,
                    "serving_size": item.serving_size,
                    "is_single_piece_entry": item.is_single_piece_entry,
                    "is_vegetarian": item.is_vegetarian,
                    "is_vegan": item.is_vegan,
                    "is_gluten_free": item.is_gluten_free,
                    "allergens": item.allergens,
                    "descriptors": item.descriptors,
                }
                if include_nutrition and item.nutrition:
                    item_dict["nutrition"] = {
                        "calories": item.nutrition.calories,
                        "serving_size": item.nutrition.normalized_serving_size or item.nutrition.serving_size,
                        "portion_count": item.nutrition.portion_count,
                        "portion_unit": item.nutrition.portion_unit,
                        "is_single_piece_entry": item.nutrition.is_single_piece_entry,
                        "protein_g": item.nutrition.protein_g,
                        "carbs_g": item.nutrition.carbohydrates_g,
                        "net_carbs_g": item.nutrition.net_carbohydrates_g,
                        "fat_g": item.nutrition.fat_g,
                        "sat_fat_g": item.nutrition.saturated_fat_g,
                        "sodium_mg": item.nutrition.sodium_mg,
                        "fiber_g": item.nutrition.fiber_g,
                        "sugar_g": item.nutrition.sugar_g,
                        "rescaled_from_bulk": item.nutrition.rescaled_from_bulk
                    }
                filtered_items.append(item_dict)
            station["items"] = filtered_items

    return enriched


async def tool_find_dishes(
    min_protein: Optional[Union[str, float, int]] = None,
    max_calories: Optional[float] = None,
    max_sodium: Optional[Union[str, float, int]] = None,
    max_net_carbs: Optional[Union[str, float, int]] = None,
    max_fat: Optional[float] = None,
    category: Optional[str] = "ENTREE",
    dietary: Optional[str] = None,
    court: Optional[str] = None,
    meal: Optional[str] = None,
    date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Nutritional search across dining courts without loading full menus.
    Accepts exact numbers or intuitive qualitative strings ('protein-dense', 'moderate', 'low').
    """
    min_p = parse_protein_filter(min_protein)
    max_sod = parse_sodium_filter(max_sodium)
    max_nc = parse_net_carbs_filter(max_net_carbs)

    # Determine locations to query
    if court:
        courts = [court]
    else:
        courts = ["Wiley", "Earhart", "Ford", "Hillenbrand", "Windsor"]

    tasks = [
        get_enriched_court_menu(
            location=c,
            date_str=date,
            meal_filter=meal,
            fetch_nutrition=True,
            client=client
        )
        for c in courts
    ]
    all_menus = await asyncio.gather(*tasks, return_exceptions=True)

    matched_dishes = []
    cat_filter = category.upper().strip() if category and category.upper() != "ALL" else None
    dietary_lower = dietary.lower().strip() if dietary else None

    for menu_data in all_menus:
        if isinstance(menu_data, Exception) or not menu_data:
            continue

        c_name = menu_data.get("location")
        for meal_obj in menu_data.get("meals", []):
            m_name = meal_obj.get("meal")
            for station in meal_obj.get("stations", []):
                st_name = station.get("station")
                for item in station.get("items", []):
                    # Category match
                    if cat_filter and item.category.value != cat_filter:
                        continue

                    # Dietary match
                    if dietary_lower:
                        if "veg" in dietary_lower and not (item.is_vegetarian or item.is_vegan):
                            continue
                        if "vegan" in dietary_lower and not item.is_vegan:
                            continue
                        if "gluten" in dietary_lower and not item.is_gluten_free:
                            continue

                    nut = item.nutrition
                    if not nut:
                        continue

                    # Nutrition filters
                    if min_p is not None and (nut.protein_g is None or nut.protein_g < min_p):
                        continue
                    if max_calories is not None and (nut.calories is None or nut.calories > max_calories):
                        continue
                    if max_sod is not None and (nut.sodium_mg is None or nut.sodium_mg > max_sod):
                        continue
                    if max_nc is not None and (nut.net_carbohydrates_g is None or nut.net_carbohydrates_g > max_nc):
                        continue
                    if max_fat is not None and (nut.fat_g is None or nut.fat_g > max_fat):
                        continue

                    matched_dishes.append({
                        "name": item.name,
                        "court": c_name,
                        "meal": m_name,
                        "station": st_name,
                        "category": item.category.value,
                        "serving_size": nut.normalized_serving_size or nut.serving_size,
                        "portion_count": nut.portion_count,
                        "portion_unit": nut.portion_unit,
                        "is_single_piece_entry": nut.is_single_piece_entry,
                        "calories": nut.calories,
                        "protein_g": nut.protein_g,
                        "carbs_g": nut.carbohydrates_g,
                        "net_carbs_g": nut.net_carbohydrates_g,
                        "fat_g": nut.fat_g,
                        "sodium_mg": nut.sodium_mg,
                        "fiber_g": nut.fiber_g,
                        "sugar_g": nut.sugar_g,
                        "descriptors": item.descriptors,
                        "rescaled_from_bulk": nut.rescaled_from_bulk
                    })

    # Sort dishes by protein descending by default
    matched_dishes.sort(key=lambda x: (x.get("protein_g") or 0.0), reverse=True)
    return matched_dishes


async def tool_get_custom_stations(
    court: Optional[str] = None,
    meal: Optional[str] = None,
    date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Query interactive build-your-own stations (Stir Fry, Salad Bar, Deli, Taco Bar).
    """
    courts = [court] if court else ["Wiley", "Earhart", "Ford", "Hillenbrand", "Windsor"]
    tasks = [
        get_enriched_court_menu(location=c, date_str=date, meal_filter=meal, fetch_nutrition=False, client=client)
        for c in courts
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_custom_stations = []
    for res in results:
        if isinstance(res, dict) and "custom_stations" in res:
            all_custom_stations.extend(res["custom_stations"])

    return all_custom_stations


async def tool_get_item_nutrition(
    item_id: Optional[str] = None,
    item_name: Optional[str] = None,
    court: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Deep-dive into a single item's ingredients, allergens, and micronutrients.
    """
    raw_details = None

    if item_id:
        raw_details = await client.get_item_details(item_id)

    # Fallback to searching by name if ID is missing or not found
    if not raw_details and item_name:
        courts = [court] if court else ["Wiley", "Earhart", "Ford", "Hillenbrand", "Windsor"]
        for c in courts:
            menu = await client.get_court_daily_menu(c)
            for m in menu.get("Meals", []):
                for st in m.get("Stations", []):
                    for it in st.get("Items", []):
                        if it.get("Name", "").lower().strip() == item_name.lower().strip():
                            found_id = it.get("ID")
                            if found_id:
                                raw_details = await client.get_item_details(found_id)
                                break
                    if raw_details:
                        break
                if raw_details:
                    break
            if raw_details:
                break

    if not raw_details:
        return None

    item_name_resolved = raw_details.get("Name", item_name or "")
    cat = categorize_food_item(
        name=item_name_resolved,
        serving_size=raw_details.get("ServingSize"),
    )
    nutrition = parse_hfs_nutrition(raw_details, cat, item_name_resolved)
    descriptors = generate_all_descriptors(nutrition, cat)

    return {
        "id": raw_details.get("ID") or item_id,
        "name": item_name_resolved,
        "category": cat.value,
        "serving_size": nutrition.normalized_serving_size or nutrition.serving_size,
        "portion_count": nutrition.portion_count,
        "portion_unit": nutrition.portion_unit,
        "is_single_piece_entry": nutrition.is_single_piece_entry,
        "original_serving_size": nutrition.serving_size,
        "rescaled_from_bulk": nutrition.rescaled_from_bulk,
        "nutrition": {
            "calories": nutrition.calories,
            "protein_g": nutrition.protein_g,
            "carbohydrates_g": nutrition.carbohydrates_g,
            "net_carbohydrates_g": nutrition.net_carbohydrates_g,
            "fat_g": nutrition.fat_g,
            "saturated_fat_g": nutrition.saturated_fat_g,
            "trans_fat_g": nutrition.trans_fat_g,
            "cholesterol_mg": nutrition.cholesterol_mg,
            "sodium_mg": nutrition.sodium_mg,
            "fiber_g": nutrition.fiber_g,
            "sugar_g": nutrition.sugar_g,
            "added_sugar_g": nutrition.added_sugar_g,
            "calcium_dv": nutrition.calcium_dv,
            "iron_dv": nutrition.iron_dv,
            "potassium_mg": nutrition.potassium_mg,
        },
        "descriptors": descriptors,
        "allergens": [
            a.get("Name") for a in raw_details.get("Allergens", [])
            if a.get("Name") and (a.get("Value") is True or a.get("IsAllergen") is True or "Value" not in a)
        ],
        "ingredients": raw_details.get("Ingredients")
    }


async def tool_assemble_meal(
    items: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Calculate exact aggregate nutritional totals for a combination meal.
    items: list of {'item_id': str, 'name': str, 'servings': float}
    """
    total_cal = 0.0
    total_prot = 0.0
    total_carb = 0.0
    total_net_carb = 0.0
    total_fat = 0.0
    total_sat_fat = 0.0
    total_sod = 0.0
    total_fib = 0.0
    total_sug = 0.0

    resolved_items = []

    for req_item in items:
        i_id = req_item.get("item_id")
        i_name = req_item.get("name")
        servings = float(req_item.get("servings", 1.0))

        details = await tool_get_item_nutrition(item_id=i_id, item_name=i_name)
        if not details:
            resolved_items.append({
                "name": i_name or i_id,
                "servings": servings,
                "status": "NOT_FOUND"
            })
            continue

        nut = details.get("nutrition", {})
        cals = (nut.get("calories") or 0.0) * servings
        prot = (nut.get("protein_g") or 0.0) * servings
        carbs = (nut.get("carbohydrates_g") or 0.0) * servings
        net_carbs = (nut.get("net_carbohydrates_g") or 0.0) * servings
        fat = (nut.get("fat_g") or 0.0) * servings
        sat_fat = (nut.get("saturated_fat_g") or 0.0) * servings
        sod = (nut.get("sodium_mg") or 0.0) * servings
        fib = (nut.get("fiber_g") or 0.0) * servings
        sug = (nut.get("sugar_g") or 0.0) * servings

        total_cal += cals
        total_prot += prot
        total_carb += carbs
        total_net_carb += net_carbs
        total_fat += fat
        total_sat_fat += sat_fat
        total_sod += sod
        total_fib += fib
        total_sug += sug

        resolved_items.append({
            "name": details.get("name"),
            "servings": servings,
            "serving_size": details.get("serving_size"),
            "calories": round(cals, 1),
            "protein_g": round(prot, 1),
            "carbs_g": round(carbs, 1),
            "net_carbs_g": round(net_carbs, 1),
            "fat_g": round(fat, 1),
            "sodium_mg": round(sod, 1),
            "descriptors": details.get("descriptors", [])
        })

    aggregate_nutrition = NutritionData(
        calories=round(total_cal, 1),
        protein_g=round(total_prot, 1),
        carbohydrates_g=round(total_carb, 1),
        net_carbohydrates_g=round(total_net_carb, 1),
        fat_g=round(total_fat, 1),
        saturated_fat_g=round(total_sat_fat, 1),
        sodium_mg=round(total_sod, 1),
        fiber_g=round(total_fib, 1),
        sugar_g=round(total_sug, 1),
    )

    meal_descriptors = generate_all_descriptors(aggregate_nutrition, FoodCategory.ENTREE)

    return {
        "items": resolved_items,
        "totals": {
            "calories": round(total_cal, 1),
            "protein_g": round(total_prot, 1),
            "carbohydrates_g": round(total_carb, 1),
            "net_carbohydrates_g": round(total_net_carb, 1),
            "fat_g": round(total_fat, 1),
            "saturated_fat_g": round(total_sat_fat, 1),
            "sodium_mg": round(total_sod, 1),
            "fiber_g": round(total_fib, 1),
            "sugar_g": round(total_sug, 1),
        },
        "descriptors": meal_descriptors
    }
