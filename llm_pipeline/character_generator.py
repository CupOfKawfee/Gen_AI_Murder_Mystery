# llm_pipeline/character_generator.py
import json
from typing import Dict, List, Any
from rag.retriever import RagRetriever
from .llm_client import chat_json

def _format_rag_context(docs: List[Dict]) -> str:
    lines = []
    for d in docs:
        lines.append(f"[{d.get('id', 'doc')}] {d.get('text', '')}")
    return "\n".join(lines)


def _parse_jsonish(raw_text: str):
    """
    Try to recover JSON arrays/objects from slightly messy model outputs.
    Returns parsed JSON or None.
    """
    candidates = []
    stripped = raw_text.strip().strip("`")
    candidates.append(stripped)

    # Heuristic: grab first JSON-looking segment
    first_bracket_positions = [pos for pos in (stripped.find("["), stripped.find("{")) if pos != -1]
    last_bracket_positions = [pos for pos in (stripped.rfind("]"), stripped.rfind("}")) if pos != -1]
    if first_bracket_positions and last_bracket_positions:
        start = min(first_bracket_positions)
        end = max(last_bracket_positions)
        if end > start:
            candidates.append(stripped[start : end + 1])

    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return None


def _coerce_character_list(raw_result: Any) -> List[Dict[str, Any]] | None:
    """
    Normalize various possible model return shapes into a character list.
    """
    if isinstance(raw_result, list):
        return raw_result

    if isinstance(raw_result, str):
        parsed = _parse_jsonish(raw_result)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            for key in ("characters", "cast", "result"):
                maybe_list = parsed.get(key)
                if isinstance(maybe_list, list):
                    return maybe_list

    if isinstance(raw_result, dict):
        # Common patterns: {"characters": [...]}, {"cast": [...]}, {"result": [...]}
        for key in ("characters", "cast", "result"):
            maybe_list = raw_result.get(key)
            if isinstance(maybe_list, list):
                return maybe_list

        # If chat_json fell back to {"raw_text": "..."} try to parse that text.
        raw_text = raw_result.get("raw_text")
        if isinstance(raw_text, str):
            parsed = _parse_jsonish(raw_text)
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict):
                for key in ("characters", "cast", "result"):
                    maybe_list = parsed.get(key)
                    if isinstance(maybe_list, list):
                        return maybe_list

    return None


def generate_characters(
    case_data: Dict,
    num_characters: int,
    retriever: RagRetriever,
) -> List[Dict[str, Any]]:
    """
    Uses LM Studio to generate character sheets based on the case and RAG context.
    """

    system_prompt = (
        "You are a writer of interactive murder mysteries. "
        "You always answer with VALID JSON arrays of character objects."
    )

    # Simple retrieval query for the whole cast (you can refine later, e.g. per character)
    query = f"{case_data['location']} {case_data['controversial_theme']} typical people occupations social environment"
    rag_docs = retriever.retrieve(query=query, k=5)
    rag_text = _format_rag_context(rag_docs)

    user_instruction = f"""
You are given a murder-mystery case:

CASE:
{case_data}

You also have some background reference material (from RAG):

RAG_CONTEXT:
{rag_text}

TASK:
Create a cast of exactly {num_characters} suspects or close contacts of the victim. One of them is the murderer.

For each character, include:
- name: string
- appearance: 1–2 sentences, visual details useful for an illustrator
- occupation: short string
- relation_to_victim: short string (friend, colleague, ex-partner, rival, etc.)
- personality_traits: list of 2–4 adjectives
- background: 2–4 sentences (use RAG_CONTEXT to make it realistic)
- secret: 1–3 sentences, describing a secret between this character and the victim
- hint_about_other: object with:
    - target: name or placeholder like "TBD" (you may link characters between each other)
    - hint: 1–2 sentences about that other character's secret or suspicious behavior
- source_references: list of RAG document ids you used, e.g. ["doc1", "doc3"]
- muderer_label: boolean indicating whether this character is the murderer

Return a JSON array of character objects.

"""

    raw_result = chat_json(system_prompt, user_instruction)
    result = _coerce_character_list(raw_result)

    # If something goes wrong, wrap a single dummy character
    if not isinstance(result, list):
        print("[WARN] Character generation returned non-list, using fallback. Raw output:")
        try:
            print(json.dumps(raw_result, indent=2))
        except Exception:
            print(raw_result)
        result = [
            {
                "name": "Fallback Character",
                "appearance": "Tall, nervous, always wearing a dark coat.",
                "occupation": "Local shop owner",
                "relation_to_victim": "Close friend and confidant",
                "personality_traits": ["anxious", "loyal", "observant"],
                "background": "Runs a small convenience store near the harbor.",
                "secret": "They knew about the victim's anonymous source and hid a crucial document.",
                "hint_about_other": {
                    "target": "TBD",
                    "hint": "They saw another character arguing with the victim the night they disappeared."
                },
                "source_references": [d.get("id", "doc") for d in rag_docs],
                "muderer_label": False,
                "raw_model_output": raw_result,
            }
        ]

    # If the model returned more/less than num_characters, trim or pad
    if len(result) > num_characters:
        result = result[:num_characters]
    elif len(result) < num_characters:
        # Just duplicate last if needed – simple fallback
        while len(result) < num_characters:
            result.append(result[-1])

    return result
