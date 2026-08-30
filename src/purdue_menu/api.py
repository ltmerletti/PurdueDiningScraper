"""
FastAPI application for Purdue Dining menu scraper.
Provides REST API endpoints for menu data retrieval, statistics, and caching.
"""
import logging
from datetime import date, datetime
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager
import threading

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from .models import MenuRequest, MenuResponse, HealthResponse
from .stats import calculate_statistics
from .utils import format_statistics, save_menu_data

# Lazy import scraper to speed up startup
_scraper_module = None


def get_scraper():
    """Lazy import scraper module to keep initial startup fast."""
    global _scraper_module
    if _scraper_module is None:
        from .scraper import PurdueDiningScraper
        _scraper_module = PurdueDiningScraper
    return _scraper_module


logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("PurdueAPI")

# Global cache for recent requests
_request_cache: Dict[str, Dict[str, Any]] = {}
_cache_lock = threading.Lock()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    logger.info("Starting Purdue Dining API...")
    yield
    logger.info("Shutting down Purdue Dining API...")


app = FastAPI(
    title="Purdue Dining Menu API",
    description="API for scraping and retrieving Purdue University dining menu data",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)


def _get_cache_key(request: MenuRequest) -> str:
    """Generate cache key from request parameters."""
    date_str = request.date or date.today().strftime("%Y/%m/%d")
    location_str = request.location or "all"
    meals_str = ",".join(sorted(request.meals))
    return f"{date_str}:{location_str}:{meals_str}:{request.for_llm}:{request.simple}"


@app.get("/", response_model=HealthResponse)
async def root():
    """Health check root endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat()
    )


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat()
    )


@app.post("/api/menus", response_model=MenuResponse)
async def get_menus(request: MenuRequest, background_tasks: BackgroundTasks):
    """Scrape and retrieve menu data for specified date, location, and meals."""
    try:
        cache_key = _get_cache_key(request)
        with _cache_lock:
            if cache_key in _request_cache:
                logger.info(f"Returning cached data for {cache_key}")
                cached_data = _request_cache[cache_key]
                return MenuResponse(
                    success=True,
                    data=cached_data.get("data"),
                    statistics=cached_data.get("statistics"),
                    cached=True
                )

        ScraperClass = get_scraper()
        scraper = ScraperClass(
            date=request.date,
            location=request.location,
            meals=request.meals,
            threads=request.threads,
            visible=False,
            for_llm=request.for_llm,
            simple=request.simple,
            logger=logger
        )

        logger.info(f"Starting scrape for date={request.date}, location={request.location}, meals={request.meals}")
        menu_data = scraper.run()

        if not menu_data:
            return MenuResponse(
                success=False,
                message="No menu data found for the specified parameters"
            )

        statistics_data = None
        if request.include_statistics:
            statistics_data = calculate_statistics(menu_data, for_llm=request.for_llm)

        with _cache_lock:
            if len(_request_cache) > 50:
                oldest_key = next(iter(_request_cache))
                del _request_cache[oldest_key]

            _request_cache[cache_key] = {
                "data": menu_data,
                "statistics": statistics_data
            }

        return MenuResponse(
            success=True,
            data=menu_data,
            statistics=statistics_data,
            cached=False
        )

    except Exception as e:
        logger.error(f"Error in get_menus: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/menus/statistics")
async def get_statistics(
    date: Optional[str] = None,
    location: Optional[str] = None,
    meals: Optional[str] = None,
    for_llm: bool = False
):
    """Get nutrition statistics for menu data by scraping then aggregating."""
    try:
        meal_list = meals.split(",") if meals else ["Breakfast", "Lunch", "Dinner"]

        ScraperClass = get_scraper()
        scraper = ScraperClass(
            date=date,
            location=location,
            meals=meal_list,
            threads=5,
            visible=False,
            for_llm=for_llm,
            simple=False,
            logger=logger
        )

        menu_data = scraper.run()
        if not menu_data:
            raise HTTPException(status_code=404, detail="No menu data found")

        statistics_data = calculate_statistics(menu_data, for_llm=for_llm)
        return JSONResponse(content={
            "success": True,
            "statistics": statistics_data
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.delete("/api/cache")
async def clear_cache():
    """Clear the request cache."""
    global _request_cache
    with _cache_lock:
        count = len(_request_cache)
        _request_cache.clear()
    logger.info(f"Cache cleared ({count} entries)")
    return {"success": True, "message": f"Cleared {count} cached entries"}


@app.get("/api/cache/info")
async def cache_info():
    """Get information about the cache."""
    with _cache_lock:
        return {
            "success": True,
            "cache_size": len(_request_cache),
            "cache_keys": list(_request_cache.keys())[:10]
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
