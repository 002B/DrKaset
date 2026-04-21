from __future__ import annotations
from typing import AsyncGenerator
import ollama

from core.config import settings
from core.crop_constants import TEMPERATURE, TOP_K, TOP_K_COMPARE
from rag.intent_detector import (
    detect_intent, detect_crop, detect_crop_in_text, detect_region_from_text, is_in_scope
)
from rag.retriever import retrieve
from rag.prompt_builder import (
    build_profit_prompt, build_compare_prompt,
    build_knowledge_prompt, build_fallback_prompt,
)


def _build_messages(system: str, user: str) -> list[dict]:
    return [
        {"role": "system", "content": system},
        {"role": "user",   "content": user},
    ]


async def stream_response(query: str) -> AsyncGenerator[str, None]:
    """
    Full RAG pipeline → yield token strings via async generator.
    Uses ollama Python library (ollama.chat with stream=True).
    """
    # 1. Scope check
    if not is_in_scope(query):
        yield "ขออภัย ระบบรองรับเฉพาะพืช 14 ชนิดเป้าหมายเท่านั้น กรุณาถามเกี่ยวกับพืชในรายการ"
        return

    # 2. Detect intent + crop + region
    intent  = detect_intent(query)
    crop    = detect_crop(query)
    region  = detect_region_from_text(query)
    crops   = detect_crop_in_text(query)

    # 3. Retrieve context from FAISS
    k = TOP_K_COMPARE if intent == "compare" else TOP_K
    docs = retrieve(query, crop=crop, region=region, k=k)

    # 4. Build prompt
    if not docs:
        system, user = build_fallback_prompt(query)
    elif intent == "compare":
        system, user = build_compare_prompt(query, docs, crops)
    elif intent == "profit":
        system, user = build_profit_prompt(query, docs, crop)
    else:
        system, user = build_knowledge_prompt(query, docs)

    messages = _build_messages(system, user)

    # 5. Stream from Ollama using Python lib
    stream = ollama.chat(
        model=settings.OLLAMA_MODEL,
        messages=messages,
        options={"temperature": TEMPERATURE},
        stream=True,
    )

    for chunk in stream:
        token = chunk["message"]["content"]
        if token:
            yield token


def get_intent(query: str) -> str:
    return detect_intent(query)
