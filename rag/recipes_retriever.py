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
    try:
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
    except Exception as e:
        print(f"[Warning] Could not load {path}: {e}")
        return []


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

    This is the OLD WORKING function - kept as default.
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


def search_recipe_by_ingredient(
    ingredient: str, recipes: List[Recipe], course_type: str
) -> Optional[Recipe]:
    """
    NEW FUNCTION: Search for a recipe by ingredient name.
    Returns the first recipe that contains the ingredient in its name or ingredients list.
    """
    if not ingredient or not ingredient.strip():
        return None

    ingredient_lower = ingredient.lower().strip()

    # Filter by course type first
    course_recipes = [r for r in recipes if r.course_type == course_type]

    if not course_recipes:
        return None

    # Search in recipe name first (exact or partial match)
    for recipe in course_recipes:
        if ingredient_lower in recipe.name.lower():
            return recipe

    # Search in ingredients list
    for recipe in course_recipes:
        if ingredient_lower in recipe.ingredients.lower():
            return recipe

    # If no match found, return None
    return None


def get_menu_by_ingredients(
    starter_ingredient: str,
    main_ingredient: str,
    dessert_ingredient: str,
    recipes: List[Recipe],
    location: str = "",
) -> Dict[str, Optional[Recipe]]:
    """
    NEW FUNCTION: Get a complete menu based on user-specified ingredients.
    Falls back to location-based menu for any missing items.
    """
    # Search for each course based on ingredient
    starter = (
        search_recipe_by_ingredient(starter_ingredient, recipes, "starter")
        if starter_ingredient
        else None
    )
    main = (
        search_recipe_by_ingredient(main_ingredient, recipes, "main")
        if main_ingredient
        else None
    )
    dessert = (
        search_recipe_by_ingredient(dessert_ingredient, recipes, "dessert")
        if dessert_ingredient
        else None
    )

    # If we couldn't find something, fall back to location-based
    if location and (not starter or not main or not dessert):
        location_menu = get_menu_for_location(location, recipes)
        if not starter:
            starter = location_menu["starter"]
        if not main:
            main = location_menu["main"]
        if not dessert:
            dessert = location_menu["dessert"]

    return {
        "starter": starter,
        "main": main,
        "dessert": dessert,
    }
