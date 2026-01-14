# main.py
from llm_pipeline.case_generator import generate_case
from llm_pipeline.character_generator import generate_characters
from llm_pipeline.last_day_victim import generate_last_day
from llm_pipeline.clue_generator import generate_clues
from llm_pipeline.solution_generator import generate_solution
from rag.retriever import RagRetriever

# from image_tool.image_generator import generate_character_image
from rag.recipes_retriever import (
    load_all_recipes,
    get_menu_for_location,
    get_menu_by_ingredients,
)

NUM_CHARACTERS = 7


def main():
    # 0. Ask for location of the murder mystery
    location = input(
        "Where should the murder mystery take place? (e.g. Kiel, Hamburg, Lübeck): "
    ).strip()
    if not location:
        location = "Hamburg"

    # 0b. Load all recipes
    all_recipes = load_all_recipes()

    # NEW: Ask user for ingredient preferences
    print("\n=== CUSTOMIZE YOUR DINNER MENU ===")
    print("Enter ingredients you'd like in each course:")

    starter_ingredient = input(
        "What kind of appetizers do you want? (e.g., fish, salad, soup): "
    ).strip()
    main_ingredient = input(
        "What kind of main course do you want? (e.g., beef, potatoes, chicken): "
    ).strip()
    dessert_ingredient = input(
        "What kind of dessert do you want? (e.g., franzbroetchen, cake, pudding): "
    ).strip()

    # Get menu based on ingredients
    if starter_ingredient or main_ingredient or dessert_ingredient:
        print("\n=== SEARCHING FOR RECIPES WITH YOUR INGREDIENTS ===")
        menu = get_menu_by_ingredients(
            starter_ingredient if starter_ingredient else "",
            main_ingredient if main_ingredient else "",
            dessert_ingredient if dessert_ingredient else "",
            all_recipes,
        )

        # Fallback to location-based if no matches found
        if not menu["starter"] and not menu["main"] and not menu["dessert"]:
            print(
                f"No recipes found with those ingredients. Using {location}-based menu instead."
            )
            menu = get_menu_for_location(location, all_recipes)
    else:
        # Use location-based menu if no ingredients specified
        menu = get_menu_for_location(location, all_recipes)

    print("\n=== DINNER MENU FOR THIS MYSTERY ===")
    if menu["starter"]:
        print(f"Starter: {menu['starter'].name} ({menu['starter'].city})")
    else:
        print("Starter: none found")
    if menu["main"]:
        print(f"Main course: {menu['main'].name} ({menu['main'].city})")
    else:
        print("Main course: none found")
    if menu["dessert"]:
        print(f"Dessert: {menu['dessert'].name} ({menu['dessert'].city})")
    else:
        print("Dessert: none found")
    print("====================================\n")

    # 1. Optional: user input for theme / setting
    user_prompt = input("Enter a desired setting or theme (or leave empty): ").strip()
    if not user_prompt:
        user_prompt = "A small coastal town with a controversial political scandal"

    # 2. Initialize RAG retriever (stub for now)
    retriever = RagRetriever(index_path="data/index")  # adapt later

    # 3. Generate the case (victim + theme), now also using location + menu
    case_data = generate_case(
        user_prompt=user_prompt,
        location=location,
        menu={
            "starter": menu["starter"].name if menu["starter"] else None,
            "main": menu["main"].name if menu["main"] else None,
            "dessert": menu["dessert"].name if menu["dessert"] else None,
        },
    )
    print("\n=== CASE ===")
    print(case_data)

    # 4. Generate characters (with RAG context)
    characters = generate_characters(
        case_data=case_data,
        num_characters=NUM_CHARACTERS,
        retriever=retriever,
    )

    # # 5. Generate Images (first image loop)
    # print("\n=== GENERATING IMAGES ===")
    # for c in characters:
    #     # We pass the whole character dict so the LLM can use background/occupation
    #     img_path = generate_character_image(c)
    #     if img_path:
    #         c["image_path"] = img_path
    #     else:
    #         c["image_path"] = "generation_failed.png"

    print("\n=== CHARACTERS ===")
    for c in characters:
        print(f"- {c['name']}: {c['occupation']} ({c['relation_to_victim']})")
        print(f"  Secret: {c['secret']}")
        print(f"  Appearance: {c['appearance']}")
        print(f"  Murder [Y/N]: {c['murderer_label']}")
        # print(f"  Image Path: {c['image_path']}")
        print()

    # 6. Reconstruct the victim's last day
    last_day_data = generate_last_day(case_data=case_data, characters=characters)
    print("\n=== VICTIM'S LAST DAY ===")
    print("Overview:", last_day_data.get("overview", ""))
    print("Timeline:")
    for event in last_day_data.get("timeline", []):
        print(f"- {event['time']} @ {event['location']}: {event['description']}")
        print(f"  Participants: {', '.join(event['participants'])}")
        print(f"  Suspicious: {event['suspicious']}")

    # 7. Generate clues
    clues = generate_clues(
        case_data=case_data,
        characters=characters,
        last_day_data=last_day_data,
    )
    print("\n=== CHARACTER CLUES ===")
    for entry in clues:
        print(f"\n{entry['character']} has clues:")
        for c in entry["clues"]:
            print(f"  -> About {c['target']}: {c['clue']}")

    # 8. Generate solution
    solution = generate_solution(
        case_data=case_data,
        characters=characters,
        last_day_data=last_day_data,
        clues=clues,
    )

    # keep murderer_label consistent with solution
    killer_name = solution.get("killer_name")
    if killer_name:
        for c in characters:
            c["murderer_label"] = c["name"] == killer_name

    print("\n=== FINAL SOLUTION ===")
    print(f"Killer: {solution.get('killer_name')}")
    print("\nMotive:")
    print(solution.get("motive", ""))
    print("\nMethod:")
    print(solution.get("method", ""))
    print("\nOpportunity:")
    print(solution.get("opportunity", ""))
    print("\nHow the clues fit together:")
    for align in solution.get("clue_alignment", []):
        print(
            f"  - {align['character']}'s clue about {align['about']} "
            f"({align['clue_role']}): {align['explanation']}"
        )
    print("\nAlternative suspects:")
    for alt in solution.get("alternative_suspects", []):
        print(f"  - {alt['name']}: {alt['why_they_looked_suspicious']}")

    print("\n=== FINAL REVEAL MONOLOGUE ===")
    print(solution.get("final_reveal_monologue", ""))


if __name__ == "__main__":
    main()
