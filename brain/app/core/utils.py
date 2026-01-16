import json
import re
import logging

logger = logging.getLogger(__name__)

def extract_json(text: str) -> dict:
    """
    Robustly extract JSON from a string that might contain markdown or other text.
    """
    if not text:
        return {}

    # Try to find JSON block in markdown
    json_match = re.search(r"```json\s*([\s\S]*?)\s*```", text)
    if json_match:
        content = json_match.group(1)
    else:
        # Try to find any block that looks like JSON
        json_match = re.search(r"({[\s\S]*})", text)
        if json_match:
            content = json_match.group(1)
        else:
            content = text

    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f"JSON Decode Error: {e}. Content snippet: {content[:100]}...")
        
        # Last resort: try to fix common issues like trailing commas
        try:
            # Remove trailing commas before closing braces/brackets
            fixed_content = re.sub(r",\s*([\]}])", r"\1", content)
            return json.loads(fixed_content)
        except Exception:
            return {}
