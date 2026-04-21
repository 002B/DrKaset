from __future__ import annotations

SYSTEM_BASE = (
    "คุณคือ DrKaset ผู้ช่วยด้านการเกษตรสำหรับเกษตรกรไทย "
    "ตอบเป็นภาษาไทยเสมอ กระชับ ชัดเจน อ้างอิงจากข้อมูลที่ให้มาเท่านั้น "
    "ถ้าไม่มีข้อมูล ให้บอกตรงๆ ว่าไม่ทราบ"
)


def _context_block(docs: list[dict]) -> str:
    if not docs:
        return "(ไม่พบข้อมูลที่เกี่ยวข้องในฐานข้อมูล)"
    parts = []
    for i, d in enumerate(docs, 1):
        meta = d.get("metadata", {})
        src = meta.get("source_type", "")
        crop = meta.get("crop", "")
        region = meta.get("region", "")
        label = " | ".join(filter(None, [crop, region, src]))
        parts.append(f"[{i}] {label}\n{d['content']}")
    return "\n\n".join(parts)


def build_profit_prompt(query: str, docs: list[dict], crop: str | None) -> tuple[str, str]:
    context = _context_block(docs)
    system = SYSTEM_BASE
    user = (
        f"คำถาม: {query}\n\n"
        f"ข้อมูลอ้างอิง:\n{context}\n\n"
        "กรุณาวิเคราะห์ความคุ้มค่าและกำไรโดยอ้างอิงข้อมูลด้านบน"
    )
    return system, user


def build_compare_prompt(query: str, docs: list[dict], crops: list[str]) -> tuple[str, str]:
    context = _context_block(docs)
    crop_str = " และ ".join(crops) if crops else "พืชที่ถามถึง"
    system = SYSTEM_BASE
    user = (
        f"คำถาม: {query}\n\n"
        f"ข้อมูลอ้างอิง:\n{context}\n\n"
        f"กรุณาเปรียบเทียบ {crop_str} ในแง่ที่ถามถึง พร้อมสรุปข้อดี-ข้อเสีย"
    )
    return system, user


def build_knowledge_prompt(query: str, docs: list[dict]) -> tuple[str, str]:
    context = _context_block(docs)
    system = SYSTEM_BASE
    user = (
        f"คำถาม: {query}\n\n"
        f"ข้อมูลอ้างอิง:\n{context}\n\n"
        "กรุณาตอบคำถามโดยอ้างอิงข้อมูลด้านบน"
    )
    return system, user


def build_fallback_prompt(query: str) -> tuple[str, str]:
    system = SYSTEM_BASE
    user = (
        f"คำถาม: {query}\n\n"
        "ไม่พบข้อมูลที่ตรงกับคำถามในฐานข้อมูล "
        "กรุณาแจ้งผู้ใช้ว่าไม่มีข้อมูลและแนะนำให้ถามเรื่องพืช 14 ชนิดที่ระบบรองรับ"
    )
    return system, user
