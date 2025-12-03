# llm_pipeline/dialogue_generator.py
from typing import List, Dict, Any
from .llm_client import chat_json

def generate_dialogues(
    characters: List[Dict[str, Any]],
    case_data: Dict,
    num_scenes: int = 5,
) -> List[Dict[str, Any]]:
    """
    Generates short conversations between the characters using LM Studio.
    
    Output: list of scenes.
    Each scene:
    {
      "description": "...",
      "turns": [
         {"speaker": "Name", "role": "[1]" or "[2]", "utterance": "..."}
      ]
    }
    """

    system_prompt = (
        "You are a screenwriter for interactive murder-mystery games. "
        "You always answer with VALID JSON, representing scenes and dialogue turns."
    )

    # Prepare a compact character summary for the prompt
    char_summary = []
    for c in characters:
        char_summary.append(
            {
                "name": c["name"],
                "relation_to_victim": c.get("relation_to_victim", ""),
                "secret_about_victim": c.get("secret_about_victim", ""),
                "personality_traits": c.get("personality_traits", []),
            }
        )

    user_instruction = f"""
You are given a murder-mystery case and the main characters.

CASE:
{case_data}

CHARACTERS (summary):
{char_summary}

TASK:
Create {num_scenes} short dialogue scenes between these characters.
Rules:
- The victim does NOT speak (they are dead or missing).
- Each living character must speak at least once across all scenes.
- Use [1] for the character who asks a direct question about another character's secret.
- Use [2] for the character who answers that question about their own secret.
- When [1] asks about a secret, they must briefly explain HOW they know or suspect that secret.
- The tone should feel tense and suspicious, but not too long-winded.

Return a JSON array of scenes.
Each scene must be of the form:
[
  {
    "description": "short description of where/when the scene takes place",
    "turns": [
      {
        "speaker": "Character Name",
        "role": "[1]" or "[2]",
        "utterance": "their line of dialogue"
      },
      ...
    ]
  },
  ...
]
"""

    result = chat_json(system_prompt, user_instruction)

    if not isinstance(result, list):
        # Minimal fallback dummy scene
        result = [
            {
                "description": "Fallback scene in a dimly lit room.",
                "turns": [
                    {
                        "speaker": characters[0]["name"],
                        "role": "[1]",
                        "utterance": "I know you’re hiding something about the victim. I saw you near the harbor that night."
                    },
                    {
                        "speaker": characters[1]["name"],
                        "role": "[2]",
                        "utterance": "Fine, I was there. But I wasn’t the only one – and I’m not the killer."
                    },
                ],
                "raw_model_output": result,
            }
        ]

    return result
