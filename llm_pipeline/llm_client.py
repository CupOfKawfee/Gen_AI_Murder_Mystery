import os
import sys
import json
from typing import List, Dict, Optional

from dotenv import load_dotenv
from openai import OpenAI, BadRequestError

load_dotenv()


def _getenv_stripped(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip()

LM_STUDIO_BASE_URL = _getenv_stripped(
    "LM_STUDIO_BASE_URL", "http://localhost:1234/v1"
)
LM_STUDIO_MODEL = _getenv_stripped("LM_STUDIO_MODEL", "qwen/qwen3-vl-4b")
LM_STUDIO_API_KEY = _getenv_stripped(
    "LM_STUDIO_API_KEY", "lm-studio"
)  # dummy but required

client = OpenAI(
    base_url=LM_STUDIO_BASE_URL,
    api_key=LM_STUDIO_API_KEY,
)


def _safe_print(text: str) -> None:
    """Print without crashing on Windows cp1252 consoles."""
    try:
        print(text)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or "utf-8"
        safe = text.encode(encoding, errors="ignore").decode(encoding, errors="ignore")
        print(safe)


def chat(
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
) -> str:
    """
    Low-level wrapper for LM Studio chat completion.
    messages: list of dicts like {"role": "user"/"system"/"assistant", "content": "..."}
    """
    try:
        response = client.chat.completions.create(
            model=LM_STUDIO_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content
    except BadRequestError as e:
        _safe_print(f"[ERROR] LLM request failed: {e}")
        # Fallback so the web app does not crash
        return "LLM error: model crashed or request invalid."


def chat_json(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.6,
) -> Dict:
    """
    Helper that asks the model to return STRICT JSON and parses it.
    Tries to be robust against extra markdown (``````).
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
        _safe_print("[WARNING] Failed to parse JSON from model. Raw output:")
        _safe_print(raw)
        # Fallback: return as text so the app doesn't crash
        return {"raw_text": raw}
