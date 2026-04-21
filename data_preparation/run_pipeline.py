#!/usr/bin/env python3
"""
DrKaset — Data Preparation Pipeline CLI
========================================
Usage:
    python run_pipeline.py --step all
    python run_pipeline.py --step load
    python run_pipeline.py --step clean
    python run_pipeline.py --step embed
"""

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import Optional

import yaml

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# ── Setup logging ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("pipeline.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("run_pipeline")

CONFIG_PATH = Path(__file__).parent / "config.yaml"


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ── Step functions ─────────────────────────────────────────────────────────────

def step_load(cfg: dict) -> list[dict]:
    """โหลดและ parse ไฟล์ทั้งหมดใน data/raw/"""
    from input_files.loader import DataLoader

    raw_dir = Path(cfg["paths"]["raw_dir"])
    if not raw_dir.exists():
        logger.warning(f"raw_dir ไม่มีอยู่ — สร้าง {raw_dir}")
        raw_dir.mkdir(parents=True, exist_ok=True)

    loader = DataLoader(cfg)
    files  = list(raw_dir.rglob("*"))
    files  = [f for f in files if f.is_file() and not f.name.startswith(".")]

    if not files:
        logger.warning("ไม่พบไฟล์ใน data/raw/ - กรุณาใส่ไฟล์ข้อมูลเองก่อน")
        return []

    logger.info(f"พบ {len(files)} ไฟล์ -> เริ่มอ่านไฟล์จาก data/raw")
    all_records: list[dict] = []
    for fp in files:
        try:
            records = loader.load(fp)
            logger.info(f"  ✓ {fp.name} → {len(records)} records")
            all_records.extend(records)
        except Exception as e:
            logger.error(f"  ✗ {fp.name} — {e}")

    logger.info(f"อ่านไฟล์เสร็จ: {len(all_records)} records รวม")
    return all_records



def step_clean(cfg: dict, records: list[dict]) -> list[dict]:
    """Clean + Normalize + Validate records"""
    from cleansing.cleaner    import TextCleaner
    from cleansing.normalizer import RecordNormalizer
    from cleansing.validator  import RecordValidator

    if not records:
        logger.warning("ไม่มี records ให้ clean — ข้ามขั้นตอน")
        return []

    cleaner    = TextCleaner()
    normalizer = RecordNormalizer(cfg)
    validator  = RecordValidator(cfg)

    cleaned: list[dict] = []
    skipped = 0

    for rec in records:
        try:
            rec_clean = cleaner.clean_record(rec)
            rec_norm  = normalizer.normalize(rec_clean)
            if validator.is_in_scope(rec_norm):
                cleaned.append(rec_norm)
            else:
                skipped += 1
        except Exception as e:
            logger.debug(f"Clean error: {e}")
            skipped += 1

    logger.info(f"Clean เสร็จ: {len(cleaned)} valid / {skipped} skipped")

    # ── บันทึก processed records ──
    import json
    processed_dir = Path(cfg["paths"]["processed_dir"])
    processed_dir.mkdir(parents=True, exist_ok=True)
    out_path = processed_dir / "records.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)
    logger.info(f"บันทึก processed records → {out_path}")

    return cleaned


def step_embed(cfg: dict, records: Optional[list[dict]] = None) -> None:
    """Embed records → FAISS index"""
    import json
    from rag_pipeline.chunker  import RecordChunker
    from rag_pipeline.embedder import DrKasetEmbedder
    from rag_pipeline.indexer  import FAISSIndexer

    # ถ้าไม่มี records ส่งมา ให้อ่านจาก processed/records.json
    if records is None:
        processed_path = Path(cfg["paths"]["processed_dir"]) / "records.json"
        if not processed_path.exists():
            logger.error("ไม่พบ processed/records.json — รัน --step clean ก่อน")
            return
        with open(processed_path, "r", encoding="utf-8") as f:
            records = json.load(f)
        logger.info(f"โหลด {len(records)} records จาก {processed_path}")

    if not records:
        logger.warning("ไม่มี records ให้ embed")
        return

    chunker  = RecordChunker(cfg)
    embedder = DrKasetEmbedder(cfg)
    indexer  = FAISSIndexer(cfg)

    logger.info("กำลัง chunk records...")
    docs = chunker.chunk_records(records)
    logger.info(f"chunk เสร็จ: {len(docs)} chunks")

    logger.info("กำลัง build FAISS index...")
    indexer.build_index(docs, embedder.get_embedding_fn())

    faiss_dir = Path(cfg["paths"]["faiss_dir"])
    indexer.save(str(faiss_dir))
    logger.info(f"บันทึก FAISS index → {faiss_dir}")
    logger.info("✅ Embed เสร็จสมบูรณ์")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="DrKaset Data Preparation Pipeline",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--step",
        choices=["all", "load", "clean", "embed"],
        default="all",
        help=(
            "ขั้นตอนที่จะรัน:\n"
            "  all   - อ่านไฟล์จาก data/raw + clean + embed\n"
            "  load  - อ่านไฟล์จาก data/raw/\n"
            "  clean - clean + normalize + validate\n"
            "  embed - embed -> FAISS index\n"
        ),
    )
    args = parser.parse_args()

    cfg = load_config()
    logger.info(f"DrKaset Pipeline เริ่มต้น — step={args.step}")
    t0 = time.time()

    records: list[dict] = []
    if args.step == "load":
        step_load(cfg)

    elif args.step == "clean":
        # อ่าน records จาก processed ถ้ามี
        import json
        processed_path = Path(cfg["paths"]["processed_dir"]) / "records.json"
        if processed_path.exists():
            with open(processed_path, "r", encoding="utf-8") as f:
                records = json.load(f)
        else:
            records = step_load(cfg)
        step_clean(cfg, records)

    elif args.step == "embed":
        step_embed(cfg)

    elif args.step == "all":
        # 1. load manually added local files
        records = step_load(cfg)

        # 3. clean
        cleaned = step_clean(cfg, records)

        # 4. embed
        step_embed(cfg, cleaned)

    elapsed = time.time() - t0
    logger.info(f"Pipeline เสร็จสิ้น ใช้เวลา {elapsed:.1f}s")


if __name__ == "__main__":
    main()

