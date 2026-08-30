"""
FastMCP Server instance setup and tool registrations for Purdue Dining.
Compatible with official Python MCP SDK.
"""
from typing import Optional, List, Dict, Any, Union
from mcp.server.fastmcp import FastMCP
from .tools import (
    tool_get_current_date,
    tool_get_open_locations,
    tool_get_court_menu,
    tool_find_dishes,
    tool_get_custom_stations,
    tool_get_item_nutrition,
    tool_assemble_meal,
)

mcp = FastMCP("purdue-dining")


@mcp.tool()
async def get_current_date() -> Dict[str, Any]:
    """
    Get the current real-world date, day of the week, and formatted date string.
    Recommended to call this first before querying menus, meal periods, or hours to ensure you are referencing today's date.
    """
    return await tool_get_current_date()


@mcp.tool()
async def get_open_locations(date: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get all Purdue dining locations, their operating status, meal periods (Breakfast, Lunch, Dinner),
    and opening/closing hours.

    Args:
        date: Optional date formatted as YYYY-MM-DD or YYYY/MM/DD (defaults to today).
    """
    return await tool_get_open_locations(date=date)


@mcp.tool()
async def get_court_menu(
    location: str,
    meal: Optional[str] = None,
    date: Optional[str] = None,
    category: Optional[str] = None,
    include_nutrition: bool = False
) -> Dict[str, Any]:
    """
    Get the menu for a specific Purdue dining court (e.g. 'Wiley', 'Earhart', 'Ford', 'Hillenbrand', 'Windsor').

    Args:
        location: Dining court name (e.g., "Wiley", "Earhart").
        meal: Optional meal period ("Breakfast", "Lunch", "Late Lunch", "Dinner").
        date: Optional date (YYYY-MM-DD).
        category: Optional food category filter ("ENTREE", "SIDE", "SAUCE_DRESSING", "DESSERT_SNACK", "BEVERAGE").
        include_nutrition: Set to True to receive full numerical nutrition facts in addition to semantic tags.
    """
    return await tool_get_court_menu(
        location=location,
        meal=meal,
        date=date,
        category=category,
        include_nutrition=include_nutrition
    )


@mcp.tool()
async def find_dishes(
    min_protein: Optional[Union[str, float]] = None,
    max_calories: Optional[float] = None,
    max_sodium: Optional[Union[str, float]] = None,
    max_net_carbs: Optional[Union[str, float]] = None,
    max_fat: Optional[float] = None,
    category: Optional[str] = "ENTREE",
    dietary: Optional[str] = None,
    court: Optional[str] = None,
    meal: Optional[str] = None,
    date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Perform a targeted nutritional search across dining courts without loading full menus.
    Accepts exact numbers (e.g., min_protein=25, max_sodium=600) or qualitative descriptors
    (e.g., min_protein='protein-rich' or 'protein-dense', max_sodium='moderate', max_net_carbs='low').

    Args:
        min_protein: Minimum protein threshold (e.g., 25 or 'protein-dense').
        max_calories: Maximum calories limit.
        max_sodium: Maximum sodium limit in mg or descriptor ('moderate', 'light').
        max_net_carbs: Maximum net carbs in grams or descriptor ('low', 'very-low').
        max_fat: Maximum fat in grams.
        category: Food category filter (default 'ENTREE', or 'SIDE', 'ALL', etc.).
        dietary: Dietary tag ('Vegetarian', 'Vegan', 'Gluten-Free').
        court: Filter to a specific court (e.g., 'Wiley').
        meal: Filter to a specific meal ('Breakfast', 'Lunch', 'Dinner').
        date: Optional date (YYYY-MM-DD).
    """
    return await tool_find_dishes(
        min_protein=min_protein,
        max_calories=max_calories,
        max_sodium=max_sodium,
        max_net_carbs=max_net_carbs,
        max_fat=max_fat,
        category=category,
        dietary=dietary,
        court=court,
        meal=meal,
        date=date
    )


@mcp.tool()
async def get_custom_stations(
    court: Optional[str] = None,
    meal: Optional[str] = None,
    date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Query active build-your-own / interactive stations (Stir Fry, Salad Bar, Deli, Taco Bar, Pizza Bar)
    which return dynamic options rather than single static dishes.

    Args:
        court: Optional court name ('Earhart', 'Wiley', etc.).
        meal: Optional meal period ('Lunch', 'Dinner').
        date: Optional date.
    """
    return await tool_get_custom_stations(court=court, meal=meal, date=date)


@mcp.tool()
async def get_item_nutrition(
    item_id: Optional[str] = None,
    item_name: Optional[str] = None,
    court: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Get detailed unrounded nutrition facts, allergens, ingredients, and normalized serving sizes for a single dish.

    Args:
        item_id: Purdue HFS UUID or item identifier.
        item_name: Food dish name to search if item_id is unknown.
        court: Optional dining court to narrow search by dish name.
    """
    return await tool_get_item_nutrition(item_id=item_id, item_name=item_name, court=court)


@mcp.tool()
async def assemble_meal(
    items: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Calculate exact combined nutritional totals for an assembled meal plate (e.g., entree + side + sauce).

    Args:
        items: List of dictionaries specifying dishes and portions, e.g.:
               [{"name": "Grilled Chicken Breast", "servings": 1.5}, {"name": "Brown Rice", "servings": 1.0}]
    """
    return await tool_assemble_meal(items=items)


def create_mcp_server() -> FastMCP:
    """Return the configured FastMCP server instance."""
    return mcp
