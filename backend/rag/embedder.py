from langchain_huggingface import HuggingFaceEmbeddings
from core.config import settings
import threading

_lock = threading.Lock()
_embedder: HuggingFaceEmbeddings | None = None


def get_embedder() -> HuggingFaceEmbeddings:
    global _embedder
    if _embedder is None:
        with _lock:
            if _embedder is None:
                _embedder = HuggingFaceEmbeddings(
                    model_name=settings.EMBEDDING_MODEL,
                    model_kwargs={"device": "cpu"},
                    encode_kwargs={"normalize_embeddings": True},
                )
    return _embedder
