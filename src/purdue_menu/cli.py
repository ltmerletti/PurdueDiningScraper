"""
CLI shell for Purdue Dining menu intelligence, scraper, and FastMCP server.
Supports direct CLI nutrient discovery, menu queries, and running the MCP server.
"""
import argparse
import sys
import asyncio
import json
import requests

from .utils import format_statistics, save_menu_data
from .mcp.tools import tool_find_dishes, tool_get_open_locations, tool_get_court_menu

try:
    from fastapi.testclient import TestClient
    from .api import app
    USE_LOCAL_API = True
except ImportError:
    USE_LOCAL_API = False


def call_api_local(request_data: dict):
    """Call the API locally (in-process, no HTTP overhead)."""
    client = TestClient(app)
    response = client.post("/api/menus", json=request_data)

    if response.status_code != 200:
        raise Exception(f"API error: {response.status_code} - {response.text}")

    return response.json()


def call_api_http(request_data: dict, api_url: str = "http://localhost:8000"):
    """Call the API via HTTP."""
    response = requests.post(
        f"{api_url}/api/menus",
        json=request_data,
        timeout=600
    )

    if response.status_code != 200:
        raise Exception(f"API error: {response.status_code} - {response.text}")

    return response.json()


def main():
    parser = argparse.ArgumentParser(description="Purdue Dining Scraper & Nutrition Intelligence CLI")

    parser.add_argument("--mcp", action="store_true", help="Start FastMCP server over stdio")
    parser.add_argument("--find-protein", type=str, help="Search for high-protein dishes (e.g. 25, 30, 'protein-dense')")
    parser.add_argument("--max-calories", type=float, help="Max calories filter for search")
    parser.add_argument("--max-sodium", type=str, help="Max sodium filter for search (e.g. 600, 'moderate')")
    parser.add_argument("--dietary", type=str, help="Dietary filter ('Vegetarian', 'Vegan', 'Gluten-Free')")
    parser.add_argument("--category", type=str, default="ENTREE", help="Food category for search (default: ENTREE)")

    parser.add_argument("--date", help="Date in YYYY/MM/DD or YYYY-MM-DD (default: today)")
    parser.add_argument("--location", help="Filter by dining location (e.g., Wiley, Ford, Earhart)")
    parser.add_argument("--meals", nargs="+", default=["Breakfast", "Lunch", "Dinner"],
                        help="Meals to scrape (Breakfast, Lunch, Dinner)")
    parser.add_argument("--output", default="purdue_menu", help="Output filename prefix (default: purdue_menu)")

    group = parser.add_mutually_exclusive_group()
    group.add_argument("--simple", action="store_true", help="Flatten items, omit ingredients/allergens")
    group.add_argument("--for-llm", action="store_true", help="Minify JSON keys for LLM context optimization")

    parser.add_argument("--statistics", action="store_true", help="Display macro and nutrition rankings")
    parser.add_argument("--threads", type=int, default=5, help="Number of concurrent worker threads (1-10)")
    parser.add_argument("--api-url", default="http://localhost:8000",
                        help="Remote API URL (default: http://localhost:8000)")
    parser.add_argument("--use-local", action="store_true",
                        help="Use local API in-process (faster, no HTTP daemon needed)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # 1. MCP Server runner
    if args.mcp:
        from .mcp.server import mcp
        print("Starting Purdue Dining FastMCP Server on stdio...", file=sys.stderr)
        mcp.run()
        return

    # 2. Direct Dish Search via Nutrition Intelligence
    if args.find_protein or args.max_calories or args.max_sodium or args.dietary:
        print(f"Searching dishes (min_protein={args.find_protein}, max_cals={args.max_calories}, court={args.location})...")
        dishes = asyncio.run(
            tool_find_dishes(
                min_protein=args.find_protein,
                max_calories=args.max_calories,
                max_sodium=args.max_sodium,
                category=args.category,
                dietary=args.dietary,
                court=args.location,
                date=args.date
            )
        )
        if not dishes:
            print("No matching dishes found.")
            return

        print(f"\nFound {len(dishes)} matching items:")
        print("-" * 80)
        for d in dishes[:20]:
            print(f"• {d['name']} ({d['court']} - {d['meal']} / {d['station']})")
            print(f"  Serving: {d['serving_size']} | Cals: {d['calories']} | Prot: {d['protein_g']}g | NetCarb: {d['net_carbs_g']}g | Fat: {d['fat_g']}g | Sod: {d['sodium_mg']}mg")
            if d.get("descriptors"):
                print(f"  Tags: {', '.join(d['descriptors'])}")
            print()
        return

    # 3. Standard Scraper / API runner
    request_data = {
        "date": args.date,
        "location": args.location,
        "meals": args.meals,
        "for_llm": args.for_llm,
        "simple": args.simple,
        "threads": args.threads,
        "include_statistics": args.statistics
    }

    try:
        if args.use_local and USE_LOCAL_API:
            if args.verbose:
                print("Using local in-process runner...")
            result = call_api_local(request_data)
        else:
            if args.verbose:
                print(f"Connecting to API at {args.api_url}...")
            result = call_api_http(request_data, api_url=args.api_url)

        if not result.get("success"):
            print(f"Error: {result.get('message', 'Unknown error')}", file=sys.stderr)
            sys.exit(1)

        if result.get("cached"):
            print("Retrieved from cache.")
        else:
            print("Scraping completed successfully.")

        output_file = f"{args.output}.json"
        menu_data = result.get("data", {})
        save_menu_data(menu_data, output_file, for_llm=args.for_llm)
        print(f"Saved to {output_file}")

        if args.statistics and result.get("statistics"):
            print(format_statistics(result["statistics"], for_llm=args.for_llm))

        print("Done.")

    except requests.exceptions.ConnectionError:
        print(f"Error: Could not connect to API at {args.api_url}", file=sys.stderr)
        print("Tip: Run locally with `--use-local` or start the server via `python run_api.py`", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
