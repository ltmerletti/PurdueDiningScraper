# Purdue Dining Scraper

![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-3776AB?style=flat-square&logo=python&logoColor=white) ![FastAPI](https://img.shields.io/badge/API-FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white) ![MCP](https://img.shields.io/badge/MCP-server-6f42c1?style=flat-square) [![CI](https://github.com/ltmerletti/PurdueDiningScraper/actions/workflows/ci.yml/badge.svg)](https://github.com/ltmerletti/PurdueDiningScraper/actions/workflows/ci.yml)

Purdue Dining Scraper pulls menus and nutrition data from Purdue's official dining API, then cleans up the parts that are hard to use. It can run as an MCP server for Claude or Cursor, a command-line tool, a local REST API, or a Python package.

## Why I made this

The raw dining data has a few problems that make it difficult to search or compare:

- Serving sizes use kitchen measurements such as `#60 Disher`, `2OZ LADLE`, and `12 Cut`.
- Some nutrition records describe an entire kitchen batch instead of one serving. This can make a dressing appear to contain tens of thousands of calories.
- Foods such as dumplings and chicken nuggets may be listed as one piece, which makes the numbers look much lower than a normal plate.
- Build-your-own stations do not fit neatly into the same structure as the rest of the menu.

This project normalizes those records into useful portions, flags single-piece entries, handles likely bulk-recipe mistakes, and keeps build-your-own stations intact.


| Purdue data  | Normalized value               |
| ------------ | ------------------------------ |
| `#60 Disher` | `1 Tbsp (#60 Disher)`          |
| `2OZ LADLE`  | `1/4 Cup (2 oz Ladle)`         |
| `12 Cut`     | `1 Slice (1/12 sheet cut)`     |
| `1 Each`     | Marked as a single-piece entry |




## What you can do with it

- Check dining court menus, stations, and meal periods.
- Search for dishes by protein, calories, sodium, net carbohydrates, fat, category, or dietary needs.
- Look up ingredients, allergens, serving sizes, and nutrition for one item.
- Find build-your-own stations such as stir fry, salad, deli, taco, pizza, and pasta bars.
- Combine several items and servings into one nutrition total.
- Export menu data as regular, simplified, or LLM-friendly JSON.

The nutrition search accepts numbers or plain terms such as `protein-dense`, `moderate`, and `low`.

## Quick start

```bash
git clone https://github.com/ltmerletti/PurdueDiningScraper.git
cd PurdueDiningScraper

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

After installation, `purdue-menu` and `python main.py` run the same CLI.

## Use it with Claude Desktop or Cursor

The MCP server lets an AI assistant query current menus without loading the entire dining dataset into the conversation.

Add the following server to your MCP configuration. Replace `/absolute/path/to/PurdueDiningScraper` with the location of your clone.

```json
{
  "mcpServers": {
    "purdue-dining": {
      "command": "/absolute/path/to/PurdueDiningScraper/.venv/bin/python",
      "args": [
        "/absolute/path/to/PurdueDiningScraper/run_mcp.py"
      ]
    }
  }
}
```

Restart Claude Desktop or Cursor after saving the configuration. You can then ask questions such as:

- "Which dining courts are open for dinner?"
- "Find a high-protein entree under 700 calories."
- "What allergens are listed for the chicken pot pie?"
- "Add up two servings of potstickers, rice, and broccoli."



### MCP tools


| Tool                  | What it does                                                   |
| --------------------- | -------------------------------------------------------------- |
| `get_current_date`    | Returns the current date and day of the week                   |
| `get_open_locations`  | Lists dining locations, meal periods, and hours                |
| `get_court_menu`      | Gets a court menu organized by meal and station                |
| `find_dishes`         | Searches across courts using nutrition and dietary filters     |
| `get_custom_stations` | Finds build-your-own stations                                  |
| `get_item_nutrition`  | Returns nutrition, ingredients, allergens, and portion details |
| `assemble_meal`       | Adds several items and serving counts into one total           |


You can also start the MCP server directly:

```bash
python run_mcp.py
```



## Use the command line

Search today's menus for entrees with at least 25 grams of protein:

```bash
purdue-menu --find-protein 25
```

Use plain-language nutrition filters:

```bash
purdue-menu \
  --find-protein protein-dense \
  --max-sodium moderate \
  --category ENTREE
```

Search one dining court or a different date:

```bash
purdue-menu --find-protein 25 --location Wiley --date 2026-09-09
```

To fetch menus and save them as JSON, start the local API first:

```bash
python run_api.py
purdue-menu --location Wiley --meals Lunch Dinner
```

You can skip the separate API process by using the in-process runner:

```bash
purdue-menu --use-local --location Wiley --meals Lunch Dinner
```

Useful output options include:

```bash
# Leave out ingredients and allergens
purdue-menu --use-local --location Wiley --simple

# Use shorter JSON keys to reduce LLM context size
purdue-menu --use-local --location Wiley --for-llm

# Include nutrition rankings in the output
purdue-menu --use-local --location Wiley --statistics
```



## Run the REST API

```bash
python run_api.py
```

The API listens on `http://localhost:8000`. FastAPI's interactive documentation is available at `http://localhost:8000/docs`.

Main endpoints:


| Method   | Path                    | Purpose                     |
| -------- | ----------------------- | --------------------------- |
| `GET`    | `/health`               | Check server health         |
| `POST`   | `/api/menus`            | Fetch and normalize menus   |
| `GET`    | `/api/menus/statistics` | Return nutrition statistics |
| `GET`    | `/api/cache/info`       | Inspect the local cache     |
| `DELETE` | `/api/cache`            | Clear the local cache       |




## How it works

The primary data path uses Purdue's HFS menu API. Location data is cached for six hours, menu data for four hours, and item details for the life of the process. Selenium remains available as a fallback for the older scraper path.

Menu items pass through three main steps:

1. Fetch the court menu and item details from Purdue.
2. Normalize serving sizes and likely bulk-recipe errors.
3. Categorize dishes and add nutrition descriptions used by search filters.



## Project layout

```text
PurdueDiningScraper/
├── src/purdue_menu/
│   ├── hfs_client.py      Purdue HFS API client and cache
│   ├── normalizer.py      Serving-size and bulk-recipe cleanup
│   ├── food_types.py      Food and station categorization
│   ├── descriptors.py     Nutrition labels and search filters
│   ├── models.py          Menu and nutrition models
│   ├── api.py             FastAPI application
│   ├── cli.py             Command-line interface
│   └── mcp/               MCP server and tools
├── tests/                 Test suite
├── main.py                CLI entry point
├── run_api.py             REST API entry point
└── run_mcp.py             MCP entry point
```



## Run the tests

```bash
pytest
```

The suite currently contains 137 tests covering the API, MCP tools, normalization rules, food categories, output helpers, and scraper behavior.

GitHub Actions runs the suite with network access blocked on Python 3.11 and 3.13 for pushes to main and pull requests. A separate weekly workflow checks the public Purdue HFS API. Monthly Dependabot PRs update Python dependencies and GitHub Actions. See [TESTING.md](TESTING.md) for local CI commands and dependency updates.

