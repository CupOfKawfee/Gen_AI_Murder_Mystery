# llm_pipeline/solution_generator.py
from typing import Dict, List, Any
from .llm_client import chat_json

def generate_solution(
    case_data: Dict,
    characters: List[Dict[str, Any]],
    last_day_data: Dict,
    clues: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Generate a coherent solution to the mystery, aligned with:
    - case_data
    - characters (including murderer_label if present)
    - last_day_data (timeline)
    - clues (who suspects whom and why)
    """

    # See if you already have a labeled murderer
    labeled_killers = [c["name"] for c in characters if c.get("murderer_label") is True]
    killer_hint = labeled_killers[0] if labeled_killers else None

    system_prompt = (
        "You are a detective summarizing and solving an interactive murder mystery. "
        "You MUST respond with VALID JSON ONLY."
    )

    compact_chars = [
        {
            "name": c["name"],
            "relation_to_victim": c.get("relation_to_victim", ""),
            "occupation": c.get("occupation", ""),
            "murderer_label": c.get("murderer_label", None),
            "secret_about_victim": c.get("secret_about_victim") or c.get("secret", ""),
        }
        for c in characters
    ]

    user_instruction = f"""
You are given a fictional murder mystery. Use ALL of the information to produce a coherent solution.

CASE_DATA:
{case_data}

CHARACTERS:
{compact_chars}

VICTIM_LAST_DAY:
{last_day_data}

CHARACTER_CLUES:
{clues}

KILLER_HINT:
{killer_hint}

RULES:

1. If KILLER_HINT is not null, that character IS the murderer.
   Your reasoning MUST conclude that this person is the killer.
2. If KILLER_HINT is null, you must pick EXACTLY ONE character as the murderer.
3. The solution MUST be consistent with the timeline in VICTIM_LAST_DAY.
4. The solution MUST use and respect the CHARACTER_CLUES: they should either
   - point to the real killer, or
   - be explainable as partial truths, misunderstandings, or red herrings.
5. Do NOT contradict the basic facts in CASE_DATA.

RETURN STRICT JSON with the following structure:

{{
  "killer_name": "exact name of the murderer (from CHARACTERS)",
  "motive": "2-5 sentence explanation of why the killer did it.",
  "method": "2-4 sentences describing how the murder was carried out.",
  "opportunity": "Explain how the killer had the opportunity (timeline + location).",
  "clue_alignment": [
    {{
      "character": "Name of character who had this clue",
      "about": "Name of target character",
      "clue_role": "supports_guilt" or "red_herring" or "partial_truth",
      "explanation": "How this clue fits into the final solution."
    }}
  ],
  "alternative_suspects": [
    {{
      "name": "Character name",
      "why_they_looked_suspicious": "short explanation"
    }}
  ],
  "final_reveal_monologue": "A short dramatic speech the detective could give when revealing the killer."
}}
"""

    result = chat_json(system_prompt, user_instruction)

    # Simple fallback if parsing fails
    if not isinstance(result, dict) or "killer_name" not in result:
        result = {
            "killer_name": killer_hint or (characters[0]["name"] if characters else "Unknown"),
            "motive": "Fallback: The killer feared the exposé would destroy their status and finances.",
            "method": "Fallback: The killer entered the study late at night and staged the scene as an accident.",
            "opportunity": "Fallback: They were present near the victim during the final hours without a solid alibi.",
            "clue_alignment": [],
            "alternative_suspects": [],
            "final_reveal_monologue": (
                "In the end, it was obvious. Only one person had motive, means, and opportunity..."
            ),
            "raw_model_output": result,
        }

    return result
