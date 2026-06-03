
from __future__ import annotations

IMPORTANT_ENTITIES = [
    "محمد بن زايد",
    "محمد بن راشد",
    "ولي عهد",
    "الإمارات",
    "رئيس الدولة",
]


def calculate_ai_score(title: str, content: str = "") -> int:
    text  = f"{title} {content}"
    score = 0
    for entity in IMPORTANT_ENTITIES:
        if entity in text:
            score += 3
    if len(text) > 500:
        score += 1
    return score
