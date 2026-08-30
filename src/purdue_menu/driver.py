"""
Selenium WebDriver manager and Chrome/Chromium configuration.
Provides isolated driver creation, lifecycle handling, and cross-platform fallbacks.
"""
import os
import sys
import shutil
import logging
from typing import Optional

logger = logging.getLogger("PurdueDriver")


def build_chrome_options(visible: bool = False, headless: bool = True):
    """Build Chrome options with performance optimizations."""
    from selenium.webdriver.chrome.options import Options

    options = Options()
    if not visible or headless:
        options.add_argument("--headless")

    # Core stability options
    for arg in ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--log-level=3"]:
        options.add_argument(arg)

    # Performance options: disable images, plugins, background networking
    for arg in [
        "--disable-images",
        "--disable-plugins",
        "--disable-extensions",
        "--disable-background-networking",
        "--disable-background-timer-throttling"
    ]:
        options.add_argument(arg)

    options.add_argument(
        "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    )

    # Detect Chrome / Chromium binary location
    chrome_paths = {
        "darwin": [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium"
        ],
        "linux": [
            "/usr/bin/google-chrome",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser"
        ]
    }
    platform = "darwin" if sys.platform == "darwin" else "linux"
    for path in chrome_paths.get(platform, []):
        if os.path.exists(path):
            options.binary_location = path
            break

    return options


def create_driver(visible: bool = False, timeout: int = 30):
    """Create a new Chrome WebDriver instance."""
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager

    options = build_chrome_options(visible=visible)
    binary_path = options.binary_location or ""
    is_chromium = (
        "chromium" in binary_path.lower() if binary_path else False
    ) or os.path.exists("/usr/bin/chromium")

    service = None
    if is_chromium:
        chromedriver_paths = [
            "/usr/bin/chromedriver",
            "/usr/lib/chromium/chromedriver",
            "/usr/lib/chromium-browser/chromedriver"
        ]
        for path in chromedriver_paths:
            if os.path.exists(path):
                logger.info(f"Using system chromedriver at {path}")
                service = Service(path)
                break

        if service is None:
            chromedriver_which = shutil.which("chromedriver")
            if chromedriver_which:
                logger.info(f"Found chromedriver via which: {chromedriver_which}")
                service = Service(chromedriver_which)
            else:
                logger.warning("System chromedriver not found, falling back to webdriver-manager")
                service = Service(ChromeDriverManager().install())
    else:
        service = Service(ChromeDriverManager().install())

    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(timeout)
    return driver
