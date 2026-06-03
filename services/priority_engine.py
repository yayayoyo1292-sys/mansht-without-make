
from __future__ import annotations

import re
import time
import unicodedata
from typing import Optional

from config.settings import AGING_MULTIPLIER
from utils.logger import logger



_KEYWORD_TIERS: list[tuple[int, list[str]]] = [

    
    (20, [
        "رئيس الدولة",
        "محمد بن زايد",
        "محمد بن زايد آل نهيان",
        "محمد بن راشد",
        "محمد بن راشد آل مكتوم",
        "منصور بن زايد",
        "منصور بن زايد آل نهيان",
        "الشيخة فاطمة",
        "أم الإمارات",
        "الشيخ زايد",
    ]),

   
    (15, [
        "سلطان القاسمي",
        "حمد الشرقي",
        "حميد بن راشد",
        "سعود بن صقر",
        "سعود المعلا",
        "خالد بن محمد بن زايد",
        "حمدان بن محمد",
        "حمدان بن زايد",
        "سيف بن زايد",
        "عبدالله بن زايد",
        "طحنون بن زايد",
        "ذياب بن محمد بن زايد",
        "هزاع بن زايد",
        "نهيان بن زايد",
        "نهيان بن مبارك",
        "زايد بن محمد بن زايد",
        "خالد بن زايد",
        "شخبوط بن نهيان",
        "مكتوم بن محمد",
        "أحمد بن محمد",
        "منصور بن محمد",
        "عمار بن حميد",
        "محمد بن سعود",
        "محمد الشرقي",
        "أنور قرقاش",
        "ثاني الزيودي",
        "لطيفة بنت محمد",
        "حمدان بن محمد زايد",
        "صقر غباش",
        "عبدالله آل حامد",
        "أحمد بن راشد المعلا",
        "سلطان النيادي",
    ]),

    
    (11, [
        "الإمارات",
        "مجلس الوزراء",
        "حكام الإمارات",
        "حكومة الإمارات",
        "المجلس التنفيذي",
        "تنفيذي أبوظبي",
        "الوطني الاتحادي",
        "اليوم الوطني",
        "يوم الشهيد",
        "المرأة الإماراتية",
        "التوازن بين الجنسين",
        "التنمية الأسرية",
        "الاتحاد النسائي",
        "حكماء المسلمين",
        "وساطة إماراتية",
        "الدفاعات الجوية الإماراتية",
        "الفارس الشهم",
        "المساعدات الإنسانية",
        "صندوق أبوظبي",
        "براكة",
        "حاكم",
    ]),

    
    (8, [
        "شرطة أبوظبي",
        "شرطة دبي",
        "شرطة الشارقة",
        "صحة أبوظبي",
        "صحة دبي",
        "بيئة أبوظبي",
        "بلدية أبوظبي",
        "النقل الذكي",
        "الاتحاد للطيران",
        "طيران الإمارات",
        "موانئ أبوظبي",
        "أبوظبي العالمي",
        "القطاع العقاري",
        "النفط",
        "الذهب",
        "الدولار",
        "الذكاء الاصطناعي",
        "الأمن السيبراني",
        "الفضاء",
        "سماء الإمارات",
        "منتخب الإمارات",
        "منتخبنا الوطني",
        "كأس الإمارات",
        "دوري",
        "فروسية",
        "هجن",
        "خيول",
        "سباق زايد الخيري",
        "أبوظبي للرياضات البحرية",
        "فرسان الإمارات",
        "وزير الرياضة",
        "بطولة",
        "يدين",
        "تدين",
        "اليوم الدولي",
        "اليوم العالمي",
        "متحف",
        "متاحف",
    ]),

   
    (5, [
        "أبوظبي",
        "دبي",
        "الشارقة",
        "الجزيرة",
        "العين",
        "ولي عهد",
        "نائب حاكم",
        "وزير",
        "الأبيض",
        "أول",
        "الأولى",
        "أكبر",
    ]),
]



_KW_MAP: dict[str, tuple[int, int]] = {}
for tier_idx, (tier_score, keywords) in enumerate(_KEYWORD_TIERS, start=1):
    for kw in keywords:
        if kw not in _KW_MAP:   # first/highest tier wins
            _KW_MAP[kw] = (tier_score, tier_idx)


_NAMED_ENTITIES: list[str] = [
    "محمد بن زايد",
    "محمد بن راشد",
    "منصور بن زايد",
    "ولي عهد",
    "الإمارات",
    "حاكم",
    "رئيس الدولة",
    "مجلس الوزراء",
]



