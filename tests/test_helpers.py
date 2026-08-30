"""
Tests for helper functions (format_statistics, save_menu_data, parse_numeric).
"""
import pytest
import json
import tempfile
import os
from src.purdue_menu.utils import format_statistics, save_menu_data, parse_numeric


class TestFormatStatistics:
    """Tests for format_statistics function."""

    def test_format_statistics_empty(self):
        """Test formatting empty statistics."""
        result = format_statistics({})
        assert result == ""

    def test_format_statistics_with_data(self):
        """Test formatting statistics with data."""
        stats = {
            "Breakfast": [
                {
                    "location": "Court A",
                    "averages": {
                        "cal": 200.0,
                        "prot": 10.0,
                        "carb": 30.0,
                        "fat": 5.0,
                        "sug": 5.0
                    },
                    "protein_per_100_cal": 5.0
                }
            ]
        }
        result = format_statistics(stats)
        assert "NUTRITION STATISTICS" in result
        assert "Court A" in result
        assert "200" in result
        assert "10.0" in result

    def test_format_statistics_empty_meal(self):
        """Test formatting statistics with empty meal."""
        stats = {
            "Breakfast": []
        }
        result = format_statistics(stats)
        assert "BREAKFAST" in result.upper()
        assert "No data available" in result


class TestSaveMenuData:
    """Tests for save_menu_data function."""

    def test_save_menu_data_normal(self):
        """Test saving menu data in normal format."""
        data = {"Breakfast": {"common": [], "courts": {}}}
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name

        try:
            save_menu_data(data, temp_path, for_llm=False)
            assert os.path.exists(temp_path)

            with open(temp_path, 'r') as f:
                loaded = json.load(f)
            assert loaded == data
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_save_menu_data_llm_format(self):
        """Test saving menu data in LLM format."""
        data = {"Breakfast": {"common": [], "courts": {}}}
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name

        try:
            save_menu_data(data, temp_path, for_llm=True)
            assert os.path.exists(temp_path)

            with open(temp_path, 'r') as f:
                content = f.read()
            # LLM format should be compact (no indentation)
            assert '\n' not in content or content.count('\n') < 2
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
