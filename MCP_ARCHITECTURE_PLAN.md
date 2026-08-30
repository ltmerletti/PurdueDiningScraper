# Purdue Dining MCP Architecture & Nutrition Intelligence Plan

This document outlines the architecture, data models, serving size normalization algorithms, semantic descriptor systems, and tool specifications for the **Purdue Dining Scraper & Model Context Protocol (MCP) Server**.

---

## 1. Executive Summary & Goals

### The Problem
1. **Scraping Inefficiency**: Selenium-based web crawling across 5+ dining courts and 3 meals is slow (~4+ minutes), brittle to DOM changes, and heavy on system resources.
2. **Serving Size & Data Logging Anomaly**: Institutional recipe databases often log items with erratic serving sizes (e.g., sauces logged as 5-gallon batches, disher numbers like `#60 Disher`, or bulk institutional pans), making direct nutritional comparison unreliable.
3. **Category Conflation**: Without role categorization, a 400-calorie sauce or dressing cannot be distinguished from a 400-calorie entree, distorting macro density and meal planning.
4. **Context Window Exhaustion**: A full daily menu dump across all courts contains thousands of items and lines of JSON, blowing out LLM context windows if returned as raw dumps.
5. **LLM Misinterpretation of Nutrition**: Weak or smaller LLMs struggle with absolute numerical ratings or rigid numeric tier numbers (e.g., classifying a high-sodium sauce as dangerous despite a tiny 2 Tbsp serving size).

### The Solution
- **Direct HFS REST API Integration**: Primary high-speed ingestion via `https://api.hfs.purdue.edu/menus/v2/` (< 1.5s full refresh, in-memory TTL caching) with Selenium retained as a fallback.
- **Rule-Based & Heuristic Normalization**: Automatic conversion of kitchen measurements (dishers, ladles, cups, cuts) and anomaly rescaling for bulk sauce/dressing entries.
- **Food Role & Station Categorization**: Explicit categorization into `ENTREE`, `SIDE`, `SAUCE_DRESSING`, `TOPPING_CONDIMENT`, `BREAD_BAKERY`, `DESSERT_SNACK`, `BEVERAGE`, and `CUSTOM_STATION` (Salad Bar, Stir Fry, Deli, etc.).
- **Dual-Track Nutritional Representation**:
  1. **Raw Numbers + Explicit Servings** for accurate mathematical meal composition and calorie tracking.
  2. **Density-Aware Semantic Descriptors** (`protein-dense`, `sod:concentrated-sauce`, `sug:light`, `fib:rich`) for natural language searching and model reasoning.
- **Granular, Token-Efficient FastMCP Server**: Modular tools enabling focused queries for menus, dietary filters, custom stations, and meal assembly.

---

## 2. Purdue HFS API Endpoints & Discovery

The official dining platform is powered by an unauthenticated REST API at `https://api.hfs.purdue.edu/menus/v2/`.

### Core Endpoints

| Endpoint | Method | Description | Response Content |
| :--- | :---: | :--- | :--- |
| `/locations` | `GET` | List all dining locations and operating hours | Location IDs, names, meal periods, open/close timestamps |
| `/locations/{court}/{YYYY-MM-DD}` | `GET` | Full daily menu for a specific dining court | Meals, stations, item names, item IDs, dietary flags (Vegetarian, Vegan) |
| `/items/{item_id}` | `GET` | Precise nutritional facts, ingredients, & allergens | Exact unrounded floats for all macros/micros, serving size string, % DV, ingredients text, allergen array |

### API Nutrition Schema (`/items/{item_id}`)
The item endpoint provides exhaustive, unrounded nutrient data:
- `Calories` (kcal)
- `ServingSize` (string, e.g., `"1/2 Cup"`, `"1 Each"`, `"2OZ LADLE"`, `"#60 Disher"`)
- `Protein` (grams)
- `TotalFat` & `SaturatedFat` (grams)
- `TransFat` & `Cholesterol` (grams / mg)
- `Sodium` (mg)
- `TotalCarbohydrate`, `DietaryFiber`, `Sugar`, & `AddedSugar` (grams)
- `Calcium`, `Iron`, `Potassium` (% DV and mg)
- `Ingredients` (full text list)
- `Allergens` (structured list of allergen flags)

---

## 3. Serving Size Normalization & Anomaly Handling

### 3.1 Kitchen Measurement Parsing

Purdue's menus frequently use institutional kitchen equipment terminology:

