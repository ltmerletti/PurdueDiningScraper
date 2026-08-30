"""
Density-aware semantic descriptors and flexible filter mappers.
Translates nutritional numbers into intuitive qualitative descriptors and maps
natural language user queries (e.g., 'protein-rich', 'sod:moderate') into numerical bounds.
"""
from typing import List, Optional, Union, Dict, Any
from .models import NutritionData
from .food_types import FoodCategory


def generate_protein_descriptor(protein_g: Optional[float]) -> Optional[str]:
    """Generate protein density descriptor."""
    if protein_g is None:
        return None
    if protein_g >= 40:
        return "p:very-high-protein"
    elif protein_g >= 30:
        return "p:protein-dense"
    elif protein_g >= 20:
        return "p:protein-rich"
    elif protein_g >= 10:
        return "p:moderate"
    elif protein_g >= 5:
        return "p:modest"
    else:
        return "p:light"


def generate_sodium_descriptor(
    sodium_mg: Optional[float],
    category: FoodCategory = FoodCategory.ENTREE
) -> Optional[str]:
    """
    Generate sodium descriptor.
    Calibrated so small servings of sauces/condiments are not tagged as dangerous high-sodium meals.
    """
    if sodium_mg is None:
        return None

    if sodium_mg < 10:
        return "sod:none"
    elif sodium_mg <= 140:
        return "sod:light"  # FDA Low Sodium
    elif sodium_mg <= 300:
        return "sod:modest"
    elif sodium_mg <= 600:
        return "sod:moderate"
    elif sodium_mg <= 900:
        return "sod:concentrated"
    elif sodium_mg <= 1400:
        return "sod:sodium-dense"
    else:
        return "sod:heavy-sodium"


def generate_sugar_descriptor(sugar_g: Optional[float]) -> Optional[str]:
    """Generate sugar descriptor."""
    if sugar_g is None:
        return None
    if sugar_g < 0.5:
        return "sug:zero"
    elif sugar_g < 3.0:
        return "sug:light"
    elif sugar_g < 6.0:
        return "sug:modest"
    elif sugar_g < 10.0:
        return "sug:moderate"
    elif sugar_g < 15.0:
        return "sug:sweet"
    elif sugar_g < 25.0:
        return "sug:sugar-rich"
    else:
        return "sug:very-sweet"


def generate_fiber_descriptor(fiber_g: Optional[float]) -> Optional[str]:
    """Generate fiber descriptor."""
    if fiber_g is None:
        return None
    if fiber_g < 0.5:
        return "fib:none"
    elif fiber_g < 2.0:
        return "fib:light"
    elif fiber_g < 4.0:
        return "fib:modest"
    elif fiber_g < 6.0:
        return "fib:good-source"  # FDA Good Source
    else:
        return "fib:fiber-rich"   # FDA Excellent Source


def generate_fat_descriptor(fat_g: Optional[float]) -> Optional[str]:
    """Generate total fat descriptor."""
    if fat_g is None:
        return None
    if fat_g < 4.0:
        return "fat:light"
    elif fat_g <= 15.0:
        return "fat:moderate"
    elif fat_g <= 25.0:
        return "fat:rich"
    else:
        return "fat:dense"


def generate_saturated_fat_descriptor(sat_fat_g: Optional[float]) -> Optional[str]:
    """Generate saturated fat descriptor."""
    if sat_fat_g is None:
        return None
    if sat_fat_g <= 0.0:
        return "sat:none"
    elif sat_fat_g <= 1.5:
        return "sat:light"
    elif sat_fat_g <= 3.5:
        return "sat:modest"
    elif sat_fat_g <= 6.0:
        return "sat:moderate"
    else:
        return "sat:dense"


def generate_net_carb_descriptor(net_carbs_g: Optional[float]) -> Optional[str]:
    """Generate net carb descriptor."""
    if net_carbs_g is None:
        return None
    if net_carbs_g < 5.0:
        return "netcarb:very-low"
    elif net_carbs_g < 15.0:
        return "netcarb:low"
    elif net_carbs_g < 35.0:
        return "netcarb:moderate"
    elif net_carbs_g <= 55.0:
        return "netcarb:carb-rich"
    else:
        return "netcarb:high-carb"


