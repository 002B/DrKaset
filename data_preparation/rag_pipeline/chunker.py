"""
DrKaset — Record Chunker
=========================
แปลง records → LangChain Documents พร้อม chunk + metadata

  - ใช้ RecursiveCharacterTextSplitter (chunk_size=900, overlap=150)
  - ใส่ metadata ทุก chunk: {crop, region, source_type, file_name, chunk_id}
  - records แบบ PDF ใช้ text ดิบก่อน split
  - records แบบ structured (csv/xlsx) สร้าง text แล้ว split
"""

import hashlib
import logging
from typing import Any

from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

# Separators สำหรับภาษาไทย + English
THAI_SEPARATORS = [
    "\n\n",    # paragraph break
    "\n",      # line break
    "。",     # thai/chinese sentence
    ".",       # english sentence
    "!",
    "?",
    "；",
    ";",
    "，",
    ",",
    " ",
    "",        # character fallback
]


class RecordChunker:
    """
    แปลง list[dict] records → list[Document]

    ใช้งาน:
        chunker = RecordChunker(cfg)
        docs    = chunker.chunk_records(records)
    """

    def __init__(self, cfg: dict):
        chunk_cfg = cfg.get("chunking", {})
        self.chunk_size    = chunk_cfg.get("chunk_size",    900)
        self.chunk_overlap = chunk_cfg.get("chunk_overlap", 150)

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size       = self.chunk_size,
            chunk_overlap    = self.chunk_overlap,
            separators       = THAI_SEPARATORS,
            length_function  = len,
            is_separator_regex = False,
        )

    def chunk_records(self, records: list[dict]) -> list[Document]:
        """
        แปลง records ทั้งหมด → Documents

        Returns:
            list[Document] — langchain Document พร้อม metadata
        """
        all_docs: list[Document] = []
        short_count = 0

        for i, rec in enumerate(records):
            try:
                docs = self._record_to_docs(rec, global_idx=i)
                all_docs.extend(docs)
            except Exception as e:
                logger.debug(f"chunk error record {i}: {e}")

        if short_count:
            logger.debug(f"{short_count} records ที่ไม่ถูก split (text สั้นกว่า chunk_size)")

        logger.info(
            f"Chunking เสร็จ: {len(records)} records → {len(all_docs)} documents"
        )
        return all_docs

    def _record_to_docs(self, record: dict, global_idx: int) -> list[Document]:
        """แปลง record เดียว → list[Document]"""
        text = self._extract_text(record)
        if not text or len(text.strip()) < 5:
            return []

        # metadata พื้นฐาน
        meta = self._build_metadata(record, global_idx)

        # split ถ้า text ยาวกว่า chunk_size
        if len(text) <= self.chunk_size:
            chunk_id = self._make_chunk_id(text, meta, 0)
            meta["chunk_id"] = chunk_id
            return [Document(page_content=text, metadata=meta)]

        chunks = self.splitter.split_text(text)
        docs   = []
        for j, chunk in enumerate(chunks):
            if not chunk.strip():
                continue
            chunk_meta = {**meta, "chunk_index": j, "total_chunks": len(chunks)}
            chunk_meta["chunk_id"] = self._make_chunk_id(chunk, chunk_meta, j)
            docs.append(Document(page_content=chunk, metadata=chunk_meta))

        return docs

    def _extract_text(self, record: dict) -> str:
        """ดึง text จาก record"""
        # ใช้ text field โดยตรงถ้ามี
        text = record.get("text")
        if text and isinstance(text, str) and len(text.strip()) > 5:
            return text.strip()

        # fallback: สร้างจาก fields
        parts: list[str] = []
        priority = ["crop", "region", "province", "price", "price_unit",
                    "date", "year", "month", "season", "variety", "yield"]

        for k in priority:
            v = record.get(k)
            if v is not None and str(v).strip():
                parts.append(f"{k}: {v}")

        skip_keys = set(priority) | {
            "text", "_source_type", "_source_file", "_source_url",
            "_source", "_scraped_at", "_fetched_at", "_page",
            "_sheet", "_zip_source", "chunk_id",
        }
        for k, v in record.items():
            if k not in skip_keys and v is not None and str(v).strip():
                parts.append(f"{k}: {v}")

        return " | ".join(parts)

    def _build_metadata(self, record: dict, idx: int) -> dict:
        """สร้าง metadata dict สำหรับ Document"""
        return {
            "crop":        record.get("crop", ""),
            "region":      record.get("region") or record.get("province", ""),
            "source_type": record.get("_source_type", "unknown"),
            "file_name":   record.get("_source_file", ""),
            "source_url":  record.get("_source_url", ""),
            "page":        record.get("_page", ""),
            "sheet":       record.get("_sheet", ""),
            "record_idx":  idx,
            "price":       record.get("price"),
            "price_unit":  record.get("price_unit", ""),
            "date":        str(record.get("date") or record.get("year", "")),
            "season":      record.get("season", ""),
            "variety":     record.get("variety", ""),
        }

    @staticmethod
    def _make_chunk_id(text: str, meta: dict, chunk_idx: int) -> str:
        """สร้าง unique chunk ID จาก hash"""
        key = f"{meta.get('file_name')}_{meta.get('record_idx')}_{chunk_idx}_{text[:50]}"
        return hashlib.md5(key.encode()).hexdigest()[:12]
