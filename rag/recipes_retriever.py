# rag/recipes_retriever.py

from dataclasses import dataclass
from typing import List, Optional, Dict
import pandas as pd
import pathlib


@dataclass
class Recipe:
    city: str
    name: str
    ingredients: str
    preparation: str
    source: str
    course_type: str  # "starter" | "main" | "dessert"


def _load_single_csv(path: pathlib.Path, course_type: str) -> List[Recipe]:
    # very forgiving encoding settings
    df = pd.read_csv(
        path,
        sep=";",
        encoding="latin1",  # handles many Windows encodings
        on_bad_lines="skip",  # skip malformed lines if any (pandas >= 1.3)
    )
    recipes: List[Recipe] = []
    for _, row in df.iterrows():
        recipes.append(
            Recipe(
                city=str(row["city"]),
                name=str(row["name"]),
                ingredients=str(row.get("ingredients", "")),
                preparation=str(row.get("preparation", "")),
                source=str(row.get("source", "")),
                course_type=course_type,
            )
        )
    return recipes


def load_all_recipes() -> List[Recipe]:
    """
    Load appetizers, main courses, and desserts from the recipes folder.
    """
    base_dir = pathlib.Path(__file__).parent.parent / "recipes"

    appetizers_path = base_dir / "appetizers.csv"
    mains_path = base_dir / "main_courses.csv"
    desserts_path = base_dir / "desserts.csv"

    recipes: List[Recipe] = []
    recipes.extend(_load_single_csv(appetizers_path, "starter"))
    recipes.extend(_load_single_csv(mains_path, "main"))
    recipes.extend(_load_single_csv(desserts_path, "dessert"))

    return recipes


def get_menu_for_location(
    location: str, recipes: List[Recipe]
) -> Dict[str, Optional[Recipe]]:
    """
    Very simple 'RAG': filter by city/location substring, then pick one
    starter, one main, one dessert. If nothing matches, fall back to any.
    """
    loc = location.lower().strip()

    def matches(r: Recipe) -> bool:
        return loc in r.city.lower() or loc in r.name.lower()

    filtered = [r for r in recipes if matches(r)]

    # Fallback to all recipes if nothing matched this location
    pool = filtered if filtered else recipes

    def pick(course: str) -> Optional[Recipe]:
        for r in pool:
            if r.course_type == course:
                return r
        return None

    return {
        "starter": pick("starter"),
        "main": pick("main"),
        "dessert": pick("dessert"),
    }
