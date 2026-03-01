from dataclasses import dataclass, asdict, field


@dataclass
class FetchResult:
    url: str
    status: int
    text: str
    error: str | None

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def ok(self) -> bool:
        return self.error is None


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ScoredChunk:
    text: str
    source_url: str
    chunk_index: int
    score: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)
