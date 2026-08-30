"""
Tests for API endpoints.
"""
import pytest
from datetime import date
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient

from src.purdue_menu.api import app, _get_cache_key, MenuRequest


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


class TestHealthEndpoints:
    """Tests for health check endpoints."""
    
    def test_root_endpoint(self, client):
        """Test root health check endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
    
    def test_health_endpoint(self, client):
        """Test /health endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data


class TestMenuEndpoints:
    """Tests for menu endpoints."""
    
    @patch('src.purdue_menu.api.get_scraper')
    def test_get_menus_success(self, mock_get_scraper, client, mock_scraper):
        """Test successful menu retrieval."""
        mock_get_scraper.return_value = Mock(return_value=mock_scraper)
        
        request_data = {
            "meals": ["Breakfast"],
            "for_llm": False,
            "simple": False,
            "threads": 1,
            "include_statistics": False
        }
        
        # Mock the scraper to avoid actual web scraping
        with patch.object(mock_scraper, 'run', return_value={"Breakfast": {"common": [], "courts": {}}}):
            response = client.post("/api/menus", json=request_data)
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "data" in data
    
    def test_get_menus_validation(self, client):
        """Test menu request validation."""
        # Test invalid threads
        request_data = {
            "threads": 15  # Exceeds max of 10
        }
        response = client.post("/api/menus", json=request_data)
        assert response.status_code == 422  # Validation error
    
    def test_get_menus_cache(self, client):
        """Test that caching works."""
        # Clear cache first
        client.delete("/api/cache")
        
        request_data = {
            "meals": ["Breakfast"],
            "threads": 1,
            "date": "2024/01/15"  # Use specific date to avoid conflicts
        }
        
        # First request - should not be cached
        with patch('src.purdue_menu.api.get_scraper') as mock_get_scraper:
            mock_scraper_instance = Mock()
            mock_scraper_instance.run.return_value = {"Breakfast": {"common": [], "courts": {}}}
            mock_get_scraper.return_value = Mock(return_value=mock_scraper_instance)
            
            response1 = client.post("/api/menus", json=request_data)
            assert response1.status_code == 200
            assert response1.json()["cached"] is False
        
        # Second request with same params - should be cached
        response2 = client.post("/api/menus", json=request_data)
        assert response2.status_code == 200
        assert response2.json()["cached"] is True


class TestCacheEndpoints:
    """Tests for cache management endpoints."""
    
    def test_clear_cache(self, client):
        """Test clearing the cache."""
        response = client.delete("/api/cache")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "message" in data
    
    def test_cache_info(self, client):
        """Test getting cache information."""
        response = client.get("/api/cache/info")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "cache_size" in data
        assert "cache_keys" in data


class TestHelperFunctions:
    """Tests for helper functions."""
    
    def test_get_cache_key(self):
        """Test cache key generation."""
        request = MenuRequest(
            date="2024/01/15",
            location="Test",
            meals=["Breakfast", "Lunch"]
        )
        key = _get_cache_key(request)
        assert "2024/01/15" in key
        assert "Test" in key
        assert "Breakfast" in key or "Lunch" in key
    
    def test_get_cache_key_defaults(self):
        """Test cache key with default values."""
        request = MenuRequest()
        key = _get_cache_key(request)
        assert "all" in key  # Default location
        assert date.today().strftime("%Y/%m/%d") in key


class TestStatisticsEndpoint:
    """Tests for statistics endpoint."""
    
    @patch('src.purdue_menu.api.get_scraper')
    def test_get_statistics(self, mock_get_scraper, client, mock_scraper):
        """Test statistics endpoint."""
        mock_get_scraper.return_value = Mock(return_value=mock_scraper)
        
        with patch.object(mock_scraper, 'run', return_value={"Breakfast": {"common": [], "courts": {}}}):
            response = client.get("/api/menus/statistics?meals=Breakfast")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "statistics" in data

