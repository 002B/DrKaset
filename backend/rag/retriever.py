from __future__ import annotations
from langchain_community.vectorstores import FAISS
from rag.embedder import get_embedder
from core.config import settings
from core.crop_constants import TOP_K, TOP_K_COMPARE
import os

_faiss_store: FAISS | None = None


def load_faiss() -> FAISS | None:
    global _faiss_store
    path = settings.FAISS_INDEX_PATH
    if os.path.exists(path):
        _faiss_store = FAISS.load_local(
            path,
            get_embedder(),
            allow_dangerous_deserialization=True,
        )
        print(f"[FAISS] Loaded index from {path}")
    else:
        print(f"[FAISS] Index not found at {path}. Run data_preparation pipeline first.")
    return _faiss_store


def get_store() -> FAISS | None:
    return _faiss_store


def retrieve(query: str, crop: str | None = None, region: str | None = None, k: int = TOP_K) -> list[dict]:
    """Search FAISS and return list of {page_content, metadata} dicts."""
    if _faiss_store is None:
        return []

    docs = _faiss_store.similarity_search(query, k=k * 2)   # over-fetch then filter

    results = []
    for doc in docs:
        meta = doc.metadata
        if crop and meta.get("crop") and meta["crop"] != crop:
            continue
        if region and meta.get("region") and meta["region"] != region:
            continue
        results.append({"content": doc.page_content, "metadata": meta})
        if len(results) >= k:
            break

    # If strict filter yields nothing, return unfiltered top-k
    if not results:
        results = [{"content": d.page_content, "metadata": d.metadata} for d in docs[:k]]

    return results
