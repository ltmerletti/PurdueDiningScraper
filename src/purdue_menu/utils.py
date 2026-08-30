"""
Formatting, parsing, and data export utilities.
"""
import re
import json
from typing import Dict, Any, Optional


def parse_numeric(value_str: Optional[str]) -> float:
    """Extract float from strings like '14g', '1,200mg', '<1 g'."""
    if not value_str or not isinstance(value_str, str):
        return 0.0
    match = re.search(r"(\d+\.?\d*)", value_str.replace(',', ''))
    return float(match.group(1)) if match else 0.0


def format_statistics(stats_data: Dict[str, Any], for_llm: bool = False) -> str:
    """Format statistics as a readable string for terminal or logs."""
    if not stats_data:
        return ""

    lines = [
        "\n" + "=" * 60,
        " NUTRITION STATISTICS (Unique Items Only)",
        " Average values per item (excluding <10-cal items)",
        "=" * 60
    ]

    for meal, stats_rows in stats_data.items():
        lines.append(f"\n>>> {meal.upper()} SUMMARY <<<")
        if not stats_rows:
            lines.append("No data available")
            continue

        # Table Header
        lines.append(f"{'Location':<20} | {'Cal':<5} | {'Prot':<5} | {'Carb':<5} | {'Fat':<5} | {'Sug':<5} | {'Prot/100k'}")
        lines.append("-" * 75)

        for row in stats_rows:
            loc = row.get("location", "")
            avg = row.get("averages", {})
            pd = row.get("protein_per_100_cal", 0.0)
            lines.append(
                f"{loc:<20} | {avg.get('cal', 0):<5.0f} | {avg.get('prot', 0):<5.1f} | "
                f"{avg.get('carb', 0):<5.1f} | {avg.get('fat', 0):<5.1f} | {avg.get('sug', 0):<5.1f} | {pd:<5.1f}"
            )
        lines.append("-" * 75)

    return "\n".join(lines)


def save_menu_data(data: Dict[str, Any], output_file: str, for_llm: bool = False) -> None:
    """Save menu data to a JSON file."""
    with open(output_file, "w", encoding="utf-8") as f:
        indent = None if for_llm else 4
        seps = (',', ':') if for_llm else (', ', ': ')
        json.dump(data, f, indent=indent, separators=seps)
