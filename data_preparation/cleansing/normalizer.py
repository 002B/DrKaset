"""
DrKaset — Record Normalizer
============================
normalize_record_from_row():
  - map column aliases → canonical field names
  - normalize หน่วย (บาท/กก., บาท/ตัน, USD/tonne → บาท/กก.)
  - normalize crop key → ชื่อมาตรฐาน
  - สร้าง text field สำหรับ embedding ถ้ายังไม่มี
"""

import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ── Crop aliases ───────────────────────────────────────────────────────────────
# map ชื่อหลายรูปแบบ → ชื่อมาตรฐาน

CROP_ALIAS_MAP: dict[str, str] = {
    # ข้าว
    "ข้าว": "ข้าว", "ข้าวเจ้า": "ข้าว", "ข้าวหอมมะลิ": "ข้าว",
    "rice": "ข้าว", "paddy": "ข้าว",
    # ข้าวโพด
    "ข้าวโพด": "ข้าวโพด", "ข้าวโพดเลี้ยงสัตว์": "ข้าวโพด",
    "maize": "ข้าวโพด", "corn": "ข้าวโพด",
    # มันสำปะหลัง
    "มันสำปะหลัง": "มันสำปะหลัง", "มัน": "มันสำปะหลัง",
    "cassava": "มันสำปะหลัง", "tapioca": "มันสำปะหลัง",
    # อ้อย
    "อ้อย": "อ้อย", "อ้อยโรงงาน": "อ้อย",
    "sugarcane": "อ้อย", "sugar cane": "อ้อย",
    # ยางพารา
    "ยางพารา": "ยางพารา", "ยาง": "ยางพารา", "ยางแผ่น": "ยางพารา",
    "rubber": "ยางพารา", "natural rubber": "ยางพารา",
    # ปาล์มน้ำมัน
    "ปาล์มน้ำมัน": "ปาล์มน้ำมัน", "ปาล์ม": "ปาล์มน้ำมัน",
    "palm oil": "ปาล์มน้ำมัน", "oil palm": "ปาล์มน้ำมัน",
    # สับปะรด
    "สับปะรด": "สับปะรด", "pineapple": "สับปะรด",
    # ลำไย
    "ลำไย": "ลำไย", "longan": "ลำไย",
    # ทุเรียน
    "ทุเรียน": "ทุเรียน", "durian": "ทุเรียน",
    # มังคุด
    "มังคุด": "มังคุด", "mangosteen": "มังคุด",
    # กล้วย
    "กล้วย": "กล้วย", "กล้วยหอม": "กล้วย", "banana": "กล้วย",
    # มะพร้าว
    "มะพร้าว": "มะพร้าว", "coconut": "มะพร้าว",
    # ถั่วเหลือง
    "ถั่วเหลือง": "ถั่วเหลือง", "soybean": "ถั่วเหลือง",
    # ถั่วเขียว
    "ถั่วเขียว": "ถั่วเขียว", "mung bean": "ถั่วเขียว", "mungbean": "ถั่วเขียว",
}

# ── Column aliases ─────────────────────────────────────────────────────────────
# map column name หลายรูปแบบ → canonical field

COLUMN_ALIAS_MAP: dict[str, str] = {
    # crop
    "ชื่อพืช": "crop", "พืช": "crop", "สินค้า": "crop",
    "crop_name": "crop", "commodity": "crop", "item": "crop",
    # price
    "ราคา": "price", "ราคาเฉลี่ย": "price", "ราคา (บาท/กก.)": "price",
    "price_thb": "price", "price_baht": "price",
    "producer_price": "price", "farm_price": "price",
    # unit
    "หน่วย": "unit", "unit_price": "unit",
    # region
    "ภาค": "region", "จังหวัด": "province", "พื้นที่": "region",
    "area": "region",
    # date/time
    "วันที่": "date", "เดือน": "month", "ปี": "year",
    "date_th": "date",
    # yield
    "ผลผลิต": "yield", "yield_kg": "yield", "production": "yield",
    # season
    "ฤดูกาล": "season", "ฤดู": "season",
    # variety
    "พันธุ์": "variety", "สายพันธุ์": "variety",
}

# ── Unit conversion ────────────────────────────────────────────────────────────
# อัตราแลกเปลี่ยนคร่าวๆ สำหรับ normalize ราคา → บาท/กก.

UNIT_CONVERSION: dict[str, float] = {
    "บาท/กก.":  1.0,
    "บาท/ตัน":  0.001,
    "บาท/100กก.": 0.01,
    "usd/tonne": 35.0 * 0.001,  # USD→THB ~35, tonne→kg /1000
    "$/tonne":   35.0 * 0.001,
    "thb/kg":    1.0,
    "thb/tonne": 0.001,
}

