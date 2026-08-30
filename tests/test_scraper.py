"""
Tests for scraper functionality.
"""
import sys
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import date

# Provide mock for webdriver_manager if not installed in local test environment
if "webdriver_manager" not in sys.modules:
    mock_wdm = MagicMock()
    mock_wdm_chrome = MagicMock()
    mock_wdm.chrome = mock_wdm_chrome
    sys.modules["webdriver_manager"] = mock_wdm
    sys.modules["webdriver_manager.chrome"] = mock_wdm_chrome

from src.purdue_menu.scraper import (
    PurdueDiningScraper,
    parse_numeric,
    NUT_MAP
)
from src.purdue_menu.driver import create_driver, build_chrome_options


class TestParseNumeric:
    """Tests for parse_numeric function."""

    def test_parse_simple_number(self):
        """Test parsing simple numbers."""
        assert parse_numeric("14g") == 14.0
        assert parse_numeric("5.5g") == 5.5

    def test_parse_with_commas(self):
        """Test parsing numbers with commas."""
        assert parse_numeric("1,200mg") == 1200.0

    def test_parse_with_less_than(self):
        """Test parsing values with < prefix."""
        assert parse_numeric("<1 g") == 1.0

    def test_parse_empty_string(self):
        """Test parsing empty string."""
        assert parse_numeric("") == 0.0
        assert parse_numeric(None) == 0.0

    def test_parse_invalid_string(self):
        """Test parsing invalid strings."""
        assert parse_numeric("abc") == 0.0
        assert parse_numeric("no numbers here") == 0.0


