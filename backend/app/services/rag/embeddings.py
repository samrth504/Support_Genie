"""Embeddings: text -> vector of 384 numbers, so "similar meaning" = "nearby vectors".

We wrap fastembed (ONNX, CPU-only, ~70 MB model, no API key, no rate limits) in LangChain's
`Embeddings` interface, so any LangChain component can use it.
"""
import logging
from functools import lru_cache

from langchain_core.embeddings import Embeddings

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class FastEmbedEmbeddings(Embeddings):
    def __init__(self, model_name: str, cache_dir: str | None = None):
        from fastembed import TextEmbedding  # imported lazily: heavy import

        logger.info("Loading embedding model %s ...", model_name)
        self._model = TextEmbedding(model_name=model_name, cache_dir=cache_dir)
        logger.info("Embedding model ready")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        # passage_embed adds the model's recommended "passage" formatting
        return [vec.tolist() for vec in self._model.passage_embed(texts)]

    def embed_query(self, text: str) -> list[float]:
        # bge models work better when queries get the "search query" instruction
        return next(iter(self._model.query_embed(text))).tolist()


@lru_cache
def get_embedder() -> Embeddings:
    """One model per process (loading takes a few seconds)."""
    settings = get_settings()
    settings.embedding_cache_dir.mkdir(parents=True, exist_ok=True)
    return FastEmbedEmbeddings(settings.embedding_model, cache_dir=str(settings.embedding_cache_dir))
