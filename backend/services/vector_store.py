"""
Thin wrappers around FAISS for load / save / incremental merge.
The heavy work (build index) is done in data_preparation/.
"""
from __future__ import annotations
import os
from langchain_community.vectorstores import FAISS
from rag.embedder import get_embedder
from core.config import settings


def load_index(path: str | None = None) -> FAISS | None:
    p = path or settings.FAISS_INDEX_PATH
    if not os.path.exists(p):
        return None
    return FAISS.load_local(p, get_embedder(), allow_dangerous_deserialization=True)


def save_index(store: FAISS, path: str | None = None) -> None:
    p = path or settings.FAISS_INDEX_PATH
    os.makedirs(p, exist_ok=True)
    store.save_local(p)


def merge_from(base: FAISS, other: FAISS) -> FAISS:
    """Merge `other` into `base` in-place and return `base`."""
    base.merge_from(other)
    return base
