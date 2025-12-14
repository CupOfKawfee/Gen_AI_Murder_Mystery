# llm_pipeline/case_generator.py
from typing import Dict
from .llm_client import chat_json


def generate_case(user_prompt: str, location: str, menu: Dict) -> Dict:
    """
    Uses LM Studio to generate a murder-mystery case with a controversial victim and theme,
    taking into account a concrete location and a dinner menu (starter, main, dessert).
    """

    starter = menu.get("starter")
    main = menu.get("main")
    dessert = menu.get("dessert")

    system_prompt = (
        "You are a creative assistant that designs grounded, structured murder-mystery cases. "
        "You must always respond with valid JSON only."
    )

    user_instruction = f"""
Create a murder-mystery setup inspired by this user setting or theme:

\"\"\"{user_prompt}\"\"\".

The mystery takes place in the following location:
- location_of_event: "{location}"

During the evening of the murder, there is a dinner being served with this menu:
- starter: {starter if starter else "none"}
- main_course: {main if main else "none"}
- dessert: {dessert if dessert else "none"}

These dishes should be typical for the location and can be referenced in the setting,
the social dynamics between guests, or the circumstances of the crime.

Requirements:
- There is ONE victim.
- The case revolves around a controversial theme (e.g. corruption, data leak, activism, art scandal, etc.).
- The setting should be specific (e.g. small coastal town, university, startup office, etc.).
- The described location and dinner context should fit naturally into the story (for example,
  the victim is killed during or around the meal, or the menu is part of the atmosphere).

Return JSON with the following keys:
- victim_name: string
- victim_description: short string (age, job, notable traits)
- controversial_theme: string
- location: short description of the main setting (include the given location where appropriate)
- summary: 3–5 sentences summarizing the case
- timeline: 1–3 sentences describing the rough timeline of the crime
"""

    result = chat_json(system_prompt, user_instruction)

    # Add minimal fallback if something goes wrong
    if "victim_name" not in result:
        result = {
            "victim_name": "Lena Hartmann",
            "victim_description": "A 35-year-old investigative journalist.",
            "controversial_theme": "Exposure of corruption in local politics",
            "location": f"{location} (defaulted case location)",
            "summary": (
                "Lena Hartmann was found dead shortly before releasing an article "
                "about corruption in the town council. Many residents had something to lose."
            ),
            "timeline": "Lena disappeared on Friday night, her body was found on Saturday morning.",
            "raw_model_output": result.get("raw_text", str(result)),
        }

    return result
