"""Check the public HFS response shapes used by the scraper, without bulk scraping."""

import asyncio
import datetime
from zoneinfo import ZoneInfo

from purdue_menu.hfs_client import HFSClient, get_enriched_court_menu


async def main():
    client = HFSClient(timeout=20)
    locations = await client.get_locations(force_refresh=True)
    if not isinstance(locations, list) or not locations:
        raise ValueError("HFS locations response must contain a non-empty Location list")
    if any(not isinstance(loc, dict) or not isinstance(loc.get("Name"), str)
           or not loc["Name"].strip() for loc in locations):
        raise ValueError("HFS location entries must have non-empty Name strings")

    # Prefer a dining court over a retail location; fall back if it is renamed.
    names = [loc["Name"] for loc in locations]
    court = "Wiley" if "Wiley" in names else names[0]
    today = datetime.datetime.now(ZoneInfo("America/Indiana/Indianapolis")).date().isoformat()
    menu = await client.get_court_daily_menu(court, today, force_refresh=True)
    if not menu:
        print(f"PASS: {len(locations)} locations; no published {court} menu for {today}")
        return
    if not isinstance(menu, dict) or not isinstance(menu.get("Meals"), list):
        raise ValueError("HFS daily menu must contain a Meals list")

    first_item_id = None
    for meal in menu["Meals"]:
        if not isinstance(meal, dict) or not isinstance(meal.get("Name"), str):
            raise ValueError("HFS meal entries must have Name strings")
        stations = meal.get("Stations", [])
        if not isinstance(stations, list):
            raise ValueError("HFS Stations must be a list")
        for station in stations:
            if not isinstance(station, dict) or not isinstance(station.get("Items", []), list):
                raise ValueError("HFS station entries must contain an Items list when present")
            for item in station.get("Items", []):
                if not isinstance(item, dict) or not isinstance(item.get("Name"), str):
                    raise ValueError("HFS menu items must have Name strings")
                first_item_id = first_item_id or item.get("ID")

    # Reuses the cached menu and exercises the application's actual parser.
    enriched = await get_enriched_court_menu(court, today, client=client)
    if first_item_id:
        details = await client.get_item_details(first_item_id)
        if not isinstance(details, dict) or not isinstance(details.get("Name"), str):
            raise ValueError("HFS item details unavailable or missing Name")
    print(f"PASS: {len(locations)} locations; {court} menu parsed for {today} "
          f"({len(enriched['meals'])} meals); item lookup {'checked' if first_item_id else 'not available'}")


if __name__ == "__main__":
    asyncio.run(main())
