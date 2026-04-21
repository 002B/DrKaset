"""
DrKaset — Data Loader
======================
Auto-detect file type และเรียก parser ที่เหมาะสม

รองรับ:
  - CSV  : try หลาย encodings (utf-8, utf-8-sig, cp874, tis-620, latin1)
  - XLSX : openpyxl, รองรับหลาย sheet
  - PDF  : pypdf page-by-page
  - JSON : list หรือ dict
  - TXT  : อ่าน plain text
  - ZIP  : extract_zip_recursive() รองรับ nested zip
"""

import io
import json
import logging
import zipfile
from pathlib import Path
from typing import Optional

import chardet

logger = logging.getLogger(__name__)

# ── Helpers ────────────────────────────────────────────────────────────────────

def _detect_encoding(raw: bytes) -> str:
    """ตรวจ encoding อัตโนมัติด้วย chardet"""
    result = chardet.detect(raw[:10_000])
    return result.get("encoding") or "utf-8"


def _read_csv_bytes(raw: bytes, encodings: list[str]) -> list[dict]:
    """ลอง encodings ทีละตัว จนอ่านได้"""
    import csv

    # เพิ่ม detected encoding ไว้หัว list
    detected = _detect_encoding(raw)
    all_enc = [detected] + [e for e in encodings if e != detected]

    last_err: Optional[Exception] = None
    for enc in all_enc:
        try:
            text = raw.decode(enc, errors="replace")
            reader = csv.DictReader(io.StringIO(text))
            rows = [dict(r) for r in reader]
            if rows:
                logger.debug(f"CSV decoded with {enc}: {len(rows)} rows")
                return rows
        except Exception as e:
            last_err = e
            continue

    raise ValueError(f"ไม่สามารถ decode CSV ได้: {last_err}")


# ── Parsers ────────────────────────────────────────────────────────────────────

class CSVParser:
    def __init__(self, encodings: list[str]):
        self.encodings = encodings

    def parse(self, path: Path) -> list[dict]:
        raw = path.read_bytes()
        rows = _read_csv_bytes(raw, self.encodings)
        return [{"_source_file": path.name, "_source_type": "csv", **r} for r in rows]


class XLSXParser:
    def parse(self, path: Path) -> list[dict]:
        import openpyxl

        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        records: list[dict] = []
        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            rows = list(ws.iter_rows(values_only=True))
            if not rows:
                continue
            headers = [str(h).strip() if h is not None else f"col_{i}"
                       for i, h in enumerate(rows[0])]
            for row in rows[1:]:
                record = {
                    "_source_file": path.name,
                    "_source_type": "xlsx",
                    "_sheet": sheet_name,
                    **{h: v for h, v in zip(headers, row)},
                }
                records.append(record)
        wb.close()
        return records


class PDFParser:
    def __init__(self, max_pages: int = 500):
        self.max_pages = max_pages

    def parse(self, path: Path) -> list[dict]:
        from pypdf import PdfReader

        reader  = PdfReader(str(path))
        records = []
        pages   = reader.pages[: self.max_pages]

        for i, page in enumerate(pages):
            text = page.extract_text() or ""
            text = text.strip()
            if text:
                records.append({
                    "_source_file": path.name,
                    "_source_type": "pdf",
                    "_page":        i + 1,
                    "text":         text,
                })

        return records


class JSONParser:
    def parse(self, path: Path) -> list[dict]:
        raw = path.read_bytes()
        enc = _detect_encoding(raw)
        data = json.loads(raw.decode(enc, errors="replace"))

        if isinstance(data, list):
            records = data
        elif isinstance(data, dict):
            # ถ้าเป็น dict ให้หา key ที่ value เป็น list
            for v in data.values():
                if isinstance(v, list) and v and isinstance(v[0], dict):
                    records = v
                    break
            else:
                records = [data]
        else:
            raise ValueError(f"JSON format ไม่รองรับ: {type(data)}")

        return [{"_source_file": path.name, "_source_type": "json", **r}
                for r in records if isinstance(r, dict)]


