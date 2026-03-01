import threading
from sentence_transformers import CrossEncoder

_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"
_model = None
_model_lock = threading.Lock()


def _get_model():
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                _model = CrossEncoder(_MODEL_NAME)
    return _model


def score_chunks(query: str, chunks: list[dict]) -> list[dict]:
    """Score chunks by cross-encoder relevance to query.

    Uses MS-MARCO MiniLM-L6 cross-encoder (~80MB, CPU) for semantic
    query-passage scoring. Lazy-loads model on first call.

    Args:
        query: Search query string.
        chunks: List of {"text": str, "source_url": str, "chunk_index": int}.

    Returns:
        Same dicts with "score" added, sorted by score descending.
    """
    if not chunks:
        return []

    model = _get_model()
    pairs = [(query, c["text"]) for c in chunks]
    scores = model.predict(pairs)

    for i, chunk in enumerate(chunks):
        chunk["score"] = round(float(scores[i]), 4)

    return sorted(chunks, key=lambda c: c["score"], reverse=True)
