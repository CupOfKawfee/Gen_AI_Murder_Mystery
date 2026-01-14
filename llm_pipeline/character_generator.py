# llm_pipeline/character_generator.py
import json
import random
from typing import Dict, List, Any, Optional
from rag.retriever import RagRetriever
from .llm_client import chat_json

REQUIRED_FIELDS = [
    "name",
    "appearance",
    "occupation",
    "relation_to_victim",
    "personality_traits",
    "background",
    "secret",
    "hint_about_other",
    "source_references",
    "murderer_label",
]

def _format_rag_context(docs: List[Dict]) -> str:
    """Format retrieved docs into a compact prompt block."""
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

def _coerce_character_list(raw_result: Any) -> Optional[List[Dict[str, Any]]]:
    """Coerce model output into a character list if possible."""
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
        for key in ("characters", "cast", "result"):
            maybe_list = raw_result.get(key)
            if isinstance(maybe_list, list):
                return maybe_list

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

def _normalize_character(c: Dict[str, Any], allowed_doc_ids: set) -> Dict[str, Any]:
    """Normalize a character dict to the required schema and types."""
    # Backward compat for typo
    if "muderer_label" in c and "murderer_label" not in c:
        c["murderer_label"] = c.pop("muderer_label")

    # Basic field defaults
    c.setdefault("name", "Unnamed")
    c.setdefault("appearance", "")
    c.setdefault("occupation", "")
    c.setdefault("relation_to_victim", "")
    c.setdefault("background", "")
    c.setdefault("secret", "")

    # Traits: ensure list[str]
    traits = c.get("personality_traits", [])
    if isinstance(traits, str):
        traits = [t.strip() for t in traits.split(",") if t.strip()]
    if not isinstance(traits, list):
        traits = []
    c["personality_traits"] = [str(t) for t in traits][:4]

    # hint_about_other: ensure object with target/hint
    hao = c.get("hint_about_other", {})
    if not isinstance(hao, dict):
        hao = {}
    hao.setdefault("target", "TBD")
    hao.setdefault("hint", "")
    c["hint_about_other"] = hao

    # source_references: whitelist
    refs = c.get("source_references", [])
    if isinstance(refs, str):
        refs = [r.strip() for r in refs.split(",") if r.strip()]
    if not isinstance(refs, list):
        refs = []
    refs = [str(r) for r in refs if str(r) in allowed_doc_ids]
    c["source_references"] = refs

    # murderer_label: ensure boolean
    ml = c.get("murderer_label", False)
    c["murderer_label"] = bool(ml)

    # Optional: strip unknown keys to keep schema clean
    cleaned = {k: c.get(k) for k in REQUIRED_FIELDS}
    return cleaned

def _enforce_exactly_one_murderer(characters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Ensure exactly one character has murderer_label set to True."""
    true_idxs = [i for i, c in enumerate(characters) if c.get("murderer_label") is True]
    if len(true_idxs) == 1:
        return characters

    # If none: pick one at random (or could be heuristic-based)
    if len(true_idxs) == 0 and characters:
        pick = random.randrange(len(characters))
        for i, c in enumerate(characters):
            c["murderer_label"] = (i == pick)
        return characters

    # If multiple: keep the first, set others false
    keep = true_idxs[0]
    for i, c in enumerate(characters):
        c["murderer_label"] = (i == keep)
    return characters

def _enforce_unique_names(characters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Ensure character names are unique by appending counters when needed."""
    seen = {}
    for c in characters:
        name = c.get("name", "Unnamed")
        if name not in seen:
            seen[name] = 1
            continue
        seen[name] += 1
        c["name"] = f"{name} ({seen[name]})"
    return characters

def generate_characters(
    case_data: Dict,
    num_characters: int,
    retriever: RagRetriever,
) -> List[Dict[str, Any]]:
    """Generate, normalize, and validate a fixed-size character cast."""
    system_prompt = (
        "You are a writer of interactive murder mysteries. "
        "You MUST output ONLY valid JSON. No markdown, no commentary. "
        "The response MUST be a JSON array of character objects."
    )

    query = f"{case_data.get('location','')} {case_data.get('controversial_theme','')} typical people occupations social environment"
    rag_docs = retriever.retrieve(query=query, k=5)
    rag_text = _format_rag_context(rag_docs)
    allowed_doc_ids = {d.get("id", "doc") for d in rag_docs}

    user_instruction = f"""
CASE:
{case_data}

RAG_CONTEXT:
{rag_text}

CONSTRAINTS:
- Create EXACTLY {num_characters} characters.
- Output MUST be a JSON array and NOTHING else.
- EXACTLY ONE character must have "murderer_label": true. All others false.
- Names must be unique.
- "source_references" may ONLY contain these ids: {sorted(list(allowed_doc_ids))}

SCHEMA (no extra keys):
[
  {{
    "name": "string",
    "appearance": "1-2 sentences",
    "occupation": "string",
    "relation_to_victim": "string",
    "personality_traits": ["adj", "adj"],
    "background": "2-4 sentences grounded in RAG_CONTEXT",
    "secret": "1-3 sentences",
    "hint_about_other": {{"target":"string","hint":"1-2 sentences"}},
    "source_references": ["docId1","docId2"],
    "murderer_label": false
  }}
]
"""

    raw_result = chat_json(system_prompt, user_instruction)
    result = _coerce_character_list(raw_result)

    if not isinstance(result, list):
        print("[WARN] Character generation returned non-list, using fallback. Raw output:")
        try:
            print(json.dumps(raw_result, indent=2))
        except Exception:
            print(raw_result)
        result = []

    # Normalize + validate shape
    normalized = []
    for item in result:
        if isinstance(item, dict):
            normalized.append(_normalize_character(item, allowed_doc_ids))

    # Enforce count without duplicating content if possible
    if len(normalized) > num_characters:
        normalized = normalized[:num_characters]
    elif len(normalized) < num_characters:
        # Safer than duplicating: add lightweight placeholders (or you can trigger a second LLM fill)
        missing = num_characters - len(normalized)
        for i in range(missing):
            normalized.append({
                "name": f"Placeholder {i+1}",
                "appearance": "",
                "occupation": "",
                "relation_to_victim": "",
                "personality_traits": [],
                "background": "",
                "secret": "",
                "hint_about_other": {"target": "TBD", "hint": ""},
                "source_references": [],
                "murderer_label": False,
            })

    normalized = _enforce_unique_names(normalized)
    normalized = _enforce_exactly_one_murderer(normalized)

    return normalized
