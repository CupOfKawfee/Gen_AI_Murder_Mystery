# app.py
from flask import Flask, render_template, request, send_file, send_from_directory, session
from flask_session import Session
from llm_pipeline.case_generator import generate_case
from llm_pipeline.character_generator import generate_characters
from llm_pipeline.last_day_victim import generate_last_day
from llm_pipeline.clue_generator import generate_clues
from llm_pipeline.solution_generator import generate_solution
from rag.recipes_retriever import (
    load_all_recipes,
    get_menu_for_location,
    get_menu_by_ingredients,
    Recipe,
)
import secrets
import os
import zipfile
from datetime import datetime
from rag.retriever import RagRetriever




# from image_tool.image_generator import generate_character_image  # Commented out

NUM_CHARACTERS = 7

app = Flask(__name__)
#app.secret_key = secrets.token_hex(16)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-only-change-me")


# Configure Flask-Session for server-side storage
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = "./flask_session"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_USE_SIGNER"] = True

# Initialize Flask-Session
Session(app)
#os.makedirs(app.config["SESSION_FILE_DIR"], exist_ok=True)

print(" Flask-Session initialized with filesystem storage")


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
                location=location,
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

        # Convert Recipe objects to dictionaries for session storage
        menu_dict = {}
        for course in ["starter", "main", "dessert"]:
            if menu[course]:
                menu_dict[course] = {
                    "city": menu[course].city,
                    "name": menu[course].name,
                    "ingredients": menu[course].ingredients,
                    "preparation": menu[course].preparation,
                    "source": menu[course].source,
                    "course_type": menu[course].course_type,
                }
            else:
                menu_dict[course] = None

        # Store mystery data in session
        session["mystery_data"] = {
            "menu": menu_dict,
            "case_data": case_data,
            "characters": characters,
            "last_day_data": last_day_data,
            "clues": clues,
            "solution": solution,
        }

        # Debug: Confirm session storage
        print(" Mystery data stored in session")
        print(f"Session keys: {list(session.keys())}")

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


@app.route("/export_pdf")
def export_pdf():
    """Generate and download complete mystery case as PDF package"""
    from llm_pipeline.pdf_generator import generate_all_pdfs
    from datetime import datetime
    import zipfile

    # Debug: Check session
    print(f"Session keys in export_pdf: {list(session.keys())}")

    # Get mystery data from session
    mystery_data = session.get("mystery_data")

    if not mystery_data:
        print(" No mystery data in session!")
        return (
            """
        <h1>Error: No Mystery Data Found</h1>
        <p>Please <a href="/">generate a mystery</a> first, then try downloading the PDF.</p>
        <p><strong>Troubleshooting:</strong> Make sure cookies are enabled in your browser.</p>
        """,
            400,
        )

    print(" Mystery data found in session")

    # Generate timestamp for unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"outputs/pdfs/{timestamp}"
    os.makedirs(output_dir, exist_ok=True)

    # Reconstruct menu Recipe objects from dictionaries
    menu = {}
    for course in ["starter", "main", "dessert"]:
        if mystery_data["menu"][course]:
            menu[course] = Recipe(**mystery_data["menu"][course])
        else:
            menu[course] = None

    try:
        # Generate all PDFs
        print(f"Generating PDFs in {output_dir}...")
        pdf_files = generate_all_pdfs(
            menu=menu,
            case_data=mystery_data["case_data"],
            characters=mystery_data["characters"],
            last_day_data=mystery_data["last_day_data"],
            clues=mystery_data["clues"],
            solution=mystery_data["solution"],
            output_dir=output_dir,
        )

        print(f" Generated {len(pdf_files)} PDF files")

        # Create zip file containing all PDFs
        zip_path = f"{output_dir}/mystery_complete.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for pdf_file in pdf_files:
                zipf.write(pdf_file, os.path.basename(pdf_file))

        print(f" Created zip file: {zip_path}")

        # Send the zip file for download
        return send_file(
            zip_path,
            mimetype="application/zip",
            as_attachment=True,
            download_name=f"mystery_case_{timestamp}.zip",
        )

    except Exception as e:
        print(f" Error generating PDFs: {str(e)}")
        import traceback

        traceback.print_exc()
        return f"<h1>Error Generating PDFs</h1><pre>{str(e)}</pre>", 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