class TXTParser:
    def parse(self, path: Path) -> list[dict]:
        raw = path.read_bytes()
        enc = _detect_encoding(raw)
        text = raw.decode(enc, errors="replace").strip()
        if not text:
            return []
        return [{
            "_source_file": path.name,
            "_source_type": "txt",
            "text":         text,
        }]


# ── ZIP recursive extractor ────────────────────────────────────────────────────

def extract_zip_recursive(
    path: Path,
    dest: Path,
    depth: int = 0,
    max_depth: int = 3,
) -> list[Path]:
    """แตก ZIP ซ้อน ZIP จนถึง max_depth"""
    if depth > max_depth:
        logger.warning(f"ZIP depth เกิน {max_depth} — หยุดที่ {path.name}")
        return []

    extracted: list[Path] = []
    try:
        with zipfile.ZipFile(path, "r") as zf:
            zf.extractall(dest)
            for name in zf.namelist():
                member = dest / name
                if member.suffix.lower() == ".zip" and member.is_file():
                    sub_dest = member.parent / member.stem
                    sub_dest.mkdir(parents=True, exist_ok=True)
                    extracted.extend(
                        extract_zip_recursive(member, sub_dest, depth + 1, max_depth)
                    )
                else:
                    extracted.append(member)
    except zipfile.BadZipFile as e:
        logger.error(f"Bad ZIP file {path.name}: {e}")

    return extracted


# ── Main DataLoader ────────────────────────────────────────────────────────────

class DataLoader:
    """
    โหลดไฟล์ทุกชนิดแล้วคืน list[dict] ของ records

    ใช้งาน:
        loader  = DataLoader(cfg)
        records = loader.load(Path("data/raw/prices.xlsx"))
    """

    SUPPORTED = {".csv", ".xlsx", ".xls", ".pdf", ".json", ".txt", ".zip"}

    def __init__(self, cfg: dict):
        self.cfg       = cfg
        self.encodings = cfg.get("input_files", {}).get(
            "encodings", ["utf-8", "utf-8-sig", "cp874", "tis-620", "latin1"]
        )
        self.max_pages = cfg.get("input_files", {}).get("pdf_max_pages", 500)
        self.max_depth = cfg.get("input_files", {}).get("zip_max_depth", 3)

        self._parsers = {
            ".csv":  CSVParser(self.encodings),
            ".xlsx": XLSXParser(),
            ".xls":  XLSXParser(),
            ".pdf":  PDFParser(self.max_pages),
            ".json": JSONParser(),
            ".txt":  TXTParser(),
        }

    def load(self, path: Path) -> list[dict]:
        suffix = path.suffix.lower()

        if suffix not in self.SUPPORTED:
            logger.warning(f"ไม่รองรับไฟล์ {suffix} — ข้าม {path.name}")
            return []

        if suffix == ".zip":
            return self._load_zip(path)

        parser = self._parsers.get(suffix)
        if parser is None:
            return []

        logger.info(f"กำลัง parse {path.name} ({suffix})")
        return parser.parse(path)

    def _load_zip(self, path: Path) -> list[dict]:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path  = Path(tmp)
            all_files = extract_zip_recursive(
                path, tmp_path, max_depth=self.max_depth
            )
            records: list[dict] = []
            for fp in all_files:
                if not fp.is_file():
                    continue
                if fp.suffix.lower() not in self.SUPPORTED - {".zip"}:
                    continue
                try:
                    recs = self.load(fp)
                    # override source_file เป็นชื่อ ZIP เดิม
                    for r in recs:
                        r["_zip_source"] = path.name
                    records.extend(recs)
                except Exception as e:
                    logger.error(f"  ✗ ภายใน zip {fp.name}: {e}")
        return records
