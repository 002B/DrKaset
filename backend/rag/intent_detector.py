from __future__ import annotations
from core.crop_constants import CROP_ALIAS_MAP, REGION_KEYWORDS, NON_SCOPE_CROP_HINTS
import re

PROFIT_KEYWORDS = [
    "กำไร", "ต้นทุน", "รายได้", "ผลตอบแทน", "คุ้มไหม", "คุ้มค่า",
    "profit", "cost", "return", "revenue",
]
COMPARE_KEYWORDS = [
    "เปรียบเทียบ", "เทียบ", "vs", "versus", "ดีกว่า", "compare",
    "ต่างกัน", "แตกต่าง",
]
KNOWLEDGE_KEYWORDS = [
    "วิธี", "ปลูก", "เก็บเกี่ยว", "โรค", "แมลง", "ดูแล", "ใส่ปุ๋ย",
    "how to", "plant", "harvest", "disease", "pest", "fertilize",
]


def detect_intent(text: str) -> str:
    t = text.lower()
    if any(k in t for k in COMPARE_KEYWORDS):
        return "compare"
    if any(k in t for k in PROFIT_KEYWORDS):
        return "profit"
    if any(k in t for k in KNOWLEDGE_KEYWORDS):
        return "knowledge"
    return "knowledge"   # default


def detect_crop(text: str) -> str | None:
    t = text.lower()
    for alias, canonical in CROP_ALIAS_MAP.items():
        if alias in t:
            return canonical
    return None


def detect_crop_in_text(text: str) -> list[str]:
    t = text.lower()
    found: list[str] = []
    for alias, canonical in CROP_ALIAS_MAP.items():
        if alias in t and canonical not in found:
            found.append(canonical)
    return found


def detect_region_from_text(text: str) -> str | None:
    t = text.lower()
    for region, keywords in REGION_KEYWORDS.items():
        if any(k in t for k in keywords):
            return region
    return None


def is_in_scope(text: str) -> bool:
    """Return False if the query is clearly about non-target crops."""
    t = text.lower()
    if any(hint in t for hint in NON_SCOPE_CROP_HINTS):
        return False
    return True
