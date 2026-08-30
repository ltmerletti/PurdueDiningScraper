"""
Unit tests for high-speed HFS API Client and enrichment pipeline.
"""
import pytest
from unittest.mock import AsyncMock, patch
from purdue_menu.hfs_client import HFSClient, get_enriched_court_menu, parse_hfs_nutrition
from purdue_menu.food_types import FoodCategory


def test_parse_hfs_nutrition():
    raw_item = {
        "ServingSize": "1 Each",
        "Nutrition": [
            {"Name": "Calories", "Value": 250},
            {"Name": "Protein", "Value": 15},
            {"Name": "Total Carbohydrate", "Value": 30},
            {"Name": "Dietary Fiber", "Value": 5},
            {"Name": "Total Fat", "Value": 8},
            {"Name": "Sodium", "Value": 450}
        ]
    }
    nutrition = parse_hfs_nutrition(raw_item, FoodCategory.ENTREE)
    assert nutrition.calories == 250.0
    assert nutrition.protein_g == 15.0
    assert nutrition.carbohydrates_g == 30.0
    assert nutrition.fiber_g == 5.0
    assert nutrition.net_carbohydrates_g == 25.0
    assert nutrition.sodium_mg == 450.0


@pytest.mark.asyncio
async def test_get_enriched_court_menu():
    mock_menu = {
        "Location": "Wiley",
        "Date": "2026-08-30",
        "Meals": [
            {
                "Name": "Lunch",
                "Status": "Open",
                "Stations": [
                    {
                        "Name": "Wiley Grill",
                        "Items": [
                            {"ID": "w1", "Name": "Grilled Chicken Breast", "IsVegetarian": False}
                        ]
                    },
                    {
                        "Name": "Salad Bar",
                        "Items": [
                            {"ID": "s1", "Name": "Romaine Lettuce", "IsVegetarian": True}
                        ]
                    }
                ]
            }
        ]
    }

    client = HFSClient()
    with patch.object(client, "get_court_daily_menu", new_callable=AsyncMock) as mock_daily:
        mock_daily.return_value = mock_menu

        res = await get_enriched_court_menu("Wiley", client=client)

        assert res["location"] == "Wiley"
        assert len(res["meals"]) == 1
        assert len(res["custom_stations"]) == 1
        assert res["custom_stations"][0]["station_type"] == "SALAD_BAR"
