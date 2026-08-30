# Installation Guide

## Quick Install

If you're in a virtual environment (`.venv`), make sure it's activated:

```bash
source .venv/bin/activate
```

Then install dependencies:

```bash
pip install -r requirements.txt
```

## If You Get Permission Errors

### Option 1: Use the virtual environment's pip directly
```bash
.venv/bin/pip install -r requirements.txt
```

### Option 2: Recreate the virtual environment
```bash
# Remove old venv
rm -rf .venv

# Create new venv
python3 -m venv .venv

# Activate it
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Option 3: Install without virtual environment (not recommended)
```bash
pip3 install --user -r requirements.txt
```

## Verify Installation

After installing, verify the packages are installed:

```bash
python -c "import uvicorn, fastapi, selenium; print('All packages installed!')"
```

## Required Packages

The main packages you need are:
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `selenium` - Web scraping
- `webdriver-manager` - ChromeDriver management
- `pytest` - Testing framework
- `requests` - HTTP client

If installation fails, you can install them one by one:
```bash
pip install fastapi uvicorn selenium webdriver-manager pytest requests tqdm pydantic
```


