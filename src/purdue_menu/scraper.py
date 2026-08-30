"""
Core scraper module for Purdue Dining menus.
Provides headless Selenium-based crawling, item parsing, and structured menu extraction.
"""
import os
import re
import time
import random
import datetime
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Any

from .models import NUT_MAP
from .driver import create_driver, build_chrome_options
from .utils import parse_numeric
from .stats import calculate_statistics

os.environ['WDM_LOG_LEVEL'] = '0'


class PurdueDiningScraper:
    """Thread-safe core scraper for Purdue Dining menus."""

    def __init__(
        self,
        date: Optional[str] = None,
        location: Optional[str] = None,
        meals: Optional[List[str]] = None,
        threads: int = 5,
        visible: bool = False,
        for_llm: bool = False,
        simple: bool = False,
        logger: Optional[logging.Logger] = None
    ):
        self.base_url = "https://dining.purdue.edu"
        self.date_target = date or datetime.date.today().strftime("%Y/%m/%d")
        self.location_filter = location
        self.meals = meals or ["Breakfast", "Lunch", "Dinner"]
        self.threads = max(1, min(threads, 10))
        self.visible = visible
        self.for_llm = for_llm
        self.simple = simple
        self.logger = logger or logging.getLogger("PurdueScraper")

        self.item_cache: Dict[str, Any] = {}
        self.cache_lock = threading.Lock()

    def create_driver(self):
        """Create a new Chrome WebDriver instance."""
        return create_driver(visible=self.visible)

    def get_item_details(self, driver, item_url: str, depth: int = 0) -> Optional[Dict[str, Any]]:
        """Fetch detailed nutrition information for a menu item."""
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        if depth > 1:
            return None

        with self.cache_lock:
            if item_url in self.item_cache:
                return self.item_cache[item_url]

        try:
            driver.get(item_url)
            WebDriverWait(driver, 6).until(
                EC.presence_of_element_located((By.CLASS_NAME, "item-widget-name__name"))
            )

            # Check if it's a collection (combo meal)
            is_collection = bool(driver.find_elements(
                By.XPATH, "//div[contains(@class, 'item-widget-title')]/span[text()='Components']"
            ))

            if is_collection:
                result = self._parse_collection(driver, depth)
            else:
                result = self._parse_single_item(driver)

            with self.cache_lock:
                self.item_cache[item_url] = result
            return result

        except Exception as e:
            self.logger.debug(f"Error fetching {item_url}: {e}")
            return None

    def _parse_collection(self, driver, depth: int) -> Dict[str, Any]:
        """Parse a collection/combo item."""
        from selenium.webdriver.common.by import By

        components = []
        for link in driver.find_elements(By.CSS_SELECTOR, "div.station-item--container_plain a.station-item"):
            try:
                name = link.find_element(By.CLASS_NAME, "station-item-text").text.strip()
                href = link.get_attribute("href")
                if href:
                    details = self.get_item_details(driver, href, depth + 1)
                    if details:
                        components.append({"name": name, "details": details})
            except Exception:
                continue

        return {"is_collection": True, "components": components}

    def _parse_single_item(self, driver) -> Dict[str, Any]:
        """Parse nutrition info for a single item."""
        from selenium.webdriver.common.by import By

        data = {"is_collection": False, "nutrition": {}, "ingredients": "Not listed", "allergens": []}

        # Nutrition table rows
        for row in driver.find_elements(By.CLASS_NAME, "nutrition-table-row"):
            try:
                label = row.find_element(By.CLASS_NAME, "table-row-label").text.strip()
                vals = row.find_elements(By.CLASS_NAME, "table-row-labelValue")
                if vals:
                    data["nutrition"][label] = vals[0].text.strip()
            except Exception:
                continue

        # Header stats
        for cls, key in [("nutrition-feature-calories-quantity", "Calories"),
                         ("nutrition-feature-servingSize-quantity", "Serving Size")]:
            els = driver.find_elements(By.CLASS_NAME, cls)
            if els:
                data["nutrition"][key] = els[0].text.strip()

        # Ingredients and allergens
        try:
            data["ingredients"] = driver.find_element(By.CLASS_NAME, "nutrition-ingredient-list").text.strip()
        except Exception:
            pass
        data["allergens"] = [a.text.strip() for a in driver.find_elements(By.CLASS_NAME, "allergen-name")]

        return data

    def scan_locations(self) -> List[Dict[str, Any]]:
        """Scan dining locations and return menu structure."""
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        target_meals = [m.capitalize() for m in self.meals]
        self.logger.info(f"Scanning {self.date_target} for: {', '.join(target_meals)}")

        driver = self.create_driver()
        courts_data = []

        try:
            driver.get(f"{self.base_url}/menus/")
            wait = WebDriverWait(driver, 10)
            header = wait.until(EC.presence_of_element_located((By.ID, "Dining Courts-heading")))
            container = header.find_element(By.XPATH, "./ancestor::section")

            # Get all dining courts
            base_courts = []
            for link in container.find_elements(By.CLASS_NAME, "menus__home-content--link"):
                raw_url = link.get_attribute("href")
                try:
                    name = link.find_element(By.CSS_SELECTOR, "span.MuiListItemText-primary").text
                except Exception:
                    name = "Unknown"

                if self.location_filter and self.location_filter.lower() not in name.lower():
                    continue

                match = re.search(r"/menus/([^/]+)/", raw_url)
                if match:
                    base_courts.append((name, match.group(1)))

            # Check each court/meal combination
            for name, slug in base_courts:
                for meal in target_meals:
                    url = f"{self.base_url}/menus/{slug}/{self.date_target}/{meal}/"
                    driver.get(url)

                    try:
                        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "station")))

                        # Verify we didn't get redirected to a different meal
                        active_els = driver.find_elements(By.CLASS_NAME, "mealpicker-meal-name")
                        if active_els and active_els[0].text.strip() != meal:
                            continue

                        menu_structure = self._extract_menu_structure(driver)
                        total = sum(len(s["items"]) for s in menu_structure)

                        if total > 0:
                            courts_data.append({
                                "location": name, "meal": meal, "url": url,
                                "menu_structure": menu_structure, "total_items": total
                            })
                            self.logger.info(f"Found {name} ({meal}): {total} items")
                        else:
                            self.logger.info(f"{name} ({meal}): Open but empty.")
                    except Exception:
                        self.logger.info(f"{name} ({meal}): Closed.")
        finally:
            driver.quit()

        return courts_data

    def _extract_menu_structure(self, driver) -> List[Dict[str, Any]]:
        """Extract menu structure from current page."""
        from selenium.webdriver.common.by import By

        menu_structure = []
        for station in driver.find_elements(By.CLASS_NAME, "station"):
            try:
                s_name = station.find_element(By.CLASS_NAME, "station-name").text.split("\n")[0].strip()
                items = []
                for link in station.find_elements(By.CSS_SELECTOR, "div.station-item--container_plain a.station-item"):
                    i_name = link.find_element(By.CLASS_NAME, "station-item-text").text.strip()
                    items.append({"name": i_name, "url": link.get_attribute("href")})
                menu_structure.append({"station": s_name, "items": items})
            except Exception:
                continue
        return menu_structure

    def scrape_worker(self, court_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Worker function to scrape a single court's menu."""
        driver = self.create_driver()
        try:
            final_stations = []
            for station in court_data["menu_structure"]:
                processed_items = []
                for item in station["items"]:
                    with self.cache_lock:
                        cached = self.item_cache.get(item["url"])

                    details = cached if cached else self.get_item_details(driver, item["url"])
                    if not cached:
                        time.sleep(random.uniform(0.05, 0.15))

                    if details:
                        processed_items.append({"name": item["name"], "details": details})

                final_stations.append({"station": station["station"], "items": processed_items})

            return {
                "meal": court_data["meal"],
                "location": court_data["location"],
                "stations": final_stations
            }
        except Exception as e:
            self.logger.error(f"Error processing {court_data['location']}: {e}")
            return None
        finally:
            driver.quit()

    def _process_node(self, name: str, details: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single nutrition item node."""
        nut_raw = details.get('nutrition', {})
        if not nut_raw:
            return None

        mini_node = {"n": name}
        for k, v in nut_raw.items():
            key = NUT_MAP.get(k, k) if self.for_llm else k
            val = v.strip().replace(" ", "") if self.for_llm else v.strip()
            mini_node[key] = val

        if not (self.simple or self.for_llm):
            if "ingredients" in details:
                mini_node["ingredients"] = details["ingredients"]
            if "allergens" in details:
                mini_node["allergens"] = details["allergens"]

        return mini_node

    def process_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process raw scraping results into structured, deduplicated JSON."""
        self.logger.info("Processing and minifying data...")

        grouped = {}
        for r in results:
            if r:
                grouped.setdefault(r['meal'], []).append(r)

        final_output = {}
        cal_key = "cal" if self.for_llm else "Calories"

        for meal, courts in grouped.items():
            optimized_courts = {}
            item_sigs = {}
            item_data = {}

            for court in courts:
                loc = court['location']
                optimized_courts[loc] = []

                for station in court['stations']:
                    for raw_item in station['items']:
                        if raw_item['details'].get('is_collection'):
                            nodes = [self._process_node(sub['name'], sub['details'])
                                     for sub in raw_item['details'].get('components', [])]
                        else:
                            nodes = [self._process_node(raw_item['name'], raw_item['details'])]

                        for node in filter(None, nodes):
                            optimized_courts[loc].append(node)
                            sig = f"{node['n']}|{node.get(cal_key, '0')}"
                            item_sigs.setdefault(sig, set()).add(loc)
                            item_data.setdefault(sig, node)

            all_locs = set(optimized_courts.keys())
            common_keys = {sig for sig, locs in item_sigs.items() if locs == all_locs} if len(all_locs) > 1 else set()

            final_output[meal] = {
                "common": sorted([item_data[sig] for sig in common_keys], key=lambda x: x['n']),
                "courts": {
                    loc: sorted([item for item in items
                                 if f"{item['n']}|{item.get(cal_key, '0')}" not in common_keys],
                                key=lambda x: x['n'])
                    for loc, items in optimized_courts.items()
                }
            }

        return final_output

    def generate_statistics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate detailed nutrition statistics."""
        return calculate_statistics(data, for_llm=self.for_llm)

    def run(self, progress_callback=None) -> Dict[str, Any]:
        """Main execution method. Scans, fetches, and returns processed menu data."""
        scouted_data = self.scan_locations()
        if not scouted_data:
            self.logger.error("No open locations found.")
            return {}

        scouted_data.sort(key=lambda x: (x["meal"], x["location"]))
        self.logger.info(f"Starting extraction ({self.threads} threads)...")

        results = []
        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            futures = {executor.submit(self.scrape_worker, data): data for data in scouted_data}

            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                        if progress_callback:
                            progress_callback("done", result)
                except Exception as e:
                    self.logger.error(f"Worker error: {e}")
                    if progress_callback:
                        progress_callback("error", {"message": str(e)})

        return self.process_results(results)
