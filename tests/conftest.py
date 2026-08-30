"""
Pytest configuration and fixtures.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from fastapi.testclient import TestClient

from src.purdue_menu.api import app


@pytest.fixture
def client():
    """Create a test client for the API."""
    return TestClient(app)


@pytest.fixture
def mock_scraper():
    """Create a mock scraper instance."""
    scraper = Mock()
    scraper.run.return_value = {
        "Breakfast": {
            "common": [],
            "courts": {
                "Test Court": [
                    {
                        "n": "Test Item",
                        "cal": "200",
                        "prot": "10g",
                        "carb": "30g",
                        "fat": "5g"
                    }
                ]
            }
        }
    }
    scraper.generate_statistics.return_value = {
        "Breakfast": [
            {
                "location": "Test Court",
                "averages": {"cal": 200.0, "prot": 10.0, "carb": 30.0, "fat": 5.0, "sug": 5.0},
                "protein_per_100_cal": 5.0
            }
        ]
    }
    return scraper


@pytest.fixture
def sample_menu_data():
    """Sample menu data for testing."""
    return {
        "Breakfast": {
            "common": [
                {"n": "Common Item", "cal": "100", "prot": "5g"}
            ],
            "courts": {
                "Court A": [
                    {"n": "Item A", "cal": "200", "prot": "10g", "carb": "30g", "fat": "5g"}
                ],
                "Court B": [
                    {"n": "Item B", "cal": "250", "prot": "15g", "carb": "35g", "fat": "8g"}
                ]
            }
        }
    }


