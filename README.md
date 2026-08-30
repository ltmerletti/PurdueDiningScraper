# Purdue Dining Menu & Nutrition Assistant

A fast, smart tool for exploring Purdue University dining court menus, checking real nutrition info, and finding meals that fit your diet.

Works as a **Claude/Cursor MCP Server**, an easy-to-use **Command Line Tool (CLI)**, a **FastAPI REST Server**, or a **Python Library**.

---

## Why this exists

If you've ever looked at raw campus dining data, you've probably noticed a few issues:
- **Cafeteria measurements**: Serving sizes often say things like `#60 Disher`, `2OZ LADLE`, or `12 Cut` instead of practical measurements like tablespoons, cups, or slices.
- **Accidental giant batch data**: Sometimes an item (like salad dressing) gets entered as a 5-gallon kitchen batch with 28,000 calories instead of an individual serving.
- **Single-piece confusion**: Dishes like dumplings, potstickers, or chicken nuggets are often logged as 1 single piece, which can make them look misleadingly low in sodium or calories unless you know the piece count.

This project connects directly to Purdue's official dining API, cleans up the confusing measurements, fixes bulk data errors, and makes everything easy to search and understand—both for people and for AI assistants.

---

## What it does

- **Real-Time Menus & Hours**: Check what's open right now across Wiley, Earhart, Ford, Hillenbrand, and Windsor.
- **Sensible Serving Sizes**: Automatically translates kitchen jargon:
  - `#60 Disher` $\to$ `1 Tbsp`
  - `2OZ LADLE` $\to$ `1/4 Cup`
  - `12 Cut` $\to$ `1 Slice`
- **Smart Fixes for Batch Recipes**: Catches crazy numbers (like a tub of sour cream logged with thousands of calories) and scales them down to a normal 1–2 tablespoon portion.
- **Portion & Piece Awareness**: Clearly labels single-piece items (e.g. `1 Piece (1 Each)`) so you don't accidentally think an entire plate of food only has 40 calories.
- **Search by Diet & Macros**: Find entrees using numbers (`min_protein=25`) or everyday words (`min_protein="high"`, `max_sodium="moderate"`, `max_net_carbs="low"`).
- **Interactive Build-Your-Own Stations**: Tracks custom stations like the Mongolian Stir Fry, Taco Bar, Pasta Bar, and Salad Bar.
- **Meal Builder**: Add up multiple items (e.g., 5 potstickers + side of rice + broccoli) to see total calories, protein, carbs, and sodium.

---

## Quick Setup

```bash
git clone https://github.com/ltmerletti/PurdueDiningScraper.git
cd PurdueDiningScraper

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install requirements
pip install -r requirements.txt
pip install -e .
```

---

## How to Use It

### 1. With Claude Desktop or Cursor (MCP)

Connect this tool directly to Claude Desktop or Cursor so your AI assistant can check today's dining courts and suggest meals for you.

Add this to your `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "purdue-dining": {
      "command": "python",
      "args": ["/path/to/PurdueDiningScraper/run_mcp.py"]
    }
  }
}
```

#### Available AI Tools:
| Tool | What it does |
|---|---|
| `get_current_date` | Get today's real-world date, day of week, and formatted date string (recommended to call first). |
| `get_open_locations` | See which dining courts are currently open, meal times, and hours. |
| `get_court_menu` | View the menu for a court, organized by station, with clean portion sizes. |
| `find_dishes` | Search across all courts for dishes matching your protein, calorie, sodium, or dietary goals. |
| `get_custom_stations` | Find today's build-your-own lines (Stir Fry, Taco Bar, Salad Bar, etc.). |
| `get_item_nutrition` | Get detailed ingredients, allergens, macros, and vitamins for a specific dish. |
| `assemble_meal` | Calculate total nutrition when combining multiple items and servings. |

---

### 2. From the Command Line (CLI)

```bash
# Find high-protein entrees (25g+ protein) across all dining courts today
python main.py --find-protein 25

# Search using natural terms
python main.py --find-protein protein-dense --max-sodium moderate --category ENTREE

# Scrape today's lunch and dinner at Wiley
python main.py --location Wiley --meals Lunch Dinner
```

---

### 3. As a Local REST API

Start the web server:
```bash
python run_api.py
```
- API will be live at `http://localhost:8000`
- Interactive docs & playground available at `http://localhost:8000/docs`

---

## Project Structure

```
PurdueDiningScraper/
├── src/purdue_menu/
│   ├── hfs_client.py        # Connects to Purdue's dining API with built-in caching
│   ├── normalizer.py        # Cleans up serving sizes and kitchen measurements
│   ├── food_types.py        # Categorizes foods (entrees, sides, sauces, desserts)
│   ├── descriptors.py       # Converts numbers to helpful tags (e.g. "protein-rich", "low-sodium")
│   ├── models.py            # Data schemas for menus, nutrition, and stations
│   ├── api.py               # FastAPI web server
│   ├── cli.py               # Command line tool
│   └── mcp/                 # FastMCP server for Claude and Cursor
├── tests/                   # Test suite (135+ tests)
├── run_mcp.py               # Entrypoint for MCP server
├── run_api.py               # Entrypoint for FastAPI server
├── main.py                  # Entrypoint for CLI
└── requirements.txt
```

---

## Running Tests

To verify that all parsers, measurement converters, and API tools are working properly:

```bash
pytest
```
