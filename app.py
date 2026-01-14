# from flask import Flask, render_template, request
# from llm_pipeline.case_generator import generate_case
# from llm_pipeline.character_generator import generate_characters
# from llm_pipeline.dialogue_generator import generate_dialogues
# from llm_pipeline.last_day_victim import generate_last_day
# from llm_pipeline.clue_generator import generate_clues
# from llm_pipeline.solution_generator import generate_solution
# from rag.retriever import RagRetriever
# from rag.recipes_retriever import load_all_recipes, get_menu_for_location
# from image_tool.image_generator import generate_character_image

# NUM_CHARACTERS = 7

# app = Flask(__name__)


# @app.route("/", methods=["GET", "POST"])
# def index():
#     if request.method == "POST":
#         location = request.form.get("location") or "Hamburg"
#         theme = (
#             request.form.get("theme")
#             or "A small coastal town with a controversial political scandal"
#         )

#         all_recipes = load_all_recipes()
#         menu = get_menu_for_location(location, all_recipes)

#         retriever = RagRetriever(index_path="data/index")

#         case_data = generate_case(
#             user_prompt=theme,
#             location=location,
#             menu={
#                 "starter": menu["starter"].name if menu["starter"] else None,
#                 "main": menu["main"].name if menu["main"] else None,
#                 "dessert": menu["dessert"].name if menu["dessert"] else None,
#             },
#         )

#         characters = generate_characters(
#             case_data=case_data,
#             num_characters=NUM_CHARACTERS,
#             retriever=retriever,
#         )

#         for c in characters:
#             img_path = generate_character_image(c)
#             c["image_path"] = img_path or "generation_failed.png"

#         last_day_data = generate_last_day(case_data=case_data, characters=characters)
#         clues = generate_clues(
#             case_data=case_data, characters=characters, last_day_data=last_day_data
#         )
#         solution = generate_solution(
#             case_data=case_data,
#             characters=characters,
#             last_day_data=last_day_data,
#             clues=clues,
#         )
#         dialogues = generate_dialogues(characters=characters, case_data=case_data)

#         return render_template(
#             "mystery.html",
#             location=location,
#             menu=menu,
#             case=case_data,
#             characters=characters,
#             last_day=last_day_data,
#             clues=clues,
#             solution=solution,
#             dialogues=dialogues,
#         )

#     return render_template("index.html")


# if __name__ == "__main__":
#     app.run(debug=True)
import os
from flask import Flask, render_template, request, send_from_directory
from llm_pipeline.case_generator import generate_case
from llm_pipeline.character_generator import generate_characters
from llm_pipeline.dialogue_generator import generate_dialogues
from llm_pipeline.last_day_victim import generate_last_day
from llm_pipeline.clue_generator import generate_clues
from llm_pipeline.solution_generator import generate_solution
from rag.retriever import RagRetriever
from rag.recipes_retriever import load_all_recipes, get_menu_for_location
from image_tool.image_generator import generate_character_image

NUM_CHARACTERS = 7

app = Flask(__name__)


# serve files from image_tool/image_output
@app.route("/character_images/<path:filename>")
def character_images(filename):
    """Serve generated character images from the output folder."""
    return send_from_directory("image_tool/image_output", filename)


@app.route("/", methods=["GET", "POST"])
def index():
    """Render the landing page or generate a new mystery on POST."""
    if request.method == "POST":
        location = request.form.get("location") or "Hamburg"
        theme = (
            request.form.get("theme")
            or "A small coastal town with a controversial political scandal"
        )

        all_recipes = load_all_recipes()
        menu = get_menu_for_location(location, all_recipes)

        retriever = RagRetriever(index_path="data/index")

        case_data = generate_case(
            user_prompt=theme,
            location=location,
            menu={
                "starter": menu["starter"].name if menu["starter"] else None,
                "main": menu["main"].name if menu["main"] else None,
                "dessert": menu["dessert"].name if menu["dessert"] else None,
            },
        )

        characters = generate_characters(
            case_data=case_data,
            num_characters=NUM_CHARACTERS,
            retriever=retriever,
        )

        for c in characters:
            img_file_path = generate_character_image(
                c
            )  # e.g. image_tool/image_output/Hans_Meier.png
            if img_file_path:
                # keep only the filename part, Flask route will serve it
                filename = img_file_path.split(os.sep)[-1]
                c["image_path"] = f"/character_images/{filename}"
            else:
                c["image_path"] = "/static/generation_failed.png"

        last_day_data = generate_last_day(case_data=case_data, characters=characters)
        clues = generate_clues(
            case_data=case_data, characters=characters, last_day_data=last_day_data
        )
        solution = generate_solution(
            case_data=case_data,
            characters=characters,
            last_day_data=last_day_data,
            clues=clues,
        )
        dialogues = generate_dialogues(characters=characters, case_data=case_data)

        return render_template(
            "mystery.html",
            location=location,
            menu=menu,
            case=case_data,
            characters=characters,
            last_day=last_day_data,
            clues=clues,
            solution=solution,
            dialogues=dialogues,
        )

    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)