def _normalize(text: str) -> str:

    text = unicodedata.normalize("NFC", str(text or ""))
    # Strip Arabic diacritics (U+064B – U+065F, U+0670)
    text = re.sub(r"[\u064B-\u065F\u0670]", "", text)
    return text.strip()



def calculate_priority_score(
    title: str,
    content: str = "",
) -> int:
    
    text    = _normalize(f"{title} {content}")
    highest = 0
    for kw, (score, _tier) in _KW_MAP.items():
        if _normalize(kw) in text:
            if score > highest:
                highest = score
    return highest


def calculate_keyword_score(
    title: str,
    content: str = "",
) -> int:

    text  = _normalize(f"{title} {content}")
    score = 0
    seen  : set[str] = set()   
    for kw, (kw_score, _tier) in _KW_MAP.items():
        nkw = _normalize(kw)
        if nkw not in seen and nkw in text:
            score += kw_score
            seen.add(nkw)
    return score


def explain_priority(
    title: str,
    content: str = "",
) -> dict:

    from config.settings import PRIORITY_THRESHOLD_INSTAGRAM

    text    = _normalize(f"{title} {content}")
    matched = []
    seen    : set[str] = set()

    for kw, (kw_score, tier) in _KW_MAP.items():
        nkw = _normalize(kw)
        if nkw not in seen and nkw in text:
            matched.append({"keyword": kw, "score": kw_score, "tier": tier})
            seen.add(nkw)

    matched.sort(key=lambda m: (-m["score"], m["tier"]))

    priority_score = max((m["score"] for m in matched), default=0)
    keyword_score  = sum(m["score"] for m in matched)
    eligible       = priority_score >= PRIORITY_THRESHOLD_INSTAGRAM

    if not matched:
        reason = "No priority keywords matched — normal routing (Facebook + Twitter)"
    elif eligible:
        top_kw = matched[0]
        reason = (
            f"Matched '{top_kw['keyword']}' (Tier {top_kw['tier']}, "
            f"score={top_kw['score']}) → Instagram-eligible"
        )
    else:
        top_kw = matched[0]
        reason = (
            f"Best match '{top_kw['keyword']}' (Tier {top_kw['tier']}, "
            f"score={top_kw['score']}) below Instagram threshold "
            f"({PRIORITY_THRESHOLD_INSTAGRAM}) → Facebook + Twitter"
        )

    return {
        "priority_score":     priority_score,
        "keyword_score":      keyword_score,
        "matched":            matched,
        "instagram_eligible": eligible,
        "reason":             reason,
    }


def log_priority_decision(title: str, content: str = "") -> int:

    from config.settings import PRIORITY_THRESHOLD_INSTAGRAM

    exp = explain_priority(title, content)
    ps  = exp["priority_score"]

    if exp["matched"]:
        kw_list = ", ".join(
            f"'{m['keyword']}'={m['score']}" for m in exp["matched"][:5]
        )
        logger.info(
            f"🏷️  Priority | score={ps} | "
            f"{'🔴 INSTAGRAM' if exp['instagram_eligible'] else '🔵 FB+TW'} | "
            f"matched=[{kw_list}] | {title[:70]}"
        )
    else:
        logger.info(f"🏷️  Priority | score=0 | 🔵 FB+TW | no match | {title[:70]}")

    if exp["instagram_eligible"]:
        logger.info(f"   ↳ Reason: {exp['reason']}")

    return ps



def calculate_aging_bonus(created_at: float, now: Optional[float] = None) -> float:

    if now is None:
        now = time.time()
    age_minutes = max(0.0, (now - created_at) / 60)
    return age_minutes * AGING_MULTIPLIER


def calculate_ai_score(title: str, content: str = "") -> int:

    text  = _normalize(f"{title} {content}")
    score = 0
    for entity in _NAMED_ENTITIES:
        if _normalize(entity) in text:
            score += 3
    if len(text) > 500:
        score += 1  
    return score


def calculate_final_score(
    title: str,
    content: str,
    created_at: float,
) -> dict:

    keyword_score = calculate_keyword_score(title, content)
    aging_score   = calculate_aging_bonus(created_at)
    ai_score      = calculate_ai_score(title, content)
    final_score   = keyword_score + aging_score + ai_score

    return {
        "keyword_score": keyword_score,
        "aging_score":   aging_score,
        "ai_score":      ai_score,
        "final_score":   final_score,
    }
