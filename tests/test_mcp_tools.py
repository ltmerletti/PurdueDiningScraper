"""
Unit tests for FastMCP tools and high-level query pipelines.
"""
import pytest
from unittest.mock import AsyncMock, patch
from purdue_menu.mcp.tools import (
    tool_get_current_date,
    tool_get_open_locations,
    tool_get_court_menu,
    tool_find_dishes,
    tool_get_custom_stations,
    tool_get_item_nutrition,
    tool_assemble_meal,
)


@pytest.mark.asyncio
async def test_tool_get_current_date():
    date_info = await tool_get_current_date()
    assert "date" in date_info
    assert "day_of_week" in date_info
    assert "year" in date_info
    assert len(date_info["date"].split("-")) == 3


@pytest.mark.asyncio
async def test_tool_get_open_locations():
    mock_locs = [
        {
            "Name": "Wiley",
            "FormalName": "Wiley Dining Court",
            "LocationType": "Dining Court",
            "Meals": [{"Name": "Lunch", "StartTime": "11:00", "EndTime": "14:00", "Status": "Open"}]
        }
    ]
    with patch("purdue_menu.mcp.tools.client.get_locations", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_locs
        locs = await tool_get_open_locations()
        assert len(locs) == 1
        assert locs[0]["name"] == "Wiley"
        assert len(locs[0]["open_meals"]) == 1


@pytest.mark.asyncio
async def test_tool_get_item_nutrition():
    mock_item = {
        "ID": "item-123",
        "Name": "Grilled Chicken Breast",
        "ServingSize": "1 Each",
        "Nutrition": [
            {"Name": "Calories", "Value": 180},
            {"Name": "Protein", "Value": 35},
            {"Name": "Total Fat", "Value": 3.5},
            {"Name": "Sodium", "Value": 320},
            {"Name": "Total Carbohydrate", "Value": 0},
            {"Name": "Dietary Fiber", "Value": 0},
            {"Name": "Sugar", "Value": 0}
        ],
        "Allergens": [],
        "Ingredients": "Chicken Breast, Salt, Pepper"
    }
    with patch("purdue_menu.mcp.tools.client.get_item_details", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_item
        res = await tool_get_item_nutrition(item_id="item-123")
        assert res is not None
        assert res["name"] == "Grilled Chicken Breast"
        assert res["nutrition"]["protein_g"] == 35.0
        assert "p:protein-dense" in res["descriptors"]


@pytest.mark.asyncio
async def test_tool_assemble_meal():
    mock_chicken = {
        "id": "1",
        "name": "Grilled Chicken Breast",
        "category": "ENTREE",
        "serving_size": "1 Each",
        "nutrition": {
            "calories": 180.0,
            "protein_g": 35.0,
            "carbohydrates_g": 0.0,
            "net_carbohydrates_g": 0.0,
            "fat_g": 3.5,
            "saturated_fat_g": 1.0,
            "sodium_mg": 300.0,
            "fiber_g": 0.0,
            "sugar_g": 0.0
        },
        "descriptors": ["p:protein-dense"]
    }

    mock_rice = {
        "id": "2",
        "name": "Steamed Brown Rice",
        "category": "SIDE",
        "serving_size": "1/2 Cup",
        "nutrition": {
            "calories": 110.0,
            "protein_g": 2.5,
            "carbohydrates_g": 23.0,
            "net_carbohydrates_g": 21.0,
            "fat_g": 1.0,
            "saturated_fat_g": 0.0,
            "sodium_mg": 5.0,
            "fiber_g": 2.0,
            "sugar_g": 0.0
        },
        "descriptors": ["netcarb:moderate"]
    }

    async def mock_get_item(item_id=None, item_name=None, court=None):
        if item_name == "Chicken":
            return mock_chicken
        return mock_rice

    with patch("purdue_menu.mcp.tools.tool_get_item_nutrition", side_effect=mock_get_item):
        items = [
            {"name": "Chicken", "servings": 1.5},
            {"name": "Rice", "servings": 1.0}
        ]
        result = await tool_assemble_meal(items)

        assert len(result["items"]) == 2
        # Chicken: 180 * 1.5 = 270, Rice: 110 * 1 = 110 -> 380 total cals
        assert result["totals"]["calories"] == 380.0
        # Chicken protein: 35 * 1.5 = 52.5 + 2.5 = 55.0g
        assert result["totals"]["protein_g"] == 55.0
        assert "p:very-high-protein" in result["descriptors"]