| Raw Kitchen String | Resolved Unit | Standard Reference Volume / Weight |
| :--- | :--- | :--- |
| `#60 Disher` | Disher scoop | 0.53 fl oz (~1.06 Tbsp / 15.7 ml) |
| `#30 Disher` | Disher scoop | 1.07 fl oz (~2.1 Tbsp / 31.5 ml) |
| `#16 Disher` | Disher scoop | 2.0 fl oz (~1/4 Cup / 59 ml) |
| `#8 Disher` | Disher scoop | 4.0 fl oz (~1/2 Cup / 118 ml) |
| `1OZ LADLE` | Ladle | 1.0 fl oz (2 Tbsp / 30 ml) |
| `2OZ LADLE` | Ladle | 2.0 fl oz (1/4 Cup / 60 ml) |
| `1/2 Cup`, `1 Cup` | Volume | 4 fl oz / 8 fl oz |
| `12 Cut` | Sheet pan cut | 1/12th of full sheet pan (standard portion) |
| `24 Cut`, `48 Cut` | Sheet pan cut | 1/24th or 1/48th portion |
| `1 Each`, `1 Slice`, `1 Patty` | Discrete count | 1 standard piece |

### 3.2 Bulk Anomaly Rescaling

Occasionally, an item is entered into the food database as a preparation batch rather than a customer portion:
- **Condition**: An item categorized as `SAUCE_DRESSING` or `TOPPING_CONDIMENT` with `Calories > 800` or `ServingSize` containing `"Gallon"`, `"Batch"`, `"Quart"`, `"1000 oz"`, or `Weight > 500g`.
- **Normalization Action**:
  1. Flag item as `rescaled_from_bulk = True`.
  2. Compute scaling factor to bring portion down to standard reference size:
     - Salad Dressing: **2 Tbsp (30 ml / 30g)**
     - Condiments / Dips: **1 Tbsp (15 ml / 15g)**
     - Cooking / Toss Sauces: **2 fl oz (60 ml / 60g)**
  3. Divide all nutrient metrics by the scaling factor.
  4. Set `normalized_serving_size = "2 Tbsp (normalized from batch)"`.

---

## 4. Food Categorization & Station Modeling

### 4.1 Food Role Taxonomy

Items are categorized to prevent false equivalencies in search and planning:

```
FoodCategory
├── ENTREE             # Primary mains: grilled meats, pasta dishes, casseroles, sandwiches, stir-fry proteins
├── SIDE               # Vegetables, grains, fries, mashed potatoes, beans, side salads
├── SAUCE_DRESSING     # Gravies, salad dressings, stir-fry sauces, syrups, salsas
├── TOPPING_CONDIMENT  # Cheeses, croutons, pickles, sour cream, mayo packets, butter
├── BREAD_BAKERY       # Rolls, garlic bread, sandwich buns, bagels, toast
├── DESSERT_SNACK      # Cookies, cakes, brownies, puddings, ice cream, chips
├── BEVERAGE           # Juices, milk, coffee, soda, tea
└── CUSTOM_STATION     # Self-service modular assembly bars (Salad Bar, Deli, etc.)
```

### 4.2 Interactive / Build-Your-Own (MYO) Stations

Purdue dining courts feature interactive stations that return `HTTP 500` on single-item API lookup because they are composed of modular ingredients.

These are explicitly represented as `CustomStation` models:
- **`STIR_FRY`**: Earhart / Wiley interactive stir-fry lines (proteins, vegetables, noodles/rice, sauces).
- **`SALAD_BAR`**: Present across most courts (greens, toppings, dressings, legumes, cheeses).
- **`DELI`**: Made-to-order sandwiches (sliced meats, cheeses, breads, spreads).
- **`PIZZA_BAR`**: Custom pizza/flatbread assembly (Wiley, Hillenbrand).
- **`TACO_BAR`**: Tortillas, seasoned beef/chicken, beans, salsa, guacamole.
- **`PASTA_BAR`**: Custom pasta, sauces (marinara, alfredo), and toppings.

**Behavior in MCP**:
- Instead of returning a single broken item, the tool reports the station as **`OPEN`** with its available component lists and baseline guidance.

---

## 5. Density-Aware Semantic Descriptors

To allow natural LLM query filtering without misleading smaller models with blunt numerical tiers, we implement **role-aware qualitative descriptors**.

### 5.1 Calibrated Scales

#### Protein (`p:*`)
- `p:light` (1–4g)
- `p:modest` (5–9g)
- `p:moderate` (10–19g)
- `p:protein-rich` (20–29g)
- `p:protein-dense` (30–39g)
- `p:very-high-protein` (40g+)

