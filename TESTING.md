# Testing Guide

This guide explains how to test the Purdue Dining Menu Helper application.

## Prerequisites

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure you have Chrome/Chromium installed (required for web scraping)

## 1. Run Automated Tests

### Run All Tests
```bash
pytest
```

### Run with Verbose Output
```bash
pytest -v
```

### Run Specific Test File
```bash
pytest tests/test_api.py
pytest tests/test_scraper.py
pytest tests/test_helpers.py
```

### Run with Coverage Report
```bash
pytest --cov=src.purdue_menu --cov-report=html
# Then open htmlcov/index.html in your browser
```

### Run Specific Test
```bash
pytest tests/test_api.py::TestHealthEndpoints::test_root_endpoint
```

## 2. Test the API Server

### Start the API Server
```bash
python run_api.py
# or
uvicorn src.purdue_menu.api:app --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### Test Health Endpoint
```bash
# Using curl
curl http://localhost:8000/health

# Using Python
python -c "import requests; print(requests.get('http://localhost:8000/health').json())"
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2024-12-20T14:30:00.123456"
}
```

### Test Menu Endpoint (Basic)
```bash
curl -X POST http://localhost:8000/api/menus \
  -H "Content-Type: application/json" \
  -d '{
    "meals": ["Breakfast"],
    "threads": 1
  }'
```

### Test Menu Endpoint (With Date)
```bash
curl -X POST http://localhost:8000/api/menus \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2024/12/20",
    "meals": ["Breakfast"],
    "location": "Earhart",
    "threads": 2
  }'
```

### Test Statistics Endpoint
```bash
curl "http://localhost:8000/api/menus/statistics?meals=Breakfast&date=2024/12/20"
```

### Test Cache Endpoints
```bash
# Get cache info
curl http://localhost:8000/api/cache/info

# Clear cache
curl -X DELETE http://localhost:8000/api/cache
```

### View API Documentation
Open in browser: `http://localhost:8000/docs`

This provides an interactive Swagger UI where you can test all endpoints.

## 3. Test the CLI

### Basic Usage
```bash
python main.py --meals Breakfast
```

### With Date and Location
```bash
python main.py --date 2024/12/20 --location "Earhart" --meals Breakfast
```

### With Statistics
```bash
python main.py --meals Breakfast --statistics
```

### Using Local API (Faster)
```bash
python main.py --use-local --meals Breakfast
```

### LLM-Optimized Output
```bash
python main.py --for-llm --meals Breakfast --output menu_llm
```

### Full Example
```bash
python main.py \
  --date 2024/12/20 \
  --location "Earhart" \
  --meals Breakfast Lunch \
  --statistics \
  --output my_menu \
  --threads 3
```

## 4. Integration Testing Script

Create a test script to verify everything works:

```python
#!/usr/bin/env python3
"""Quick integration test script."""
import requests
import json
import time

API_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint."""
    print("Testing health endpoint...")
    response = requests.get(f"{API_URL}/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    print("✓ Health check passed")

def test_menu_endpoint():
    """Test menu endpoint (this will take a while as it scrapes)."""
    print("\nTesting menu endpoint (this may take 30-60 seconds)...")
    payload = {
        "meals": ["Breakfast"],
        "threads": 1,
        "date": "2024/12/20"
    }
    response = requests.post(f"{API_URL}/api/menus", json=payload, timeout=120)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "data" in data
    print("✓ Menu endpoint passed")
    return data

def test_cache():
    """Test cache functionality."""
    print("\nTesting cache...")
    # Get cache info
    response = requests.get(f"{API_URL}/api/cache/info")
    assert response.status_code == 200
    print(f"✓ Cache info: {response.json()}")
    
    # Clear cache
    response = requests.delete(f"{API_URL}/api/cache")
    assert response.status_code == 200
    print("✓ Cache cleared")

if __name__ == "__main__":
    print("Starting integration tests...")
    print("Make sure the API server is running: python run_api.py\n")
    
    try:
        test_health()
        test_cache()
        # Uncomment to test actual scraping (takes time)
        # test_menu_endpoint()
        print("\n✓ All tests passed!")
    except requests.exceptions.ConnectionError:
        print("\n✗ Error: Could not connect to API server")
        print("Start the server with: python run_api.py")
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
```

Save as `test_integration.py` and run:
```bash
python test_integration.py
```

## 5. Manual Testing Checklist

### API Server
- [ ] Server starts without errors
- [ ] Health endpoint returns 200
- [ ] API docs accessible at `/docs`
- [ ] Menu endpoint accepts requests
- [ ] Cache endpoints work
- [ ] CORS headers present (for frontend)

### CLI
- [ ] CLI runs without errors
- [ ] Help message displays: `python main.py --help`
- [ ] Output file is created
- [ ] Statistics display correctly
- [ ] Local API mode works (`--use-local`)

### Scraper
- [ ] Can scrape menu data
- [ ] Handles missing dates gracefully
- [ ] Filters locations correctly
- [ ] Processes multiple meals
- [ ] Generates statistics correctly

## 6. Performance Testing

### Test Response Times
```bash
# Time a menu request
time curl -X POST http://localhost:8000/api/menus \
  -H "Content-Type: application/json" \
  -d '{"meals": ["Breakfast"], "threads": 1}'
```

### Test Caching Performance
```bash
# First request (should be slow - actual scraping)
time curl -X POST http://localhost:8000/api/menus \
  -H "Content-Type: application/json" \
  -d '{"meals": ["Breakfast"], "threads": 1}'

# Second request (should be fast - from cache)
time curl -X POST http://localhost:8000/api/menus \
  -H "Content-Type: application/json" \
  -d '{"meals": ["Breakfast"], "threads": 1}'
```

## 7. Error Handling Tests

### Test Invalid Input
```bash
# Invalid threads (too high)
curl -X POST http://localhost:8000/api/menus \
  -H "Content-Type: application/json" \
  -d '{"threads": 15}'
# Should return 422 validation error

# Invalid date format
curl -X POST http://localhost:8000/api/menus \
  -H "Content-Type: application/json" \
  -d '{"date": "invalid-date"}'
```

### Test Server Offline
```bash
# Stop the server, then try:
python main.py --meals Breakfast
# Should show connection error
```

## 8. Quick Smoke Test

Run this one-liner to verify basic functionality:

```bash
# Start server in background, test, then stop
python run_api.py &
sleep 2
curl http://localhost:8000/health && echo "✓ API is working"
pkill -f "python run_api.py"
```

## Troubleshooting

### Tests Fail
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check Python version: `python --version` (should be 3.8+)

### API Won't Start
- Check if port 8000 is in use: `lsof -i :8000`
- Try a different port: `uvicorn src.purdue_menu.api:app --port 8001`

### Scraping Fails
- Ensure Chrome/Chromium is installed
- Check internet connection
- Verify the dining website is accessible

### Import Errors
- Ensure you're in the project root directory
- Activate virtual environment: `source .venv/bin/activate`
- Install package in development mode: `pip install -e .`


