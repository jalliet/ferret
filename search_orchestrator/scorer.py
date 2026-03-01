from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def score_chunks(query: str, chunks: list[dict]) -> list[dict]:
    """Score chunks by TF-IDF cosine similarity to query.

    Args:
        query: Search query string.
        chunks: List of {"text": str, "source_url": str, "chunk_index": int}.

    Returns:
        Same dicts with "score" added, sorted by score descending.
    """
    if not chunks:
        return []

    texts = [c["text"] for c in chunks]
    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform([query] + texts)

    similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()

    for i, chunk in enumerate(chunks):
        chunk["score"] = round(float(similarities[i]), 4)

    return sorted(chunks, key=lambda c: c["score"], reverse=True)
