import re


def _collapse_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def normalize_city_for_search(city: str) -> str:
    collapsed = _collapse_spaces(city)
    return collapsed.casefold().replace("ё", "е")


def format_city_for_display(city: str) -> str:
    collapsed = _collapse_spaces(city)
    parts = []
    for token in collapsed.split(" "):
        hyphen_parts = [chunk.capitalize() for chunk in token.split("-")]
        parts.append("-".join(hyphen_parts))
    return " ".join(parts)