def generate_all_descriptors(
    nutrition: Optional[NutritionData],
    category: FoodCategory = FoodCategory.ENTREE
) -> List[str]:
    """
    Generate a complete list of qualitative semantic descriptors for an item.
    """
    if not nutrition:
        return []

    descriptors = []

    # Tag single-piece items clearly so LLMs and users evaluate portions
    if nutrition.is_single_piece_entry:
        descriptors.append("portion:single-piece")

    p = generate_protein_descriptor(nutrition.protein_g)
    if p:
        descriptors.append(p)

    sod = generate_sodium_descriptor(nutrition.sodium_mg, category)
    if sod:
        descriptors.append(sod)

    sug = generate_sugar_descriptor(nutrition.sugar_g)
    if sug:
        descriptors.append(sug)

    fib = generate_fiber_descriptor(nutrition.fiber_g)
    if fib:
        descriptors.append(fib)

    fat = generate_fat_descriptor(nutrition.fat_g)
    if fat:
        descriptors.append(fat)

    sat = generate_saturated_fat_descriptor(nutrition.saturated_fat_g)
    if sat:
        descriptors.append(sat)

    net_carbs = nutrition.net_carbohydrates_g
    if net_carbs is None and nutrition.carbohydrates_g is not None:
        net_carbs = max(0.0, nutrition.carbohydrates_g - (nutrition.fiber_g or 0.0))
    nc = generate_net_carb_descriptor(net_carbs)
    if nc:
        descriptors.append(nc)

    return descriptors


# Mapping tables for resolving qualitative search filters to numerical thresholds
PROTEIN_MAP = {
    "light": 1.0,
    "p:light": 1.0,
    "modest": 5.0,
    "p:modest": 5.0,
    "moderate": 10.0,
    "p:moderate": 10.0,
    "protein-rich": 20.0,
    "rich": 20.0,
    "p:protein-rich": 20.0,
    "protein-dense": 30.0,
    "dense": 30.0,
    "p:protein-dense": 30.0,
    "very-high-protein": 40.0,
    "p:very-high-protein": 40.0,
}

SODIUM_MAP = {
    "none": 10.0,
    "sod:none": 10.0,
    "light": 140.0,
    "sod:light": 140.0,
    "modest": 300.0,
    "sod:modest": 300.0,
    "moderate": 600.0,
    "sod:moderate": 600.0,
    "concentrated": 900.0,
    "sod:concentrated": 900.0,
    "sodium-dense": 1400.0,
    "sod:sodium-dense": 1400.0,
}

NET_CARBS_MAP = {
    "very-low": 5.0,
    "netcarb:very-low": 5.0,
    "low": 15.0,
    "netcarb:low": 15.0,
    "moderate": 35.0,
    "netcarb:moderate": 35.0,
    "carb-rich": 55.0,
    "netcarb:carb-rich": 55.0,
}


def parse_protein_filter(val: Optional[Union[str, float, int]]) -> Optional[float]:
    """Convert min_protein input (number or string descriptor) to numerical float threshold."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    val_str = str(val).lower().strip()
    return PROTEIN_MAP.get(val_str, float(val_str) if val_str.replace('.', '', 1).isdigit() else None)


def parse_sodium_filter(val: Optional[Union[str, float, int]]) -> Optional[float]:
    """Convert max_sodium input (number or string descriptor) to numerical max threshold."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    val_str = str(val).lower().strip()
    return SODIUM_MAP.get(val_str, float(val_str) if val_str.replace('.', '', 1).isdigit() else None)


def parse_net_carbs_filter(val: Optional[Union[str, float, int]]) -> Optional[float]:
    """Convert max_net_carbs input (number or string descriptor) to numerical max threshold."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    val_str = str(val).lower().strip()
    return NET_CARBS_MAP.get(val_str, float(val_str) if val_str.replace('.', '', 1).isdigit() else None)