class TestPurdueDiningScraper:
    """Tests for PurdueDiningScraper class."""

    def test_init_defaults(self):
        """Test scraper initialization with defaults."""
        scraper = PurdueDiningScraper()
        assert scraper.date_target == date.today().strftime("%Y/%m/%d")
        assert scraper.meals == ["Breakfast", "Lunch", "Dinner"]
        assert scraper.threads == 5
        assert scraper.visible is False

    def test_init_custom_params(self):
        """Test scraper initialization with custom parameters."""
        scraper = PurdueDiningScraper(
            date="2024/01/15",
            location="Test Court",
            meals=["Breakfast"],
            threads=2,
            for_llm=True
        )
        assert scraper.date_target == "2024/01/15"
        assert scraper.location_filter == "Test Court"
        assert scraper.meals == ["Breakfast"]
        assert scraper.threads == 2
        assert scraper.for_llm is True

    @patch('selenium.webdriver.Chrome')
    @patch('selenium.webdriver.chrome.service.Service')
    @patch('webdriver_manager.chrome.ChromeDriverManager')
    @patch('os.path.exists')
    @patch('sys.platform', 'linux')
    def test_create_driver_linux(self, mock_exists, mock_chrome_manager, mock_service, mock_chrome):
        """Test driver creation on Linux/Docker."""
        scraper = PurdueDiningScraper()
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        mock_exists.side_effect = lambda path: path == "/usr/bin/google-chrome"

        driver = scraper.create_driver()
        assert driver is not None
        mock_chrome.assert_called_once()

    @patch('selenium.webdriver.Chrome')
    @patch('selenium.webdriver.chrome.service.Service')
    @patch('webdriver_manager.chrome.ChromeDriverManager')
    @patch('os.path.exists')
    @patch('sys.platform', 'darwin')
    def test_create_driver_macos(self, mock_exists, mock_chrome_manager, mock_service, mock_chrome):
        """Test driver creation on macOS."""
        scraper = PurdueDiningScraper()
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        mock_exists.side_effect = lambda path: "/Applications/Google Chrome.app" in path

        driver = scraper.create_driver()
        assert driver is not None
        mock_chrome.assert_called_once()

    @patch('selenium.webdriver.Chrome')
    @patch('selenium.webdriver.chrome.service.Service')
    @patch('webdriver_manager.chrome.ChromeDriverManager')
    @patch('os.path.exists')
    @patch('sys.platform', 'linux')
    def test_create_driver_chromium_fallback(self, mock_exists, mock_chrome_manager, mock_service, mock_chrome):
        """Test driver creation with Chromium fallback."""
        scraper = PurdueDiningScraper()
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        mock_exists.side_effect = lambda path: path == "/usr/bin/chromium"

        driver = scraper.create_driver()
        assert driver is not None
        mock_chrome.assert_called_once()

    def test_process_results_empty(self):
        """Test processing empty results."""
        scraper = PurdueDiningScraper()
        results = []
        output = scraper.process_results(results)
        assert output == {}

    def test_process_results_single_meal(self):
        """Test processing results for a single meal."""
        scraper = PurdueDiningScraper()
        results = [
            {
                "meal": "Breakfast",
                "location": "Court A",
                "stations": [
                    {
                        "station": "Station 1",
                        "items": [
                            {
                                "name": "Item 1",
                                "details": {
                                    "is_collection": False,
                                    "nutrition": {
                                        "Calories": "200",
                                        "Protein": "10g",
                                        "Total Carbohydrate": "30g"
                                    }
                                }
                            }
                        ]
                    }
                ]
            }
        ]
        output = scraper.process_results(results)
        assert "Breakfast" in output
        assert "courts" in output["Breakfast"]
        assert "Court A" in output["Breakfast"]["courts"]

    def test_process_results_for_llm(self):
        """Test processing results with LLM optimization."""
        scraper = PurdueDiningScraper(for_llm=True)
        results = [
            {
                "meal": "Breakfast",
                "location": "Court A",
                "stations": [
                    {
                        "station": "Station 1",
                        "items": [
                            {
                                "name": "Item 1",
                                "details": {
                                    "is_collection": False,
                                    "nutrition": {
                                        "Calories": "200",
                                        "Protein": "10g"
                                    }
                                }
                            }
                        ]
                    }
                ]
            }
        ]
        output = scraper.process_results(results)
        item = output["Breakfast"]["courts"]["Court A"][0]
        assert "cal" in item
        assert "prot" in item
        assert "n" in item

    def test_generate_statistics_empty(self):
        """Test statistics generation with empty data."""
        scraper = PurdueDiningScraper()
        data = {}
        stats = scraper.generate_statistics(data)
        assert stats == {}

    def test_generate_statistics_with_data(self):
        """Test statistics generation with data."""
        scraper = PurdueDiningScraper()
        data = {
            "Breakfast": {
                "common": [],
                "courts": {
                    "Court A": [
                        {
                            "n": "Item 1",
                            "Calories": "200",
                            "Protein": "10g",
                            "Total Carbohydrate": "30g",
                            "Total fat": "5g",
                            "Sugar": "5g"
                        },
                        {
                            "n": "Item 2",
                            "Calories": "300",
                            "Protein": "15g",
                            "Total Carbohydrate": "40g",
                            "Total fat": "8g",
                            "Sugar": "10g"
                        }
                    ]
                }
            }
        }
        stats = scraper.generate_statistics(data)
        assert "Breakfast" in stats
        assert len(stats["Breakfast"]) > 0
        assert "location" in stats["Breakfast"][0]
        assert "averages" in stats["Breakfast"][0]
        assert "protein_per_100_cal" in stats["Breakfast"][0]

    def test_generate_statistics_filters_low_cal(self):
        """Test that statistics filter out low-calorie items."""
        scraper = PurdueDiningScraper()
        data = {
            "Breakfast": {
                "common": [],
                "courts": {
                    "Court A": [
                        {
                            "n": "Water",
                            "Calories": "0",
                            "Protein": "0g"
                        },
                        {
                            "n": "Item 1",
                            "Calories": "200",
                            "Protein": "10g",
                            "Total Carbohydrate": "30g",
                            "Total fat": "5g",
                            "Sugar": "5g"
                        }
                    ]
                }
            }
        }
        stats = scraper.generate_statistics(data)
        assert len(stats["Breakfast"]) == 1


class TestNutMap:
    """Tests for nutrition key mapping."""

    def test_nut_map_keys(self):
        """Test that NUT_MAP contains expected keys."""
        assert "Calories" in NUT_MAP
        assert "Protein" in NUT_MAP
        assert "Total Carbohydrate" in NUT_MAP
