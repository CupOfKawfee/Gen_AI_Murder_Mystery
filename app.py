# app.py
from flask import Flask, render_template, request, send_from_directory
from llm_pipeline.case_generator import generate_case
from llm_pipeline.character_generator import generate_characters
from llm_pipeline.last_day_victim import generate_last_day
from llm_pipeline.clue_generator import generate_clues
from llm_pipeline.solution_generator import generate_solution
from rag.retriever import RagRetriever

from rag.recipes_retriever import (
    load_all_recipes,
    get_menu_for_location,
    get_menu_by_ingredients,
)
# from image_tool.image_generator import generate_character_image  # Commented out

NUM_CHARACTERS = 7

app = Flask(__name__)


@app.route("/character_images/<path:filename>")
def character_images(filename):
    return send_from_directory("image_tool/image_output", filename)


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Get form data
        location = request.form.get("location", "").strip() or "Hamburg"
        theme = (
            request.form.get("theme", "").strip()
            or "A small coastal town with a controversial political scandal"
        )

        # Get ingredient preferences
        starter_ingredient = request.form.get("starter_ingredient", "").strip()
        main_ingredient = request.form.get("main_ingredient", "").strip()
        dessert_ingredient = request.form.get("dessert_ingredient", "").strip()

        # Load recipes
        all_recipes = load_all_recipes()

        # Get menu based on ingredients with location fallback
        if starter_ingredient or main_ingredient or dessert_ingredient:
            print(
                f"Searching for recipes with: starter={starter_ingredient}, main={main_ingredient}, dessert={dessert_ingredient}"
            )
            menu = get_menu_by_ingredients(
                starter_ingredient,
                main_ingredient,
                dessert_ingredient,
                all_recipes,
                location=location,  # Added location for fallback
            )
        else:
            print(f"Using location-based menu for: {location}")
            menu = get_menu_for_location(location, all_recipes)

        # Initialize RAG retriever
        retriever = RagRetriever(index_path="data/index")

        # Generate case
        print("Generating case...")
        case_data = generate_case(
            user_prompt=theme,
            location=location,
            menu={
                "starter": menu["starter"].name if menu["starter"] else None,
                "main": menu["main"].name if menu["main"] else None,
                "dessert": menu["dessert"].name if menu["dessert"] else None,
            },
        )
        print(f"Case generated: {case_data.get('victim_name', 'Unknown')}")

        # Generate characters
        print("Generating characters...")
        characters = generate_characters(
            case_data=case_data,
            num_characters=NUM_CHARACTERS,
            retriever=retriever,
        )
        print(f"Generated {len(characters)} characters")

        # Set default image path (since image generation is disabled)
        for c in characters:
            c["image_path"] = "/static/placeholder.png"

        # Uncomment below if you want to enable image generation later
        # import os
        # from image_tool.image_generator import generate_character_image
        # for c in characters:
        #     img_file_path = generate_character_image(c)
        #     if img_file_path:
        #         filename = img_file_path.split(os.sep)[-1]
        #         c["image_path"] = f"/character_images/{filename}"
        #     else:
        #         c["image_path"] = "/static/generation_failed.png"

        # Generate last day
        print("Generating victim's last day...")
        last_day_data = generate_last_day(case_data=case_data, characters=characters)

        # Generate clues
        print("Generating clues...")
        clues = generate_clues(
            case_data=case_data, characters=characters, last_day_data=last_day_data
        )

        # Generate solution
        print("Generating solution...")
        solution = generate_solution(
            case_data=case_data,
            characters=characters,
            last_day_data=last_day_data,
            clues=clues,
        )

        print("Mystery generation complete!")

        return render_template(
            "mystery.html",
            location=location,
            menu=menu,
            case=case_data,
            characters=characters,
            last_day=last_day_data,
            clues=clues,
            solution=solution,
        )

    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)
