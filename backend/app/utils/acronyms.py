import re


def canonicalize_acronyms(value: str) -> str:
    """Correct known career acronyms without changing other words."""
    return re.sub(r"\b(ai|ml|ux|ui|nlp|api)\b", lambda match: match.group(0).upper(), value, flags=re.I)
