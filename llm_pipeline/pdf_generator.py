import json
import os
import re
from typing import Dict, List, Any, Optional

from fpdf import FPDF


# ----------------------------
# Font handling (Unicode)
# ----------------------------
DEFAULT_FONT_FAMILY = "DejaVu"


def _find_font_file() -> Optional[str]:
    candidates = [
        os.path.join(os.getcwd(), "assets", "fonts", "DejaVuSans.ttf"),
        os.path.join(os.getcwd(), "DejaVuSans.ttf"),
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/local/share/fonts/dejavu/DejaVuSans.ttf",
        "/Library/Fonts/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/DejaVuSans.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def _register_fonts(pdf: FPDF) -> None:
    font_path = _find_font_file()
    if font_path:
        pdf.add_font(DEFAULT_FONT_FAMILY, "", font_path, uni=True)
        pdf.add_font(DEFAULT_FONT_FAMILY, "B", font_path, uni=True)
    # else: fallback to core fonts; PDF still works but may show '?' for unsupported chars


def _set_font(pdf: FPDF, style: str, size: int) -> None:
    try:
        pdf.set_font(DEFAULT_FONT_FAMILY, style, size)
    except Exception:
        pdf.set_font("Helvetica", style, size)


# ----------------------------
# Content filters (remove unwanted fields)
# ----------------------------
DROP_KEYS_CASE = {
    "controversial_theme",
    "controversial theme",
    "secret",
    "hint_about_other",
    "hint about other",
    "source_reference",
    "source reference",
    "source_references",
    "source references",
}

DROP_KEYS_CHARACTER_DETAILS = {
    "controversial_theme",
    "controversial theme",
    "secret",
    "hint_about_other",
    "hint about other",
    "source_reference",
    "source reference",
    "source_references",
    "source references",
}


# ----------------------------
# Text cleaning / normalization
# ----------------------------
def _strip_source_references_block(text: str) -> str:
    """
    Remove blocks like:
    Source References:
    - doc1
    - doc2
    """
    return re.sub(
        r"\n?Source References:\s*\n(?:-.*\n?)*",
        "",
        text,
        flags=re.IGNORECASE,
    )


def _fix_hard_wraps_inside_words(text: str) -> str:
    """
    Fix cases like 're\\nvealed' or 'wit\\nh' caused by hard line breaks inside words.
    """
    text = re.sub(r"([A-Za-zÀ-ÖØ-öø-ÿ])\n([A-Za-zÀ-ÖØ-öø-ÿ])", r"\1\2", text)
    text = re.sub(r"\s*\n\s*", " ", text)
    text = re.sub(r"[ \t]{2,}", " ", text).strip()
    return text


def _normalize_punctuation(text: str) -> str:
    replacements = {
        "“": '"',
        "”": '"',
        "„": '"',
        "’": "'",
        "‘": "'",
        "–": "-",
        "—": "-",
        "…": "...",
        "\u00a0": " ",  # NBSP
        "\u200b": "",   # zero-width space
        "\ufeff": "",   # BOM
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text


def _break_long_tokens(text: str, chunk: int = 30) -> str:
    """
    Prevent fpdf from needing to break words mid-token by inserting spaces
    into extremely long tokens (e.g., URLs, hashes, long AI strings without spaces).
    This allows wrapmode="WORD" without crashes or ugly mid-word splits.
    """
    def split_token(tok: str) -> str:
        if len(tok) <= chunk:
            return tok
        return " ".join(tok[i:i + chunk] for i in range(0, len(tok), chunk))

    parts = text.split(" ")
    parts = [split_token(p) for p in parts]
    return " ".join(parts)


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)

    text = _strip_source_references_block(text)
    text = _fix_hard_wraps_inside_words(text)
    text = _normalize_punctuation(text)
    text = _break_long_tokens(text, chunk=30)

    return text


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _new_pdf() -> FPDF:
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_margins(15, 15, 15)
    _register_fonts(pdf)
    pdf.add_page()
    return pdf


def _title(pdf: FPDF, text: str) -> None:
    _set_font(pdf, "B", 18)
    pdf.cell(0, 10, _clean_text(text), ln=True)
    pdf.ln(2)


def _heading(pdf: FPDF, text: str) -> None:
    _set_font(pdf, "B", 13)
    pdf.cell(0, 8, _clean_text(text), ln=True)


def _paragraph(pdf: FPDF, text: str) -> None:
    _set_font(pdf, "", 11)
    txt = _clean_text(text)

    pdf.set_x(pdf.l_margin)
    w = pdf.w - pdf.l_margin - pdf.r_margin

    # WORD wrapping avoids splitting words like "wit h"
    pdf.multi_cell(w, 6, txt, wrapmode="WORD")


def _kv(pdf: FPDF, key: str, value: Any) -> None:
    _set_font(pdf, "B", 11)
    pdf.set_x(pdf.l_margin)
    pdf.cell(0, 6, _clean_text(f"{key}:"), ln=True)

    _set_font(pdf, "", 11)
    pdf.set_x(pdf.l_margin)
    w = pdf.w - pdf.l_margin - pdf.r_margin
    pdf.multi_cell(w, 6, _clean_text(value), wrapmode="WORD")


def _pretty_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return value

    if isinstance(value, list):
        parts: List[str] = []
        for item in value:
            if isinstance(item, dict):
                # compact dict summary
                parts.append("; ".join(f"{k}: {v}" for k, v in item.items()))
            else:
                parts.append(str(item))
        return "\n".join(f"- {p}" for p in parts) if parts else ""

    if isinstance(value, dict):
        lines: List[str] = []
        for k, v in value.items():
            if isinstance(v, (dict, list)):
                lines.append(f"{k}:")
                nested = _pretty_value(v)
                if nested:
                    for ln in nested.splitlines():
                        lines.append(f"  {ln}")
            else:
                lines.append(f"{k}: {v}")
        return "\n".join(lines)

    return str(value)


def _render_case_section(pdf: FPDF, case_data: Dict[str, Any]) -> None:
    """
    Render case data in a readable way, excluding unwanted keys.
    """
    preferred = [
        "title",
        "case_title",
        "setting",
        "location",
        "city",
        "date",
        "victim",
        "victim_name",
        "crime",
        "crime_summary",
        "overview",
        "objective",
        "rules",
        "notes",
    ]

    rendered_keys = set()

    def allowed(k: str) -> bool:
        return k.strip().lower() not in DROP_KEYS_CASE

    for key in preferred:
        if key in case_data and allowed(key) and case_data[key] not in (None, "", [], {}):
            _kv(pdf, key.replace("_", " ").title(), _pretty_value(case_data[key]))
            rendered_keys.add(key)

    for key in sorted(case_data.keys()):
        if key in rendered_keys:
            continue
        if not allowed(key):
            continue
        value = case_data[key]
        if value in (None, "", [], {}):
            continue
        _kv(pdf, key.replace("_", " ").title(), _pretty_value(value))


def create_menu_pdf(menu: Dict[str, Any], output_dir: str) -> str:
    _ensure_dir(output_dir)
    pdf = _new_pdf()
    _title(pdf, "Dinner Menu and Recipes")

    for label, key in [("Starter", "starter"), ("Main Course", "main"), ("Dessert", "dessert")]:
        recipe = menu.get(key)
        _heading(pdf, label)
        if recipe:
            _paragraph(pdf, f"{recipe.name} ({recipe.city})")
            _kv(pdf, "Ingredients", recipe.ingredients)
            _kv(pdf, "Preparation", recipe.preparation)
            if getattr(recipe, "source", ""):
                _kv(pdf, "Source", recipe.source)
        else:
            _paragraph(pdf, "None found for this location.")
        pdf.ln(2)

    path = os.path.join(output_dir, "dinner_menu_and_recipes.pdf")
    pdf.output(path)
    return path


def create_last_day_pdf(last_day_data: Dict[str, Any], output_dir: str) -> str:
    _ensure_dir(output_dir)
    pdf = _new_pdf()
    _title(pdf, "Victim's Last Day")

    _heading(pdf, "Overview")
    _paragraph(pdf, last_day_data.get("overview", ""))
    pdf.ln(2)

    _heading(pdf, "Timeline")
    timeline = last_day_data.get("timeline", [])
    if not timeline:
        _paragraph(pdf, "No timeline entries available.")
    else:
        for event in timeline:
            time = event.get("time", "Unknown time")
            location = event.get("location", "Unknown location")
            desc = event.get("description", "")
            participants = ", ".join(event.get("participants", []) or [])
            suspicious = "Yes" if event.get("suspicious") else "No"
            _paragraph(pdf, f"{time} @ {location}")
            _paragraph(pdf, desc)
            _paragraph(pdf, f"Participants: {participants}")
            _paragraph(pdf, f"Suspicious: {suspicious}")
            pdf.ln(2)

    path = os.path.join(output_dir, "victims_last_day.pdf")
    pdf.output(path)
    return path


def create_clues_pdf(clues: List[Dict[str, Any]], output_dir: str) -> str:
    _ensure_dir(output_dir)
    pdf = _new_pdf()
    _title(pdf, "Character Clues (Cutout Pages)")

    for idx, entry in enumerate(clues):
        if idx > 0:
            pdf.add_page()
        _heading(pdf, entry.get("character", "Unknown Character"))
        clue_list = entry.get("clues", [])
        if not clue_list:
            _paragraph(pdf, "No clues available.")
        else:
            for clue in clue_list:
                target = clue.get("target", "Unknown")
                text = clue.get("clue", "")
                _paragraph(pdf, f"About {target}:")
                _paragraph(pdf, text)
                pdf.ln(1)

    path = os.path.join(output_dir, "character_clues.pdf")
    pdf.output(path)
    return path


def create_solution_pdf(solution: Dict[str, Any], output_dir: str) -> str:
    _ensure_dir(output_dir)
    pdf = _new_pdf()
    _title(pdf, "Final Solution")

    _kv(pdf, "Killer", solution.get("killer_name", ""))
    _kv(pdf, "Motive", solution.get("motive", ""))
    _kv(pdf, "Method", solution.get("method", ""))
    _kv(pdf, "Opportunity", solution.get("opportunity", ""))

    pdf.ln(2)
    _heading(pdf, "Clue Alignment")
    alignments = solution.get("clue_alignment", [])
    if not alignments:
        _paragraph(pdf, "No clue alignment details available.")
    else:
        for item in alignments:
            character = item.get("character", "")
            about = item.get("about", "")
            role = item.get("clue_role", "")
            explanation = item.get("explanation", "")
            _paragraph(pdf, f"{character} about {about} ({role})")
            _paragraph(pdf, explanation)
            pdf.ln(1)

    pdf.ln(2)
    _heading(pdf, "Alternative Suspects")
    alts = solution.get("alternative_suspects", [])
    if not alts:
        _paragraph(pdf, "No alternative suspects listed.")
    else:
        for alt in alts:
            name = alt.get("name", "")
            why = alt.get("why_they_looked_suspicious", "")
            _paragraph(pdf, f"{name}: {why}")

    pdf.ln(2)
    _heading(pdf, "Final Reveal Monologue")
    _paragraph(pdf, solution.get("final_reveal_monologue", ""))

    path = os.path.join(output_dir, "final_solution.pdf")
    pdf.output(path)
    return path


def _character_image_path(character: Dict[str, Any], image_dir: str) -> Optional[str]:
    image_path = character.get("image_path")
    if image_path and os.path.exists(image_path):
        return image_path

    safe_name = str(character.get("name", "Unnamed")).replace(" ", "_")
    candidate = os.path.join(image_dir, f"{safe_name}.png")
    if os.path.exists(candidate):
        return candidate
    return None


def create_character_pdfs(
    characters: List[Dict[str, Any]],
    case_data: Dict[str, Any],
    output_dir: str,
    image_dir: str = "image_tool/image_output",
) -> List[str]:
    _ensure_dir(output_dir)
    outputs: List[str] = []

    def allowed_character_key(k: str) -> bool:
        return k.strip().lower() not in DROP_KEYS_CHARACTER_DETAILS

    for character in characters:
        safe_name = str(character.get("name", "Unnamed")).replace(" ", "_")
        pdf = _new_pdf()
        _title(pdf, f"Character Sheet: {character.get('name', 'Unnamed')}")

        img_path = _character_image_path(character, image_dir)
        if img_path:
            try:
                pdf.image(img_path, w=60)
                pdf.ln(2)
            except Exception:
                _paragraph(pdf, "Image present but could not be embedded.")
        else:
            _paragraph(pdf, "Image not available.")
            pdf.ln(2)

        _heading(pdf, "Case")
        _render_case_section(pdf, case_data)
        pdf.ln(2)

        _heading(pdf, "Character Details")
        for key, value in character.items():
            if not allowed_character_key(key):
                continue
            _kv(pdf, key.replace("_", " ").title(), _pretty_value(value))

        path = os.path.join(output_dir, f"character_{safe_name}.pdf")
        pdf.output(path)
        outputs.append(path)

    return outputs


def generate_all_pdfs(
    menu: Dict[str, Any],
    case_data: Dict[str, Any],
    characters: List[Dict[str, Any]],
    last_day_data: Dict[str, Any],
    clues: List[Dict[str, Any]],
    solution: Dict[str, Any],
    output_dir: str = "outputs/pdfs",
) -> List[str]:
    outputs: List[str] = []
    outputs.append(create_menu_pdf(menu, output_dir))
    outputs.append(create_last_day_pdf(last_day_data, output_dir))
    outputs.append(create_clues_pdf(clues, output_dir))
    outputs.append(create_solution_pdf(solution, output_dir))
    outputs.extend(create_character_pdfs(characters, case_data, output_dir))
    return outputs
