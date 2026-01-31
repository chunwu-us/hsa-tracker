"""Config utilities."""

import json
from pathlib import Path

CONFIG_DIR = Path(__file__).parent


def load_categories() -> dict:
    """Load category definitions."""
    with open(CONFIG_DIR / 'categories.json') as f:
        return json.load(f)


def get_category_keywords() -> dict[str, list[str]]:
    """Get mapping of category names to keywords."""
    data = load_categories()
    return {cat['name']: cat['keywords'] for cat in data['categories']}