#### Sodium (`sod:*`)
*Calibrated so a concentrated sauce in a small 2 Tbsp serving is not tagged as a hazardous high-sodium meal.*
- `sod:none` (< 10mg)
- `sod:light` (10–140mg) — *FDA Low Sodium guideline*
- `sod:modest` (141–300mg)
- `sod:moderate` (301–600mg) — *Standard balanced single-serving level*
- `sod:concentrated` (601–900mg) — *Seasoned sauce or standard hearty entree*
- `sod:sodium-dense` (901–1400mg)
- `sod:heavy-sodium` (> 1400mg)

#### Sugar & Added Sugar (`sug:*` / `addsug:*`)
- `sug:zero` (< 0.5g)
- `sug:light` (0.5–2.9g)
- `sug:modest` (3.0–5.9g)
- `sug:moderate` (6.0–9.9g)
- `sug:sweet` (10.0–14.9g)
- `sug:sugar-rich` (15.0–24.9g)
- `sug:very-sweet` (25g+)

#### Dietary Fiber (`fib:*`)
- `fib:none` (< 0.5g)
- `fib:light` (0.5–1.9g)
- `fib:modest` (2.0–3.9g)
- `fib:good-source` (4.0–5.9g) — *FDA Good Source*
- `fib:fiber-rich` (6.0g+) — *FDA Excellent Source*

#### Fat & Saturated Fat (`fat:*` / `sat:*`)
- `fat:light` (< 4g), `fat:moderate` (4–15g), `fat:rich` (16–25g), `fat:dense` (> 25g)
- `sat:none` (0g), `sat:light` (0.5–1.5g), `sat:modest` (1.6–3.5g), `sat:moderate` (3.6–6.0g), `sat:dense` (> 6.0g)

#### Net Carbs (`netcarb:*`)
- `netcarb:very-low` (< 5g)
- `netcarb:low` (5–14g)
- `netcarb:moderate` (15–34g)
- `netcarb:carb-rich` (35–55g)
- `netcarb:high-carb` (> 55g)

---

## 6. MCP Server Tools Specification

The MCP server is implemented using `FastMCP` (via official Python MCP SDK).

```
MCP Server: purdue-dining
├── Tool 1: get_open_locations(date?)
├── Tool 2: get_court_menu(location, meal?, date?, category?, include_nutrition=False)
├── Tool 3: find_dishes(min_protein?, max_calories?, max_sodium?, max_net_carbs?, category?, court?, meal?)
├── Tool 4: get_custom_stations(court?, meal?, date?)
├── Tool 5: get_item_nutrition(item_id or name)
└── Tool 6: assemble_meal(items: list[{item_id/name, servings}])
```

### Detailed Tool Signatures

#### 1. `get_open_locations`
- **Purpose**: Fast check of which dining courts are open, their hours, and available meal periods.
- **Input**: `date` (str, optional, defaults to today `YYYY-MM-DD`).
- **Output**: Lightweight list of open courts, meal periods (Breakfast, Lunch, Late Lunch, Dinner), and operating hours.

#### 2. `get_court_menu`
- **Purpose**: Get the menu for a dining court, organized by station.
- **Input**:
  - `location` (str, e.g., `"Wiley"`, `"Earhart"`, `"Windsor"`).
  - `meal` (str, optional: `"Breakfast"`, `"Lunch"`, `"Dinner"`).
  - `date` (str, optional).
  - `category` (str, optional: `"ENTREE"`, `"SIDE"`, etc.).
  - `include_nutrition` (bool, default `False` — keeps context light by returning names + descriptors unless detailed numbers are requested).
- **Output**: Clean station list with dish names, food categories, and semantic tags.

#### 3. `find_dishes`
- **Purpose**: Nutritional search across all open courts without loading full menus.
- **Input**:
  - `min_protein` (str or float, e.g., `"protein-rich"`, `"protein-dense"`, or `25`).
  - `max_calories` (float, optional).
  - `max_sodium` (str or float, e.g., `"moderate"`, `"concentrated"`, or `600`).
  - `max_net_carbs` (str or float, e.g., `"low"`, `"moderate"`, or `15`).
  - `max_fat` (str or float, optional).
  - `category` (str, default `"ENTREE"`).
  - `dietary` (str, optional: `"Vegetarian"`, `"Vegan"`, `"Gluten-Free"`).
  - `meal` (str, optional).
- **Output**: Ranked list of matching dishes, the court/station serving them, serving size, exact macros, and descriptors.

#### 4. `get_custom_stations`
- **Purpose**: Query interactive build-your-own stations (Stir Fry, Salad Bar, Deli, Taco Bar).
- **Input**: `court` (optional), `meal` (optional), `date` (optional).
- **Output**: List of active custom stations, locations, and available component categories.

