# llm_pipeline/llm_client.py
import os
import json
from typing import List, Dict, Optional
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# You can set these in your .env file
LM_STUDIO_BASE_URL = os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
LM_STUDIO_MODEL = os.getenv("LM_STUDIO_MODEL", "Your-Model-Name-Here")
LM_STUDIO_API_KEY = os.getenv("LM_STUDIO_API_KEY", "lm-studio")  # dummy but required

client = OpenAI(
    base_url=LM_STUDIO_BASE_URL,
    api_key=LM_STUDIO_API_KEY,
)


def chat(
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
) -> str:
    """
    Low-level wrapper for LM Studio chat completion.
    messages: list of dicts like {"role": "user"/"system"/"assistant", "content": "..."}
    """

    response = client.chat.completions.create(
        model=LM_STUDIO_MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content


def chat_json(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.6,
) -> Dict:
    """
    Helper that asks the model to return STRICT JSON and parses it.
    Tries to be robust against extra markdown (```json ... ```).
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (
                user_prompt
                + "\n\nRespond ONLY with valid JSON, no explanation, no markdown."
            ),
        },
    ]

    raw = chat(messages, temperature=temperature)
    # Try to find JSON if the model wrapped it in backticks
    raw_stripped = raw.strip()
    if raw_stripped.startswith("```"):
        raw_stripped = raw_stripped.strip("`")
        # remove possible "json" language tag
        raw_stripped = raw_stripped.replace("json", "", 1).strip()

    try:
        return json.loads(raw_stripped)
    except json.JSONDecodeError:
        print("[WARNING] Failed to parse JSON from model. Raw output:")
        print(raw)
        # Fallback: return as text
        return {"raw_text": raw}
