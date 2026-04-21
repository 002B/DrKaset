"""
DrKaset — Record Validator
===========================
is_record_in_scope():
  - กรองเฉพาะ 14 พืชเป้าหมาย
  - validate required fields
  - กรอง records ที่ไม่มีข้อมูลเพียงพอ
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

# ถ้า record มีคำเหล่านี้ แต่ไม่ใช่พืชในขอบเขต ให้ตัดทิ้ง
NON_SCOPE_HINTS = [
    "หมู", "ไก่", "ปลา", "กุ้ง", "ปศุสัตว์", "livestock",
    "fertilizer", "ปุ๋ย", "pesticide", "ยาฆ่าแมลง",
    "รถ", "เครื่องจักร", "machinery",
    "สต็อค", "stock market", "ตลาดหุ้น",
]

# min text length สำหรับ embedding
MIN_TEXT_LENGTH = 10


class RecordValidator:
    """
    Validate และ filter records ให้อยู่ใน scope ของ DrKaset

    ใช้งาน:
        validator = RecordValidator(cfg)
        ok        = validator.is_in_scope(record)
    """

    def __init__(self, cfg: dict):
        self.target_crops    = cfg.get("target_crops", [])
        # lowercase set สำหรับ lookup เร็ว
        self._crop_set = {c.lower() for c in self.target_crops}

    def is_in_scope(self, record: dict) -> bool:
        """
        Return True ถ้า record ผ่านการ validate ทั้งหมด

        Checks:
          1. ต้องมี text หรือ fields ที่ embed ได้
          2. text ต้องยาวเพียงพอ
          3. ถ้ามี crop field ต้องอยู่ใน 14 พืชเป้าหมาย
          4. ต้องไม่มี non-scope hints ที่ชัดเจน
        """
        # 1. ต้องมีข้อมูล embed ได้
        if not self._has_embeddable_content(record):
            return False

        # 2. ตรวจ text length
        text = record.get("text", "")
        if isinstance(text, str) and text and len(text) < MIN_TEXT_LENGTH:
            return False

        # 3. ตรวจ crop scope (ถ้ามี crop field)
        crop_val = record.get("crop")
        if crop_val is not None:
            if not self._crop_in_scope(str(crop_val)):
                return False
        else:
            # ไม่มี crop field — ตรวจใน text ว่ามี crop ที่ถูกต้องไหม
            if not self._text_mentions_target_crop(record):
                # source type บางอย่างไม่จำเป็นต้องมี crop (เช่น weather)
                src = record.get("_source_type", "")
                if src in ("api_weather", "api_fao", "hf_dataset"):
                    pass  # allow
                else:
                    return False

        # 4. non-scope hints check
        if self._has_non_scope_content(record):
            return False

        return True

    def validate_fields(self, record: dict) -> dict[str, list[str]]:
        """
        Return dict ของ field → list of issues
        ใช้สำหรับ logging / audit
        """
        issues: dict[str, list[str]] = {}

        text = record.get("text", "")
        if not text or (isinstance(text, str) and len(text) < MIN_TEXT_LENGTH):
            issues.setdefault("text", []).append("text สั้นหรือว่าง")

        price = record.get("price")
        if price is not None:
            try:
                p = float(price)
                if p < 0:
                    issues.setdefault("price", []).append("ราคาติดลบ")
                if p > 1_000_000:
                    issues.setdefault("price", []).append("ราคาสูงผิดปกติ")
            except (TypeError, ValueError):
                issues.setdefault("price", []).append(f"price ไม่ใช่ตัวเลข: {price}")

        return issues

    # ── Private helpers ────────────────────────────────────────────────────────

    def _has_embeddable_content(self, record: dict) -> bool:
        """ต้องมี text หรือ fields ที่สร้าง text ได้"""
        if record.get("text"):
            return True
        # มี meaningful fields
        useful_keys = {"crop", "price", "region", "yield", "season", "variety", "province"}
        return bool(useful_keys & record.keys())

    def _crop_in_scope(self, crop_val: str) -> bool:
        crop_lower = crop_val.lower().strip()
        # exact match
        if crop_lower in self._crop_set:
            return True
        # partial match
        return any(tc in crop_lower or crop_lower in tc for tc in self._crop_set)

    def _text_mentions_target_crop(self, record: dict) -> bool:
        """ตรวจใน text + all string values ว่ามีพืชเป้าหมายไหม"""
        all_text = " ".join(
            str(v) for v in record.values()
            if isinstance(v, str)
        ).lower()
        return any(tc.lower() in all_text for tc in self.target_crops)

    def _has_non_scope_content(self, record: dict) -> bool:
        """ตรวจว่า record พูดถึง non-scope content ที่ชัดเจนไหม"""
        all_text = " ".join(
            str(v) for v in record.values()
            if isinstance(v, str)
        ).lower()

        # ถ้ามี non-scope hint และ ไม่มี crop ใดๆ ของเราเลย
        has_hint = any(hint.lower() in all_text for hint in NON_SCOPE_HINTS)
        has_crop = any(tc.lower() in all_text for tc in self.target_crops)

        return has_hint and not has_crop
