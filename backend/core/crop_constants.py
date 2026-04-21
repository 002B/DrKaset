# ---- 14 พืชเป้าหมาย + aliases ----
TARGET_CROPS = {
    "ข้าว":        ["rice", "ข้าวเจ้า", "ข้าวหอมมะลิ"],
    "ข้าวโพด":     ["corn", "maize", "โพด"],
    "อ้อย":        ["sugarcane", "sugar cane"],
    "มันสำปะหลัง": ["cassava", "tapioca", "มัน"],
    "ยางพารา":     ["rubber", "para rubber"],
    "ปาล์มน้ำมัน": ["oil palm", "palm"],
    "สับปะรด":     ["pineapple"],
    "ทุเรียน":     ["durian"],
    "มังคุด":      ["mangosteen"],
    "ลำไย":        ["longan"],
    "มะม่วง":      ["mango"],
    "กาแฟ":        ["coffee"],
    "ถั่วเหลือง":  ["soybean", "soy"],
    "ถั่วลิสง":    ["peanut", "groundnut"],
}

# Flat alias → canonical key
CROP_ALIAS_MAP: dict[str, str] = {}
for canonical, aliases in TARGET_CROPS.items():
    CROP_ALIAS_MAP[canonical] = canonical
    for alias in aliases:
        CROP_ALIAS_MAP[alias.lower()] = canonical

REGION_KEYWORDS = {
    "เหนือ":     ["เหนือ", "north", "ภาคเหนือ", "เชียงใหม่", "เชียงราย", "ลำปาง"],
    "อีสาน":     ["อีสาน", "northeast", "ภาคอีสาน", "ภาคตะวันออกเฉียงเหนือ", "โคราช", "ขอนแก่น", "อุบล"],
    "กลาง":      ["กลาง", "central", "ภาคกลาง", "กรุงเทพ", "อยุธยา", "ชัยนาท"],
    "ตะวันออก":  ["ตะวันออก", "east", "ภาคตะวันออก", "ระยอง", "จันทบุรี", "ตราด"],
    "ใต้":       ["ใต้", "south", "ภาคใต้", "สุราษฎร์", "นครศรีธรรมราช", "ยะลา"],
    "ตะวันตก":   ["ตะวันตก", "west", "ภาคตะวันตก", "กาญจนบุรี", "ราชบุรี"],
}

NON_SCOPE_CROP_HINTS = [
    "ผัก", "เห็ด", "ดอกไม้", "ต้นไม้ประดับ", "สมุนไพร",
    "herb", "vegetable", "flower", "ornamental",
]

# LLM / RAG config
OLLAMA_MODEL    = "qwen2.5:7b"
TEMPERATURE     = 0.2
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
CHUNK_SIZE      = 900
CHUNK_OVERLAP   = 150
TOP_K           = 8
TOP_K_COMPARE   = 10
