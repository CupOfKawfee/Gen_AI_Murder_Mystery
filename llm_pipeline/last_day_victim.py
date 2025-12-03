# llm_pipeline/last_day_victim.py
from typing import Dict, List, Any
from .llm_client import chat_json

def generate_last_day(case_data: Dict, characters: List[Dict[str, Any]]) -> Dict:
    """
    Uses the case data and the character list to reconstruct
    the victim's last day as a structured timeline.
    """

    system_prompt = (
        "You are an investigator reconstructing the victim's last day. "
        "Always respond with VALID JSON."
    )

    # Optional: make a compact list of characters for the prompt
    char_summary = [
        {
            "name": c["name"],
            "relation_to_victim": c.get("relation_to_victim", ""),
            "occupation": c.get("occupation", ""),
            "secret_about_victim": c.get("secret_about_victim", "")
        }
        for c in characters
    ]

    user_instruction = f"""
You are given a murder case and the main characters.

CASE:
{case_data}

CHARACTERS (summary):
{char_summary}

TASK:
Reconstruct the victim's last day as a clear, chronological timeline.

Return JSON with:
- "overview": 2–4 sentence summary of the last day
- "timeline": an array of events, each:
    - "time": short string (e.g. "09:00", "late evening")
    - "location": string
    - "participants": list of character names involved (use names from CHARACTERS, plus victim if relevant)
    - "description": 1–3 sentences describing what happened
    - "suspicious": boolean indicating whether this event is suspicious
"""

    result = chat_json(system_prompt, user_instruction)

    # Basic fallback if the model doesn't behave
    if not isinstance(result, dict) or "timeline" not in result:
        result = {
            "overview": "Fallback: the victim moved through the town, meeting several suspects.",
            "timeline": [],
            "raw_model_output": result,
        }

    return result
