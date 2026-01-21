import json
import re
from typing import Any, Optional


def extract_json_block(text: str) -> Optional[str]:
    """
    Extracts the first JSON array or object from text.
    Handles LLM outputs with explanations or code fences.
    """
    if not text:
        return None

    text = text.strip()

    # Remove markdown fences if present
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()

    # Match JSON object or array
    match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
    if not match:
        return None

    return match.group(1)


def safe_json_loads(text: str) -> Optional[Any]:
    """
    Safely parse JSON from noisy LLM output.
    Returns None if parsing fails.
    """
    json_block = extract_json_block(text)
    if not json_block:
        return None

    try:
        return json.loads(json_block)
    except json.JSONDecodeError:
        return None