# ── Region normalization ───────────────────────────────────────────────────────

REGION_MAP: dict[str, str] = {
    "เหนือ": "ภาคเหนือ", "ภาคเหนือ": "ภาคเหนือ", "north": "ภาคเหนือ",
    "ใต้":   "ภาคใต้",  "ภาคใต้":  "ภาคใต้",  "south": "ภาคใต้",
    "ตะวันออกเฉียงเหนือ": "ภาคตะวันออกเฉียงเหนือ",
    "อีสาน": "ภาคตะวันออกเฉียงเหนือ", "northeast": "ภาคตะวันออกเฉียงเหนือ",
    "กลาง":  "ภาคกลาง", "ภาคกลาง": "ภาคกลาง", "central": "ภาคกลาง",
    "ตะวันออก": "ภาคตะวันออก", "east": "ภาคตะวันออก",
    "ตะวันตก":  "ภาคตะวันตก",  "west": "ภาคตะวันตก",
}


# ── Helper ─────────────────────────────────────────────────────────────────────

def _to_number(val: Any) -> Optional[float]:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    try:
        s = re.sub(r"[,\s]", "", str(val))
        return float(s)
    except (ValueError, TypeError):
        return None


def _normalize_crop(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    raw_clean = raw.strip().lower()
    # exact match
    for alias, canonical in CROP_ALIAS_MAP.items():
        if raw_clean == alias.lower():
            return canonical
    # partial match
    for alias, canonical in CROP_ALIAS_MAP.items():
        if alias.lower() in raw_clean:
            return canonical
    return raw.strip()


def _normalize_region(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    raw_clean = raw.strip().lower()
    for alias, canonical in REGION_MAP.items():
        if alias.lower() in raw_clean:
            return canonical
    return raw.strip()


def _normalize_price(price: Any, unit: Optional[str]) -> Optional[float]:
    """แปลง price → บาท/กก."""
    numeric = _to_number(price)
    if numeric is None:
        return None
    if not unit:
        return numeric  # assume already บาท/กก.

    unit_lower = unit.strip().lower()
    for u, factor in UNIT_CONVERSION.items():
        if u.lower() in unit_lower:
            return round(numeric * factor, 4)

    return numeric  # ไม่รู้ unit — return as-is


def _build_text(record: dict) -> str:
    """สร้าง text สำหรับ embedding"""
    parts: list[str] = []

    crop   = record.get("crop")
    region = record.get("region")
    price  = record.get("price")
    unit   = record.get("unit", "บาท/กก.")
    date   = record.get("date") or record.get("year")
    text   = record.get("text")

    # ถ้ามี text อยู่แล้ว ให้ใช้
    if text and isinstance(text, str) and len(text) > 20:
        return text

    if crop:
        parts.append(f"พืช: {crop}")
    if region:
        parts.append(f"พื้นที่: {region}")
    if price is not None:
        parts.append(f"ราคา: {price} {unit}")
    if date:
        parts.append(f"วันที่: {date}")

    # season / variety
    for field in ["season", "variety", "province", "yield"]:
        val = record.get(field)
        if val:
            parts.append(f"{field}: {val}")

    # source_type context
    src = record.get("_source_type", "")
    if src == "pdf":
        # สำหรับ PDF ใช้ text ดิบ
        raw_text = record.get("text", "")
        if raw_text:
            return raw_text[:800]

    return " | ".join(parts) if parts else ""


# ── Main Normalizer ────────────────────────────────────────────────────────────

class RecordNormalizer:
    """
    Normalize record dict ให้เป็น canonical format

    ใช้งาน:
        normalizer = RecordNormalizer(cfg)
        norm_rec   = normalizer.normalize(record)
    """

    def __init__(self, cfg: dict):
        self.cfg = cfg

    def normalize(self, record: dict) -> dict:
        normalized: dict = {}

        # 1. map column aliases
        for key, val in record.items():
            canonical_key = COLUMN_ALIAS_MAP.get(key, key)
            normalized[canonical_key] = val

        # 2. normalize crop
        raw_crop = normalized.get("crop")
        if raw_crop:
            normalized["crop"] = _normalize_crop(str(raw_crop))

        # 3. normalize region
        raw_region = normalized.get("region")
        if raw_region:
            normalized["region"] = _normalize_region(str(raw_region))

        # 4. normalize price + unit
        raw_price = normalized.get("price")
        raw_unit  = normalized.get("unit")
        if raw_price is not None:
            normalized["price"]      = _normalize_price(raw_price, raw_unit)
            normalized["price_unit"] = "บาท/กก."

        # 5. สร้าง/update text field
        text = _build_text(normalized)
        if text:
            normalized["text"] = text

        # 6. ล้าง None values
        normalized = {k: v for k, v in normalized.items() if v is not None}

        return normalized
