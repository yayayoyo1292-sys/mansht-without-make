
from __future__ import annotations

import os
import re
import unicodedata
from typing import Optional

import joblib


_BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
_MODEL_PATH = os.path.join(_BASE_DIR, "model.pkl")
_VEC_PATH   = os.path.join(_BASE_DIR, "vectorizer.pkl")

_model      = joblib.load(_MODEL_PATH)
_vectorizer = joblib.load(_VEC_PATH)


_LABEL_MAP: dict = {
    "سياسة":    1,
    "سياسه":    1,
    "politics": 1,
    1:           1,
    "عام":      0,
    "اجتماعية": 0,
    "اجتماعيه": 0,
    "رياضة":    0,
    "فن":       0,
    "general":  0,
    0:           0,
}

CONFIDENCE_THRESHOLD: float = 0.40


def normalize_arabic(text: str) -> str:
    text = str(text)
    text = re.sub(r"[إأآا]", "ا", text)
    text = re.sub(r"ى",      "ي", text)
    text = re.sub(r"ؤ",      "و", text)
    text = re.sub(r"ئ",      "ي", text)
    text = re.sub(r"ة",      "ه", text)
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\d+",    " ", text)
    text = re.sub(r"\s+",    " ", text)
    return text.strip()



def classify_political(
    title: str,
    content: Optional[str] = None,
) -> tuple[int, float]:

    text = normalize_arabic(title)
    if content:
        text += " " + normalize_arabic(content)

    try:
        X      = _vectorizer.transform([text])
        probs  = _model.predict_proba(X)[0]
        classes = _model.classes_

        best_idx    = int(probs.argmax())
        raw_label   = classes[best_idx]
        confidence  = float(probs[best_idx])

        label = _LABEL_MAP.get(raw_label, 0)

        if confidence < CONFIDENCE_THRESHOLD:
            return 0, confidence

        return label, confidence

    except Exception as exc:
        import logging
        logging.getLogger(__name__).error(f"❌ Classifier error: {exc}")
        return 0, 0.0


def get_template_key(label: int) -> str:
    """Map binary label to template key string."""
    from config.settings import AI_TEMPLATE_MAP
    return AI_TEMPLATE_MAP.get(label, "عام")



def classify_news(
    title: str,
    content: Optional[str] = None,
) -> tuple[Optional[str], float]:

    label, conf = classify_political(title, content)
    arabic = "سياسة" if label == 1 else "عام"
    return arabic, conf
