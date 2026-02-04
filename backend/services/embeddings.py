"""Text embedding service supporting multiple providers.

Supports:
- voyage: Voyage AI cloud embeddings (low memory, recommended for cloud deployment)
- local: SentenceTransformers local embeddings (high memory, requires PyTorch)
"""

import logging
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import List, Optional

from config import settings

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts efficiently."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the embedding dimension."""
        pass


class VoyageEmbeddingProvider(EmbeddingProvider):
    """Voyage AI cloud embedding provider."""

    # Model dimensions
    MODEL_DIMENSIONS = {
        "voyage-3-large": 1024,
        "voyage-3": 1024,
        "voyage-3-lite": 512,
        "voyage-code-3": 1024,
        "voyage-finance-2": 1024,
        "voyage-law-2": 1024,
    }

    def __init__(self, api_key: str, model: str = "voyage-3-lite"):
        import voyageai

        self.client = voyageai.Client(api_key=api_key)
        self.model = model
        self._dimension = self.MODEL_DIMENSIONS.get(model, 512)
        logger.info(f"Voyage AI embedding provider initialized with model: {model}")

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text using Voyage AI."""
        if not text or not text.strip():
            return [0.0] * self._dimension

        result = self.client.embed([text], model=self.model, input_type="document")
        return result.embeddings[0]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts using Voyage AI."""
        if not texts:
            return []

        # Track which texts are empty for later
        empty_indices = set()
        non_empty_texts = []
        for i, text in enumerate(texts):
            if not text or not text.strip():
                empty_indices.add(i)
            else:
                non_empty_texts.append(text)

        # If all texts are empty, return zero vectors
        if not non_empty_texts:
            return [[0.0] * self._dimension for _ in texts]

        # Get embeddings for non-empty texts
        # Voyage AI recommends batches of up to 128 texts
        all_embeddings = []
        batch_size = 128
        for i in range(0, len(non_empty_texts), batch_size):
            batch = non_empty_texts[i : i + batch_size]
            result = self.client.embed(batch, model=self.model, input_type="document")
            all_embeddings.extend(result.embeddings)

        # Reconstruct results with zero vectors for empty texts
        result = []
        embedding_idx = 0
        for i in range(len(texts)):
            if i in empty_indices:
                result.append([0.0] * self._dimension)
            else:
                result.append(all_embeddings[embedding_idx])
                embedding_idx += 1

        return result


class LocalEmbeddingProvider(EmbeddingProvider):
    """Local SentenceTransformers embedding provider."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        try:
            from sentence_transformers import SentenceTransformer

            logger.info(f"Loading local embedding model: {model_name}")
            self.model = SentenceTransformer(model_name)
            self._dimension = self.model.get_sentence_embedding_dimension()
            logger.info(f"Local embedding model loaded. Dimension: {self._dimension}")
        except ImportError:
            raise ImportError(
                "sentence-transformers is required for local embeddings. "
                "Install with: pip install sentence-transformers"
            )

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        if not text or not text.strip():
            return [0.0] * self._dimension

        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts efficiently."""
        if not texts:
            return []

        # Replace empty strings with placeholder to maintain alignment
        processed_texts = [t if t and t.strip() else " " for t in texts]

        embeddings = self.model.encode(processed_texts, convert_to_numpy=True)

        # Convert to list of lists and handle empty inputs
        result = []
        for i, text in enumerate(texts):
            if not text or not text.strip():
                result.append([0.0] * self._dimension)
            else:
                result.append(embeddings[i].tolist())

        return result


# Global provider instance
_provider: Optional[EmbeddingProvider] = None


@lru_cache(maxsize=1)
def get_embedding_provider() -> EmbeddingProvider:
    """
    Get the configured embedding provider.

    Uses settings.embedding_provider to determine which provider to use:
    - "voyage": Voyage AI cloud embeddings (recommended for cloud deployment)
    - "local": SentenceTransformers local embeddings (high memory)
    """
    global _provider
    if _provider is not None:
        return _provider

    provider_type = settings.embedding_provider

    if provider_type == "voyage":
        if not settings.voyage_api_key:
            raise ValueError(
                "VOYAGE_API_KEY environment variable is required for Voyage AI embeddings. "
                "Get your API key from https://dash.voyageai.com/"
            )
        _provider = VoyageEmbeddingProvider(
            api_key=settings.voyage_api_key, model=settings.embedding_model
        )
    elif provider_type == "local":
        _provider = LocalEmbeddingProvider(model_name=settings.embedding_model)
    else:
        raise ValueError(
            f"Unknown embedding provider: {provider_type}. "
            "Supported providers: 'voyage', 'local'"
        )

    return _provider


def embed_text(text: str) -> List[float]:
    """
    Generate embedding for a single text.

    Args:
        text: The text to embed

    Returns:
        List of floats representing the embedding vector
    """
    provider = get_embedding_provider()
    return provider.embed_text(text)


def embed_batch(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for multiple texts efficiently.

    Args:
        texts: List of texts to embed

    Returns:
        List of embedding vectors
    """
    provider = get_embedding_provider()
    return provider.embed_batch(texts)


def get_embedding_dimension() -> int:
    """Get the dimension of embeddings from the current provider."""
    provider = get_embedding_provider()
    return provider.dimension
