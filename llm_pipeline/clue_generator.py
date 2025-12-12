# llm_pipeline/clue_generator.py
from typing import List, Dict, Any
from .llm_client import chat_json

def generate_clues(
    case_data: Dict,
    characters: List[Dict[str, Any]],
    last_day_data: Dict
) -> List[Dict[str, Any]]:
    """
    Generate 1–2 meaningful clues per character.
    Each clue should help solve the mystery when combined with the others.
    Clues MUST relate to:
    - the case_data (theme, victim, timeline)
    - characters (secrets, relationships, muderer_label)
    - last_day_data (events, suspicious moments)
    """

    system_prompt = (
        "You are an investigator designing advanced deduction puzzles. "
        "All output MUST be valid JSON."
    )

    # Create compact summaries for the prompt
    char_summary = [
        {
            "name": c["name"],
            "relation_to_victim": c.get("relation_to_victim", ""),
            "secret_about_victim": c.get("secret_about_victim", ""),
            "personality": c.get("personality_traits", [])
        }
        for c in characters
    ]

    user_instruction = f"""
We are constructing a murder mystery. You are given:

CASE_DATA:
{case_data}

CHARACTERS:
{char_summary}

VICTIM_LAST_DAY:
{last_day_data}

TASK:
For EACH character, generate 1–2 clues that they have about ANOTHER character.
These clues will be DISCUSSED later by the group to solve the mystery.

RULES FOR CLUES:
1. A clue MUST point toward suspicious behavior, contradictions, evidence, or important insights.
2. A clue MUST involve EXACT character names from the character list.
3. The clues MUST be consistent with the victim's timeline from LAST_DAY_DATA.
4. The clues MUST help solve the mystery when combined and give hints about who is the killer. 
5. Clues must avoid revealing the killer directly — they should provide partial, interconnected leads.
6. Clues MUST be specific, not vague.
7. A character must NEVER have a clue about themselves. The "target" must always be a DIFFERENT character name.

FORMAT:
Return a JSON array. Each entry is:

{{
  "character": "NameOfCharacterWhoHasTheClue",
  "clues": [
    {{
      "target": "NameOfCharacterTheClueIsAbout",
      "clue": "1-3 sentence description of evidence, behavior, contradiction, or suspicious detail."
    }},
    ...
  ]
}}

IMPORTANT:
- Ensure EVERY character appears exactly once in the output.
- Ensure each has 1–2 clues.
- Ensure each clue references concrete details from CASE_DATA or LAST_DAY_DATA.
"""

    result = chat_json(system_prompt, user_instruction)

    # basic fallback if model fails:
    if not isinstance(result, list):
        result = [
            {
                "character": characters[0]["name"],
                "clues": [
                    {
                        "target": characters[1]["name"],
                        "clue": "Fallback clue: observed at the harbor near the victim's last location."
                    }
                ],
                "raw_model_output": result,
            }
        ]

    return result
