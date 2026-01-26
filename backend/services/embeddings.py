"""Text embedding service using SentenceTransformers."""

import logging
from typing import List
from functools import lru_cache

from sentence_transformers import SentenceTransformer

from config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    """
    Load and cache the embedding model.

    The model is loaded once and reused for all embedding requests.
    """
    logger.info(f"Loading embedding model: {settings.embedding_model}")
    model = SentenceTransformer(settings.embedding_model)
    logger.info(f"Embedding model loaded. Dimension: {model.get_sentence_embedding_dimension()}")
    return model


def embed_text(text: str) -> List[float]:
    """
    Generate embedding for a single text.

    Args:
        text: The text to embed

    Returns:
        List of floats representing the embedding vector
    """
    if not text or not text.strip():
        # Return zero vector for empty text
        return [0.0] * settings.embedding_dimension

    model = get_embedding_model()
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding.tolist()


def embed_batch(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for multiple texts efficiently.

    Args:
        texts: List of texts to embed

    Returns:
        List of embedding vectors
    """
    if not texts:
        return []

    model = get_embedding_model()

    # Replace empty strings with placeholder to maintain alignment
    processed_texts = [t if t and t.strip() else " " for t in texts]

    embeddings = model.encode(processed_texts, convert_to_numpy=True)

    # Convert to list of lists and handle empty inputs
    result = []
    for i, text in enumerate(texts):
        if not text or not text.strip():
            result.append([0.0] * settings.embedding_dimension)
        else:
            result.append(embeddings[i].tolist())

    return result