#### 5. `get_item_nutrition`
- **Purpose**: Deep-dive into a single item's ingredients, allergens, and micronutrients.
- **Input**: `item_id` (str) or `item_name` (str with optional `court`).
- **Output**: Complete unrounded nutrition table, serving size, allergen warnings, and full ingredients list.

#### 6. `assemble_meal`
- **Purpose**: Calculate exact aggregate nutritional totals for a combination meal (e.g. 1 entree + 1 side + 1 sauce).
- **Input**:
  - `items`: List of objects `[{"name": "Grilled Chicken", "servings": 1.5}, {"name": "Szechuan Sauce", "servings": 1}]`.
- **Output**: Combined total calories, protein, carbs, net carbs, fat, saturated fat, sodium, fiber, sugar, and aggregate semantic evaluation.

---

## 7. Target File & Package Structure

```
PurdueDiningScraper/
├── src/
│   └── purdue_menu/
│       ├── __init__.py          # Package root exports
│       ├── models.py            # Pydantic schemas (Nutrition, Item, Station, Menu, Descriptors)
│       ├── food_types.py        # FoodCategory & CustomStation categorization heuristics
│       ├── normalizer.py        # Serving size string parser, unit converter, bulk anomaly scaler
│       ├── descriptors.py       # Density-aware semantic descriptor generators & filter mappers
│       ├── hfs_client.py        # Async & sync client for api.hfs.purdue.edu with TTL cache
│       ├── scraper.py           # Selenium fallback scraper (retained for resilience)
│       ├── stats.py             # Macro stats, high-protein rankings, court comparisons
│       ├── driver.py            # Webdriver management for Selenium fallback
│       ├── utils.py             # String parsers, formatting, terminal tables
│       ├── api.py               # FastAPI REST API endpoints
│       ├── cli.py               # CLI tool with --date, --location, --high-protein, --mcp flags
│       └── mcp/
│           ├── __init__.py
│           ├── server.py        # FastMCP server definition & lifespan
│           └── tools.py         # MCP tool handlers
├── tests/
│   ├── conftest.py
│   ├── test_hfs_client.py      # Tests for HFS API client & caching
│   ├── test_normalizer.py      # Tests for serving sizes & anomaly rescaling
│   ├── test_descriptors.py     # Tests for semantic word descriptors & search filters
│   ├── test_mcp_tools.py       # Tests for MCP tool responses
│   └── test_scraper.py         # Tests for fallback Selenium scraper
├── main.py                      # CLI entrypoint
├── run_api.py                   # FastAPI server entrypoint
├── run_mcp.py                   # FastMCP server entrypoint
├── setup.py                     # Package setup
└── requirements.txt             # Dependencies (httpx, pydantic, mcp/fastmcp, fastapi, uvicorn, etc.)
```

---

## 8. Step-by-Step Implementation Strategy

1. **Step 1: Core Models & Categorization (`food_types.py`, `models.py`)**
   - Implement `FoodCategory` and `CustomStationType` enums.
   - Define Pydantic models for `NutritionData`, `NormalizedItem`, `CustomStation`, and `CourtMenu`.

2. **Step 2: Normalizer & Anomaly Rescaling (`normalizer.py`)**
   - Regex parser for `#XX Disher`, `X OZ LADLE`, `Cup`, `Cut`, `Slice`, `Each`.
   - Heuristics to catch institutional batch entries (e.g. 5-gallon sauces) and rescale them to standard reference amounts (2 Tbsp).

3. **Step 3: Semantic Word Descriptors (`descriptors.py`)**
   - Implement density-calibrated qualitative word tags (`protein-dense`, `sod:concentrated`, `sug:light`, etc.).
   - Implement query filter translator mapping natural terms (`"protein-rich"`) to numerical criteria.

4. **Step 4: Purdue HFS API Client (`hfs_client.py`)**
   - High-speed async/sync HTTP client using `httpx`.
   - In-memory 12-hour TTL cache for menus and permanent cache for item IDs.
   - Automatic identification and routing of `CUSTOM_STATION` entries.

5. **Step 5: MCP Server Implementation (`src/purdue_menu/mcp/`)**
   - Implement the 6 MCP tools via `FastMCP`.
   - Support stdio transport (compatible with Claude Desktop, Claude Code, Cursor, and LM Studio).

6. **Step 6: CLI & Entrypoints (`cli.py`, `run_mcp.py`)**
   - Provide direct CLI testing: `python main.py --find-protein 30 --meal Lunch`.
   - Provide MCP runner: `python run_mcp.py`.

7. **Step 7: Test Suite & Verification (`tests/`)**
   - Complete unit test suite verifying normalization, descriptors, API mock parsing, and MCP tool executions.
