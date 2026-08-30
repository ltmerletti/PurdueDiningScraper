"""
Nutrition statistics, macro calculations, and ranking utilities.
"""
import statistics
from typing import Dict, List, Any
from .models import NUT_MAP
from .utils import parse_numeric


def calculate_statistics(data: Dict[str, Any], for_llm: bool = False) -> Dict[str, List[Dict[str, Any]]]:
    """
    Calculate detailed nutrition averages and protein density statistics per court and meal.
    """
    k_cal = "cal" if for_llm else "Calories"
    k_prot = "prot" if for_llm else "Protein"
    k_carb = "carb" if for_llm else "Total Carbohydrate"
    k_fat = "fat" if for_llm else "Total fat"
    k_sug = "sug" if for_llm else "Sugar"

    stats_output = {}
    for meal, content in data.items():
        stats_rows = []

        courts_dict = content.get('courts', {})
        for loc, items in courts_dict.items():
            vals = {'cal': [], 'prot': [], 'carb': [], 'fat': [], 'sug': []}

            for item in items:
                c = parse_numeric(item.get(k_cal))
                if c >= 10:  # Exclude negligible items like spices / salt
                    vals['cal'].append(c)
                    vals['prot'].append(parse_numeric(item.get(k_prot)))
                    vals['carb'].append(parse_numeric(item.get(k_carb)))
                    vals['fat'].append(parse_numeric(item.get(k_fat)))
                    vals['sug'].append(parse_numeric(item.get(k_sug)))

            if vals['cal']:
                avg = {k: statistics.mean(v) for k, v in vals.items()}
                stats_rows.append({
                    "location": loc,
                    "averages": avg,
                    "protein_per_100_cal": (avg['prot'] / avg['cal'] * 100) if avg['cal'] > 0 else 0.0
                })

        stats_rows.sort(key=lambda x: x["protein_per_100_cal"], reverse=True)
        stats_output[meal] = stats_rows

    return stats_output
