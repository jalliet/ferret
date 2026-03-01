import re

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into word-count-based chunks at sentence boundaries.

    Args:
        text: Clean text to chunk.
        chunk_size: Target words per chunk.
        overlap: Words of overlap between chunks.

    Returns:
        List of text chunks.
    """
    if not text.strip():
        return []

    sentences = re.split(r'(?<=[.!?])\s+', text)
    if not sentences:
        return []

    chunks = []
    current_words = []
    current_count = 0

    for sentence in sentences:
        words = sentence.split()
        if not words:
            continue

        if current_count + len(words) > chunk_size and current_count > 0:
            chunks.append(" ".join(current_words))
            if overlap > 0 and len(current_words) > overlap:
                current_words = current_words[-overlap:]
                current_count = len(current_words)
            else:
                current_words = []
                current_count = 0

        current_words.extend(words)
        current_count += len(words)

    if current_words:
        chunks.append(" ".join(current_words))

    return chunks
