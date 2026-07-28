from dataclasses import dataclass, field


@dataclass
class TextSpan:
    text: str
    bbox: list[float]
    font_size: float
    is_bold: bool


@dataclass
class PageText:
    page_number: int  # 1-indexed
    raw_text: str
    spans: list[TextSpan]
    is_scanned: bool = False


@dataclass
class TableExtract:
    page_number: int
    bbox: list[float] | None
    rows: list[list[str | None]]
    markdown: str


@dataclass
class ImageExtract:
    page_number: int
    bbox: list[float] | None
    storage_path: str


@dataclass
class Heading:
    page_number: int
    text: str
    level: int  # 1 = highest
    bbox: list[float]


@dataclass
class ChunkDraft:
    temp_id: str
    text: str
    chunk_type: str  # "text" | "table" | "figure"
    page_number: int
    section_title: str | None
    section_path: str | None
    bbox: list[float] | None = None
    token_count: int = 0
    is_parent: bool = False
    parent_temp_id: str | None = None
